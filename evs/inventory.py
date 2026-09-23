"""Count the raw numbers left in decompiled output, by where they appear."""
import re
from collections import Counter
from corpus import load
import lang

ctx = Counter()
sys_args = Counter()


def walk_expr(e, where):
    k = e[0]
    if k == 'const':
        ctx[where] += 1
    elif k == 'mem':
        t = lang.mem_text(e[1], e[2])
        ctx['memory: named' if not re.match(r'(save_data2?|runtime|bit)[.\[]', t) else f'memory: raw {e[1]}'] += 1
    elif k == 'actor':
        ctx['thread ref'] += 1
    elif k == 'bin':
        walk_expr(e[2], 'operand of ' + lang.BINOP.get(e[1], 'alu')); walk_expr(e[3], 'operand of ' + lang.BINOP.get(e[1], 'alu'))
    elif k == 'un':
        walk_expr(e[2], where)
    elif k == 'call':
        for i, a in enumerate(e[2]):
            if a[0] == 'const':
                sys_args[(lang.SYS_NAME.get(e[1], e[1]), i)] += 1
            walk_expr(a, 'syscall arg')
    elif k == 'intr':
        ctx[f'{lang.INTR_NAME[e[1]]} operand'] += 1
        for a in e[3]:
            walk_expr(a, 'intrinsic arg')


def walk(stmts):
    for s in stmts:
        k = s[0]
        if k == 'assign':
            walk_expr(s[1], 'lhs'); walk_expr(s[2], 'assigned value')
        elif k == 'expr':
            walk_expr(s[1], 'stmt')
        elif k == 'task':
            ctx['start/await entry'] += 1
            walk_expr(s[3][0], 'start/await level'); walk_expr(s[3][1], 'start/await thread')
        elif k in ('ifnot',):
            walk_expr(s[1], 'condition')


for st in load():
    ins = lang.decode(st['stream'])
    threads, _ = lang.split_threads(ins)
    targets = {pc + lang.et.sign24(iv) for pc, (oc, iv) in enumerate(ins) if oc in (2, 3)}
    for h, ys in threads:
        starts = [h + 1] + [y + 1 for y in ys[:-1]]
        for s0, y in zip(starts, ys):
            try:
                walk(lang.build_stmts(ins, s0, y, targets))
            except lang.Fail:
                pass

for k, v in ctx.most_common(20):
    print(f'{v:>9}  {k}')
print('\ntop syscall args still numeric:')
for (name, i), v in sys_args.most_common(30):
    print(f'{v:>9}  {name} arg {i}')
