"""Rewrite a repo's evs/ tree from its built mod/ files, so every .evs picks up the current names,
syntax and `globals { }` block. Only run when mod/ was built from evs/ (it is decompiled back)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lang


def refresh(repo):
    repo = Path(repo)
    evs_dir = repo / 'evs'
    rewritten = 0
    for evs_path in sorted(evs_dir.rglob('*.evs')):
        relative = evs_path.relative_to(evs_dir).with_suffix('')
        built = repo / 'mod' / relative
        if not built.is_file():
            print(f'skip {relative}: no mod/ file')
            continue
        evs_path.write_text(lang.decompile_file(built), encoding='utf-8')
        rewritten += 1
    print(f'{rewritten} .evs file(s) rewritten from mod/')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    refresh(sys.argv[1])
