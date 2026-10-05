"""BDS: a C-like, exactly round-trippable view of KH1 enemy behavior bytecode (.bd blocks in xa_*.mdls).
decompile_block(...) -> text and compile_block(text) -> bytes; functions the decompiler can't express
are kept as `asm` listings and unreachable bytes as `data` blocks.
"""
import json
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'asm'))
import kh1_bd_disasm as bd
import kh1_bd_asm as bdasm
from kh1_motion_dict import read_motion_dict

NAMES_DIR = HERE.parent / 'data' / 'names'

CLASS_MISC = 0
CLASS_ARITH = 1
CLASS_PUSH = 2
CLASS_STORE = 3
CLASS_JUMP = 4
CLASS_BRANCH_IF_ZERO = 5
CLASS_BRANCH_IF_NONZERO = 6
CLASS_COMPARE = 7
CLASS_CALL = 8
CLASS_INDEX = 9
CLASS_LOAD = 0xA
CLASS_NATIVE = 0xB
BRANCH_CLASSES = (CLASS_BRANCH_IF_ZERO, CLASS_BRANCH_IF_NONZERO)
JUMP_CLASSES = (CLASS_JUMP, CLASS_BRANCH_IF_ZERO, CLASS_BRANCH_IF_NONZERO)
FOUR_BYTE_CLASSES = (CLASS_STORE, CLASS_JUMP, CLASS_BRANCH_IF_ZERO, CLASS_BRANCH_IF_NONZERO, CLASS_CALL)

PUSH_INT = 0
PUSH_FLOAT = 1
PUSH_ADDRESS = 2
PUSH_VALUE = 3
IMMEDIATE_PUSH_MODES = (PUSH_INT, PUSH_FLOAT)

MODE_INT = 0
MODE_FLOAT = 1
DEFAULT_MODE = MODE_FLOAT
MODE_SUFFIX = {MODE_INT: 'i', MODE_FLOAT: 'f'}
MARK_MODE = {'i': 0, 'f': 1, 'm2': 2, 'm3': 3}

INHERITED_OPCODE_BITS = 0xFFF0
MODE_BITS, MODE_SHIFT = 0x0030, 4
BASE_BITS, BASE_SHIFT = 0x00C0, 6
SUB_BITS, SUB_SHIFT = 0xFF00, 8

BASE_GLOB = 1
BASE_DATA = 3
BASE_NAMES = {0: 'loc', 1: 'glob', 2: 'heap'}
BASE_IDS = {name: base for base, name in BASE_NAMES.items()}

YIELD = 0
RETURN = 3
POP = 4
STORE_INDIRECT = 7
ABORT = 8
DUPLICATE = 12
LOGICAL_NOT = 13
SCAFFOLDING_MISC_OPS = (YIELD, RETURN, ABORT)

SUBTRACT = 1
LOGICAL_AND = 10
LOGICAL_OR = 11
ARITH_SYMBOLS = {0: '+', 1: '-', 2: '*', 3: '/', 4: '%', 5: '&', 6: '|', 7: '^', 8: '<<', 9: '>>'}
ARITH_IDS = {symbol: sub for sub, symbol in ARITH_SYMBOLS.items()}
COMPARE_SYMBOLS = {0: '<', 1: '<=', 2: '==', 3: '!=', 4: '>=', 5: '>'}
COMPARE_IDS = {symbol: sub for sub, symbol in COMPARE_SYMBOLS.items()}
UNARY_FUNCTIONS = {1: 'iabs', 2: 'fabs', 5: 'ftoi', 6: 'ftoi2', 9: 'ineg', 10: 'fneg', 11: 'bnot'}
UNARY_FUNCTION_IDS = {name: sub for sub, name in UNARY_FUNCTIONS.items()}
UNARY_RESULT_MODES = {1: MODE_INT, 9: MODE_INT, 11: MODE_INT, LOGICAL_NOT: MODE_INT, 2: MODE_FLOAT, 10: MODE_FLOAT}

VECTOR_FIELDS = {'pos': 4, 'rot': 12, 'scale': 16}
ACTOR_FIELDS = {'target': 29, 'stats': 27, 'air': 28, 'attacker': 31, 'motion_speed': 161}
STATS_FIELDS = {'hp': 15, 'max_hp': 16, 'mp': 17}
AXES = 'xyzw'
VECTOR_WIDTH = 4

MIN_FUNCTION_REF = 10

RESERVED = {'func', 'asm', 'data', 'bd', 'names', 'if', 'else', 'while', 'loop', 'switch', 'case',
            'default', 'goto', 'return', 'yield', 'abort', 'frame', 'seed', 'loc', 'glob', 'heap',
            'self', 'load', '__push'} | set(UNARY_FUNCTION_IDS)
IDENT = re.compile(r'[A-Za-z_]\w*')
RAW_NATIVE_RE = re.compile(r'__t(\d)_(0x[0-9a-fA-F]+)$')
BLOCK_RE = re.compile(r'^bd (\S+) code (0x[0-9A-Fa-f]+) \{$')
FUNC_RE = re.compile(r'^    func ([A-Za-z_]\w*\??)(?:\((.*?)\))?(?: (asm))?(?: \((\d+)\))?(?: -> (\d+))?'
                     r'(?: frame (\d+))?(?: seed (0x[0-9A-Fa-f]{4}))? \{(?:\s*//.*)?$')
ASM_LABEL_RE = re.compile(r'^\s*(@L-?[0-9A-Fa-f]+):\s*$')
ASM_EXACT_OPCODE_RE = re.compile(r'\s~(0x[0-9A-Fa-f]{4})$')
ASM_FUNCTION_TARGET_RE = re.compile(r'^([A-Za-z_]\w*\??)(\s+locals=\d+)?$')
ABSOLUTE_LABEL_RE = re.compile(r'@L-?[0-9A-Fa-f]+')
LISTING_LINE_RE = re.compile(r'^\s+([0-9A-F]{4})\s{2}(?:[0-9a-f]{2} )+\s*(\S+)\s*(.*?)\s*(?:;.*)?$')
POSTFIX_SAFE_RE = re.compile(r'[\w.?]+(\[[^\[\]]*\](:\d+)?)*')

STATS = {}


class PartError(Exception):
    def __init__(self, part, err):
        super().__init__(f'{part}: {type(err).__name__}: {err}')
        self.part = part


class Fail(Exception):
    pass


def glob_offset(name_and_offset):
    return name_and_offset[1]


def unique_native_names():
    keys_by_name = {}
    for key, name in bd.VERBS.items():
        if name:
            keys_by_name.setdefault(name, []).append(key)
    names = {}
    for name, keys in keys_by_name.items():
        if len(keys) == 1:
            base, sub = keys[0].split(':')
            names[(int(base, 0), int(sub, 0))] = name
    return names


NATIVE_NAMES = unique_native_names()
NATIVE_IDS = {name: key for key, name in NATIVE_NAMES.items()}


def record_stat(reason):
    reason = re.sub(r' at [0-9A-F]{4}', '', reason)
    STATS[reason] = STATS.get(reason, 0) + 1


def number_text(n):
    if -10 < n < 10:
        return str(n)
    if n >= 0:
        return f'0x{n:X}'
    return f'-0x{-n:X}'


def float_text(four_bytes):
    text = bd.f32_text(four_bytes)
    if text.startswith('0x'):
        return f'__f32({text})'
    if not re.search(r'[.en]', text):
        text += '.0'
    return text


def inferred_mode(e):
    kind = e[0]
    if kind in ('int', 'fref', 'cmp', 'sc'):
        return MODE_INT
    if kind == 'flt':
        return MODE_FLOAT
    if kind == 'bin':
        return e[2]
    if kind == 'un':
        return UNARY_RESULT_MODES.get(e[1])
    return None


def operation_mode(a, b):
    modes = (inferred_mode(a), inferred_mode(b))
    if MODE_FLOAT in modes:
        return MODE_FLOAT
    if MODE_INT in modes:
        return MODE_INT
    return DEFAULT_MODE


def case_mode(value):
    mode = inferred_mode(value)
    if mode is None:
        return DEFAULT_MODE
    return mode


def is_zero(e):
    if e[0] == 'int':
        return e[1] == 0
    if e[0] == 'flt':
        return e[1] == b'\0\0\0\0'
    return False


def is_chain_end_if(statement):
    return statement[0] == 'if' and statement[6]


def is_else_if_branch(statements):
    return len(statements) == 1 and is_chain_end_if(statements[0])


def is_bin_subtract(e):
    return e[0] == 'bin' and e[1] == SUBTRACT


def replace_bits(opcode, mask, shift, value):
    return (opcode & ~mask) | (value << shift)


def compose(cls, fields, previous_opcode):
    opcode = previous_opcode & INHERITED_OPCODE_BITS
    if 'mode' in fields:
        opcode = replace_bits(opcode, MODE_BITS, MODE_SHIFT, fields['mode'])
    if 'base' in fields:
        opcode = replace_bits(opcode, BASE_BITS, BASE_SHIFT, fields['base'])
    if 'sub' in fields:
        opcode = replace_bits(opcode, SUB_BITS, SUB_SHIFT, fields['sub'])
    return opcode | cls


def instruction_length(cls, fields):
    if 'raw' in fields:
        return bd.ilen(fields['raw'])
    if cls == CLASS_PUSH:
        if fields['mode'] in IMMEDIATE_PUSH_MODES:
            return 6
        return 4
    if cls in FOUR_BYTE_CLASSES:
        return 4
    return 2


def canonical_fields(instruction):
    cls = instruction['c']
    if cls == CLASS_MISC:
        return cls, {'sub': instruction['sub']}
    if cls in (CLASS_ARITH, CLASS_COMPARE):
        return cls, {'sub': instruction['sub'], 'mode': instruction['mode']}
    if cls == CLASS_PUSH:
        mode = instruction['mode']
        if mode in IMMEDIATE_PUSH_MODES:
            return cls, {'mode': mode}
        if mode == PUSH_ADDRESS:
            return cls, {'mode': PUSH_ADDRESS, 'base': instruction['base'], 'sub': 0}
        return cls, {'mode': PUSH_VALUE, 'base': instruction['base'], 'sub': instruction['sub']}
    if cls == CLASS_STORE:
        return cls, {'base': instruction['base']}
    if cls in JUMP_CLASSES:
        return cls, {}
    if cls in (CLASS_CALL, CLASS_INDEX, CLASS_LOAD):
        return cls, {'sub': instruction['sub']}
    if cls == CLASS_NATIVE:
        return cls, {'base': instruction['base'], 'sub': instruction['sub'], 'mode': 0}
    return cls, {'raw': instruction['op']}


def is_misc(instruction, sub):
    return instruction['c'] == CLASS_MISC and instruction['sub'] == sub


def find_short_circuits(instructions, pcs):
    index_of = {pc: n for n, pc in enumerate(pcs)}
    branches = {}
    for n, pc in enumerate(pcs[:-1]):
        if not is_misc(instructions[pc], DUPLICATE):
            continue
        branch = instructions[pcs[n + 1]]
        if branch['c'] not in BRANCH_CLASSES:
            continue
        target = bd._target(branch)
        if target not in index_of or index_of[target] == 0:
            continue
        join = instructions[pcs[index_of[target] - 1]]
        if branch['c'] == CLASS_BRANCH_IF_ZERO:
            wanted = LOGICAL_AND
        else:
            wanted = LOGICAL_OR
        if join['c'] == CLASS_ARITH and join['sub'] == wanted:
            branches[pcs[n + 1]] = (join['pos'], target)
    return branches


class StatementBuilder:
    def __init__(self, data, instructions, pcs, targets, param_count, signatures, block_off):
        self.data = data
        self.instructions = instructions
        self.pcs = pcs
        self.targets = targets
        self.signatures = signatures
        self.block_off = block_off
        self.stack = [('param', k) for k in range(param_count)]
        self.statements = []
        self.inside_switch = False
        self.skipped = set()
        self.frame = None
        self.short_circuit_branches = find_short_circuits(instructions, pcs)
        self.short_circuit_targets = {target for _, target in self.short_circuit_branches.values()}
        self.short_circuit_joins = {join for join, _ in self.short_circuit_branches.values()}

    def build(self):
        for index, pc in enumerate(self.pcs):
            if pc in self.targets and pc not in self.short_circuit_targets:
                self.flush_stack()
                self.statements.append(('label', self.label(pc)))
            if pc in self.skipped:
                continue
            self.translate(index, pc, self.instructions[pc])
        if self.inside_switch:
            raise Fail('switch not closed')
        self.flush_stack()
        return self.statements

    def label(self, pc):
        return f'@L{pc - self.block_off:04X}'

    def jump_label(self, instruction):
        return self.label(bd._target(instruction))

    def pop(self, count, pc):
        if len(self.stack) < count:
            raise Fail(f'stack underflow at {pc - self.block_off:04X}')
        values = self.stack[len(self.stack) - count:]
        del self.stack[len(self.stack) - count:]
        return values

    def pop_one(self, pc):
        return self.pop(1, pc)[0]

    def flush_stack(self):
        first_kept = 0
        while first_kept < len(self.stack) and self.stack[first_kept][0] == 'param':
            first_kept += 1
        for value in self.stack[first_kept:]:
            if value[0] in ('dupload', 'rmwptr'):
                raise Fail('read-modify-write split by a statement')
            self.statements.append(('keep', value))
        del self.stack[first_kept:]

    def emit(self, statement):
        self.flush_stack()
        self.statements.append(statement)

    def immediate(self, instruction):
        pc = instruction['pos']
        if instruction['mode'] == PUSH_INT:
            return ('int', bd.i32(self.data, pc + 2))
        return ('flt', self.data[pc + 2:pc + 6])

    def translate(self, index, pc, instruction):
        cls = instruction['c']
        if cls == CLASS_PUSH:
            self.translate_push(instruction)
        elif cls == CLASS_INDEX:
            self.stack.append(('idx', self.pop_one(pc), instruction['sub']))
        elif cls == CLASS_LOAD:
            pointer = self.pop_one(pc)
            if pointer[0] == 'rmwptr':
                raise Fail('load of a duplicated pointer')
            self.stack.append(('load', pointer, instruction['sub']))
        elif cls == CLASS_ARITH:
            self.translate_arith(pc, instruction)
        elif cls == CLASS_COMPARE:
            if instruction['sub'] not in COMPARE_SYMBOLS:
                raise Fail(f'cmp {instruction["sub"]}')
            self.stack.append(('cmp', instruction['sub'], instruction['mode'], self.pop_one(pc)))
        elif cls == CLASS_MISC:
            self.translate_misc(index, pc, instruction)
        elif cls == CLASS_STORE:
            if instruction['base'] == BASE_DATA:
                raise Fail('store to imm base')
            value = self.pop_one(pc)
            self.emit(('store', instruction['base'], instruction['arg'], value))
        elif cls == CLASS_JUMP:
            self.emit(('goto', self.jump_label(instruction)))
        elif cls in BRANCH_CLASSES:
            self.translate_branch(pc, instruction)
        elif cls == CLASS_CALL:
            self.translate_call(pc, instruction)
        elif cls == CLASS_NATIVE:
            self.translate_native(pc, instruction)
        else:
            raise Fail(f'class {cls:#x}')

    def translate_push(self, instruction):
        mode = instruction['mode']
        base = instruction['base']
        if mode in IMMEDIATE_PUSH_MODES:
            self.stack.append(self.immediate(instruction))
        elif mode == PUSH_ADDRESS:
            if base == BASE_DATA:
                data_offset = instruction['pos'] + 2 + instruction['arg'] - self.block_off
                self.stack.append(('lea', BASE_DATA, data_offset))
            else:
                self.stack.append(('lea', base, instruction['arg']))
        else:
            if base == BASE_DATA:
                raise Fail('value read from imm base')
            self.stack.append(('val', base, instruction['arg'], instruction['sub']))

    def translate_arith(self, pc, instruction):
        sub = instruction['sub']
        if sub in (LOGICAL_AND, LOGICAL_OR) and pc in self.short_circuit_joins:
            a, b = self.pop(2, pc)
            self.stack.append(('sc', sub, instruction['mode'], a, b))
        elif sub in ARITH_SYMBOLS:
            a, b = self.pop(2, pc)
            self.stack.append(('bin', sub, instruction['mode'], a, b))
        else:
            raise Fail(f'arith {sub}')

    def translate_branch(self, pc, instruction):
        if pc in self.short_circuit_branches:
            return
        condition = self.pop_one(pc)
        if instruction['c'] == CLASS_BRANCH_IF_ZERO:
            kind = 'ifz'
        else:
            kind = 'ifnz'
        self.emit((kind, condition, self.jump_label(instruction)))

    def translate_call(self, pc, instruction):
        target = bd._target(instruction)
        if self.frame is None:
            self.frame = instruction['sub']
        elif self.frame != instruction['sub']:
            raise Fail('call frame sizes differ')
        if target not in self.signatures:
            raise Fail('call to a non-routine')
        param_count, return_count = self.signatures[target]
        call = ('call', target, self.pop(param_count, pc))
        if return_count == 1:
            self.stack.append(call)
        elif return_count == 0:
            self.emit(('expr', call))
        else:
            raise Fail('multi-value return')

    def translate_native(self, pc, instruction):
        key = (instruction['base'], instruction['sub'])
        if instruction['mode'] != 0:
            raise Fail('native with non-zero mode')
        if key in bd.STUB_VERBS:
            self.emit(('expr', ('nat', instruction['base'], instruction['sub'], [])))
            return
        arity = bd.ARITY.get(key)
        if arity is None:
            raise Fail('native arity unknown')
        param_count, returns_value = arity
        call = ('nat', instruction['base'], instruction['sub'], self.pop(param_count, pc))
        if returns_value:
            self.stack.append(call)
        else:
            self.emit(('expr', call))

    def translate_misc(self, index, pc, instruction):
        sub = instruction['sub']
        if sub == DUPLICATE:
            self.translate_duplicate(index, pc)
        elif sub == LOGICAL_NOT or sub in UNARY_FUNCTIONS:
            self.stack.append(('un', sub, self.pop_one(pc)))
        elif sub == POP:
            self.translate_pop(pc)
        elif sub == STORE_INDIRECT:
            self.translate_store_indirect(pc)
        elif sub == YIELD:
            self.emit(('yield',))
        elif sub == RETURN:
            values = list(self.stack)
            self.stack.clear()
            for value in values:
                if value[0] in ('dupload', 'rmwptr'):
                    raise Fail('return of a duplicated value')
            self.statements.append(('ret', values))
        elif sub == ABORT:
            self.emit(('abort',))
        else:
            raise Fail(f'unary {sub}')

    def is_switch_case_test(self, following):
        if len(following) < 3:
            return False
        push, subtract, branch = following[0], following[1], following[2]
        return (push['c'] == CLASS_PUSH and push['mode'] in IMMEDIATE_PUSH_MODES
                and subtract['c'] == CLASS_ARITH and subtract['sub'] == SUBTRACT
                and branch['c'] == CLASS_BRANCH_IF_NONZERO)

    def translate_duplicate(self, index, pc):
        following_pcs = self.pcs[index + 1:index + 4]
        following = [self.instructions[x] for x in following_pcs]
        if following and following[0]['c'] in BRANCH_CLASSES and following_pcs[0] in self.short_circuit_branches:
            return
        if self.is_switch_case_test(following):
            self.translate_switch_case(pc, following)
            self.skipped.update(following_pcs)
            return
        if following and following[0]['c'] == CLASS_LOAD:
            pointer = self.pop_one(pc)
            self.stack.append(('rmwptr', pointer))
            self.stack.append(('dupload', pointer, following[0]['sub']))
            self.skipped.add(following_pcs[0])
            return
        raise Fail('dup')

    def translate_switch_case(self, pc, following):
        if not self.inside_switch:
            subject = self.pop_one(pc)
            self.flush_stack()
            self.inside_switch = True
            self.statements.append(('swbegin', subject))
        elif self.stack:
            raise Fail('switch subject under other values')
        push, subtract, branch = following
        value = self.immediate(push)
        self.statements.append(('swcase', value, subtract['mode'], self.jump_label(branch)))

    def translate_pop(self, pc):
        if not self.stack and self.inside_switch:
            self.inside_switch = False
            self.statements.append(('swend',))
            return
        value = self.pop_one(pc)
        self.flush_stack()
        if value[0] not in ('nat', 'call'):
            raise Fail('pop of a plain value')
        if value[0] == 'nat' and not bd.ARITY.get((value[1], value[2]), (0, 0))[1]:
            raise Fail('pop after a void native')
        self.statements.append(('expr', value))

    def translate_store_indirect(self, pc):
        pointer, value = self.pop(2, pc)
        self.flush_stack()
        if pointer[0] != 'rmwptr':
            self.statements.append(('storei', pointer, value))
            return
        target = pointer[1]
        is_read_modify_write = value[0] == 'bin' and value[3][0] == 'dupload' and value[3][1] is target
        if not is_read_modify_write:
            raise Fail('read-modify-write shape')
        _, sub, mode, read, rhs = value
        self.statements.append(('rmw', target, read[2], sub, mode, rhs))


def count_refs(statements, label):
    count = 0
    for statement in statements:
        kind = statement[0]
        if kind == 'goto' and statement[1] == label:
            count += 1
        elif kind in ('ifz', 'ifnz') and statement[2] == label:
            count += 1
    return count


def single_entry(statements, lo, hi, refs, allow=()):
    inside = statements[lo:hi]
    for statement in inside:
        if statement[0] != 'label' or statement[1] in allow:
            continue
        if refs.get(statement[1], 0) != count_refs(inside, statement[1]):
            return False
    return True


def index_after(position, count):
    return min(position + 1, count)


class Structurer:
    def __init__(self, statements, refs, end):
        self.statements = statements
        self.refs = refs
        self.end = end
        self.count = len(statements)
        self.position = {}
        for index, statement in enumerate(statements):
            if statement[0] == 'label':
                self.position[statement[1]] = index
        if end is not None:
            self.position.setdefault(end, self.count)

    def structure(self):
        out = []
        i = 0
        while i < self.count:
            statement = self.statements[i]
            if statement[0] == 'swbegin':
                match = match_switch(self.statements, i, self.position, self.refs)
                if match is None:
                    raise Fail('switch shape')
            else:
                match = self.match_loop(i)
                if match is None and statement[0] == 'ifz':
                    match = self.match_if(i)
            if match is None:
                out.append(statement)
                i += 1
            else:
                out.append(match[0])
                i = match[1]
        return out

    def match_loop(self, i):
        label_statement = self.statements[i]
        if label_statement[0] != 'label' or self.refs.get(label_statement[1]) != 1:
            return None
        top = label_statement[1]
        match = self.match_while(i, top)
        if match is not None:
            return match
        back_jump = None
        for k in range(i + 1, self.count):
            if self.statements[k] == ('goto', top):
                back_jump = k
                break
        if back_jump is not None and single_entry(self.statements, i + 1, back_jump, self.refs):
            return ('loop', structure(self.statements[i + 1:back_jump], self.refs)), back_jump + 1
        return None

    def match_while(self, i, top):
        if i + 1 >= self.count or self.statements[i + 1][0] != 'ifz':
            return None
        _, condition, exit_label = self.statements[i + 1]
        exit_index = self.position.get(exit_label)
        if exit_index is None or not i + 1 < exit_index < self.count:
            return None
        if self.refs.get(exit_label) != 1 or self.statements[exit_index - 1] != ('goto', top):
            return None
        body = structure(self.statements[i + 2:exit_index - 1], self.refs)
        return ('while', condition, body), exit_index + 1

    def all_refs_inside(self, label, lo, hi):
        return self.refs.get(label, 0) == count_refs(self.statements[lo:hi], label)

    def match_if(self, i):
        statements, refs, count = self.statements, self.refs, self.count
        _, condition, else_label = statements[i]
        else_index = self.position.get(else_label)
        if else_index is None or else_index <= i:
            return None
        then_raw = statements[i + 1:else_index]
        last = None
        if then_raw:
            last = then_raw[-1]
        shares_end = else_label == self.end
        if last == ('goto', else_label):
            if (shares_end or refs.get(else_label) == 2) and single_entry(statements, i + 1, else_index - 1, refs):
                node = ('if', condition, structure(then_raw[:-1], refs), None, True, False, shares_end)
                return node, index_after(else_index, count)
        if last is not None and last[0] == 'goto' and last[1] != else_label and else_index < count:
            if self.if_else_applies(i, else_label, else_index, last[1]):
                return self.if_else(condition, else_index, then_raw, last[1])
        if shares_end and else_index == count and single_entry(statements, i + 1, else_index, refs):
            return ('if', condition, structure(then_raw, refs), None, False, False, True), count
        if (not shares_end and refs.get(else_label) == 1 and else_index < count
                and single_entry(statements, i + 1, else_index, refs)):
            return ('if', condition, structure(then_raw, refs), None, False, False, False), else_index + 1
        return None

    def if_else_applies(self, i, else_label, else_index, end_label):
        statements, refs = self.statements, self.refs
        end_index = self.position.get(end_label)
        if end_index is None or end_index <= else_index or refs.get(else_label) != 1:
            return False
        if not (end_label == self.end or self.all_refs_inside(end_label, i, end_index)):
            return False
        if not single_entry(statements, i + 1, else_index - 1, refs):
            return False
        return single_entry(statements, else_index + 1, end_index, refs, allow={end_label})

    def if_else(self, condition, else_index, then_raw, end_label):
        statements, refs = self.statements, self.refs
        end_index = self.position[end_label]
        else_raw = statements[else_index + 1:end_index]
        else_tree = structure(else_raw, refs, end=end_label)
        if is_else_if_branch(else_tree):
            other, else_jumps = else_tree, False
        elif else_raw and else_raw[-1] == ('goto', end_label):
            other, else_jumps = structure(else_raw[:-1], refs, end=end_label), True
        else:
            other, else_jumps = else_tree, False
        if not is_else_if_branch(else_tree):
            for statement in other:
                if is_chain_end_if(statement):
                    return None
        node = ('if', condition, structure(then_raw[:-1], refs), other, True, else_jumps, end_label == self.end)
        return node, index_after(end_index, self.count)


def structure(statements, refs, end=None):
    return Structurer(statements, refs, end).structure()


def match_switch(statements, i, position, refs):
    subject = statements[i][1]
    end = None
    for k in range(i + 1, len(statements)):
        if statements[k][0] == 'swend':
            end = k
            break
    if end is None or statements[end - 1][0] != 'label':
        return None
    end_label = statements[end - 1][1]
    cases = []
    j = i + 1
    while j < end - 1 and statements[j][0] == 'swcase':
        _, value, mode, next_label = statements[j]
        if next_label == end_label:
            body = statements[j + 1:end - 1]
            for statement in body:
                if statement[0] in ('swbegin', 'swcase', 'swend'):
                    return None
            cases.append((value, mode, structure(body, refs)))
            j = end - 1
            break
        next_index = position.get(next_label)
        if next_index is None or next_index <= j or next_index >= end or refs.get(next_label) != 1:
            return None
        body = statements[j + 1:next_index]
        if not body or body[-1] != ('goto', end_label):
            return None
        cases.append((value, mode, structure(body[:-1], refs)))
        j = next_index + 1
    if not cases:
        return None
    default = None
    if j < end - 1:
        default = statements[j:end - 1]
    jumps_to_end = statements[i + 1:end - 1].count(('goto', end_label))
    if default is None:
        last_case_branches = 1
    else:
        last_case_branches = 0
    if refs.get(end_label, 0) != jumps_to_end + last_case_branches:
        return None
    default_tree = None
    if default is not None:
        default_tree = structure(default, refs)
    return ('switch', subject, cases, default_tree), end + 1


def renumber(statements):
    new_names = {}

    def rename(label):
        if label not in new_names:
            new_names[label] = f'L{len(new_names) + 1}'
        return new_names[label]

    def rename_optional(body):
        if body is None:
            return None
        return rename_all(body)

    def rename_all(body):
        out = []
        for s in body:
            kind = s[0]
            if kind in ('label', 'goto'):
                s = (kind, rename(s[1]))
            elif kind in ('ifz', 'ifnz'):
                s = (kind, s[1], rename(s[2]))
            elif kind == 'if':
                then = rename_all(s[2])
                s = ('if', s[1], then, rename_optional(s[3])) + s[4:]
            elif kind == 'while':
                s = ('while', s[1], rename_all(s[2]))
            elif kind == 'loop':
                s = ('loop', rename_all(s[1]))
            elif kind == 'switch':
                cases = [(value, mode, rename_all(case_body)) for value, mode, case_body in s[2]]
                s = ('switch', s[1], cases, rename_optional(s[3]))
            out.append(s)
        return out

    return rename_all(statements)


class Names:
    def __init__(self, glob, routines=None, self_slot=None):
        self.glob = dict(glob)
        if self_slot is not None:
            self.glob[self_slot] = 'self'
        self.glob_id = {name: offset for offset, name in self.glob.items()}
        self.routines = {}
        if routines is not None:
            self.routines = dict(routines)


def is_actor(e, names):
    if e == ('val', BASE_GLOB, names.glob_id.get('self', -1), 1):
        return True
    return (e[0] == 'load' and e[2] == 1 and e[1][0] == 'idx' and e[1][2] == ACTOR_FIELDS['target']
            and is_actor(e[1][1], names))


def is_stats(e, names):
    return (e[0] == 'load' and e[2] == 1 and e[1][0] == 'idx' and e[1][2] == ACTOR_FIELDS['stats']
            and is_actor(e[1][1], names))


def field_text(base, word, width, names):
    base_text = expr_text(base, names, False)
    if is_actor(base, names):
        for field, offset in VECTOR_FIELDS.items():
            if word == offset and width == VECTOR_WIDTH:
                return f'{base_text}.{field}'
            if width == 1 and offset <= word < offset + VECTOR_WIDTH:
                return f'{base_text}.{field}.{AXES[word - offset]}'
        for field, offset in ACTOR_FIELDS.items():
            if word == offset and width == 1:
                return f'{base_text}.{field}'
    if is_stats(base, names) and width == 1:
        for field, offset in STATS_FIELDS.items():
            if word == offset:
                return f'{base_text}.{field}'
    return None


def postfix_text(e, names):
    text = expr_text(e, names, False)
    if POSTFIX_SAFE_RE.fullmatch(text):
        return text
    return f'({text})'


def mode_suffix(mode):
    return MODE_SUFFIX.get(mode, f'm{mode}')


def mode_mark(actual, inferred):
    if actual == inferred:
        return ''
    return '.' + mode_suffix(actual)


def wrap_unless_top(text, top):
    if top:
        return text
    return f'({text})'


def width_suffix(text, width):
    if width == 1:
        return text
    return f'{text}:{width}'


def compare_text(e, names, top):
    _, op, compare_mode, operand = e
    symbol = COMPARE_SYMBOLS[op]
    if is_bin_subtract(operand) and not is_zero(operand[4]):
        _, _, subtract_mode, a, b = operand
        inferred = operation_mode(a, b)
        if subtract_mode == inferred and compare_mode == inferred:
            text = f'{expr_text(a, names, False)} {symbol} {expr_text(b, names, False)}'
            return wrap_unless_top(text, top)
        if subtract_mode == compare_mode:
            text = f'{expr_text(a, names, False)} {symbol}.{mode_suffix(compare_mode)} {expr_text(b, names, False)}'
            return wrap_unless_top(text, top)
    if compare_mode == MODE_INT:
        zero = '0'
    elif compare_mode == MODE_FLOAT:
        zero = '0.0'
    else:
        raise Fail('compare mode')
    return wrap_unless_top(f'{expr_text(operand, names, False)} {symbol} {zero}', top)


def variable_text(base, offset, names):
    if base == BASE_GLOB and offset in names.glob:
        return names.glob[offset]
    return f'{BASE_NAMES[base]}[{offset}]'


def address_text(base, offset, names):
    if base == BASE_DATA:
        return f'&data[0x{offset:04X}]'
    return f'&{variable_text(base, offset, names)}'


def load_text(pointer, width, names):
    if pointer[0] == 'idx':
        _, base, word = pointer
        field = field_text(base, word, width, names)
        if field:
            return field
        return width_suffix(f'{postfix_text(base, names)}[{word}]', width)
    if width == 1:
        return f'*{postfix_text(pointer, names)}'
    return f'load({expr_text(pointer, names)}, {width})'


def index_address_text(base, word, names):
    if word in VECTOR_FIELDS.values():
        field = field_text(base, word, VECTOR_WIDTH, names)
        if field:
            return f'&{field}'
    return f'&{postfix_text(base, names)}[{word}]'


def arguments_text(args, names):
    return ', '.join(expr_text(a, names) for a in args)


def native_name(base, sub):
    if (base, sub) in NATIVE_NAMES:
        return NATIVE_NAMES[(base, sub)]
    return f'__t{base}_0x{sub:02x}'


def expr_text(e, names, top=True):
    kind = e[0]
    if kind == 'int':
        return number_text(e[1])
    if kind == 'flt':
        return float_text(e[1])
    if kind == 'param':
        return f'a{e[1]}'
    if kind == 'fref':
        return f'@{e[1]}'
    if kind == 'val':
        _, base, offset, width = e
        return width_suffix(variable_text(base, offset, names), width)
    if kind == 'lea':
        return address_text(e[1], e[2], names)
    if kind == 'load':
        return load_text(e[1], e[2], names)
    if kind == 'idx':
        return index_address_text(e[1], e[2], names)
    if kind == 'un':
        if e[1] == LOGICAL_NOT:
            return f'!{postfix_text(e[2], names)}'
        return f'{UNARY_FUNCTIONS[e[1]]}({expr_text(e[2], names)})'
    if kind == 'bin':
        _, sub, mode, a, b = e
        mark = mode_mark(mode, operation_mode(a, b))
        text = f'{expr_text(a, names, False)} {ARITH_SYMBOLS[sub]}{mark} {expr_text(b, names, False)}'
        return wrap_unless_top(text, top)
    if kind == 'cmp':
        return compare_text(e, names, top)
    if kind == 'sc':
        _, sub, mode, a, b = e
        if sub == LOGICAL_AND:
            symbol = '&&'
        else:
            symbol = '||'
        text = f'{expr_text(a, names, False)} {symbol}{mode_mark(mode, MODE_INT)} {expr_text(b, names, False)}'
        return wrap_unless_top(text, top)
    if kind == 'nat':
        _, base, sub, args = e
        return f'{native_name(base, sub)}({arguments_text(args, names)})'
    if kind == 'call':
        return f'{names.routines[e[1]]}({arguments_text(e[2], names)})'
    raise Fail(f'cannot print {kind}')


def pointer_target_text(pointer, names):
    if pointer[0] == 'idx':
        field = field_text(pointer[1], pointer[2], 1, names)
        if field:
            return field
        return f'{postfix_text(pointer[1], names)}[{pointer[2]}]'
    return f'*{postfix_text(pointer, names)}'


def no_jump_mark(has_jump):
    if has_jump:
        return ''
    return '.nj'


MOTION_VERBS = {(0, 0x0C), (0, 0x0D), (0, 0x0E)}
MOTION_ID_MASK = 0xFFFF


def constant_motion_id(expression):
    if expression[0] != 'nat' or (expression[1], expression[2]) not in MOTION_VERBS:
        return None
    arguments = expression[3]
    if len(arguments) < 2 or arguments[1][0] != 'int':
        return None
    return arguments[1][1] & MOTION_ID_MASK


def motion_comment(expression, motions):
    if motions is None:
        return ''
    motion_id = constant_motion_id(expression)
    if motion_id is None:
        return ''
    if motion_id in motions:
        return f'  // -> anim{motions[motion_id]:04d}'
    return f'  // motion_id {motion_id} (no anim)'


class StatementPrinter:
    def __init__(self, names, motions=None):
        self.names = names
        self.motions = motions

    def text(self, e):
        return expr_text(e, self.names)

    def lines(self, statements, depth):
        pad = '    ' * depth
        out = []
        for s in statements:
            out += self.statement_lines(s, depth, pad)
        return out

    def statement_lines(self, s, depth, pad):
        kind = s[0]
        if kind == 'label':
            return [f'{"    " * max(depth - 1, 0)}{s[1]}:']
        if kind == 'store':
            comment = motion_comment(s[3], self.motions)
            return [f'{pad}{self.text(("val", s[1], s[2], 1))} = {self.text(s[3])};{comment}']
        if kind == 'storei':
            return [f'{pad}{pointer_target_text(s[1], self.names)} = {self.text(s[2])};']
        if kind == 'rmw':
            return [pad + self.read_modify_write_text(s)]
        if kind == 'expr':
            comment = motion_comment(s[1], self.motions)
            return [f'{pad}{self.text(s[1])};{comment}']
        if kind == 'keep':
            return [f'{pad}__push({self.text(s[1])});']
        if kind in ('yield', 'abort'):
            return [f'{pad}{kind};']
        if kind == 'ret':
            values = ', '.join(self.text(v) for v in s[1])
            if values:
                return [f'{pad}return {values};']
            return [f'{pad}return;']
        if kind == 'goto':
            return [f'{pad}goto {s[1]};']
        if kind == 'ifz':
            return [f'{pad}if (!{postfix_text(s[1], self.names)}) goto {s[2]};']
        if kind == 'ifnz':
            condition = self.text(s[1])
            if condition.startswith('!'):
                condition = f'({condition})'
            return [f'{pad}if ({condition}) goto {s[2]};']
        if kind == 'if':
            return self.if_lines(s, depth, pad)
        if kind == 'while':
            return [f'{pad}while ({self.text(s[1])}) {{'] + self.lines(s[2], depth + 1) + [f'{pad}}}']
        if kind == 'loop':
            return [f'{pad}loop {{'] + self.lines(s[1], depth + 1) + [f'{pad}}}']
        if kind == 'switch':
            return self.switch_lines(s, depth, pad)
        raise Fail(f'cannot print statement {kind}')

    def read_modify_write_text(self, s):
        _, pointer, width, sub, mode, rhs = s
        if width == 1:
            target = pointer_target_text(pointer, self.names)
        else:
            target = f'load({self.text(pointer)}, {width})'
        mark = mode_mark(mode, operation_mode(('load', pointer, width), rhs))
        return f'{target} {ARITH_SYMBOLS[sub]}={mark} {self.text(rhs)};'

    def if_lines(self, s, depth, pad):
        _, condition, then, other, then_jumps, else_jumps, _ = s
        out = [f'{pad}if{no_jump_mark(then_jumps)} ({self.text(condition)}) {{']
        out += self.lines(then, depth + 1)
        while other is not None and is_else_if_branch(other):
            chained = other[0]
            out.append(f'{pad}}} else if{no_jump_mark(chained[4])} ({self.text(chained[1])}) {{')
            out += self.lines(chained[2], depth + 1)
            other, else_jumps = chained[3], chained[5]
        if other is not None:
            out.append(f'{pad}}} else{no_jump_mark(else_jumps)} {{')
            out += self.lines(other, depth + 1)
        out.append(f'{pad}}}')
        return out

    def switch_lines(self, s, depth, pad):
        _, subject, cases, default = s
        out = [f'{pad}switch ({self.text(subject)}) {{']
        for value, mode, body in cases:
            out.append(f'{pad}case{mode_mark(mode, case_mode(value))} {self.text(value)}:')
            out += self.lines(body, depth + 1)
        if default is not None:
            out.append(f'{pad}default:')
            out += self.lines(default, depth + 1)
        out.append(f'{pad}}}')
        return out


def statement_lines(statements, names, depth, motions=None):
    return StatementPrinter(names, motions).lines(statements, depth)


MODE_MARK = r'(?:\.(?:i|f|m2|m3)\b)?'
COMMENT_PATTERN = r'//[^\n]*'
FLOAT_PATTERN = r'(?P<flt>\d+\.\d*(?:e[+-]?\d+)?|\d+e[+-]?\d+)'
NUMBER_PATTERN = r'(?P<num>0x[0-9A-Fa-f]+|\d+)'
IDENTIFIER_PATTERN = r'(?P<id>[A-Za-z_][\w]*\??)'
OPERATOR_PATTERN = (r'(?P<op>(?:\|\||&&|==|!=|>=|<=|<<|>>|->|[-+*/%&|^]=)' + MODE_MARK
                    + r'|[-+*/%<>&|^]' + MODE_MARK + r'|[~!(){}\[\];:,=.@])')
TOKEN_RE = re.compile(r'\s*(?:' + '|'.join((COMMENT_PATTERN, FLOAT_PATTERN, NUMBER_PATTERN,
                                            IDENTIFIER_PATTERN, OPERATOR_PATTERN)) + r')')


def tokenize(text):
    tokens = []
    position = 0
    text = text.rstrip()
    while position < len(text):
        match = TOKEN_RE.match(text, position)
        if not match:
            raise SyntaxError(f'bad token at {text[position:position + 30]!r}')
        position = match.end()
        if match.group('flt'):
            tokens.append(('flt', struct.pack('<f', float(match.group('flt')))))
        elif match.group('num'):
            tokens.append(('num', int(match.group('num'), 0)))
        elif match.group('id'):
            tokens.append(('id', match.group('id')))
        elif match.group('op'):
            tokens.append(('op', match.group('op')))
    return tokens


def split_mark(op):
    if '.' in op and op != '.':
        base, mark = op.split('.', 1)
        return base, MARK_MODE[mark]
    return op, None


def is_compound_assignment(token):
    if token[0] != 'op':
        return False
    op = split_mark(token[1])[0]
    return op.endswith('=') and op not in ('==', '!=', '<=', '>=')


def chosen_mode(mark, default):
    if mark is not None:
        return mark
    return default


BINARY_LEVELS = [('||',), ('&&',), ('|',), ('^',), ('&',), ('==', '!='), ('<', '<=', '>', '>='),
                 ('<<', '>>'), ('+', '-'), ('*', '/', '%')]


class Parser:
    def __init__(self, tokens, names, funcs):
        self.tokens = tokens
        self.position = 0
        self.names = names
        self.funcs = funcs

    def peek(self, ahead=0):
        if self.position + ahead < len(self.tokens):
            return self.tokens[self.position + ahead]
        return ('eof', None)

    def peek_value(self, ahead=0):
        return self.peek(ahead)[1]

    def take(self, expected=None):
        token = self.peek()
        if expected is not None and token[1] != expected:
            raise SyntaxError(f'expected {expected!r}, got {token}')
        self.position += 1
        return token

    def take_value(self):
        return self.take()[1]

    def take_no_jump_mark(self):
        if self.peek_value() == '.' and self.peek_value(1) == 'nj':
            self.position += 2
            return True
        return False

    def expr(self, level=0):
        if level == len(BINARY_LEVELS):
            return self.unary()
        a = self.expr(level + 1)
        while True:
            token = self.peek()
            if token[0] != 'op':
                return a
            op, mark = split_mark(token[1])
            if op not in BINARY_LEVELS[level]:
                return a
            self.take()
            b = self.expr(level + 1)
            a = self.binary(op, mark, a, b)

    def binary(self, op, mark, a, b):
        if op in ('&&', '||'):
            if op == '&&':
                sub = LOGICAL_AND
            else:
                sub = LOGICAL_OR
            return ('sc', sub, chosen_mode(mark, MODE_INT), a, b)
        if op in COMPARE_IDS:
            if is_zero(b):
                if b[0] == 'int':
                    zero_mode = MODE_INT
                else:
                    zero_mode = MODE_FLOAT
                return ('cmp', COMPARE_IDS[op], chosen_mode(mark, zero_mode), a)
            mode = chosen_mode(mark, operation_mode(a, b))
            return ('cmp', COMPARE_IDS[op], mode, ('bin', SUBTRACT, mode, a, b))
        return ('bin', ARITH_IDS[op], chosen_mode(mark, operation_mode(a, b)), a, b)

    def unary(self):
        value = self.peek_value()
        if value == '!':
            self.take()
            return ('un', LOGICAL_NOT, self.unary())
        if value == '-' and self.peek(1)[0] in ('num', 'flt'):
            self.take()
            kind, number = self.take()
            if kind == 'num':
                return ('int', -number)
            return ('flt', struct.pack('<f', -struct.unpack('<f', number)[0]))
        if value == '*':
            self.take()
            return ('load', self.unary(), 1)
        if value == '&':
            self.take()
            return self.address(self.postfix_expr())
        return self.postfix_expr()

    def address(self, e):
        if e[0] == 'val' and e[3] == 1:
            return ('lea', e[1], e[2])
        if e[0] == 'load' and e[1][0] == 'idx':
            return e[1]
        if e[0] == 'datalea':
            return ('lea', BASE_DATA, e[1])
        raise SyntaxError(f'cannot take the address of {e}')

    def postfix_expr(self):
        e = self.primary()
        while True:
            value = self.peek_value()
            if value == '[':
                self.take()
                word = self.take_value()
                self.take(']')
                e = ('load', ('idx', e, word), self.optional_width())
            elif value == '.' and self.peek(1)[0] == 'id':
                self.take()
                e = self.field(e, self.take_value())
            else:
                return e

    def optional_width(self):
        if self.peek_value() == ':' and self.peek(1)[0] == 'num':
            self.take()
            width = self.take_value()
            if width:
                return width
        return 1

    def field(self, e, name):
        if name in VECTOR_FIELDS:
            offset = VECTOR_FIELDS[name]
            if self.peek_value() == '.' and self.peek(1)[0] == 'id' and self.peek_value(1) in AXES:
                self.take()
                axis = self.take_value()
                return ('load', ('idx', e, offset + AXES.index(axis)), 1)
            return ('load', ('idx', e, offset), VECTOR_WIDTH)
        if name in ACTOR_FIELDS:
            return ('load', ('idx', e, ACTOR_FIELDS[name]), 1)
        if name in STATS_FIELDS:
            return ('load', ('idx', e, STATS_FIELDS[name]), 1)
        raise SyntaxError(f'unknown field .{name}')

    def primary(self):
        kind, value = self.take()
        if kind == 'num':
            return ('int', value)
        if kind == 'flt':
            return ('flt', value)
        if value == '(':
            e = self.expr()
            self.take(')')
            return e
        if value == '@':
            name = self.take_value()
            if name not in self.funcs:
                raise SyntaxError(f'@{name}: no such function')
            return ('fref', name)
        if kind != 'id':
            raise SyntaxError(f'unexpected {value!r}')
        next_value = self.peek_value()
        if value in BASE_IDS and next_value == '[':
            return self.variable(BASE_IDS[value])
        if value == 'data' and next_value == '[':
            self.take('[')
            offset = self.take_value()
            self.take(']')
            return ('datalea', offset)
        if re.fullmatch(r'a\d+', value) and next_value != '(':
            return ('param', int(value[1:]))
        if value in self.names.glob_id and next_value != '(':
            return ('val', BASE_GLOB, self.names.glob_id[value], self.optional_width())
        if next_value == '(':
            return self.call(value, self.call_arguments())
        raise SyntaxError(f'unknown name {value!r}')

    def variable(self, base):
        self.take('[')
        sign = 1
        if self.peek_value() == '-':
            sign = -1
            self.take()
        offset = sign * self.take_value()
        self.take(']')
        return ('val', base, offset, self.optional_width())

    def call_arguments(self):
        self.take('(')
        args = []
        while self.peek_value() != ')':
            args.append(self.expr())
            if self.peek_value() == ',':
                self.take()
        self.take(')')
        return args

    def call(self, name, args):
        if name in UNARY_FUNCTION_IDS:
            return ('un', UNARY_FUNCTION_IDS[name], args[0])
        if name == 'load':
            return ('load', args[0], args[1][1])
        if name == '__f32':
            return ('flt', struct.pack('<I', args[0][1]))
        if name in self.funcs:
            return ('call', name, args)
        raw = RAW_NATIVE_RE.fullmatch(name)
        if raw:
            return ('nat', int(raw.group(1)), int(raw.group(2), 16), args)
        if name in NATIVE_IDS:
            base, sub = NATIVE_IDS[name]
            return ('nat', base, sub, args)
        raise SyntaxError(f'unknown function {name!r}')

    def block(self):
        self.take('{')
        out = []
        while self.peek_value() != '}':
            out.append(self.stmt())
        self.take('}')
        return out

    def stmts_until(self, stops):
        out = []
        while self.peek()[0] != 'eof' and self.peek_value() not in stops:
            out.append(self.stmt())
        return out

    def parenthesized_expr(self):
        self.take('(')
        e = self.expr()
        self.take(')')
        return e

    def goto_label(self):
        self.take()
        label = self.take_value()
        self.take(';')
        return label

    def stmt(self):
        kind, value = self.peek()
        if kind == 'id' and self.peek_value(1) == ':' and value != 'default':
            self.position += 2
            return ('label', value)
        if value == 'if':
            return self.if_stmt()
        if value == 'while':
            self.take()
            condition = self.parenthesized_expr()
            return ('while', condition, self.block())
        if value == 'loop':
            self.take()
            return ('loop', self.block())
        if value == 'switch':
            return self.switch_stmt()
        if value == 'goto':
            return ('goto', self.goto_label())
        if value in ('yield', 'abort'):
            self.take()
            self.take(';')
            return (value,)
        if value == 'return':
            return self.return_stmt()
        if value == '__push':
            self.take()
            e = self.parenthesized_expr()
            self.take(';')
            return ('keep', e)
        return self.expression_stmt()

    def if_stmt(self):
        self.take()
        then_jumps = not self.take_no_jump_mark()
        self.take('(')
        if self.peek_value() == '!':
            saved = self.position
            self.take()
            negated = self.unary()
            if self.peek_value() == ')' and self.peek_value(1) == 'goto':
                self.take(')')
                return ('ifz', negated, self.goto_label())
            self.position = saved
        condition = self.expr()
        self.take(')')
        if self.peek_value() == 'goto':
            return ('ifnz', condition, self.goto_label())
        then = self.block()
        other, else_jumps = None, False
        if self.peek_value() == 'else':
            self.take()
            if self.peek_value() == 'if':
                chained = self.stmt()
                other = [chained[:6] + (True,)]
            else:
                else_jumps = not self.take_no_jump_mark()
                other = self.block()
        return ('if', condition, then, other, then_jumps, else_jumps, False)

    def switch_stmt(self):
        self.take()
        subject = self.parenthesized_expr()
        self.take('{')
        cases, default = [], None
        while self.peek_value() != '}':
            word = self.take_value()
            if word.startswith('case'):
                mark = None
                if self.peek_value() == '.':
                    self.take()
                    mark = {'i': 0, 'f': 1}[self.take_value()]
                value = self.unary()
                self.take(':')
                body = self.stmts_until(('case', 'default', '}'))
                cases.append((value, chosen_mode(mark, case_mode(value)), body))
            elif word == 'default':
                self.take(':')
                default = self.stmts_until(('case', 'default', '}'))
            else:
                raise SyntaxError(f'expected case/default, got {word!r}')
        self.take('}')
        return ('switch', subject, cases, default)

    def return_stmt(self):
        self.take()
        values = []
        while self.peek_value() != ';':
            values.append(self.expr())
            if self.peek_value() == ',':
                self.take()
        self.take(';')
        return ('ret', values)

    def expression_stmt(self):
        lhs = self.expr()
        token = self.peek()
        if token[1] == '=':
            self.take()
            rhs = self.expr()
            self.take(';')
            return self.assign(lhs, rhs)
        if is_compound_assignment(token):
            op, mark = split_mark(self.take_value())
            rhs = self.expr()
            self.take(';')
            if lhs[0] != 'load':
                raise SyntaxError('compound assignment needs a pointer target')
            _, pointer, width = lhs
            mode = chosen_mode(mark, operation_mode(lhs, rhs))
            return ('rmw', pointer, width, ARITH_IDS[op[:-1]], mode, rhs)
        self.take(';')
        return ('expr', lhs)

    def assign(self, lhs, rhs):
        if lhs[0] == 'val' and lhs[3] == 1:
            return ('store', lhs[1], lhs[2], rhs)
        if lhs[0] == 'load' and lhs[2] == 1:
            return ('storei', lhs[1], rhs)
        raise SyntaxError(f'cannot assign to {lhs}')


def parse_statements(text, names, funcs):
    return Parser(tokenize(text), names, funcs).stmts_until(())


class Emitter:
    def __init__(self, code_offset):
        self.items = []
        self.code_offset = code_offset
        self.label_count = 0
        self.scope = ''
        self.frame = 0
        self.funcs = {}

    def fresh_label(self):
        self.label_count += 1
        return f'__c{self.label_count}'

    def ins(self, cls, fields, kind=None, value=None, exact=None):
        self.items.append(('ins', cls, fields, kind, value, exact))

    def jump(self, cls, label):
        self.ins(cls, {}, 'rel', label)

    def misc(self, sub):
        self.ins(CLASS_MISC, {'sub': sub})

    def label(self, name):
        self.items.append(('label', name))

    def local(self, name):
        return self.scope + name

    def expr(self, e):
        kind = e[0]
        if kind == 'int':
            self.ins(CLASS_PUSH, {'mode': PUSH_INT}, 'imm', struct.pack('<i', e[1]))
        elif kind == 'fref':
            self.ins(CLASS_PUSH, {'mode': PUSH_INT}, 'fref', self.funcs[e[1]][0])
        elif kind == 'flt':
            self.ins(CLASS_PUSH, {'mode': PUSH_FLOAT}, 'imm', e[1])
        elif kind == 'val':
            self.ins(CLASS_PUSH, {'mode': PUSH_VALUE, 'base': e[1], 'sub': e[3]}, 'off', e[2])
        elif kind == 'lea':
            if e[1] == BASE_DATA:
                operand_kind = 'data'
            else:
                operand_kind = 'off'
            self.ins(CLASS_PUSH, {'mode': PUSH_ADDRESS, 'base': e[1], 'sub': 0}, operand_kind, e[2])
        elif kind == 'param':
            pass
        elif kind == 'idx':
            self.expr(e[1])
            self.ins(CLASS_INDEX, {'sub': e[2]})
        elif kind == 'load':
            self.expr(e[1])
            self.ins(CLASS_LOAD, {'sub': e[2]})
        elif kind == 'un':
            self.expr(e[2])
            self.misc(e[1])
        elif kind == 'bin':
            self.expr(e[3])
            self.expr(e[4])
            self.ins(CLASS_ARITH, {'sub': e[1], 'mode': e[2]})
        elif kind == 'cmp':
            self.expr(e[3])
            self.ins(CLASS_COMPARE, {'sub': e[1], 'mode': e[2]})
        elif kind == 'sc':
            self.short_circuit(e)
        elif kind == 'nat':
            for arg in e[3]:
                self.expr(arg)
            self.ins(CLASS_NATIVE, {'base': e[1], 'sub': e[2], 'mode': 0})
        elif kind == 'call':
            for arg in e[2]:
                self.expr(arg)
            label, _ = self.funcs[e[1]]
            self.ins(CLASS_CALL, {'sub': self.frame}, 'rel', label)
        else:
            raise ValueError(f'cannot emit {kind}')

    def short_circuit(self, e):
        _, sub, mode, a, b = e
        end = self.fresh_label()
        self.expr(a)
        self.misc(DUPLICATE)
        if sub == LOGICAL_AND:
            self.jump(CLASS_BRANCH_IF_ZERO, end)
        else:
            self.jump(CLASS_BRANCH_IF_NONZERO, end)
        self.expr(b)
        self.ins(CLASS_ARITH, {'sub': sub, 'mode': mode})
        self.label(end)

    def returns_value(self, e):
        if e[0] == 'nat':
            if (e[1], e[2]) in bd.STUB_VERBS and not e[3]:
                return False
            return bool(bd.ARITY.get((e[1], e[2]), (0, 0))[1])
        if e[0] == 'call':
            return self.funcs[e[1]][1] > 0
        return True

    def stmts(self, statements):
        for s in statements:
            self.stmt(s)

    def stmt(self, s):
        kind = s[0]
        if kind == 'label':
            self.label(self.local(s[1]))
        elif kind == 'store':
            self.expr(s[3])
            self.ins(CLASS_STORE, {'base': s[1]}, 'off', s[2])
        elif kind == 'storei':
            self.expr(s[1])
            self.expr(s[2])
            self.misc(STORE_INDIRECT)
        elif kind == 'rmw':
            _, pointer, width, sub, mode, rhs = s
            self.expr(pointer)
            self.misc(DUPLICATE)
            self.ins(CLASS_LOAD, {'sub': width})
            self.expr(rhs)
            self.ins(CLASS_ARITH, {'sub': sub, 'mode': mode})
            self.misc(STORE_INDIRECT)
        elif kind == 'expr':
            self.expr(s[1])
            if self.returns_value(s[1]):
                self.misc(POP)
        elif kind == 'keep':
            self.expr(s[1])
        elif kind == 'yield':
            self.misc(YIELD)
        elif kind == 'abort':
            self.misc(ABORT)
        elif kind == 'ret':
            for value in s[1]:
                self.expr(value)
            self.misc(RETURN)
        elif kind == 'goto':
            self.jump(CLASS_JUMP, self.local(s[1]))
        elif kind == 'ifz':
            self.expr(s[1])
            self.jump(CLASS_BRANCH_IF_ZERO, self.local(s[2]))
        elif kind == 'ifnz':
            self.expr(s[1])
            self.jump(CLASS_BRANCH_IF_NONZERO, self.local(s[2]))
        elif kind == 'if':
            self.emit_if(s)
        elif kind == 'while':
            self.emit_while(s)
        elif kind == 'loop':
            top = self.fresh_label()
            self.label(top)
            self.stmts(s[1])
            self.jump(CLASS_JUMP, top)
        elif kind == 'switch':
            self.emit_switch(s)
        else:
            raise ValueError(f'cannot emit statement {kind}')

    def emit_while(self, s):
        _, condition, body = s
        top = self.fresh_label()
        end = self.fresh_label()
        self.label(top)
        self.expr(condition)
        self.jump(CLASS_BRANCH_IF_ZERO, end)
        self.stmts(body)
        self.jump(CLASS_JUMP, top)
        self.label(end)

    def emit_switch(self, s):
        _, subject, cases, default = s
        end = self.fresh_label()
        self.expr(subject)
        for n, (value, mode, body) in enumerate(cases):
            is_last = n == len(cases) - 1 and default is None
            if is_last:
                next_case = end
            else:
                next_case = self.fresh_label()
            self.misc(DUPLICATE)
            self.expr(value)
            self.ins(CLASS_ARITH, {'sub': SUBTRACT, 'mode': mode})
            self.jump(CLASS_BRANCH_IF_NONZERO, next_case)
            self.stmts(body)
            if not is_last:
                self.jump(CLASS_JUMP, end)
                self.label(next_case)
        if default is not None:
            self.stmts(default)
        self.label(end)
        self.misc(POP)

    def emit_if(self, s, chain_end=None):
        _, condition, then, other, then_jumps, else_jumps, shares_end = s
        if shares_end:
            end = chain_end
        else:
            end = self.fresh_label()
        if other is None:
            else_label = end
        else:
            else_label = self.fresh_label()
        self.expr(condition)
        self.jump(CLASS_BRANCH_IF_ZERO, else_label)
        self.stmts(then)
        if then_jumps:
            self.jump(CLASS_JUMP, end)
        if other is not None:
            self.label(else_label)
            if is_else_if_branch(other):
                self.emit_if(other[0], end)
            else:
                self.stmts(other)
                if else_jumps:
                    self.jump(CLASS_JUMP, end)
        if not shares_end:
            self.label(end)

    def label_positions(self):
        position = self.code_offset
        labels = {}
        for item in self.items:
            if item[0] == 'label':
                labels[item[1]] = position
            elif item[0] == 'ins':
                position += instruction_length(item[1], item[2])
            elif item[0] == 'raw':
                position += len(item[1])
        return labels

    def assemble(self):
        labels = self.label_positions()
        out = bytearray()
        position = self.code_offset
        previous_opcode = 0
        part_starts = []
        for item in self.items:
            kind = item[0]
            if kind == 'part':
                part_starts.append(position)
            elif kind == 'seed':
                previous_opcode = item[1]
            elif kind == 'raw':
                out += item[1]
                position += len(item[1])
            elif kind == 'ins':
                opcode, encoded = self.encode(item, position, previous_opcode, labels)
                out += encoded
                position += len(encoded)
                previous_opcode = opcode
        spans = []
        for n, start in enumerate(part_starts):
            if n + 1 < len(part_starts):
                spans.append((start, part_starts[n + 1]))
            else:
                spans.append((start, position))
        return bytes(out), spans

    def encode(self, item, position, previous_opcode, labels):
        _, cls, fields, operand_kind, value, exact = item
        if 'raw' in fields:
            opcode = fields['raw']
        elif exact is not None:
            opcode = exact
        else:
            opcode = compose(cls, fields, previous_opcode)
        length = instruction_length(cls, fields)
        encoded = struct.pack('<H', opcode)
        if operand_kind == 'imm':
            encoded += value
        elif operand_kind == 'fref':
            encoded += struct.pack('<i', labels[value] // 2)
        elif operand_kind == 'off':
            encoded += struct.pack('<h', value)
        elif operand_kind == 'data':
            encoded += struct.pack('<h', value - (position + 2))
        elif operand_kind == 'rel':
            target = jump_target(value, labels)
            encoded += struct.pack('<h', (target - (position + 4)) // 2)
        if len(encoded) != length:
            raise ValueError(f'encoded {len(encoded)} bytes, expected {length}')
        return opcode, encoded


def jump_target(label, labels):
    if label in labels:
        return labels[label]
    if ABSOLUTE_LABEL_RE.fullmatch(label):
        return int(label[2:], 16)
    if '.' in label:
        raise PartError(label.split('.')[0], ValueError(f'unknown label {label}'))
    raise ValueError(f'unknown label {label}')


def load_names(block_name):
    path = NAMES_DIR / f'{block_name}.json'
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def asm_listing(data, block_off, name, size):
    roles = bd.detect_roles(data, block_off, name, size)
    text = bd.disasm(data, block_off, name, size)
    listing = {}
    for line in text.splitlines():
        match = LISTING_LINE_RE.match(line)
        if not match:
            continue
        operand = match.group(3)
        if roles.get('self') is not None:
            operand = operand.replace('[self]', f'[glob+{roles["self"]}]')
        listing[int(match.group(1), 16) + block_off] = (match.group(2), operand)
    return listing


def code_region(data, block_off, name, size):
    end = min(block_off + 4 + size, len(data))
    start = bd.code_start(data, block_off, name, end)
    return start, bd.extend_end(data, block_off, start, end)


def is_scaffolding(instruction):
    if instruction['op'] == 0:
        return False
    if instruction['c'] == CLASS_JUMP:
        return True
    return instruction['c'] == CLASS_MISC and instruction['sub'] in SCAFFOLDING_MISC_OPS


class Part:
    def __init__(self, kind, lo, hi, entry):
        self.kind = kind
        self.lo = lo
        self.hi = hi
        self.entry = entry
        self.seed = None


class Block:
    def __init__(self, data, block_off, name, size, motions=None):
        self.data = data
        self.motions = motions
        self.block_off = block_off
        self.name = name
        self.start, self.end = code_region(data, block_off, name, size)
        self.instructions, self.order = bd._decode(data, self.start, self.end)
        self.signatures, analysis, calls = bd._signatures(self.instructions, self.order, self.start)
        self.entries = sorted({self.start} | set(calls))
        self.parts = self.split_parts(analysis)
        self.targets = set()
        for instruction in self.instructions.values():
            if instruction['c'] in JUMP_CLASSES:
                self.targets.add(bd._target(instruction))
        self.listing = asm_listing(data, block_off, name, size)
        names_file = load_names(name)
        self.routines = self.routine_names(names_file)
        roles = bd.detect_roles(data, block_off, name, size)
        glob = {int(offset): glob_name for offset, glob_name in names_file.get('glob', {}).items()}
        self.names = Names(glob, self.routines, roles.get('self'))
        self.funcs = {}
        for entry in self.entries:
            name_of_entry = self.routines[entry]
            self.funcs[name_of_entry] = (name_of_entry, self.signature(entry)[1])
        self.thread_starts = {}
        for offset, routine in self.routines.items():
            relative = offset - block_off
            if offset != self.start and relative % 2 == 0:
                self.thread_starts[relative // 2] = routine
        self.assign_seeds()

    def signature(self, entry):
        return self.signatures.get(entry, (0, 0))

    def pcs_between(self, lo, hi):
        return [pc for pc in self.order if lo <= pc < hi]

    def split_parts(self, analysis):
        parts = []
        for n, entry in enumerate(self.entries):
            if n + 1 < len(self.entries):
                next_entry = self.entries[n + 1]
            else:
                next_entry = self.end
            reachable = [pc for pc in analysis[entry]['depth'] if entry <= pc < next_entry]
            if not reachable:
                parts.append(Part('data', entry, next_entry, None))
                continue
            pcs = self.pcs_between(entry, next_entry)
            k = pcs.index(max(reachable)) + 1
            while k < len(pcs) and is_scaffolding(self.instructions[pcs[k]]):
                k += 1
            if k < len(pcs):
                hi = pcs[k]
            else:
                hi = next_entry
            parts.append(Part('func', entry, hi, entry))
            if hi < next_entry:
                parts.append(Part('data', hi, next_entry, None))
        return parts

    def routine_names(self, names_file):
        routines = {}
        for entry in self.entries:
            if entry == self.start:
                routines[entry] = 'entry'
            else:
                routines[entry] = f'sub_{entry - self.block_off:04X}'
        for label, routine in names_file.get('routines', {}).items():
            offset = int(label[2:], 16) + self.block_off
            if offset in routines and IDENT.fullmatch(routine) and routine not in RESERVED:
                routines[offset] = routine
        return routines

    def previous_opcode(self, pc):
        k = self.order.index(pc)
        if k > 0:
            return self.instructions[self.order[k - 1]]['op']
        return None

    def assign_seeds(self):
        previous_kind = None
        for part in self.parts:
            if part.kind == 'func':
                first = self.instructions[part.entry]
                previous = None
                if previous_kind != 'data':
                    previous = self.previous_opcode(part.entry)
                cls, fields = canonical_fields(first)
                if previous is None or 'raw' in fields or compose(cls, fields, previous) != first['op']:
                    part.seed = first['op']
            previous_kind = part.kind

    def header_comment(self, entry):
        return f' {{  // @L{entry - self.block_off:04X}'


def link_function_refs(node, thread_starts):
    if isinstance(node, list):
        return [link_function_refs(x, thread_starts) for x in node]
    if not isinstance(node, tuple) or not node:
        return node
    if node[0] in ('call', 'nat'):
        return node[:-1] + ([as_function_ref(arg, thread_starts) for arg in node[-1]],)
    if node[0] == 'storei':
        return ('storei', link_function_refs(node[1], thread_starts), as_function_ref(node[2], thread_starts))
    return tuple(link_function_refs(x, thread_starts) for x in node)


def as_function_ref(arg, thread_starts):
    if arg[0] == 'int' and arg[1] >= MIN_FUNCTION_REF and arg[1] in thread_starts:
        return ('fref', thread_starts[arg[1]])
    return link_function_refs(arg, thread_starts)


def count_label_refs(statements):
    refs = {}
    for s in statements:
        if s[0] == 'goto':
            label = s[1]
        elif s[0] in ('ifz', 'ifnz'):
            label = s[2]
        elif s[0] == 'swcase':
            label = s[3]
        else:
            continue
        refs[label] = refs.get(label, 0) + 1
    return refs


def function_header(name, param_count, return_count, frame, seed):
    params = ', '.join(f'a{k}' for k in range(param_count))
    head = f'    func {name}({params})'
    if return_count:
        head += f' -> {return_count}'
    if frame is not None:
        head += f' frame {frame}'
    if seed is not None:
        head += f' seed 0x{seed:04x}'
    return head


def check_labels_survive(lines, block, frame):
    emitter = Emitter(0)
    emitter.funcs = block.funcs
    emitter.scope = 'v.'
    if frame is not None:
        emitter.frame = frame
    for s in parse_statements('\n'.join(lines[1:-1]), block.names, block.funcs):
        emitter.stmt(s)
    defined = {item[1] for item in emitter.items if item[0] == 'label'}
    for item in emitter.items:
        if item[0] == 'ins' and item[3] == 'rel' and item[4] not in defined and item[4].startswith('v.'):
            raise Fail('label lost in structuring')


def structured_lines(block, part):
    param_count, return_count = block.signature(part.entry)
    builder = StatementBuilder(block.data, block.instructions, block.pcs_between(part.lo, part.hi),
                               block.targets, param_count, block.signatures, block.block_off)
    statements = link_function_refs(builder.build(), block.thread_starts)
    refs = count_label_refs(statements)
    own_labels = {s[1] for s in statements if s[0] == 'label'}
    for label in refs:
        if label not in own_labels:
            raise Fail('jump out of the function')
    tree = renumber(structure(statements, refs))
    head = function_header(block.routines[part.entry], param_count, return_count, builder.frame, part.seed)
    lines = [head + block.header_comment(part.entry)] + statement_lines(tree, block.names, 2, block.motions) + ['    }']
    check_labels_survive(lines, block, builder.frame)
    return lines


def try_structured_lines(block, part):
    try:
        return structured_lines(block, part)
    except Fail as failure:
        record_stat('fail: ' + str(failure)[:50])
    except (SyntaxError, ValueError, KeyError, IndexError, TypeError) as ex:
        record_stat(f'text: {type(ex).__name__}: {str(ex)[:50]}')
    return None


def asm_operand_names(operand, routines, block_off):
    def routine_or_label(match):
        offset = int(match.group(1), 16) + block_off
        return routines.get(offset, match.group(0))
    return re.sub(r'@L([0-9A-F]{4})\b', routine_or_label, operand)


def asm_lines(block, part):
    param_count, return_count = block.signature(part.entry)
    head = f'    func {block.routines[part.entry]} asm'
    if param_count or return_count:
        head += f' ({param_count}) -> {return_count}'
    if part.seed is not None:
        head += f' seed 0x{part.seed:04x}'
    out = [head + block.header_comment(part.entry)]
    if part.seed is not None:
        previous_opcode = part.seed
    else:
        previous_opcode = block.previous_opcode(part.entry)
    for pc in block.pcs_between(part.lo, part.hi):
        if pc != part.entry and (pc in block.targets or pc in block.routines):
            out.append(f'    @L{pc - block.block_off:04X}:')
        mnemonic, operand = block.listing[pc]
        operand = asm_operand_names(operand, block.routines, block.block_off)
        instruction = block.instructions[pc]
        cls, fields = canonical_fields(instruction)
        exact = ''
        if 'raw' not in fields and compose(cls, fields, previous_opcode) != instruction['op']:
            exact = f' ~0x{instruction["op"]:04x}'
        out.append(f'        {mnemonic} {operand}{exact}'.rstrip())
        previous_opcode = instruction['op']
    return out + ['    }']


def data_lines(block, part):
    out = [f'    data {{  // 0x{part.lo - block.block_off:04X}-0x{part.hi - block.block_off - 1:04X}']
    raw = block.data[part.lo:part.hi]
    for k in range(0, len(raw), 16):
        out.append('        ' + raw[k:k + 16].hex(' '))
    return out + ['    }']


def block_text(name, code_offset, names, body):
    lines = [f'bd {name} code 0x{code_offset:04X} {{']
    declarations = sorted(names.glob.items(), key=glob_offset)
    if declarations:
        lines.append('    names {')
        for offset, glob_name in declarations:
            lines.append(f'        {glob_name} = glob[{offset}];')
        lines += ['    }', '']
    return '\n'.join(lines + body + ['}']) + '\n'


class PartRenderer:
    def __init__(self, block, force_asm):
        self.block = block
        self.forced = set()
        if force_asm is not None:
            self.forced = set(force_asm)
        self.structured = {}
        self.asm = {}

    def lines(self, part):
        if part.kind == 'data':
            return data_lines(self.block, part)
        if part.lo not in self.forced:
            if part.lo not in self.structured:
                self.structured[part.lo] = try_structured_lines(self.block, part)
            if self.structured[part.lo] is not None:
                return self.structured[part.lo]
        if part.lo not in self.asm:
            self.asm[part.lo] = asm_lines(self.block, part)
        return self.asm[part.lo]

    def text(self):
        block = self.block
        body = []
        for part in block.parts:
            body += self.lines(part)
        return block_text(block.name, block.start - block.block_off, block.names, body)


def mismatched_functions(block, code, span_list):
    spans = {}
    if len(span_list) == len(block.parts):
        for part, (lo, hi) in zip(block.parts, span_list):
            spans[part.lo] = (lo + block.block_off, hi + block.block_off)
    functions = [part for part in block.parts if part.kind == 'func']
    wrong = []
    for part in functions:
        if part.lo not in spans:
            wrong.append(part.lo)
        else:
            start, end = spans[part.lo]
            if end - start != part.hi - part.lo:
                wrong.append(part.lo)
    if wrong:
        return wrong
    for part in functions:
        start, end = spans[part.lo]
        if code[start - block.start:end - block.start] != block.data[part.lo:part.hi]:
            wrong.append(part.lo)
    return wrong


def decompile_block(data, block_off, name, size, force_asm=None, motions=None):
    block = Block(data, block_off, name, size, motions)
    renderer = PartRenderer(block, force_asm)
    original = data[block.start:block.end]
    for _ in range(len(block.parts) + 2):
        text = renderer.text()
        code, span_list = compile_block(text, with_spans=True)
        if code == original:
            return text
        wrong = [lo for lo in mismatched_functions(block, code, span_list) if lo not in renderer.forced]
        if not wrong:
            raise AssertionError(f'{name}: round trip mismatch that no function explains')
        for lo in wrong:
            renderer.forced.add(lo)
            record_stat('bytes differ')
    raise AssertionError(f'{name}: round trip did not converge')


def parse_names_section(lines):
    glob = {}
    i = 1
    if lines[i].strip() == 'names {':
        i += 1
        while lines[i].strip() != '}':
            glob_name, _, value = lines[i].strip().rstrip(';').partition('=')
            offset = int(re.fullmatch(r'\s*glob\[(-?\d+)\]\s*', value).group(1))
            glob[offset] = glob_name.strip()
            i += 1
        i += 1
    return glob, i


def emit_asm_body(emitter, body, funcs):
    for line in body:
        line = line.split(';')[0].rstrip()
        if not line.strip():
            continue
        label = ASM_LABEL_RE.match(line)
        if label:
            emitter.label(label.group(1))
            continue
        exact = None
        exact_match = ASM_EXACT_OPCODE_RE.search(line)
        if exact_match:
            exact = int(exact_match.group(1), 16)
            line = line[:exact_match.start()]
        mnemonic, _, operand = line.strip().partition(' ')
        operand = operand.strip()
        function_target = None
        target_match = ASM_FUNCTION_TARGET_RE.match(operand)
        if mnemonic in ('jmp', 'bz', 'bnz', 'call') and target_match and target_match.group(1) in funcs:
            function_target = target_match.group(1)
            operand = '@L0000'
            if target_match.group(2):
                operand += target_match.group(2)
        cls, fields, operand_kind, value = bdasm.meaning(mnemonic, operand, 0)
        if function_target:
            value = function_target
        emitter.ins(cls, fields, operand_kind, value, exact)


def emit_bds_body(emitter, name, frame, body, names, funcs):
    emitter.scope = f'{name}.'
    if frame:
        emitter.frame = int(frame)
    else:
        emitter.frame = 0
    try:
        for s in parse_statements('\n'.join(body), names, funcs):
            emitter.stmt(s)
    except (SyntaxError, ValueError, KeyError, IndexError, TypeError) as ex:
        raise PartError(name, ex) from ex
    emitter.scope = ''


def data_bytes(body):
    hex_text = ''.join(line.split('//')[0] for line in body)
    return bytes.fromhex(hex_text.replace(' ', ''))


def emit_part(emitter, header, body, names, funcs):
    emitter.items.append(('part', len(emitter.items)))
    if header.startswith('    data {'):
        emitter.items.append(('raw', data_bytes(body)))
        return
    match = FUNC_RE.match(header)
    if not match:
        raise SyntaxError(f'bad part header {header!r}')
    name, _, is_asm, _, _, frame, seed = match.groups()
    if seed:
        emitter.items.append(('seed', int(seed, 16)))
    emitter.label(name)
    if is_asm:
        emit_asm_body(emitter, body, funcs)
    else:
        emit_bds_body(emitter, name, frame, body, names, funcs)


def declared_return_count(func_match):
    if func_match.group(5):
        return int(func_match.group(5))
    return 0


def compile_block(text, with_spans=False):
    lines = text.rstrip('\n').split('\n')
    header = BLOCK_RE.match(lines[0])
    if not header:
        raise SyntaxError(f'expected "bd NAME code 0x... {{", got {lines[0]!r}')
    code_offset = int(header.group(2), 16)
    glob, i = parse_names_section(lines)
    names = Names(glob)
    funcs = {}
    for line in lines[i:]:
        match = FUNC_RE.match(line)
        if match:
            funcs[match.group(1)] = (match.group(1), declared_return_count(match))
    emitter = Emitter(code_offset)
    emitter.funcs = funcs
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line == '}':
            i += 1
            continue
        part_end = i + 1
        while lines[part_end] != '    }':
            part_end += 1
        emit_part(emitter, line, lines[i + 1:part_end], names, funcs)
        i = part_end + 1
    code, spans = emitter.assemble()
    if with_spans:
        return code, spans
    return code_offset, code


def sibling_motions(mdls_path):
    mset_path = Path(mdls_path).with_suffix('.mset')
    try:
        return read_motion_dict(str(mset_path))
    except (FileNotFoundError, struct.error):
        return None


def decompile_file(path, only=None):
    data = Path(path).read_bytes()
    motions = sibling_motions(path)
    out = []
    for block_off, name, size in bd.find_blocks(data):
        if only is not None and only != name:
            continue
        out.append(decompile_block(data, block_off, name, size, motions=motions))
    return '\n'.join(out)


def split_blocks(text):
    blocks = {}
    current = None
    for line in text.split('\n'):
        match = BLOCK_RE.match(line)
        if match:
            current = match.group(1)
            blocks[current] = [line]
        elif current is not None:
            blocks[current].append(line)
            if line == '}':
                current = None
    return {name: '\n'.join(lines) + '\n' for name, lines in blocks.items()}


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
