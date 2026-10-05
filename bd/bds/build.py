"""Build one .bds file into an enemy .mdls: compile each `bd NAME code 0x... { }` block and write its
code over that block's code region in a copy of the original file.
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lang

bd = lang.bd

HELP = 'Build a .bds file into a copy of an enemy .mdls.'

MAX_SECTIONS = 64
NUMBER_IN_TEXT_RE = re.compile(r'(?<![\w.\[])(0x[0-9A-Fa-f]+|\d+)(?![\w.\]])')
OLD_OFFSET_RE = re.compile(r'// @L([0-9A-F]{4})')


def section_offsets(data):
    count = struct.unpack_from('<I', data, 0)[0]
    if 0 < count < MAX_SECTIONS and 4 + 4 * count <= len(data):
        return set(struct.unpack_from(f'<{count}I', data, 4))
    return set()


def boundaries(data):
    limits = {len(data)}
    for block_off, _, _ in bd.find_blocks(data):
        limits.add(block_off)
    return limits | section_offsets(data)


def round_down_to_even(n):
    return n - n % 2


def room_end(data, end, limits):
    later_limits = [limit for limit in limits if limit >= end]
    if later_limits:
        stop = min(later_limits)
    else:
        stop = len(data)
    position = end
    while position < stop and data[position] == 0:
        position += 1
    if position < stop:
        return round_down_to_even(position)
    return stop


def build_block(data, name, block_text, block_off, size, limits):
    start, end = lang.code_region(bytes(data), block_off, name, size)
    end = room_end(bytes(data), end, limits)
    code_offset, code = lang.compile_block(block_text)
    if code_offset != start - block_off:
        raise ValueError(f'{name}: text says code 0x{code_offset:04X}, the file has 0x{start - block_off:04X}')
    room = end - start
    if len(code) > room:
        raise ValueError(f'{name}: compiled code is {len(code)} bytes, only {room} available '
                         f'(the original code plus the zero padding after it)')
    warn_moved(name, block_text)
    data[start:start + len(code)] = code
    data[start + len(code):end] = bytes(room - len(code))
    print(f'{name}: {len(code)} of {room} bytes')


def build_file(bds_path, orig_path, out_path):
    text = Path(bds_path).read_text(encoding='utf-8')
    data = bytearray(Path(orig_path).read_bytes())
    blocks = {name: (block_off, size) for block_off, name, size in bd.find_blocks(bytes(data))}
    limits = boundaries(bytes(data))
    block_texts = lang.split_blocks(text)
    if not block_texts:
        raise ValueError(f'{Path(bds_path).name}: no `bd NAME code 0x... {{ }}` blocks')
    for name, block_text in block_texts.items():
        if name not in blocks:
            raise ValueError(f'{name}: no such .bd block in {Path(orig_path).name}')
        block_off, size = blocks[name]
        build_block(data, name, block_text, block_off, size, limits)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(bytes(data))


def warn_moved(name, block_text):
    _, spans = lang.compile_block(block_text, with_spans=True)
    part_headers = []
    for line in block_text.split('\n'):
        if lang.FUNC_RE.match(line) or line.startswith('    data {'):
            part_headers.append(line)
    pushed_numbers = {int(number, 0) for number in NUMBER_IN_TEXT_RE.findall(block_text)}
    moved = []
    for n, header in enumerate(part_headers):
        old_offset_match = OLD_OFFSET_RE.search(header)
        if not old_offset_match or n >= len(spans):
            continue
        old_offset = int(old_offset_match.group(1), 16)
        new_offset = spans[n][0]
        if old_offset != new_offset and old_offset % 2 == 0 and old_offset // 2 in pushed_numbers:
            function_name = lang.FUNC_RE.match(header).group(1)
            moved.append(f'{function_name} (0x{old_offset:04X} -> 0x{new_offset:04X})')
    if moved:
        print(f'  warning: {name}: moved functions whose old offset/2 appears as a number '
              f'(thread/handler starts?): {", ".join(moved)} - update those numbers by hand')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=HELP, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('bds'); ap.add_argument('original'); ap.add_argument('out')
    a = ap.parse_args()
    try:
        build_file(a.bds, a.original, a.out)
    except (ValueError, SyntaxError, lang.PartError) as e:
        sys.exit(f'error: {e}')
