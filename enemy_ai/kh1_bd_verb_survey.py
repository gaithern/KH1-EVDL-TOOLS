#!/usr/bin/env python3
"""Survey every enemy .bd script for unnamed native verbs (NATIVE_tN_0xXX), so the most
cross-cutting ones (used by the most distinct enemies - i.e. real generic engine verbs,
not one enemy's own quirk) can be prioritized for Ghidra/CheatEngine confirmation next.

Usage:
  python kh1_bd_verb_survey.py <mdls_glob> [--top N]
  python kh1_bd_verb_survey.py "/c/OpenKH/OpenKHEGS/data/kh1/*.mdls" --top 25
"""
import sys, glob, re, collections
from kh1_bd_disasm import find_blocks, fold, VERBS

NATIVE_RE = re.compile(r"NATIVE_t(\d)_(0x[0-9a-fA-F]+)\(")

def survey(paths):
    per_verb_files = collections.defaultdict(set)
    per_verb_count = collections.Counter()
    per_verb_examples = collections.defaultdict(list)
    for path in paths:
        try:
            data = open(path, "rb").read()
        except Exception:
            continue
        blocks = find_blocks(data)
        if not blocks:
            continue
        for off, name, size in blocks:
            try:
                text = fold(data, off, name, size)
            except Exception:
                continue
            for line in text.splitlines():
                for m in NATIVE_RE.finditer(line):
                    key = (int(m.group(1)), int(m.group(2), 16))
                    per_verb_files[key].add(path)
                    per_verb_count[key] += 1
                    if len(per_verb_examples[key]) < 3:
                        per_verb_examples[key].append(line.strip())
    return per_verb_files, per_verb_count, per_verb_examples

def main():
    args = sys.argv[1:]
    top = 25
    if "--top" in args:
        i = args.index("--top"); top = int(args[i+1]); args = args[:i]+args[i+2:]
    pattern = args[0] if args else "/c/OpenKH/OpenKHEGS/data/kh1/*.mdls"
    paths = sorted(glob.glob(pattern))
    print(f"scanning {len(paths)} files matching {pattern!r} ...", file=sys.stderr)
    files_by_verb, count_by_verb, examples = survey(paths)
    ranked = sorted(files_by_verb, key=lambda k: (-len(files_by_verb[k]), -count_by_verb[k]))
    print(f"{'verb':<14} {'#enemies':>8} {'#calls':>7}  example(s)")
    for key in ranked[:top]:
        t, idx = key
        label = f"t{t}_{idx:#04x}"
        print(f"{label:<14} {len(files_by_verb[key]):>8} {count_by_verb[key]:>7}")
        for ex in examples[key]:
            print(f"    {ex}")
    print(f"\n{len(ranked)} distinct unnamed verbs seen total across {len(paths)} files.")

if __name__ == "__main__":
    main()
