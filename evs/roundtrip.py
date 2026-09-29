"""Decompile and recompile every corpus stream; report exact-match rate and script coverage."""
from collections import Counter
from pathlib import Path
from corpus import load, GAME_DATA
import entities
import lang

stats = {}
shown = 0
ok = bad = 0
errs = Counter()
first_bad = []
for st in load():
    try:
        src = GAME_DATA / st['src']
        msgs = entities.messages_for(src)
        txt = lang.decompile(st['stream'], stats, entities.entities_for(src), entities.world_prefix(src), msgs)
        out = lang.compile_text(txt, msgs)
    except Exception as e:
        errs[f'{type(e).__name__}: {e}'[:80]] += 1
        bad += 1
        continue
    shown += txt.count('messages[')
    if out == st['stream']:
        ok += 1
    else:
        bad += 1
        if len(first_bad) < 5:
            first_bad.append(st['src'])
print(f'streams round-tripped exactly: {ok}/{ok + bad}')
print(f"threads as EVS: {stats.get('ok', 0)}, kept as asm: {stats.get('asm', 0)}, raw tails: {stats.get('raw', 0)}")
print('asm fallback reasons:', stats.get('fail'))
print('errors:', errs.most_common(8))
print('mismatches:', first_bad)
print('message texts shown:', shown)
