"""Build one .bds file into an enemy .mdls: compile each `bd NAME code 0x... { }` block and write
its code over that block's code region in a copy of the original file.

Blocks not in the .bds keep their original bytes. A block's new code must fit in its original
code region plus the zero padding after it (up to the next section or block); shorter code is
zero-padded. The .mdls layout itself is never moved.

Threads and event handlers are started with a pushed number N meaning the function at block
offset N*2 (StartThread, SetEventHandler, ...). Those are plain numbers in the text, so when an
edit moves a function whose old offset/2 is pushed somewhere, a warning names it.
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lang  # noqa: E402

bd = lang.bd


def region(data, block_off, name, size):
    """(code start, code end) of a block, as the decompiler sees it."""
    end = min(block_off + 4 + size, len(data))
    start = bd.code_start(data, block_off, name, end)
    return start, bd.extend_end(data, block_off, start, end)


def boundaries(data):
    """Offsets nothing may grow past: the .mdls section table (u32 count, then count offsets)
    and every .bd block header."""
    out = {len(data)} | {b for b, n, s in bd.find_blocks(data)}
    count = struct.unpack_from('<I', data, 0)[0]
    if 0 < count < 64 and 4 + 4 * count <= len(data):
        out |= set(struct.unpack_from(f'<{count}I', data, 4))
    return out


def room_end(data, end, limits):
    """End of the code region plus the zero padding after it (up to the next section/block)."""
    stop = min((x for x in limits if x >= end), default=len(data))
    pad = end
    while pad < stop and data[pad] == 0:
        pad += 1
    return pad & ~1 if pad < stop else stop


def build_file(bds_path, orig_path, out_path):
    text = Path(bds_path).read_text(encoding='utf-8')
    data = bytearray(Path(orig_path).read_bytes())
    blocks = {n: (b, s) for b, n, s in bd.find_blocks(bytes(data))}
    limits = boundaries(bytes(data))
    parts = lang.split_blocks(text)
    if not parts:
        raise ValueError(f'{Path(bds_path).name}: no `bd NAME code 0x... {{ }}` blocks')
    for name, btext in parts.items():
        if name not in blocks:
            raise ValueError(f'{name}: no such .bd block in {Path(orig_path).name}')
        b, s = blocks[name]
        start, end = region(bytes(data), b, name, s)
        end = room_end(bytes(data), end, limits)
        code_rel, code = lang.compile_block(btext)
        if code_rel != start - b:
            raise ValueError(f'{name}: text says code 0x{code_rel:04X}, the file has 0x{start - b:04X}')
        room = end - start
        if len(code) > room:
            raise ValueError(f'{name}: compiled code is {len(code)} bytes, only {room} available '
                             f'(the original code plus the zero padding after it)')
        _warn_moved(name, btext)
        data[start:start + len(code)] = code
        data[start + len(code):end] = bytes(room - len(code))
        print(f'{name}: {len(code)} of {room} bytes')
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(bytes(data))


def _warn_moved(name, btext):
    _, spans = lang.compile_block(btext, with_spans=True)
    heads = [ln for ln in btext.split('\n') if lang.FUNC_RE.match(ln) or ln.startswith('    data {')]
    pushed = {int(x, 0) for x in re.findall(r'(?<![\w.\[])(0x[0-9A-Fa-f]+|\d+)(?![\w.\]])', btext)}
    risky = []
    for n, ln in enumerate(heads):
        m = re.search(r'// @L([0-9A-F]{4})', ln)
        if not m or n >= len(spans):
            continue
        old, new = int(m.group(1), 16), spans[n][0]
        if old != new and old % 2 == 0 and old // 2 in pushed:
            risky.append(f'{lang.FUNC_RE.match(ln).group(1)} (0x{old:04X} -> 0x{new:04X})')
    if risky:
        print(f'  warning: {name}: moved functions whose old offset/2 appears as a number '
              f'(thread/handler starts?): {", ".join(risky)} - update those numbers by hand')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('bds'); ap.add_argument('original'); ap.add_argument('out')
    a = ap.parse_args()
    try:
        build_file(a.bds, a.original, a.out)
    except (ValueError, SyntaxError, lang.PartError) as e:
        sys.exit(f'error: {e}')
