"""Build one .evs file into a game script: compile each `kgr N { }` block, repack the streams into
the original binary (like evdl_tool's asm command), and write the result.

New message string literals are appended to the set's .binl: the copy next to the output if one
exists (earlier builds / hand edits), else the game's; changed .binl files are written next to the
output.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import evdl_tool as et
import lang
import msgstore


def repack(orig, file_type, streams):
    kgrs = et.parse_ard(orig) if file_type == 'ard' else et.parse_evdl(orig)
    streams = list(streams)
    while len(streams) < len(kgrs):
        streams.append(bytes(kgrs[len(streams)]['stream']))
    return et.repack_ard(orig, kgrs, streams) if file_type == 'ard' else et.repack_evdl(orig, kgrs, streams)


def build_file(evs_path, orig_path, out_path):
    """Returns the list of .binl files written (new message strings)."""
    evs_path, orig_path, out_path = Path(evs_path), Path(orig_path), Path(out_path)
    file_type = 'ard' if orig_path.suffix.lower() == '.ard' else 'evdl'
    store = None
    if file_type != 'ard':
        store = msgstore.store_for(out_path, [out_path.parent, orig_path.parent], out_path.parent)
    blocks = lang.compile_file_text(evs_path.read_text(encoding='utf-8'), store)
    if not blocks:
        raise ValueError(f'{evs_path.name}: no `kgr N {{ }}` blocks')
    streams = [blocks[i] for i in range(max(blocks) + 1)]
    out = repack(orig_path.read_bytes(), file_type, streams)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(out)
    return [str(store.targets[lang_]) for lang_ in store.save()] if store else []


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('evs'); ap.add_argument('original'); ap.add_argument('out')
    a = ap.parse_args()
    print(build_file(a.evs, a.original, a.out))
