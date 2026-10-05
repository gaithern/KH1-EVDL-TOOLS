#!/usr/bin/env python3
# Assembler for kh1_bd_disasm.py's raw listing: checks that blocks round-trip, and patches an
# edited listing back into an .mdls.
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kh1_bd_disasm as bd

USAGE = """Usage:
  python kh1_bd_asm.py roundtrip <file.mdls> [block|all]
  python kh1_bd_asm.py patch <in.mdls> <edited listing> <out.mdls>
"""


def _invert(table):
    inverted = {}
    for value, name in table.items():
        inverted[name] = value
    return inverted


UNARY_OP = _invert(bd.UNARY)
ARITH_OP = _invert(bd.ARITH)
CMP_OP = _invert(bd.CMP)
BASE_OP = _invert(bd.BASE)
MODE_BY_SUFFIX = _invert(bd.MODESFX)
JUMP_CLASS_BY_MNEMONIC = {"jmp": bd.CLASS_JUMP, "bz": bd.CLASS_BRANCH_IF_ZERO, "bnz": bd.CLASS_BRANCH_IF_NONZERO}

HEADER_RE = re.compile(r"^; =====\s+(\S+)\s+block@0x([0-9A-Fa-f]+)\s+code@0x([0-9A-Fa-f]+)\s+size=0x([0-9A-Fa-f]+)")
LABEL_RE = re.compile(r"^(@L[0-9A-Fa-f]+):")
LINE_RE = re.compile(r"^\s*(?:([0-9A-F]{4})\s+)?((?:[0-9a-f]{2} )*)\s*([A-Za-z][\w.?]*)\s*(.*?)\s*$")
MEM_RE = re.compile(r"^\[(loc|glob|heap|imm)(\+-?\d+|-\d+)\]$")
SELF_SLOT_RE = re.compile(r"^; detected: glob\[(\d+)\] = self")
RAW_UNARY_RE = re.compile(r"un0x[0-9a-f]+")
RAW_ARITH_RE = re.compile(r"ar0x[0-9a-f]+")
RAW_COMPARE_RE = re.compile(r"c0x[0-9a-f]+")
PUSH_VALUE_RE = re.compile(r"(\[[^\]]+\])\s*x(\d+)")
CALL_OPERAND_RE = re.compile(r"(@L[0-9A-Fa-f]+)\s+locals=(\d+)")
NATIVE_OPERAND_RE = re.compile(r"t(\d)\s*#(0x[0-9a-fA-F]+)")
PUSHED_NUMBER_RE = re.compile(r"push\s+#(\d+)\b")

CLASS_MASK = 0xF
INHERITED_FIELDS_MASK = 0xFFF0
KEEP_ALL_BUT_SUB_MASK = 0x00FF
MODE_MASK = 0x30
BASE_MASK = 0xC0
SUB_SHIFT = 8
MODE_SHIFT = 4
BASE_SHIFT = 6


class AsmError(Exception):
    pass


def _strip_comment(raw):
    if raw.startswith("; ====="):
        return raw
    return raw.split(";", 1)[0]


def _parse_instruction_line(line, raw, line_no):
    match = LINE_RE.match(line)
    if not match:
        raise AsmError(f"line {line_no}: can't parse: {raw.strip()}")
    hint = None
    if match.group(2).strip():
        hint = bytes.fromhex(match.group(2).replace(" ", ""))
    return ("ins", match.group(3), match.group(4).strip(), hint, line_no)


def parse_listing(text):
    blocks = []
    current = None
    self_slot = None
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = _strip_comment(raw)
        header = HEADER_RE.match(raw)
        if header:
            current = (header.group(1), int(header.group(2), 16), int(header.group(3), 16), [])
            blocks.append(current)
            self_slot = None
            continue
        self_match = SELF_SLOT_RE.match(raw)
        if self_match:
            self_slot = int(self_match.group(1))
            continue
        if self_slot is not None:
            line = line.replace("[self]", f"[glob+{self_slot}]")
        if current is None or not line.strip():
            continue
        label = LABEL_RE.match(line.strip())
        if label:
            current[3].append(("label", label.group(1)))
            continue
        current[3].append(_parse_instruction_line(line, raw, line_no))
    return blocks


def _mem(operand, line_no):
    match = MEM_RE.match(operand.replace(" ", ""))
    if not match:
        raise AsmError(f"line {line_no}: expected [base+off], got {operand!r}")
    offset = int(match.group(2).replace("+-", "-"))
    return BASE_OP[match.group(1)], offset


def _arith_sub(name):
    if name in ARITH_OP:
        return ARITH_OP[name]
    return int(name[2:], 16)


def _compare_sub(name):
    if name in CMP_OP:
        return CMP_OP[name]
    return int(name[1:], 16)


def _is_arith_mnemonic(parts):
    if len(parts) != 2 or parts[1] not in MODE_BY_SUFFIX:
        return False
    return parts[0] in ARITH_OP or RAW_ARITH_RE.fullmatch(parts[0]) is not None


def _is_compare_mnemonic(parts):
    if len(parts) != 3 or parts[0] != "cmp" or parts[2] not in MODE_BY_SUFFIX:
        return False
    return parts[1] in CMP_OP or RAW_COMPARE_RE.fullmatch(parts[1]) is not None


def _float_bytes(text):
    if text.startswith("0x"):
        return bytes.fromhex(text[2:])[::-1]
    return struct.pack("<f", float(text))


def _push_meaning(operand, line_no):
    if operand.startswith("#"):
        value = operand[1:]
        if value.endswith("f"):
            return bd.CLASS_PUSH, {"mode": bd.PUSH_FLOAT}, "imm", _float_bytes(value[:-1])
        return bd.CLASS_PUSH, {"mode": bd.PUSH_INT}, "imm", struct.pack("<i", int(value, 0))
    match = PUSH_VALUE_RE.fullmatch(operand)
    if not match:
        raise AsmError(f"line {line_no}: push needs #value or [base+off] xN")
    base, offset = _mem(match.group(1), line_no)
    fields = {"mode": bd.PUSH_VALUE, "base": base, "sub": int(match.group(2))}
    return bd.CLASS_PUSH, fields, "off", offset


def _lea_meaning(operand, line_no):
    if operand.startswith("@D"):
        fields = {"mode": bd.PUSH_ADDRESS, "base": bd.BASE_IMMEDIATE, "sub": 0}
        return bd.CLASS_PUSH, fields, "data", int(operand[2:], 16)
    base, offset = _mem(operand, line_no)
    return bd.CLASS_PUSH, {"mode": bd.PUSH_ADDRESS, "base": base, "sub": 0}, "off", offset


def meaning(mnem, oper, n):
    if mnem in UNARY_OP:
        return bd.CLASS_UNARY, {"sub": UNARY_OP[mnem]}, None, None
    if mnem == "op":
        op = int(oper, 16)
        return op & CLASS_MASK, {"raw": op}, None, None
    if RAW_UNARY_RE.fullmatch(mnem):
        return bd.CLASS_UNARY, {"sub": int(mnem[2:], 16)}, None, None
    parts = mnem.split(".")
    if _is_arith_mnemonic(parts):
        return bd.CLASS_ARITH, {"sub": _arith_sub(parts[0]), "mode": MODE_BY_SUFFIX[parts[1]]}, None, None
    if _is_compare_mnemonic(parts):
        return bd.CLASS_COMPARE, {"sub": _compare_sub(parts[1]), "mode": MODE_BY_SUFFIX[parts[2]]}, None, None
    if mnem == "push":
        return _push_meaning(oper, n)
    if mnem == "lea":
        return _lea_meaning(oper, n)
    if mnem == "store":
        base, offset = _mem(oper, n)
        return bd.CLASS_STORE, {"base": base}, "off", offset
    if mnem in JUMP_CLASS_BY_MNEMONIC:
        return JUMP_CLASS_BY_MNEMONIC[mnem], {}, "rel", oper.split()[0]
    if mnem == "call":
        match = CALL_OPERAND_RE.fullmatch(oper)
        if not match:
            raise AsmError(f"line {n}: call needs @Lxxxx locals=N")
        return bd.CLASS_CALL, {"sub": int(match.group(2))}, "rel", match.group(1)
    if mnem == "idxadd":
        return bd.CLASS_INDEX_ADD, {"sub": int(oper)}, None, None
    if mnem == "load":
        return bd.CLASS_LOAD, {"sub": int(oper.lstrip("x"))}, None, None
    match = NATIVE_OPERAND_RE.fullmatch(oper)
    if match:
        fields = {"base": int(match.group(1)), "sub": int(match.group(2), 16), "mode": 0}
        return bd.CLASS_NATIVE, fields, None, None
    raise AsmError(f"line {n}: unknown instruction {mnem} {oper}")


def _length(cls, fields):
    if "raw" in fields:
        return bd.ilen(fields["raw"])
    if cls == bd.CLASS_PUSH:
        if fields["mode"] in (bd.PUSH_INT, bd.PUSH_FLOAT):
            return 6
        return 4
    if cls in bd.FOUR_BYTE_CLASSES:
        return 4
    return 2


def _compose(cls, fields, prev_op):
    if "raw" in fields:
        return fields["raw"]
    op = prev_op & INHERITED_FIELDS_MASK
    if "mode" in fields:
        op = (op & ~MODE_MASK) | (fields["mode"] << MODE_SHIFT)
    if "base" in fields:
        op = (op & ~BASE_MASK) | (fields["base"] << BASE_SHIFT)
    if "sub" in fields:
        op = (op & KEEP_ALL_BUT_SUB_MASK) | (fields["sub"] << SUB_SHIFT)
    return op | cls


def _same_meaning(hint, cls, fields):
    if not hint or len(hint) < 2:
        return False
    op = struct.unpack_from("<H", hint)[0]
    if bd.opcode_class(op) != cls:
        return False
    if "raw" in fields:
        return op == fields["raw"]
    current = {"mode": bd.opcode_mode(op), "base": bd.opcode_base(op), "sub": bd.opcode_sub(op)}
    for field, value in fields.items():
        if cls == bd.CLASS_NATIVE and field == "mode":
            continue
        if current[field] != value:
            return False
    return True


def _parse_items(items):
    parsed = []
    for item in items:
        if item[0] == "label":
            parsed.append(item)
        else:
            _, mnemonic, operand, hint, line_no = item
            parsed.append(("ins", meaning(mnemonic, operand, line_no), hint, line_no))
    return parsed


def _label_offsets(parsed, block_off, code_off):
    pos = code_off
    labels = {}
    for item in parsed:
        if item[0] == "label":
            labels[item[1]] = pos - block_off
        else:
            cls, fields, _, _ = item[1]
            pos += _length(cls, fields)
    return labels


def _jump_target(value, labels, line_no):
    if value in labels:
        return labels[value]
    try:
        return int(value[2:], 16)
    except ValueError:
        raise AsmError(f"line {line_no}: unknown label {value}")


def _encode_operand(kind, value, pos, block_off, labels, line_no):
    if kind == "imm":
        return value
    if kind == "off":
        return struct.pack("<h", value)
    if kind == "data":
        return struct.pack("<h", value + block_off - (pos + 2))
    if kind == "rel":
        target = _jump_target(value, labels, line_no)
        delta = target + block_off - (pos + 4)
        if delta % 2:
            raise AsmError(f"line {line_no}: odd jump distance to {value}")
        return struct.pack("<h", delta // 2)
    return b""


def assemble(items, block_off, code_off, use_hints=True):
    parsed = _parse_items(items)
    labels = _label_offsets(parsed, block_off, code_off)
    out = bytearray()
    pos = code_off
    prev_op = 0
    for item in parsed:
        if item[0] == "label":
            continue
        (cls, fields, kind, value), hint, line_no = item[1], item[2], item[3]
        length = _length(cls, fields)
        if use_hints and _same_meaning(hint, cls, fields):
            op = struct.unpack_from("<H", hint)[0]
        else:
            op = _compose(cls, fields, prev_op)
        encoded = struct.pack("<H", op) + _encode_operand(kind, value, pos, block_off, labels, line_no)
        if len(encoded) != length:
            raise AsmError(f"line {line_no}: encoded {len(encoded)} bytes, expected {length}")
        out += encoded
        pos += length
        prev_op = op
    old = {}
    for label in labels:
        old[label] = int(label[2:], 16)
    return bytes(out), labels, old


def _region(data, block_off, name, size):
    return bd._code_region(data, block_off, name, size)


def _differing_bytes(code, original):
    count = 0
    for new_byte, old_byte in zip(code, original):
        if new_byte != old_byte:
            count += 1
    return count + abs(len(code) - len(original))


def roundtrip(path, sel="all"):
    with open(path, "rb") as file:
        data = file.read()
    ok = True
    for index, (block_off, name, size) in enumerate(bd.find_blocks(data)):
        if not (sel == "all" or sel == str(index) or sel in name):
            continue
        start, end = _region(data, block_off, name, size)
        block = parse_listing(bd.disasm(data, block_off, name, size))[0]
        original = data[start:end]
        results = []
        for use_hints in (True, False):
            code, _, _ = assemble(block[3], block_off, start, use_hints=use_hints)
            if code == original:
                results.append("exact")
            else:
                results.append(f"{_differing_bytes(code, original)} bytes differ")
                if use_hints:
                    ok = False
        print(f"{name:18} {len(original):6} bytes  with hints: {results[0]:18} mnemonics only: {results[1]}")
    return ok


def _warn_moved_thread_entries(name, listing_text, moved, old):
    pushed_numbers = set()
    for number in PUSHED_NUMBER_RE.findall(listing_text):
        pushed_numbers.add(int(number))
    risky = []
    for label in moved:
        if old[label] % 2 == 0 and old[label] // 2 in pushed_numbers:
            risky.append(label)
    risky.sort()
    if risky:
        print(f"warning: {name}: routines moved whose old offset/2 appears as a pushed number "
              f"(thread/handler entries?): {', '.join(risky)} - update those literals by hand")


def patch(src, listing, dst):
    with open(src, "rb") as file:
        data = bytearray(file.read())
    blocks_by_offset = {}
    for block_off, name, size in bd.find_blocks(bytes(data)):
        blocks_by_offset[block_off] = (name, size)
    with open(listing, encoding="utf-8") as file:
        listing_text = file.read()
    for name, block_off, code_off, items in parse_listing(listing_text):
        if block_off not in blocks_by_offset:
            raise AsmError(f"{name}: no .bd block at 0x{block_off:X} in {src}")
        file_name, size = blocks_by_offset[block_off]
        start, end = _region(bytes(data), block_off, file_name, size)
        if start != code_off:
            raise AsmError(f"{name}: listing says code@0x{code_off:X}, file has 0x{start:X}")
        code, new, old = assemble(items, block_off, start)
        room = end - start
        if len(code) > room:
            raise AsmError(f"{name}: assembled code is {len(code)} bytes, only {room} available")
        moved = set()
        for label in new:
            if new[label] != old[label]:
                moved.add(label)
        if moved:
            _warn_moved_thread_entries(name, listing_text, moved, old)
        data[start:start + len(code)] = code
        data[start + len(code):end] = bytes(room - len(code))
        summary = f"{name}: {len(code)} of {room} bytes"
        if moved:
            summary += f", {len(moved)} labels moved"
        print(summary)
    with open(dst, "wb") as file:
        file.write(bytes(data))


def main():
    args = sys.argv[1:]
    try:
        if args[:1] == ["roundtrip"] and len(args) >= 2:
            if len(args) > 2:
                selector = args[2]
            else:
                selector = "all"
            if roundtrip(args[1], selector):
                sys.exit(0)
            sys.exit(1)
        if args[:1] == ["patch"] and len(args) == 4:
            patch(args[1], args[2], args[3])
            return
    except AsmError as error:
        sys.exit(f"error: {error}")
    print(USAGE)


if __name__ == "__main__":
    main()
