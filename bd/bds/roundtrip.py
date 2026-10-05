"""Decompile and recompile every .bd block of the enemy .mdls files (or just the named ones) and
report the exact-match rate and how many functions came out as BDS vs asm.
"""
import os
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lang

GAME_DATA = Path(os.environ.get('KH1_GAME_DATA', 'C:/OpenKH/OpenKHEGS/data/kh1'))
BELOW_NORMAL_PRIORITY_CLASS = 0x4000
UNIX_NICENESS = 10


def below_normal():
    if os.name == 'nt':
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), BELOW_NORMAL_PRIORITY_CLASS)
    else:
        os.nice(UNIX_NICENESS)


def highest_count_first(reason_and_count):
    return -reason_and_count[1]


def model_files(names):
    if names:
        return [GAME_DATA / f'{name}.mdls' for name in names]
    return sorted(GAME_DATA.glob('xa_*.mdls'))


def is_asm_function(line):
    match = lang.FUNC_RE.match(line)
    return bool(match and match.group(3))


def main(names):
    below_normal()
    files = model_files(names)
    exact = failed = function_count = asm_count = 0
    errors = Counter()
    started = time.time()
    for path in files:
        data = path.read_bytes()
        for block_off, block_name, size in lang.bd.find_blocks(data):
            try:
                text = lang.decompile_block(data, block_off, block_name, size)
            except Exception as e:
                failed += 1
                errors[f'{type(e).__name__}: {e}'[:90]] += 1
                continue
            exact += 1
            headers = [line for line in text.split('\n') if line.startswith('    func ')]
            function_count += len(headers)
            asm_count += sum(1 for line in headers if is_asm_function(line))
    print(f'files {len(files)}  blocks round-tripped exactly: {exact}/{exact + failed}  ({time.time() - started:.0f}s)')
    bds_count = function_count - asm_count
    print(f'functions {function_count}: as BDS {bds_count} ({100 * bds_count // max(function_count, 1)}%), '
          f'kept as asm {asm_count}')
    print('asm fallback reasons:')
    for reason, count in sorted(lang.STATS.items(), key=highest_count_first):
        print(f'  {count:6}  {reason}')
    if errors:
        print('errors:', errors.most_common(8))


if __name__ == '__main__':
    main(sys.argv[1:])
