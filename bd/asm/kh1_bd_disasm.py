#!/usr/bin/env python3
# Disassembler for KH1 enemy behavior scripts (.bd blocks inside xa_*.mdls): decodes the bytecode
# into a raw instruction listing. BDS (bd/bds) builds its C-like view on top of this decoder.
import json
import os
import re
import struct
import sys

USAGE = """Usage:
  python kh1_bd_disasm.py <file.mdls>                  list behavior blocks
  python kh1_bd_disasm.py <file.mdls> <block|all>      disassemble (block = name part or index)
"""

CLASS_UNARY = 0
CLASS_ARITH = 1
CLASS_PUSH = 2
CLASS_STORE = 3
CLASS_JUMP = 4
CLASS_BRANCH_IF_ZERO = 5
CLASS_BRANCH_IF_NONZERO = 6
CLASS_COMPARE = 7
CLASS_CALL = 8
CLASS_INDEX_ADD = 9
CLASS_LOAD = 0xA
CLASS_NATIVE = 0xB

BRANCH_CLASSES = (CLASS_BRANCH_IF_ZERO, CLASS_BRANCH_IF_NONZERO)
JUMP_CLASSES = (CLASS_JUMP, CLASS_BRANCH_IF_ZERO, CLASS_BRANCH_IF_NONZERO)
FOUR_BYTE_CLASSES = (CLASS_STORE, CLASS_JUMP, CLASS_BRANCH_IF_ZERO, CLASS_BRANCH_IF_NONZERO, CLASS_CALL)

PUSH_INT = 0
PUSH_FLOAT = 1
PUSH_ADDRESS = 2
PUSH_VALUE = 3

BASE_IMMEDIATE = 3

UNARY_YIELD = 0
UNARY_INT_ABS = 1
UNARY_FLOAT_ABS = 2
UNARY_RETURN = 3
UNARY_POP = 4
UNARY_FLOAT_TO_INT = 5
UNARY_FLOAT_TO_INT2 = 6
UNARY_STORE_INDIRECT = 7
UNARY_ABORT = 8
UNARY_INT_NEGATE = 9
UNARY_FLOAT_NEGATE = 10
UNARY_BIT_NOT = 11
UNARY_DUP = 12
UNARY_LOGICAL_NOT = 13


OP_YIELD = 0x0000
OP_RETURN = 0x0300
OP_ABORT = 0x0800

BD_MAGIC = b"\x14\x03"
BD_NAME_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_."
MAX_NAME_READ = 24
MAX_PADDING_WORDS = 3
MAX_SKIPPED_LEADING_INSTRUCTIONS = 4

UNARY = {
    0: "yield",
    1: "iabs",
    2: "fabs",
    3: "ret",
    4: "pop",
    5: "ftoi",
    6: "ftoi2",
    7: "store.ind",
    8: "abort",
    9: "ineg",
    10: "fneg",
    11: "bnot",
    12: "dup",
    13: "lnot",
}
ARITH = {
    0: "add",
    1: "sub",
    2: "mul",
    3: "div",
    4: "mod",
    5: "and",
    6: "or",
    7: "xor",
    8: "shl",
    9: "shr",
    10: "land",
    11: "lor",
}
CMP = {0: "ltz", 1: "lez", 2: "eqz", 3: "nez", 4: "gez", 5: "gtz"}
BASE = {0: "loc", 1: "glob", 2: "heap", 3: "imm"}
MODESFX = {0: "i", 1: "f", 2: "m2", 3: "m3"}
JUMP_MNEMONICS = {
    CLASS_JUMP: "jmp",
    CLASS_BRANCH_IF_ZERO: "bz",
    CLASS_BRANCH_IF_NONZERO: "bnz",
    CLASS_CALL: "call",
}

VERBS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kh1_bd_verbs.json")


def load_verbs():
    try:
        with open(VERBS_PATH) as file:
            verb_table = json.load(file)
        names = {}
        for key, entry in verb_table.items():
            if not key.startswith("_"):
                names[key] = entry.get("name")
        return names
    except Exception:
        return {}


VERBS = load_verbs()


def load_arity():
    try:
        with open(VERBS_PATH) as file:
            verb_table = json.load(file)
        arity = {}
        for table in (0, 1):
            for index, pair in enumerate(verb_table.get("_arity_t%d" % table, [])):
                arity[(table, index)] = tuple(pair)
        return arity
    except Exception:
        return {}


ARITY = load_arity()


def opcode_class(op):
    return op & 0xF


def opcode_mode(op):
    return (op >> 4) & 3


def opcode_base(op):
    return (op >> 6) & 3


def opcode_sub(op):
    return op >> 8


def ilen(op):
    op_class = opcode_class(op)
    if op_class == CLASS_PUSH:
        if opcode_mode(op) in (PUSH_INT, PUSH_FLOAT):
            return 6
        return 4
    if op_class in FOUR_BYTE_CLASSES:
        return 4
    return 2


def is_invalid_opcode(op):
    return opcode_class(op) == CLASS_UNARY and opcode_sub(op) not in UNARY


def f32_text(four_bytes):
    value = struct.unpack("<f", four_bytes)[0]
    if value != value or value in (float("inf"), float("-inf")):
        return "0x" + four_bytes[::-1].hex()
    for precision in range(1, 10):
        text = f"{value:.{precision}g}"
        if struct.pack("<f", float(text)) != four_bytes:
            continue
        if "e" in text and (value == 0 or abs(value) >= 1e-4):
            plain = format(float(text), "f").rstrip("0").rstrip(".")
            if struct.pack("<f", float(plain)) == four_bytes:
                text = plain
        return text
    return repr(value)


def u16(buffer, offset):
    return struct.unpack_from("<H", buffer, offset)[0]


def s16(buffer, offset):
    return struct.unpack_from("<h", buffer, offset)[0]


def i32(buffer, offset):
    return struct.unpack_from("<i", buffer, offset)[0]


def _is_bd_name(name):
    if not 3 <= len(name) <= 20:
        return False
    if b"." not in name:
        return False
    if not chr(name[0]).isalpha():
        return False
    for byte in name:
        if chr(byte) not in BD_NAME_CHARS:
            return False
    return True


def _read_block_name(data, block_off):
    return data[block_off + 4:block_off + 4 + MAX_NAME_READ].split(b"\x00")[0]


def find_blocks(data):
    blocks = []
    for match in re.finditer(BD_MAGIC, data):
        block_off = match.start()
        name = _read_block_name(data, block_off)
        if not _is_bd_name(name):
            continue
        size = u16(data, block_off + 2)
        if size > 0 and block_off + 4 + size <= len(data) + 16:
            blocks.append((block_off, name.decode("ascii", "replace"), size))
    return blocks


def _count_valid_instructions(data, start, end):
    pos = start
    instruction_count = 0
    zero_run = 0
    while pos < end - 1:
        op = u16(data, pos)
        if op == OP_YIELD:
            zero_run += 1
            if zero_run > MAX_PADDING_WORDS:
                break
            pos += 2
            continue
        zero_run = 0
        if is_invalid_opcode(op):
            break
        instruction_count += 1
        pos += ilen(op)
    return instruction_count


def _skip_leading_jumps_and_yields(data, start):
    for _ in range(MAX_SKIPPED_LEADING_INSTRUCTIONS):
        op = u16(data, start)
        if opcode_class(op) in JUMP_CLASSES or op == OP_YIELD:
            start += ilen(op)
        else:
            break
    return start


def code_start(data, block_off, name, end):
    first_candidate = block_off + 4 + len(name)
    if first_candidate % 2:
        first_candidate += 1
    best_start = None
    best_count = -1
    for candidate in range(first_candidate, end - 2, 2):
        count = _count_valid_instructions(data, candidate, end)
        if count > best_count:
            best_start = candidate
            best_count = count
    if best_start is None:
        return first_candidate
    return _skip_leading_jumps_and_yields(data, best_start)


def _is_block_header_at(data, pos):
    return data[pos:pos + 2] == BD_MAGIC and _is_bd_name(_read_block_name(data, pos))


def extend_end(data, block_off, start, end):
    pos = start
    zero_run = 0
    limit = len(data)
    while pos < limit - 1:
        if pos < end:
            pos += ilen(u16(data, pos))
            continue
        if _is_block_header_at(data, pos):
            break
        op = u16(data, pos)
        if op == OP_YIELD:
            zero_run += 1
            if zero_run > MAX_PADDING_WORDS:
                break
            pos += 2
            continue
        zero_run = 0
        if is_invalid_opcode(op):
            break
        pos += ilen(op)
    return max(pos, end)


def _code_region(data, block_off, name, size):
    declared_end = min(block_off + 4 + size, len(data))
    start = code_start(data, block_off, name, declared_end)
    end = extend_end(data, block_off, start, declared_end)
    return start, end


def _rename_roles(text, roles):
    for role, slot in roles.items():
        text = text.replace(f"globblk[{slot}]", role)
        text = text.replace(f"glob[{slot}]", role)
        text = re.sub(rf"glob\+{slot}\b", role, text)
    return text


def _self_role_header_line(roles):
    return (f"; detected: glob[{roles['self']}] = self (cached actor handle, "
            f"renamed below) - arg0 of SetMotion/QueueMotion/BlendMotion/MakeAttack")


def _disasm_push(data, pos, op, block_off):
    mode = opcode_mode(op)
    base = opcode_base(op)
    if mode == PUSH_INT:
        return "push", f"#{i32(data, pos + 2)}"
    if mode == PUSH_FLOAT:
        return "push", f"#{f32_text(data[pos + 2:pos + 6])}f"
    if mode == PUSH_ADDRESS:
        if base == BASE_IMMEDIATE:
            return "lea", f"@D{pos + 2 + s16(data, pos + 2) - block_off:04X}"
        return "lea", f"[{BASE[base]}+{s16(data, pos + 2)}]"
    return "push", f"[{BASE[base]}+{s16(data, pos + 2)}] x{opcode_sub(op)}"


def _disasm_instruction(data, pos, op, block_off):
    op_class = opcode_class(op)
    sub = opcode_sub(op)
    mode = opcode_mode(op)
    base = opcode_base(op)
    if op_class == CLASS_UNARY:
        return UNARY.get(sub, f"un{sub:#x}"), ""
    if op_class == CLASS_ARITH:
        return f"{ARITH.get(sub, f'ar{sub:#x}')}.{MODESFX[mode]}", ""
    if op_class == CLASS_PUSH:
        return _disasm_push(data, pos, op, block_off)
    if op_class == CLASS_STORE:
        return "store", f"[{BASE[base]}+{s16(data, pos + 2)}]"
    if op_class in JUMP_MNEMONICS:
        target = pos + 4 + s16(data, pos + 2) * 2
        operand = f"@L{target - block_off:04X}"
        if op_class == CLASS_CALL:
            operand += f" locals={sub}"
        return JUMP_MNEMONICS[op_class], operand
    if op_class == CLASS_COMPARE:
        return f"cmp.{CMP.get(sub, f'c{sub:#x}')}.{MODESFX[mode]}", ""
    if op_class == CLASS_INDEX_ADD:
        return "idxadd", str(sub)
    if op_class == CLASS_LOAD:
        return "load", f"x{sub}"
    if op_class == CLASS_NATIVE:
        verb_name = VERBS.get(f"{base}:{sub:#04x}")
        if not verb_name:
            verb_name = "NATIVE"
        return verb_name, f"t{base} #{sub:#04x}"
    return "op", f"0x{op:04x}"


def _terminator_note(op):
    if op == OP_RETURN:
        return "  ; ---- return ----"
    if op == OP_ABORT:
        return "  ; ---- abort ----"
    if op == OP_YIELD:
        return "  ; resumes here next update"
    return ""


def disasm(data, block_off, name, size):
    start, end = _code_region(data, block_off, name, size)
    roles = detect_roles(data, block_off, name, size)
    rows = []
    targets = set()
    call_counts = {}
    pos = start
    while pos < end - 1:
        op = u16(data, pos)
        length = ilen(op)
        mnemonic, operand = _disasm_instruction(data, pos, op, block_off)
        if opcode_class(op) in JUMP_MNEMONICS:
            target = pos + 4 + s16(data, pos + 2) * 2
            targets.add(target)
            if opcode_class(op) == CLASS_CALL:
                call_counts[target] = call_counts.get(target, 0) + 1
        rows.append((pos, data[pos:pos + length], mnemonic, operand, op))
        pos += length
    header = [f"; ===== {name}  block@0x{block_off:X}  code@0x{start:X}  size=0x{size:X} ====="]
    if roles.get("self") is not None:
        header.append(_self_role_header_line(roles))
    lines = []
    for pos, raw, mnemonic, operand, op in rows:
        relative = pos - block_off
        if pos in targets:
            label_line = f"@L{relative:04X}:"
            if call_counts.get(pos):
                label_line += f"  ; sub, called {call_counts[pos]}x"
            lines.append(label_line)
        lines.append(f"      {relative:04X}  {raw.hex(' '):<17} {mnemonic:<14} {operand:<16}{_terminator_note(op)}")
    return "\n".join(header) + "\n" + _rename_roles("\n".join(lines), roles)


STUB_VERBS = {(0, 0x42)}
MAX_PARAMS = 16
MAX_RETURNS = 4
ACTOR_ARG0_VERBS = {(0, 0x0c), (0, 0x0d), (0, 0x0e), (0, 0x17)}
SELF_MIN_HITS = 2
SELF_MIN_SHARE = 0.8


def _pop_or_none(stack):
    if stack:
        stack.pop()


def _simulate_glob_arguments(data, start, end):
    stack = []
    tally = {}
    pos = start
    while pos < end - 1:
        op = u16(data, pos)
        op_class = opcode_class(op)
        sub = opcode_sub(op)
        base = opcode_base(op)
        if op_class == CLASS_PUSH:
            if opcode_mode(op) in (PUSH_INT, PUSH_FLOAT):
                stack.append(None)
            elif BASE[base] == "glob":
                stack.append(("glob", s16(data, pos + 2)))
            else:
                stack.append(None)
        elif op_class == CLASS_LOAD:
            stack.append(None)
        elif op_class == CLASS_INDEX_ADD:
            _pop_or_none(stack)
            stack.append(None)
        elif op_class in (CLASS_ARITH, CLASS_COMPARE):
            _pop_or_none(stack)
            if op_class == CLASS_ARITH:
                _pop_or_none(stack)
            stack.append(None)
        elif op_class == CLASS_UNARY:
            _simulate_unary(stack, sub)
        elif op_class == CLASS_STORE:
            _pop_or_none(stack)
        elif op_class == CLASS_CALL:
            stack.clear()
        elif op_class == CLASS_NATIVE:
            _simulate_native(stack, base, sub, tally)
        pos += ilen(op)
    return tally


def _simulate_unary(stack, sub):
    if sub == UNARY_YIELD:
        stack.clear()
    elif sub == UNARY_DUP:
        if stack:
            stack.append(stack[-1])
    elif sub in (UNARY_INT_ABS, UNARY_FLOAT_ABS, UNARY_INT_NEGATE, UNARY_FLOAT_NEGATE,
                 UNARY_FLOAT_TO_INT, UNARY_FLOAT_TO_INT2, UNARY_BIT_NOT, UNARY_LOGICAL_NOT):
        _pop_or_none(stack)
        stack.append(None)
    elif sub in (UNARY_RETURN, UNARY_POP):
        _pop_or_none(stack)


def _simulate_native(stack, table, sub, tally):
    arity = ARITY.get((table, sub))
    if arity:
        argument_count = arity[0]
    else:
        argument_count = len(stack)
    arguments = []
    for _ in range(argument_count):
        if stack:
            arguments.append(stack.pop())
        else:
            arguments.append(None)
    arguments.reverse()
    if (table, sub) in ACTOR_ARG0_VERBS and arguments and arguments[0]:
        slot = arguments[0][1]
        tally[slot] = tally.get(slot, 0) + 1
    if arity and arity[1]:
        stack.append(None)


def detect_roles(data, block_off, name, size):
    start, end = _code_region(data, block_off, name, size)
    tally = _simulate_glob_arguments(data, start, end)
    if not tally:
        return {}
    best = max(tally, key=tally.get)
    total = sum(tally.values())
    if tally[best] >= SELF_MIN_HITS and tally[best] >= SELF_MIN_SHARE * total:
        return {"self": best}
    return {}


def _decode(data, start, end):
    ins = {}
    order = []
    pos = start
    while pos < end - 1:
        op = u16(data, pos)
        length = ilen(op)
        if length >= 4:
            argument = s16(data, pos + 2)
        else:
            argument = None
        ins[pos] = {
            "pos": pos,
            "op": op,
            "c": opcode_class(op),
            "sub": opcode_sub(op),
            "mode": opcode_mode(op),
            "base": opcode_base(op),
            "len": length,
            "arg": argument,
        }
        order.append(pos)
        pos += length
    return ins, order


def _target(i):
    return i["pos"] + 4 + i["arg"] * 2


def _unary_effect(sub):
    if sub == UNARY_YIELD:
        return 0, 0, "fall"
    if sub == UNARY_RETURN:
        return 0, 0, "ret"
    if sub == UNARY_ABORT:
        return 0, 0, "stop"
    if sub == UNARY_POP:
        return 1, 0, "fall"
    if sub == UNARY_STORE_INDIRECT:
        return 2, 0, "fall"
    if sub == UNARY_DUP:
        return 1, 2, "fall"
    if sub in (UNARY_INT_ABS, UNARY_FLOAT_ABS, UNARY_FLOAT_TO_INT, UNARY_FLOAT_TO_INT2,
               UNARY_INT_NEGATE, UNARY_FLOAT_NEGATE, UNARY_BIT_NOT, UNARY_LOGICAL_NOT):
        return 1, 1, "fall"
    return 0, 0, "fall"


def _native_effect(table, sub):
    if (table, sub) in STUB_VERBS:
        return 0, 0, "fall"
    arity = ARITY.get((table, sub))
    if not arity:
        return 0, 0, "fall"
    if arity[1]:
        return arity[0], 1, "fall"
    return arity[0], 0, "fall"


def _effect(i, sig):
    op_class = i["c"]
    if op_class == CLASS_UNARY:
        return _unary_effect(i["sub"])
    if op_class == CLASS_ARITH:
        return 2, 1, "fall"
    if op_class == CLASS_PUSH:
        return 0, 1, "fall"
    if op_class == CLASS_STORE:
        return 1, 0, "fall"
    if op_class == CLASS_JUMP:
        return 0, 0, "jump"
    if op_class in BRANCH_CLASSES:
        return 1, 0, "branch"
    if op_class == CLASS_COMPARE:
        return 1, 1, "fall"
    if op_class == CLASS_CALL:
        params, returns = sig.get(_target(i), (0, 0))
        return params, returns, "fall"
    if op_class in (CLASS_INDEX_ADD, CLASS_LOAD):
        return 1, 1, "fall"
    if op_class == CLASS_NATIVE:
        return _native_effect(i["base"], i["sub"])
    return 0, 0, "fall"


def _successors(pc, i, flow):
    if flow == "fall":
        return [pc + i["len"]]
    if flow == "jump":
        return [_target(i)]
    if flow == "branch":
        return [pc + i["len"], _target(i)]
    return []


def _analyze_function(ins, entry, sig):
    depth = {entry: 0}
    work = [entry]
    lowest = 0
    return_depths = []
    mismatches = 0
    while work:
        pc = work.pop()
        i = ins.get(pc)
        if i is None:
            continue
        current = depth[pc]
        pops, pushes, flow = _effect(i, sig)
        lowest = min(lowest, current - pops)
        next_depth = current - pops + pushes
        if flow == "ret":
            return_depths.append(current)
        for successor in _successors(pc, i, flow):
            if successor not in ins:
                continue
            if successor in depth:
                if depth[successor] != next_depth:
                    mismatches += 1
                continue
            depth[successor] = next_depth
            work.append(successor)
    return {"depth": depth, "min": lowest, "rets": return_depths, "bad": mismatches}


def _analyze(ins, order, entries, sig):
    result = {}
    for entry in entries:
        result[entry] = _analyze_function(ins, entry, sig)
    return result


def _is_scaffolding(i):
    if i["c"] == CLASS_JUMP:
        return True
    return i["c"] == CLASS_UNARY and i["sub"] in (UNARY_YIELD, UNARY_RETURN, UNARY_ABORT)


def _ends_flow(i):
    if i["c"] == CLASS_JUMP:
        return True
    return i["c"] == CLASS_UNARY and i["sub"] in (UNARY_RETURN, UNARY_ABORT)


def _orphans(ins, order, entries, sig):
    reached = set()
    for analysis in _analyze(ins, order, entries, sig).values():
        reached |= set(analysis["depth"])
    found = []
    previous = None
    for pc in order:
        if pc not in reached and previous is not None and _ends_flow(ins[previous]):
            if _is_scaffolding(ins[pc]):
                reached.add(pc)
            else:
                found.append(pc)
                reached |= set(_analyze(ins, order, [pc], sig)[pc]["depth"])
        previous = pc
    return found


def _most_common_return_depth(return_depths):
    return max(set(return_depths), key=return_depths.count)


def _signature_of(analysis):
    params = -analysis["min"]
    if analysis["rets"]:
        returns = max(_most_common_return_depth(analysis["rets"]) + params, 0)
    else:
        returns = 0
    return min(params, MAX_PARAMS), min(returns, MAX_RETURNS)


def _signatures(ins, order, start):
    call_targets = set()
    for i in ins.values():
        if i["c"] == CLASS_CALL and _target(i) in ins:
            call_targets.add(_target(i))
    entries = [start]
    for target in sorted(call_targets):
        if target != start:
            entries.append(target)
    for orphan in _orphans(ins, order, entries, {}):
        if orphan not in entries:
            entries.append(orphan)
    calls = entries[1:]
    sig = {}
    for _ in range(12):
        analyses = _analyze(ins, order, entries, sig)
        new_sig = {}
        for entry in entries:
            new_sig[entry] = _signature_of(analyses[entry])
        if new_sig == sig:
            break
        sig = new_sig
    return sig, analyses, calls


def _print_block_table(blocks):
    print(f"{'idx':>3}  {'name':<18} {'block':>12} {'size':>7}")
    for index, (block_off, name, size) in enumerate(blocks):
        print(f"{index:>3}  {name:<18} 0x{block_off:08X} 0x{size:04X}")


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        return
    with open(sys.argv[1], "rb") as file:
        data = file.read()
    blocks = find_blocks(data)
    if not blocks:
        print("No .bd blocks found.")
        return
    if len(sys.argv) == 2:
        _print_block_table(blocks)
        return
    selector = sys.argv[2]
    matched = False
    for index, (block_off, name, size) in enumerate(blocks):
        if selector == "all" or selector == str(index) or selector in name:
            matched = True
            print(disasm(data, block_off, name, size))
            print()
    if not matched:
        print(f"No block matches {selector!r}.")


if __name__ == "__main__":
    main()
