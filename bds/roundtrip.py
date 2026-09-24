"""Decompile and recompile every .bd block of the enemy .mdls files; report the exact-match rate and
how many functions came out as BDS vs asm.

    python bds/roundtrip.py                  every xa_*.mdls under KH1_GAME_DATA
    python bds/roundtrip.py xa_tz_3000 ...   just these files

Runs as one process at below-normal priority.
"""
import os
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lang  # noqa: E402

GAME_DATA = Path(os.environ.get('KH1_GAME_DATA', 'C:/OpenKH/OpenKHEGS/data/kh1'))


def below_normal():
    if os.name == 'nt':
        import ctypes
        k = ctypes.windll.kernel32
        k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)   # BELOW_NORMAL_PRIORITY_CLASS
    else:
        os.nice(10)


def main(names):
    below_normal()
    files = [GAME_DATA / f'{n}.mdls' for n in names] if names else sorted(GAME_DATA.glob('xa_*.mdls'))
    ok = bad = funcs = asm = 0
    errs = Counter()
    t0 = time.time()
    for f in files:
        data = f.read_bytes()
        for b, n, s in lang.bd.find_blocks(data):
            try:
                text = lang.decompile_block(data, b, n, s)     # asserts the exact round trip itself
            except Exception as e:
                bad += 1
                errs[f'{type(e).__name__}: {e}'[:90]] += 1
                continue
            ok += 1
            heads = [ln for ln in text.split('\n') if ln.startswith('    func ')]
            funcs += len(heads)
            asm += sum(1 for ln in heads if lang.FUNC_RE.match(ln) and lang.FUNC_RE.match(ln).group(3))
    print(f'files {len(files)}  blocks round-tripped exactly: {ok}/{ok + bad}  ({time.time() - t0:.0f}s)')
    print(f'functions {funcs}: as BDS {funcs - asm} ({100 * (funcs - asm) // max(funcs, 1)}%), kept as asm {asm}')
    print('asm fallback reasons:')
    for k, v in sorted(lang.STATS.items(), key=lambda kv: -kv[1]):
        print(f'  {v:6}  {k}')
    if errs:
        print('errors:', errs.most_common(8))


if __name__ == '__main__':
    main(sys.argv[1:])
