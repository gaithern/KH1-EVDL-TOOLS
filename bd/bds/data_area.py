"""Where a .bd block's data area ends and its code begins, and what records the data area holds.

The block header is a `jmp init`; the engine has no boundary field. Code is what control flow reaches
from the header (plus thread / handler starts passed as offset/2 ints). Everything before the first
reachable instruction is data, split into records at every `&data[...]` target. The record types come
from where the pointers end up (which native, or which load), and only name the records.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'asm'))
import kh1_bd_disasm as bd

UNKNOWN = ('unknown',)
MAX_CHOICES = 32
MAX_DEPTH = 16
MAX_ROUNDS = 6

CODE_OFFSET_ARGS = {
    (0, 0x14): [0],
    (0, 0x22): [0],
    (0, 0x96): [0],
    (0, 0x21): [0, 1, 2, 3],
}

STAT_PAGE = 'stat page'
DROP_TABLE = 'drop table'
HIT_PARAMS = 'hit params'
TARGET_WEIGHTS = 'target weights'
TABLE_BLOB = 'table blob'
EFFECT_SCRIPT_ARG = 'effect script arg'

RECORD_SIZES = {
    STAT_PAGE: 0x6C,
    DROP_TABLE: 0x34,
    HIT_PARAMS: 0x70,
    TARGET_WEIGHTS: 0x14,
}

NATIVE_RECORDS = {
    (0, 0x2D): {'any': STAT_PAGE},
    (0, 0x7A): {'any': DROP_TABLE},
    (0, 0xD7): {'any': DROP_TABLE},
    (0, 0x17): {'any': HIT_PARAMS},
    (0, 0x5E): {3: EFFECT_SCRIPT_ARG, 4: EFFECT_SCRIPT_ARG},
    (0, 0x30): {1: TARGET_WEIGHTS},
    (0, 0xAB): {'any': TABLE_BLOB},
}


def native_arity(native):
    if native in bd.STUB_VERBS:
        return 0, 0
    return bd.ARITY.get(native, (0, 0))


def is_data_address_push(op):
    return (bd.opcode_class(op) == bd.CLASS_PUSH and bd.opcode_mode(op) == bd.PUSH_ADDRESS
            and bd.opcode_base(op) == bd.BASE_IMMEDIATE)


def jump_target(data, pos):
    return pos + 4 + bd.s16(data, pos + 2) * 2


class Reachability:
    def __init__(self, data, block_off, limit):
        self.data = data
        self.block_off = block_off
        self.limit = limit
        self.summaries = {}
        self.in_progress = set()
        self.code_bytes = set()
        self.lea_targets = set()
        self.function_starts = set()
        self.literal_code_refs = set()

    def summary(self, entry):
        if entry in self.summaries:
            return self.summaries[entry]
        if entry in self.in_progress:
            return (0, 0, set())
        self.in_progress.add(entry)
        result = self.run_function(entry)
        self.in_progress.discard(entry)
        self.summaries[entry] = result
        self.function_starts.add(entry)
        return result

    def run_function(self, entry):
        data = self.data
        visited = set()
        param_code_slots = set()
        returns = None
        consumed = [0]
        states = [(entry, [], {})]

        def pop(stack):
            if stack:
                return stack.pop()
            value = ('param', consumed[0])
            consumed[0] += 1
            return value

        def note_code_value(value):
            if value[0] == 'int':
                self.literal_code_refs.add(value[1])
            elif value[0] == 'param':
                param_code_slots.add(value[1])

        while states:
            pos, stack, local_values = states.pop()
            while self.block_off <= pos < self.limit and pos not in visited:
                visited.add(pos)
                op = bd.u16(data, pos)
                if bd.is_invalid_opcode(op):
                    break
                length = bd.ilen(op)
                for byte_pos in range(pos, pos + length):
                    self.code_bytes.add(byte_pos)
                cls = bd.opcode_class(op)
                mode = bd.opcode_mode(op)
                base = bd.opcode_base(op)
                sub = bd.opcode_sub(op)
                next_pos = pos + length
                if cls == bd.CLASS_UNARY:
                    if sub == bd.UNARY_YIELD:
                        pass
                    elif sub == bd.UNARY_RETURN:
                        if returns is None:
                            returns = len(stack)
                        break
                    elif sub == bd.UNARY_ABORT:
                        break
                    elif sub == bd.UNARY_POP:
                        pop(stack)
                    elif sub == bd.UNARY_STORE_INDIRECT:
                        pop(stack)
                        pop(stack)
                    elif sub == bd.UNARY_DUP:
                        value = pop(stack)
                        stack.append(value)
                        stack.append(value)
                    else:
                        pop(stack)
                        stack.append(UNKNOWN)
                elif cls == bd.CLASS_ARITH:
                    pop(stack)
                    pop(stack)
                    stack.append(UNKNOWN)
                elif cls == bd.CLASS_PUSH:
                    if mode == bd.PUSH_INT:
                        stack.append(('int', bd.i32(data, pos + 2)))
                    elif mode == bd.PUSH_FLOAT:
                        stack.append(UNKNOWN)
                    elif mode == bd.PUSH_ADDRESS:
                        if base == bd.BASE_IMMEDIATE:
                            self.lea_targets.add(pos + 2 + bd.s16(data, pos + 2))
                        stack.append(UNKNOWN)
                    else:
                        offset = bd.s16(data, pos + 2)
                        if base == 0 and sub == 1 and offset in local_values:
                            stack.append(local_values[offset])
                        else:
                            stack.append(UNKNOWN)
                elif cls == bd.CLASS_STORE:
                    value = pop(stack)
                    if base == 0:
                        local_values[bd.s16(data, pos + 2)] = value
                elif cls == bd.CLASS_JUMP:
                    next_pos = jump_target(data, pos)
                elif cls in (bd.CLASS_BRANCH_IF_ZERO, bd.CLASS_BRANCH_IF_NONZERO):
                    pop(stack)
                    states.append((jump_target(data, pos), list(stack), dict(local_values)))
                elif cls in (bd.CLASS_COMPARE, bd.CLASS_INDEX_ADD, bd.CLASS_LOAD):
                    pop(stack)
                    stack.append(UNKNOWN)
                elif cls == bd.CLASS_CALL:
                    param_count, return_count, callee_code_slots = self.summary(jump_target(data, pos))
                    arguments = []
                    for _ in range(param_count):
                        arguments.append(pop(stack))
                    for slot in callee_code_slots:
                        if slot < len(arguments):
                            note_code_value(arguments[slot])
                    for _ in range(return_count):
                        stack.append(UNKNOWN)
                elif cls == bd.CLASS_NATIVE:
                    native = (base, sub)
                    argument_count, return_count = native_arity(native)
                    arguments = []
                    for _ in range(argument_count):
                        arguments.append(pop(stack))
                    for slot in CODE_OFFSET_ARGS.get(native, []):
                        if slot < len(arguments):
                            note_code_value(arguments[slot])
                    if return_count:
                        stack.append(UNKNOWN)
                pos = next_pos
        if returns is None:
            returns = 0
        return (consumed[0], returns, param_code_slots)

    def run(self):
        pending = [self.block_off]
        done = set()
        while pending:
            entry = pending.pop()
            if entry in done:
                continue
            done.add(entry)
            self.summary(entry)
            for value in list(self.literal_code_refs):
                target = self.block_off + value * 2
                if self.block_off < target < self.limit and target not in done:
                    pending.append(target)
            for start in list(self.function_starts):
                if start not in done:
                    pending.append(start)

    def first_code(self):
        after_header = [pos for pos in self.code_bytes if pos >= self.block_off + 4]
        if not after_header:
            return self.limit
        return min(after_header)


def round_up(value, step):
    return (value + step - 1) // step * step


def table_blob_size(data, address):
    if address + 24 > len(data):
        return None
    words = struct.unpack_from('<6I', data, address)
    first_end = words[2] + words[4] * 2
    second_end = words[3] + words[5] * 2
    return round_up(max(first_end, second_end), 16)


def choices(value):
    if value[0] == 'any':
        return list(value[1])
    return [value]


def make_choice(values):
    unique = []
    for value in values:
        for member in choices(value):
            if member not in unique:
                unique.append(member)
    if not unique:
        return UNKNOWN
    if len(unique) == 1:
        return unique[0]
    if len(unique) > MAX_CHOICES:
        return UNKNOWN
    return ('any', tuple(unique))


def add_values(left, right):
    if left[0] == 'int' and right[0] == 'int':
        return ('int', left[1] + right[1])
    for pointer, other in ((left, right), (right, left)):
        if pointer[0] == 'data':
            if other[0] == 'int':
                return ('data', pointer[1], pointer[2] + other[1])
            if other[0] == 'mul':
                return ('indexed', pointer[1], pointer[2], other[2], other[1])
            return ('indexed', pointer[1], pointer[2], 1, UNKNOWN)
        if pointer[0] == 'glob' and other[0] == 'int':
            return ('glob', pointer[1] + other[1])
    return UNKNOWN


def multiply_values(left, right):
    if left[0] == 'int' and right[0] == 'int':
        return ('int', left[1] * right[1])
    if right[0] == 'int':
        return ('mul', left, right[1])
    if left[0] == 'int':
        return ('mul', right, left[1])
    return UNKNOWN


def arith(sub, left, right):
    left_choices = choices(left)
    right_choices = choices(right)
    if len(left_choices) * len(right_choices) > MAX_CHOICES:
        return UNKNOWN
    results = []
    for a in left_choices:
        for b in right_choices:
            if sub == 0:
                results.append(add_values(a, b))
            elif sub == 2:
                results.append(multiply_values(a, b))
            elif sub == 1 and a[0] == 'int' and b[0] == 'int':
                results.append(('int', a[1] - b[1]))
            elif sub == 1 and a[0] == 'data' and b[0] == 'int':
                results.append(('data', a[1], a[2] - b[1]))
            else:
                results.append(UNKNOWN)
    return make_choice(results)


def merge_state(seen_states, pos, stack, local_values, consumed):
    if pos not in seen_states:
        seen_states[pos] = (list(stack), dict(local_values), consumed)
        return list(stack), dict(local_values), consumed
    old_stack, old_locals, old_consumed = seen_states[pos]
    if len(old_stack) == len(stack):
        new_stack = []
        for old_value, value in zip(old_stack, stack):
            new_stack.append(make_choice([old_value, value]))
    else:
        new_stack = list(old_stack)
    new_locals = dict(old_locals)
    for offset, value in local_values.items():
        if offset in new_locals:
            new_locals[offset] = make_choice([new_locals[offset], value])
        else:
            new_locals[offset] = value
    new_consumed = max(old_consumed, consumed)
    if new_stack == old_stack and new_locals == old_locals and new_consumed == old_consumed:
        return None
    seen_states[pos] = (list(new_stack), dict(new_locals), new_consumed)
    return new_stack, new_locals, new_consumed


class PointerUse:
    def __init__(self, target, offset, kind, stride, index):
        self.target = target
        self.offset = offset
        self.kind = kind
        self.stride = stride
        self.index = index


class PointerTracking:
    def __init__(self, data, block_off, limit, reach):
        self.data = data
        self.block_off = block_off
        self.limit = limit
        self.reach = reach
        self.memory = {}
        self.memory_changed = False
        self.uses = []
        self.memo = {}
        self.in_progress = set()

    def note_use(self, value, kind):
        for member in choices(value):
            if member[0] == 'data':
                self.uses.append(PointerUse(member[1], member[2], kind, None, None))
            elif member[0] == 'indexed':
                self.uses.append(PointerUse(member[1], member[2], kind, member[3], member[4]))

    def store_memory(self, key, value):
        old = self.memory.get(key)
        if old is None:
            new = value
        else:
            new = make_choice([old, value])
        if new != old:
            self.memory[key] = new
            self.memory_changed = True

    def load_memory(self, key):
        return self.memory.get(key, UNKNOWN)

    def run(self):
        entries = set(self.reach.function_starts)
        entries.add(self.block_off)
        for value in self.reach.literal_code_refs:
            target = self.block_off + value * 2
            if self.block_off < target < self.limit:
                entries.add(target)
        for _ in range(MAX_ROUNDS):
            self.memory_changed = False
            self.uses = []
            self.memo = {}
            for entry in sorted(entries):
                param_count = self.reach.summaries.get(entry, (0, 0, set()))[0]
                self.call(entry, tuple([UNKNOWN] * param_count), 0)
            if not self.memory_changed:
                break

    def call(self, entry, arguments, depth):
        key = (entry, arguments)
        if key in self.memo:
            return self.memo[key]
        if key in self.in_progress or depth > MAX_DEPTH:
            return None
        self.in_progress.add(key)
        result = self.run_function(entry, arguments, depth)
        self.in_progress.discard(key)
        self.memo[key] = result
        return result

    def run_function(self, entry, arguments, depth):
        data = self.data
        seen_states = {}
        returned = []
        states = [(entry, [], {}, 0)]
        while states:
            pos, stack, local_values, consumed = states.pop()
            while self.block_off <= pos < self.limit:
                merged = merge_state(seen_states, pos, stack, local_values, consumed)
                if merged is None:
                    break
                stack, local_values, consumed = merged
                op = bd.u16(data, pos)
                if bd.is_invalid_opcode(op):
                    break
                cls = bd.opcode_class(op)
                mode = bd.opcode_mode(op)
                base = bd.opcode_base(op)
                sub = bd.opcode_sub(op)
                next_pos = pos + bd.ilen(op)

                def pop():
                    nonlocal consumed
                    if stack:
                        return stack.pop()
                    if consumed < len(arguments):
                        value = arguments[consumed]
                    else:
                        value = UNKNOWN
                    consumed += 1
                    return value

                def heap_key(offset):
                    owner = local_values.get(0, UNKNOWN)
                    if owner[0] == 'glob':
                        return owner[1] + offset
                    return None

                if cls == bd.CLASS_UNARY:
                    if sub == bd.UNARY_YIELD:
                        pass
                    elif sub == bd.UNARY_RETURN:
                        returned.append(list(stack))
                        break
                    elif sub == bd.UNARY_ABORT:
                        break
                    elif sub == bd.UNARY_POP:
                        pop()
                    elif sub == bd.UNARY_STORE_INDIRECT:
                        value = pop()
                        pointer = pop()
                        for member in choices(pointer):
                            if member[0] == 'glob':
                                self.store_memory(member[1], value)
                    elif sub == bd.UNARY_DUP:
                        value = pop()
                        stack.append(value)
                        stack.append(value)
                    else:
                        pop()
                        stack.append(UNKNOWN)
                elif cls == bd.CLASS_ARITH:
                    right = pop()
                    left = pop()
                    stack.append(arith(sub, left, right))
                elif cls == bd.CLASS_PUSH:
                    offset = bd.s16(data, pos + 2)
                    if mode == bd.PUSH_INT:
                        stack.append(('int', bd.i32(data, pos + 2)))
                    elif mode == bd.PUSH_FLOAT:
                        stack.append(UNKNOWN)
                    elif mode == bd.PUSH_ADDRESS:
                        if base == bd.BASE_IMMEDIATE:
                            stack.append(('data', pos + 2 + offset, 0))
                        elif base == 1:
                            stack.append(('glob', offset))
                        elif base == 2 and heap_key(offset) is not None:
                            stack.append(('glob', heap_key(offset)))
                        else:
                            stack.append(UNKNOWN)
                    else:
                        if base == 0:
                            stack.append(local_values.get(offset, UNKNOWN))
                        elif base == 1:
                            stack.append(self.load_memory(offset))
                        elif base == 2 and heap_key(offset) is not None:
                            stack.append(self.load_memory(heap_key(offset)))
                        else:
                            stack.append(UNKNOWN)
                elif cls == bd.CLASS_STORE:
                    value = pop()
                    offset = bd.s16(data, pos + 2)
                    if base == 0:
                        local_values[offset] = value
                    elif base == 1:
                        self.store_memory(offset, value)
                    elif base == 2 and heap_key(offset) is not None:
                        self.store_memory(heap_key(offset), value)
                elif cls == bd.CLASS_JUMP:
                    next_pos = jump_target(data, pos)
                elif cls in (bd.CLASS_BRANCH_IF_ZERO, bd.CLASS_BRANCH_IF_NONZERO):
                    pop()
                    states.append((jump_target(data, pos), list(stack), dict(local_values), consumed))
                elif cls == bd.CLASS_COMPARE:
                    pop()
                    stack.append(UNKNOWN)
                elif cls == bd.CLASS_INDEX_ADD:
                    pointer = pop()
                    results = []
                    for member in choices(pointer):
                        if member[0] == 'data':
                            results.append(('data', member[1], member[2] + sub * 4))
                        elif member[0] == 'glob':
                            results.append(('glob', member[1] + sub * 4))
                        else:
                            results.append(UNKNOWN)
                    stack.append(make_choice(results))
                elif cls == bd.CLASS_LOAD:
                    pointer = pop()
                    results = []
                    for member in choices(pointer):
                        if member[0] in ('data', 'indexed'):
                            self.note_use(member, ('read', sub * 4))
                            results.append(UNKNOWN)
                        elif member[0] == 'glob':
                            results.append(self.load_memory(member[1]))
                        else:
                            results.append(UNKNOWN)
                    stack.append(make_choice(results))
                elif cls == bd.CLASS_CALL:
                    callee = jump_target(data, pos)
                    param_count, return_count, _ = self.reach.summary(callee)
                    call_arguments = []
                    for _ in range(param_count):
                        call_arguments.append(pop())
                    result = self.call(callee, tuple(call_arguments), depth + 1)
                    for index in range(return_count):
                        if result is not None and index < len(result):
                            stack.append(result[index])
                        else:
                            stack.append(UNKNOWN)
                elif cls == bd.CLASS_NATIVE:
                    native = (base, sub)
                    argument_count, return_count = native_arity(native)
                    popped = []
                    for _ in range(argument_count):
                        popped.append(pop())
                    left_to_right = list(reversed(popped))
                    record_map = NATIVE_RECORDS.get(native, {})
                    for position, value in enumerate(left_to_right):
                        kind = record_map.get(position, record_map.get('any'))
                        if kind is None:
                            kind = ('native', native, position)
                        self.note_use(value, kind)
                    if return_count:
                        stack.append(UNKNOWN)
                pos = next_pos
        if not returned:
            return []
        width = min(len(values) for values in returned)
        merged = []
        for index in range(width):
            merged.append(make_choice([values[len(values) - width + index] for values in returned]))
        return merged


def record_kind_names(uses, target):
    names = []
    for use in uses:
        if use.target != target or use.offset != 0:
            continue
        if isinstance(use.kind, str) and use.kind not in names:
            names.append(use.kind)
    return names


class Record:
    def __init__(self, lo, hi, kinds):
        self.lo = lo
        self.hi = hi
        self.kinds = kinds


class DataArea:
    def __init__(self, data, block_off, limit):
        reach = Reachability(data, block_off, limit)
        reach.run()
        self.code_start = reach.first_code()
        tracking = PointerTracking(data, block_off, limit, reach)
        tracking.run()
        targets = sorted(t for t in reach.lea_targets if block_off + 4 <= t < self.code_start)
        if targets:
            self.header_end = targets[0]
        else:
            self.header_end = self.code_start
        self.records = []
        for index, target in enumerate(targets):
            if index + 1 < len(targets):
                end = targets[index + 1]
            else:
                end = self.code_start
            self.records.append(Record(target, end, record_kind_names(tracking.uses, target)))

    def add_leading_record(self, lo):
        if lo < self.header_end:
            self.records.insert(0, Record(lo, self.header_end, []))
            self.header_end = lo

    def split_at(self, target):
        for index, record in enumerate(self.records):
            if record.lo < target < record.hi:
                first = Record(record.lo, target, record.kinds)
                second = Record(target, record.hi, record.kinds)
                self.records[index:index + 1] = [first, second]
                return
