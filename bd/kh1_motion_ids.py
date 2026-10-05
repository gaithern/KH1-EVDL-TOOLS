#!/usr/bin/env python3
# Lists the motion IDs each enemy .bd script plays (SetMotion/QueueMotion/BlendMotion) and
# resolves each to its local .mset animation index.
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "asm"))
import kh1_bd_disasm as bd
from kh1_motion_dict import read_motion_dict

USAGE = """Usage:
  python kh1_motion_ids.py <file.mdls> [<file2.mdls> ...] [--json out.json]
"""

NATIVE_RE = re.compile(r"(NATIVE_t0_0x0?[cCdDeE]|SetMotion|QueueMotion|BlendMotion)\(([^)]*)\)")
LABEL_RE = re.compile(r"^(@L[0-9A-Fa-f]{4}):$")
SLOT_BY_VERB_NAME = {"SetMotion": "d", "QueueMotion": "e", "BlendMotion": "c"}
MOTION_ID_MASK = 0xFFFF
FLAGS_SHIFT = 16


def _slot_letter(verb_text):
    if verb_text.startswith("NATIVE_t0_0x"):
        return verb_text[-1].lower()
    return SLOT_BY_VERB_NAME[verb_text]


def _base(name):
    return name.rsplit(".", 1)[0]


def _is_suffixed(name):
    return _base(name).count("_") >= 2


def _enemy_id(name):
    return "_".join(_base(name).split("_")[:2])


def _sibling_motion_dict(mdls_path):
    mset_path = os.path.splitext(mdls_path)[0] + ".mset"
    try:
        return read_motion_dict(mset_path)
    except (FileNotFoundError, struct.error):
        return {}


def _block_confidence(name, has_suffixed):
    if _is_suffixed(name) or not has_suffixed:
        return "high"
    return "low"


def _motion_calls(line):
    calls = []
    for verb_text, args in NATIVE_RE.findall(line):
        arguments = []
        for argument in args.split(","):
            arguments.append(argument.strip())
        if len(arguments) < 2:
            continue
        try:
            raw = int(arguments[1])
        except ValueError:
            continue
        calls.append((_slot_letter(verb_text), raw))
    return calls


def extract(mdls_path):
    with open(mdls_path, "rb") as file:
        data = file.read()
    motion_dict = _sibling_motion_dict(mdls_path)
    blocks = bd.find_blocks(data)
    has_suffixed = False
    for _, name, _ in blocks:
        if _is_suffixed(name):
            has_suffixed = True
    findings = []
    for block_off, name, size in blocks:
        text = bd.fold(data, block_off, name, size)
        confidence = _block_confidence(name, has_suffixed)
        current_label = None
        for line in text.split("\n"):
            label = LABEL_RE.match(line.strip())
            if label:
                current_label = label.group(1)
                continue
            for slot, raw in _motion_calls(line):
                motion_id = raw & MOTION_ID_MASK
                findings.append({
                    "enemy": _enemy_id(name),
                    "file": mdls_path,
                    "block": name,
                    "label": current_label,
                    "slot": f"0x0{slot.lower()}",
                    "motion_id": motion_id,
                    "anim_index": motion_dict.get(motion_id),
                    "flags": raw >> FLAGS_SHIFT,
                    "raw": raw,
                    "confidence": confidence,
                })
    return findings


def _split_json_option(args):
    if "--json" not in args:
        return args, None
    index = args.index("--json")
    return args[:index] + args[index + 2:], args[index + 1]


def _print_table(findings):
    print(f"{'enemy':<14} {'block':<18} {'label':<8} {'slot':<6} {'id':>5} {'anim':<8} {'flags':>8}  {'conf':<5} raw")
    for finding in findings:
        if finding["anim_index"] is not None:
            anim = f"anim{finding['anim_index']:04d}"
        else:
            anim = "-"
        label = finding["label"] or "-"
        print(f"{finding['enemy']:<14} {finding['block']:<18} {label:<8} {finding['slot']:<6} "
              f"{finding['motion_id']:>5} {anim:<8} {finding['flags']:>#8x}  {finding['confidence']:<5} {finding['raw']}")


def main():
    args, out_json = _split_json_option(sys.argv[1:])
    if not args:
        print(USAGE)
        return
    all_findings = []
    for path in args:
        try:
            all_findings.extend(extract(path))
        except Exception as error:
            print(f"skipping {path}: {error}", file=sys.stderr)
    if out_json:
        with open(out_json, "w") as file:
            json.dump(all_findings, file, indent=1)
        print(f"wrote {len(all_findings)} findings to {out_json}")
    else:
        _print_table(all_findings)


if __name__ == "__main__":
    main()
