"""Fix syscall (args, returns) splits the solver got wrong: for each syscall that blocks
decompilation, try shifted splits and keep the one that decompiles the most scripts."""
import json
import re
from collections import Counter
from corpus import load
import lang

streams = [x['stream'] for x in load()]


def fails(subset):
    st = {}
    for s in subset:
        lang.decompile(s, st)
    return st.get('asm', 0), st.get('fail', {})


def main(rounds=2):
    path = lang.HERE / 'syscall_arity.json'
    data = json.loads(path.read_text())
    for _ in range(rounds):
        _, why = fails(streams)
        culprits = Counter()
        for msg, n in why.items():
            m = re.search(r'syscall (\w+)', msg)
            if m and m.group(1) in lang.SYS_ID:
                culprits[lang.SYS_ID[m.group(1)]] += n
        changed = False
        for sid, n in culprits.most_common(12):
            pat = sid.to_bytes(3, 'little') + bytes([24])
            users = [s for s in streams if pat in s]
            a, r = lang.ARITY[sid]
            best = (fails(users)[0], (a, r))
            for da in (-1, 1, 2):
                for rr in (0, 1):
                    cand = (a + da + (rr - r), rr)
                    if cand[0] < 0 or cand == (a, r):
                        continue
                    lang.ARITY[sid] = cand
                    score = fails(users)[0]
                    if score < best[0]:
                        best = (score, cand)
            lang.ARITY[sid] = best[1]
            if best[1] != (a, r):
                changed = True
                data[str(sid)].update(args=best[1][0], returns=best[1][1])
                print(f'{lang.SYS_NAME[sid]}: {a},{r} -> {best[1][0]},{best[1][1]}  (asm scripts now {best[0]})')
        if not changed:
            break
    path.write_text(json.dumps(data, indent=1))
    print('total asm scripts:', fails(streams)[0])


if __name__ == '__main__':
    main()
