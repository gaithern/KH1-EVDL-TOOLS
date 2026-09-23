"""Convert a repo's asm/**/*.asm to EVS and check the EVS rebuilds the repo's mod/ files byte for byte.

Mirrors build_mod.py: asm/<rel>.asm assembles into <game_data>/<rel> and lands in mod/<rel>.
For each file: asm -> KGR streams (evdl_tool) -> EVS (written to evs/<rel>.evs) -> compile ->
repack into the vanilla binary -> compare with mod/<rel>.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import evdl_tool as et
import entities as ent
import lang
from corpus import GAME_DATA


def asm_streams(text):
    streams, errors = [], []
    for i, sec in enumerate(et.split_asm_text(text)):
        stream, errs = et.asm_sec(et.parse_asm_sec(sec), f'KGR[{i}]')
        streams.append(stream)
        errors += errs
    return streams, errors


def repack(orig, file_type, streams):
    kgrs = et.parse_ard(orig) if file_type == 'ard' else et.parse_evdl(orig)
    streams = list(streams)
    while len(streams) < len(kgrs):
        streams.append(bytes(kgrs[len(streams)]['stream']))
    out = et.repack_ard(orig, kgrs, streams) if file_type == 'ard' else et.repack_evdl(orig, kgrs, streams)
    return out, kgrs


def convert(repo, out_dir):
    asm_dir, mod_dir = repo / 'asm', repo / 'mod'
    rows = []
    for asm_path in sorted(asm_dir.rglob('*.asm')):
        rel = asm_path.relative_to(asm_dir).with_suffix('')
        orig_path, mod_path = GAME_DATA / rel, mod_dir / rel
        row = {'file': str(rel).replace('\\', '/')}
        rows.append(row)
        try:
            text = asm_path.read_text(encoding='utf-8')
            file_type = et.parse_file_header(text)['file_type'] or 'evdl'
            streams, errors = asm_streams(text)
            if errors:
                row['error'] = f'asm errors: {errors[:2]}'
                continue
            orig = orig_path.read_bytes()
            built, kgrs = repack(orig, file_type, streams)
            row['asm_matches_mod'] = mod_path.exists() and built == mod_path.read_bytes()

            # EVS: messages from the mod/ tree (appended strings live there), entities from the ARD
            src = mod_path if mod_path.exists() else orig_path
            parts, checks = [], []
            for i, stream in enumerate(streams):
                kgr = kgrs[i] if i < len(kgrs) else None
                msgs = ent.messages_for(src if file_type != 'ard' else orig_path, kgr)
                txt = lang.decompile(stream, entities=ent.entities_for(orig_path, kgr),
                                     world=ent.world_prefix(orig_path), messages=msgs,
                                     names=ent.names_for(orig_path, i))
                body = '\n'.join(lang.INDENT + l if l else l for l in txt.rstrip('\n').split('\n'))
                parts.append(f'kgr {i} {{\n{body}\n}}')
                checks.append((txt, msgs))
            evs_text = '\n\n'.join(parts) + '\n'
            evs_path = out_dir / (str(rel) + '.evs')
            evs_path.parent.mkdir(parents=True, exist_ok=True)
            evs_path.write_text(evs_text, encoding='utf-8')

            # compile the EVS file as written (per KGR, checking message text against its .binl)
            back = lang.compile_file_text(evs_path.read_text(encoding='utf-8'))
            for txt, msgs in checks:
                if msgs:
                    lang.compile_text(txt, msgs)  # raises if a message's text differs from its .binl
            new_streams = [back[i] for i in range(len(streams))]
            row['evs_streams_match_asm'] = new_streams == [bytes(s) for s in streams]
            rebuilt, _ = repack(orig, file_type, new_streams)
            row['evs_matches_mod'] = mod_path.exists() and rebuilt == mod_path.read_bytes()
            row['kgrs'] = len(streams)
            row['asm_threads'] = evs_text.count(' asm {')
        except Exception as e:
            row['error'] = f'{type(e).__name__}: {e}'
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument('repo', help='repo with asm/ and mod/ (e.g. KH1-RANDOMIZER)')
    ap.add_argument('--out', help='where to write the .evs tree (default: <repo>/evs)')
    a = ap.parse_args()
    repo = Path(a.repo)
    rows = convert(repo, Path(a.out) if a.out else repo / 'evs')
    ok = [r for r in rows if r.get('evs_matches_mod')]
    print(f'{len(rows)} asm files; EVS rebuilds mod/ byte for byte: {len(ok)}')
    stale = [r['file'] for r in rows if 'error' not in r and not r['asm_matches_mod']]
    if stale:
        print(f'asm does not match mod/ (stale or unbuilt mod files), {len(stale)}:', *stale, sep='\n  ')
    bad = [r for r in rows if 'error' not in r and r['asm_matches_mod'] and not r['evs_matches_mod']]
    if bad:
        print('EVS mismatches:', *[r['file'] for r in bad], sep='\n  ')
    for r in rows:
        if 'error' in r:
            print(f"ERROR {r['file']}: {r['error']}")
    fallbacks = [(r['file'], r['asm_threads']) for r in rows if r.get('asm_threads')]
    if fallbacks:
        print('files with threads kept as asm:', fallbacks)


if __name__ == '__main__':
    main()
