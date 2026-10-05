"""EVS: a C-like view of KGR bytecode. decompile(stream) -> text, compile_text(text) -> stream.
The round trip is exact; a thread the decompiler cannot express is kept as an asm block.
"""
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import evdl_format

HERE = Path(__file__).parent

HEADER = 0
ALU = 1
JMP = 2
BEQZ = 3
YIELD_OPCODE = 5
STORE_REG = 6
CMP_REG_IMM = 7
DEC_REG_IDX = 8
PUSH = 9
LOAD_LOCAL = 10
STORE_LOCAL = 11
PUSH_ACTOR = 21
INIT_CALL = 22
AWAIT_CALL = 23
SYSCALL = 24
BRANCH_OPCODES = (JMP, BEQZ)
TASK_OPCODES = (INIT_CALL, AWAIT_CALL)

YIELD_OPERAND = 0x10
MAX_THREAD_ENTRIES = 256
MIN_ENTRIES = 11
SET_CHAR_ID = 10
PARTY_ID_LIMIT = 0x10
PARTY_ENTITY_COUNT = 10


def load_arity_tables():
    arity = {}
    for file_name in ('syscall_arity.json', 'arity_overrides.json'):
        table = json.loads((HERE / file_name).read_text())
        for syscall_id, info in table.items():
            arity[int(syscall_id)] = (info['args'], info['returns'])
    return arity


ARITY = load_arity_tables()
VARIADIC = {377, 378, 375, 376}

LABELS = dict(evdl_format.SAVE_DATA_LABELS)
LABEL_VAR = {name: var for var, name in LABELS.items()}


def load_bit_labels():
    table = json.loads((evdl_format.DATA_DIR / 'bit_labels.json').read_text())
    return {int(bit, 16): name for bit, name in table.items()}


BIT_LABELS = load_bit_labels()
BIT_LABEL_NUM = {name: bit for bit, name in BIT_LABELS.items()}


def unique_or_numbered_names(table, numbered_prefix):
    usage = {}
    for name in table.values():
        usage[name] = usage.get(name, 0) + 1
    result = {}
    for number, name in table.items():
        if usage[name] == 1:
            result[number] = name
        else:
            result[number] = f'{numbered_prefix}{number}'
    return result


SYS_NAME = unique_or_numbered_names(evdl_format.SYSCALLS, 'sys_')
SYS_ID = {name: syscall_id for syscall_id, name in SYS_NAME.items()}

BINOP = {0: '+', 1: '-', 2: '*', 3: '/', 4: '%', 6: '==', 7: '>', 8: '>=', 9: '<', 10: '<=',
         11: '!=', 12: '&', 13: '|', 14: '^', 16: '<<'}
UNOP = {5: '-', 15: '~'}
BINFN = {17}
BINOP_ID = {symbol: number for number, symbol in BINOP.items()}
UNOP_ID = {symbol: number for number, symbol in UNOP.items()}

WIDTH = {12: 'byte', 14: 'word', 16: 'dword', 30: 'bit'}
WRITE = {13: 'byte', 15: 'word', 17: 'dword', 31: 'bit'}
READ_OP = {width: opcode for opcode, width in WIDTH.items()}
WRITE_OP = {width: opcode for opcode, width in WRITE.items()}

INTRINSIC = {6: (1, 0), 7: (0, 1), 8: (0, 0), 25: (2, 0), 26: (0, 1), 27: (0, 1), 28: (0, 1), 29: (0, 1)}
INTR_NAME = {opcode: '__' + evdl_format.OPCODES[opcode] for opcode in INTRINSIC}
INTR_ID = {name: opcode for opcode, name in INTR_NAME.items()}

ASM_NAME = unique_or_numbered_names(evdl_format.OPCODES, 'op')
ASM_ID = {name: opcode for opcode, name in ASM_NAME.items()}

SAVE_DATA_END = 0x900
RUNTIME_LOW_END = 0xB00
SAVE_DATA_HIGH_END = 0xC80
SAVE_DATA2_BASE = 0xD40
SAVE_DATA_HIGH_SHIFT = 0x200

SLOT = {0: 'init', 1: 'main', 3: 'on_action', 4: 'on_hit', 5: 'on_talk', 6: 'on_touch', 7: 'on_lockon'}
EVENT_SLOTS = {3, 4, 5, 6, 7}
SLOT_ID = {name: slot for slot, name in SLOT.items()}

WARNINGS = []
COMPILE_WARNINGS = []
IDENT_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
RESERVED = {'thread', 'entry', 'level', 'if', 'else', 'while', 'goto', 'start', 'await', 'messages',
            'switch', 'case', 'default', 'break',
            'yield', 'raw', 'asm', 'bit', 'save_data', 'save_data2', 'runtime'} | set(SLOT.values())

WORLD_PREFIX = {0: 'dh', 1: 'di', 2: 'dc', 3: 'tw', 4: 'aw', 5: 'tz', 6: 'po', 8: 'al', 9: 'lm',
                10: 'nm', 11: 'he', 12: 'pi', 13: 'pp', 15: 'pc', 16: 'ew'}
WORLD_NAME = {0: 'WORLD_DIVE_TO_THE_HEART', 1: 'WORLD_DESTINY_ISLANDS', 2: 'WORLD_DISNEY_CASTLE',
              3: 'WORLD_TRAVERSE_TOWN', 4: 'WORLD_WONDERLAND', 5: 'WORLD_DEEP_JUNGLE',
              6: 'WORLD_100_ACRE_WOOD', 8: 'WORLD_AGRABAH', 9: 'WORLD_ATLANTICA',
              10: 'WORLD_HALLOWEEN_TOWN', 11: 'WORLD_OLYMPUS_COLISEUM', 12: 'WORLD_MONSTRO',
              13: 'WORLD_NEVERLAND', 15: 'WORLD_HOLLOW_BASTION', 16: 'WORLD_END_OF_THE_WORLD'}
WORLD_ID = {prefix: world for world, prefix in WORLD_PREFIX.items()}
MAX_AREA = 0x40

BREAK = '__break'


class Fail(Exception):
    pass


def number_text(number):
    if number < 10:
        return str(number)
    return f'0x{number:X}'


def quote(text):
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


def unquote(token):
    return re.sub(r'\\(.)', r'\1', token[1:-1])


def constant_slug(text):
    return re.sub(r'[^A-Z0-9]+', '_', text.upper().replace("'", '')).strip('_')


def unique_name(base, taken):
    name = base
    suffix = 2
    while name in taken:
        name = f'{base}_{suffix}'
        suffix += 1
    taken.add(name)
    return name


def area_name(prefix, area):
    return f'{prefix.upper()}{area + 1:02d}'


def gift_names():
    import entities
    names = {}
    for (world, gift), location in entities.gift_locations().items():
        slug = constant_slug(location)
        world_words = WORLD_NAME.get(world, '').replace('WORLD_', '', 1)
        if world_words and slug.startswith(world_words + '_'):
            slug = WORLD_PREFIX[world].upper() + slug[len(world_words):]
        names[(world, gift)] = f'GIFT_{slug}'
    return names


def item_const_names():
    import entities
    names = {}
    for item_id, item_name in entities.item_names().items():
        names[item_id] = 'ITEM_' + constant_slug(item_name)
    usage = {}
    for name in names.values():
        usage[name] = usage.get(name, 0) + 1
    result = {}
    for item_id, name in names.items():
        if usage[name] == 1:
            result[item_id] = name
        else:
            result[item_id] = f'{name}_{item_id:X}'
    return result


GIFT_NAME = gift_names()
ITEM_NAME = item_const_names()


def global_constants():
    constants = {name: world for world, name in WORLD_NAME.items()}
    for (world, gift), name in GIFT_NAME.items():
        constants[name] = gift
    for item_id, name in ITEM_NAME.items():
        constants[name] = item_id
    for prefix in WORLD_PREFIX.values():
        for area in range(MAX_AREA):
            constants[area_name(prefix, area)] = area
    return constants


GLOBAL_CONSTS = global_constants()

ENTITY_ARG_SYSCALLS = {SYS_ID[name] for name in (
    'Set_char_ID', 'Display_model', 'Discard_object_data', 'Load_model', 'Message_to_battle_script',
    'Change_appear_flag', 'Transfer_object_SE', 'Delete_save_point')}
GET_WORLD_NUMBER = SYS_ID['Get_world_number']
GET_AREA_NUMBER = SYS_ID['Get_area_number']
MAP_CHANGE_REWRITE_SET = SYS_ID['Start_map_change_rewrite_set']
GIFT_ARG = {SYS_ID['Get_item_from_gift_table']: 0, SYS_ID['Display_message_from_gift_table']: 1,
            SYS_ID['Scale_window_from_gift']: 1}
ITEM_ARG_SYSCALLS = {SYS_ID[name] for name in (
    'Change_bag_items', 'Check_bag_item_count', 'Check_bag_item_count_only', 'Check_bag_item_count2',
    'Get_item_type', 'Set_item_number_in_message', 'Change_weapon')}
GIFT_TABLE_ITEM_VAR = 0x1104
TRIGGER_EVENT = SYS_ID['Trigger_event']
DISPLAY_MESSAGE = SYS_ID['Display_message']

TYPED_MEMORY = {('byte', 0xD40): 'world', ('byte', 0xD5C): 'world',
                ('byte', 0xD41): 'area'}


def branch_target(pc, operand):
    return pc + evdl_format.sign24(operand)


def memory_region(var):
    if var < SAVE_DATA_END:
        return 'save_data', var
    if var < RUNTIME_LOW_END:
        return 'runtime', var
    if var < SAVE_DATA_HIGH_END:
        return 'save_data', var - SAVE_DATA_HIGH_SHIFT
    if var < SAVE_DATA2_BASE:
        return 'runtime', var
    return 'save_data2', var - SAVE_DATA2_BASE


def mem_raw(width, var):
    if width == 'bit':
        return f'bit[{number_text(var)}]'
    region, offset = memory_region(var)
    if width == 'byte':
        return f'{region}[{number_text(offset)}]'
    return f'{region}.{width}[{number_text(offset)}]'


def mem_var(region, offset):
    if region == 'bit' or region == 'runtime':
        return offset
    if region == 'save_data':
        if offset < SAVE_DATA_END:
            return offset
        return offset + SAVE_DATA_HIGH_SHIFT
    if region == 'save_data2':
        return offset + SAVE_DATA2_BASE
    raise ValueError(region)


def decode(stream):
    instructions = []
    for position in range(0, len(stream) - 3, 4):
        operand = stream[position] | (stream[position + 1] << 8) | (stream[position + 2] << 16)
        instructions.append((stream[position + 3], operand))
    return instructions


class Naming:
    def __init__(self, thread_names, entity_names, messages):
        self.thread_names = thread_names
        self.entity_names = entity_names
        self.messages = messages
        self.entry_aliases = {}
        self.memory_aliases = {}
        self.local_aliases = {}

    def with_local_aliases(self, local_aliases):
        thread_naming = copy.copy(self)
        thread_naming.local_aliases = local_aliases
        return thread_naming

    def thread(self, index):
        return self.thread_names.get(index, f'thread_{index}')

    def local(self, number):
        return self.local_aliases.get(number, f'local{number}')

    def entry(self, entry, bound, thread=None):
        if (thread, entry) in self.entry_aliases:
            return self.entry_aliases[(thread, entry)]
        if entry in EVENT_SLOTS and not bound:
            return f'entry_{entry}'
        return SLOT.get(entry, f'entry_{entry}')

    def memory(self, width, var):
        if (width, var) in self.memory_aliases:
            return self.memory_aliases[(width, var)]
        if width == 'bit':
            if var in BIT_LABELS:
                return BIT_LABELS[var]
            return f'bit[{number_text(var)}]'
        if var in LABELS:
            if width == 'byte':
                return LABELS[var]
            return f'{LABELS[var]}.{width}'
        return mem_raw(width, var)


def entity_ident(entity_id, entities):
    if entity_id in entities:
        name = re.sub(r'[^A-Za-z0-9_]', '_', entities[entity_id]).lower().strip('_')
    elif entity_id == 0:
        name = 'sora'
    elif entity_id < PARTY_ID_LIMIT:
        name = f'player{entity_id}'
    else:
        return None
    if not re.fullmatch(r'[a-z][a-z0-9_]+', name):
        return None
    if name in RESERVED or re.fullmatch(r'(local|sys_|thread_|entry_)\d+', name):
        return None
    return name


def bound_entity_id(instructions, header_pc, first_yield_pc):
    for pc in range(header_pc + 2, first_yield_pc):
        if instructions[pc] == (SYSCALL, SET_CHAR_ID) and instructions[pc - 1][0] == PUSH:
            return instructions[pc - 1][1]
    return None


def thread_names(instructions, threads, entities):
    names = {}
    used = set()
    for index, (header_pc, yield_pcs) in enumerate(threads):
        entity_id = bound_entity_id(instructions, header_pc, yield_pcs[0])
        if entity_id is None:
            continue
        base = entity_ident(entity_id, entities)
        if not base:
            continue
        names[index] = unique_name(base, used)
    return names


def entity_consts(entities):
    taken = set(GLOBAL_CONSTS) | set(LABEL_VAR) | set(BIT_LABEL_NUM)
    names = {}
    pool = dict(entities)
    for entity_id in range(PARTY_ENTITY_COUNT):
        if entity_id == 0:
            pool.setdefault(entity_id, 'SORA')
        else:
            pool.setdefault(entity_id, f'PLAYER{entity_id}')
    for entity_id in sorted(pool):
        base = re.sub(r'[^A-Za-z0-9_]', '_', pool[entity_id]).upper().strip('_')
        if not re.fullmatch(r'[A-Z][A-Z0-9_]+', base):
            continue
        names[entity_id] = unique_name(base, taken)
    return names


def used_entities(text, naming):
    used = set()
    for entity_id, name in naming.entity_names.items():
        if re.search(rf'\b{name}\b', text):
            used.add(entity_id)
    return sorted(used)


def split_threads(instructions):
    threads = []
    pc = 0
    count = len(instructions)
    while pc < count:
        opcode, entry_count = instructions[pc]
        if opcode != HEADER or not 1 <= entry_count <= MAX_THREAD_ENTRIES:
            break
        yield_pcs = []
        scan = pc + 1
        while len(yield_pcs) < entry_count and scan < count:
            if instructions[scan][0] == YIELD_OPCODE:
                yield_pcs.append(scan)
            scan += 1
        if len(yield_pcs) < entry_count:
            break
        threads.append((pc, yield_pcs))
        pc = scan
    return threads, pc


def const_text(constant, naming):
    value = constant[1]
    value_tag = None
    if len(constant) > 2:
        value_tag = constant[2]
    is_tuple_tag = isinstance(value_tag, tuple)
    if value_tag == 'world' and value in WORLD_NAME:
        return WORLD_NAME[value]
    if is_tuple_tag and value_tag[0] == 'area' and value < MAX_AREA:
        return area_name(value_tag[1], value)
    if value_tag == 'entity' and value in naming.entity_names:
        return naming.entity_names[value]
    if value_tag == 'kgr':
        return str(value)
    if value_tag == 'item' and value in ITEM_NAME:
        return ITEM_NAME[value]
    if is_tuple_tag and value_tag[0] == 'gift' and (value_tag[1], value) in GIFT_NAME:
        return GIFT_NAME[(value_tag[1], value)]
    if value_tag == 'msg':
        if value in naming.messages:
            return f'messages[{number_text(value)}]={quote(naming.messages[value])}'
        return f'messages[{number_text(value)}]'
    return number_text(value)


def intrinsic_operand(intrinsic):
    return ('const', intrinsic[2]) + tuple(intrinsic[4:5])


def expr_text(expression, naming, top=True):
    kind = expression[0]
    if kind == 'const':
        return const_text(expression, naming)
    if kind == 'actor':
        return naming.thread(expression[1])
    if kind == 'mem':
        return naming.memory(expression[1], expression[2])
    if kind == 'local':
        return naming.local(expression[1])
    if kind == 'un':
        operand = expr_text(expression[2], naming, False)
        return f'{UNOP[expression[1]]}{operand}'
    if kind == 'bin' and expression[1] in BINFN:
        left = expr_text(expression[2], naming)
        right = expr_text(expression[3], naming)
        return f'__alu{expression[1]}({left}, {right})'
    if kind == 'bin':
        left = expr_text(expression[2], naming, False)
        right = expr_text(expression[3], naming, False)
        text = f'{left} {BINOP[expression[1]]} {right}'
        if top:
            return text
        return f'({text})'
    if kind == 'keep':
        return f'__push({expr_text(expression[1], naming)})'
    if kind == 'nop':
        return f'__nop({expr_text(expression[1], naming)})'
    if kind == 'call':
        name = SYS_NAME.get(expression[1], f'sys_{expression[1]}')
        arguments = [expr_text(argument, naming) for argument in expression[2]]
        return f'{name}({", ".join(arguments)})'
    if kind == 'intr':
        arguments = [const_text(intrinsic_operand(expression), naming)]
        arguments += [expr_text(argument, naming) for argument in expression[3]]
        return f'{INTR_NAME[expression[1]]}({", ".join(arguments)})'
    raise ValueError(expression)


def value_type(expression, world, variable_types):
    kind = expression[0]
    if kind == 'mem' and (expression[1], expression[2]) in TYPED_MEMORY:
        memory_type = TYPED_MEMORY[(expression[1], expression[2])]
        if memory_type == 'world':
            return 'world'
        if world:
            return ('area', world)
        return None
    if kind in ('local', 'mem'):
        return variable_types.get(expression)
    if kind == 'call' and expression[1] == GET_WORLD_NUMBER:
        return 'world'
    if kind == 'call' and expression[1] == GET_AREA_NUMBER and world:
        return ('area', world)
    return None


def is_const(expression):
    return expression[0] == 'const'


def tag_const(expression, value_tag):
    return ('const', expression[1], value_tag)


def tag_comparison(expression, world, entity_ids, variable_types):
    left = tag_constants(expression[2], world, entity_ids, variable_types)
    right = tag_constants(expression[3], world, entity_ids, variable_types)
    if expression[1] in (BINOP_ID['=='], BINOP_ID['!=']):
        left_type = value_type(left, world, variable_types)
        right_type = value_type(right, world, variable_types)
        if left_type and is_const(right):
            right = tag_const(right, left_type)
        if right_type and is_const(left):
            left = tag_const(left, right_type)
    return ('bin', expression[1], left, right)


def tag_message_argument(argument):
    if is_const(argument):
        return tag_const(argument, 'msg')
    if argument[0] == 'bin' and argument[1] == BINOP_ID['+'] and is_const(argument[2]):
        return ('bin', argument[1], tag_const(argument[2], 'msg'), argument[3])
    return argument


def tag_call(expression, world, entity_ids, variable_types):
    syscall = expression[1]
    arguments = [tag_constants(argument, world, entity_ids, variable_types) for argument in expression[2]]
    first_is_const = bool(arguments) and is_const(arguments[0])
    if syscall in ENTITY_ARG_SYSCALLS and first_is_const and arguments[0][1] in entity_ids:
        arguments[0] = tag_const(arguments[0], 'entity')
    if syscall == DISPLAY_MESSAGE and len(arguments) == 2:
        arguments[1] = tag_message_argument(arguments[1])
    if syscall in ITEM_ARG_SYSCALLS and first_is_const:
        arguments[0] = tag_const(arguments[0], 'item')
    gift_index = GIFT_ARG.get(syscall)
    if gift_index is not None and len(arguments) > gift_index and is_const(arguments[gift_index]) and world in WORLD_ID:
        arguments[gift_index] = tag_const(arguments[gift_index], ('gift', WORLD_ID[world]))
    if syscall == TRIGGER_EVENT and first_is_const:
        arguments[0] = tag_const(arguments[0], 'kgr')
    if syscall == MAP_CHANGE_REWRITE_SET and len(arguments) == 4 and is_const(arguments[0]):
        world_number = arguments[0][1]
        arguments[0] = tag_const(arguments[0], 'world')
        if is_const(arguments[1]) and world_number in WORLD_PREFIX:
            arguments[1] = tag_const(arguments[1], ('area', WORLD_PREFIX[world_number]))
    return ('call', syscall, arguments)


def tag_constants(expression, world, entity_ids, variable_types):
    kind = expression[0]
    if kind == 'bin':
        return tag_comparison(expression, world, entity_ids, variable_types)
    if kind == 'un':
        return ('un', expression[1], tag_constants(expression[2], world, entity_ids, variable_types))
    if kind == 'call':
        return tag_call(expression, world, entity_ids, variable_types)
    if kind == 'intr':
        arguments = [tag_constants(argument, world, entity_ids, variable_types) for argument in expression[3]]
        return ('intr', expression[1], expression[2], arguments)
    return expression


def message_locals(statements):
    locals_ = set()
    for statement in statements:
        if statement[0] != 'expr':
            continue
        expression = statement[1]
        if expression[0] != 'call' or expression[1] != DISPLAY_MESSAGE or len(expression[2]) != 2:
            continue
        if expression[2][1][0] == 'local':
            locals_.add(expression[2][1])
    return locals_


class StatementTyper:
    def __init__(self, statements, world, entity_ids):
        self.world = world
        self.entity_ids = entity_ids
        self.message_locals = message_locals(statements)
        self.variable_types = {}
        self.switch_value_type = None

    def tag(self, expression):
        return tag_constants(expression, self.world, self.entity_ids, self.variable_types)

    def assignment(self, statement):
        target = statement[1]
        value = self.tag(statement[2])
        value_kind = value_type(value, self.world, self.variable_types)
        variable = target[:3]
        if value_kind:
            self.variable_types[variable] = value_kind
        else:
            self.variable_types.pop(variable, None)
        if target in self.message_locals and is_const(value):
            value = tag_const(value, 'msg')
        if target[0] == 'mem' and target[2] == GIFT_TABLE_ITEM_VAR and is_const(value) and self.world in WORLD_ID:
            value = tag_const(value, ('gift', WORLD_ID[self.world]))
        return ('assign', target, value)

    def expression_statement(self, statement):
        expression = self.tag(statement[1])
        if expression[0] == 'intr' and expression[1] == STORE_REG:
            self.switch_value_type = value_type(expression[3][0], self.world, self.variable_types)
        return ('expr', expression)

    def conditional_jump(self, statement):
        condition = self.tag(statement[1])
        if condition[0] == 'intr' and condition[1] == CMP_REG_IMM and self.switch_value_type:
            condition = condition + (self.switch_value_type,)
        return ('ifnot', condition, statement[2])

    def task(self, statement):
        arguments = [self.tag(argument) for argument in statement[3]]
        return ('task', statement[1], statement[2], arguments)

    def type_statement(self, statement):
        kind = statement[0]
        if kind == 'assign':
            return self.assignment(statement)
        if kind == 'expr':
            return self.expression_statement(statement)
        if kind == 'ifnot':
            return self.conditional_jump(statement)
        if kind == 'task':
            return self.task(statement)
        return statement


def type_stmts(statements, world, entity_ids):
    typer = StatementTyper(statements, world, entity_ids)
    return [typer.type_statement(statement) for statement in statements]


def pushes_value(opcode):
    return opcode in (PUSH, PUSH_ACTOR, LOAD_LOCAL) or opcode in WIDTH


def pushed_value(opcode, operand):
    if opcode == PUSH:
        return ('const', operand)
    if opcode == PUSH_ACTOR:
        return ('actor', operand)
    if opcode == LOAD_LOCAL:
        return ('local', operand)
    return ('mem', WIDTH[opcode], operand)


class EntryDecompiler:
    def __init__(self, instructions, targets):
        self.instructions = instructions
        self.targets = targets
        self.stack = []
        self.statements = []

    def flush_stack(self):
        for value in self.stack:
            if value[0] == 'call':
                self.statements.append(('expr', value))
            else:
                self.statements.append(('expr', ('keep', value)))
        self.stack.clear()

    def finish_statement(self, statement):
        self.flush_stack()
        self.statements.append(statement)

    def pop(self, count, pc):
        if len(self.stack) < count:
            opcode, operand = self.instructions[pc]
            detail = ''
            if opcode == SYSCALL:
                detail = SYS_NAME.get(operand, operand)
            raise Fail(f'stack underflow at {evdl_format.OPCODES[opcode]} {detail}')
        first = len(self.stack) - count
        values = self.stack[first:]
        del self.stack[first:]
        return values

    def decompile(self, start, end):
        nop_pending = False
        for pc in range(start, end):
            if pc in self.targets:
                if nop_pending:
                    raise Fail('jump target after nop')
                self.finish_statement(('label', f'L{pc}'))
            opcode, operand = self.instructions[pc]
            if nop_pending and not pushes_value(opcode):
                raise Fail('nop inside an expression')
            if opcode == HEADER and operand == 0 and self.stack:
                nop_pending = True
                continue
            if pushes_value(opcode):
                value = pushed_value(opcode, operand)
                if nop_pending:
                    value = ('nop', value)
                    nop_pending = False
                self.stack.append(value)
                continue
            self.decompile_instruction(pc, opcode, operand)
        self.flush_stack()
        if end in self.targets:
            self.statements.append(('label', f'L{end}'))
        return self.statements

    def decompile_instruction(self, pc, opcode, operand):
        if opcode == ALU:
            self.decompile_alu(pc, operand)
        elif opcode in WRITE or opcode == STORE_LOCAL:
            value = self.pop(1, pc)[0]
            if opcode == STORE_LOCAL:
                target = ('local', operand)
            else:
                target = ('mem', WRITE[opcode], operand)
            self.finish_statement(('assign', target, value))
        elif opcode == SYSCALL:
            self.decompile_syscall(pc, operand)
        elif opcode in TASK_OPCODES:
            arguments = self.pop(2, pc)
            self.finish_statement(('task', opcode, operand, arguments))
        elif opcode in INTRINSIC:
            pops, pushes = INTRINSIC[opcode]
            intrinsic = ('intr', opcode, operand, self.pop(pops, pc))
            if pushes:
                self.stack.append(intrinsic)
            else:
                self.finish_statement(('expr', intrinsic))
        elif opcode == YIELD_OPCODE:
            self.finish_statement(('yield', operand))
        elif opcode in BRANCH_OPCODES:
            self.decompile_branch(pc, opcode, operand)
        else:
            self.finish_statement(('op', opcode, operand))

    def decompile_alu(self, pc, operation):
        if operation in BINOP or operation in BINFN:
            left, right = self.pop(2, pc)
            self.stack.append(('bin', operation, left, right))
        elif operation in UNOP:
            self.stack.append(('un', operation, self.pop(1, pc)[0]))
        else:
            raise Fail(f'alu {operation}')

    def decompile_syscall(self, pc, syscall):
        if syscall not in ARITY:
            raise Fail(f'syscall {syscall} arity unknown')
        argument_count, return_count = ARITY[syscall]
        if syscall in VARIADIC and return_count == 0:
            argument_count = max(argument_count, len(self.stack))
        call = ('call', syscall, self.pop(argument_count, pc))
        if return_count == 1:
            self.stack.append(call)
        elif return_count == 0:
            self.finish_statement(('expr', call))
        else:
            raise Fail('multi-return')

    def decompile_branch(self, pc, opcode, operand):
        target = branch_target(pc, operand)
        if target not in self.targets:
            raise Fail('branch out of stream')
        if opcode == JMP:
            self.finish_statement(('goto', f'L{target}'))
        else:
            condition = self.pop(1, pc)[0]
            self.finish_statement(('ifnot', condition, f'L{target}'))


def case_values(condition):
    if condition[0] == 'intr' and condition[1] == CMP_REG_IMM and not condition[3]:
        return [intrinsic_operand(condition)]
    if condition[0] == 'bin' and condition[1] == BINOP_ID['|']:
        left = case_values(condition[2])
        right = case_values(condition[3])
        if left and right and len(right) == 1:
            return left + right
    return None


def is_intrinsic_statement(statement, opcode):
    return statement[0] == 'expr' and statement[1][0] == 'intr' and statement[1][1] == opcode


def switch_end(statements, start):
    depth = 0
    for index in range(start, len(statements)):
        statement = statements[index]
        if is_intrinsic_statement(statement, STORE_REG):
            depth += 1
        elif is_intrinsic_statement(statement, DEC_REG_IDX):
            depth -= 1
            if depth == 0:
                return index
    return None


def is_case_test(statement):
    return statement[0] == 'ifnot' and bool(case_values(statement[1]))


def jumps_to(statement, label):
    if statement == ('goto', label):
        return True
    return statement[0] == 'ifnot' and statement[2] == label


def replace_end_jumps_with_break(body, end_label):
    result = []
    for statement in body:
        if statement == ('goto', end_label):
            result.append(('break',))
        elif statement[0] == 'ifnot' and statement[2] == end_label:
            result.append(('ifnot', statement[1], BREAK))
        else:
            result.append(statement)
    return result


def collect_switch_cases(statements, start, end_index, end_label, positions, refs):
    cases = []
    default_body_end = end_index - 1
    index = start + 1
    while index < default_body_end and is_case_test(statements[index]):
        condition, next_label = statements[index][1], statements[index][2]
        next_index = positions.get(next_label)
        if next_index is None or next_index <= index or next_index > default_body_end:
            return None
        body = statements[index + 1:next_index]
        followed_by_case = next_index + 1 < default_body_end and is_case_test(statements[next_index + 1])
        is_last = next_index == default_body_end or not followed_by_case
        if not is_last and not (body and body[-1][0] == 'goto'):
            return None
        if next_label != end_label and refs.get(next_label) != 1:
            return None
        cases.append([case_values(condition), body])
        if next_label == end_label:
            index = default_body_end
            break
        index = next_index + 1
    return cases, index


def match_switch(statements, start, positions, refs):
    register = statements[start][1][2]
    value = statements[start][1][3][0]
    end_index = switch_end(statements, start)
    if end_index is None or statements[end_index][1][2] != 0 or statements[end_index - 1][0] != 'label':
        return None
    end_label = statements[end_index - 1][1]
    collected = collect_switch_cases(statements, start, end_index, end_label, positions, refs)
    if collected is None:
        return None
    cases, default_start = collected
    if not cases:
        return None
    default = statements[default_start:end_index - 1]
    inside = statements[start + 1:end_index - 1]
    end_uses = 0
    for statement in inside:
        if jumps_to(statement, end_label):
            end_uses += 1
    if refs.get(end_label, 0) != end_uses:
        return None
    structured_cases = []
    for values, body in cases:
        structured_cases.append((values, structure(replace_end_jumps_with_break(body, end_label), refs)))
    structured_default = None
    if default:
        structured_default = structure(replace_end_jumps_with_break(default, end_label), refs)
    return ('switch', register, value, structured_cases, structured_default), end_index + 1


def match_while(statements, index, positions, refs):
    statement = statements[index]
    if statement[0] != 'label' or refs.get(statement[1]) != 1:
        return None
    if index + 1 >= len(statements) or statements[index + 1][0] != 'ifnot':
        return None
    end_label = statements[index + 1][2]
    end_index = positions.get(end_label)
    if end_index is None or end_index <= index + 1 or refs.get(end_label) != 1:
        return None
    if statements[end_index - 1] != ('goto', statement[1]):
        return None
    body = structure(statements[index + 2:end_index - 1], refs)
    return ('while', statements[index + 1][1], body), end_index + 1


def match_if(statements, index, positions, refs):
    statement = statements[index]
    if statement[0] != 'ifnot' or refs.get(statement[2]) != 1:
        return None
    else_index = positions.get(statement[2])
    if else_index is None or else_index <= index:
        return None
    if else_index - 1 > index:
        last_then = statements[else_index - 1]
        if last_then[0] == 'goto' and refs.get(last_then[1]) == 1:
            end_index = positions.get(last_then[1])
            if end_index is not None and end_index > else_index:
                then_body = structure(statements[index + 1:else_index - 1], refs)
                else_body = structure(statements[else_index + 1:end_index], refs)
                return ('if', statement[1], then_body, else_body), end_index + 1
    then_body = structure(statements[index + 1:else_index], refs)
    return ('if', statement[1], then_body, None), else_index + 1


def structure(statements, refs):
    result = []
    positions = {}
    for index, statement in enumerate(statements):
        if statement[0] == 'label':
            positions[statement[1]] = index
    index = 0
    while index < len(statements):
        matched = None
        if is_intrinsic_statement(statements[index], STORE_REG):
            matched = match_switch(statements, index, positions, refs)
        if not matched:
            matched = match_while(statements, index, positions, refs)
        if not matched:
            matched = match_if(statements, index, positions, refs)
        if matched:
            result.append(matched[0])
            index = matched[1]
        else:
            result.append(statements[index])
            index += 1
    return result


def nested_bodies(statement):
    kind = statement[0]
    if kind == 'switch':
        bodies = [body for _, body in statement[3]]
        if statement[4] is not None:
            bodies.append(statement[4])
        return bodies
    if kind == 'if':
        bodies = [statement[2]]
        if statement[3] is not None:
            bodies.append(statement[3])
        return bodies
    if kind == 'while':
        return [statement[2]]
    return []


def statement_label(statement):
    if statement[0] in ('label', 'goto'):
        return statement[1]
    if statement[0] == 'ifnot' and statement[2] != BREAK:
        return statement[2]
    return None


def number_labels_in_order(statements, new_names):
    for statement in statements:
        label = statement_label(statement)
        if label is not None:
            new_names.setdefault(label, f'L{len(new_names) + 1}')
        for body in nested_bodies(statement):
            number_labels_in_order(body, new_names)


def rename_optional_body(body, new_names):
    if body is None:
        return None
    return rename_labels(body, new_names)


def rename_labels(statements, new_names):
    result = []
    for statement in statements:
        kind = statement[0]
        if kind in ('label', 'goto'):
            statement = (kind, new_names[statement[1]])
        elif kind == 'ifnot' and statement[2] != BREAK:
            statement = ('ifnot', statement[1], new_names[statement[2]])
        elif kind == 'switch':
            cases = [(values, rename_labels(body, new_names)) for values, body in statement[3]]
            statement = ('switch', statement[1], statement[2], cases, rename_optional_body(statement[4], new_names))
        elif kind == 'if':
            statement = ('if', statement[1], rename_labels(statement[2], new_names),
                         rename_optional_body(statement[3], new_names))
        elif kind == 'while':
            statement = ('while', statement[1], rename_labels(statement[2], new_names))
        result.append(statement)
    return result


def renumber_labels(statements):
    new_names = {}
    number_labels_in_order(statements, new_names)
    return rename_labels(statements, new_names)


class StatementRenderer:
    def __init__(self, naming, bound):
        self.naming = naming
        self.bound = bound

    def expression(self, expression, top=True):
        return expr_text(expression, self.naming, top)

    def task_text(self, statement):
        level, thread = statement[3]
        entry = statement[2]
        if thread[0] == 'actor':
            entry_text = self.naming.entry(entry, thread[1] in self.bound, thread[1])
            target = f'{self.expression(thread)}.{entry_text}'
        else:
            target = f'{self.expression(thread)}, {self.naming.entry(entry, False)}'
        function = 'start'
        if statement[1] == AWAIT_CALL:
            function = 'await'
        return f'{function}({target}, level={self.expression(level)});'

    def switch_lines(self, statement, indent, depth):
        pad = '    ' * indent
        register = ''
        if statement[1] != depth:
            register = f'[{statement[1]}]'
        lines = [f'{pad}switch{register} ({self.expression(statement[2])}) {{']
        for values, body in statement[3]:
            lines.append(pad + ' '.join(f'case {const_text(value, self.naming)}:' for value in values))
            lines += self.lines(body, indent + 1, depth + 1)
        if statement[4] is not None:
            lines.append(f'{pad}default:')
            lines += self.lines(statement[4], indent + 1, depth + 1)
        lines.append(f'{pad}}}')
        return lines

    def if_lines(self, statement, indent, depth):
        pad = '    ' * indent
        lines = [f'{pad}if ({self.expression(statement[1])}) {{']
        lines += self.lines(statement[2], indent + 1, depth)
        if statement[3] is not None:
            lines.append(f'{pad}}} else {{')
            lines += self.lines(statement[3], indent + 1, depth)
        lines.append(f'{pad}}}')
        return lines

    def while_lines(self, statement, indent, depth):
        pad = '    ' * indent
        lines = [f'{pad}while ({self.expression(statement[1])}) {{']
        lines += self.lines(statement[2], indent + 1, depth)
        lines.append(f'{pad}}}')
        return lines

    def simple_line(self, statement):
        kind = statement[0]
        if kind == 'assign':
            return f'{self.expression(statement[1])} = {self.expression(statement[2])};'
        if kind == 'expr':
            return f'{self.expression(statement[1])};'
        if kind == 'task':
            return self.task_text(statement)
        if kind == 'yield':
            return f'yield({number_text(statement[1])});'
        if kind == 'goto':
            return f'goto {statement[1]};'
        if kind == 'ifnot' and statement[2] == BREAK:
            return f'if (!{self.expression(statement[1], False)}) break;'
        if kind == 'ifnot':
            return f'if (!{self.expression(statement[1], False)}) goto {statement[2]};'
        if kind == 'break':
            return 'break;'
        if kind == 'op':
            return f'__op{statement[1]}({number_text(statement[2])});'
        return None

    def lines(self, statements, indent, depth=0):
        pad = '    ' * indent
        lines = []
        for statement in statements:
            kind = statement[0]
            if kind == 'label':
                lines.append(f'{"    " * max(indent - 1, 0)}{statement[1]}:')
            elif kind == 'switch':
                lines += self.switch_lines(statement, indent, depth)
            elif kind == 'if':
                lines += self.if_lines(statement, indent, depth)
            elif kind == 'while':
                lines += self.while_lines(statement, indent, depth)
            else:
                line = self.simple_line(statement)
                if line is not None:
                    lines.append(pad + line)
        return lines


def asm_operand_text(pc, opcode, operand, targets):
    if opcode in BRANCH_OPCODES:
        target = branch_target(pc, operand)
        if target in targets:
            return f'L{target}'
        return number_text(operand)
    if opcode == ALU and operand in evdl_format.ALU_OPS:
        return evdl_format.ALU_OPS[operand]
    if opcode == SYSCALL and operand in SYS_NAME:
        return SYS_NAME[operand]
    return number_text(operand)


def asm_lines(instructions, start, end, targets):
    lines = []
    for pc in range(start, end):
        if pc in targets:
            lines.append(f'L{pc}:')
        opcode, operand = instructions[pc]
        lines.append(f'    {ASM_NAME[opcode]} {asm_operand_text(pc, opcode, operand, targets)}')
    if end in targets:
        lines.append(f'L{end}:')
    return lines


def parse_mem(text):
    expression = Parser(tokenize(text)).expr()
    if expression[0] != 'mem':
        raise ValueError(f'{text!r} is not a memory reference')
    return expression


def names_section(names, key):
    section = names.get(key)
    if not section:
        return {}
    return section


class NameApplier:
    def __init__(self, threads, naming, warnings):
        self.threads = threads
        self.naming = naming
        self.warnings = warnings
        self.taken = (set(naming.thread_names.values()) | RESERVED | set(SYS_ID) | set(LABEL_VAR)
                      | set(GLOBAL_CONSTS))

    def claim(self, name, what):
        if not IDENT_RE.fullmatch(name) or name in self.taken:
            self.warnings.append(f'{what}: {name!r} is not a free identifier')
            return False
        self.taken.add(name)
        return True

    def thread_names(self, section):
        for thread_text, name in section.items():
            thread = int(thread_text)
            if thread >= len(self.threads):
                self.warnings.append(f'thread {thread} ({name}) does not exist')
            elif self.claim(name, f'thread {thread}'):
                self.naming.thread_names[thread] = name

    def entry_names(self, section):
        for key, name in section.items():
            thread_text, _, entry_text = key.partition('.')
            thread, entry = int(thread_text), int(entry_text)
            if thread >= len(self.threads) or entry >= len(self.threads[thread][1]):
                self.warnings.append(f'entry {key} ({name}) does not exist')
            elif self.claim(name, f'entry {key}'):
                self.naming.entry_aliases[(thread, entry)] = name

    def memory_names(self, section):
        for text, name in section.items():
            memory = parse_mem(text)
            if self.claim(name, text):
                self.naming.memory_aliases[(memory[1], memory[2])] = name

    def local_names(self, section):
        local_aliases = {}
        for thread_text, thread_locals in section.items():
            for text, name in thread_locals.items():
                match = re.fullmatch(r'local(\d+)', text)
                if not match or int(thread_text) >= len(self.threads):
                    self.warnings.append(f'locals of thread {thread_text}: {text!r} ({name}) does not exist')
                elif IDENT_RE.fullmatch(name):
                    local_aliases.setdefault(int(thread_text), {})[int(match.group(1))] = name
        return local_aliases


def apply_names(names, threads, naming, warnings):
    applier = NameApplier(threads, naming, warnings)
    applier.thread_names(names_section(names, 'threads'))
    applier.entry_names(names_section(names, 'entries'))
    applier.memory_names(names_section(names, 'vars'))
    return applier.local_names(names_section(names, 'locals'))


GLOBAL_NAME_RE = re.compile(r'\b[A-Z][A-Z0-9_]*\b')
STRING_RE = re.compile(r'"(?:[^"\\]|\\.)*"')
GLOBAL_KIND_ORDER = {'mem': 0, 'const': 1}


def global_value(name):
    if name in GLOBAL_CONSTS:
        return ('const', GLOBAL_CONSTS[name])
    if name in LABEL_VAR:
        return ('mem', 'byte', LABEL_VAR[name])
    if name in BIT_LABEL_NUM:
        return ('mem', 'bit', BIT_LABEL_NUM[name])
    return None


def global_value_text(value):
    if value[0] == 'mem':
        return mem_raw(value[1], value[2])
    return number_text(value[1])


def global_sort_key(item):
    name, value = item
    return (GLOBAL_KIND_ORDER[value[0]], name)


def globals_block(text):
    used = {}
    for name in GLOBAL_NAME_RE.findall(STRING_RE.sub('""', text)):
        if name in used:
            continue
        value = global_value(name)
        if value:
            used[name] = value
    if not used:
        return ''
    lines = []
    for name, value in sorted(used.items(), key=global_sort_key):
        lines.append(f'    {name} = {global_value_text(value)};')
    return 'globals {\n' + '\n'.join(lines) + '\n}\n\n'


def lines_until(lines, start, closing):
    end = start
    while lines[end] != closing:
        end += 1
    return lines[start:end]


def block_lines(lines, opening):
    if opening not in lines:
        return []
    return lines_until(lines, lines.index(opening) + 1, '}')


def split_assignment(line):
    name, _, value = line.strip().rstrip(';').partition('=')
    return name.strip(), value.strip()


def parse_globals(lines):
    declared = {}
    for line in block_lines(lines, 'globals {'):
        name, value = split_assignment(line)
        if name:
            declared[name] = Parser(tokenize(value)).expr()
    return declared


def check_globals(declared):
    for name, declared_value in declared.items():
        current = global_value(name)
        if current is None or current[1:] == declared_value[1:]:
            continue
        if current[0] == 'mem' and declared_value[0] == 'mem' and current[2] == declared_value[2]:
            continue
        COMPILE_WARNINGS.append(f'{name} is {global_value_text(declared_value)} in this file but '
                                f'{global_value_text(current)} in the current tables '
                                f'(the file\'s value is used)')


def count_stat(stats, key):
    if stats is not None:
        stats[key] = stats.get(key, 0) + 1


def count_failure(stats, failure):
    if stats is not None:
        failures = stats.setdefault('fail', {})
        failures.setdefault(str(failure), 0)
        failures[str(failure)] += 1


def branch_targets(instructions):
    targets = set()
    for pc, (opcode, operand) in enumerate(instructions):
        if opcode in BRANCH_OPCODES:
            target = branch_target(pc, operand)
            if 0 <= target <= len(instructions):
                targets.add(target)
    return targets


def check_branches_stay_in_entry(instructions, start, yield_pc):
    for pc in range(start, yield_pc):
        opcode, operand = instructions[pc]
        if opcode in BRANCH_OPCODES and not start <= branch_target(pc, operand) <= yield_pc:
            raise Fail('branch leaves entry')


def decompile_thread_entries(instructions, header_pc, yield_pcs, targets):
    for yield_pc in yield_pcs:
        if instructions[yield_pc][1] != YIELD_OPERAND:
            raise Fail('yield operand')
    if header_pc in targets:
        raise Fail('branch to header')
    starts = [header_pc + 1] + [yield_pc + 1 for yield_pc in yield_pcs[:-1]]
    entries = {}
    for entry, (start, yield_pc) in enumerate(zip(starts, yield_pcs)):
        check_branches_stay_in_entry(instructions, start, yield_pc)
        if yield_pc > start or yield_pc in targets:
            entries[entry] = EntryDecompiler(instructions, targets).decompile(start, yield_pc)
    return entries


def decompile_threads(instructions, threads, targets, stats):
    built = []
    for header_pc, yield_pcs in threads:
        try:
            entries = decompile_thread_entries(instructions, header_pc, yield_pcs, targets)
        except Fail as failure:
            entries = None
            count_failure(stats, failure)
        built.append((header_pc, yield_pcs, entries))
    return built


def add_reference(refs, label, count):
    refs[label] = refs.get(label, 0) + count


def label_reference_counts(instructions, built, tail):
    refs = {}
    for _, _, entries in built:
        if entries is None:
            continue
        for body in entries.values():
            for statement in body:
                if statement[0] == 'goto':
                    add_reference(refs, statement[1], 1)
                elif statement[0] == 'ifnot':
                    add_reference(refs, statement[2], 1)
    asm_ranges = []
    for header_pc, yield_pcs, entries in built:
        if entries is None:
            asm_ranges.append((header_pc + 1, yield_pcs[-1] + 1))
    asm_ranges.append((tail, len(instructions)))
    for start, end in asm_ranges:
        for pc in range(start, end):
            opcode, operand = instructions[pc]
            if opcode in BRANCH_OPCODES:
                add_reference(refs, f'L{branch_target(pc, operand)}', 2)
    return refs


def bound_threads(instructions, built):
    bound = set()
    for index, (header_pc, yield_pcs, _) in enumerate(built):
        if (SYSCALL, SET_CHAR_ID) in instructions[header_pc + 1:yield_pcs[0]]:
            bound.add(index)
    return bound


class ThreadRenderer:
    def __init__(self, instructions, targets, refs, bound, naming, local_aliases, world, entity_ids):
        self.instructions = instructions
        self.targets = targets
        self.refs = refs
        self.bound = bound
        self.naming = naming
        self.local_aliases = local_aliases
        self.world = world
        self.entity_ids = entity_ids

    def name_and_note(self, index):
        if index in self.naming.thread_names:
            return self.naming.thread_names[index], f'  // {index}'
        return str(index), ''

    def asm_thread(self, index, header_pc, yield_pcs):
        name, note = self.name_and_note(index)
        lines = asm_lines(self.instructions, header_pc + 1, yield_pcs[-1] + 1, self.targets)
        return f'thread {name} [{len(yield_pcs)}] asm {{{note}\n' + '\n'.join(lines) + '\n}'

    def names_block(self, index, thread_naming):
        declarations = []
        for (thread, entry), alias in sorted(self.naming.entry_aliases.items()):
            if thread == index:
                declarations.append(f'        {alias} = entry_{entry};')
        for number, alias in sorted(thread_naming.local_aliases.items()):
            declarations.append(f'        {alias} = local{number};')
        if not declarations:
            return []
        return ['    names {'] + declarations + ['    }']

    def entry_body(self, statements, thread_naming):
        typed = type_stmts(statements, self.world, self.entity_ids)
        structured = renumber_labels(structure(typed, self.refs))
        return StatementRenderer(thread_naming, self.bound).lines(structured, 2)

    def evs_thread(self, index, yield_pcs, entries):
        name, note = self.name_and_note(index)
        count = len(yield_pcs)
        implied = max(MIN_ENTRIES, max(entries, default=-1) + 1)
        if count > implied:
            entries.setdefault(count - 1, [])
            implied = count
        head = f'thread {name}'
        if count != implied:
            head = f'thread {name} [{count}]'
        thread_naming = self.naming.with_local_aliases(self.local_aliases.get(index, {}))
        lines = self.names_block(index, thread_naming)
        for entry in sorted(entries):
            lines.append(f'    {self.naming.entry(entry, index in self.bound, index)} {{')
            lines += self.entry_body(entries[entry], thread_naming)
            lines.append('    }')
        return f'{head} {{{note}\n' + '\n'.join(lines) + '\n}'


def alias_of(memory_alias_item):
    return memory_alias_item[1]


def prepend_memory_names(body, naming):
    used = []
    for memory, alias in sorted(naming.memory_aliases.items(), key=alias_of):
        if re.search(rf'\b{alias}\b', body):
            used.append((memory, alias))
    if not used:
        return body
    declarations = '\n'.join(f'    {alias} = {mem_raw(*memory)};' for memory, alias in used)
    return f'names {{\n{declarations}\n}}\n\n' + body


def prepend_entities(body, naming):
    used = used_entities(body, naming)
    if not used:
        return body
    declarations = '\n'.join(f'    {naming.entity_names[entity_id]} = {number_text(entity_id)};' for entity_id in used)
    return f'entities {{\n{declarations}\n}}\n\n' + body


def decompile(stream, stats=None, entities=None, world=None, messages=None, names=None, emit_globals=True):
    instructions = decode(stream)
    targets = branch_targets(instructions)
    threads, tail = split_threads(instructions)
    built = decompile_threads(instructions, threads, targets, stats)
    refs = label_reference_counts(instructions, built, tail)
    bound = bound_threads(instructions, built)
    if entities is None:
        naming = Naming({}, {}, None)
    else:
        naming = Naming(thread_names(instructions, threads, entities), entity_consts(entities), None)
    if messages:
        naming.messages = messages
    else:
        naming.messages = {}
    entity_ids = set(naming.entity_names)
    WARNINGS.clear()
    if names is None:
        names = {}
    local_aliases = apply_names(names, threads, naming, WARNINGS)
    renderer = ThreadRenderer(instructions, targets, refs, bound, naming, local_aliases, world, entity_ids)
    parts = []
    for index, (header_pc, yield_pcs, entries) in enumerate(built):
        if entries is None:
            parts.append(renderer.asm_thread(index, header_pc, yield_pcs))
            count_stat(stats, 'asm')
        else:
            parts.append(renderer.evs_thread(index, yield_pcs, entries))
            count_stat(stats, 'ok')
    if tail < len(instructions):
        parts.append('raw asm {\n' + '\n'.join(asm_lines(instructions, tail, len(instructions), targets)) + '\n}')
        count_stat(stats, 'raw')
    body = '\n\n'.join(parts) + '\n'
    body = prepend_memory_names(body, naming)
    body = prepend_entities(body, naming)
    if emit_globals:
        body = globals_block(body) + body
    return body


TOK = re.compile(r'\s*(?://[^\n]*|(0x[0-9A-Fa-f]+|\d+)|([A-Za-z_][\w.]*)|(==|!=|>=|<=|<<|[-+*/%<>&|^~!(){}\[\];:,=])|("(?:[^"\\]|\\.)*"))')


def tokenize(text):
    tokens = []
    position = 0
    text = text.rstrip()
    while position < len(text):
        match = TOK.match(text, position)
        if not match or match.end() == position:
            raise SyntaxError(f'bad token at {text[position:position + 20]!r}')
        position = match.end()
        number, identifier, operator, string = match.groups()
        if number:
            tokens.append(('num', int(number, 0)))
        elif identifier:
            tokens.append(('id', identifier))
        elif operator:
            tokens.append(('op', operator))
        elif string:
            tokens.append(('str', unquote(string)))
    return tokens


def negated(condition):
    if condition[0] == 'not':
        return condition[1]
    return ('not', condition)


class Parser:
    def __init__(self, tokens, thread_numbers=None, entity_constants=None, messages=None, aliases=None,
                 thread=None, declared_globals=None):
        self.tokens = tokens
        self.position = 0
        self.thread_numbers = thread_numbers or {}
        self.entity_constants = entity_constants or {}
        self.messages = messages
        self.declared_globals = declared_globals or {}
        self.thread = thread
        if aliases is None:
            aliases = {}
        self.memory_aliases = aliases.get('mem', {})
        self.entry_aliases = aliases.get('entries', {})
        self.local_aliases = aliases.get('locals', {}).get(thread, {})

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

    def stmts(self):
        statements = []
        while self.peek()[0] != 'eof' and self.peek_value() != '}':
            statements.append(self.stmt())
        return statements

    def entry_ref(self, name=None, thread=None):
        if not name:
            name = self.take_value()
        if thread is None:
            thread = self.thread
        aliases = self.entry_aliases.get(thread, {})
        if name in aliases:
            return aliases[name]
        match = re.fullmatch(r'entry_(\d+)', name)
        if match:
            return int(match.group(1))
        return SLOT_ID[name]

    def thread_ref(self, name):
        match = re.fullmatch(r'thread_(\d+)', name)
        if match:
            return ('actor', int(match.group(1)))
        return ('actor', self.thread_numbers[name])

    def case_body(self):
        statements = []
        while self.peek_value() not in ('case', 'default', '}'):
            statements.append(self.stmt())
        return statements

    def entries(self):
        entries = {}
        if self.peek_value() == 'names':
            while self.take_value() != '}':
                pass
        while self.peek()[0] != 'eof':
            entry = self.entry_ref()
            entries[entry] = self.block()
        return entries

    def block(self):
        self.take('{')
        statements = self.stmts()
        self.take('}')
        return statements

    def parenthesized_expression(self):
        self.take('(')
        expression = self.expr()
        self.take(')')
        return expression

    def if_statement(self):
        self.take()
        condition = self.parenthesized_expression()
        if self.peek_value() == 'goto':
            self.take()
            label = self.take_value()
            self.take(';')
            return ('ifnot', negated(condition), label)
        if self.peek_value() == 'break':
            self.take()
            self.take(';')
            return ('ifnot', negated(condition), BREAK)
        then_body = self.block()
        else_body = None
        if self.peek_value() == 'else':
            self.take()
            else_body = self.block()
        return ('if', condition, then_body, else_body)

    def while_statement(self):
        self.take()
        condition = self.parenthesized_expression()
        return ('while', condition, self.block())

    def case_label_values(self):
        values = []
        while True:
            value = self.expr()
            self.take(':')
            if value[0] != 'const':
                raise SyntaxError('case value must be a constant')
            values.append(value)
            if self.peek_value() != 'case':
                return values
            self.take()

    def switch_statement(self):
        self.take()
        register = None
        if self.peek_value() == '[':
            self.take('[')
            register = self.take_value()
            self.take(']')
        value = self.parenthesized_expression()
        self.take('{')
        cases = []
        default = None
        while self.peek_value() != '}':
            if self.take_value() == 'case':
                values = self.case_label_values()
                cases.append((values, self.case_body()))
            else:
                self.take(':')
                default = self.case_body()
        self.take('}')
        return ('switch', register, value, cases, default)

    def numbered_call_statement(self, keyword):
        self.take()
        self.take('(')
        operand = self.take_value()
        self.take(')')
        self.take(';')
        if keyword == 'yield':
            return ('yield', operand)
        return ('op', int(keyword[4:]), operand)

    def task_statement(self, keyword):
        self.take()
        self.take('(')
        kind, value = self.peek()
        if kind == 'id' and '.' in value and self.peek_value(1) == ',':
            self.take()
            thread_name, _, entry_name = value.partition('.')
            thread = self.thread_ref(thread_name)
            entry = self.entry_ref(entry_name, thread[1])
        else:
            thread = self.expr()
            self.take(',')
            entry = self.entry_ref()
        self.take(',')
        self.take('level')
        self.take('=')
        level = self.expr()
        self.take(')')
        self.take(';')
        opcode = INIT_CALL
        if keyword == 'await':
            opcode = AWAIT_CALL
        return ('task', opcode, entry, [level, thread])

    def stmt(self):
        kind, value = self.peek()
        if kind == 'id' and self.peek_value(1) == ':':
            self.position += 2
            return ('label', value)
        if value == 'if':
            return self.if_statement()
        if value == 'while':
            return self.while_statement()
        if value == 'switch':
            return self.switch_statement()
        if value == 'break':
            self.take()
            self.take(';')
            return ('break',)
        if value == 'goto':
            self.take()
            label = self.take_value()
            self.take(';')
            return ('goto', label)
        if value == 'yield' or (kind == 'id' and value.startswith('__op')):
            return self.numbered_call_statement(value)
        if value in ('start', 'await') and self.peek_value(1) == '(':
            return self.task_statement(value)
        expression = self.expr()
        if self.peek_value() == '=':
            self.take()
            assigned = self.expr()
            self.take(';')
            return ('assign', expression, assigned)
        self.take(';')
        return ('expr', expression)

    def expr(self):
        left = self.unary()
        if self.peek()[0] == 'op' and self.peek_value() in BINOP_ID:
            operation = BINOP_ID[self.take_value()]
            right = self.unary()
            return ('bin', operation, left, right)
        return left

    def unary(self):
        kind, value = self.peek()
        if value == '!':
            self.take()
            return ('not', self.unary())
        if kind == 'op' and value in UNOP_ID:
            self.take()
            return ('un', UNOP_ID[value], self.unary())
        return self.primary()

    def args(self):
        self.take('(')
        arguments = []
        while self.peek_value() != ')':
            arguments.append(self.expr())
            if self.peek_value() == ',':
                self.take()
        self.take(')')
        return arguments

    def message_reference(self):
        self.take('[')
        index = self.take_value()
        self.take(']')
        if self.peek_value() == '=' and self.peek(1)[0] == 'str':
            self.take()
            text = self.take_value()
            if self.messages is not None:
                have = self.messages.get(index)
                if have != text:
                    raise ValueError(f'messages[{number_text(index)}] is {have!r} in the .binl, not {text!r}')
        return ('const', index)

    def declared_global(self, name):
        base, _, width = name.partition('.')
        if base not in self.declared_globals:
            return None
        declared = self.declared_globals[base]
        if declared[0] == 'const' and not width:
            return declared
        if declared[0] == 'mem':
            if declared[1] == 'bit':
                return ('mem', 'bit', declared[2])
            if not width:
                width = 'byte'
            return ('mem', width, declared[2])
        return None

    def call(self, name):
        arguments = self.args()
        if name in INTR_ID:
            return ('intr', INTR_ID[name], arguments[0][1], arguments[1:])
        if name.startswith('sys_'):
            return ('call', int(name[4:]), arguments)
        return ('call', SYS_ID[name], arguments)

    def indexed_memory(self, name):
        self.take('[')
        offset = self.take_value()
        self.take(']')
        region, _, width = name.partition('.')
        if region == 'bit':
            return ('mem', 'bit', offset)
        if not width:
            width = 'byte'
        return ('mem', width, mem_var(region, offset))

    def primary(self):
        kind, value = self.take()
        if kind == 'num':
            return ('const', value)
        if kind == 'str':
            return ('newmsg', value)
        if value == 'messages' and self.peek_value() == '[':
            return self.message_reference()
        if value == '(':
            expression = self.expr()
            self.take(')')
            return expression
        if kind != 'id':
            raise SyntaxError(f'unexpected {value!r}')
        return self.name(value)

    def name(self, name):
        if name.startswith('__alu'):
            arguments = self.args()
            return ('bin', int(name[5:]), arguments[0], arguments[1])
        if name == '__push':
            return ('keep', self.args()[0])
        if name == '__nop':
            return ('nop', self.args()[0])
        if re.fullmatch(r'thread_\d+', name):
            return self.thread_ref(name)
        if name in self.thread_numbers:
            return ('actor', self.thread_numbers[name])
        declared = self.declared_global(name)
        if declared is not None:
            return declared
        if name in self.entity_constants:
            return ('const', self.entity_constants[name])
        if name in GLOBAL_CONSTS:
            return ('const', GLOBAL_CONSTS[name])
        if name in self.local_aliases:
            return ('local', self.local_aliases[name])
        if name in self.memory_aliases:
            return self.memory_aliases[name]
        if name.startswith('local') and name[5:].isdigit():
            return ('local', int(name[5:]))
        if self.peek_value() == '(':
            return self.call(name)
        if self.peek_value() == '[':
            return self.indexed_memory(name)
        if name in BIT_LABEL_NUM:
            return ('mem', 'bit', BIT_LABEL_NUM[name])
        base, _, width = name.partition('.')
        if base in LABEL_VAR and width in ('', 'word', 'dword'):
            if not width:
                width = 'byte'
            return ('mem', width, LABEL_VAR[base])
        raise SyntaxError(f'unknown name {name!r}')


class Emitter:
    def __init__(self, messages=None):
        self.messages = messages
        self.code = []
        self.labels = {}
        self.label_count = 0
        self.scope = ''
        self.switch_ends = []

    def emit(self, opcode, operand):
        self.code.append([opcode, operand])

    def place_label(self, label):
        self.labels[label] = len(self.code)

    def fresh_label(self):
        self.label_count += 1
        return f'__c{self.label_count}'

    def new_message(self, text):
        if not hasattr(self.messages, 'resolve'):
            raise ValueError(f'"{text}" needs a message store (the set\'s .binl) to compile')
        self.emit(PUSH, self.messages.resolve(text))

    def expr(self, expression):
        kind = expression[0]
        if kind == 'const':
            self.emit(PUSH, expression[1])
        elif kind == 'actor':
            self.emit(PUSH_ACTOR, expression[1])
        elif kind == 'local':
            self.emit(LOAD_LOCAL, expression[1])
        elif kind == 'mem':
            self.emit(READ_OP[expression[1]], expression[2])
        elif kind == 'newmsg':
            self.new_message(expression[1])
        elif kind == 'not':
            self.expr(expression[1])
            self.emit(PUSH, 0)
            self.emit(ALU, BINOP_ID['=='])
        elif kind == 'un':
            self.expr(expression[2])
            self.emit(ALU, expression[1])
        elif kind == 'bin':
            self.expr(expression[2])
            self.expr(expression[3])
            self.emit(ALU, expression[1])
        elif kind == 'keep':
            self.expr(expression[1])
        elif kind == 'nop':
            self.emit(HEADER, 0)
            self.expr(expression[1])
        elif kind == 'call':
            self.expressions(expression[2])
            self.emit(SYSCALL, expression[1])
        elif kind == 'intr':
            self.expressions(expression[3])
            self.emit(expression[1], expression[2])

    def expressions(self, expressions):
        for expression in expressions:
            self.expr(expression)

    def stmts(self, statements):
        for statement in statements:
            self.stmt(statement)

    def assignment(self, target, value):
        self.expr(value)
        if target[0] == 'local':
            self.emit(STORE_LOCAL, target[1])
        else:
            self.emit(WRITE_OP[target[1]], target[2])

    def switch(self, statement):
        register = statement[1]
        if register is None:
            register = len(self.switch_ends)
        end = self.fresh_label()
        self.expr(statement[2])
        self.emit(STORE_REG, register)
        self.switch_ends.append(end)
        for values, body in statement[3]:
            next_case = self.fresh_label()
            self.emit(CMP_REG_IMM, values[0][1])
            for value in values[1:]:
                self.emit(CMP_REG_IMM, value[1])
                self.emit(ALU, BINOP_ID['|'])
            self.emit(BEQZ, next_case)
            self.stmts(body)
            self.place_label(next_case)
        if statement[4] is not None:
            self.stmts(statement[4])
        self.switch_ends.pop()
        self.place_label(end)
        self.emit(DEC_REG_IDX, 0)

    def if_statement(self, statement):
        end = self.fresh_label()
        self.expr(statement[1])
        if statement[3] is None:
            self.emit(BEQZ, end)
            self.stmts(statement[2])
        else:
            else_label = self.fresh_label()
            self.emit(BEQZ, else_label)
            self.stmts(statement[2])
            self.emit(JMP, end)
            self.place_label(else_label)
            self.stmts(statement[3])
        self.place_label(end)

    def while_statement(self, statement):
        top = self.fresh_label()
        end = self.fresh_label()
        self.place_label(top)
        self.expr(statement[1])
        self.emit(BEQZ, end)
        self.stmts(statement[2])
        self.emit(JMP, top)
        self.place_label(end)

    def stmt(self, statement):
        kind = statement[0]
        if kind == 'label':
            self.place_label(self.scope + statement[1])
        elif kind == 'assign':
            self.assignment(statement[1], statement[2])
        elif kind == 'expr':
            self.expr(statement[1])
        elif kind == 'task':
            self.expressions(statement[3])
            self.emit(statement[1], statement[2])
        elif kind == 'yield':
            self.emit(YIELD_OPCODE, statement[1])
        elif kind == 'op':
            self.emit(statement[1], statement[2])
        elif kind == 'goto':
            self.emit(JMP, self.scope + statement[1])
        elif kind == 'ifnot' and statement[2] == BREAK:
            self.expr(statement[1])
            self.emit(BEQZ, self.switch_ends[-1])
        elif kind == 'ifnot':
            self.expr(statement[1])
            self.emit(BEQZ, self.scope + statement[2])
        elif kind == 'break':
            self.emit(JMP, self.switch_ends[-1])
        elif kind == 'switch':
            self.switch(statement)
        elif kind == 'if':
            self.if_statement(statement)
        elif kind == 'while':
            self.while_statement(statement)

    def asm_instruction(self, mnemonic, operand):
        opcode = ASM_ID[mnemonic]
        if opcode in BRANCH_OPCODES and operand.startswith('L'):
            self.emit(opcode, operand)
        elif opcode == ALU and operand in evdl_format.ALU_BY_NAME:
            self.emit(ALU, evdl_format.ALU_BY_NAME[operand])
        elif opcode == SYSCALL and operand in SYS_ID:
            self.emit(SYSCALL, SYS_ID[operand])
        else:
            self.emit(opcode, int(operand, 0))

    def asm(self, lines):
        for line in lines:
            line = line.split(';')[0].strip()
            if not line:
                continue
            if line.endswith(':'):
                self.place_label(line[:-1])
                continue
            mnemonic, _, operand = line.partition(' ')
            self.asm_instruction(mnemonic, operand.strip())

    def assemble(self):
        output = bytearray()
        for pc, (opcode, operand) in enumerate(self.code):
            if isinstance(operand, str):
                operand = (self.labels[operand] - pc) & evdl_format.U24_MASK
            output += evdl_format.encode_instruction(opcode, operand)
        return bytes(output)


HEAD_RE = re.compile(r'^(?:thread (\w+)(?: \[(\d+)\])?|(raw))( asm)? \{(?:\s*//.*)?$')


def thread_head(line):
    match = HEAD_RE.match(line)
    if match and not match.group(3):
        return match
    return None


def named_thread_numbers(lines):
    numbers = {}
    thread_number = 0
    for line in lines:
        match = thread_head(line)
        if match is None:
            continue
        if not match.group(1).isdigit():
            numbers[match.group(1)] = thread_number
        thread_number += 1
    return numbers


def parse_entities_block(lines):
    constants = {}
    for line in block_lines(lines, 'entities {'):
        name, value = split_assignment(line)
        constants[name] = int(value, 0)
    return constants


def parse_memory_names(lines):
    aliases = {}
    for line in block_lines(lines, 'names {'):
        name, value = split_assignment(line)
        aliases[name] = parse_mem(value)
    return aliases


def parse_thread_aliases(lines, aliases):
    thread = -1
    for index, line in enumerate(lines):
        if thread_head(line):
            thread += 1
        elif line == '    names {':
            for alias_line in lines_until(lines, index + 1, '    }'):
                name, value = split_assignment(alias_line)
                if value.startswith('entry_'):
                    aliases['entries'].setdefault(thread, {})[name] = int(value[len('entry_'):])
                else:
                    aliases['locals'].setdefault(thread, {})[name] = int(value[len('local'):])


def block_end(lines, start):
    end = start + 1
    while lines[end] != '}':
        end += 1
    return end


def compile_evs_thread(emitter, match, head_index, parser):
    entries = parser.entries()
    if match.group(2):
        count = int(match.group(2))
    else:
        count = max(MIN_ENTRIES, max(entries, default=-1) + 1)
    emitter.emit(HEADER, count)
    for entry in range(count):
        emitter.scope = f'{head_index}.{entry}.'
        emitter.stmts(entries.get(entry, []))
        emitter.emit(YIELD_OPCODE, YIELD_OPERAND)
    emitter.scope = ''


def compile_text(text, messages=None, file_globals=None):
    emitter = Emitter(messages)
    lines = text.split('\n')
    declared_globals = {}
    if file_globals:
        declared_globals.update(file_globals)
    own_globals = parse_globals(lines)
    check_globals(own_globals)
    declared_globals.update(own_globals)
    thread_numbers = named_thread_numbers(lines)
    entity_constants = parse_entities_block(lines)
    aliases = {'mem': parse_memory_names(lines), 'entries': {}, 'locals': {}}
    parse_thread_aliases(lines, aliases)
    thread = -1
    index = 0
    while index < len(lines):
        match = HEAD_RE.match(lines[index])
        if not match:
            index += 1
            continue
        end = block_end(lines, index)
        body = lines[index + 1:end]
        is_raw = bool(match.group(3))
        if not is_raw:
            thread += 1
        if match.group(4):
            if not is_raw:
                emitter.emit(HEADER, int(match.group(2)))
            emitter.asm(body)
        else:
            parser = Parser(tokenize('\n'.join(body)), thread_numbers, entity_constants, messages, aliases,
                            thread, declared_globals)
            compile_evs_thread(emitter, match, index, parser)
        index = end + 1
    return emitter.assemble()


KGR_RE = re.compile(r'^kgr (\d+) \{$')
INDENT = '    '


def indent_block(text):
    lines = []
    for line in text.rstrip('\n').split('\n'):
        if line:
            lines.append(INDENT + line)
        else:
            lines.append(line)
    return '\n'.join(lines)


def decompile_file(path, only=None):
    from corpus import load_file
    import entities
    path = Path(path)
    parts = []
    for index, kgr in enumerate(load_file(path)):
        if only is not None and index != only:
            continue
        messages = entities.messages_for(path, kgr)
        text = decompile(kgr['stream'], entities=entities.entities_for(path, kgr), world=entities.world_prefix(path),
                         messages=messages, names=entities.names_for(path, index), emit_globals=False)
        for warning in WARNINGS:
            print(f'warning: {path.name} kgr {index}: {warning}', file=sys.stderr)
        if compile_text(text, messages) != kgr['stream']:
            raise AssertionError(f'round trip mismatch in KGR {index}')
        parts.append(f'kgr {index} {{\n{indent_block(text)}\n}}')
    text = '\n\n'.join(parts) + '\n'
    return globals_block(text) + text


def unindent(line):
    if line.startswith(INDENT):
        return line[len(INDENT):]
    return line


def compile_file_text(text, messages=None):
    streams = {}
    lines = text.split('\n')
    file_globals = parse_globals(lines)
    check_globals(file_globals)
    index = 0
    while index < len(lines):
        match = KGR_RE.match(lines[index])
        if not match:
            index += 1
            continue
        end = block_end(lines, index)
        body = [unindent(line) for line in lines[index + 1:end]]
        streams[int(match.group(1))] = compile_text('\n'.join(body), messages, file_globals)
        index = end + 1
    return streams


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
