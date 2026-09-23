"""Infer each syscall's stack effect (args popped, values returned) from the vanilla corpus.

Assumes the compiler left the stack empty at every basic-block boundary, with exactly one
value on it before a beqz. Every block then gives one linear equation over the unknown
net effects; blocks with a single unknown solve it, and solving repeats until stable.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import evdl_tool as et
from corpus import load, decode

# net stack effect of opcodes whose behaviour is known
KNOWN = {
    9: +1,              # push
    10: +1, 11: -1,     # load_local, store_local
    12: +1, 13: -1, 14: +1, 15: -1, 16: +1, 17: -1,  # read/write byte/word/dword
    30: +1, 31: -1,     # read_bit, write_bit
    5: 0, 2: 0,         # yield, jmp
}


def var_of(oc, iv):
    """Key for an instruction whose effect is unknown, or None if known."""
    if oc in KNOWN:
        return None
    if oc == 1:
        return ('alu', et.ALU_OPS.get(iv, iv))
    if oc == 3:
        return None
    if oc == 24:
        return ('sys', iv)
    return ('op', et.OPCODES.get(oc, oc))


def effect_known(oc, iv):
    if oc in KNOWN:
        return KNOWN[oc]
    if oc == 1:
        return 0 if iv == 5 else -1   # negate is unary, the rest binary
    if oc == 3:
        return -1
    return None


def blocks(ins):
    """Split a stream into basic blocks: (start, end_exclusive, ends_in_beqz)."""
    n = len(ins)
    leaders = {0}
    prev = None
    for pc, (oc, iv) in enumerate(ins):
        if et.is_sh(pc, oc, iv, prev):
            leaders.add(pc)
            leaders.add(pc + 1)
        if oc in (2, 3):
            t = pc + et.sign24(iv)
            if 0 <= t < n:
                leaders.add(t)
            leaders.add(pc + 1)
        prev = oc
    heads = set()
    prev = None
    for pc, (oc, iv) in enumerate(ins):
        if et.is_sh(pc, oc, iv, prev):
            heads.add(pc)
        prev = oc
    ls = sorted(l for l in leaders if l < n)
    out = []
    for i, s in enumerate(ls):
        e = ls[i + 1] if i + 1 < len(ls) else n
        if s in heads:
            continue
        out.append((s, e, ins[e - 1][0] == 3))
    return out


def equations(streams):
    """Each block -> (Counter of unknown vars, constant from known ops)."""
    eqs = []
    for st in streams:
        ins = decode(st['stream'])
        for s, e, _ in blocks(ins):
            unk = Counter()
            k = 0
            for oc, iv in ins[s:e]:
                v = var_of(oc, iv)
                if v is None:
                    k += effect_known(oc, iv)
                else:
                    unk[v] += 1
            if unk or k:
                eqs.append((unk, k))
    return eqs


# hypotheses the greedy solver cannot find on its own
SEED = {
    ('op', 'push_cond'): +1,    # pushes a reference to actor/script N
    ('op', 'store_reg'): -1,    # switch: pop value into the case register
    ('op', 'cmp_reg_imm'): +1,  # switch: push (reg == N)
    ('op', 'init_call'): -2,    # pops priority and actor
    ('op', 'await_call'): -2,
    ('alu', 'eq'): -1, ('alu', 'add'): -1, ('alu', 'negate'): 0,
    ('sys', 290): 0, ('sys', 291): 0, ('sys', 292): 0,  # Push_actor_coord_X2/Y2/Z2(i)
}


def solve(eqs, rounds=50, sol=None):
    sol = dict(sol or SEED)
    for _ in range(rounds):
        votes = defaultdict(Counter)
        for unk, k in eqs:
            rest = [v for v in unk if v not in sol]
            if len(rest) != 1:
                continue
            v = rest[0]
            total = k + sum(c * sol[u] for u, c in unk.items() if u in sol)
            val = -total / unk[v]
            if val == int(val):
                votes[v][int(val)] += 1
        new = {v: c.most_common(1)[0][0] for v, c in votes.items() if v not in sol}
        if not new:
            break
        sol.update(new)
    return sol


CONSUMERS = {1, 3, 11, 13, 15, 17, 31}  # alu, beqz, store_local, write_*, write_bit


def statement_votes(streams, sol):
    """For the first unsolved syscall in each block, vote for the effect that empties the stack
    right after it (or leaves one value when the next instruction consumes it)."""
    votes = defaultdict(Counter)
    for st in streams:
        ins = decode(st['stream'])
        for s, e, _ in blocks(ins):
            d = 0
            for i in range(s, e):
                oc, iv = ins[i]
                v = var_of(oc, iv)
                if v is None:
                    d += effect_known(oc, iv)
                elif v in sol:
                    d += sol[v]
                else:
                    if v[0] == 'sys' and i + 1 < e:
                        votes[v][-d + (1 if ins[i + 1][0] in CONSUMERS else 0)] += 1
                    break
    return {v: c.most_common(1)[0][0] for v, c in votes.items()}


def check(eqs, sol):
    ok = bad = unsolved = 0
    bad_by_var = Counter()
    for unk, k in eqs:
        if any(v not in sol for v in unk):
            unsolved += 1
            continue
        if k + sum(c * sol[v] for v, c in unk.items()) == 0:
            ok += 1
        else:
            bad += 1
            for v in unk:
                bad_by_var[v] += 1
    return ok, bad, unsolved, bad_by_var


def split_args_returns(streams, sol):
    """Given net effect d, pick (args, returns). returns=0 unless a call is never seen at a
    depth that would leave nothing for its result to be built on."""
    min_depth = {}
    for st in streams:
        ins = decode(st['stream'])
        for s, e, _ in blocks(ins):
            d = 0
            for oc, iv in ins[s:e]:
                if oc == 24:
                    key = ('sys', iv)
                    min_depth[key] = min(min_depth.get(key, 99), d)
                v = var_of(oc, iv)
                if v is None:
                    d += effect_known(oc, iv)
                elif v in sol:
                    d += sol[v]
                else:
                    break
    out = {}
    for v, d in sol.items():
        if v[0] != 'sys':
            continue
        md = min_depth.get(v, 0)
        r = 1 if d > 0 else (0 if md <= -d else 1)
        out[v[1]] = {'args': r - d, 'returns': r, 'min_depth': md}
    return out


def main():
    streams = load()
    eqs = equations(streams)
    sol = solve(eqs)
    for _ in range(5):
        extra = statement_votes(streams, sol)
        if not extra:
            break
        sol.update(extra)
        sol = solve(eqs, sol=sol)
    ok, bad, unsolved, bad_by_var = check(eqs, sol)
    print(f'{len(streams)} streams, {len(eqs)} block equations')
    print(f'consistent {ok}, inconsistent {bad}, unsolved {unsolved}')
    print('non-syscall effects:', {v[1]: d for v, d in sol.items() if v[0] == 'op'})
    used = Counter()
    for st in streams:
        for oc, iv in decode(st['stream']):
            if oc == 24:
                used[iv] += 1
    solved = [s for s in used if ('sys', s) in sol]
    print(f'syscalls used {len(used)}, solved {len(solved)}')
    print('most-inconsistent vars:', bad_by_var.most_common(15))
    print('unsolved by use count:', sorted(((used[s], str(et.SYSCALLS.get(s, s))) for s in used if ('sys', s) not in sol), reverse=True)[:20])
    print('alu effects:', {v[1]: d for v, d in sol.items() if v[0] == 'alu'})
    Path(__file__).with_name('op_effects.json').write_text(json.dumps(
        {f'{v[0]}:{v[1]}': d for v, d in sol.items() if v[0] != 'sys'}, indent=1))
    ar = split_args_returns(streams, sol)
    Path(__file__).with_name('syscall_arity.json').write_text(json.dumps(
        {str(k): {'name': et.SYSCALLS.get(k, f'sys_{k}'), **v, 'uses': used[k]} for k, v in sorted(ar.items())}, indent=1))


if __name__ == '__main__':
    main()
