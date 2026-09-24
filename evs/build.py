"""Build one .evs file into a game script: compile each `kgr N { }` block, repack the streams into
the original binary (like evdl_tool's asm command), and write the result.

New message string literals are appended to the set's .binl: the copy next to the output if one
exists (earlier builds / hand edits), else the game's; changed .binl files are written next to the
output.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import evdl_tool as et
import lang
import msgstore


STUB_KGR = struct.pack('<I', 8) + et.enc_instr(5, 0x10) * 8  # one thread of 8 empty entries, as in vanilla set files


def set_file_header(data):
    """(h0, h1, kgr count, string offset) for a set .evdl whose header is followed directly by its
    offset table (h0 + h1 other sections, then the KGRs), else None."""
    if len(data) < 16:
        return None
    h0, h1, n, so = struct.unpack_from('<4i', data, 0)
    if min(h0, h1) < 0 or n < 1 or so != 16 + 4 * (h0 + h1 + n):
        return None
    return h0, h1, n, so


def grow_set_file(data, extra):
    """Append KGR streams `extra` (indices n, n+1, ...) to a set .evdl: grow the offset table,
    shift everything after it (the string data is position-independent), pad to 0x80."""
    h0, h1, n, so = set_file_header(data)
    delta = 4 * len(extra)
    table = [o + delta for o in struct.unpack_from(f'<{h0 + h1 + n}i', data, 16)]
    body = bytearray(data[so:])
    for s in extra:
        table.append(so + delta + len(body))
        body += b'KGR\0' + struct.pack('<II', 1, 1) + bytes([et.count_scripts(s)]) + s
    body += bytes(-(so + delta + len(body)) % 0x80)
    return struct.pack('<4i', h0, h1, n + len(extra), so + delta) + struct.pack(f'<{len(table)}i', *table) + bytes(body)


def repack(orig, file_type, streams):
    """streams: {kgr index: stream}; missing indices keep the original KGR. For a set .evdl,
    indices past the file's KGR count are appended, with empty stub KGRs filling any gap."""
    kgrs = et.parse_ard(orig) if file_type == 'ard' else et.parse_evdl(orig)
    have = [streams.get(i, bytes(k['stream'])) for i, k in enumerate(kgrs)]
    out = et.repack_ard(orig, kgrs, have) if file_type == 'ard' else et.repack_evdl(orig, kgrs, have)
    top = max(streams) + 1
    if top <= len(kgrs):
        return out
    if file_type == 'ard' or set_file_header(out) is None or set_file_header(out)[2] != len(kgrs):
        raise ValueError(f'kgr {top - 1}: cannot add KGRs to this file (has {len(kgrs)})')
    return grow_set_file(out, [streams.get(i, STUB_KGR) for i in range(len(kgrs), top)])


def build_file(evs_path, orig_path, out_path):
    """Returns the list of .binl files written (new message strings)."""
    evs_path, orig_path, out_path = Path(evs_path), Path(orig_path), Path(out_path)
    file_type = 'ard' if orig_path.suffix.lower() == '.ard' else 'evdl'
    store = None
    if file_type != 'ard':
        store = msgstore.store_for(out_path, [out_path.parent, orig_path.parent], out_path.parent)
    lang.COMPILE_WARNINGS.clear()
    blocks = lang.compile_file_text(evs_path.read_text(encoding='utf-8'), store)
    for w in lang.COMPILE_WARNINGS:
        print(f'  warning: {evs_path.name}: {w}')
    if not blocks:
        raise ValueError(f'{evs_path.name}: no `kgr N {{ }}` blocks')
    out = repack(orig_path.read_bytes(), file_type, blocks)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(out)
    return [str(store.targets[lang_]) for lang_ in store.save()] if store else []


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('evs'); ap.add_argument('original'); ap.add_argument('out')
    a = ap.parse_args()
    print(build_file(a.evs, a.original, a.out))
