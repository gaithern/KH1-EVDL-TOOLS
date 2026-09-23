"""EVS: a C-like view of KGR bytecode. decompile(stream) -> text, compile_text(text) -> stream.

A KGR is a list of threads; each thread is an entry-count header followed by that many
entries, each ending in `yield`. EVS shows every thread as a block of entry blocks and leaves
the yields and the count implicit.

Round trip is exact: compile_text(decompile(s)) == s for every stream. A thread the
decompiler cannot express (stack not empty where a statement must start, a branch leaving
its entry) is kept as an asm block, which also round-trips.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import evdl_tool as et

HERE = Path(__file__).parent
ARITY = {int(k): (v['args'], v['returns'])
         for f in ('syscall_arity.json', 'arity_overrides.json')
         for k, v in json.loads((HERE / f).read_text()).items()}

# void syscalls seen with a varying number of arguments; they take the whole pending stack
VARIADIC = {377, 378, 375, 376}  # Make_inoperable, Make_operable, Make_(not_)invincible_actor

LABELS = {k: v for k, v in et._SAVE_DATA_LABELS.items()}
LABEL_VAR = {v: k for k, v in LABELS.items()}
BIT_LABELS = {int(k, 16): v for k, v in json.loads((HERE.parent / 'bit_labels.json').read_text()).items()}
BIT_LABEL_NUM = {v: k for k, v in BIT_LABELS.items()}

_names = {}
for _i, _n in et.SYSCALLS.items():
    _names.setdefault(_n, []).append(_i)
SYS_NAME = {i: (n if len(_names[n]) == 1 else f'sys_{i}') for i, n in et.SYSCALLS.items()}
SYS_ID = {n: i for i, n in SYS_NAME.items()}

BINOP = {0: '+', 1: '-', 2: '*', 3: '/', 4: '%', 6: '==', 7: '>', 8: '>=', 9: '<', 10: '<=',
         11: '!=', 12: '&', 13: '|', 14: '^', 16: '<<'}
UNOP = {5: '-', 15: '~'}
BINFN = {17}  # binary alu ops with no known operator, shown as __aluN(a, b)
BINOP_ID = {v: k for k, v in BINOP.items()}
UNOP_ID = {v: k for k, v in UNOP.items()}

WIDTH = {12: 'byte', 14: 'word', 16: 'dword', 30: 'bit'}
WRITE = {13: 'byte', 15: 'word', 17: 'dword', 31: 'bit'}
READ_OP = {v: k for k, v in WIDTH.items()}
WRITE_OP = {v: k for k, v in WRITE.items()}

# opcodes shown as __name(operand, args...) with (pops, pushes)
INTRINSIC = {6: (1, 0), 7: (0, 1), 8: (0, 0), 25: (2, 0), 26: (0, 1), 27: (0, 1), 28: (0, 1), 29: (0, 1)}
INTR_NAME = {oc: '__' + et.OPCODES[oc] for oc in INTRINSIC}
INTR_ID = {v: k for k, v in INTR_NAME.items()}


class Fail(Exception):
    pass


def num(n):
    return str(n) if n < 10 else f'0x{n:X}'


# ─────────────────────────── memory naming ───────────────────────────
def mem_text(width, var):
    if (width, var) in _MEM_ALIAS:
        return _MEM_ALIAS[(width, var)]
    if width == 'bit':
        return BIT_LABELS.get(var) or f'bit[{num(var)}]'
    if var in LABELS:
        return LABELS[var] if width == 'byte' else f'{LABELS[var]}.{width}'
    return mem_raw(width, var)


def mem_raw(width, var):
    """A memory reference by address only (save_data2.word[0x3C4], bit[0x6AD8])."""
    if width == 'bit':
        return f'bit[{num(var)}]'
    if var < 0x900:
        region, off = 'save_data', var
    elif var < 0xB00:
        region, off = 'runtime', var
    elif var < 0xC80:
        region, off = 'save_data', var - 0x200
    elif var < 0xD40:
        region, off = 'runtime', var
    else:
        region, off = 'save_data2', var - 0xD40
    sfx = '' if width == 'byte' else '.' + width
    return f'{region}{sfx}[{num(off)}]'


def mem_var(region, off):
    if region == 'bit' or region == 'runtime':
        return off
    if region == 'save_data':
        return off if off < 0x900 else off + 0x200
    if region == 'save_data2':
        return off + 0xD40
    raise ValueError(region)


# ─────────────────────────── decompiler ───────────────────────────
def decode(stream):
    return [(stream[i + 3], stream[i] | (stream[i + 1] << 8) | (stream[i + 2] << 16))
            for i in range(0, len(stream) - 3, 4)]


# entry names (see the vault note "EVDL scripting"). init/main hold for every thread; the
# event slots are only named in threads that bind an actor (Set_char_ID in init), since the
# engine dispatches events to the thread whose id matches the entity.
SLOT = {0: 'init', 1: 'main', 3: 'on_action', 4: 'on_hit', 5: 'on_talk', 6: 'on_touch', 7: 'on_lockon'}
EVENT_SLOTS = {3, 4, 5, 6, 7}
SLOT_ID = {v: k for k, v in SLOT.items()}
MIN_ENTRIES = 11  # the compiler always emits slots 0..10
YIELD = 0x10
SET_CHAR_ID = 10


# thread index -> name for the stream being decompiled (set by decompile)
_TNAME = {}
_ENTRY_ALIAS = {}  # (thread index, entry) -> hand-given name
_MEM_ALIAS = {}    # (width, var) -> hand-given name
_LOCAL_ALIAS = {}  # local number -> hand-given name, for the thread being rendered
WARNINGS = []      # names that could not be applied (set by decompile)
IDENT_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
RESERVED = {'thread', 'entry', 'level', 'if', 'else', 'while', 'goto', 'start', 'await', 'messages',
            'switch', 'case', 'default', 'break',
            'yield', 'raw', 'asm', 'bit', 'save_data', 'save_data2', 'runtime'} | set(SLOT.values())


def entity_ident(cid, entities):
    """Identifier for entity id cid: its ARD name, or sora/playerN for party ids not in the table."""
    if cid in entities:
        name = re.sub(r'[^A-Za-z0-9_]', '_', entities[cid]).lower().strip('_')
    elif cid == 0:
        name = 'sora'
    elif cid < 0x10:
        name = f'player{cid}'
    else:
        return None
    if (not re.fullmatch(r'[a-z][a-z0-9_]+', name) or name in RESERVED
            or re.fullmatch(r'(local|sys_|thread_|entry_)\d+', name)):
        return None
    return name


def thread_names(ins, threads, entities):
    """{thread index: name} for threads whose init binds an entity with a constant Set_char_ID."""
    names = {}
    used = set()
    for idx, (h, ys) in enumerate(threads):
        cid = next((ins[pc - 1][1] for pc in range(h + 2, ys[0])
                    if ins[pc] == (24, SET_CHAR_ID) and ins[pc - 1][0] == 9), None)
        base = None if cid is None else entity_ident(cid, entities)
        if not base:
            continue
        name, n = base, 2
        while name in used:
            name, n = f'{base}_{n}', n + 1
        used.add(name)
        names[idx] = name
    return names


# g_WorldNumber -> world, from the exe's world-prefix pointer table (Steam 0x1404dcca0);
# 7 and 14 point at "xx" (unused)
WORLD_PREFIX = {0: 'dh', 1: 'di', 2: 'dc', 3: 'tw', 4: 'aw', 5: 'tz', 6: 'po', 8: 'al', 9: 'lm',
                10: 'nm', 11: 'he', 12: 'pi', 13: 'pp', 15: 'pc', 16: 'ew'}
WORLD_NAME = {0: 'WORLD_DIVE_TO_THE_HEART', 1: 'WORLD_DESTINY_ISLANDS', 2: 'WORLD_DISNEY_CASTLE',
              3: 'WORLD_TRAVERSE_TOWN', 4: 'WORLD_WONDERLAND', 5: 'WORLD_DEEP_JUNGLE',
              6: 'WORLD_100_ACRE_WOOD', 8: 'WORLD_AGRABAH', 9: 'WORLD_ATLANTICA',
              10: 'WORLD_HALLOWEEN_TOWN', 11: 'WORLD_OLYMPUS_COLISEUM', 12: 'WORLD_MONSTRO',
              13: 'WORLD_NEVERLAND', 15: 'WORLD_HOLLOW_BASTION', 16: 'WORLD_END_OF_THE_WORLD'}
MAX_AREA = 0x40


def area_name(prefix, area):
    """Area numbers are 0-based: area N of world tw is room file tw<N+1>."""
    return f'{prefix.upper()}{area + 1:02d}'


def gift_names():
    """{(world number, gift index): GIFT_<WORLD CODE>_<LOCATION>} from the randomizer's locations.lua."""
    import entities
    out = {}
    for (w, g), loc in entities.gift_locations().items():
        slug = re.sub(r'[^A-Z0-9]+', '_', loc.upper().replace("'", '')).strip('_')
        world = WORLD_NAME.get(w, '').replace('WORLD_', '', 1)
        if world and slug.startswith(world + '_'):
            slug = WORLD_PREFIX[w].upper() + slug[len(world):]
        out[(w, g)] = f'GIFT_{slug}'
    return out


def item_const_names():
    """{item id: ITEM_<VANILLA NAME>}; a name shared by several ids gets the id appended."""
    import entities
    raw = {i: 'ITEM_' + re.sub(r'[^A-Z0-9]+', '_', n.upper().replace("'", '')).strip('_')
           for i, n in entities.item_names().items()}
    counts = {}
    for n in raw.values():
        counts[n] = counts.get(n, 0) + 1
    return {i: (n if counts[n] == 1 else f'{n}_{i:X}') for i, n in raw.items()}


GIFT_NAME = gift_names()
ITEM_NAME = item_const_names()
WORLD_ID = {v: k for k, v in WORLD_PREFIX.items()}

# names that resolve to plain numbers in every file
GLOBAL_CONSTS = {v: k for k, v in WORLD_NAME.items()}
GLOBAL_CONSTS.update({name: g for (w, g), name in GIFT_NAME.items()})
GLOBAL_CONSTS.update({name: i for i, name in ITEM_NAME.items()})
GLOBAL_CONSTS.update({area_name(pfx, a): a for pfx in WORLD_PREFIX.values() for a in range(MAX_AREA)})

# syscalls whose first argument is an entity id of the room's set
ENTITY_ARG_SYSCALLS = {SYS_ID[n] for n in (
    'Set_char_ID', 'Display_model', 'Discard_object_data', 'Load_model', 'Message_to_battle_script',
    'Change_appear_flag', 'Transfer_object_SE', 'Delete_save_point')}
GET_WORLD_NUMBER, GET_AREA_NUMBER = SYS_ID['Get_world_number'], SYS_ID['Get_area_number']
MAP_CHANGE_REWRITE_SET = SYS_ID['Start_map_change_rewrite_set']  # (world, area, set, entrance)
GIFT_ARG = {SYS_ID['Get_item_from_gift_table']: 0, SYS_ID['Display_message_from_gift_table']: 1,
            SYS_ID['Scale_window_from_gift']: 1}  # syscall -> index of its gift-table argument
ITEM_ARG_SYSCALLS = {SYS_ID[n] for n in (  # first argument is an item id
    'Change_bag_items', 'Check_bag_item_count', 'Check_bag_item_count_only', 'Check_bag_item_count2',
    'Get_item_type', 'Set_item_number_in_message')}
GIFT_TABLE_ITEM_VAR = 0x1104  # save_data2[0x3C4], the gift index the rando's scripts pass around
TRIGGER_EVENT = SYS_ID['Trigger_event']  # N < 100: KGR N of the set's script; N >= 100: WDT KGR N - 100


def entry_name(k, bound, thread=None):
    if (thread, k) in _ENTRY_ALIAS:
        return _ENTRY_ALIAS[(thread, k)]
    if k in EVENT_SLOTS and not bound:
        return f'entry_{k}'
    return SLOT.get(k, f'entry_{k}')


def split_threads(ins):
    """Walk header -> count yields -> next header. Returns ([(header_pc, [yield pcs])], tail_pc)
    where tail_pc is where parsing stopped (== len(ins) for a clean stream)."""
    threads = []
    pc = 0
    n = len(ins)
    while pc < n:
        oc, cnt = ins[pc]
        if oc != 0 or not 1 <= cnt <= 256:
            break
        ys = []
        q = pc + 1
        while len(ys) < cnt and q < n:
            if ins[q][0] == 5:
                ys.append(q)
            q += 1
        if len(ys) < cnt:
            break
        threads.append((pc, ys))
        pc = q
    return threads, pc


def expr_text(e, top=True):
    k = e[0]
    if k == 'const':
        return const_text(e)
    if k == 'actor':
        return _TNAME.get(e[1]) or f'thread_{e[1]}'
    if k == 'mem':
        return mem_text(e[1], e[2])
    if k == 'local':
        return _LOCAL_ALIAS.get(e[1]) or f'local{e[1]}'
    if k == 'un':
        inner = expr_text(e[2], False)
        return f'{UNOP[e[1]]}{inner}'
    if k == 'bin' and e[1] in BINFN:
        return f'__alu{e[1]}({expr_text(e[2])}, {expr_text(e[3])})'
    if k == 'bin':
        s = f'{expr_text(e[2], False)} {BINOP[e[1]]} {expr_text(e[3], False)}'
        return s if top else f'({s})'
    if k == 'call':
        return f'{SYS_NAME.get(e[1], f"sys_{e[1]}")}({", ".join(expr_text(a) for a in e[2])})'
    if k == 'intr':
        op = const_text(('const', e[2]) + tuple(e[4:5]))
        return f'{INTR_NAME[e[1]]}({", ".join([op] + [expr_text(a) for a in e[3]])})'
    raise ValueError(e)


_ENAME = {}  # entity id -> constant name for the file being decompiled (set by decompile)
_MSGS = {}   # message index -> text of the set's .binl (set by decompile)
DISPLAY_MESSAGE = SYS_ID['Display_message']  # (window, message index into the set's .binl)
NEG_ONE = ('un', 5, ('const', 1))  # "no message" sentinel in local24/local25 message pairs


def quote(text):
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


def unquote(tok):
    return re.sub(r'\\(.)', r'\1', tok[1:-1])


def const_text(e):
    """A constant, by name when its type gives it one."""
    v, t = e[1], (e[2] if len(e) > 2 else None)
    if t == 'world' and v in WORLD_NAME:
        return WORLD_NAME[v]
    if isinstance(t, tuple) and t[0] == 'area' and v < MAX_AREA:
        return area_name(t[1], v)
    if t == 'entity' and v in _ENAME:
        return _ENAME[v]
    if t == 'kgr':
        return str(v)
    if t == 'item' and v in ITEM_NAME:
        return ITEM_NAME[v]
    if isinstance(t, tuple) and t[0] == 'gift' and (t[1], v) in GIFT_NAME:
        return GIFT_NAME[(t[1], v)]
    if t == 'msg':
        if v in _MSGS:
            return f'messages[{num(v)}]={quote(_MSGS[v])}'
        return f'messages[{num(v)}]'
    return num(v)


# memory whose value is a world / an area number (see save_data_labels.json)
TYPED_MEMORY = {('byte', 0xD40): 'world', ('byte', 0xD5C): 'world',  # PREVIOUS_WORLD, CURRENT_WORLD
                ('byte', 0xD41): 'area'}                               # PREVIOUS_AREA (assumes same world)


def value_type(e, world, vars_=None):
    if e[0] == 'mem' and (e[1], e[2]) in TYPED_MEMORY:
        t = TYPED_MEMORY[(e[1], e[2])]
        return ('area', world) if t == 'area' and world else (t if t == 'world' else None)
    if vars_ and e[0] in ('local', 'mem'):
        return vars_.get(e)
    if e[0] == 'call' and e[1] == GET_WORLD_NUMBER:
        return 'world'
    if e[0] == 'call' and e[1] == GET_AREA_NUMBER and world:
        return ('area', world)
    return None


def typed(e, world, entities, vars_=None):
    """Tag constants whose meaning is fixed by where they are used."""
    k = e[0]
    if k == 'bin':
        a, b = typed(e[2], world, entities, vars_), typed(e[3], world, entities, vars_)
        if e[1] in (BINOP_ID['=='], BINOP_ID['!=']):
            ta, tb = value_type(a, world, vars_), value_type(b, world, vars_)
            if ta and b[0] == 'const':
                b = ('const', b[1], ta)
            if tb and a[0] == 'const':
                a = ('const', a[1], tb)
        return ('bin', e[1], a, b)
    if k == 'un':
        return ('un', e[1], typed(e[2], world, entities, vars_))
    if k == 'call':
        args = [typed(x, world, entities, vars_) for x in e[2]]
        if e[1] in ENTITY_ARG_SYSCALLS and args and args[0][0] == 'const' and args[0][1] in entities:
            args[0] = ('const', args[0][1], 'entity')
        if e[1] == DISPLAY_MESSAGE and len(args) == 2:
            a = args[1]
            if a[0] == 'const':
                args[1] = ('const', a[1], 'msg')
            elif a[0] == 'bin' and a[1] == BINOP_ID['+'] and a[2][0] == 'const':  # base index + offset
                args[1] = ('bin', a[1], ('const', a[2][1], 'msg'), a[3])
        if e[1] in ITEM_ARG_SYSCALLS and args and args[0][0] == 'const':
            args[0] = ('const', args[0][1], 'item')
        g = GIFT_ARG.get(e[1])
        if g is not None and len(args) > g and args[g][0] == 'const' and world in WORLD_ID:
            args[g] = ('const', args[g][1], ('gift', WORLD_ID[world]))
        if e[1] == TRIGGER_EVENT and args and args[0][0] == 'const':
            args[0] = ('const', args[0][1], 'kgr')
        if e[1] == MAP_CHANGE_REWRITE_SET and len(args) == 4 and args[0][0] == 'const':
            w = args[0][1]
            args[0] = ('const', w, 'world')
            if args[1][0] == 'const' and w in WORLD_PREFIX:
                args[1] = ('const', args[1][1], ('area', WORLD_PREFIX[w]))
        return ('call', e[1], args)
    if k == 'intr':
        return ('intr', e[1], e[2], [typed(x, world, entities, vars_) for x in e[3]])
    return e


def message_locals(stmts):
    """Locals passed straight to Display_message as the message index."""
    return {s[1][2][1] for s in stmts
            if s[0] == 'expr' and s[1][0] == 'call' and s[1][1] == DISPLAY_MESSAGE
            and len(s[1][2]) == 2 and s[1][2][1][0] == 'local'}


def type_stmts(stmts, world, entities):
    """typed() over a flat statement list. A variable assigned from Get_world_number() or
    Get_area_number() keeps that type until reassigned, and a switch on such a value types
    its case values. Constants assigned to a local that is later shown with Display_message
    are message indexes."""
    msg_locals = message_locals(stmts)
    out = []
    reg = None
    vars_ = {}
    for s in stmts:
        k = s[0]
        if k == 'assign':
            x = typed(s[2], world, entities, vars_)
            t = value_type(x, world, vars_)
            lhs = s[1][:3]
            if t:
                vars_[lhs] = t
            else:
                vars_.pop(lhs, None)
            if s[1] in msg_locals and x[0] == 'const':
                x = ('const', x[1], 'msg')
            if s[1][0] == 'mem' and s[1][2] == GIFT_TABLE_ITEM_VAR and x[0] == 'const' and world in WORLD_ID:
                x = ('const', x[1], ('gift', WORLD_ID[world]))
            s = ('assign', s[1], x)
        elif k == 'expr':
            x = typed(s[1], world, entities, vars_)
            if x[0] == 'intr' and x[1] == 6:  # store_reg
                reg = value_type(x[3][0], world, vars_)
            s = ('expr', x)
        elif k == 'ifnot':
            c = typed(s[1], world, entities, vars_)
            if c[0] == 'intr' and c[1] == 7 and reg:  # cmp_reg_imm
                c = c + (reg,)
            s = ('ifnot', c, s[2])
        elif k == 'task':
            s = ('task', s[1], s[2], [typed(x, world, entities, vars_) for x in s[3]])
        out.append(s)
    return out


def entity_consts(entities):
    """{entity id: CONSTANT_NAME} for a set's entity table, plus party ids 0..9."""
    taken = set(GLOBAL_CONSTS) | set(LABEL_VAR) | set(BIT_LABEL_NUM)
    out = {}
    pool = dict(entities)
    for cid in range(10):
        pool.setdefault(cid, 'SORA' if cid == 0 else f'PLAYER{cid}')
    for cid in sorted(pool):
        base = re.sub(r'[^A-Za-z0-9_]', '_', pool[cid]).upper().strip('_')
        if not re.fullmatch(r'[A-Z][A-Z0-9_]+', base):
            continue
        name, n = base, 2
        while name in taken:
            name, n = f'{base}_{n}', n + 1
        taken.add(name)
        out[cid] = name
    return out


def used_entities(text_parts):
    return sorted({cid for cid, name in _ENAME.items() if re.search(rf'\b{name}\b', text_parts)})


def build_stmts(ins, s, e, targets):
    """Linear statements for pcs [s, e). Raises Fail if the stack model breaks."""
    st = []
    out = []

    def need_empty():
        if st:
            raise Fail(f'stack not empty at {et.OPCODES[ins[pc][0]]} {SYS_NAME.get(ins[pc][1], ins[pc][1]) if ins[pc][0] == 24 else ""}')

    def pop(n):
        if len(st) < n:
            raise Fail(f'stack underflow at {et.OPCODES[ins[pc][0]]} {SYS_NAME.get(ins[pc][1], ins[pc][1]) if ins[pc][0] == 24 else ""}')
        args = st[len(st) - n:] if n else []
        del st[len(st) - n:]
        return args

    for pc in range(s, e):
        if pc in targets and pc != s - 1:
            need_empty()
            out.append(('label', f'L{pc}'))
        oc, iv = ins[pc]
        if oc == 9:
            st.append(('const', iv))
        elif oc == 21:
            st.append(('actor', iv))
        elif oc == 10:
            st.append(('local', iv))
        elif oc in WIDTH:
            st.append(('mem', WIDTH[oc], iv))
        elif oc == 1:
            if iv in BINOP:
                a, b = pop(2)
                st.append(('bin', iv, a, b))
            elif iv in UNOP:
                st.append(('un', iv, pop(1)[0]))
            elif iv in BINFN:
                a, b = pop(2)
                st.append(('bin', iv, a, b))
            else:
                raise Fail(f'alu {iv}')
        elif oc in WRITE or oc == 11:
            v = pop(1)[0]
            need_empty()
            lhs = ('local', iv) if oc == 11 else ('mem', WRITE[oc], iv)
            out.append(('assign', lhs, v))
        elif oc == 24:
            if iv not in ARITY:
                raise Fail(f'syscall {iv} arity unknown')
            a, r = ARITY[iv]
            if iv in VARIADIC and r == 0:
                a = max(a, len(st))
            call = ('call', iv, pop(a))
            if r == 1:
                st.append(call)
            elif r == 0:
                need_empty()
                out.append(('expr', call))
            else:
                raise Fail('multi-return')
        elif oc in (22, 23):
            args = pop(2)
            need_empty()
            out.append(('task', oc, iv, args))
        elif oc in INTRINSIC:
            pops, pushes = INTRINSIC[oc]
            x = ('intr', oc, iv, pop(pops))
            if pushes:
                st.append(x)
            else:
                need_empty()
                out.append(('expr', x))
        elif oc == 5:
            need_empty()
            out.append(('yield', iv))
        elif oc in (2, 3) and pc + et.sign24(iv) not in targets:
            raise Fail('branch out of stream')
        elif oc == 2:
            need_empty()
            out.append(('goto', f'L{pc + et.sign24(iv)}'))
        elif oc == 3:
            c = pop(1)[0]
            need_empty()
            out.append(('ifnot', c, f'L{pc + et.sign24(iv)}'))
        else:  # nop variants
            need_empty()
            out.append(('op', oc, iv))
    need_empty()
    if e in targets:
        out.append(('label', f'L{e}'))
    return out


STORE_REG, CMP_REG_IMM, DEC_REG_IDX = 6, 7, 8
BREAK = '__break'  # jump target meaning "end of the innermost switch"


def case_values(c):
    """Constants a case test compares against: cmp_reg_imm(N), or a left-nested OR of them
    (C's `case A: case B:`). None if c is not a plain case test."""
    if c[0] == 'intr' and c[1] == CMP_REG_IMM and not c[3]:
        return [('const', c[2]) + tuple(c[4:5])]
    if c[0] == 'bin' and c[1] == BINOP_ID['|']:
        left, right = case_values(c[2]), case_values(c[3])
        if left and right and len(right) == 1:
            return left + right
    return None


def switch_end(stmts, i):
    """Index of the dec_reg_idx that closes the store_reg at stmts[i] (they nest like brackets)."""
    depth = 0
    for j in range(i, len(stmts)):
        t = stmts[j]
        if t[0] == 'expr' and t[1][0] == 'intr':
            if t[1][1] == STORE_REG:
                depth += 1
            elif t[1][1] == DEC_REG_IDX:
                depth -= 1
                if depth == 0:
                    return j
    return None


def match_switch(stmts, i, pos, refs):
    """The compiler's switch shape starting at stmts[i] = store_reg(k, x):
        store_reg(k, x)
        { ifnot <case test> goto Lnext; body; Lnext: }*
        default-body
        Lend: dec_reg_idx(0)
    A case body that is not the last must end in a goto (to Lend = C's break, or elsewhere),
    since falling off it would run the next case's test. A jump to Lend anywhere inside the
    switch becomes break. Returns (('switch', k, x, cases, default), index after the end) or None."""
    k, x = stmts[i][1][2], stmts[i][1][3][0]
    d = switch_end(stmts, i)
    if d is None or stmts[d][1][2] != 0 or stmts[d - 1][0] != 'label':
        return None
    lend = stmts[d - 1][1]
    cases = []
    j = i + 1
    while j < d - 1 and stmts[j][0] == 'ifnot' and case_values(stmts[j][1]):
        cond, lnext = stmts[j][1], stmts[j][2]
        p = pos.get(lnext)
        if p is None or p <= j or p > d - 1:
            return None
        body = stmts[j + 1:p]
        last = p == d - 1 or not (p + 1 < d - 1 and stmts[p + 1][0] == 'ifnot' and case_values(stmts[p + 1][1]))
        if not last and not (body and body[-1][0] == 'goto'):
            return None  # would run on into the next case's test: not C's switch
        if lnext != lend and refs.get(lnext) != 1:
            return None
        cases.append([case_values(cond), body])
        if lnext == lend:
            j = d - 1
            break
        j = p + 1
    if not cases:
        return None
    default = stmts[j:d - 1]
    # every reference to Lend must come from inside the switch (they all become breaks)
    inside = stmts[i + 1:d - 1]
    uses = sum(1 for t in inside if t == ('goto', lend) or (t[0] == 'ifnot' and t[2] == lend))
    if refs.get(lend, 0) != uses:
        return None

    def brk(body):
        return [('break',) if t == ('goto', lend) else ('ifnot', t[1], BREAK) if t[0] == 'ifnot' and t[2] == lend else t
                for t in body]

    cases = [(v, structure(brk(b), refs)) for v, b in cases]
    return ('switch', k, x, cases, structure(brk(default), refs) if default else None), d + 1


def structure(stmts, refs):
    """Rewrite goto patterns into switch / if / if-else / while. refs = label -> reference count."""
    out = []
    i = 0
    n = len(stmts)
    pos = {s[1]: j for j, s in enumerate(stmts) if s[0] == 'label'}
    while i < n:
        s = stmts[i]
        if s[0] == 'expr' and s[1][0] == 'intr' and s[1][1] == STORE_REG:
            m = match_switch(stmts, i, pos, refs)
            if m:
                out.append(m[0])
                i = m[1]
                continue
        # while: Ltop: ifnot c goto Lend; body; goto Ltop; Lend:
        if (s[0] == 'label' and refs.get(s[1]) == 1 and i + 1 < n and stmts[i + 1][0] == 'ifnot'):
            lend = stmts[i + 1][2]
            j = pos.get(lend)
            if (j is not None and j > i + 1 and refs.get(lend) == 1
                    and stmts[j - 1] == ('goto', s[1])):
                out.append(('while', stmts[i + 1][1], structure(stmts[i + 2:j - 1], refs)))
                i = j + 1
                continue
        if s[0] == 'ifnot' and refs.get(s[2]) == 1:
            j = pos.get(s[2])
            if j is not None and j > i:
                prev = stmts[j - 1] if j - 1 > i else None
                if prev and prev[0] == 'goto' and refs.get(prev[1]) == 1:
                    k = pos.get(prev[1])
                    if k is not None and k > j:
                        out.append(('if', s[1], structure(stmts[i + 1:j - 1], refs),
                                    structure(stmts[j + 1:k], refs)))
                        i = k + 1
                        continue
                out.append(('if', s[1], structure(stmts[i + 1:j], refs), None))
                i = j + 1
                continue
        out.append(s)
        i += 1
    return out


def renumber_labels(stmts):
    """L1, L2, ... in order of first appearance, so an edit only renames labels in its own entry."""
    order = {}

    def seen(name):
        order.setdefault(name, f'L{len(order) + 1}')

    def visit(ss):
        for s in ss:
            if s[0] in ('label', 'goto'):
                seen(s[1])
            elif s[0] == 'ifnot' and s[2] != BREAK:
                seen(s[2])
            elif s[0] == 'switch':
                for _, b in s[3]:
                    visit(b)
                visit(s[4] or [])
            elif s[0] == 'if':
                visit(s[2]); visit(s[3] or [])
            elif s[0] == 'while':
                visit(s[2])

    def rename(ss):
        out = []
        for s in ss:
            if s[0] in ('label', 'goto'):
                s = (s[0], order[s[1]])
            elif s[0] == 'ifnot' and s[2] != BREAK:
                s = ('ifnot', s[1], order[s[2]])
            elif s[0] == 'switch':
                s = ('switch', s[1], s[2], [(v, rename(b)) for v, b in s[3]], None if s[4] is None else rename(s[4]))
            elif s[0] == 'if':
                s = ('if', s[1], rename(s[2]), None if s[3] is None else rename(s[3]))
            elif s[0] == 'while':
                s = ('while', s[1], rename(s[2]))
            out.append(s)
        return out

    visit(stmts)
    return rename(stmts)


def stmt_lines(stmts, ind, bound=frozenset(), depth=0):
    pad = '    ' * ind
    out = []
    for s in stmts:
        k = s[0]
        if k == 'label':
            out.append(f'{"    " * max(ind - 1, 0)}{s[1]}:')
        elif k == 'assign':
            lhs = expr_text(s[1])
            out.append(f'{pad}{lhs} = {expr_text(s[2])};')
        elif k == 'expr':
            out.append(f'{pad}{expr_text(s[1])};')
        elif k == 'task':
            fn = 'start' if s[1] == 22 else 'await'
            lvl, thr = s[3]
            if thr[0] == 'actor':
                target = f'{expr_text(thr)}.{entry_name(s[2], thr[1] in bound, thr[1])}'
            else:  # thread index computed at run time
                target = f'{expr_text(thr)}, {entry_name(s[2], False)}'
            out.append(f'{pad}{fn}({target}, level={expr_text(lvl)});')
        elif k == 'yield':
            out.append(f'{pad}yield({num(s[1])});')
        elif k == 'goto':
            out.append(f'{pad}goto {s[1]};')
        elif k == 'ifnot' and s[2] == BREAK:
            out.append(f'{pad}if (!{expr_text(s[1], False)}) break;')
        elif k == 'ifnot':
            out.append(f'{pad}if (!{expr_text(s[1], False)}) goto {s[2]};')
        elif k == 'break':
            out.append(f'{pad}break;')
        elif k == 'switch':
            reg = '' if s[1] == depth else f'[{s[1]}]'
            out.append(f'{pad}switch{reg} ({expr_text(s[2])}) {{')
            for vals, body in s[3]:
                out.append(pad + ' '.join(f'case {const_text(v)}:' for v in vals))
                out += stmt_lines(body, ind + 1, bound, depth + 1)
            if s[4] is not None:
                out.append(f'{pad}default:')
                out += stmt_lines(s[4], ind + 1, bound, depth + 1)
            out.append(f'{pad}}}')
        elif k == 'op':
            out.append(f'{pad}__op{s[1]}({num(s[2])});')
        elif k == 'if':
            out.append(f'{pad}if ({expr_text(s[1])}) {{')
            out += stmt_lines(s[2], ind + 1, bound, depth)
            if s[3] is not None:
                out.append(f'{pad}}} else {{')
                out += stmt_lines(s[3], ind + 1, bound, depth)
            out.append(f'{pad}}}')
        elif k == 'while':
            out.append(f'{pad}while ({expr_text(s[1])}) {{')
            out += stmt_lines(s[2], ind + 1, bound, depth)
            out.append(f'{pad}}}')
    return out


ASM_NAME = {}
for _oc, _n in et.OPCODES.items():
    ASM_NAME[_oc] = _n if list(et.OPCODES.values()).count(_n) == 1 else f'op{_oc}'
ASM_ID = {v: k for k, v in ASM_NAME.items()}


def asm_lines(ins, s, e, targets):
    out = []
    for pc in range(s, e):
        if pc in targets:
            out.append(f'L{pc}:')
        oc, iv = ins[pc]
        if oc in (2, 3):
            t = pc + et.sign24(iv)
            op = f'L{t}' if t in targets else num(iv)
        elif oc == 1 and iv in et.ALU_OPS:
            op = et.ALU_OPS[iv]
        elif oc == 24 and iv in SYS_NAME:
            op = SYS_NAME[iv]
        else:
            op = num(iv)
        out.append(f'    {ASM_NAME[oc]} {op}')
    if e in targets:
        out.append(f'L{e}:')
    return out


def parse_mem(text):
    """('mem', width, var) for a memory reference written like runtime.dword[0xA00]."""
    e = Parser(tokenize(text)).expr()
    if e[0] != 'mem':
        raise ValueError(f'{text!r} is not a memory reference')
    return e


def apply_names(names, threads):
    """Load hand-given names for one KGR: {"threads": {idx: name}, "entries": {"idx.entry": name},
    "vars": {"runtime.dword[0xA00]": name}, "locals": {"idx": {"local24": name}}}."""
    global _ENTRY_ALIAS, _MEM_ALIAS
    _ENTRY_ALIAS, _MEM_ALIAS = {}, {}
    local_alias = {}
    taken = set(_TNAME.values()) | RESERVED | set(SYS_ID) | set(LABEL_VAR) | set(GLOBAL_CONSTS)

    def ok(name, what):
        if not IDENT_RE.fullmatch(name) or name in taken:
            WARNINGS.append(f'{what}: {name!r} is not a free identifier')
            return False
        taken.add(name)
        return True

    for t, name in (names.get('threads') or {}).items():
        t = int(t)
        if t >= len(threads):
            WARNINGS.append(f'thread {t} ({name}) does not exist')
        elif ok(name, f'thread {t}'):
            _TNAME[t] = name
    for key, name in (names.get('entries') or {}).items():
        t, _, k = key.partition('.')
        t, k = int(t), int(k)
        if t >= len(threads) or k >= len(threads[t][1]):
            WARNINGS.append(f'entry {key} ({name}) does not exist')
        elif ok(name, f'entry {key}'):
            _ENTRY_ALIAS[(t, k)] = name
    for text, name in (names.get('vars') or {}).items():
        e = parse_mem(text)
        if ok(name, text):
            _MEM_ALIAS[(e[1], e[2])] = name
    for t, locals_ in (names.get('locals') or {}).items():
        for text, name in locals_.items():
            m = re.fullmatch(r'local(\d+)', text)
            if not m or int(t) >= len(threads):
                WARNINGS.append(f'locals of thread {t}: {text!r} ({name}) does not exist')
            elif IDENT_RE.fullmatch(name):
                local_alias.setdefault(int(t), {})[int(m.group(1))] = name
    return local_alias


GLOBAL_NAME_RE = re.compile(r'\b[A-Z][A-Z0-9_]*\b')
STRING_RE = re.compile(r'"(?:[^"\\]|\\.)*"')


def global_value(name):
    """Current value of a tool-defined global name: ('const', v) or ('mem', width, var), else None."""
    if name in GLOBAL_CONSTS:
        return ('const', GLOBAL_CONSTS[name])
    if name in LABEL_VAR:
        return ('mem', 'byte', LABEL_VAR[name])
    if name in BIT_LABEL_NUM:
        return ('mem', 'bit', BIT_LABEL_NUM[name])
    return None


def globals_block(text):
    """`globals { NAME = value; }` for every tool-defined global name used in text (outside strings):
    the file's record of what those names meant when it was written."""
    used = {}
    for name in GLOBAL_NAME_RE.findall(STRING_RE.sub('""', text)):
        if name not in used:
            g = global_value(name)
            if g:
                used[name] = g
    if not used:
        return ''
    order = {'mem': 0, 'const': 1}
    lines = [f'    {n} = {mem_raw(g[1], g[2]) if g[0] == "mem" else num(g[1])};'
             for n, g in sorted(used.items(), key=lambda kv: (order[kv[1][0]], kv[0]))]
    return 'globals {\n' + '\n'.join(lines) + '\n}\n\n'


def parse_globals(lines):
    """{name: ('const', v) | ('mem', width, var)} from a column-0 `globals { }` block."""
    out = {}
    if 'globals {' in lines:
        i = lines.index('globals {') + 1
        while lines[i] != '}':
            name, _, val = lines[i].strip().rstrip(';').partition('=')
            if name.strip():
                out[name.strip()] = Parser(tokenize(val.strip())).expr()
            i += 1
    return out


COMPILE_WARNINGS = []  # declared globals whose value differs from the tool's current tables


def check_globals(decl):
    for name, g in decl.items():
        now = global_value(name)
        if now is not None and now[1:] != g[1:] and not (now[0] == 'mem' and g[0] == 'mem' and now[2] == g[2]):
            shown = lambda x: mem_raw(x[1], x[2]) if x[0] == 'mem' else num(x[1])
            COMPILE_WARNINGS.append(f'{name} is {shown(g)} in this file but {shown(now)} in the current tables '
                                    f'(the file\'s value is used)')


def decompile(stream, stats=None, entities=None, world=None, messages=None, names=None, emit_globals=True):
    """entities: {entity id: ARD name} for the script's set; threads binding one get its name.
    world: the 2-letter prefix of the script's world (types area numbers)."""
    global _TNAME, _ENAME, _MSGS, _LOCAL_ALIAS
    ins = decode(stream)
    targets = {pc + et.sign24(iv) for pc, (oc, iv) in enumerate(ins) if oc in (2, 3)}
    targets = {t for t in targets if 0 <= t <= len(ins)}
    threads, tail = split_threads(ins)

    def bump(key):
        if stats is not None:
            stats[key] = stats.get(key, 0) + 1

    built = []  # (header_pc, yield pcs, {entry: stmts} or None for asm)
    for h, ys in threads:
        starts = [h + 1] + [y + 1 for y in ys[:-1]]
        try:
            if any(ins[y][1] != YIELD for y in ys):
                raise Fail('yield operand')
            if h in targets:
                raise Fail('branch to header')
            entries = {}
            for k, (s0, y) in enumerate(zip(starts, ys)):
                for pc in range(s0, y):
                    oc, iv = ins[pc]
                    if oc in (2, 3) and not s0 <= pc + et.sign24(iv) <= y:
                        raise Fail('branch leaves entry')
                if y > s0 or y in targets:
                    entries[k] = build_stmts(ins, s0, y, targets)
            built.append((h, ys, entries))
        except Fail as f:
            built.append((h, ys, None))
            if stats is not None:
                stats.setdefault('fail', {}).setdefault(str(f), 0)
                stats['fail'][str(f)] += 1

    refs = {}
    for *_, entries in built:
        for body in (entries or {}).values():
            for s_ in body:
                if s_[0] == 'goto':
                    refs[s_[1]] = refs.get(s_[1], 0) + 1
                elif s_[0] == 'ifnot':
                    refs[s_[2]] = refs.get(s_[2], 0) + 1
    # labels referenced from asm blocks must survive structuring
    raw_ranges = [(h + 1, ys[-1] + 1) for h, ys, entries in built if entries is None] + [(tail, len(ins))]
    for s0, e0 in raw_ranges:
        for pc in range(s0, e0):
            oc, iv = ins[pc]
            if oc in (2, 3):
                t = f'L{pc + et.sign24(iv)}'
                refs[t] = refs.get(t, 0) + 2

    bound = {idx for idx, (h, ys, _) in enumerate(built)
             if any(oc == 24 and iv == SET_CHAR_ID for oc, iv in ins[h + 1:ys[0]])}
    _TNAME = thread_names(ins, threads, entities) if entities is not None else {}
    _ENAME = entity_consts(entities) if entities is not None else {}
    _MSGS = messages or {}
    ent_ids = set(_ENAME)
    WARNINGS.clear()
    local_alias = apply_names(names or {}, threads)
    parts = []
    for idx, (h, ys, entries) in enumerate(built):
        cnt = len(ys)
        tname = _TNAME.get(idx, str(idx))
        note = f'  // {idx}' if idx in _TNAME else ''
        if entries is None:
            parts.append(f'thread {tname} [{cnt}] asm {{{note}\n' + '\n'.join(asm_lines(ins, h + 1, ys[-1] + 1, targets)) + '\n}')
            bump('asm')
            continue
        implied = max(MIN_ENTRIES, max(entries, default=-1) + 1)
        if cnt > implied:
            entries.setdefault(cnt - 1, [])
            implied = cnt
        head = f'thread {tname}' if cnt == implied else f'thread {tname} [{cnt}]'
        lines = []
        _LOCAL_ALIAS = local_alias.get(idx, {})
        decl = [f'        {a} = entry_{k};' for (t, k), a in sorted(_ENTRY_ALIAS.items()) if t == idx]
        decl += [f'        {a} = local{n};' for n, a in sorted(_LOCAL_ALIAS.items())]
        if decl:
            lines += ['    names {'] + decl + ['    }']
        for k in sorted(entries):
            lines.append(f'    {entry_name(k, idx in bound, idx)} {{')
            lines += stmt_lines(renumber_labels(structure(type_stmts(entries[k], world, ent_ids), refs)), 2, bound)
            lines.append('    }')
        _LOCAL_ALIAS = {}
        parts.append(f'{head} {{{note}\n' + '\n'.join(lines) + '\n}')
        bump('ok')
    if tail < len(ins):
        parts.append('raw asm {\n' + '\n'.join(asm_lines(ins, tail, len(ins), targets)) + '\n}')
        bump('raw')
    body = '\n\n'.join(parts) + '\n'
    aliases = sorted(_MEM_ALIAS.items(), key=lambda kv: kv[1])
    used = [(k, a) for k, a in aliases if re.search(rf'\b{a}\b', body)]
    if used:
        decl = '\n'.join(f'    {a} = {mem_raw(*k)};' for k, a in used)
        body = f'names {{\n{decl}\n}}\n\n' + body
    used = used_entities(body)
    if used:
        decl = '\n'.join(f'    {_ENAME[c]} = {num(c)};' for c in used)
        body = f'entities {{\n{decl}\n}}\n\n' + body
    if emit_globals:
        body = globals_block(body) + body
    return body


# ─────────────────────────── compiler ───────────────────────────
TOK = re.compile(r'\s*(?://[^\n]*|(0x[0-9A-Fa-f]+|\d+)|([A-Za-z_][\w.]*)|(==|!=|>=|<=|<<|[-+*/%<>&|^~!(){}\[\];:,=])|("(?:[^"\\]|\\.)*"))')


def tokenize(text):
    toks = []
    p = 0
    text = text.rstrip()
    while p < len(text):
        m = TOK.match(text, p)
        if not m or m.end() == p:
            raise SyntaxError(f'bad token at {text[p:p + 20]!r}')
        p = m.end()
        if m.group(1):
            toks.append(('num', int(m.group(1), 0)))
        elif m.group(2):
            toks.append(('id', m.group(2)))
        elif m.group(3):
            toks.append(('op', m.group(3)))
        elif m.group(4):
            toks.append(('str', unquote(m.group(4))))
    return toks


class Parser:
    def __init__(self, toks, names=None, consts=None, messages=None, aliases=None, thread=None, globals_=None):
        self.t = toks
        self.globals = globals_ or {}
        self.names = names or {}
        a = aliases or {}
        self.mem_alias = a.get('mem', {})                   # name -> ('mem', width, var)
        self.entry_alias = a.get('entries', {})             # thread -> {name: entry}
        self.local_alias = a.get('locals', {}).get(thread, {})  # name -> local number
        self.thread = thread
        self.consts = consts or {}
        self.messages = messages  # the set's .binl texts, to check messages[N]="..." against
        self.i = 0

    def peek(self, k=0):
        return self.t[self.i + k] if self.i + k < len(self.t) else ('eof', None)

    def take(self, val=None):
        tok = self.peek()
        if val is not None and tok[1] != val:
            raise SyntaxError(f'expected {val!r}, got {tok}')
        self.i += 1
        return tok

    def stmts(self):
        out = []
        while self.peek()[0] != 'eof' and self.peek()[1] != '}':
            out.append(self.stmt())
        return out

    def entry_ref(self, name=None, thread=None):
        name = name or self.take()[1]
        alias = self.entry_alias.get(self.thread if thread is None else thread, {})
        if name in alias:
            return alias[name]
        m = re.fullmatch(r'entry_(\d+)', name)
        return int(m.group(1)) if m else SLOT_ID[name]

    def thread_ref(self, name):
        m = re.fullmatch(r'thread_(\d+)', name)
        return ('actor', int(m.group(1)) if m else self.names[name])

    def case_body(self):
        out = []
        while self.peek()[1] not in ('case', 'default', '}'):
            out.append(self.stmt())
        return out

    def entries(self):
        out = {}
        if self.peek()[1] == 'names':  # declarations, read up front by compile_text
            while self.take()[1] != '}':
                pass
        while self.peek()[0] != 'eof':
            k = self.entry_ref()
            out[k] = self.block()
        return out

    def block(self):
        self.take('{')
        b = self.stmts()
        self.take('}')
        return b

    def stmt(self):
        k, v = self.peek()
        if k == 'id' and self.peek(1)[1] == ':':
            self.i += 2
            return ('label', v)
        if v == 'if':
            self.take(); self.take('('); c = self.expr(); self.take(')')
            if self.peek()[1] == 'goto':
                # if (!c) goto L is a plain beqz; any other condition is negated first
                self.take(); lbl = self.take()[1]; self.take(';')
                return ('ifnot', c[1], lbl) if c[0] == 'not' else ('ifnot', ('not', c), lbl)
            if self.peek()[1] == 'break':
                self.take(); self.take(';')
                return ('ifnot', c[1], BREAK) if c[0] == 'not' else ('ifnot', ('not', c), BREAK)
            then = self.block()
            other = None
            if self.peek()[1] == 'else':
                self.take()
                other = self.block()
            return ('if', c, then, other)
        if v == 'while':
            self.take(); self.take('('); c = self.expr(); self.take(')')
            return ('while', c, self.block())
        if v == 'switch':
            self.take()
            reg = None
            if self.peek()[1] == '[':
                self.take('['); reg = self.take()[1]; self.take(']')
            self.take('('); x = self.expr(); self.take(')'); self.take('{')
            cases, default = [], None
            while self.peek()[1] != '}':
                if self.take()[1] == 'case':
                    vals = []
                    while True:
                        value = self.expr(); self.take(':')
                        if value[0] != 'const':
                            raise SyntaxError('case value must be a constant')
                        vals.append(value)
                        if self.peek()[1] != 'case':
                            break
                        self.take()
                    cases.append((vals, self.case_body()))
                else:
                    self.take(':')
                    default = self.case_body()
            self.take('}')
            return ('switch', reg, x, cases, default)
        if v == 'break':
            self.take(); self.take(';')
            return ('break',)
        if v == 'goto':
            self.take(); lbl = self.take()[1]; self.take(';')
            return ('goto', lbl)
        if v in ('yield',) or (k == 'id' and v.startswith('__op')):
            self.take(); self.take('('); n = self.take()[1]; self.take(')'); self.take(';')
            return ('yield', n) if v == 'yield' else ('op', int(v[4:]), n)
        if v in ('start', 'await') and self.peek(1)[1] == '(':
            self.take(); self.take('(')
            k0, v0 = self.peek()
            if k0 == 'id' and '.' in v0 and self.peek(1)[1] == ',':  # thread.entry
                self.take()
                tname, _, ename = v0.partition('.')
                thr = self.thread_ref(tname)
                ent = self.entry_ref(ename, thr[1])
            else:  # computed thread: expr, entry
                thr = self.expr(); self.take(',')
                ent = self.entry_ref()
            self.take(','); self.take('level'); self.take('=')
            lvl = self.expr(); self.take(')'); self.take(';')
            return ('task', 22 if v == 'start' else 23, ent, [lvl, thr])
        e = self.expr()
        if self.peek()[1] == '=':
            self.take()
            val = self.expr()
            self.take(';')
            return ('assign', e, val)
        self.take(';')
        return ('expr', e)

    def expr(self):
        a = self.unary()
        if self.peek()[0] == 'op' and self.peek()[1] in BINOP_ID:
            op = BINOP_ID[self.take()[1]]
            b = self.unary()
            return ('bin', op, a, b)
        return a

    def unary(self):
        k, v = self.peek()
        if v == '!':
            self.take()
            return ('not', self.unary())
        if k == 'op' and v in UNOP_ID:
            self.take()
            return ('un', UNOP_ID[v], self.unary())
        return self.primary()

    def args(self):
        self.take('(')
        out = []
        while self.peek()[1] != ')':
            out.append(self.expr())
            if self.peek()[1] == ',':
                self.take()
        self.take(')')
        return out

    def primary(self):
        k, v = self.take()
        if k == 'num':
            return ('const', v)
        if k == 'str':
            return ('newmsg', v)
        if v == 'messages' and self.peek()[1] == '[':
            self.take('[')
            idx = self.take()[1]
            self.take(']')
            if self.peek()[1] == '=' and self.peek(1)[0] == 'str':
                self.take()
                text = self.take()[1]
                have = None if self.messages is None else self.messages.get(idx)
                if self.messages is not None and have != text:
                    raise ValueError(f'messages[{num(idx)}] is {have!r} in the .binl, not {text!r}')
            return ('const', idx)
        if v == '(':
            e = self.expr()
            self.take(')')
            return e
        if k != 'id':
            raise SyntaxError(f'unexpected {v!r}')
        if v.startswith('__alu'):
            a = self.args()
            return ('bin', int(v[5:]), a[0], a[1])
        if re.fullmatch(r'thread_\d+', v):
            return self.thread_ref(v)
        if v in self.names:
            return ('actor', self.names[v])
        gbase, _, gwidth = v.partition('.')
        if gbase in self.globals:
            g = self.globals[gbase]
            if g[0] == 'const' and not gwidth:
                return g
            if g[0] == 'mem':
                return ('mem', 'bit' if g[1] == 'bit' else (gwidth or 'byte'), g[2])
        if v in self.consts:
            return ('const', self.consts[v])
        if v in GLOBAL_CONSTS:
            return ('const', GLOBAL_CONSTS[v])
        if v in self.local_alias:
            return ('local', self.local_alias[v])
        if v in self.mem_alias:
            return self.mem_alias[v]
        if v.startswith('local') and v[5:].isdigit():
            return ('local', int(v[5:]))
        if self.peek()[1] == '(':
            a = self.args()
            if v in INTR_ID:
                return ('intr', INTR_ID[v], a[0][1], a[1:])
            if v.startswith('sys_'):
                return ('call', int(v[4:]), a)
            return ('call', SYS_ID[v], a)
        if self.peek()[1] == '[':
            self.take('[')
            off = self.take()[1]
            self.take(']')
            region, _, width = v.partition('.')
            if region == 'bit':
                return ('mem', 'bit', off)
            return ('mem', width or 'byte', mem_var(region, off))
        if v in BIT_LABEL_NUM:
            return ('mem', 'bit', BIT_LABEL_NUM[v])
        base, _, width = v.partition('.')
        if base in LABEL_VAR and width in ('', 'word', 'dword'):
            return ('mem', width or 'byte', LABEL_VAR[base])
        raise SyntaxError(f'unknown name {v!r}')


class Emitter:
    def __init__(self, messages=None):
        self.messages = messages
        self.code = []      # [opcode, operand or label]
        self.labels = {}
        self.n = 0
        self.scope = ''  # labels in EVS entries are local to their entry
        self.switch_ends = []  # end label of each enclosing switch, innermost last

    def emit(self, oc, iv):
        self.code.append([oc, iv])

    def fresh(self):
        self.n += 1
        return f'__c{self.n}'

    def expr(self, e):
        k = e[0]
        if k == 'const':
            self.emit(9, e[1])
        elif k == 'actor':
            self.emit(21, e[1])
        elif k == 'local':
            self.emit(10, e[1])
        elif k == 'mem':
            self.emit(READ_OP[e[1]], e[2])
        elif k == 'newmsg':  # a message given by its text: its index in the set's table
            if not hasattr(self.messages, 'resolve'):
                raise ValueError(f'"{e[1]}" needs a message store (the set\'s .binl) to compile')
            self.emit(9, self.messages.resolve(e[1]))
        elif k == 'not':  # logical not: x == 0 (the VM has no not opcode)
            self.expr(e[1]); self.emit(9, 0); self.emit(1, BINOP_ID['=='])
        elif k == 'un':
            self.expr(e[2]); self.emit(1, e[1])
        elif k == 'bin':
            self.expr(e[2]); self.expr(e[3]); self.emit(1, e[1])
        elif k == 'call':
            for a in e[2]:
                self.expr(a)
            self.emit(24, e[1])
        elif k == 'intr':
            for a in e[3]:
                self.expr(a)
            self.emit(e[1], e[2])

    def stmts(self, ss):
        for s in ss:
            self.stmt(s)

    def stmt(self, s):
        k = s[0]
        if k == 'label':
            self.labels[self.scope + s[1]] = len(self.code)
        elif k == 'assign':
            self.expr(s[2])
            lhs = s[1]
            if lhs[0] == 'local':
                self.emit(11, lhs[1])
            else:
                self.emit(WRITE_OP[lhs[1]], lhs[2])
        elif k == 'expr':
            self.expr(s[1])
        elif k == 'task':
            for a in s[3]:
                self.expr(a)
            self.emit(s[1], s[2])
        elif k == 'yield':
            self.emit(5, s[1])
        elif k == 'op':
            self.emit(s[1], s[2])
        elif k == 'goto':
            self.emit(2, self.scope + s[1])
        elif k == 'ifnot' and s[2] == BREAK:
            self.expr(s[1]); self.emit(3, self.switch_ends[-1])
        elif k == 'ifnot':
            self.expr(s[1]); self.emit(3, self.scope + s[2])
        elif k == 'break':
            self.emit(2, self.switch_ends[-1])
        elif k == 'switch':
            reg = len(self.switch_ends) if s[1] is None else s[1]
            end = self.fresh()
            self.expr(s[2]); self.emit(STORE_REG, reg)
            self.switch_ends.append(end)
            for vals, body in s[3]:
                nxt = self.fresh()
                self.emit(CMP_REG_IMM, vals[0][1])
                for v in vals[1:]:
                    self.emit(CMP_REG_IMM, v[1]); self.emit(1, BINOP_ID['|'])
                self.emit(3, nxt)
                self.stmts(body)
                self.labels[nxt] = len(self.code)
            self.stmts(s[4] or [])
            self.switch_ends.pop()
            self.labels[end] = len(self.code)
            self.emit(DEC_REG_IDX, 0)
        elif k == 'if':
            end = self.fresh()
            self.expr(s[1])
            if s[3] is None:
                self.emit(3, end)
                self.stmts(s[2])
            else:
                other = self.fresh()
                self.emit(3, other)
                self.stmts(s[2])
                self.emit(2, end)
                self.labels[other] = len(self.code)
                self.stmts(s[3])
            self.labels[end] = len(self.code)
        elif k == 'while':
            top, end = self.fresh(), self.fresh()
            self.labels[top] = len(self.code)
            self.expr(s[1])
            self.emit(3, end)
            self.stmts(s[2])
            self.emit(2, top)
            self.labels[end] = len(self.code)

    def asm(self, lines):
        for ln in lines:
            ln = ln.split(';')[0].strip()
            if not ln:
                continue
            if ln.endswith(':'):
                self.labels[ln[:-1]] = len(self.code)
                continue
            mn, _, op = ln.partition(' ')
            op = op.strip()
            oc = ASM_ID[mn]
            if oc in (2, 3) and op.startswith('L'):
                self.emit(oc, op)
            elif oc == 1 and op in et.ALU_BY_NAME:
                self.emit(1, et.ALU_BY_NAME[op])
            elif oc == 24 and op in SYS_ID:
                self.emit(24, SYS_ID[op])
            else:
                self.emit(oc, int(op, 0))

    def bytes(self):
        out = bytearray()
        for pc, (oc, iv) in enumerate(self.code):
            if isinstance(iv, str):
                iv = (self.labels[iv] - pc) & 0xFFFFFF
            out += et.enc_instr(oc, iv)
        return bytes(out)


HEAD_RE = re.compile(r'^(?:thread (\w+)(?: \[(\d+)\])?|(raw))( asm)? \{(?:\s*//.*)?$')


def compile_text(text, messages=None, file_globals=None):
    em = Emitter(messages)
    lines = text.split('\n')
    glob = dict(file_globals or {})
    own = parse_globals(lines)
    check_globals(own)
    glob.update(own)
    heads = [m for m in map(HEAD_RE.match, lines) if m and not m.group(3)]
    names = {m.group(1): i for i, m in enumerate(heads) if not m.group(1).isdigit()}
    consts = {}
    if 'entities {' in lines:
        i = lines.index('entities {') + 1
        while lines[i] != '}':
            name, _, val = lines[i].strip().rstrip(';').partition('=')
            consts[name.strip()] = int(val.strip(), 0)
            i += 1
    aliases = {'mem': {}, 'entries': {}, 'locals': {}}
    if 'names {' in lines:
        i = lines.index('names {') + 1
        while lines[i] != '}':
            name, _, val = lines[i].strip().rstrip(';').partition('=')
            aliases['mem'][name.strip()] = parse_mem(val.strip())
            i += 1
    t = -1
    for i, line in enumerate(lines):  # thread-level names { alias = entry_N; / alias = localN; }
        if HEAD_RE.match(line) and not HEAD_RE.match(line).group(3):
            t += 1
        elif line == '    names {':
            j = i + 1
            while lines[j] != '    }':
                name, _, val = lines[j].strip().rstrip(';').partition('=')
                name, val = name.strip(), val.strip()
                if val.startswith('entry_'):
                    aliases['entries'].setdefault(t, {})[name] = int(val[6:])
                else:
                    aliases['locals'].setdefault(t, {})[name] = int(val[5:])
                j += 1
    thread_no = -1
    i = 0
    while i < len(lines):
        m = HEAD_RE.match(lines[i])
        if not m:
            i += 1
            continue
        j = i + 1
        while lines[j] != '}':
            j += 1
        body = lines[i + 1:j]
        if not m.group(3):
            thread_no += 1
        if m.group(4):
            if not m.group(3):
                em.emit(0, int(m.group(2)))
            em.asm(body)
        else:
            entries = Parser(tokenize('\n'.join(body)), names, consts, messages, aliases, thread_no, glob).entries()
            cnt = int(m.group(2)) if m.group(2) else max(MIN_ENTRIES, max(entries, default=-1) + 1)
            em.emit(0, cnt)
            for k in range(cnt):
                em.scope = f'{i}.{k}.'
                em.stmts(entries.get(k, []))
                em.emit(5, YIELD)
            em.scope = ''
        i = j + 1
    return em.bytes()


KGR_RE = re.compile(r'^kgr (\d+) \{$')
INDENT = '    '


def decompile_file(path, only=None):
    """Every KGR of a script file (or just KGR `only`), each as a `kgr N { ... }` block."""
    from corpus import load_file
    import entities as ent
    path = Path(path)
    parts = []
    for i, k in enumerate(load_file(path)):
        if only is not None and i != only:
            continue
        msgs = ent.messages_for(path, k)
        txt = decompile(k['stream'], entities=ent.entities_for(path, k), world=ent.world_prefix(path), messages=msgs,
                        names=ent.names_for(path, i), emit_globals=False)
        for w in WARNINGS:
            print(f'warning: {path.name} kgr {i}: {w}', file=sys.stderr)
        if compile_text(txt, msgs) != k['stream']:
            raise AssertionError(f'round trip mismatch in KGR {i}')
        body = '\n'.join(INDENT + line if line else line for line in txt.rstrip('\n').split('\n'))
        parts.append(f'kgr {i} {{\n{body}\n}}')
    text = '\n\n'.join(parts) + '\n'
    return globals_block(text) + text


def compile_file_text(text, messages=None):
    """{kgr index: stream} for text made by decompile_file."""
    out = {}
    lines = text.split('\n')
    file_globals = parse_globals(lines)
    check_globals(file_globals)
    i = 0
    while i < len(lines):
        m = KGR_RE.match(lines[i])
        if not m:
            i += 1
            continue
        j = i + 1
        while lines[j] != '}':
            j += 1
        body = [line[len(INDENT):] if line.startswith(INDENT) else line for line in lines[i + 1:j]]
        out[int(m.group(1))] = compile_text('\n'.join(body), messages, file_globals)
        i = j + 1
    return out


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--kgr', type=int, help='only this KGR (default: all)')
    ap.add_argument('-o', '--out', help='write here instead of stdout')
    a = ap.parse_args()
    text = decompile_file(a.file, a.kgr)
    if a.out:
        Path(a.out).write_text(text, encoding='utf-8')
    else:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stdout.write(text)
