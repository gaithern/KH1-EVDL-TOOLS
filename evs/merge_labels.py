"""Merge crawled save-data label candidates into save_data_labels.json, bit_labels.json and a
reference catalog (save_data_catalog.json) with meanings, value tables and evidence."""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
LABELS = TOOLS / 'save_data_labels.json'
BITS = TOOLS / 'bit_labels.json'
CATALOG = TOOLS / 'save_data_catalog.json'

RANK = {'high': 3, 'medium': 2, 'low': 1}
SOURCE_PREF = {'evdl_docs': 3, 'lua': 2, 'denhonator': 1}
ROOM_TABLE = range(0x46C, 0x556)  # save_data2 per-room set bytes, named by the engine formula
RENAME = {0xDA9: 'GREEN_TRINITIES_ACTIVATED'}  # labels added this session that the crawl corrected


def var_id(region, off):
    if region == 'save_data':
        return off if off < 0x900 else off + 0x200
    return off + 0xD40


def load(paths):
    out = []
    for src, p in paths.items():
        for e in json.loads(Path(p).read_text(encoding='utf-8')):
            region = e.get('region')
            if region not in ('save_data', 'save_data2'):
                continue
            off = int(str(e['offset']), 16)
            width = e.get('width', 'byte')
            if '[' in width or 'array' in e.get('meaning', '').lower()[:40] and e.get('bit') is None:
                width_kind = 'array'
            else:
                width_kind = width
            bit = e.get('bit')
            out.append(dict(src=src, region=region, off=off, bit=None if bit is None else int(bit),
                            width=width_kind, name=e['name'], meaning=e.get('meaning', ''),
                            values=e.get('values') or {}, evidence=e.get('evidence', []),
                            conf=e.get('confidence', 'low'), note=e.get('note', '')))
    return out


def main(paths):
    labels = {int(k, 16): v for k, v in json.loads(LABELS.read_text()).items()}
    cands = load(paths)
    groups = defaultdict(list)
    for c in cands:
        groups[(c['region'], c['off'], c['bit'])].append(c)
    # per-element names beat an array-base name at the same byte
    elem_bytes = {k[:2] for k, cs in groups.items() if any(c['width'] != 'array' for c in cs)}

    byte_names, bit_names, catalog, report = {}, {}, [], defaultdict(list)
    for key, cs in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or -1)):
        region, off, bit = key
        var = var_id(region, off)
        usable = [c for c in cs if c['width'] != 'array' or key[:2] not in elem_bytes]
        if region == 'save_data2' and off in ROOM_TABLE and bit is None:
            room = [c for c in usable if c['name'].endswith('_SET_NUMBER')]
            usable = room or usable
        if not usable:
            continue
        agree = defaultdict(set)
        for c in usable:
            agree[c['name']].add(c['src'])
        best = max(usable, key=lambda c: (RANK.get(c['conf'], 0), len(agree[c['name']]), SOURCE_PREF[c['src']]))
        conf = max(RANK.get(c['conf'], 0) for c in usable if c['name'] == best['name'])
        if region == 'save_data2' and off in ROOM_TABLE and best['name'].endswith('_SET_NUMBER'):
            conf = 3  # derived from the engine's room-count table (vault: allset.set note)
        entry = dict(region=region, offset=f'0x{off:X}', var_id=f'0x{var:X}', bit=bit, name=best['name'],
                     confidence={3: 'high', 2: 'medium', 1: 'low'}[conf],
                     meaning=' | '.join(dict.fromkeys(c['meaning'] for c in usable if c['meaning'])),
                     values={k: v for c in usable for k, v in c['values'].items()},
                     other_names=sorted({c['name'] for c in usable} - {best['name']}),
                     sources=sorted({c['src'] for c in usable}),
                     evidence=list(dict.fromkeys(ev for c in usable for ev in c['evidence']))[:6])
        if bit is None and var in labels:
            entry['existing_label'] = labels[var]
        catalog.append(entry)
        if conf < 2:
            report['low'].append(entry)
            continue
        if bit is None:
            if var in labels:
                if var in RENAME:
                    byte_names[var] = RENAME[var]
                elif labels[var] != best['name'] and best['name'] not in entry['other_names']:
                    report['conflict'].append((labels[var], entry))
                continue
            byte_names[var] = best['name']
        else:
            bit_names[var * 8 + bit] = best['name']

    # names must be unique across both tables
    taken = set(labels.values())
    for table in (byte_names, bit_names):
        for k in sorted(table):
            base = table[k]
            if k in RENAME:
                taken.discard(labels.get(k))
            name, n = base, 2
            while name in taken:
                name, n = f'{base}_{n}', n + 1
            if name != base:
                report['renamed_dup'].append((base, name))
            table[k] = name
            taken.add(name)

    merged = dict(labels)
    merged.update(byte_names)
    LABELS.write_text(json.dumps({f'0x{k:X}': v for k, v in sorted(merged.items())}, indent=2) + '\n')
    BITS.write_text(json.dumps({f'0x{k:X}': v for k, v in sorted(bit_names.items())}, indent=2) + '\n')
    CATALOG.write_text(json.dumps(catalog, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    new = len([k for k in byte_names if k not in labels])
    print(f'byte labels: {len(labels)} -> {len(merged)} (+{new}), renamed {sum(1 for k in RENAME if k in byte_names)}')
    print(f'bit labels: {len(bit_names)}; catalog entries: {len(catalog)}; low-confidence skipped: {len(report["low"])}')
    print('conflicts with existing labels (kept existing):')
    for old, e in report['conflict']:
        print(f'  {e["var_id"]} {old}  vs  {e["name"]} ({e["confidence"]}, {",".join(e["sources"])})')
    print('duplicate names suffixed:', report['renamed_dup'][:20])


if __name__ == '__main__':
    s = Path(sys.argv[1])
    main({'evdl_docs': s / 'labels_evdl_docs.json', 'lua': s / 'labels_lua.json',
          'denhonator': s / 'labels_denhonator.json'})
