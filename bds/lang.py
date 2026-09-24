"""BDS: a C-like view of KH1 enemy behavior bytecode (.bd blocks inside xa_*.mdls).
decompile_block(...) -> text, compile_block(text) -> bytes.

Round trip is exact: compiling the decompiled text gives back the original bytes of every
block, with no edits. The same design as EVS (evs/lang.py): the decompiler only produces a
construct in the exact shape the emitter lays it out, and a function it cannot express is
kept as an `asm` function (instruction listing), which also round-trips. Bytes nothing can
reach are kept as a `data` block.

The VM (KH1_BehaviorScriptInterpreter, Steam 0x1402CC620) in short:
  - operand stack of variable-size values; `call` keeps it (args stay on it for the callee,
    whose prologue pops them into locals); `ret` returns whatever is left on it
  - locals/globals/heap addressed by byte offset; `glob[868]` reads a value, `&glob[868]` is
    its address; `E[N]` reads word N of the object/array a handle points at
  - `yield` stops for this update and resumes at the next instruction next update
  - opcode fields an instruction doesn't use repeat the previous opcode's (how the original
    compiler encoded), so each function may carry a `seed` opcode to continue from
"""
import json
import os
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'enemy_ai'))
import kh1_bd_disasm as bd  # noqa: E402  (decoder, stack analysis, native table)
import kh1_bd_asm as bdasm  # noqa: E402  (instruction-listing assembler, used for asm functions)

BASES = {0: 'loc', 1: 'glob', 2: 'heap'}
BASE_ID = {v: k for k, v in BASES.items()}
ARITH_SYM = {0: '+', 1: '-', 2: '*', 3: '/', 4: '%', 5: '&', 6: '|', 7: '^', 8: '<<', 9: '>>'}
ARITH_ID = {v: k for k, v in ARITH_SYM.items()}
LAND, LOR = 10, 11
CMP_SYM = {0: '<', 1: '<=', 2: '==', 3: '!=', 4: '>=', 5: '>'}
CMP_ID = {v: k for k, v in CMP_SYM.items()}
UNARY_FN = {1: 'iabs', 2: 'fabs', 5: 'ftoi', 6: 'ftoi2', 9: 'ineg', 10: 'fneg', 11: 'bnot'}
UNARY_FN_ID = {v: k for k, v in UNARY_FN.items()}
LNOT, DUP, POP, STOREI, YIELD, RET, ABORT = 13, 12, 4, 7, 0, 3, 8
MODE_SFX = {0: 'i', 1: 'f'}
DEFAULT_MODE = 1                      # mode chosen when neither operand says int or float

# natives: unique names from the verb table; a name used by two natives falls back to __tB_0xNN
_NAT = {}
for _k, _v in bd.VERBS.items():
    if _v:
        _NAT.setdefault(_v, []).append(_k)
NAT_NAME = {tuple(int(x, 0) for x in k.split(':')): n for n, ks in _NAT.items() if len(ks) == 1 for k in ks}
NAT_ID = {v: k for k, v in NAT_NAME.items()}
NAT_RAW_RE = re.compile(r'__t(\d)_(0x[0-9a-fA-F]+)$')

# actor fields (word offsets into the engine's `entity`), and the stats page's
VEC_FIELDS = {'pos': 4, 'rot': 12, 'scale': 16}
ACTOR_FIELDS = {'target': 29, 'stats': 27}
STATS_FIELDS = {'hp': 15, 'max_hp': 16, 'mp': 17}
AXES = 'xyzw'

RESERVED = {'func', 'asm', 'data', 'bd', 'names', 'if', 'else', 'while', 'loop', 'switch', 'case',
            'default', 'goto', 'return', 'yield', 'abort', 'frame', 'seed', 'loc', 'glob', 'heap',
            'self', 'load', '__push'} | set(UNARY_FN_ID)


class PartError(Exception):
    """A part (function) of a block failed to compile; .part is its name."""
    def __init__(self, part, err):
        super().__init__(f'{part}: {type(err).__name__}: {err}')
        self.part = part


class Fail(Exception):
    """The decompiler can't express a function; it is kept as asm."""


def num(n):
    return str(n) if -10 < n < 10 else (f'0x{n:X}' if n >= 0 else f'-0x{-n:X}')


def flt_text(b4):
    """A float literal that reads back to exactly these 4 bytes, always with a '.' or exponent."""
    t = bd.f32_text(b4)
    if t.startswith('0x'):
        return f'__f32({t})'
    if not re.search(r'[.en]', t):
        t += '.0'
    return t


# ─────────────────────────── expressions ───────────────────────────
# ('int', v) ('flt', b4) ('val', base, off, n) ('lea', base, off)  base 3 = data, off = block offset
# ('param', k) ('idx', e, n) ('load', e, n) ('un', sub, e) ('bin', sub, mode, a, b)
# ('cmp', sub, mode, e) ('sc', sub, mode, a, b)  (short-circuit && / ||)
# ('nat', base, sub, args) ('call', target, args) ('dupload', p, n)  (read side of p op= x)
# ('fref', name)  `@name`: the int offset/2 of a function, how threads/handlers are started

def infer(e):
    k = e[0]
    if k in ('int', 'fref', 'cmp', 'sc'):
        return 0
    if k == 'flt':
        return 1
    if k == 'bin':
        return e[2]
    if k == 'un':
        return {1: 0, 9: 0, 11: 0, 13: 0, 2: 1, 10: 1}.get(e[1])
    return None


def infer2(a, b):
    ma, mb = infer(a), infer(b)
    if 1 in (ma, mb):
        return 1
    if 0 in (ma, mb):
        return 0
    return DEFAULT_MODE


# ─────────────────────────── building statements ───────────────────────────
def build_stmts(ins, order, s, e, targets, params, labels_at, frame_of, sig, block_off, ret_of):
    """Linear statements for the instructions of one function (pcs in [s, e)). Raises Fail."""
    pcs = [pc for pc in order if s <= pc < e]
    st = [('param', k) for k in range(params)]
    out = []
    subject = []                     # switch subjects (kept off the expression stack)
    sc = {}                          # branch pc -> (land pc, target) for && / ||

    # pre-scan short-circuits: dup; bz|bnz L; ...; land|lor; L:
    idx = {pc: n for n, pc in enumerate(pcs)}
    for n, pc in enumerate(pcs[:-1]):
        i = ins[pc]
        if i['c'] == 0 and i['sub'] == DUP:
            br = ins[pcs[n + 1]]
            if br['c'] in (5, 6):
                t = bd._target(br)
                if t in idx and idx[t] > 0:
                    last = ins[pcs[idx[t] - 1]]
                    want = LAND if br['c'] == 5 else LOR
                    if last['c'] == 1 and last['sub'] == want:
                        sc[pcs[n + 1]] = (last['pos'], t)
    sc_targets = {t for _, t in sc.values()}
    sc_land = {lp for lp, _ in sc.values()}

    def lab(pc):
        return f'@L{pc - block_off:04X}'

    def pop(n, pc):
        if len(st) < n:
            raise Fail(f'stack underflow at {pc - block_off:04X}')
        args = st[len(st) - n:] if n else []
        del st[len(st) - n:]
        return args

    def need_empty():
        # the caller's arguments (params, at the bottom) wait there until the prologue takes them
        keep_from = 0
        while keep_from < len(st) and st[keep_from][0] == 'param':
            keep_from += 1
        for x in st[keep_from:]:
            if x[0] in ('dupload', 'rmwptr'):
                raise Fail('read-modify-write split by a statement')
            out.append(('keep', x))
        del st[keep_from:]

    skip = set()
    for n, pc in enumerate(pcs):
        i = ins[pc]
        c, sub = i['c'], i['sub']
        if pc in targets and pc not in sc_targets:
            need_empty()
            out.append(('label', lab(pc)))
        if pc in skip:
            continue
        if c == 2:
            m = i['op'] & 0x30
            if m == 0x00:
                st.append(('int', bd.i32(bd_data[0], pc + 2)))
            elif m == 0x10:
                st.append(('flt', bd_data[0][pc + 2:pc + 6]))
            elif m == 0x20:
                if i['base'] == 3:
                    st.append(('lea', 3, pc + 2 + i['arg'] - block_off))
                else:
                    st.append(('lea', i['base'], i['arg']))
            else:
                if i['base'] == 3:
                    raise Fail('value read from imm base')
                st.append(('val', i['base'], i['arg'], sub))
        elif c == 9:
            st.append(('idx', pop(1, pc)[0], sub))
        elif c == 0xA:
            p = pop(1, pc)[0]
            if p[0] == 'rmwptr':
                raise Fail('load of a duplicated pointer')
            st.append(('load', p, sub))
        elif c == 1:
            if sub in (LAND, LOR) and pc in sc_land:
                b, a = pop(2, pc)[::-1]
                st.append(('sc', sub, i['mode'], a, b))
            elif sub in ARITH_SYM:
                a, b = pop(2, pc)
                st.append(('bin', sub, i['mode'], a, b))
            else:
                raise Fail(f'arith {sub}')
        elif c == 7:
            if sub not in CMP_SYM:
                raise Fail(f'cmp {sub}')
            st.append(('cmp', sub, i['mode'], pop(1, pc)[0]))
        elif c == 0:
            if sub == DUP:
                nx = [ins[x] for x in pcs[n + 1:n + 4]]
                if nx and nx[0]['c'] in (5, 6) and pcs[n + 1] in sc:
                    continue                           # the && / || test; the branch is skipped too
                if (len(nx) >= 3 and nx[0]['c'] == 2 and (nx[0]['op'] & 0x30) in (0, 0x10)
                        and nx[1]['c'] == 1 and nx[1]['sub'] == 1 and nx[2]['c'] == 6):
                    # switch case test: dup; push k; sub; bnz Lnext
                    if not subject:
                        x = pop(1, pc)[0]
                        need_empty()
                        subject.append(x)
                        out.append(('swbegin', x))
                    elif st:
                        raise Fail('switch subject under other values')
                    k = ('int', bd.i32(bd_data[0], nx[0]['pos'] + 2)) if (nx[0]['op'] & 0x30) == 0 \
                        else ('flt', bd_data[0][nx[0]['pos'] + 2:nx[0]['pos'] + 6])
                    out.append(('swcase', k, nx[1]['mode'], lab(bd._target(nx[2]))))
                    skip.update(pcs[n + 1:n + 4])
                    continue
                if nx and nx[0]['c'] == 0xA:
                    p = pop(1, pc)[0]
                    st.append(('rmwptr', p))
                    st.append(('dupload', p, nx[0]['sub']))
                    skip.add(pcs[n + 1])
                    continue
                raise Fail('dup')
            elif sub == LNOT:
                st.append(('un', LNOT, pop(1, pc)[0]))
            elif sub in UNARY_FN:
                st.append(('un', sub, pop(1, pc)[0]))
            elif sub == POP:
                if not st and subject:
                    subject.pop()
                    out.append(('swend',))
                    continue
                v = pop(1, pc)[0]
                need_empty()
                if v[0] not in ('nat', 'call'):
                    raise Fail('pop of a plain value')
                if v[0] == 'nat' and not bd.ARITY.get((v[1], v[2]), (0, 0))[1]:
                    raise Fail('pop after a void native')
                out.append(('expr', v))
            elif sub == STOREI:
                v, p = pop(2, pc)[::-1]
                need_empty()
                if p[0] == 'rmwptr':
                    if not (v[0] == 'bin' and v[3][0] == 'dupload' and v[3][1] is p[1]):
                        raise Fail('read-modify-write shape')
                    out.append(('rmw', p[1], v[3][2], v[1], v[2], v[4]))
                else:
                    out.append(('storei', p, v))
            elif sub == YIELD:
                need_empty()
                out.append(('yield',))
            elif sub == RET:
                vals = list(st)
                st.clear()
                if any(x[0] in ('dupload', 'rmwptr') for x in vals):
                    raise Fail('return of a duplicated value')
                out.append(('ret', vals))
            elif sub == ABORT:
                need_empty()
                out.append(('abort',))
            else:
                raise Fail(f'unary {sub}')
        elif c == 3:
            if i['base'] == 3:
                raise Fail('store to imm base')
            v = pop(1, pc)[0]
            need_empty()
            out.append(('store', i['base'], i['arg'], v))
        elif c == 4:
            need_empty()
            out.append(('goto', lab(bd._target(i))))
        elif c in (5, 6):
            if pc in sc:
                continue
            v = pop(1, pc)[0]
            need_empty()
            out.append(('ifz' if c == 5 else 'ifnz', v, lab(bd._target(i))))
        elif c == 8:
            t = bd._target(i)
            if frame_of[0] is None:
                frame_of[0] = sub
            elif frame_of[0] != sub:
                raise Fail('call frame sizes differ')
            if t not in sig:
                raise Fail('call to a non-routine')
            p, r = sig[t]
            args = pop(p, pc)
            call = ('call', t, args)
            if r == 1:
                st.append(call)
            elif r == 0:
                need_empty()
                out.append(('expr', call))
            else:
                raise Fail('multi-value return')
        elif c == 0xB:
            key = (i['base'], sub)
            if i['op'] & 0x30:
                raise Fail('native with non-zero mode')
            if key in bd.STUB_VERBS:
                need_empty()
                out.append(('expr', ('nat', i['base'], sub, [])))
                continue
            ar = bd.ARITY.get(key)
            if ar is None:
                raise Fail('native arity unknown')
            call = ('nat', i['base'], sub, pop(ar[0], pc))
            if ar[1]:
                st.append(call)
            else:
                need_empty()
                out.append(('expr', call))
        else:
            raise Fail(f'class {c:#x}')
    if subject:
        raise Fail('switch not closed')
    need_empty()
    return out


bd_data = [b'']                      # the file being decompiled (build_stmts reads immediates from it)


# ─────────────────────────── structuring (exact emitter shapes only) ───────────────────────────
def structure(stmts, refs, end=None):
    """Rewrite goto patterns into if / else-if chains / while / loop / switch. refs = label ->
    reference count. `end` names a label that sits just after these statements (the end of an
    enclosing else-if chain), so a jump to it is a jump to len(stmts)."""
    out = []
    pos = {s[1]: j for j, s in enumerate(stmts) if s[0] == 'label'}
    if end is not None:
        pos.setdefault(end, len(stmts))
    n = len(stmts)

    def internal(label, lo, hi):
        """every reference to `label` comes from stmts[lo:hi] (possibly nested)"""
        return refs.get(label, 0) == count_refs(stmts[lo:hi], label)

    i = 0
    while i < n:
        s = stmts[i]
        if s[0] == 'swbegin':
            m = match_switch(stmts, i, pos, refs)
            if m is None:
                raise Fail('switch shape')
            out.append(m[0])
            i = m[1]
            continue
        # while: Ltop: ifz c Lend; body; goto Ltop; Lend:
        if s[0] == 'label' and refs.get(s[1]) == 1 and i + 1 < n and stmts[i + 1][0] == 'ifz':
            lend = stmts[i + 1][2]
            j = pos.get(lend)
            if (j is not None and i + 1 < j <= n and j < n and refs.get(lend) == 1
                    and stmts[j - 1] == ('goto', s[1])):
                out.append(('while', stmts[i + 1][1], structure(stmts[i + 2:j - 1], refs)))
                i = j + 1
                continue
        # loop: Ltop: body; goto Ltop
        if s[0] == 'label' and refs.get(s[1]) == 1:
            j = next((k for k in range(i + 1, n) if stmts[k] == ('goto', s[1])), None)
            if j is not None and single_entry(stmts, i + 1, j, refs):
                out.append(('loop', structure(stmts[i + 1:j], refs)))
                i = j + 1
                continue
        # if (c) { T } [else { E }]:  ifz c Lx; T; [goto Le; Lx: E;] Lx|Le:
        # if: the compiler's shape is  c; ifz Lelse; T; jmp END; Lelse: [E; jmp END;] END:
        # (the jumps can be no-ops). Node: ('if', c, T, E|None, then_jumps, else_jumps, shares_end)
        # where shares_end marks an `else if` whose jumps go to the enclosing chain's END.
        if s[0] == 'ifz':
            m = match_if(stmts, i, pos, refs, end, n, internal)
            if m is not None:
                out.append(m[0])
                i = m[1]
                continue
        out.append(s)
        i += 1
    return out


def match_if(stmts, i, pos, refs, end, n, internal):
    """-> (if node, index after it) or None for the ifz at stmts[i]."""
    c, lx = stmts[i][1], stmts[i][2]
    j = pos.get(lx)
    if j is None or j <= i:
        return None
    t = stmts[i + 1:j]
    last = t[-1] if t else None
    shared = lx == end                               # this if's labels are the chain end
    # no else: ifz Lx; T; [jmp Lx]; Lx:
    if last == ('goto', lx):
        if (shared or refs.get(lx) == 2) and single_entry(stmts, i + 1, j - 1, refs):
            return ('if', c, structure(t[:-1], refs), None, True, False, shared), (j + 1 if j < n else n)
    if last is not None and last[0] == 'goto' and last[1] != lx and j < n:
        le = last[1]
        k = pos.get(le)
        if (k is not None and k > j and refs.get(lx) == 1 and (le == end or internal(le, i, k))
                and single_entry(stmts, i + 1, j - 1, refs) and single_entry(stmts, j + 1, k, refs, allow={le})):
            e_raw = stmts[j + 1:k]
            e = structure(e_raw, refs, end=le)
            if len(e) == 1 and e[0][0] == 'if' and e[0][6]:
                other, ej = e, False                 # else if: the chained if owns the trailing jump
            elif e_raw and e_raw[-1] == ('goto', le):
                other, ej = structure(e_raw[:-1], refs, end=le), True
            else:
                other, ej = e, False
            if (other is not e or len(e) != 1) and any(x[0] == 'if' and x[6] for x in other):
                return None                          # a chain-end if that isn't written as `else if`
            return ('if', c, structure(t[:-1], refs), other, True, ej, le == end), (k + 1 if k < n else n)
    if shared and j == n and single_entry(stmts, i + 1, j, refs):
        return ('if', c, structure(t, refs), None, False, False, True), n
    if not shared and refs.get(lx) == 1 and j < n and single_entry(stmts, i + 1, j, refs):
        return ('if', c, structure(t, refs), None, False, False, False), j + 1
    return None


def count_refs(stmts, label):
    c = 0
    for t in stmts:
        k = t[0]
        if (k == 'goto' and t[1] == label) or (k in ('ifz', 'ifnz') and t[2] == label):
            c += 1
    return c


def single_entry(stmts, lo, hi, refs, allow=()):
    """no label inside stmts[lo:hi] is jumped to from outside that range"""
    for t in stmts[lo:hi]:
        if t[0] == 'label' and t[1] not in allow and refs.get(t[1], 0) != count_refs(stmts[lo:hi], t[1]):
            return False
    return True


def match_switch(stmts, i, pos, refs):
    """swbegin x; { swcase k Lnext; body; [goto Lend]; Lnext: }* [default]; Lend: swend
    The last case with no default branches straight to Lend and has no goto."""
    x = stmts[i][1]
    end = next((k for k in range(i + 1, len(stmts)) if stmts[k][0] == 'swend'), None)
    if end is None or stmts[end - 1][0] != 'label':
        return None
    lend = stmts[end - 1][1]
    cases = []
    j = i + 1
    while j < end - 1 and stmts[j][0] == 'swcase':
        _, k, mode, lnext = stmts[j]
        if lnext == lend:                       # last case, no default
            body = stmts[j + 1:end - 1]
            if any(t[0] in ('swbegin', 'swcase', 'swend') for t in body):
                return None
            cases.append((k, mode, structure(body, refs)))
            j = end - 1
            break
        p = pos.get(lnext)
        if p is None or p <= j or p >= end or refs.get(lnext) != 1:
            return None
        body = stmts[j + 1:p]
        if not body or body[-1] != ('goto', lend):
            return None
        cases.append((k, mode, structure(body[:-1], refs)))
        j = p + 1
    if not cases:
        return None
    default = stmts[j:end - 1] if j < end - 1 else None
    jumps = sum(1 for t in stmts[i + 1:end - 1] if t == ('goto', lend))
    last_branch = 1 if default is None else 0
    if refs.get(lend, 0) != jumps + last_branch:
        return None
    return ('switch', x, cases, structure(default, refs) if default is not None else None), end + 1


def renumber(stmts):
    order = {}

    def see(name):
        order.setdefault(name, f'L{len(order) + 1}')

    def visit(ss):
        for s in ss:
            if s[0] in ('label', 'goto'):
                see(s[1])
            elif s[0] in ('ifz', 'ifnz'):
                see(s[2])
            elif s[0] == 'if':
                visit(s[2]); visit(s[3] or [])
            elif s[0] in ('while',):
                visit(s[2])
            elif s[0] == 'loop':
                visit(s[1])
            elif s[0] == 'switch':
                for _, _, b in s[2]:
                    visit(b)
                visit(s[3] or [])

    def ren(ss):
        out = []
        for s in ss:
            if s[0] in ('label', 'goto'):
                s = (s[0], order[s[1]])
            elif s[0] in ('ifz', 'ifnz'):
                s = (s[0], s[1], order[s[2]])
            elif s[0] == 'if':
                s = ('if', s[1], ren(s[2]), None if s[3] is None else ren(s[3])) + s[4:]
            elif s[0] == 'while':
                s = ('while', s[1], ren(s[2]))
            elif s[0] == 'loop':
                s = ('loop', ren(s[1]))
            elif s[0] == 'switch':
                s = ('switch', s[1], [(k, m, ren(b)) for k, m, b in s[2]], None if s[3] is None else ren(s[3]))
            out.append(s)
        return out

    visit(stmts)
    return ren(stmts)


# ─────────────────────────── rendering ───────────────────────────
class Names:
    """Names for one block: glob aliases (name <-> glob offset) and routine names."""
    def __init__(self, glob=None, routines=None, self_slot=None):
        self.glob = dict(glob or {})            # offset -> name
        if self_slot is not None:
            self.glob[self_slot] = 'self'
        self.glob_id = {v: k for k, v in self.glob.items()}
        self.routines = dict(routines or {})    # block offset -> name
        self.routine_id = {v: k for k, v in self.routines.items()}


def is_actor(e, names):
    """self, or a .target read through one (field sugar applies to these)."""
    if e == ('val', 1, names.glob_id.get('self', -1), 1):
        return True
    return (e[0] == 'load' and e[2] == 1 and e[1][0] == 'idx' and e[1][2] == ACTOR_FIELDS['target']
            and is_actor(e[1][1], names))


def is_stats(e, names):
    return (e[0] == 'load' and e[2] == 1 and e[1][0] == 'idx' and e[1][2] == ACTOR_FIELDS['stats']
            and is_actor(e[1][1], names))


def field_text(base, n, width, names):
    """Sugar for word n (width words) read from actor/stats `base`, or None."""
    b = expr_text(base, names, False)
    if is_actor(base, names):
        for f, o in VEC_FIELDS.items():
            if n == o and width == 4:
                return f'{b}.{f}'
            if width == 1 and o <= n < o + 4:
                return f'{b}.{f}.{AXES[n - o]}'
        for f, o in ACTOR_FIELDS.items():
            if n == o and width == 1:
                return f'{b}.{f}'
    if is_stats(base, names) and width == 1:
        for f, o in STATS_FIELDS.items():
            if n == o:
                return f'{b}.{f}'
    return None


def postfix(e, names):
    """Text of e usable before [n] / .field (parenthesized unless already postfix-able)."""
    t = expr_text(e, names, False)
    if re.fullmatch(r'[\w.?]+(\[[^\[\]]*\](:\d+)?)*', t):
        return t
    return f'({t})'


def msfx(m):
    return MODE_SFX.get(m, f'm{m}')


def mode_mark(actual, inferred):
    return '' if actual == inferred else '.' + msfx(actual)


def is_zero(e):
    return (e[0] == 'int' and e[1] == 0) or (e[0] == 'flt' and e[1] == b'\0\0\0\0')


def cmp_text(e, names, top):
    """cmp(op, cm, X) is written `A op B` when X = A - B (B not a literal zero), else `X op 0`
    (int compare) / `X op 0.0` (float compare). Modes the reader can't infer get .i/.f."""
    _, op, cm, x = e
    sym = CMP_SYM[op]
    if x[0] == 'bin' and x[1] == 1 and not is_zero(x[4]):
        a, b, sm = x[3], x[4], x[2]
        inf = infer2(a, b)
        if sm == inf and cm == inf:
            t = f'{expr_text(a, names, False)} {sym} {expr_text(b, names, False)}'
        elif sm == cm:
            t = f'{expr_text(a, names, False)} {sym}.{msfx(cm)} {expr_text(b, names, False)}'
        else:
            t = None
        if t is not None:
            return t if top else f'({t})'
    if cm == 0:
        zero = '0'
    elif cm == 1:
        zero = '0.0'
    else:
        raise Fail('compare mode')
    xt = expr_text(x, names, False)
    if x[0] == 'bin' and x[1] == 1 and not xt.startswith('('):
        xt = f'({xt})'
    t = f'{xt} {sym} {zero}'
    return t if top else f'({t})'


def expr_text(e, names, top=True):
    k = e[0]
    if k == 'int':
        return num(e[1])
    if k == 'flt':
        return flt_text(e[1])
    if k == 'param':
        return f'a{e[1]}'
    if k == 'fref':
        return f'@{e[1]}'
    if k == 'val':
        _, base, off, n = e
        t = names.glob[off] if base == 1 and off in names.glob else f'{BASES[base]}[{off}]'
        return t if n == 1 else f'{t}:{n}'
    if k == 'lea':
        _, base, off = e
        if base == 3:
            return f'&data[0x{off:04X}]'
        if base == 1 and off in names.glob:
            return f'&{names.glob[off]}'
        return f'&{BASES[base]}[{off}]'
    if k == 'load':
        p, n = e[1], e[2]
        if p[0] == 'idx':
            f = field_text(p[1], p[2], n, names)
            if f:
                return f
            t = f'{postfix(p[1], names)}[{p[2]}]'
            return t if n == 1 else f'{t}:{n}'
        return f'*{postfix(p, names)}' if n == 1 else f'load({expr_text(p, names)}, {n})'
    if k == 'idx':
        if e[2] in VEC_FIELDS.values():
            f = field_text(e[1], e[2], 4, names)
            if f:
                return f'&{f}'
        return f'&{postfix(e[1], names)}[{e[2]}]'
    if k == 'un':
        if e[1] == LNOT:
            return f'!{postfix(e[2], names)}'
        return f'{UNARY_FN[e[1]]}({expr_text(e[2], names)})'
    if k == 'bin':
        _, sub, mode, a, b = e
        t = f'{expr_text(a, names, False)} {ARITH_SYM[sub]}{mode_mark(mode, infer2(a, b))} {expr_text(b, names, False)}'
        return t if top else f'({t})'
    if k == 'cmp':
        return cmp_text(e, names, top)
    if k == 'sc':
        _, sub, mode, a, b = e
        sym = '&&' if sub == LAND else '||'
        t = f'{expr_text(a, names, False)} {sym}{mode_mark(mode, 0)} {expr_text(b, names, False)}'
        return t if top else f'({t})'
    if k == 'nat':
        _, base, sub, args = e
        nm = NAT_NAME.get((base, sub), f'__t{base}_0x{sub:02x}')
        return f'{nm}({", ".join(expr_text(a, names) for a in args)})'
    if k == 'call':
        return f'{names.routines[e[1]]}({", ".join(expr_text(a, names) for a in e[2])})'
    raise Fail(f'cannot print {k}')


def lhs_ptr_text(p, names):
    """Assignment target for a store through pointer p: E[n] when p = &E[n], else *p."""
    if p[0] == 'idx':
        f = field_text(p[1], p[2], 1, names)
        return f or f'{postfix(p[1], names)}[{p[2]}]'
    return f'*{postfix(p, names)}'


def stmt_lines(stmts, names, ind):
    pad = '    ' * ind
    out = []
    for s in stmts:
        k = s[0]
        if k == 'label':
            out.append(f'{"    " * max(ind - 1, 0)}{s[1]}:')
        elif k == 'store':
            out.append(f'{pad}{expr_text(("val", s[1], s[2], 1), names)} = {expr_text(s[3], names)};')
        elif k == 'storei':
            out.append(f'{pad}{lhs_ptr_text(s[1], names)} = {expr_text(s[2], names)};')
        elif k == 'rmw':
            _, p, n, sub, mode, rhs = s
            lhs = lhs_ptr_text(p, names) if n == 1 else f'load({expr_text(p, names)}, {n})'
            out.append(f'{pad}{lhs} {ARITH_SYM[sub]}={mode_mark(mode, infer2(("load", p, n), rhs))} {expr_text(rhs, names)};')
        elif k == 'expr':
            out.append(f'{pad}{expr_text(s[1], names)};')
        elif k == 'keep':
            out.append(f'{pad}__push({expr_text(s[1], names)});')
        elif k in ('yield', 'abort'):
            out.append(f'{pad}{k};')
        elif k == 'ret':
            vals = ', '.join(expr_text(v, names) for v in s[1])
            out.append(f'{pad}return{" " + vals if vals else ""};')
        elif k == 'goto':
            out.append(f'{pad}goto {s[1]};')
        elif k == 'ifz':
            out.append(f'{pad}if (!{postfix(s[1], names)}) goto {s[2]};')
        elif k == 'ifnz':
            c = expr_text(s[1], names)
            out.append(f'{pad}if ({"(" + c + ")" if c.startswith("!") else c}) goto {s[2]};')
        elif k == 'if':
            nj = lambda f: '' if f else '.nj'
            out.append(f'{pad}if{nj(s[4])} ({expr_text(s[1], names)}) {{')
            out += stmt_lines(s[2], names, ind + 1)
            e, ej = s[3], s[5]
            while e is not None and len(e) == 1 and e[0][0] == 'if' and e[0][6]:
                out.append(f'{pad}}} else if{nj(e[0][4])} ({expr_text(e[0][1], names)}) {{')
                out += stmt_lines(e[0][2], names, ind + 1)
                e, ej = e[0][3], e[0][5]
            if e is not None:
                out.append(f'{pad}}} else{nj(ej)} {{')
                out += stmt_lines(e, names, ind + 1)
            out.append(f'{pad}}}')
        elif k == 'while':
            out.append(f'{pad}while ({expr_text(s[1], names)}) {{')
            out += stmt_lines(s[2], names, ind + 1)
            out.append(f'{pad}}}')
        elif k == 'loop':
            out.append(f'{pad}loop {{')
            out += stmt_lines(s[1], names, ind + 1)
            out.append(f'{pad}}}')
        elif k == 'switch':
            out.append(f'{pad}switch ({expr_text(s[1], names)}) {{')
            for kv, mode, body in s[2]:
                inf = infer(kv)
                out.append(f'{pad}case{mode_mark(mode, DEFAULT_MODE if inf is None else inf)} {expr_text(kv, names)}:')
                out += stmt_lines(body, names, ind + 1)
            if s[3] is not None:
                out.append(f'{pad}default:')
                out += stmt_lines(s[3], names, ind + 1)
            out.append(f'{pad}}}')
        else:
            raise Fail(f'cannot print statement {k}')
    return out


# ─────────────────────────── compiler: tokens and parser ───────────────────────────
MARK = r'(?:\.(?:i|f|m2|m3)\b)?'
TOK = re.compile(
    r'\s*(?://[^\n]*'
    r'|(?P<flt>\d+\.\d*(?:e[+-]?\d+)?|\d+e[+-]?\d+)'
    r'|(?P<num>0x[0-9A-Fa-f]+|\d+)'
    r'|(?P<id>[A-Za-z_][\w]*\??)'
    r'|(?P<op>(?:\|\||&&|==|!=|>=|<=|<<|>>|->|[-+*/%&|^]=)' + MARK + r'|[-+*/%<>&|^]' + MARK +
    r'|[~!(){}\[\];:,=.@])'
    r')')


def tokenize(text):
    toks = []
    p = 0
    text = text.rstrip()
    while p < len(text):
        m = TOK.match(text, p)
        if not m or m.end() == p:
            raise SyntaxError(f'bad token at {text[p:p + 30]!r}')
        p = m.end()
        if m.group('flt'):
            toks.append(('flt', struct.pack('<f', float(m.group('flt')))))
        elif m.group('num'):
            toks.append(('num', int(m.group('num'), 0)))
        elif m.group('id'):
            toks.append(('id', m.group('id')))
        elif m.group('op'):
            toks.append(('op', m.group('op')))
    return toks


def split_mark(op):
    """'<.f' -> ('<', 1); '+' -> ('+', None)"""
    if '.' in op and op not in ('.',):
        base, m = op.split('.', 1)
        return base, {'i': 0, 'f': 1, 'm2': 2, 'm3': 3}[m]
    return op, None


BIN_LEVELS = [('||',), ('&&',), ('|',), ('^',), ('&',), ('==', '!='), ('<', '<=', '>', '>='),
              ('<<', '>>'), ('+', '-'), ('*', '/', '%')]


class Parser:
    def __init__(self, toks, names, funcs):
        self.t = toks
        self.i = 0
        self.names = names            # Names (glob aliases)
        self.funcs = funcs            # routine name -> (label, returns)

    def peek(self, k=0):
        return self.t[self.i + k] if self.i + k < len(self.t) else ('eof', None)

    def take(self, val=None):
        tok = self.peek()
        if val is not None and tok[1] != val:
            raise SyntaxError(f'expected {val!r}, got {tok}')
        self.i += 1
        return tok

    def nj(self):
        """consume a `.nj` mark (a then/else block without the trailing jump to the if's end)"""
        if self.peek()[1] == '.' and self.peek(1)[1] == 'nj':
            self.i += 2
            return True
        return False

    # ---- expressions ----
    def expr(self, level=0):
        if level == len(BIN_LEVELS):
            return self.unary()
        a = self.expr(level + 1)
        while True:
            tok = self.peek()
            if tok[0] != 'op':
                return a
            op, mark = split_mark(tok[1])
            if op not in BIN_LEVELS[level]:
                return a
            self.take()
            b = self.expr(level + 1)
            a = self.binary(op, mark, a, b)

    def binary(self, op, mark, a, b):
        if op in ('&&', '||'):
            return ('sc', LAND if op == '&&' else LOR, 0 if mark is None else mark, a, b)
        if op in CMP_ID:
            if is_zero(b) and b[0] in ('int', 'flt'):
                cm = mark if mark is not None else (0 if b[0] == 'int' else 1)
                return ('cmp', CMP_ID[op], cm, a)
            m = mark if mark is not None else infer2(a, b)
            return ('cmp', CMP_ID[op], m, ('bin', 1, m, a, b))
        m = mark if mark is not None else infer2(a, b)
        return ('bin', ARITH_ID[op], m, a, b)

    def unary(self):
        k, v = self.peek()
        if v == '!':
            self.take()
            return ('un', LNOT, self.unary())
        if v == '-' and self.peek(1)[0] in ('num', 'flt'):
            self.take()
            k2, v2 = self.take()
            if k2 == 'num':
                return ('int', -v2)
            f = struct.unpack('<f', v2)[0]
            return ('flt', struct.pack('<f', -f))
        if v == '*':
            self.take()
            return ('load', self.unary(), 1)
        if v == '&':
            self.take()
            return self.address(self.postfix_expr())
        return self.postfix_expr()

    def address(self, e):
        """&X: lea for a variable, idx for an indexed read (E[n] / E.field)."""
        if e[0] == 'val' and e[3] == 1:
            return ('lea', e[1], e[2])
        if e[0] == 'load' and e[1][0] == 'idx':
            return e[1]
        if e[0] == 'datalea':
            return ('lea', 3, e[1])
        raise SyntaxError(f'cannot take the address of {e}')

    def postfix_expr(self):
        e = self.primary()
        while True:
            v = self.peek()[1]
            if v == '[':
                self.take()
                n = self.take()[1]
                self.take(']')
                w = self.width()
                e = ('load', ('idx', e, n), w or 1)
            elif v == '.' and self.peek(1)[0] == 'id':
                self.take()
                e = self.field(e, self.take()[1])
            else:
                return e

    def width(self):
        if self.peek()[1] == ':' and self.peek(1)[0] == 'num':
            self.take()
            return self.take()[1]
        return None

    def field(self, e, name):
        if name in VEC_FIELDS:
            o = VEC_FIELDS[name]
            if self.peek()[1] == '.' and self.peek(1)[0] == 'id' and self.peek(1)[1] in AXES:
                self.take()
                ax = self.take()[1]
                return ('load', ('idx', e, o + AXES.index(ax)), 1)
            return ('load', ('idx', e, o), 4)
        if name in ACTOR_FIELDS:
            return ('load', ('idx', e, ACTOR_FIELDS[name]), 1)
        if name in STATS_FIELDS:
            return ('load', ('idx', e, STATS_FIELDS[name]), 1)
        raise SyntaxError(f'unknown field .{name}')

    def primary(self):
        k, v = self.take()
        if k == 'num':
            return ('int', v)
        if k == 'flt':
            return ('flt', v)
        if v == '(':
            e = self.expr()
            self.take(')')
            return e
        if v == '@':
            name = self.take()[1]
            if name not in self.funcs:
                raise SyntaxError(f'@{name}: no such function')
            return ('fref', name)
        if k != 'id':
            raise SyntaxError(f'unexpected {v!r}')
        if v in BASE_ID and self.peek()[1] == '[':
            self.take('[')
            sign = -1 if self.peek()[1] == '-' else 1
            if sign < 0:
                self.take()
            off = sign * self.take()[1]
            self.take(']')
            return ('val', BASE_ID[v], off, self.width() or 1)
        if v == 'data' and self.peek()[1] == '[':
            self.take('[')
            off = self.take()[1]
            self.take(']')
            return ('datalea', off)
        if re.fullmatch(r'a\d+', v) and self.peek()[1] != '(':
            return ('param', int(v[1:]))
        if v in self.names.glob_id and self.peek()[1] != '(':
            return ('val', 1, self.names.glob_id[v], self.width() or 1)
        if self.peek()[1] == '(':
            self.take('(')
            args = []
            while self.peek()[1] != ')':
                args.append(self.expr())
                if self.peek()[1] == ',':
                    self.take()
            self.take(')')
            return self.call(v, args)
        raise SyntaxError(f'unknown name {v!r}')

    def call(self, name, args):
        if name in UNARY_FN_ID:
            return ('un', UNARY_FN_ID[name], args[0])
        if name == 'load':
            return ('load', args[0], args[1][1])
        if name == '__f32':
            return ('flt', struct.pack('<I', args[0][1]))
        if name in self.funcs:
            return ('call', name, args)
        m = NAT_RAW_RE.fullmatch(name)
        if m:
            return ('nat', int(m.group(1)), int(m.group(2), 16), args)
        if name in NAT_ID:
            b, s = NAT_ID[name]
            return ('nat', b, s, args)
        raise SyntaxError(f'unknown function {name!r}')

    # ---- statements ----
    def block(self):
        self.take('{')
        out = []
        while self.peek()[1] != '}':
            out.append(self.stmt())
        self.take('}')
        return out

    def stmts_until(self, stops):
        out = []
        while self.peek()[0] != 'eof' and self.peek()[1] not in stops:
            out.append(self.stmt())
        return out

    def stmt(self):
        k, v = self.peek()
        if k == 'id' and self.peek(1)[1] == ':' and v not in ('default',):
            self.i += 2
            return ('label', v)
        if v == 'if':
            self.take()
            tj = not self.nj()
            self.take('(')
            if self.peek()[1] == '!':
                save = self.i
                self.take()
                c = self.unary()
                if self.peek()[1] == ')' and self.peek(1)[1] == 'goto':
                    self.take(')'); self.take('goto'); lbl = self.take()[1]; self.take(';')
                    return ('ifz', c, lbl)
                self.i = save
            c = self.expr()
            self.take(')')
            if self.peek()[1] == 'goto':
                self.take(); lbl = self.take()[1]; self.take(';')
                return ('ifnz', c, lbl)
            then = self.block()
            other, ej = None, False
            if self.peek()[1] == 'else':
                self.take()
                if self.peek()[1] == 'if':
                    child = self.stmt()
                    other = [child[:6] + (True,)]     # else if: shares this chain's end
                else:
                    ej = not self.nj()
                    other = self.block()
            return ('if', c, then, other, tj, ej, False)
        if v == 'while':
            self.take(); self.take('('); c = self.expr(); self.take(')')
            return ('while', c, self.block())
        if v == 'loop':
            self.take()
            return ('loop', self.block())
        if v == 'switch':
            self.take(); self.take('('); x = self.expr(); self.take(')'); self.take('{')
            cases, default = [], None
            while self.peek()[1] != '}':
                t = self.take()[1]
                if t.startswith('case'):
                    mark = None
                    if self.peek()[1] == '.':
                        self.take(); mark = {'i': 0, 'f': 1}[self.take()[1]]
                    kv = self.unary()
                    self.take(':')
                    body = self.stmts_until(('case', 'default', '}'))
                    inf = infer(kv)
                    cases.append((kv, mark if mark is not None else (DEFAULT_MODE if inf is None else inf), body))
                elif t == 'default':
                    self.take(':')
                    default = self.stmts_until(('case', 'default', '}'))
                else:
                    raise SyntaxError(f'expected case/default, got {t!r}')
            self.take('}')
            return ('switch', x, cases, default)
        if v == 'goto':
            self.take(); lbl = self.take()[1]; self.take(';')
            return ('goto', lbl)
        if v in ('yield', 'abort'):
            self.take(); self.take(';')
            return (v,)
        if v == 'return':
            self.take()
            vals = []
            while self.peek()[1] != ';':
                vals.append(self.expr())
                if self.peek()[1] == ',':
                    self.take()
            self.take(';')
            return ('ret', vals)
        if v == '__push':
            self.take(); self.take('('); e = self.expr(); self.take(')'); self.take(';')
            return ('keep', e)
        lhs = self.expr()
        tok = self.peek()
        if tok[1] == '=':
            self.take()
            rhs = self.expr()
            self.take(';')
            return self.assign(lhs, rhs)
        if tok[0] == 'op' and split_mark(tok[1])[0].endswith('=') and split_mark(tok[1])[0] not in ('==', '!=', '<=', '>='):
            op, mark = split_mark(self.take()[1])
            rhs = self.expr()
            self.take(';')
            if lhs[0] != 'load':
                raise SyntaxError('compound assignment needs a pointer target')
            p, n = lhs[1], lhs[2]
            m = mark if mark is not None else infer2(lhs, rhs)
            return ('rmw', p, n, ARITH_ID[op[:-1]], m, rhs)
        self.take(';')
        return ('expr', lhs)

    def assign(self, lhs, rhs):
        if lhs[0] == 'val' and lhs[3] == 1:
            return ('store', lhs[1], lhs[2], rhs)
        if lhs[0] == 'load' and lhs[2] == 1:
            return ('storei', lhs[1], rhs)
        raise SyntaxError(f'cannot assign to {lhs}')


# ─────────────────────────── compiler: emitter ───────────────────────────
def _len(cls, fields):
    if cls == 2:
        return 6 if fields['mode'] in (0, 1) else 4
    return 4 if cls in (3, 4, 5, 6, 8) else 2


def compose(cls, fields, prev):
    """Opcode word: the given fields, everything else repeated from the previous opcode."""
    op = prev & 0xFFF0
    if 'mode' in fields:
        op = (op & ~0x30) | (fields['mode'] << 4)
    if 'base' in fields:
        op = (op & ~0xC0) | (fields['base'] << 6)
    if 'sub' in fields:
        op = (op & 0x00FF) | (fields['sub'] << 8)
    return op | cls


class Emitter:
    def __init__(self, block_code_off):
        self.items = []               # ('ins', cls, fields, kind, val, exact_op) | ('label', name) | ('raw', b) | ('seed', op)
        self.code_off = block_code_off
        self.n = 0
        self.scope = ''
        self.funcs = {}               # routine name -> (label, returns)

    def fresh(self):
        self.n += 1
        return f'__c{self.n}'

    def ins(self, cls, fields, kind=None, val=None, exact=None):
        self.items.append(('ins', cls, fields, kind, val, exact))

    def label(self, name):
        self.items.append(('label', name))

    def local(self, name):
        return self.scope + name

    # ---- expressions ----
    def expr(self, e):
        k = e[0]
        if k == 'int':
            self.ins(2, {'mode': 0}, 'imm', struct.pack('<i', e[1]))
        elif k == 'fref':
            self.ins(2, {'mode': 0}, 'fref', self.funcs[e[1]][0])
        elif k == 'flt':
            self.ins(2, {'mode': 1}, 'imm', e[1])
        elif k == 'val':
            self.ins(2, {'mode': 3, 'base': e[1], 'sub': e[3]}, 'off', e[2])
        elif k == 'lea':
            if e[1] == 3:
                self.ins(2, {'mode': 2, 'base': 3, 'sub': 0}, 'data', e[2])
            else:
                self.ins(2, {'mode': 2, 'base': e[1], 'sub': 0}, 'off', e[2])
        elif k == 'param':
            pass                                   # already on the stack
        elif k == 'idx':
            self.expr(e[1]); self.ins(9, {'sub': e[2]})
        elif k == 'load':
            self.expr(e[1]); self.ins(0xA, {'sub': e[2]})
        elif k == 'un':
            self.expr(e[2]); self.ins(0, {'sub': e[1]})
        elif k == 'bin':
            self.expr(e[3]); self.expr(e[4]); self.ins(1, {'sub': e[1], 'mode': e[2]})
        elif k == 'cmp':
            self.expr(e[3]); self.ins(7, {'sub': e[1], 'mode': e[2]})
        elif k == 'sc':
            end = self.fresh()
            self.expr(e[3])
            self.ins(0, {'sub': DUP})
            self.ins(5 if e[1] == LAND else 6, {}, 'rel', end)
            self.expr(e[4])
            self.ins(1, {'sub': e[1], 'mode': e[2]})
            self.label(end)
        elif k == 'nat':
            if (e[1], e[2]) in bd.STUB_VERBS and not e[3]:
                self.ins(0xB, {'base': e[1], 'sub': e[2], 'mode': 0})
                return
            for a in e[3]:
                self.expr(a)
            self.ins(0xB, {'base': e[1], 'sub': e[2], 'mode': 0})
        elif k == 'call':
            for a in e[2]:
                self.expr(a)
            label, _ = self.funcs[e[1]]
            self.ins(8, {'sub': self.frame}, 'rel', label)
        else:
            raise ValueError(f'cannot emit {k}')

    def returns(self, e):
        if e[0] == 'nat':
            if (e[1], e[2]) in bd.STUB_VERBS and not e[3]:
                return False
            return bool(bd.ARITY.get((e[1], e[2]), (0, 0))[1])
        if e[0] == 'call':
            return self.funcs[e[1]][1] > 0
        return True

    # ---- statements ----
    def stmts(self, ss, chain_end=None):
        for s in ss:
            self.stmt(s)

    def stmt(self, s, chain_end=None):
        k = s[0]
        if k == 'label':
            self.label(self.local(s[1]))
        elif k == 'store':
            self.expr(s[3]); self.ins(3, {'base': s[1]}, 'off', s[2])
        elif k == 'storei':
            self.expr(s[1]); self.expr(s[2]); self.ins(0, {'sub': STOREI})
        elif k == 'rmw':
            _, p, n, sub, mode, rhs = s
            self.expr(p); self.ins(0, {'sub': DUP}); self.ins(0xA, {'sub': n})
            self.expr(rhs); self.ins(1, {'sub': sub, 'mode': mode}); self.ins(0, {'sub': STOREI})
        elif k == 'expr':
            self.expr(s[1])
            if self.returns(s[1]):
                self.ins(0, {'sub': POP})
        elif k == 'keep':
            self.expr(s[1])
        elif k == 'yield':
            self.ins(0, {'sub': YIELD})
        elif k == 'abort':
            self.ins(0, {'sub': ABORT})
        elif k == 'ret':
            for v in s[1]:
                self.expr(v)
            self.ins(0, {'sub': RET})
        elif k == 'goto':
            self.ins(4, {}, 'rel', self.local(s[1]))
        elif k in ('ifz', 'ifnz'):
            self.expr(s[1]); self.ins(5 if k == 'ifz' else 6, {}, 'rel', self.local(s[2]))
        elif k == 'if':
            self.emit_if(s, chain_end)
        elif k == 'while':
            top, end = self.fresh(), self.fresh()
            self.label(top); self.expr(s[1]); self.ins(5, {}, 'rel', end)
            self.stmts(s[2]); self.ins(4, {}, 'rel', top); self.label(end)
        elif k == 'loop':
            top = self.fresh()
            self.label(top); self.stmts(s[1]); self.ins(4, {}, 'rel', top)
        elif k == 'switch':
            _, x, cases, default = s
            end = self.fresh()
            self.expr(x)
            for n, (kv, mode, body) in enumerate(cases):
                last = n == len(cases) - 1 and default is None
                nxt = end if last else self.fresh()
                self.ins(0, {'sub': DUP}); self.expr(kv); self.ins(1, {'sub': 1, 'mode': mode})
                self.ins(6, {}, 'rel', nxt)
                self.stmts(body)
                if not last:
                    self.ins(4, {}, 'rel', end)
                    self.label(nxt)
            if default is not None:
                self.stmts(default)
            self.label(end)
            self.ins(0, {'sub': POP})
        else:
            raise ValueError(f'cannot emit statement {k}')

    def emit_if(self, s, chain_end=None):
        """c; ifz Lelse; T; [jmp END;] Lelse: [E; [jmp END;]] END:  (no else: Lelse is END).
        An `else if` (shared) jumps to the enclosing chain's END and doesn't place it."""
        _, c, then, other, tj, ej, shared = s
        end = chain_end if shared else self.fresh()
        lelse = end if other is None else self.fresh()
        self.expr(c); self.ins(5, {}, 'rel', lelse); self.stmts(then)
        if tj:
            self.ins(4, {}, 'rel', end)
        if other is not None:
            self.label(lelse)
            if len(other) == 1 and other[0][0] == 'if' and other[0][6]:
                self.emit_if(other[0], end)
            else:
                self.stmts(other)
                if ej:
                    self.ins(4, {}, 'rel', end)
        if not shared:
            self.label(end)

    # ---- asm / data / output ----
    def asm_line(self, line):
        m = re.match(r'^\s*(@L-?[0-9A-Fa-f]+):\s*$', line)
        if m:
            self.label(m.group(1).upper().replace('@L', '@L'))
            return
        exact = None
        mo = re.search(r'\s~(0x[0-9A-Fa-f]{4})\s*$', line)
        if mo:
            exact = int(mo.group(1), 16)
            line = line[:mo.start()]
        parts = line.strip().split(None, 1)
        mnem, oper = parts[0], (parts[1].strip() if len(parts) > 1 else '')
        cls, fields, kind, val = bdasm.meaning(mnem, oper, 0)
        if kind == 'data':
            pass
        self.ins(cls, fields, kind, val, exact)

    def bytes(self, first_prev=0):
        # pass 1: layout
        pos = self.code_off
        labels = {}
        for it in self.items:
            if it[0] == 'label':
                labels[it[1]] = pos
            elif it[0] == 'ins':
                pos += bdasm._length(it[1], it[2]) if 'raw' in it[2] else _len(it[1], it[2])
            elif it[0] == 'raw':
                pos += len(it[1])
        out = bytearray()
        pos = self.code_off
        prev = first_prev
        self.spans = []                    # [(start, end)] of each part, in order
        for it in self.items:
            if it[0] == 'part':
                if self.spans:
                    self.spans[-1] = (self.spans[-1][0], pos)
                self.spans.append((pos, None))
                continue
            if it[0] == 'seed':
                prev = it[1]
                continue
            if it[0] == 'label':
                continue
            if it[0] == 'raw':
                out += it[1]
                pos += len(it[1])
                continue
            _, cls, fields, kind, val, exact = it
            if 'raw' in fields:
                op = fields['raw']
                L = bd.ilen(op)
            else:
                op = exact if exact is not None else compose(cls, fields, prev)
                L = _len(cls, fields)
            b = struct.pack('<H', op)
            if kind == 'imm':
                b += val
            elif kind == 'fref':
                b += struct.pack('<i', labels[val] // 2)
            elif kind == 'off':
                b += struct.pack('<h', val)
            elif kind == 'data':
                b += struct.pack('<h', val - (pos + 2))
            elif kind == 'rel':
                if val in labels:
                    tgt = labels[val]
                elif re.fullmatch(r'@L-?[0-9A-Fa-f]+', val):
                    tgt = int(val[2:], 16)
                elif '.' in val:                          # a function's own label: blame that function
                    raise PartError(val.split('.')[0], ValueError(f'unknown label {val}'))
                else:
                    raise ValueError(f'unknown label {val}')
                b += struct.pack('<h', (tgt - (pos + 4)) // 2)
            if len(b) != L:
                raise ValueError(f'encoded {len(b)} bytes, expected {L}')
            out += b
            pos += L
            prev = op
        if self.spans:
            self.spans[-1] = (self.spans[-1][0], pos)
        return bytes(out)


# ─────────────────────────── blocks: decompile ───────────────────────────
NAMES_DIR = HERE.parent / 'names'


def load_names(block_name):
    """names/<block>.json: {"glob": {"840": "encounter"}, "routines": {"@L1BF4": "break_floor_hole"}}"""
    p = NAMES_DIR / f'{block_name}.json'
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def fields_of(i):
    """(cls, canonical fields) of a decoded instruction, as the emitter would give them."""
    c = i['c']
    if c == 0:
        return c, {'sub': i['sub']}
    if c in (1, 7):
        return c, {'sub': i['sub'], 'mode': i['mode']}
    if c == 2:
        m = i['mode']
        if m in (0, 1):
            return c, {'mode': m}
        if m == 2:
            return c, {'mode': 2, 'base': i['base'], 'sub': 0}
        return c, {'mode': 3, 'base': i['base'], 'sub': i['sub']}
    if c == 3:
        return c, {'base': i['base']}
    if c in (4, 5, 6):
        return c, {}
    if c in (8, 9, 0xA):
        return c, {'sub': i['sub']}
    if c == 0xB:
        return c, {'base': i['base'], 'sub': i['sub'], 'mode': 0}
    return c, {'raw': i['op']}


def asm_listing(data, block_off, name, size):
    """{pc: (mnemonic, operand)} from kh1_bd_disasm's raw view (with [glob+N], not [self])."""
    roles = bd.detect_roles(data, block_off, name, size)
    text = bd.disasm(data, block_off, name, size)
    out = {}
    for ln in text.splitlines():
        m = re.match(r'^\s+([0-9A-F]{4})\s{2}(?:[0-9a-f]{2} )+\s*(\S+)\s*(.*?)\s*(?:;.*)?$', ln)
        if m:
            oper = m.group(3)
            if roles.get('self') is not None:
                oper = oper.replace('[self]', f'[glob+{roles["self"]}]')
            out[int(m.group(1), 16) + block_off] = (m.group(2), oper)
    return out


def block_parts(data, block_off, name, size):
    end = min(block_off + 4 + size, len(data))
    start = bd.code_start(data, block_off, name, end)
    end = bd.extend_end(data, block_off, start, end)
    ins, order = bd._decode(data, start, end)
    sig, ana, calls = bd._signatures(ins, order, start)
    entries = sorted({start} | set(calls))
    parts = []                      # (kind 'func'|'data', lo, hi, entry)
    for n, e in enumerate(entries):
        nxt = entries[n + 1] if n + 1 < len(entries) else end
        reach = [pc for pc in ana[e]['depth'] if e <= pc < nxt]
        if not reach:
            parts.append(('data', e, nxt, None))
            continue
        pcs = [pc for pc in order if e <= pc < nxt]
        last = max(reach)
        k = pcs.index(last) + 1
        while k < len(pcs) and ins[pcs[k]]['op'] != 0 and (
                ins[pcs[k]]['c'] == 4 or (ins[pcs[k]]['c'] == 0 and ins[pcs[k]]['sub'] in (0, 3, 8))):
            k += 1          # dead goto / return scaffolding stays with the function; zero padding is data
        hi = pcs[k] if k < len(pcs) else nxt
        parts.append(('func', e, hi, e))
        if hi < nxt:
            parts.append(('data', hi, nxt, None))
    return start, end, ins, order, sig, ana, entries, parts


STATS = {}                          # fallback reason -> count (filled by decompile_block)
FORCED = []                         # (block, function offset) forced to asm by the round-trip check


def _stat(key):
    key = re.sub(r' at [0-9A-F]{4}', '', key)
    STATS[key] = STATS.get(key, 0) + 1


def decompile_block(data, block_off, name, size, force_asm=None):
    """Text of one .bd block, checked to compile back to exactly the original bytes. Functions
    the decompiler can't express, or whose text doesn't reproduce their bytes, are kept as asm."""
    start, end, ins, order, sig, ana, entries, parts = block_parts(data, block_off, name, size)
    names_file = load_names(name)
    roles = bd.detect_roles(data, block_off, name, size)
    glob = {int(k): v for k, v in names_file.get('glob', {}).items()}
    routines = {e: ('entry' if e == start else f'sub_{e - block_off:04X}') for e in entries}
    for lb, nm in names_file.get('routines', {}).items():
        off = int(lb[2:], 16) + block_off
        if off in routines and IDENT.fullmatch(nm) and nm not in RESERVED:
            routines[off] = nm
    names = Names(glob, routines, roles.get('self'))
    targets = {bd._target(i) for i in ins.values() if i['c'] in (4, 5, 6)}
    bd_data[0] = data
    funcs = {routines[e]: (routines[e], sig.get(e, (0, 0))[1]) for e in entries}
    ctx = dict(data=data, block_off=block_off, start=start, ins=ins, order=order, sig=sig, targets=targets,
               names=names, routines=routines, funcs=funcs,
               listing=asm_listing(data, block_off, name, size))
    force = set(force_asm or ())
    texts = {}                                   # part lo -> lines
    prev_kind = None
    for kind, lo, hi, e in parts:
        seed = None
        if kind == 'func':
            first = ins[e]
            prev = _prev_op(ins, order, e) if prev_kind != 'data' else None
            cls, flds = fields_of(first)
            if prev is None or 'raw' in flds or compose(cls, flds, prev) != first['op']:
                seed = first['op']
        texts[lo] = (kind, lo, hi, e, seed)
        prev_kind = kind
    rendered = {}

    def part_lines(lo):
        kind, lo, hi, e, seed = texts[lo]
        if kind == 'data':
            out = [f'    data {{  // 0x{lo - block_off:04X}-0x{hi - block_off - 1:04X}']
            raw = data[lo:hi]
            out += ['        ' + raw[k:k + 16].hex(' ') for k in range(0, len(raw), 16)]
            return out + ['    }']
        if lo not in force:
            if (lo, 'st') not in rendered:
                rendered[(lo, 'st')] = _structured(ctx, lo, hi, e, seed)
            if rendered[(lo, 'st')] is not None:
                return rendered[(lo, 'st')]
        if (lo, 'asm') not in rendered:
            rendered[(lo, 'asm')] = _asm_part(ctx, lo, hi, e, seed)
        return rendered[(lo, 'asm')]

    want = data[start:end]
    for _ in range(len(parts) + 2):
        body = []
        for kind, lo, hi, e in parts:
            body += part_lines(lo)
        text = _block_text(name, start - block_off, names, body)
        code, span_list = compile_block(text, with_spans=True)
        if code == want:
            return text
        spans = {lo: span_list[n] for n, (kind, lo, hi, e) in enumerate(parts)} if len(span_list) == len(parts) else {}
        spans = {lo: (a_ + block_off, b_ + block_off) for lo, (a_, b_) in spans.items()}
        # every function whose size differs; if all sizes match, every function whose bytes differ
        sizes = {lo: (b - a) for lo, (a, b) in spans.items()}
        wrong = [lo for kind, lo, hi, e in parts if kind == 'func' and sizes.get(lo) != hi - lo]
        if not wrong:
            wrong = [lo for kind, lo, hi, e in parts if kind == 'func'
                     and code[spans[lo][0] - start:spans[lo][1] - start] != data[lo:hi]]
        wrong = [lo for lo in wrong if lo not in force]
        if not wrong:
            raise AssertionError(f'{name}: round trip mismatch that no function explains')
        for lo in wrong:
            force.add(lo)
            _stat('bytes differ'); FORCED.append((name, lo - block_off, rendered.get((lo, 'st')), code[spans[lo][0] - start:spans[lo][1] - start] if lo in spans else None, data[lo:{p[1]: p[2] for p in parts}[lo]]))
    raise AssertionError(f'{name}: round trip did not converge')


IDENT = re.compile(r'[A-Za-z_]\w*')


def _prev_op(ins, order, pc):
    k = order.index(pc)
    return ins[order[k - 1]]['op'] if k > 0 else None


def _structured(ctx, lo, hi, e, seed):
    """Lines of a structured function, or None (-> asm). The text is parsed and emitted on
    its own first, so anything the compiler would reject falls back here."""
    ins, sig, names, routines = ctx['ins'], ctx['sig'], ctx['names'], ctx['routines']
    p_, r_ = sig.get(e, (0, 0))
    try:
        frame = [None]
        st = build_stmts(ins, ctx['order'], lo, hi, ctx['targets'], p_, None, frame, sig, ctx['block_off'], None)
        st = link_frefs(st, routines, ctx['block_off'], ctx['start'])
        refs = {}
        for t in st:
            if t[0] == 'goto':
                refs[t[1]] = refs.get(t[1], 0) + 1
            elif t[0] in ('ifz', 'ifnz'):
                refs[t[2]] = refs.get(t[2], 0) + 1
            elif t[0] == 'swcase':
                refs[t[3]] = refs.get(t[3], 0) + 1
        own = {t[1] for t in st if t[0] == 'label'}
        if any(lb not in own for lb in refs):
            raise Fail('jump out of the function')
        tree = renumber(structure(st, refs))
        params = ', '.join(f'a{k}' for k in range(p_))
        head = f'    func {routines[e]}({params})'
        if r_:
            head += f' -> {r_}'
        if frame[0] is not None:
            head += f' frame {frame[0]}'
        if seed is not None:
            head += f' seed 0x{seed:04x}'
        lines = [head + f' {{  // @L{e - ctx["block_off"]:04X}'] + stmt_lines(tree, names, 2) + ['    }']
        # validate: parse + emit this function alone (its own labels must all resolve)
        em = Emitter(0)
        em.funcs = ctx['funcs']
        em.scope = 'v.'
        em.frame = frame[0] or 0
        for s in Parser(tokenize('\n'.join(lines[1:-1])), names, ctx['funcs']).stmts_until(()):
            em.stmt(s)
        defined = {it[1] for it in em.items if it[0] == 'label'}
        for it in em.items:
            if it[0] == 'ins' and it[3] == 'rel' and it[4] not in defined and it[4].startswith('v.'):
                raise Fail('label lost in structuring')
        return lines
    except Fail as f:
        _stat('fail: ' + str(f)[:50])
    except (SyntaxError, ValueError, KeyError, IndexError, TypeError) as ex:
        _stat(f'text: {type(ex).__name__}: {str(ex)[:50]}')
    return None


def link_frefs(e, routines, block_off, start):
    """Threads and handlers are started with the int offset/2 of a function (StartThread,
    SetEventHandler, often through a helper) or stored into an object as a callback (an attack's
    word 14): an int N >= 10 passed to a call or native or stored through a pointer, where N*2
    starts a function other than the block entry, becomes ('fref', name) so builds relocate it."""
    def ref(a):
        off = block_off + 2 * a[1] if a[0] == 'int' else None
        if off is not None and a[1] >= 10 and off != start and off in routines:
            return ('fref', routines[off])
        return link_frefs(a, routines, block_off, start)

    if isinstance(e, list):
        return [link_frefs(x, routines, block_off, start) for x in e]
    if not isinstance(e, tuple) or not e:
        return e
    if e[0] in ('call', 'nat'):
        return e[:-1] + ([ref(a) for a in e[-1]],)
    if e[0] == 'storei':
        return ('storei', link_frefs(e[1], routines, block_off, start), ref(e[2]))
    return tuple(link_frefs(x, routines, block_off, start) for x in e)


def _asm_part(ctx, lo, hi, e, seed):
    ins, order, block_off = ctx['ins'], ctx['order'], ctx['block_off']
    p_, r_ = ctx['sig'].get(e, (0, 0))
    head = f'    func {ctx["routines"][e]} asm'
    if p_ or r_:
        head += f' ({p_}) -> {r_}'
    if seed is not None:
        head += f' seed 0x{seed:04x}'
    out = [head + f' {{  // @L{e - block_off:04X}']
    prev = seed if seed is not None else _prev_op(ins, order, e)
    for pc in [pc for pc in order if lo <= pc < hi]:
        if pc != e and (pc in ctx['targets'] or pc in ctx['routines']):
            out.append(f'    @L{pc - block_off:04X}:')
        mnem, oper = ctx['listing'][pc]
        oper = _asm_names(oper, ctx['routines'], block_off)
        i = ins[pc]
        cls, flds = fields_of(i)
        exact = '' if 'raw' in flds or compose(cls, flds, prev) == i['op'] else f' ~0x{i["op"]:04x}'
        out.append(f'        {mnem} {oper}{exact}'.rstrip())
        prev = i['op']
    return out + ['    }']


def _block_text(name, code_rel, names, body):
    lines = [f'bd {name} code 0x{code_rel:04X} {{']
    decl = sorted(names.glob.items(), key=lambda kv: kv[1])
    if decl:
        lines += ['    names {'] + [f'        {n} = glob[{o}];' for o, n in decl] + ['    }', '']
    return '\n'.join(lines + body + ['}']) + '\n'


def _asm_names(oper, routines, block_off):
    """call/jump targets that start a routine are written by the routine's name."""
    def sub(m):
        off = int(m.group(1), 16) + block_off
        return routines.get(off, m.group(0))
    return re.sub(r'@L([0-9A-F]{4})\b', sub, oper)


# ─────────────────────────── blocks: compile ───────────────────────────
BLOCK_RE = re.compile(r'^bd (\S+) code (0x[0-9A-Fa-f]+) \{$')
FUNC_RE = re.compile(r'^    func ([A-Za-z_]\w*\??)(?:\((.*?)\))?(?: (asm))?(?: \((\d+)\))?(?: -> (\d+))?'
                     r'(?: frame (\d+))?(?: seed (0x[0-9A-Fa-f]{4}))? \{(?:\s*//.*)?$')


def compile_block(text, with_spans=False):
    """-> (code offset, bytes) for the text of one block (`bd NAME code 0x... { ... }`); with_spans
    -> (bytes, {part: (start, end)}) keyed by each part's position in the file, for the round-trip check."""
    lines = text.rstrip('\n').split('\n')
    m = BLOCK_RE.match(lines[0])
    if not m:
        raise SyntaxError(f'expected "bd NAME code 0x... {{", got {lines[0]!r}')
    code_off = int(m.group(2), 16)
    glob = {}
    i = 1
    if lines[i].strip() == 'names {':
        i += 1
        while lines[i].strip() != '}':
            nm, _, val = lines[i].strip().rstrip(';').partition('=')
            glob[int(re.fullmatch(r'\s*glob\[(-?\d+)\]\s*', val).group(1))] = nm.strip()
            i += 1
        i += 1
    names = Names(glob)
    funcs = {}
    for ln in lines[i:]:
        fm = FUNC_RE.match(ln)
        if fm:
            funcs[fm.group(1)] = (fm.group(1), int(fm.group(5) or 0))
    em = Emitter(code_off)
    em.funcs = funcs
    while i < len(lines):
        ln = lines[i]
        if not ln.strip() or ln == '}':
            i += 1
            continue
        j = i + 1
        while lines[j] != '    }':
            j += 1
        body = lines[i + 1:j]
        em.items.append(('part', len(em.items)))
        if ln.startswith('    data {'):
            em.items.append(('raw', bytes.fromhex(''.join(x.split('//')[0] for x in body).replace(' ', ''))))
        else:
            fm = FUNC_RE.match(ln)
            if not fm:
                raise SyntaxError(f'bad part header {ln!r}')
            name, params, is_asm, _, rets, frame, seed = fm.groups()
            if seed:
                em.items.append(('seed', int(seed, 16)))
            em.label(name)
            if is_asm:
                for b in body:
                    b = b.split(';')[0].rstrip()
                    if not b.strip():
                        continue
                    lm = re.match(r'^\s*(@L-?[0-9A-Fa-f]+):\s*$', b)
                    if lm:
                        em.label(lm.group(1))
                        continue
                    exact = None
                    mo = re.search(r'\s~(0x[0-9A-Fa-f]{4})$', b)
                    if mo:
                        exact = int(mo.group(1), 16)
                        b = b[:mo.start()]
                    mnem, _, oper = b.strip().partition(' ')
                    oper = oper.strip()
                    tgt = None
                    tm = re.match(r'^([A-Za-z_]\w*\??)(\s+locals=\d+)?$', oper)
                    if mnem in ('jmp', 'bz', 'bnz', 'call') and tm and tm.group(1) in funcs:
                        tgt = tm.group(1)
                        oper = '@L0000' + (tm.group(2) or '')
                    cls, fields, kind, val = bdasm.meaning(mnem, oper, 0)
                    if tgt:
                        val = tgt
                    em.ins(cls, fields, kind, val, exact)
            else:
                em.scope = f'{name}.'
                em.frame = int(frame) if frame else 0
                try:
                    stmts = Parser(tokenize('\n'.join(body)), names, funcs).stmts_until(())
                    for s in stmts:
                        em.stmt(s)
                except (SyntaxError, ValueError, KeyError, IndexError, TypeError) as ex:
                    raise PartError(name, ex) from ex
                em.scope = ''
        i = j + 1
    code = em.bytes()
    if with_spans:
        return code, em.spans
    return code_off, code


# ─────────────────────────── files ───────────────────────────
def decompile_file(path, only=None):
    """Every .bd block in an .mdls (or just the one named `only`), each as a `bd NAME { }` block."""
    data = Path(path).read_bytes()
    out = []
    for b, n, s in bd.find_blocks(data):
        if only is not None and only != n:
            continue
        out.append(decompile_block(data, b, n, s))
    return '\n'.join(out)


def split_blocks(text):
    """{block name: block text} for a .bds file."""
    out = {}
    cur = None
    for ln in text.split('\n'):
        m = BLOCK_RE.match(ln)
        if m:
            cur = m.group(1)
            out[cur] = [ln]
        elif cur is not None:
            out[cur].append(ln)
            if ln == '}':
                cur = None
    return {k: '\n'.join(v) + '\n' for k, v in out.items()}


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Decompile the .bd blocks of an .mdls to BDS.')
    ap.add_argument('file')
    ap.add_argument('--block', help='only this block (e.g. tz_3000.bd)')
    ap.add_argument('-o', '--out', help='write here instead of stdout')
    a = ap.parse_args()
    text = decompile_file(a.file, a.block)
    if a.out:
        Path(a.out).write_text(text, encoding='utf-8')
    else:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stdout.write(text)
