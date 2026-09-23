"""Rewrite a repo's evs/ tree from its built mod/ files, so every .evs picks up the current names,
syntax and `globals { }` block. Only run when mod/ was built from evs/ (it is decompiled back)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lang


def refresh(repo):
    repo = Path(repo)
    done = 0
    for evs in sorted((repo / 'evs').rglob('*.evs')):
        rel = evs.relative_to(repo / 'evs').with_suffix('')
        built = repo / 'mod' / rel
        if not built.is_file():
            print(f'skip {rel}: no mod/ file')
            continue
        evs.write_text(lang.decompile_file(built), encoding='utf-8')
        done += 1
    print(f'{done} .evs file(s) rewritten from mod/')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    refresh(sys.argv[1])
