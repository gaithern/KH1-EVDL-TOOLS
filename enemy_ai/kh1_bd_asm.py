#!/usr/bin/env python3
"""Assembler for kh1_bd_disasm.py's raw listing: edit a .bd block's instructions as text and
patch them back into the .mdls.

Usage:
  python kh1_bd_asm.py roundtrip <file.mdls> [block|all]
      disassemble -> assemble every block and check the bytes come back identical, both with
      the listing's byte column as a hint and re-encoding from mnemonics alone.
  python kh1_bd_asm.py patch <in.mdls> <edited listing> <out.mdls>
      assemble every block in the listing and write a patched copy of the .mdls.

Editing the listing:
  - Change mnemonics/operands freely; the offset and byte columns may be left stale or deleted.
    A line keeps its original bytes only while its meaning is unchanged.
  - Labels (@Lxxxx:) are just names: add, move or reference them; jumps and calls are
    re-resolved, so instructions can be inserted or removed.
  - Fields an instruction doesn't use are copied from the previous instruction's opcode, the
    way the original compiler did (99.9% of the shipped bytecode follows this).
  - The assembled block must fit in the space the original code occupied; smaller is padded.
  - Code offsets passed as plain numbers (StartThread / ReplaceThread / SetEventHandlers entry
    arguments, in 16-bit words) are NOT re-resolved; the tool warns when a size-changing edit
    moves a routine whose offset appears as such a number.
"""
import os, re, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kh1_bd_disasm as bd

UNARY_OP = {v: k for k, v in bd.UNARY.items()}
ARITH_OP = {v: k for k, v in bd.ARITH.items()}
CMP_OP = {v: k for k, v in bd.CMP.items()}
BASE_OP = {v: k for k, v in bd.BASE.items()}
HEADER_RE = re.compile(r"^; =====\s+(\S+)\s+block@0x([0-9A-Fa-f]+)\s+code@0x([0-9A-Fa-f]+)\s+size=0x([0-9A-Fa-f]+)")
LABEL_RE = re.compile(r"^(@L[0-9A-Fa-f]+):")
LINE_RE = re.compile(r"^\s*(?:([0-9A-F]{4})\s+)?((?:[0-9a-f]{2} )*)\s*([A-Za-z][\w.?]*)\s*(.*?)\s*$")
MEM_RE = re.compile(r"^\[(loc|glob|heap|imm)(\+-?\d+|-\d+)\]$")


class AsmError(Exception):
    pass


def parse_listing(text):
    """[(block_name, block_off, code_off, [items])]; items are ('label', name) or
    ('ins', mnemonic, operand, hint_bytes|None, line_no)."""
    blocks = []; cur = None; self_slot = None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split(";", 1)[0] if not raw.startswith("; =====") else raw
        m = HEADER_RE.match(raw)
        if m:
            cur = (m.group(1), int(m.group(2), 16), int(m.group(3), 16), [])
            blocks.append(cur); self_slot = None; continue
        m = re.match(r"^; detected: glob\[(\d+)\] = self", raw)
        if m:                                       # the listing shows [glob+N] as [self]
            self_slot = int(m.group(1)); continue
        if self_slot is not None:
            line = line.replace("[self]", f"[glob+{self_slot}]")
        if cur is None or not line.strip():
            continue
        m = LABEL_RE.match(line.strip())
        if m:
            cur[3].append(("label", m.group(1))); continue
        m = LINE_RE.match(line)
        if not m:
            raise AsmError(f"line {n}: can't parse: {raw.strip()}")
        hint = bytes.fromhex(m.group(2).replace(" ", "")) if m.group(2).strip() else None
        cur[3].append(("ins", m.group(3), m.group(4).strip(), hint, n))
    return blocks


def _mem(oper, n):
    m = MEM_RE.match(oper.replace(" ", ""))
    if not m:
        raise AsmError(f"line {n}: expected [base+off], got {oper!r}")
    return BASE_OP[m.group(1)], int(m.group(2).replace("+-", "-"))


def meaning(mnem, oper, n):
    """-> (cls, fields{name: value}, operand_kind, operand_value). Fields are the opcode parts
    that matter for this instruction; everything else is inherited."""
    if mnem in UNARY_OP:
        return 0, {"sub": UNARY_OP[mnem]}, None, None
    if mnem == "op":                               # raw opcode word (no such class in the VM)
        op = int(oper, 16)
        return op & 0xF, {"raw": op}, None, None
    if re.fullmatch(r"un0x[0-9a-f]+", mnem):
        return 0, {"sub": int(mnem[2:], 16)}, None, None
    parts = mnem.split(".")
    MODE = {"i": 0, "f": 1, "m2": 2, "m3": 3}
    if len(parts) == 2 and parts[1] in MODE and (parts[0] in ARITH_OP or re.fullmatch(r"ar0x[0-9a-f]+", parts[0])):
        sub = ARITH_OP.get(parts[0]) if parts[0] in ARITH_OP else int(parts[0][2:], 16)
        return 1, {"sub": sub, "mode": MODE[parts[1]]}, None, None
    if len(parts) == 3 and parts[0] == "cmp" and parts[2] in MODE and (parts[1] in CMP_OP or re.fullmatch(r"c0x[0-9a-f]+", parts[1])):
        sub = CMP_OP.get(parts[1]) if parts[1] in CMP_OP else int(parts[1][1:], 16)
        return 7, {"sub": sub, "mode": MODE[parts[2]]}, None, None
    if mnem == "push":
        if oper.startswith("#"):
            v = oper[1:]
            if v.endswith("f"):
                t = v[:-1]
                b = bytes.fromhex(t[2:])[::-1] if t.startswith("0x") else struct.pack("<f", float(t))
                return 2, {"mode": 1}, "imm", b
            return 2, {"mode": 0}, "imm", struct.pack("<i", int(v, 0))
        m = re.fullmatch(r"(\[[^\]]+\])\s*x(\d+)", oper)
        if not m:
            raise AsmError(f"line {n}: push needs #value or [base+off] xN")
        base, off = _mem(m.group(1), n)
        return 2, {"mode": 3, "base": base, "sub": int(m.group(2))}, "off", off
    if mnem == "lea":
        if oper.startswith("@D"):
            return 2, {"mode": 2, "base": 3, "sub": 0}, "data", int(oper[2:], 16)
        base, off = _mem(oper, n)
        return 2, {"mode": 2, "base": base, "sub": 0}, "off", off     # compiler clears sub on lea
    if mnem == "store":
        base, off = _mem(oper, n)
        return 3, {"base": base}, "off", off
    if mnem in ("jmp", "bz", "bnz"):
        return {"jmp": 4, "bz": 5, "bnz": 6}[mnem], {}, "rel", oper.split()[0]
    if mnem == "call":
        m = re.fullmatch(r"(@L[0-9A-Fa-f]+)\s+locals=(\d+)", oper)
        if not m:
            raise AsmError(f"line {n}: call needs @Lxxxx locals=N")
        return 8, {"sub": int(m.group(2))}, "rel", m.group(1)
    if mnem == "idxadd":
        return 9, {"sub": int(oper)}, None, None
    if mnem == "load":
        return 0xA, {"sub": int(oper.lstrip("x"))}, None, None
    m = re.fullmatch(r"t(\d)\s*#(0x[0-9a-fA-F]+)", oper)
    if m:                                          # native: any name, the operand decides
        return 0xB, {"base": int(m.group(1)), "sub": int(m.group(2), 16), "mode": 0}, None, None
    raise AsmError(f"line {n}: unknown instruction {mnem} {oper}")


def _length(cls, fields):
    if "raw" in fields:
        return bd.ilen(fields["raw"])
    if cls == 2:
        return 6 if fields["mode"] in (0, 1) else 4
    return 4 if cls in (3, 4, 5, 6, 8) else 2


def _compose(cls, fields, prev_op):
    if "raw" in fields:
        return fields["raw"]
    op = prev_op & 0xFFF0                            # inherit everything not given
    if "mode" in fields: op = (op & ~0x30) | (fields["mode"] << 4)
    if "base" in fields: op = (op & ~0xC0) | (fields["base"] << 6)
    if "sub" in fields: op = (op & 0x00FF) | (fields["sub"] << 8)
    return op | cls


def _same_meaning(hint, cls, fields):
    if not hint or len(hint) < 2:
        return False
    op = struct.unpack_from("<H", hint)[0]
    if op & 0xF != cls:
        return False
    if "raw" in fields:
        return op == fields["raw"]
    have = {"mode": (op >> 4) & 3, "base": (op >> 6) & 3, "sub": op >> 8}
    # native calls are encoded with mode 0, but keep whatever an unedited line had
    return all(have[k] == v for k, v in fields.items() if not (cls == 0xB and k == "mode"))


def assemble(items, block_off, code_off, use_hints=True):
    """-> (code bytes, {label: new block-relative offset}, {label: old offset})."""
    parsed = []
    for it in items:
        if it[0] == "label":
            parsed.append(it)
        else:
            _, mnem, oper, hint, n = it
            parsed.append(("ins", meaning(mnem, oper, n), hint, n))
    # pass 1: addresses
    pos = code_off; labels = {}
    for it in parsed:
        if it[0] == "label":
            labels[it[1]] = pos - block_off
        else:
            cls, fields, _, _ = it[1]; pos += _length(cls, fields)
    # pass 2: encode
    out = bytearray(); pos = code_off; prev_op = 0
    for it in parsed:
        if it[0] == "label":
            continue
        (cls, fields, kind, val), hint, n = it[1], it[2], it[3]
        L = _length(cls, fields)
        op = struct.unpack_from("<H", hint)[0] if use_hints and _same_meaning(hint, cls, fields) \
            else _compose(cls, fields, prev_op)
        b = struct.pack("<H", op)
        if kind == "imm":
            b += val
        elif kind == "off":
            b += struct.pack("<h", val)
        elif kind == "data":
            b += struct.pack("<h", val + block_off - (pos + 2))
        elif kind == "rel":
            if val in labels:
                tgt = labels[val]
            else:                                  # target outside the listed code: keep it fixed
                try: tgt = int(val[2:], 16)
                except ValueError: raise AsmError(f"line {n}: unknown label {val}")
            delta = tgt + block_off - (pos + 4)
            if delta % 2:
                raise AsmError(f"line {n}: odd jump distance to {val}")
            b += struct.pack("<h", delta // 2)
        if len(b) != L:
            raise AsmError(f"line {n}: encoded {len(b)} bytes, expected {L}")
        out += b; pos += L; prev_op = op
    old = {lb: int(lb[2:], 16) for lb in labels}
    return bytes(out), labels, old


def _region(data, block_off, name, size):
    end = min(block_off + 4 + size, len(data))
    start = bd.code_start(data, block_off, name, end)
    return start, bd.extend_end(data, block_off, start, end)


def roundtrip(path, sel="all"):
    data = open(path, "rb").read(); ok = True
    for i, (b, n, s) in enumerate(bd.find_blocks(data)):
        if not (sel == "all" or sel == str(i) or sel in n):
            continue
        start, end = _region(data, b, n, s)
        blk = parse_listing(bd.disasm(data, b, n, s))[0]
        orig = data[start:end]
        res = []
        for hints in (True, False):
            code, _, _ = assemble(blk[3], b, start, use_hints=hints)
            same = code == orig
            diff = sum(1 for x, y in zip(code, orig) if x != y) + abs(len(code) - len(orig))
            res.append(f"{'exact' if same else f'{diff} bytes differ'}")
            ok &= same or not hints
        print(f"{n:18} {len(orig):6} bytes  with hints: {res[0]:18} mnemonics only: {res[1]}")
    return ok


def patch(src, listing, dst):
    data = bytearray(open(src, "rb").read())
    by_off = {b: (n, s) for b, n, s in bd.find_blocks(bytes(data))}
    for name, block_off, code_off, items in parse_listing(open(listing, encoding="utf-8").read()):
        if block_off not in by_off:
            raise AsmError(f"{name}: no .bd block at 0x{block_off:X} in {src}")
        n, s = by_off[block_off]
        start, end = _region(bytes(data), block_off, n, s)
        if start != code_off:
            raise AsmError(f"{name}: listing says code@0x{code_off:X}, file has 0x{start:X}")
        code, new, old = assemble(items, block_off, start)
        room = end - start
        if len(code) > room:
            raise AsmError(f"{name}: assembled code is {len(code)} bytes, only {room} available")
        moved = {lb for lb in new if new[lb] != old[lb]}
        if moved:
            text = open(listing, encoding="utf-8").read()
            lits = {int(x) for x in re.findall(r"push\s+#(\d+)\b", text)}
            risky = sorted(lb for lb in moved if old[lb] % 2 == 0 and old[lb] // 2 in lits)
            if risky:
                print(f"warning: {name}: routines moved whose old offset/2 appears as a pushed number "
                      f"(thread/handler entries?): {', '.join(risky)} - update those literals by hand")
        data[start:start + len(code)] = code
        data[start + len(code):end] = bytes(room - len(code))
        print(f"{name}: {len(code)} of {room} bytes" + (f", {len(moved)} labels moved" if moved else ""))
    open(dst, "wb").write(bytes(data))


def main():
    a = sys.argv[1:]
    try:
        if a[:1] == ["roundtrip"] and len(a) >= 2:
            sys.exit(0 if roundtrip(a[1], a[2] if len(a) > 2 else "all") else 1)
        if a[:1] == ["patch"] and len(a) == 4:
            patch(a[1], a[2], a[3]); return
    except AsmError as e:
        sys.exit(f"error: {e}")
    print(__doc__)


if __name__ == "__main__":
    main()
