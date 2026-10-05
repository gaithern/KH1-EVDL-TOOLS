#!/usr/bin/env python3
# Disassembler for KH1 enemy behavior scripts (.bd blocks inside xa_*.mdls): a raw instruction
# listing, or with --fold a structured pseudocode view built from a stack simulation.
import json
import os
import re
import struct
import sys

USAGE = """Usage:
  python kh1_bd_disasm.py <file.mdls>                  list behavior blocks
  python kh1_bd_disasm.py <file.mdls> <block|all>      disassemble (block = name part or index)
  python kh1_bd_disasm.py <file.mdls> <block> --fold   fold into pseudocode
"""

CLASS_UNARY = 0
CLASS_ARITH = 1
CLASS_PUSH = 2
CLASS_STORE = 3
CLASS_JUMP = 4
CLASS_BRANCH_IF_ZERO = 5
CLASS_BRANCH_IF_NONZERO = 6
CLASS_COMPARE = 7
CLASS_CALL = 8
CLASS_INDEX_ADD = 9
CLASS_LOAD = 0xA
CLASS_NATIVE = 0xB

BRANCH_CLASSES = (CLASS_BRANCH_IF_ZERO, CLASS_BRANCH_IF_NONZERO)
JUMP_CLASSES = (CLASS_JUMP, CLASS_BRANCH_IF_ZERO, CLASS_BRANCH_IF_NONZERO)
FOUR_BYTE_CLASSES = (CLASS_STORE, CLASS_JUMP, CLASS_BRANCH_IF_ZERO, CLASS_BRANCH_IF_NONZERO, CLASS_CALL)

PUSH_INT = 0
PUSH_FLOAT = 1
PUSH_ADDRESS = 2
PUSH_VALUE = 3

BASE_IMMEDIATE = 3

UNARY_YIELD = 0
UNARY_INT_ABS = 1
UNARY_FLOAT_ABS = 2
UNARY_RETURN = 3
UNARY_POP = 4
UNARY_FLOAT_TO_INT = 5
UNARY_FLOAT_TO_INT2 = 6
UNARY_STORE_INDIRECT = 7
UNARY_ABORT = 8
UNARY_INT_NEGATE = 9
UNARY_FLOAT_NEGATE = 10
UNARY_BIT_NOT = 11
UNARY_DUP = 12
UNARY_LOGICAL_NOT = 13

ARITH_SUB = 1
ARITH_LOGICAL_AND = 10
ARITH_LOGICAL_OR = 11

OP_YIELD = 0x0000
OP_RETURN = 0x0300
OP_ABORT = 0x0800

BD_MAGIC = b"\x14\x03"
BD_NAME_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_."
MAX_NAME_READ = 24
MAX_PADDING_WORDS = 3
MAX_SKIPPED_LEADING_INSTRUCTIONS = 4
WORD_SIZE = 4
SPILL_LENGTH = 300

UNARY = {
    0: "yield",
    1: "iabs",
    2: "fabs",
    3: "ret",
    4: "pop",
    5: "ftoi",
    6: "ftoi2",
    7: "store.ind",
    8: "abort",
    9: "ineg",
    10: "fneg",
    11: "bnot",
    12: "dup",
    13: "lnot",
}
ARITH = {
    0: "add",
    1: "sub",
    2: "mul",
    3: "div",
    4: "mod",
    5: "and",
    6: "or",
    7: "xor",
    8: "shl",
    9: "shr",
    10: "land",
    11: "lor",
}
CMP = {0: "ltz", 1: "lez", 2: "eqz", 3: "nez", 4: "gez", 5: "gtz"}
BASE = {0: "loc", 1: "glob", 2: "heap", 3: "imm"}
MODESFX = {0: "i", 1: "f", 2: "m2", 3: "m3"}
JUMP_MNEMONICS = {
    CLASS_JUMP: "jmp",
    CLASS_BRANCH_IF_ZERO: "bz",
    CLASS_BRANCH_IF_NONZERO: "bnz",
    CLASS_CALL: "call",
}

VERBS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kh1_bd_verbs.json")


def load_verbs():
    try:
        with open(VERBS_PATH) as file:
            verb_table = json.load(file)
        names = {}
        for key, entry in verb_table.items():
            if not key.startswith("_"):
                names[key] = entry.get("name")
        return names
    except Exception:
        return {}


VERBS = load_verbs()


def load_arity():
    try:
        with open(VERBS_PATH) as file:
            verb_table = json.load(file)
        arity = {}
        for table in (0, 1):
            for index, pair in enumerate(verb_table.get("_arity_t%d" % table, [])):
                arity[(table, index)] = tuple(pair)
        return arity
    except Exception:
        return {}


ARITY = load_arity()


def opcode_class(op):
    return op & 0xF


def opcode_mode(op):
    return (op >> 4) & 3


def opcode_base(op):
    return (op >> 6) & 3


def opcode_sub(op):
    return op >> 8


def ilen(op):
    op_class = opcode_class(op)
    if op_class == CLASS_PUSH:
        if opcode_mode(op) in (PUSH_INT, PUSH_FLOAT):
            return 6
        return 4
    if op_class in FOUR_BYTE_CLASSES:
        return 4
    return 2


def is_invalid_opcode(op):
    return opcode_class(op) == CLASS_UNARY and opcode_sub(op) not in UNARY


def f32_text(four_bytes):
    value = struct.unpack("<f", four_bytes)[0]
    if value != value or value in (float("inf"), float("-inf")):
        return "0x" + four_bytes[::-1].hex()
    for precision in range(1, 10):
        text = f"{value:.{precision}g}"
        if struct.pack("<f", float(text)) != four_bytes:
            continue
        if "e" in text and (value == 0 or abs(value) >= 1e-4):
            plain = format(float(text), "f").rstrip("0").rstrip(".")
            if struct.pack("<f", float(plain)) == four_bytes:
                text = plain
        return text
    return repr(value)


def u16(buffer, offset):
    return struct.unpack_from("<H", buffer, offset)[0]


def s16(buffer, offset):
    return struct.unpack_from("<h", buffer, offset)[0]


def i32(buffer, offset):
    return struct.unpack_from("<i", buffer, offset)[0]


def f32(buffer, offset):
    return struct.unpack_from("<f", buffer, offset)[0]


def _sibling_motion_dict(mdls_path):
    mset_path = os.path.splitext(mdls_path)[0] + ".mset"
    try:
        from kh1_motion_dict import read_motion_dict
        return read_motion_dict(mset_path)
    except Exception:
        return {}


def _is_bd_name(name):
    if not 3 <= len(name) <= 20:
        return False
    if b"." not in name:
        return False
    if not chr(name[0]).isalpha():
        return False
    for byte in name:
        if chr(byte) not in BD_NAME_CHARS:
            return False
    return True


def _read_block_name(data, block_off):
    return data[block_off + 4:block_off + 4 + MAX_NAME_READ].split(b"\x00")[0]


def find_blocks(data):
    blocks = []
    for match in re.finditer(BD_MAGIC, data):
        block_off = match.start()
        name = _read_block_name(data, block_off)
        if not _is_bd_name(name):
            continue
        size = u16(data, block_off + 2)
        if size > 0 and block_off + 4 + size <= len(data) + 16:
            blocks.append((block_off, name.decode("ascii", "replace"), size))
    return blocks


def _count_valid_instructions(data, start, end):
    pos = start
    instruction_count = 0
    zero_run = 0
    while pos < end - 1:
        op = u16(data, pos)
        if op == OP_YIELD:
            zero_run += 1
            if zero_run > MAX_PADDING_WORDS:
                break
            pos += 2
            continue
        zero_run = 0
        if is_invalid_opcode(op):
            break
        instruction_count += 1
        pos += ilen(op)
    return instruction_count


def _skip_leading_jumps_and_yields(data, start):
    for _ in range(MAX_SKIPPED_LEADING_INSTRUCTIONS):
        op = u16(data, start)
        if opcode_class(op) in JUMP_CLASSES or op == OP_YIELD:
            start += ilen(op)
        else:
            break
    return start


def code_start(data, block_off, name, end):
    first_candidate = block_off + 4 + len(name)
    if first_candidate % 2:
        first_candidate += 1
    best_start = None
    best_count = -1
    for candidate in range(first_candidate, end - 2, 2):
        count = _count_valid_instructions(data, candidate, end)
        if count > best_count:
            best_start = candidate
            best_count = count
    if best_start is None:
        return first_candidate
    return _skip_leading_jumps_and_yields(data, best_start)


def _is_block_header_at(data, pos):
    return data[pos:pos + 2] == BD_MAGIC and _is_bd_name(_read_block_name(data, pos))


def extend_end(data, block_off, start, end):
    pos = start
    zero_run = 0
    limit = len(data)
    while pos < limit - 1:
        if pos < end:
            pos += ilen(u16(data, pos))
            continue
        if _is_block_header_at(data, pos):
            break
        op = u16(data, pos)
        if op == OP_YIELD:
            zero_run += 1
            if zero_run > MAX_PADDING_WORDS:
                break
            pos += 2
            continue
        zero_run = 0
        if is_invalid_opcode(op):
            break
        pos += ilen(op)
    return max(pos, end)


def _code_region(data, block_off, name, size):
    declared_end = min(block_off + 4 + size, len(data))
    start = code_start(data, block_off, name, declared_end)
    end = extend_end(data, block_off, start, declared_end)
    return start, end


def _rename_roles(text, roles):
    for role, slot in roles.items():
        text = text.replace(f"globblk[{slot}]", role)
        text = text.replace(f"glob[{slot}]", role)
        text = re.sub(rf"glob\+{slot}\b", role, text)
    return text


ACTOR_VECS = {4: "pos", 8: "vel?", 12: "rot", 16: "scale"}
ACTOR_FIELDS = {26: "model?", 27: "stats", 28: "state?", 29: "target", 31: "other?"}
STATS_FIELDS = {15: "hp", 16: "max_hp", 17: "mp"}
_ACTOR_BASE = r"self(?:\.(?:target|other\?))*"
_FIELD_RE = re.compile(r"(?<![\w.])(" + _ACTOR_BASE + r")\[(\d+)\](:(\d+))?")
_STATS_RE = re.compile(r"(?<![\w.])(" + _ACTOR_BASE + r"\.stats)\[(\d+)\](?![:\d])")
_NAMED_GLOB_RE = re.compile(r"(?<![\w.])(&?)glob\[(\d+)\](?::(\d+))?")
_LABEL_LINE_RE = re.compile(r"^(@L[0-9A-F]{4}(?:,@L[0-9A-F]{4})*):(.*)$")
_CALL_LABEL_RE = re.compile(r"call (@L[0-9A-F]{4})\(")
_ARGUMENT_LABEL_RE = re.compile(r"(?<![\w@])(@L[0-9A-F]{4})(?=[,)])")
VECTOR_COMPONENTS = "xyzw"

NAMES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "names")


def load_names(block_name):
    path = os.path.join(NAMES_DIR, block_name + ".json")
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except (OSError, ValueError):
        return {}


def _apply_glob_names(text, glob_names):
    def replace_glob(match):
        slot = int(match.group(2))
        width = match.group(3)
        if slot not in glob_names:
            return match.group(0)
        replacement = f"{match.group(1)}{glob_names[slot]}"
        if width and width not in ("3", "4"):
            replacement += f":{width}"
        return replacement

    return _NAMED_GLOB_RE.sub(replace_glob, text)


def _name_label_line(match, routine_names):
    labels = match.group(1)
    given_names = []
    for label in labels.split(","):
        if label in routine_names:
            given_names.append(routine_names[label])
    if not given_names:
        return match.string
    rest = match.group(2).strip()
    if rest.startswith(";"):
        rest = rest[1:].strip()
    line = f"{labels}:  ; {given_names[0]}"
    if rest:
        line += f" - {rest}"
    return line


def _name_routine_references(line, routine_names):
    def replace_call(match):
        if match.group(1) in routine_names:
            return f"call {routine_names[match.group(1)]}("
        return match.group(0)

    def replace_argument(match):
        return routine_names.get(match.group(1), match.group(1))

    line = _CALL_LABEL_RE.sub(replace_call, line)
    line = _ARGUMENT_LABEL_RE.sub(replace_argument, line)
    return line


def _apply_routine_names(text, routine_names):
    lines = []
    for line in text.split("\n"):
        match = _LABEL_LINE_RE.match(line)
        if match:
            lines.append(_name_label_line(match, routine_names))
        else:
            lines.append(_name_routine_references(line, routine_names))
    return "\n".join(lines)


def _apply_names(text, names):
    glob_names = {}
    for slot, name in names.get("glob", {}).items():
        glob_names[int(slot)] = name
    if glob_names:
        text = _apply_glob_names(text, glob_names)
    routine_names = names.get("routines", {})
    if routine_names:
        text = _apply_routine_names(text, routine_names)
    return text


def _name_actor_field(match):
    base = match.group(1)
    index = int(match.group(2))
    width = match.group(4)
    is_address = match.start() > 0 and match.string[match.start() - 1] == "&"
    for vector_start, vector_name in ACTOR_VECS.items():
        if index == vector_start:
            if width and int(width) in (3, 4):
                return f"{base}.{vector_name}"
            if is_address and not width:
                return f"{base}.{vector_name}"
        if not width and vector_start <= index < vector_start + 4:
            return f"{base}.{vector_name}.{VECTOR_COMPONENTS[index - vector_start]}"
    if not width and index in ACTOR_FIELDS:
        return f"{base}.{ACTOR_FIELDS[index]}"
    return match.group(0)


def _name_stats_field(match):
    index = int(match.group(2))
    if index in STATS_FIELDS:
        return f"{match.group(1)}.{STATS_FIELDS[index]}"
    return match.group(0)


def _name_fields(text):
    for _ in range(4):
        new_text = _FIELD_RE.sub(_name_actor_field, text)
        new_text = _STATS_RE.sub(_name_stats_field, new_text)
        if new_text == text:
            break
        text = new_text
    return text


def _self_role_header_line(roles):
    return (f"; detected: glob[{roles['self']}] = self (cached actor handle, "
            f"renamed below) - arg0 of SetMotion/QueueMotion/BlendMotion/MakeAttack")


def _disasm_push(data, pos, op, block_off):
    mode = opcode_mode(op)
    base = opcode_base(op)
    if mode == PUSH_INT:
        return "push", f"#{i32(data, pos + 2)}"
    if mode == PUSH_FLOAT:
        return "push", f"#{f32_text(data[pos + 2:pos + 6])}f"
    if mode == PUSH_ADDRESS:
        if base == BASE_IMMEDIATE:
            return "lea", f"@D{pos + 2 + s16(data, pos + 2) - block_off:04X}"
        return "lea", f"[{BASE[base]}+{s16(data, pos + 2)}]"
    return "push", f"[{BASE[base]}+{s16(data, pos + 2)}] x{opcode_sub(op)}"


def _disasm_instruction(data, pos, op, block_off):
    op_class = opcode_class(op)
    sub = opcode_sub(op)
    mode = opcode_mode(op)
    base = opcode_base(op)
    if op_class == CLASS_UNARY:
        return UNARY.get(sub, f"un{sub:#x}"), ""
    if op_class == CLASS_ARITH:
        return f"{ARITH.get(sub, f'ar{sub:#x}')}.{MODESFX[mode]}", ""
    if op_class == CLASS_PUSH:
        return _disasm_push(data, pos, op, block_off)
    if op_class == CLASS_STORE:
        return "store", f"[{BASE[base]}+{s16(data, pos + 2)}]"
    if op_class in JUMP_MNEMONICS:
        target = pos + 4 + s16(data, pos + 2) * 2
        operand = f"@L{target - block_off:04X}"
        if op_class == CLASS_CALL:
            operand += f" locals={sub}"
        return JUMP_MNEMONICS[op_class], operand
    if op_class == CLASS_COMPARE:
        return f"cmp.{CMP.get(sub, f'c{sub:#x}')}.{MODESFX[mode]}", ""
    if op_class == CLASS_INDEX_ADD:
        return "idxadd", str(sub)
    if op_class == CLASS_LOAD:
        return "load", f"x{sub}"
    if op_class == CLASS_NATIVE:
        verb_name = VERBS.get(f"{base}:{sub:#04x}")
        if not verb_name:
            verb_name = "NATIVE"
        return verb_name, f"t{base} #{sub:#04x}"
    return "op", f"0x{op:04x}"


def _terminator_note(op):
    if op == OP_RETURN:
        return "  ; ---- return ----"
    if op == OP_ABORT:
        return "  ; ---- abort ----"
    if op == OP_YIELD:
        return "  ; resumes here next update"
    return ""


def disasm(data, block_off, name, size):
    start, end = _code_region(data, block_off, name, size)
    roles = detect_roles(data, block_off, name, size)
    rows = []
    targets = set()
    call_counts = {}
    pos = start
    while pos < end - 1:
        op = u16(data, pos)
        length = ilen(op)
        mnemonic, operand = _disasm_instruction(data, pos, op, block_off)
        if opcode_class(op) in JUMP_MNEMONICS:
            target = pos + 4 + s16(data, pos + 2) * 2
            targets.add(target)
            if opcode_class(op) == CLASS_CALL:
                call_counts[target] = call_counts.get(target, 0) + 1
        rows.append((pos, data[pos:pos + length], mnemonic, operand, op))
        pos += length
    header = [f"; ===== {name}  block@0x{block_off:X}  code@0x{start:X}  size=0x{size:X} ====="]
    if roles.get("self") is not None:
        header.append(_self_role_header_line(roles))
    lines = []
    for pos, raw, mnemonic, operand, op in rows:
        relative = pos - block_off
        if pos in targets:
            label_line = f"@L{relative:04X}:"
            if call_counts.get(pos):
                label_line += f"  ; sub, called {call_counts[pos]}x"
            lines.append(label_line)
        lines.append(f"      {relative:04X}  {raw.hex(' '):<17} {mnemonic:<14} {operand:<16}{_terminator_note(op)}")
    return "\n".join(header) + "\n" + _rename_roles("\n".join(lines), roles)


CMPSYM = {0: "<0", 1: "<=0", 2: "==0", 3: "!=0", 4: ">=0", 5: ">0"}
ARITHSYM = {
    0: "+",
    1: "-",
    2: "*",
    3: "/",
    4: "%",
    5: "&",
    6: "|",
    7: "^",
    8: "<<",
    9: ">>",
    10: "&&",
    11: "||",
}


def _ffmt(value):
    text = f"{value:g}"
    for character in ".en":
        if character in text:
            return text
    return text + ".0"


STUB_VERBS = {(0, 0x42)}
MAX_PARAMS = 16
MAX_RETURNS = 4
MAX_STACK = 64
MOTION_VERBS = {(0, 0x0c), (0, 0x0d), (0, 0x0e)}
ACTOR_ARG0_VERBS = {(0, 0x0c), (0, 0x0d), (0, 0x0e), (0, 0x17)}
SELF_MIN_HITS = 2
SELF_MIN_SHARE = 0.8


def _pop_or_none(stack):
    if stack:
        stack.pop()


def _simulate_glob_arguments(data, start, end):
    stack = []
    tally = {}
    pos = start
    while pos < end - 1:
        op = u16(data, pos)
        op_class = opcode_class(op)
        sub = opcode_sub(op)
        base = opcode_base(op)
        if op_class == CLASS_PUSH:
            if opcode_mode(op) in (PUSH_INT, PUSH_FLOAT):
                stack.append(None)
            elif BASE[base] == "glob":
                stack.append(("glob", s16(data, pos + 2)))
            else:
                stack.append(None)
        elif op_class == CLASS_LOAD:
            stack.append(None)
        elif op_class == CLASS_INDEX_ADD:
            _pop_or_none(stack)
            stack.append(None)
        elif op_class in (CLASS_ARITH, CLASS_COMPARE):
            _pop_or_none(stack)
            if op_class == CLASS_ARITH:
                _pop_or_none(stack)
            stack.append(None)
        elif op_class == CLASS_UNARY:
            _simulate_unary(stack, sub)
        elif op_class == CLASS_STORE:
            _pop_or_none(stack)
        elif op_class == CLASS_CALL:
            stack.clear()
        elif op_class == CLASS_NATIVE:
            _simulate_native(stack, base, sub, tally)
        pos += ilen(op)
    return tally


def _simulate_unary(stack, sub):
    if sub == UNARY_YIELD:
        stack.clear()
    elif sub == UNARY_DUP:
        if stack:
            stack.append(stack[-1])
    elif sub in (UNARY_INT_ABS, UNARY_FLOAT_ABS, UNARY_INT_NEGATE, UNARY_FLOAT_NEGATE,
                 UNARY_FLOAT_TO_INT, UNARY_FLOAT_TO_INT2, UNARY_BIT_NOT, UNARY_LOGICAL_NOT):
        _pop_or_none(stack)
        stack.append(None)
    elif sub in (UNARY_RETURN, UNARY_POP):
        _pop_or_none(stack)


def _simulate_native(stack, table, sub, tally):
    arity = ARITY.get((table, sub))
    if arity:
        argument_count = arity[0]
    else:
        argument_count = len(stack)
    arguments = []
    for _ in range(argument_count):
        if stack:
            arguments.append(stack.pop())
        else:
            arguments.append(None)
    arguments.reverse()
    if (table, sub) in ACTOR_ARG0_VERBS and arguments and arguments[0]:
        slot = arguments[0][1]
        tally[slot] = tally.get(slot, 0) + 1
    if arity and arity[1]:
        stack.append(None)


def detect_roles(data, block_off, name, size):
    start, end = _code_region(data, block_off, name, size)
    tally = _simulate_glob_arguments(data, start, end)
    if not tally:
        return {}
    best = max(tally, key=tally.get)
    total = sum(tally.values())
    if tally[best] >= SELF_MIN_HITS and tally[best] >= SELF_MIN_SHARE * total:
        return {"self": best}
    return {}


class _Structurer:
    def __init__(self, recs, entry_labels):
        self.recs = recs
        self.entry_labels = entry_labels
        self.record_index_by_label = {}
        self.jumps_to_label = {}
        self.consumed = set()
        for index, rec in enumerate(recs):
            for label in rec["labs"]:
                self.record_index_by_label[label] = index
            if rec.get("kind") in ("goto", "if"):
                self.jumps_to_label.setdefault(rec["tgt"], []).append(index)

    def single_entry(self, low, high, allowed_sources=()):
        for index in range(low, high):
            for label in self.recs[index]["labs"]:
                if label in self.entry_labels:
                    return False
                for source in self.jumps_to_label.get(label, []):
                    is_outside = source < low or source >= high
                    if is_outside and source not in allowed_sources:
                        return False
        return True

    def labels_at(self, index):
        if index < len(self.recs):
            return set(self.recs[index]["labs"])
        return set()

    def kind(self, index):
        return self.recs[index].get("kind")

    def resolve_label_index(self, label, high, follow):
        index = self.record_index_by_label.get(label)
        if label in follow and (index is None or index >= high):
            index = high
        return index

    def follow_labels(self, index, high, follow):
        labels = self.labels_at(index)
        if index == high:
            labels = labels | follow
        return labels

    def backward_jumps(self, index, high):
        sources = []
        for label in set(self.recs[index]["labs"]):
            for source in self.jumps_to_label.get(label, []):
                if index < source < high and source not in self.consumed:
                    sources.append(source)
        return sources

    def try_while(self, index, high, follow, back):
        rec = self.recs[index]
        last = max(back)
        if self.kind(last) != "goto":
            return None
        exit_label = rec["tgt"]
        exits_right_after = exit_label in self.labels_at(last + 1)
        exits_to_follow = last + 1 == high and exit_label in follow
        if not (exits_right_after or exits_to_follow):
            return None
        if not self.single_entry(index + 1, last):
            return None
        self.consumed.update({index, last})
        heads = set(rec["labs"])
        node = {"t": "while", "r": rec, "cond": rec["fc"], "body": self.build(index + 1, last, heads)}
        return node, last + 1

    def try_loop(self, index, back):
        rec = self.recs[index]
        last = max(back)
        if not self.single_entry(index + 1, last + 1):
            return None
        self.consumed.add(last)
        if self.kind(last) == "if":
            loop_type = "dowhile"
        else:
            loop_type = "forever"
        heads = set(rec["labs"])
        node = {"t": loop_type, "r": rec, "cond": self.recs[last].get("jc"), "end": self.recs[last],
                "body": self.build(index, last, heads, noloop=index)}
        return node, last + 1

    def try_if_else(self, index, then_end, high, follow):
        else_start = then_end
        if not (else_start - 1 > index and self.kind(else_start - 1) == "goto" and else_start < high):
            return None
        after_label = self.recs[else_start - 1]["tgt"]
        after = self.resolve_label_index(after_label, high, follow)
        if after is None or not else_start < after <= high:
            return None
        if not self.single_entry(index + 1, else_start - 1):
            return None
        if not self.single_entry(else_start, after, allowed_sources={index}):
            return None
        after_follow = self.follow_labels(after, high, follow)
        self.consumed.update({index, else_start - 1})
        rec = self.recs[index]
        node = {"t": "if", "r": rec, "cond": rec["fc"],
                "then": self.build(index + 1, else_start - 1, after_follow),
                "else": self.build(else_start, after, after_follow)}
        return node, after

    def try_if(self, index, high, follow):
        rec = self.recs[index]
        then_end = self.resolve_label_index(rec["tgt"], high, follow)
        if then_end is None or not index < then_end <= high:
            return None
        then_follow = self.follow_labels(then_end, high, follow)
        result = self.try_if_else(index, then_end, high, follow)
        if result:
            return result
        if not self.single_entry(index + 1, then_end):
            return None
        self.consumed.add(index)
        node = {"t": "if", "r": rec, "cond": rec["fc"], "then": self.build(index + 1, then_end, then_follow),
                "else": None}
        return node, then_end

    def is_redundant_goto(self, index, high, follow):
        rec = self.recs[index]
        if rec.get("kind") != "goto":
            return False
        if index == high - 1 and rec["tgt"] in follow:
            return True
        return rec["tgt"] in self.labels_at(index + 1)

    def try_constructs(self, index, high, follow, noloop):
        rec = self.recs[index]
        if rec["labs"] and index != noloop:
            back = self.backward_jumps(index, high)
            if rec.get("kind") == "if" and back:
                result = self.try_while(index, high, follow, back)
                if result:
                    return result
            if back:
                result = self.try_loop(index, back)
                if result:
                    return result
        if rec.get("kind") == "if":
            return self.try_if(index, high, follow)
        return None

    def build(self, low, high, follow, noloop=None):
        nodes = []
        index = low
        while index < high:
            result = self.try_constructs(index, high, follow, noloop)
            if result:
                node, index = result
                nodes.append(node)
                continue
            rec = self.recs[index]
            if self.is_redundant_goto(index, high, follow):
                self.consumed.add(index)
                if rec["labs"]:
                    nodes.append({"t": "label", "r": rec})
                index += 1
                continue
            nodes.append({"t": "stmt", "r": rec})
            index += 1
        return nodes

    def live_labels(self):
        labels = set()
        for index, rec in enumerate(self.recs):
            if rec.get("kind") in ("goto", "if") and index not in self.consumed:
                labels.add(rec["tgt"])
        return labels | set(self.entry_labels)


def _structure(recs, entry_labels):
    structurer = _Structurer(recs, entry_labels)
    tree = structurer.build(0, len(recs), set())
    return tree, structurer.live_labels()


def _bare(expression):
    if len(expression) > 1 and expression[0] == "(" and expression[-1] == ")":
        depth = 0
        for index, character in enumerate(expression):
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
            if depth == 0 and index < len(expression) - 1:
                return expression
        return expression[1:-1]
    return expression


def _rec_text(rec):
    if rec.get("kind") == "goto":
        return f"goto {rec['tgt']}"
    if rec.get("kind") == "if":
        return f"if ({_bare(rec['jc'])}) goto {rec['tgt']}"
    return rec["text"]


_CASE_RE = re.compile(r"^\(?(.+?) == (-?\d+)\)?$")
_SIMPLE_SUBJECT_RE = re.compile(r"[\w.\[\]&*]+")


def _has_kept_label(rec, keep):
    for label in rec["labs"]:
        if label in keep:
            return True
    return False


def _else_if_node(else_nodes, keep):
    if else_nodes and len(else_nodes) == 1 and else_nodes[0]["t"] == "if":
        if not _has_kept_label(else_nodes[0]["r"], keep):
            return else_nodes[0]
    return None


def _switch_arms(node, keep, min_arms=3):
    arms = []
    while True:
        match = _CASE_RE.match(_bare(node["cond"]))
        if not match or not _SIMPLE_SUBJECT_RE.fullmatch(match.group(1)):
            return None
        arms.append((match.group(1), match.group(2), node["r"], node["then"]))
        next_node = _else_if_node(node["else"], keep)
        if next_node is None:
            default = node["else"]
            break
        node = next_node
    subjects = set()
    for arm in arms:
        subjects.add(arm[0])
    if len(arms) < min_arms or len(subjects) != 1:
        return None
    return arms, default


class _Renderer:
    def __init__(self, keep, label_line):
        self.keep = keep
        self.label_line = label_line
        self.lines = []

    def labels(self, rec):
        kept = []
        for label in rec["labs"]:
            if label in self.keep:
                kept.append(label)
        if kept:
            self.lines.append(self.label_line(kept))

    def line(self, rec, text, depth):
        self.lines.append(f"      {rec['off']:04X}  {'    ' * depth}{text}")

    def brace(self, text, depth):
        self.lines.append(f"            {'    ' * depth}{text}")

    def walk(self, nodes, depth, skip_first_labels=False):
        for index, node in enumerate(nodes):
            if not (skip_first_labels and index == 0):
                self.labels(node["r"])
            self.render_node(node, depth)

    def render_node(self, node, depth):
        node_type = node["t"]
        rec = node["r"]
        if node_type == "stmt":
            self.line(rec, _rec_text(rec), depth)
        elif node_type == "if":
            switch = _switch_arms(node, self.keep)
            if switch:
                self.render_switch(rec, switch, depth)
            else:
                self.render_if(node, depth)
        elif node_type == "while":
            self.line(rec, f"while ({_bare(node['cond'])}) {{", depth)
            self.walk(node["body"], depth + 1)
            self.brace("}", depth)
        elif node_type == "forever":
            self.brace("while (1) {", depth)
            self.walk(node["body"], depth + 1, skip_first_labels=True)
            self.brace("}", depth)
        elif node_type == "dowhile":
            self.brace("do {", depth)
            self.walk(node["body"], depth + 1, skip_first_labels=True)
            self.line(node["end"], f"}} while ({_bare(node['cond'])})", depth)

    def render_switch(self, rec, switch, depth):
        arms, default = switch
        self.line(rec, f"switch ({arms[0][0]}) {{", depth)
        for subject, constant, arm_rec, body in arms:
            self.line(arm_rec, f"case {constant}:", depth)
            self.walk(body, depth + 1)
        if default:
            self.brace("default:", depth)
            self.walk(default, depth + 1)
        self.brace("}", depth)

    def render_if(self, node, depth):
        self.line(node["r"], f"if ({_bare(node['cond'])}) {{", depth)
        self.walk(node["then"], depth + 1)
        else_nodes = node["else"]
        while True:
            else_if = _else_if_node(else_nodes, self.keep)
            if else_if is None:
                break
            self.line(else_if["r"], f"}} else if ({_bare(else_if['cond'])}) {{", depth)
            self.walk(else_if["then"], depth + 1)
            else_nodes = else_if["else"]
        if else_nodes:
            self.brace("} else {", depth)
            self.walk(else_nodes, depth + 1)
        self.brace("}", depth)


def _render(tree, keep, label_line):
    renderer = _Renderer(keep, label_line)
    renderer.walk(tree, 0)
    return renderer.lines


CMPOP = {0: "<", 1: "<=", 2: "==", 3: "!=", 4: ">=", 5: ">"}
NEGOP = {"<": ">=", "<=": ">", "==": "!=", "!=": "==", ">=": "<", ">": "<="}


def _decode(data, start, end):
    ins = {}
    order = []
    pos = start
    while pos < end - 1:
        op = u16(data, pos)
        length = ilen(op)
        if length >= 4:
            argument = s16(data, pos + 2)
        else:
            argument = None
        ins[pos] = {
            "pos": pos,
            "op": op,
            "c": opcode_class(op),
            "sub": opcode_sub(op),
            "mode": opcode_mode(op),
            "base": opcode_base(op),
            "len": length,
            "arg": argument,
        }
        order.append(pos)
        pos += length
    return ins, order


def _target(i):
    return i["pos"] + 4 + i["arg"] * 2


def _unary_effect(sub):
    if sub == UNARY_YIELD:
        return 0, 0, "fall"
    if sub == UNARY_RETURN:
        return 0, 0, "ret"
    if sub == UNARY_ABORT:
        return 0, 0, "stop"
    if sub == UNARY_POP:
        return 1, 0, "fall"
    if sub == UNARY_STORE_INDIRECT:
        return 2, 0, "fall"
    if sub == UNARY_DUP:
        return 1, 2, "fall"
    if sub in (UNARY_INT_ABS, UNARY_FLOAT_ABS, UNARY_FLOAT_TO_INT, UNARY_FLOAT_TO_INT2,
               UNARY_INT_NEGATE, UNARY_FLOAT_NEGATE, UNARY_BIT_NOT, UNARY_LOGICAL_NOT):
        return 1, 1, "fall"
    return 0, 0, "fall"


def _native_effect(table, sub):
    if (table, sub) in STUB_VERBS:
        return 0, 0, "fall"
    arity = ARITY.get((table, sub))
    if not arity:
        return 0, 0, "fall"
    if arity[1]:
        return arity[0], 1, "fall"
    return arity[0], 0, "fall"


def _effect(i, sig):
    op_class = i["c"]
    if op_class == CLASS_UNARY:
        return _unary_effect(i["sub"])
    if op_class == CLASS_ARITH:
        return 2, 1, "fall"
    if op_class == CLASS_PUSH:
        return 0, 1, "fall"
    if op_class == CLASS_STORE:
        return 1, 0, "fall"
    if op_class == CLASS_JUMP:
        return 0, 0, "jump"
    if op_class in BRANCH_CLASSES:
        return 1, 0, "branch"
    if op_class == CLASS_COMPARE:
        return 1, 1, "fall"
    if op_class == CLASS_CALL:
        params, returns = sig.get(_target(i), (0, 0))
        return params, returns, "fall"
    if op_class in (CLASS_INDEX_ADD, CLASS_LOAD):
        return 1, 1, "fall"
    if op_class == CLASS_NATIVE:
        return _native_effect(i["base"], i["sub"])
    return 0, 0, "fall"


def _successors(pc, i, flow):
    if flow == "fall":
        return [pc + i["len"]]
    if flow == "jump":
        return [_target(i)]
    if flow == "branch":
        return [pc + i["len"], _target(i)]
    return []


def _analyze_function(ins, entry, sig):
    depth = {entry: 0}
    work = [entry]
    lowest = 0
    return_depths = []
    mismatches = 0
    while work:
        pc = work.pop()
        i = ins.get(pc)
        if i is None:
            continue
        current = depth[pc]
        pops, pushes, flow = _effect(i, sig)
        lowest = min(lowest, current - pops)
        next_depth = current - pops + pushes
        if flow == "ret":
            return_depths.append(current)
        for successor in _successors(pc, i, flow):
            if successor not in ins:
                continue
            if successor in depth:
                if depth[successor] != next_depth:
                    mismatches += 1
                continue
            depth[successor] = next_depth
            work.append(successor)
    return {"depth": depth, "min": lowest, "rets": return_depths, "bad": mismatches}


def _analyze(ins, order, entries, sig):
    result = {}
    for entry in entries:
        result[entry] = _analyze_function(ins, entry, sig)
    return result


def _is_scaffolding(i):
    if i["c"] == CLASS_JUMP:
        return True
    return i["c"] == CLASS_UNARY and i["sub"] in (UNARY_YIELD, UNARY_RETURN, UNARY_ABORT)


def _ends_flow(i):
    if i["c"] == CLASS_JUMP:
        return True
    return i["c"] == CLASS_UNARY and i["sub"] in (UNARY_RETURN, UNARY_ABORT)


def _orphans(ins, order, entries, sig):
    reached = set()
    for analysis in _analyze(ins, order, entries, sig).values():
        reached |= set(analysis["depth"])
    found = []
    previous = None
    for pc in order:
        if pc not in reached and previous is not None and _ends_flow(ins[previous]):
            if _is_scaffolding(ins[pc]):
                reached.add(pc)
            else:
                found.append(pc)
                reached |= set(_analyze(ins, order, [pc], sig)[pc]["depth"])
        previous = pc
    return found


def _most_common_return_depth(return_depths):
    return max(set(return_depths), key=return_depths.count)


def _signature_of(analysis):
    params = -analysis["min"]
    if analysis["rets"]:
        returns = max(_most_common_return_depth(analysis["rets"]) + params, 0)
    else:
        returns = 0
    return min(params, MAX_PARAMS), min(returns, MAX_RETURNS)


def _signatures(ins, order, start):
    call_targets = set()
    for i in ins.values():
        if i["c"] == CLASS_CALL and _target(i) in ins:
            call_targets.add(_target(i))
    entries = [start]
    for target in sorted(call_targets):
        if target != start:
            entries.append(target)
    for orphan in _orphans(ins, order, entries, {}):
        if orphan not in entries:
            entries.append(orphan)
    calls = entries[1:]
    sig = {}
    for _ in range(12):
        analyses = _analyze(ins, order, entries, sig)
        new_sig = {}
        for entry in entries:
            new_sig[entry] = _signature_of(analyses[entry])
        if new_sig == sig:
            break
        sig = new_sig
    return sig, analyses, calls


_BASE_ADDR = re.compile(r"^&(loc|glob|heap)\[(-?\d+)\]$")
_GEN_ADDR = re.compile(r"^&(.+)\[(-?\d+)\]$")
_SIMPLE_EXPRESSION_RE = re.compile(r"[\w.&]+(\[[^\[\]]*\])*")
_SPILL_FREE_RE = re.compile(r"-?[\w.&]+(\[[^\[\]]*\])*")
_SIDE_EFFECT_RE = re.compile(r"[A-Za-z_]\w*\??\(|call @")
_THREAD_OFFSET_RE = re.compile(r"\d{2,6}")


def _wrap(expression):
    if _SIMPLE_EXPRESSION_RE.fullmatch(expression):
        return expression
    return f"({expression})"


def _motion_note(motion_dict, argv):
    try:
        motion_id = int(argv[1]) & 0xFFFF
    except ValueError:
        return ""
    anim_index = motion_dict.get(motion_id)
    if anim_index is not None:
        return f"  ; -> anim{anim_index:04d}"
    return f"  ; motion_id {motion_id} (no anim)"


class _Folder:
    def __init__(self, data, block_off, start, ins, sig, calls, motion_dict):
        self.data = data
        self.block_off = block_off
        self.start = start
        self.ins = ins
        self.sig = sig
        self.motion_dict = motion_dict
        self.targets = set(calls)
        for i in ins.values():
            if i["c"] in JUMP_MNEMONICS:
                self.targets.add(_target(i))
        self.entry_offsets = set()
        for entry in sig:
            if entry != start:
                self.entry_offsets.add(self.rel(entry))
        self.stack = []
        self.recs = []
        self.pending_labels = []
        self.live = True
        self.carried_stacks = {}
        self.subtractions = {}
        self.comparisons = {}
        self.short_circuits = []
        self.temp_count = 0
        self.thread_refs = {}
        self.dead_start = None
        self.dead_is_real = False

    def rel(self, pos):
        return pos - self.block_off

    def label(self, pos):
        return f"@L{self.rel(pos):04X}"

    def emit(self, pos, text, **extra):
        rec = {"off": self.rel(pos), "labs": self.pending_labels, "text": text}
        rec.update(extra)
        self.recs.append(rec)
        self.pending_labels = []

    def remember_stack_at(self, target):
        self.carried_stacks.setdefault(target, []).append(list(self.stack))

    def negate(self, expression):
        if expression in self.comparisons:
            left, operator, right = self.comparisons[expression]
            negated = f"({left} {NEGOP[operator]} {right})"
            self.comparisons[negated] = (left, NEGOP[operator], right)
            return negated
        if expression.startswith("!") and not expression.startswith("!="):
            return expression[1:]
        return f"!{_wrap(expression)}"

    def spill(self, pc, expression):
        if _SPILL_FREE_RE.fullmatch(expression):
            return expression
        temp = f"t{self.temp_count}"
        self.temp_count += 1
        self.emit(pc, f"{temp} = {expression}")
        return temp

    def pop(self):
        if self.stack:
            return self.stack.pop()
        return "?"

    def pop_many(self, count):
        values = []
        for _ in range(count):
            values.append(self.pop())
        values.reverse()
        return values

    def link_entries(self, pc, argv):
        linked = []
        for argument in argv:
            if _THREAD_OFFSET_RE.fullmatch(argument) and 2 * int(argument) in self.entry_offsets:
                entry_offset = 2 * int(argument)
                self.thread_refs.setdefault(entry_offset, []).append(self.rel(pc))
                linked.append(f"@L{entry_offset:04X}")
            else:
                linked.append(argument)
        return linked

    def variable(self, i, width=1):
        base = BASE[i["base"]]
        if width == 1:
            return f"{base}[{i['arg']}]"
        return f"{base}[{i['arg']}:{width}]"

    def address(self, i):
        if i["base"] == BASE_IMMEDIATE:
            return f"&data_{self.rel(i['pos'] + 2 + i['arg']):04X}"
        return f"&{BASE[i['base']]}[{i['arg']}]"

    def pointer_add(self, pointer, count):
        match = _BASE_ADDR.match(pointer)
        if match:
            return f"&{match.group(1)}[{int(match.group(2)) + WORD_SIZE * count}]"
        match = _GEN_ADDR.match(pointer)
        if match and not pointer.startswith("&("):
            return f"&{match.group(1)}[{int(match.group(2)) + count}]"
        if pointer.startswith("&"):
            if count:
                return f"&{pointer[1:]}[{count}]"
            return pointer
        return f"&{_wrap(pointer)}[{count}]"

    def dereference(self, pointer, width):
        if pointer.startswith("&"):
            text = pointer[1:]
        else:
            text = f"*{_wrap(pointer)}"
        if width == 1:
            return text
        return f"{text}:{width}"

    def flush_dead(self, upto):
        if self.dead_start is not None and self.dead_is_real:
            self.emit(self.dead_start, f"; unreachable bytes 0x{self.rel(self.dead_start):04X}-0x"
                                       f"{self.rel(upto) - 1:04X} (never executed: data or dead code)")
        self.dead_start = None
        self.dead_is_real = False

    def mark_dead(self, pc):
        if self.dead_start is None:
            self.dead_start = pc
        if not _is_scaffolding(self.ins[pc]):
            self.dead_is_real = True
        self.live = False

    def spill_long_expressions(self, pc):
        if len(self.stack) > MAX_STACK:
            self.stack = self.stack[-MAX_STACK:]
        for index, expression in enumerate(self.stack):
            if len(expression) > SPILL_LENGTH:
                self.stack[index] = self.spill(pc, expression)

    def enter_function(self, pc):
        params = self.sig[pc][0]
        self.stack = []
        for index in range(params):
            self.stack.append(f"a{index}")
        self.live = True
        if pc == self.start and params:
            self.emit(pc, f"; block entry receives {params} value(s) from the engine: {', '.join(self.stack)}")

    def resync_stack(self, pc, expected_depth):
        depth = max(expected_depth, 0)
        carried = []
        for stack in self.carried_stacks.get(pc, []):
            if len(stack) == depth:
                carried.append(stack)
        all_agree = True
        for stack in carried:
            if stack != carried[0]:
                all_agree = False
        if not self.live and carried and all_agree:
            self.stack = list(carried[0])
        elif not self.live:
            self.stack = []
        if len(self.stack) < depth:
            padding = []
            for index in range(depth - len(self.stack)):
                padding.append(f"s{index}")
            self.stack = padding + self.stack
        elif len(self.stack) > depth:
            self.stack = self.stack[len(self.stack) - depth:]
        self.live = True

    def prepare_stack(self, pc, depth_by_pc):
        if pc in self.sig:
            self.enter_function(pc)
        elif pc in depth_by_pc and (not self.live or len(self.stack) != depth_by_pc[pc]):
            self.resync_stack(pc, depth_by_pc[pc])
        elif not self.live:
            self.stack = []
            self.live = True

    def fold_push(self, pc, i):
        mode = i["mode"]
        if mode == PUSH_INT:
            self.stack.append(str(i32(self.data, pc + 2)))
        elif mode == PUSH_FLOAT:
            self.stack.append(_ffmt(f32(self.data, pc + 2)))
        elif mode == PUSH_ADDRESS:
            self.stack.append(self.address(i))
        else:
            self.stack.append(self.variable(i, i["sub"]))

    def closes_short_circuit(self, pc, i):
        sub = i["sub"]
        if sub not in (ARITH_LOGICAL_AND, ARITH_LOGICAL_OR) or not self.short_circuits:
            return False
        rec_index, target, branch_class = self.short_circuits[-1]
        if sub == ARITH_LOGICAL_AND:
            expected_branch = CLASS_BRANCH_IF_ZERO
        else:
            expected_branch = CLASS_BRANCH_IF_NONZERO
        return target == pc + i["len"] and rec_index == len(self.recs) - 1 and branch_class == expected_branch

    def fold_arith(self, pc, i):
        right = self.pop()
        left = self.pop()
        sub = i["sub"]
        expression = f"({left} {ARITHSYM.get(sub, '?')} {right})"
        if sub == ARITH_SUB:
            self.subtractions[expression] = (left, right)
        if self.closes_short_circuit(pc, i):
            skipped = self.recs.pop()
            self.pending_labels = skipped["labs"] + self.pending_labels
            self.short_circuits.pop()
        self.stack.append(expression)

    def fold_compare(self, i):
        value = self.pop()
        operator = CMPOP.get(i["sub"], "?")
        left, right = self.subtractions.get(value, (value, "0"))
        expression = f"({left} {operator} {right})"
        self.comparisons[expression] = (left, operator, right)
        self.stack.append(expression)

    def fold_unary(self, pc, i):
        sub = i["sub"]
        if sub == UNARY_YIELD:
            self.emit(pc, "yield")
        elif sub == UNARY_RETURN:
            if self.stack:
                self.emit(pc, f"return {', '.join(self.stack)}")
            else:
                self.emit(pc, "return")
            self.stack = []
            self.live = False
        elif sub == UNARY_ABORT:
            self.emit(pc, "abort")
            self.live = False
        elif sub == UNARY_POP:
            value = self.pop()
            if _SIDE_EFFECT_RE.search(value):
                self.emit(pc, value)
        elif sub == UNARY_STORE_INDIRECT:
            value = self.pop()
            pointer = self.pop()
            self.emit(pc, f"{self.dereference(pointer, 1)} = {value}")
        elif sub == UNARY_DUP:
            self.fold_dup(pc, i)
        elif sub in (UNARY_INT_ABS, UNARY_FLOAT_ABS):
            self.stack.append(f"abs({self.pop()})")
        elif sub in (UNARY_INT_NEGATE, UNARY_FLOAT_NEGATE):
            self.stack.append(f"-{_wrap(self.pop())}")
        elif sub in (UNARY_FLOAT_TO_INT, UNARY_FLOAT_TO_INT2):
            self.stack.append(f"int({self.pop()})")
        elif sub == UNARY_BIT_NOT:
            self.stack.append(f"~{_wrap(self.pop())}")
        elif sub == UNARY_LOGICAL_NOT:
            self.stack.append(f"!{_wrap(self.pop())}")

    def fold_dup(self, pc, i):
        next_instruction = self.ins.get(pc + i["len"])
        feeds_branch = next_instruction and next_instruction["c"] in BRANCH_CLASSES
        if self.stack and not feeds_branch:
            self.stack[-1] = self.spill(pc, self.stack[-1])
        if self.stack:
            self.stack.append(self.stack[-1])
        else:
            self.stack.append("?")

    def fold_jump(self, pc, i):
        self.remember_stack_at(_target(i))
        label = self.label(_target(i))
        self.emit(pc, f"goto {label}", kind="goto", tgt=label)
        self.live = False

    def previous_is_dup(self, pc):
        previous = self.ins.get(pc - 2)
        if previous is None:
            return False
        return previous["c"] == CLASS_UNARY and previous["sub"] == UNARY_DUP

    def fold_branch(self, pc, i):
        condition = self.pop()
        self.remember_stack_at(_target(i))
        label = self.label(_target(i))
        if condition in self.subtractions:
            left, right = self.subtractions[condition]
            condition = f"({left} != {right})"
            self.comparisons[condition] = (left, "!=", right)
        if i["c"] == CLASS_BRANCH_IF_ZERO:
            jump_condition = self.negate(condition)
            fall_condition = condition
        else:
            jump_condition = condition
            fall_condition = self.negate(condition)
        self.emit(pc, f"if ({jump_condition}) goto {label}", kind="if", tgt=label, jc=jump_condition,
                  fc=fall_condition)
        if self.previous_is_dup(pc):
            self.short_circuits.append((len(self.recs) - 1, _target(i), i["c"]))

    def fold_call(self, pc, i):
        target = _target(i)
        params, returns = self.sig.get(target, (0, 0))
        argv = self.link_entries(pc, self.pop_many(params))
        call = f"call {self.label(target)}({', '.join(argv)})"
        if returns == 1:
            self.stack.append(call)
        elif returns > 1:
            temp = self.spill(pc, call)
            for index in range(returns):
                self.stack.append(f"{temp}[{index}]")
        else:
            self.emit(pc, call)

    def fold_native(self, pc, i):
        table = i["base"]
        sub = i["sub"]
        verb_name = VERBS.get(f"{table}:{sub:#04x}")
        if not verb_name:
            verb_name = f"NATIVE_t{table}_{sub:#x}"
        arity = ARITY.get((table, sub))
        if (table, sub) in STUB_VERBS:
            self.emit(pc, f"{verb_name}()")
            return
        if arity is None:
            arguments = ", ".join(self.stack)
            self.stack = []
            self.emit(pc, f"{verb_name}({arguments})")
            return
        argument_count, has_return = arity
        argv = self.link_entries(pc, self.pop_many(argument_count))
        call = f"{verb_name}({', '.join(argv)})"
        if has_return:
            self.stack.append(call)
            return
        note = ""
        if self.motion_dict is not None and (table, sub) in MOTION_VERBS and len(argv) >= 2:
            note = _motion_note(self.motion_dict, argv)
        self.emit(pc, call + note)

    def fold_instruction(self, pc, i):
        op_class = i["c"]
        if op_class == CLASS_PUSH:
            self.fold_push(pc, i)
        elif op_class == CLASS_LOAD:
            self.stack.append(self.dereference(self.pop(), i["sub"]))
        elif op_class == CLASS_INDEX_ADD:
            self.stack.append(self.pointer_add(self.pop(), i["sub"]))
        elif op_class == CLASS_ARITH:
            self.fold_arith(pc, i)
        elif op_class == CLASS_COMPARE:
            self.fold_compare(i)
        elif op_class == CLASS_UNARY:
            self.fold_unary(pc, i)
        elif op_class == CLASS_STORE:
            value = self.pop()
            self.emit(pc, f"{self.variable(i)} = {value}")
        elif op_class == CLASS_JUMP:
            self.fold_jump(pc, i)
        elif op_class in BRANCH_CLASSES:
            self.fold_branch(pc, i)
        elif op_class == CLASS_CALL:
            self.fold_call(pc, i)
        elif op_class == CLASS_NATIVE:
            self.fold_native(pc, i)

    def run(self, order, depth_by_pc, end):
        for pc in order:
            if pc not in depth_by_pc and pc not in self.targets:
                self.mark_dead(pc)
                continue
            self.flush_dead(pc)
            self.spill_long_expressions(pc)
            if pc in self.targets:
                self.pending_labels = self.pending_labels + [self.label(pc)]
            self.prepare_stack(pc, depth_by_pc)
            self.fold_instruction(pc, self.ins[pc])
        if self.dead_start is not None:
            self.flush_dead(end)


def _depth_by_pc(start, calls, sig, analyses):
    depth_by_pc = {}
    for entry in [start] + calls:
        params = sig.get(entry, (0, 0))[0]
        for pc, depth in analyses[entry]["depth"].items():
            if pc not in depth_by_pc:
                depth_by_pc[pc] = depth + params
    return depth_by_pc


def _call_counts(ins):
    counts = {}
    for i in ins.values():
        if i["c"] == CLASS_CALL:
            counts[_target(i)] = counts.get(_target(i), 0) + 1
    return counts


class _LabelLineFormatter:
    def __init__(self, block_off, start, sig, call_counts, thread_refs):
        self.block_off = block_off
        self.start = start
        self.sig = sig
        self.call_counts = call_counts
        self.thread_refs = thread_refs

    def usage(self, pos):
        if pos in self.call_counts:
            return f"called {self.call_counts[pos]}x"
        refs = self.thread_refs.get(pos - self.block_off)
        if refs:
            sites = []
            for site in sorted(set(refs)):
                sites.append(f"0x{site:04X}")
            return f"thread entry, started from {', '.join(sites)}"
        return "not called in this block"

    def __call__(self, labels):
        notes = []
        for label in labels:
            pos = int(label[2:], 16) + self.block_off
            if pos not in self.sig or pos == self.start:
                continue
            params, returns = self.sig.get(pos, (0, 0))
            param_names = []
            for index in range(params):
                param_names.append(f"a{index}")
            note = f"sub({', '.join(param_names)})"
            if returns:
                note += " -> " + str(returns)
            notes.append(f"{note}, {self.usage(pos)}")
        line = f"{','.join(labels)}:"
        if notes:
            line += "  ; " + "; ".join(notes)
        return line


def fold(data, block_off, name, size, motion_dict=None):
    start, end = _code_region(data, block_off, name, size)
    roles = detect_roles(data, block_off, name, size)
    ins, order = _decode(data, start, end)
    sig, analyses, calls = _signatures(ins, order, start)
    folder = _Folder(data, block_off, start, ins, sig, calls, motion_dict)
    folder.run(order, _depth_by_pc(start, calls, sig, analyses), end)
    entry_labels = set()
    for entry in sig:
        if entry != start:
            entry_labels.add(f"@L{entry - block_off:04X}")
    tree, keep = _structure(folder.recs, entry_labels)
    header = [f"; ===== {name}  (folded)  block@0x{block_off:X}  code@0x{start:X} ====="]
    if roles.get("self") is not None:
        header.append(_self_role_header_line(roles))
    label_line = _LabelLineFormatter(block_off, start, sig, _call_counts(ins), folder.thread_refs)
    lines = _render(tree, keep, label_line)
    text = _rename_roles("\n".join(lines), roles)
    if roles.get("self") is not None:
        text = _name_fields(text)
    names = load_names(name)
    if names:
        text = _apply_names(text, names)
        header.append(f"; names: bd/data/names/{name}.json")
    return "\n".join(header) + "\n" + text


FOLD_FLAGS = ("fold", "--fold", "-f")


def _print_block_table(blocks):
    print(f"{'idx':>3}  {'name':<18} {'block':>12} {'size':>7}")
    for index, (block_off, name, size) in enumerate(blocks):
        print(f"{index:>3}  {name:<18} 0x{block_off:08X} 0x{size:04X}")


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        return
    with open(sys.argv[1], "rb") as file:
        data = file.read()
    blocks = find_blocks(data)
    if not blocks:
        print("No .bd blocks found.")
        return
    if len(sys.argv) == 2:
        _print_block_table(blocks)
        return
    args = sys.argv[2:]
    folded = False
    selectors = []
    for arg in args:
        if arg in FOLD_FLAGS:
            folded = True
        else:
            selectors.append(arg)
    if selectors:
        selector = selectors[0]
    else:
        selector = "all"
    motion_dict = None
    if folded:
        motion_dict = _sibling_motion_dict(sys.argv[1])
    for index, (block_off, name, size) in enumerate(blocks):
        if selector == "all" or selector == str(index) or selector in name:
            if folded:
                print(fold(data, block_off, name, size, motion_dict))
            else:
                print(disasm(data, block_off, name, size))
            print()


if __name__ == "__main__":
    main()
