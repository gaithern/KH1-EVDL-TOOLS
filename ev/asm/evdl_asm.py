"""ASM text format for KH1 event scripts: disassembler and assembler."""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from evdl_format import (
    ALU, ALU_BY_NAME, ALU_OPS, BRANCH_OPCODES, CALL_OPCODES, LOCAL_VARIABLE_OPCODES,
    MEMORY_OPCODES, OPCODE_BY_NAME, OPCODES, PUSH, REPO_ROOT, SAVE_DATA_LABELS, SCRIPT_HEADER,
    SYSCALL, SYSCALL_BY_NAME, SYSCALLS, VALID_OPS, ZERO_WORD, encode_instruction, find_kgrs,
    find_script_headers, opcode_of, operand_of, parse_ard, parse_evdl, parse_evdl_string_table,
    repack_ard, repack_evdl, sign24, words_of,
)

WORKING = REPO_ROOT / 'working'

DISPLAY_MESSAGE_SYSCALL = 1
SET_CHAR_ID_SYSCALL = 10
SEPARATOR = '; ' + '─' * 72


class EvdlAsmError(Exception):
    pass


def strip_suffix_ignoring_case(text, suffix):
    if text.lower().endswith(suffix):
        return text[:-len(suffix)]
    return text


def describe_memory_address(address):
    label = SAVE_DATA_LABELS.get(address, '')
    label_suffix = f'  ({label})' if label else ''
    if address < 0x900:
        return f'save_data[0x{address:X}]{label_suffix}'
    if address < 0xB00:
        return f'runtime?[0x{address:X}]{label_suffix}'
    if address < 0xC80:
        if label:
            return f'save_data[0x{address - 0x200:X}]{label_suffix}'
        return f'save_data[0x{address - 0x200:X}]  (alias, unsigned)'
    if address < 0xD40:
        return f'runtime?[0x{address:X}]{label_suffix}'
    return f'save_data2[0x{address - 0xD40:X}]{label_suffix}'


def find_branch_targets(words):
    targets = set()
    for pc, word in enumerate(words):
        if opcode_of(word) in BRANCH_OPCODES:
            target = pc + sign24(operand_of(word))
            if 0 <= target < len(words):
                targets.add(target)
    return targets


def name_branch_targets(words, headers, source_name, kgr_index):
    prefix = (source_name + '.asm').replace('.', '_')
    labels_per_script = {}
    names = {}
    for target in sorted(find_branch_targets(words)):
        headers_before = sum(1 for header in headers if header < target)
        script = max(headers_before - 1, 0)
        number = labels_per_script.get(script, 0)
        labels_per_script[script] = number + 1
        names[target] = f'{prefix}_KGR_{kgr_index}_SCRIPT_{script}_{number}'
    return names


def find_character_id(words, script_start, script_end):
    for pc in range(script_start + 1, script_end):
        word = words[pc]
        previous = words[pc - 1]
        if opcode_of(word) == SYSCALL and operand_of(word) == SET_CHAR_ID_SYSCALL and opcode_of(previous) == PUSH:
            return f'0x{operand_of(previous):X}'
    return None


def find_character_ids(words, headers):
    script_ends = headers[1:] + [len(words)]
    return [find_character_id(words, start, end) for start, end in zip(headers, script_ends)]


def find_display_message_ids(words):
    message_ids = {}
    for pc in range(len(words) - 1):
        word = words[pc]
        next_word = words[pc + 1]
        if opcode_of(word) == PUSH and opcode_of(next_word) == SYSCALL and operand_of(next_word) == DISPLAY_MESSAGE_SYSCALL:
            message_ids[pc] = operand_of(word)
    return message_ids


def format_data_blob(words, start):
    blob = b''
    pc = start
    while pc < len(words) and opcode_of(words[pc]) not in VALID_OPS:
        blob += bytes(words[pc])
        pc += 1
    text = blob.rstrip(b'\x00').decode('latin-1')
    return f"  {'':8}  ; db  '{text}'"


def format_message_comment(text):
    message_lines = text.split('{lf}')
    comment = [f'; Message: {message_lines[0]}']
    for line in message_lines[1:]:
        comment.append(f';          {line}')
    return comment


def format_script_banner(script_number, subscript_count, pc, stream_offset, kgr_index):
    file_offset = stream_offset + pc * 4
    return [
        '',
        SEPARATOR,
        f'; Script {script_number}  |  {subscript_count} subscript(s)  |  PC {pc}  |  file 0x{file_offset:X}  |  KGR {kgr_index}',
        SEPARATOR,
        '',
    ]


def describe_call_target(script_number, headers, character_ids):
    if script_number >= len(headers):
        return f'→ Script {script_number} (outside KGR)'
    description = f'→ Script {script_number}'
    if character_ids[script_number]:
        description += f' ({character_ids[script_number]})'
    return description + f'  PC {headers[script_number]}'


def format_instruction(pc, word, label_names, headers, character_ids):
    opcode = opcode_of(word)
    operand = operand_of(word)
    hex_text = word.hex().upper()
    operand_text = ''
    comment = ''

    if opcode == ALU:
        operand_text = ALU_OPS.get(operand, f'sub_{operand}')
    elif opcode in BRANCH_OPCODES:
        offset = sign24(operand)
        target = pc + offset
        comment = f'→ PC {target}'
        if target in label_names:
            operand_text = f'@{label_names[target]}'
            hex_text = '????????'
        else:
            operand_text = f'{offset:+}'
    elif opcode == SYSCALL:
        operand_text = str(operand)
        comment = SYSCALLS.get(operand, '')
    elif opcode in MEMORY_OPCODES:
        operand_text = f'[0x{operand:X}]'
        comment = describe_memory_address(operand)
    elif opcode in LOCAL_VARIABLE_OPCODES:
        operand_text = f'[{operand}]'
    elif opcode == PUSH:
        operand_text = f'0x{operand:X}'
        if operand > 9:
            comment = str(operand)
    elif opcode in CALL_OPCODES:
        operand_text = f'0x{operand:X}'
        comment = describe_call_target(operand, headers, character_ids)
    elif operand:
        operand_text = f'0x{operand:X}'

    comment_text = f'  ; {comment}' if comment else ''
    return f'  {hex_text}  {OPCODES[opcode]:<14}  {operand_text:<16}{comment_text}'


def disassemble_stream(stream, stream_offset, title, source_name, kgr_index, messages):
    words = words_of(stream)
    headers = find_script_headers(words)
    label_names = name_branch_targets(words, headers, source_name, kgr_index)
    character_ids = find_character_ids(words, headers)
    message_ids = find_display_message_ids(words) if messages else {}

    lines = [SEPARATOR, f'; KGR  {title}', f'; Stream @ 0x{stream_offset:X}  ({len(words)} instructions)', SEPARATOR, '']
    for pc, word in enumerate(words):
        if opcode_of(word) not in VALID_OPS:
            if pc == 0 or opcode_of(words[pc - 1]) in VALID_OPS:
                lines.append(format_data_blob(words, pc))
            continue
        if pc in label_names:
            lines.append(f'@{label_names[pc]}:')
        if pc in message_ids and messages.get(message_ids[pc]) is not None:
            lines += format_message_comment(messages[message_ids[pc]])
        if pc in headers:
            lines += format_script_banner(headers.index(pc), operand_of(word), pc, stream_offset, kgr_index)
            continue
        lines.append(format_instruction(pc, word, label_names, headers, character_ids))

    lines.append('')
    return '\n'.join(lines)


def disassemble_kgr(kgr, index, kgr_count, source_name, messages):
    text = ''
    if kgr_count > 1:
        text += f'\n\n{"#" * 76}\n# KGR[{index}]'
        if kgr['ard_section'] is not None:
            text += f'  section={kgr["ard_section"]}'
        text += f'  KGR@0x{kgr["kgr_offset"]:X}  stream@0x{kgr["stream_abs"]:X}\n{"#" * 76}\n'
    title = f'{source_name}  KGR@0x{kgr["kgr_offset"]:X}  NN={kgr["nn_scripts"]}'
    return text + disassemble_stream(kgr['stream'], kgr['stream_abs'], title, source_name, index, messages)


PLACEHOLDER_HEX = '????????'
INSTRUCTION_LINE = re.compile(r'^\s*(?:\[\s*(?:\d+|new|-|\*)\s*\]\s+)?([0-9A-Fa-f?]{8})\s*(.*)')
LABEL_LINE = re.compile(r'^\s*@(\w+)\s*:\s*$')
DATA_LINE = re.compile(r'^\s*(?:\[\s*(?:\d+|new|-|\*)\s*\]\s+)?;\s+db\s+(.+)$')
BANNER_LINE = re.compile(r'^(#{10,}|;\s*-{10,}|;\s*KGR\b|;\s*Script\b)')
SCRIPT_HEADER_LINE = re.compile(r';\s*Script\s+\d+\s*\|\s*(\d+)\s*subscript')
KGR_BANNER = re.compile(r'^#{10,}[^\n]*\n#\s*KGR\[', re.MULTILINE)


def parse_int(text):
    text = text.strip().rstrip(',;')
    if text.lower().startswith('0x'):
        return int(text, 16)
    try:
        return int(text, 10)
    except ValueError:
        return int(text, 16)


def number_or_zero(text):
    try:
        return parse_int(text)
    except ValueError:
        return 0


def remove_comment(text):
    return text.split(';', 1)[0].strip()


def parse_syscall(text):
    try:
        return parse_int(text)
    except ValueError:
        pass
    if text.lower() not in SYSCALL_BY_NAME:
        raise ValueError(f'Unknown syscall: {text}')
    return SYSCALL_BY_NAME[text.lower()]


def parse_alu_operation(text):
    name = text.lower()
    if name in ALU_BY_NAME:
        return ALU_BY_NAME[name]
    numbered = re.fullmatch(r'sub_(\d+)', name)
    if numbered:
        return int(numbered.group(1))
    return parse_int(name)


def encode_mnemonic(mnemonic, operands):
    name = mnemonic.lower()
    arguments = remove_comment(operands).split()
    first = arguments[0] if arguments else ''
    if name in ('nop', 'yield'):
        return encode_instruction(OPCODE_BY_NAME[name], number_or_zero(first))
    if name == 'push':
        return encode_instruction(PUSH, parse_int(first))
    if name == 'syscall':
        return encode_instruction(SYSCALL, parse_syscall(first))
    if name == 'alu':
        return encode_instruction(ALU, parse_alu_operation(first))
    if name in ('jmp', 'beqz'):
        return encode_instruction(OPCODE_BY_NAME[name], parse_int(first.lstrip('+')))
    if name not in OPCODE_BY_NAME:
        raise ValueError(f'Unknown mnemonic: {name}')
    return encode_instruction(OPCODE_BY_NAME[name], number_or_zero(first.lstrip('[').rstrip(']')))


def is_ignored_line(line):
    if not line or line.startswith('#') or BANNER_LINE.match(line):
        return True
    return line.startswith(';') and not line.startswith('; db')


def parse_instruction(match):
    rest = match.group(2).strip()
    mnemonic = rest.split()[0] if rest else ''
    operands = remove_comment(rest[len(mnemonic):])
    return {'kind': 'instruction', 'hex': match.group(1), 'mnemonic': mnemonic, 'operands': operands}


def parse_asm_line(raw_line):
    line = raw_line.strip()
    header = SCRIPT_HEADER_LINE.search(line)
    if header:
        return {'kind': 'script_header', 'subscript_count': int(header.group(1))}
    if is_ignored_line(line):
        return None
    label = LABEL_LINE.match(line)
    if label:
        return {'kind': 'label', 'name': label.group(1)}
    data = DATA_LINE.match(raw_line)
    if data:
        return {'kind': 'data', 'spec': data.group(1).strip()}
    instruction = INSTRUCTION_LINE.match(raw_line)
    if instruction:
        return parse_instruction(instruction)
    return None


def parse_asm_section(text):
    lines = []
    for raw_line in text.splitlines():
        parsed = parse_asm_line(raw_line)
        if parsed is not None:
            lines.append(parsed)
    return lines


def find_label_pcs(lines):
    label_pcs = {}
    pc = 0
    for line in lines:
        if line['kind'] == 'label':
            label_pcs[line['name']] = pc
        if line['kind'] in ('script_header', 'instruction'):
            pc += 1
    return label_pcs


def data_bytes(spec):
    spec = spec.strip()
    if re.fullmatch(r'[0-9A-Fa-f]+', spec) and len(spec) % 2 == 0:
        return bytes.fromhex(spec)
    return spec.strip("'").encode('latin-1', errors='replace')


def is_branch_to_label(line):
    return line['mnemonic'].lower() in ('jmp', 'beqz') and line['operands'].startswith('@')


def assemble_section(lines):
    label_pcs = find_label_pcs(lines)
    output = bytearray()
    errors = []
    undefined_label_errors = []
    pc = 0
    for line in lines:
        if line['kind'] == 'script_header':
            output += encode_instruction(SCRIPT_HEADER, line['subscript_count'])
            pc += 1
        elif line['kind'] == 'data':
            output += data_bytes(line['spec'])
        elif line['kind'] == 'instruction':
            if line['hex'] != PLACEHOLDER_HEX:
                word = bytes.fromhex(line['hex'])
            elif is_branch_to_label(line):
                label = line['operands'][1:].split()[0]
                opcode = OPCODE_BY_NAME[line['mnemonic'].lower()]
                if label in label_pcs:
                    word = encode_instruction(opcode, label_pcs[label] - pc)
                else:
                    word = encode_instruction(opcode, 0)
                    undefined_label_errors.append(f'Undefined label: @{label}')
            else:
                try:
                    word = encode_mnemonic(line['mnemonic'], line['operands'])
                except ValueError as error:
                    errors.append(f'PC {pc} ({line["mnemonic"]} {line["operands"]}): {error}')
                    word = ZERO_WORD
            output += word
            pc += 1
    return bytes(output), errors + undefined_label_errors


def split_asm_text(text):
    starts = [match.start() for match in KGR_BANNER.finditer(text)]
    if not starts:
        return [text]
    ends = starts[1:] + [len(text)]
    return [text[start:end] for start, end in zip(starts, ends)]


def assemble_text(text):
    streams = []
    errors = []
    for index, section in enumerate(split_asm_text(text)):
        stream, section_errors = assemble_section(parse_asm_section(section))
        streams.append(stream)
        errors += [f'KGR[{index}] {error}' for error in section_errors]
    return streams, errors


def make_file_header(input_path, file_type, kgrs):
    return (
        f'; evdl-tool disassembly\n'
        f'; source: {os.path.basename(input_path)}\n'
        f'; type: {file_type}\n'
        f'; kgr_count: {len(kgrs)}\n'
        f'; --- Do not edit the lines above ---\n'
        '\n'
    )


def parse_file_header(text):
    for line in text.splitlines():
        match = re.match(r'^;\s*type:\s*(\S+)', line)
        if match:
            return {'file_type': match.group(1)}
    return {'file_type': None}


def read_source_name(text):
    for line in text.splitlines():
        match = re.match(r'^;\s*source:\s*(.+)', line)
        if match:
            return match.group(1).strip()
    return None


def parse_binary(data, input_path):
    if os.path.splitext(input_path)[1].lower() == '.ard':
        try:
            return parse_ard(data), 'ard'
        except Exception:
            pass
    kgrs = find_kgrs(data)
    if kgrs:
        return kgrs, 'evdl'
    try:
        return parse_ard(data), 'ard'
    except Exception as error:
        raise EvdlAsmError(f'No KGR sections found in {os.path.basename(input_path)}: {error}')


def disassemble_file(input_path, output_path=None):
    if not os.path.exists(input_path):
        raise EvdlAsmError(f'File not found: {input_path}')
    data = Path(input_path).read_bytes()
    kgrs, file_type = parse_binary(data, input_path)
    source_name = os.path.basename(input_path)
    messages = parse_evdl_string_table(data) if file_type == 'evdl' else {}

    text = make_file_header(input_path, file_type, kgrs)
    for index, kgr in enumerate(kgrs):
        text += disassemble_kgr(kgr, index, len(kgrs), source_name, messages)

    if not output_path:
        output_path = str(WORKING / (source_name + '.asm'))
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(text)
    print(f'Disassembled {len(kgrs)} KGR section(s) → {output_path}')


def default_assembly_output(input_path, detected_type):
    base = strip_suffix_ignoring_case(input_path, '.asm')
    source_extension = os.path.splitext(base)[1].lower().lstrip('.')
    if source_extension and source_extension not in ('evdl', 'ard', 'ev'):
        return base, source_extension
    extension = detected_type or source_extension or 'evdl'
    for suffix in ('.evdl', '.ard', '.ev'):
        if base.lower().endswith(suffix):
            base = base[:-len(suffix)]
            break
    return base + '.' + extension, extension


def find_original_binary(asm_path, source_name):
    candidates = []
    if source_name:
        asm_dir = os.path.dirname(os.path.abspath(asm_path))
        candidates.append(os.path.join(asm_dir, source_name))
        candidates.append(os.path.abspath(source_name))
    candidates.append(strip_suffix_ignoring_case(asm_path, '.asm'))
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def assemble_file(input_path, output_path=None, original_path=None):
    if not os.path.exists(input_path):
        raise EvdlAsmError(f'File not found: {input_path}')
    with open(input_path, 'r', encoding='utf-8') as file:
        text = file.read()
    detected_type = parse_file_header(text)['file_type']

    if output_path:
        output_extension = os.path.splitext(output_path)[1].lower().lstrip('.') or 'evdl'
    else:
        output_path, output_extension = default_assembly_output(input_path, detected_type)
    file_type = detected_type or ('ard' if output_extension == 'ard' else 'evdl')

    new_streams, errors = assemble_text(text)
    if errors:
        print('Assembly errors:', file=sys.stderr)
        for error in errors:
            print(f'  {error}', file=sys.stderr)

    if not original_path:
        source_name = read_source_name(text)
        original_path = find_original_binary(input_path, source_name)
        if not original_path:
            raise EvdlAsmError(
                f'Cannot find original binary to repack into.\n'
                f'Expected "{source_name or "source file"}" next to the .asm file.\n'
                f'Usage: python evdl-tool.py asm <input.asm> [output.evdl]'
            )
    original = Path(original_path).read_bytes()

    try:
        kgrs = parse_ard(original) if file_type == 'ard' else parse_evdl(original)
    except Exception as error:
        raise EvdlAsmError(f'Failed to parse original binary: {error}')

    if len(new_streams) != len(kgrs):
        print(f'Warning: asm has {len(new_streams)} KGR section(s), binary has {len(kgrs)}. Using available sections.', file=sys.stderr)
        for kgr in kgrs[len(new_streams):]:
            new_streams.append(bytes(kgr['stream']))

    try:
        if file_type == 'ard':
            output = repack_ard(original, kgrs, new_streams)
        else:
            output = repack_evdl(original, kgrs, new_streams)
    except Exception as error:
        raise EvdlAsmError(f'Repack failed: {error}')

    Path(output_path).write_bytes(output)
    if errors:
        print(f'Assembled with {len(errors)} error(s) → {output_path}')
    else:
        print(f'Assembled {len(kgrs)} KGR section(s) → {output_path}')
