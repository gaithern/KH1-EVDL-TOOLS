#!/usr/bin/env python3
# Lists the motion IDs each enemy .bd script plays (SetMotion/QueueMotion/BlendMotion) and
# resolves each to its local .mset animation index.
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "asm"))
sys.path.insert(0, os.path.join(HERE, "bds"))
import lang
from kh1_motion_dict import read_motion_dict

USAGE = """Usage:
  python kh1_motion_ids.py <file.mdls> [<file2.mdls> ...] [--json out.json]
"""

MOTION_CALL_RE = re.compile(r"(SetMotion|QueueMotion|BlendMotion|__t0_0x0[cde])\(([^)]*)\)")
ASM_MOTION_CALL_RE = re.compile(r"^\S+ t0 #0x0([cde])$")
ASM_INTEGER_PUSH_RE = re.compile(r"^push #(-?\d+)$")
MOTION_TABLE = 0
SLOT_BY_VERB_NAME = {"SetMotion": "d", "QueueMotion": "e", "BlendMotion": "c"}
MOTION_ID_MASK = 0xFFFF
FLAGS_SHIFT = 16


def slot_letter(verb_text):
    if verb_text in SLOT_BY_VERB_NAME:
        return SLOT_BY_VERB_NAME[verb_text]
    return verb_text[-1]


def block_base(name):
    return name.rsplit(".", 1)[0]


def is_suffixed(name):
    return block_base(name).count("_") >= 2


def enemy_id(name):
    return "_".join(block_base(name).split("_")[:2])


def sibling_motion_dict(mdls_path):
    mset_path = os.path.splitext(mdls_path)[0] + ".mset"
    try:
        return read_motion_dict(mset_path)
    except (FileNotFoundError, struct.error):
        return {}


def block_confidence(name, has_suffixed):
    if is_suffixed(name) or not has_suffixed:
        return "high"
    return "low"


def motion_calls(line):
    calls = []
    for verb_text, argument_text in MOTION_CALL_RE.findall(line):
        arguments = [argument.strip() for argument in argument_text.split(",")]
        if len(arguments) < 2:
            continue
        try:
            raw = int(arguments[1], 0)
        except ValueError:
            continue
        calls.append((slot_letter(verb_text), raw))
    return calls


def asm_motion_call(instruction, previous_instructions):
    native = ASM_MOTION_CALL_RE.match(instruction)
    if not native:
        return None
    slot = native.group(1)
    argument_count = lang.bd.ARITY[(MOTION_TABLE, int(slot, 16))][0]
    if len(previous_instructions) < argument_count:
        return None
    arguments = previous_instructions[-argument_count:]
    for argument in arguments:
        if not argument.startswith("push "):
            return None
    motion_argument = ASM_INTEGER_PUSH_RE.match(arguments[1])
    if not motion_argument:
        return None
    return slot, int(motion_argument.group(1))


def extract(mdls_path):
    with open(mdls_path, "rb") as file:
        data = file.read()
    motion_dict = sibling_motion_dict(mdls_path)
    blocks = lang.bd.find_blocks(data)
    has_suffixed = any(is_suffixed(name) for _, name, _ in blocks)
    findings = []
    for block_off, name, size in blocks:
        text = lang.decompile_block(data, block_off, name, size)
        confidence = block_confidence(name, has_suffixed)
        current_function = None
        in_asm_function = False
        previous_instructions = []
        for line in text.split("\n"):
            function = lang.FUNC_RE.match(line)
            if function:
                current_function = function.group(1)
                in_asm_function = function.group(3) == "asm"
                previous_instructions = []
                continue
            calls = motion_calls(line)
            if in_asm_function:
                instruction = line.strip()
                asm_call = asm_motion_call(instruction, previous_instructions)
                calls = []
                if asm_call:
                    calls = [asm_call]
                if instruction and not instruction.endswith(":"):
                    previous_instructions.append(instruction)
            for slot, raw in calls:
                motion_id = raw & MOTION_ID_MASK
                findings.append({
                    "enemy": enemy_id(name),
                    "file": mdls_path,
                    "block": name,
                    "function": current_function,
                    "slot": f"0x0{slot}",
                    "motion_id": motion_id,
                    "anim_index": motion_dict.get(motion_id),
                    "flags": raw >> FLAGS_SHIFT,
                    "raw": raw,
                    "confidence": confidence,
                })
    return findings


def split_json_option(args):
    if "--json" not in args:
        return args, None
    index = args.index("--json")
    return args[:index] + args[index + 2:], args[index + 1]


def print_table(findings):
    print(f"{'enemy':<14} {'block':<18} {'function':<20} {'slot':<6} {'id':>5} {'anim':<8} {'flags':>8}  {'conf':<5} raw")
    for finding in findings:
        if finding["anim_index"] is not None:
            anim = f"anim{finding['anim_index']:04d}"
        else:
            anim = "-"
        function = finding["function"] or "-"
        print(f"{finding['enemy']:<14} {finding['block']:<18} {function:<20} {finding['slot']:<6} "
              f"{finding['motion_id']:>5} {anim:<8} {finding['flags']:>#8x}  {finding['confidence']:<5} {finding['raw']}")


def main():
    args, out_json = split_json_option(sys.argv[1:])
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
        print_table(all_findings)


if __name__ == "__main__":
    main()
