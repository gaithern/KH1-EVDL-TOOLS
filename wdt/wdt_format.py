"""Parser for KH1 <world>.wdt files: sections, areas, entrances, world script, colours and images, as a tree of fields."""
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

from wdt_music import MISSING_TRACK_LABEL, music_detail, music_label
from wdt_images import PALETTE_COLOURS, PALETTE_SIZE, indexed_to_rgba


DEFAULT_DIR = r'C:\OpenKH\OpenKHEGS\data\kh1'

SECTION_NAMES = [
    'Areas & entrances',
    'World script (EVDL)',
    'Text colours',
    'Unused',
    'World logo (TIM2)',
    'Dialog window texture',
]

MIN_FILE_SIZE = 0x40

MAX_SECTION_COUNT = 16

SECTION_TABLE_OFFSET = 0x10

SECTION_ENTRY_SIZE = 8

AREA_SIZE = 0x40

ENTRANCE_SIZE = 0x40

SPAWN_SLOT_SIZE = 0x10

AXIS_NAMES = ('x', 'y', 'z', 'rot')

ROTATION_AXIS = 3

AREA_GROUP = 0

AREA_FIELD_BGM = 2

AREA_BATTLE_BGM = 3

AREA_FLAGS = 4

AREA_UNKNOWN_14 = 5

AREA_VOLUME_18 = 6

AREA_VOLUME_1C = 7

AREA_AMBIENT_SE_1 = 8

AREA_AMBIENT_SE_2 = 9

AREA_ALT_FIELD_BGM = 10

AREA_ALT_BATTLE_BGM = 11

AREA_FLAGS_OFFSET = 0x10

AREA_ALT_BGM_FIRST_OFFSET = 0x28

SCRIPT_HEADER_SIZE = 16

KGR_MAGIC = b'KGR\x00'

KGR_SCRIPT_COUNT_OFFSET = 12

KGR_HEADER_SIZE = 13

FIRST_DOOR_EVENT_ID = 100

SYSCALL_CHANGE_AREA = 60

SYSCALL_MAP_CHANGE_REWRITE_SET = 612

DOOR_SYSCALLS = (SYSCALL_CHANGE_AREA, SYSCALL_MAP_CHANGE_REWRITE_SET)

OP_PUSH = 0x09

OP_SYSCALL = 0x18

INSTRUCTION_SIZE = 4

WORLD_PUSH_DISTANCE = 4

COLOUR_SET_SIZE = 16

COLOURS_PER_SET = 4

TIM2_MAGIC = b'TIM2'

TIM2_FILE_HEADER_SIZE = 0x10

TIM2_IMAGE_TYPE_NAMES = {4: '4bpp', 5: '8bpp'}

TIM2_IMAGE_TYPE_8BPP = 5

TIM2_CLUT_CSM2_FLAG = 0x80

DIALOG_TEXTURE_WIDTH = 256

DIALOG_TEXTURE_HEIGHT = 128

RAW_HEX_LIMIT = 16


@dataclass
class Field:
    offset: int
    size: int
    name: str
    type: str
    value: str
    note: str = ''
    relative_offset: int = None
    color: tuple = None


@dataclass
class Node:
    title: str
    start: int
    end: int
    fields: list = field(default_factory=list)
    children: list = field(default_factory=list)
    summary: tuple = None
    image: tuple = None
    info: str = ''


def read_u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def read_f32(data, offset):
    return struct.unpack_from('<f', data, offset)[0]


def format_hex(value):
    return f'0x{value:X}'


def format_number(value):
    if value > 9:
        return f'0x{value:X} ({value})'
    return str(value)


def format_float(value):
    if value != value:
        return 'nan'
    return f'{value:.3f}'.rstrip('0').rstrip('.')


def opcode_of(word):
    return word >> 24


def operand_of(word):
    return word & 0xFFFFFF


def compact_room_list(rooms):
    room_keys = sorted({(room[:2], int(room[2:])) for room in rooms})
    ranges = []
    first = 0
    while first < len(room_keys):
        last = first
        world, first_number = room_keys[first]
        while last + 1 < len(room_keys):
            next_world, next_number = room_keys[last + 1]
            if next_world != world or next_number != room_keys[last][1] + 1:
                break
            last += 1
        if first == last:
            ranges.append(f'{world}{first_number:02d}')
        else:
            ranges.append(f'{world}{first_number:02d}-{room_keys[last][1]:02d}')
        first = last + 1
    return ', '.join(ranges)


def format_spawn_summary(slot):
    parts = []
    for axis, value in enumerate(slot):
        if axis == ROTATION_AXIS:
            parts.append(format_float(round(value, 2)))
        else:
            parts.append(format_float(round(value)))
    return ', '.join(parts)


def read_world_strings(section_bytes):
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ev'))
        from evdl_format import parse_evdl_string_table
        return parse_evdl_string_table(section_bytes)
    except Exception:
        return {}


def walk_nodes(nodes):
    for node in nodes:
        yield node
        yield from walk_nodes(node.children)


class Wdt:
    AREA_FIELDS = [
        (0x00, 'Location group', 'rooms of one location share it'),
        (0x04, 'Unknown mask', 'not read by the loader'),
        (0x08, 'Field BGM', 'amusic/musicNNN.dat'),
        (0x0C, 'Battle BGM', 'amusic/musicNNN.dat'),
        (0x10, 'Flags', 'bit1 tint; bit0, bit2, bit3, bit6 -> engine flags'),
        (0x14, 'Unknown 0x14', ''),
        (0x18, 'Volume-style 0x18', 'sqrt(v*0x3FFF)*2'),
        (0x1C, 'Volume-style 0x1C', 'sqrt(v*0x3FFF)*2'),
        (0x20, 'Ambient SE 1', 'looping room SE, amusic/se<world>.dat/seNNNNNN.win32.scd'),
        (0x24, 'Ambient SE 2', 'second ambient SE channel, same naming'),
        (0x28, 'Alt field BGM', 'used only in Traverse Town (world 3) once story byte >= 0x2B'),
        (0x2C, 'Alt battle BGM', 'used only in Traverse Town (world 3) once story byte >= 0x2B'),
        (0x30, 'Unused 0x30', ''),
        (0x34, 'Unused 0x34', ''),
        (0x38, 'Unused 0x38', ''),
        (0x3C, 'Unused 0x3C', ''),
    ]
    BGM_OFFSETS = {0x08: 'field', 0x0C: 'battle', 0x28: 'alt field', 0x2C: 'alt battle'}
    SLOT_NAMES = ['Sora', 'party slot 1', 'party slot 2']

    def __init__(self, data: bytes, name: str = 'xx.wdt', music: dict = None):
        self.data = data
        self.name = name
        self.music = music or {}
        self.world = Path(name).stem[:2].lower()
        self.warnings = []
        self.sections = []
        self.areas = []
        self.entrances = []
        self.kgrs = []
        self.nodes = []
        self.area_table_node = None
        self.entrance_table_node = None
        self.door_overview_node = None
        self.parse()

    def room(self, area):
        return f'{self.world}{area + 1:02d}'

    def in_bounds(self, offset, size):
        return 0 <= offset and offset + size <= len(self.data)

    def u32_field(self, offset, name, note='', relative_offset=None, formatter=format_number):
        value = read_u32(self.data, offset)
        return Field(offset, 4, name, 'u32', formatter(value), note, relative_offset)

    def bgm(self, music_id):
        label = music_label(self.music, music_id)
        if label:
            return f'{music_id:X} {label}'
        return format_hex(music_id)

    def parse(self):
        self.check_header()
        self.nodes.append(self.parse_section_table())
        builders = [self.parse_areas_and_entrances, self.parse_world_script,
                    self.parse_text_colours, None, self.parse_title_logo,
                    self.parse_dialog_texture]
        for index, (offset, size) in enumerate(self.sections):
            builder = None
            if index < len(builders):
                builder = builders[index]
            self.nodes.append(self.parse_section(index, offset, size, builder))
        self.link_doors()

    def check_header(self):
        data = self.data
        if len(data) < MIN_FILE_SIZE:
            raise ValueError(f'{self.name}: {len(data)} bytes is too small for a WDT header')
        count = read_u32(data, 0)
        if not 1 <= count <= MAX_SECTION_COUNT:
            raise ValueError(f'{self.name}: section count {count} does not look like a WDT')

    def parse_section_table(self):
        count = read_u32(self.data, 0)
        header = Node('File header', 0, SECTION_TABLE_OFFSET + count * SECTION_ENTRY_SIZE)
        header.fields.append(self.u32_field(0, 'Section count', relative_offset=0))
        header.fields.append(Field(4, 12, 'Unused', 'bytes', '', 'always zero', 4))
        for index in range(count):
            entry_offset = SECTION_TABLE_OFFSET + index * SECTION_ENTRY_SIZE
            offset, size = struct.unpack_from('<2I', self.data, entry_offset)
            self.sections.append((offset, size))
            if index < len(SECTION_NAMES):
                section_name = SECTION_NAMES[index]
            else:
                section_name = f'section {index}'
            header.fields.append(self.u32_field(entry_offset, f'Sec {index} offset', section_name,
                                                entry_offset, format_hex))
            end_note = f'ends at {format_hex(offset + size)}'
            if not self.in_bounds(offset, size):
                end_note += '  (OUT OF FILE)'
                self.warnings.append(f'section {index} runs past the end of the file')
            header.fields.append(self.u32_field(entry_offset + 4, f'Sec {index} size', end_note,
                                                entry_offset + 4, format_hex))
        return header

    def parse_section(self, index, offset, size, builder):
        if index < len(SECTION_NAMES):
            section_name = SECTION_NAMES[index]
        else:
            section_name = 'unknown'
        node = Node(f'Section {index}: {section_name}', offset, offset + size)
        node.info = f'offset {format_hex(offset)}, size {format_hex(size)}'
        if size and self.in_bounds(offset, size):
            try:
                if builder:
                    builder(node, offset, size)
                else:
                    node.fields.append(Field(offset, size, 'Raw data', 'bytes', f'{size} bytes'))
            except Exception as error:
                self.warnings.append(f'section {index}: {error}')
                node.fields.append(Field(offset, size, 'Raw data (parse failed)', 'bytes', str(error)))
        elif not size:
            node.info += '  (empty)'
        return node

    def parse_areas_and_entrances(self, node, section_start, size):
        area_table_offset, area_table_size, entrance_table_offset, entrance_table_size = \
            struct.unpack_from('<4I', self.data, section_start)
        node.fields += [
            self.u32_field(section_start, 'Area table offset',
                           f'file {format_hex(section_start + area_table_offset)}', 0, format_hex),
            self.u32_field(section_start + 4, 'Area table size',
                           f'{area_table_size // AREA_SIZE} areas', 4, format_hex),
            self.u32_field(section_start + 8, 'Entrance table offset',
                           f'file {format_hex(section_start + entrance_table_offset)}', 8, format_hex),
            self.u32_field(section_start + 12, 'Entrance table size',
                           f'{entrance_table_size // ENTRANCE_SIZE} entrances', 12, format_hex),
        ]

        area_table = self.parse_area_table(section_start + area_table_offset, area_table_size)
        node.children.append(area_table)
        self.area_table_node = area_table
        node.children.append(self.build_music_node(area_table))

        entrance_table = self.parse_entrance_table(section_start + entrance_table_offset,
                                                   entrance_table_size)
        node.children.append(entrance_table)
        self.entrance_table_node = entrance_table

        tables_end = section_start + max(area_table_offset + area_table_size,
                                         entrance_table_offset + entrance_table_size)
        if tables_end < section_start + size:
            node.fields.append(Field(tables_end, section_start + size - tables_end,
                                     'Trailing bytes', 'bytes', ''))

    def parse_area_table(self, table_start, table_size):
        area_count = table_size // AREA_SIZE
        table = Node(f'Area table ({area_count})', table_start, table_start + table_size)
        columns = ['Area', 'Room', 'Offset', 'Group', 'Field BGM', 'Battle BGM', 'Flags',
                   '+14', '+18', '+1C', '+20', '+24', 'Alt BGM', 'Entrances']
        rows = []
        for index in range(area_count):
            offset = table_start + index * AREA_SIZE
            if not self.in_bounds(offset, AREA_SIZE):
                self.warnings.append(f'area {index} past end of file')
                break
            values = struct.unpack_from('<16I', self.data, offset)
            self.areas.append({'index': index, 'off': offset, 'vals': values})
            area_node = self.build_area_node(index, offset, values)
            table.children.append(area_node)
            rows.append((area_node, self.area_summary_row(index, offset, values)))
        table.summary = (columns, rows)
        return table

    def build_area_node(self, index, offset, values):
        area_node = Node(f'Area {index:02d}  {self.room(index)}', offset, offset + AREA_SIZE)
        for relative_offset, name, note in self.AREA_FIELDS:
            if relative_offset == AREA_FLAGS_OFFSET:
                formatter = format_hex
            else:
                formatter = format_number
            area_field = self.u32_field(offset + relative_offset, name, note, relative_offset, formatter)
            if relative_offset in self.BGM_OFFSETS:
                self.annotate_bgm_field(area_field, index, relative_offset, values[relative_offset // 4])
            area_node.fields.append(area_field)
        return area_node

    def annotate_bgm_field(self, area_field, area_index, relative_offset, music_id):
        label = music_label(self.music, music_id)
        if label:
            area_field.value = f'{area_field.value}  {label}'
        detail = music_detail(self.music, music_id)
        if detail:
            if relative_offset >= AREA_ALT_BGM_FIRST_OFFSET:
                area_field.note = f'{detail}; {area_field.note}'
            else:
                area_field.note = detail
        if label == MISSING_TRACK_LABEL:
            self.warnings.append(f'{self.room(area_index)} +{relative_offset:02X}: '
                                 f'BGM {music_id} is not in music.csv')

    def area_summary_row(self, index, offset, values):
        alt_bgm = ''
        if values[AREA_ALT_FIELD_BGM] or values[AREA_ALT_BATTLE_BGM]:
            alt_bgm = f'{self.bgm(values[AREA_ALT_FIELD_BGM])} / {self.bgm(values[AREA_ALT_BATTLE_BGM])}'
        return [index, self.room(index), format_hex(offset), values[AREA_GROUP],
                self.bgm(values[AREA_FIELD_BGM]), self.bgm(values[AREA_BATTLE_BGM]),
                format_hex(values[AREA_FLAGS]), format_hex(values[AREA_UNKNOWN_14]),
                format_hex(values[AREA_VOLUME_18]), format_hex(values[AREA_VOLUME_1C]),
                format_hex(values[AREA_AMBIENT_SE_1]), format_hex(values[AREA_AMBIENT_SE_2]),
                alt_bgm, '']

    def area_bgm_ids(self, area):
        values = area['vals']
        return (values[AREA_FIELD_BGM], values[AREA_BATTLE_BGM],
                values[AREA_ALT_FIELD_BGM], values[AREA_ALT_BATTLE_BGM])

    def collect_music_uses(self):
        uses = {}
        for area in self.areas:
            for relative_offset, kind in self.BGM_OFFSETS.items():
                music_id = area['vals'][relative_offset // 4]
                if music_id:
                    rooms_by_kind = uses.setdefault(music_id, {})
                    rooms_by_kind.setdefault(kind, []).append(self.room(area['index']))
        return uses

    def first_area_node_using(self, music_id, area_table):
        for area, area_node in zip(self.areas, area_table.children):
            if music_id in self.area_bgm_ids(area):
                return area_node
        return None

    def build_music_node(self, area_table):
        uses = self.collect_music_uses()
        music_node = Node(f'Music used ({len(uses)} tracks)', area_table.start, area_table.end)
        if self.music:
            music_node.info = 'BGM ids from the area table, named from KH1-DOCUMENTATION/data/sound/music.csv'
        else:
            music_node.info = 'music.csv not loaded: ids only (see --music / KH1_MUSIC_CSV)'
        columns = ['BGM', 'Track', 'File / length', 'Field in', 'Battle in', 'Alt (story >= 0x2B) in']
        rows = []
        for music_id in sorted(uses):
            rooms_by_kind = uses[music_id]
            alt_rooms = sorted(set(rooms_by_kind.get('alt field', []) + rooms_by_kind.get('alt battle', [])))
            track = music_label(self.music, music_id)
            if not track:
                track = '?'
            rows.append((self.first_area_node_using(music_id, area_table), [
                f'{music_id} ({format_hex(music_id)})', track, music_detail(self.music, music_id),
                compact_room_list(rooms_by_kind.get('field', [])),
                compact_room_list(rooms_by_kind.get('battle', [])),
                compact_room_list(alt_rooms)]))
        music_node.summary = (columns, rows)
        return music_node

    def parse_entrance_table(self, table_start, table_size):
        entrance_count = table_size // ENTRANCE_SIZE
        table = Node(f'Entrance table ({entrance_count})', table_start, table_start + table_size)
        columns = ['Entrance', 'Offset', 'Area', 'Room', 'Sora x, y, z, rot',
                   'Slot 1', 'Slot 2', 'Used by']
        rows = []
        for index in range(entrance_count):
            offset = table_start + index * ENTRANCE_SIZE
            if not self.in_bounds(offset, ENTRANCE_SIZE):
                self.warnings.append(f'entrance {index} past end of file')
                break
            area = read_u32(self.data, offset)
            slots = []
            for slot in range(len(self.SLOT_NAMES)):
                slots.append(struct.unpack_from('<4f', self.data, offset + SPAWN_SLOT_SIZE * (slot + 1)))
            self.entrances.append({'index': index, 'off': offset, 'area': area, 'slots': slots,
                                   'pad': struct.unpack_from('<3I', self.data, offset + 4)})
            entrance_node = self.build_entrance_node(index, offset, area)
            table.children.append(entrance_node)
            rows.append((entrance_node, [f'{index} ({format_hex(index)})', format_hex(offset), area,
                                         self.room(area), format_spawn_summary(slots[0]),
                                         format_spawn_summary(slots[1]), format_spawn_summary(slots[2]),
                                         '']))
        table.summary = (columns, rows)
        return table

    def build_entrance_node(self, index, offset, area):
        entrance_node = Node(f'Entrance {index:02d} ({format_hex(index)})  -> {self.room(area)}',
                             offset, offset + ENTRANCE_SIZE)
        entrance_node.fields.append(self.u32_field(offset, 'Area', f'loads {self.room(area)}.ard', 0))
        for padding_offset in (4, 8, 12):
            entrance_node.fields.append(self.u32_field(offset + padding_offset,
                                                       f'Unused +{padding_offset:X}', '', padding_offset))
        for slot, slot_name in enumerate(self.SLOT_NAMES):
            slot_offset = SPAWN_SLOT_SIZE * (slot + 1)
            for axis_index, axis in enumerate(AXIS_NAMES):
                relative_offset = slot_offset + axis_index * 4
                value = read_f32(self.data, offset + relative_offset)
                note = ''
                if axis == 'rot':
                    note = 'radians'
                entrance_node.fields.append(Field(offset + relative_offset, 4, f'{slot_name} {axis}', 'f32',
                                                  format_float(value), note, relative_offset))
        return entrance_node

    def parse_world_script(self, node, section_start, size):
        _, _, kgr_count, string_table_offset = struct.unpack_from('<4I', self.data, section_start)
        node.fields += [
            self.u32_field(section_start, 'Header word 0', 'always 0', 0),
            self.u32_field(section_start + 4, 'Header word 1', 'always 0', 4),
            self.u32_field(section_start + 8, 'KGR count', '', 8),
            self.u32_field(section_start + 12, 'String table offset',
                           f'file {format_hex(section_start + string_table_offset)}', 12, format_hex),
        ]
        kgr_offsets = []
        for index in range(kgr_count):
            entry_offset = section_start + SCRIPT_HEADER_SIZE + index * 4
            if not self.in_bounds(entry_offset, 4):
                break
            kgr_offset = read_u32(self.data, entry_offset)
            kgr_offsets.append(kgr_offset)
            node.fields.append(self.u32_field(entry_offset, f'KGR {index} offset',
                                              f'file {format_hex(section_start + kgr_offset)}',
                                              SCRIPT_HEADER_SIZE + index * 4, format_hex))

        if kgr_offsets:
            first_kgr = section_start + min(kgr_offsets)
        else:
            first_kgr = section_start + size
        string_table_start = section_start + string_table_offset
        if string_table_start < first_kgr:
            node.children.append(self.build_string_table_node(section_start, size,
                                                              string_table_start, first_kgr))

        columns = ['KGR', 'Offset', 'Size', 'Scripts', 'Change_area targets']
        rows = []
        for index, kgr_offset in enumerate(kgr_offsets):
            kgr_start = section_start + kgr_offset
            kgr_end = section_start + self.next_kgr_offset(kgr_offset, kgr_offsets, size)
            kgr_node = self.build_kgr_node(index, kgr_start, kgr_end)
            node.children.append(kgr_node)
            script_count = ''
            if self.in_bounds(kgr_start, KGR_HEADER_SIZE):
                script_count = self.data[kgr_start + KGR_SCRIPT_COUNT_OFFSET]
            rows.append((kgr_node, [index, format_hex(kgr_start), format_hex(kgr_end - kgr_start),
                                    script_count, '']))
        if kgr_offsets:
            overview_start = section_start + min(kgr_offsets)
        else:
            overview_start = section_start
        overview = Node(f'Door targets ({len(kgr_offsets)} KGRs)', overview_start, section_start + size)
        overview.info = 'every `push N; Change_area` per KGR; double-click a row to open the KGR'
        overview.summary = (columns, rows)
        node.children.insert(0, overview)
        self.door_overview_node = overview

    def next_kgr_offset(self, kgr_offset, kgr_offsets, section_size):
        later_offsets = [offset for offset in kgr_offsets + [section_size] if offset > kgr_offset]
        if later_offsets:
            return min(later_offsets)
        return section_size

    def build_string_table_node(self, section_start, section_size, table_start, table_end):
        table = Node('String table', table_start, table_end)
        string_count = 0
        if self.in_bounds(table_start, 4):
            string_count = read_u32(self.data, table_start)
        table.fields.append(self.u32_field(table_start, 'String count', '', 0))
        strings = read_world_strings(self.data[section_start:section_start + section_size])
        for index, text in sorted(strings.items()):
            table.fields.append(Field(table_start, 0, f'String {index}', 'khscii', text))
        data_size = table_end - table_start - 4
        if data_size > 0:
            table.fields.append(Field(table_start + 4, data_size, 'String data', 'bytes',
                                      f'{data_size} bytes', f'{string_count} strings'))
        return table

    def build_kgr_node(self, index, kgr_start, kgr_end):
        kgr_node = Node(f'KGR {index}', kgr_start, kgr_end)
        kgr_info = {'index': index, 'off': kgr_start, 'end': kgr_end, 'targets': []}
        if self.in_bounds(kgr_start, KGR_HEADER_SIZE) and self.data[kgr_start:kgr_start + 4] == KGR_MAGIC:
            kgr_info['targets'] = self.find_door_targets(kgr_start + KGR_HEADER_SIZE, kgr_end)
            self.add_kgr_fields(kgr_node, kgr_start, kgr_end, kgr_info['targets'])
        else:
            self.warnings.append(f'KGR {index} at {format_hex(kgr_start)} has no KGR magic')
            kgr_node.fields.append(Field(kgr_start, kgr_end - kgr_start, 'Raw data (no KGR magic)', 'bytes', ''))
        if index == 0:
            kgr_node.info = 'runs once per room load (Get_area_number switch)'
        else:
            event_id = FIRST_DOOR_EVENT_ID + index
            kgr_node.info = f'Trigger_event {event_id} / polygon event id {event_id}'
        self.kgrs.append(kgr_info)
        return kgr_node

    def add_kgr_fields(self, kgr_node, kgr_start, kgr_end, targets):
        script_count = self.data[kgr_start + KGR_SCRIPT_COUNT_OFFSET]
        stream_start = kgr_start + KGR_HEADER_SIZE
        stream_length = kgr_end - stream_start
        kgr_node.fields += [
            Field(kgr_start, 4, 'Magic', 'char[4]', "'KGR\\0'", '', 0),
            self.u32_field(kgr_start + 4, 'Unknown 0', '', 4),
            self.u32_field(kgr_start + 8, 'Unknown 1', '', 8),
            Field(kgr_start + KGR_SCRIPT_COUNT_OFFSET, 1, 'Script count', 'u8', str(script_count), '',
                  KGR_SCRIPT_COUNT_OFFSET),
            Field(stream_start, stream_length, 'Instruction stream', 'bytes', f'{stream_length} bytes',
                  'disassemble with: evdl_tool.py disasm', KGR_HEADER_SIZE),
        ]
        for push_offset, entrance, syscall, world in targets:
            if syscall == SYSCALL_CHANGE_AREA:
                call_name = 'Change_area'
            else:
                call_name = 'Start_map_change_rewrite_set'
            world_note = ''
            if world is not None:
                world_note = f' of world {world}'
            kgr_node.fields.append(Field(push_offset, 4, 'push (entrance)', 'instr',
                                         f'{entrance} ({format_hex(entrance)})',
                                         f'{call_name} -> entrance {entrance}{world_note}',
                                         push_offset - kgr_start))

    def find_door_targets(self, start, end):
        positions = list(range(start, end - 3, INSTRUCTION_SIZE))
        words = [read_u32(self.data, position) for position in positions]
        targets = []
        for index, word in enumerate(words):
            if opcode_of(word) != OP_SYSCALL or operand_of(word) not in DOOR_SYSCALLS:
                continue
            if index == 0 or opcode_of(words[index - 1]) != OP_PUSH:
                continue
            syscall = operand_of(word)
            world = None
            if syscall == SYSCALL_MAP_CHANGE_REWRITE_SET and index >= WORLD_PUSH_DISTANCE:
                world_word = words[index - WORLD_PUSH_DISTANCE]
                if opcode_of(world_word) == OP_PUSH:
                    world = operand_of(world_word)
            targets.append((positions[index - 1], operand_of(words[index - 1]), syscall, world))
        return targets

    def link_doors(self):
        kgrs_by_entrance = {}
        for kgr in self.kgrs:
            for _, entrance, _, world in kgr['targets']:
                if world is None:
                    kgrs_by_entrance.setdefault(entrance, []).append(kgr['index'])
        entrances_by_area = {}
        for entrance in self.entrances:
            entrances_by_area.setdefault(entrance['area'], []).append(entrance['index'])

        if self.entrance_table_node:
            for index, (_, values) in enumerate(self.entrance_table_node.summary[1]):
                kgr_indices = sorted(set(kgrs_by_entrance.get(self.entrances[index]['index'], [])))
                values[-1] = ', '.join(f'KGR {kgr_index}' for kgr_index in kgr_indices)
        if self.area_table_node:
            for index, (_, values) in enumerate(self.area_table_node.summary[1]):
                entrance_list = ', '.join(str(entrance) for entrance in entrances_by_area.get(index, []))
                if not entrance_list:
                    entrance_list = '(none)'
                values[-1] = entrance_list
        if self.door_overview_node:
            for _, values in self.door_overview_node.summary[1]:
                kgr = self.kgrs[values[0]]
                values[-1] = ', '.join(self.describe_target(entrance, world)
                                       for _, entrance, _, world in kgr['targets'])
        for entrance in self.entrances:
            entrance['used_by'] = sorted(set(kgrs_by_entrance.get(entrance['index'], [])))

    def describe_target(self, entrance, world):
        if world is not None:
            return f'{entrance} (world {world})'
        if entrance < len(self.entrances):
            return f'{entrance} ({self.room(self.entrances[entrance]["area"])})'
        return f'{entrance} (?)'

    def parse_text_colours(self, node, section_start, size):
        for colour_set in range(size // COLOUR_SET_SIZE):
            for colour in range(COLOURS_PER_SET):
                offset = section_start + colour_set * COLOUR_SET_SIZE + colour * 4
                red, green, blue, alpha = self.data[offset:offset + 4]
                note = ''
                if alpha == 0:
                    note = 'transparent'
                node.fields.append(Field(offset, 4, f'Colour set {colour_set}, colour {colour}', 'RGBA',
                                         f'#{red:02X}{green:02X}{blue:02X}  a={format_hex(alpha)}',
                                         note, offset - section_start, (red, green, blue, alpha)))
        node.info = 'fnc_copy_world_text_palette_entry copies one 16-byte set (4 colours) per text style'

    def parse_title_logo(self, node, section_start, size):
        data = self.data
        if data[section_start:section_start + 4] != TIM2_MAGIC:
            node.fields.append(Field(section_start, size, 'Raw data (no TIM2 magic)', 'bytes', ''))
            return
        node.fields += [
            Field(section_start, 4, 'Magic', 'char[4]', "'TIM2'", '', 0),
            Field(section_start + 4, 1, 'Version', 'u8', str(data[section_start + 4]), '', 4),
            Field(section_start + 5, 1, 'Alignment', 'u8', str(data[section_start + 5]), '0 = 16 bytes', 5),
            Field(section_start + 6, 2, 'Picture count', 'u16', str(struct.unpack_from('<H', data, section_start + 6)[0]),
                  '', 6),
            Field(section_start + 8, 8, 'Reserved', 'bytes', '', '', 8),
        ]
        picture = section_start + TIM2_FILE_HEADER_SIZE
        (total_size, clut_size, image_size, header_size, clut_colours, picture_format, mipmaps,
         clut_type, image_type, width, height) = struct.unpack_from('<3I2H4B2H', data, picture)
        image_type_name = TIM2_IMAGE_TYPE_NAMES.get(image_type, '?')
        picture_fields = [
            (0x00, 4, 'Total size', 'u32', format_hex(total_size)),
            (0x04, 4, 'CLUT size', 'u32', format_hex(clut_size)),
            (0x08, 4, 'Image size', 'u32', format_hex(image_size)),
            (0x0C, 2, 'Header size', 'u16', format_hex(header_size)),
            (0x0E, 2, 'CLUT colours', 'u16', str(clut_colours)),
            (0x10, 1, 'Picture format', 'u8', str(picture_format)),
            (0x11, 1, 'Mipmaps', 'u8', str(mipmaps)),
            (0x12, 1, 'CLUT type', 'u8', format_hex(clut_type)),
            (0x13, 1, 'Image type', 'u8', f'{image_type} ({image_type_name})'),
            (0x14, 2, 'Width', 'u16', str(width)),
            (0x16, 2, 'Height', 'u16', str(height)),
            (0x18, 8, 'GS TEX0', 'u64', format_hex(struct.unpack_from('<Q', data, picture + 0x18)[0])),
            (0x20, 8, 'GS TEX1', 'u64', format_hex(struct.unpack_from('<Q', data, picture + 0x20)[0])),
            (0x28, 4, 'GS regs', 'u32', format_hex(read_u32(data, picture + 0x28))),
            (0x2C, 4, 'GS TEXCLUT', 'u32', format_hex(read_u32(data, picture + 0x2C))),
        ]
        for relative_offset, field_size, name, field_type, value in picture_fields:
            node.fields.append(Field(picture + relative_offset, field_size, name, field_type, value, '',
                                     TIM2_FILE_HEADER_SIZE + relative_offset))
        pixels = picture + header_size
        clut = pixels + image_size
        node.fields.append(Field(pixels, image_size, 'Pixels', 'bytes', f'{width}x{height}', '',
                                 pixels - section_start))
        node.fields.append(Field(clut, clut_size, 'CLUT', 'bytes', f'{clut_colours} colours', '',
                                 clut - section_start))
        is_8bpp_with_full_palette = image_type == TIM2_IMAGE_TYPE_8BPP and clut_colours == PALETTE_COLOURS
        if is_8bpp_with_full_palette and self.in_bounds(clut, PALETTE_SIZE):
            uses_csm1 = (clut_type & TIM2_CLUT_CSM2_FLAG) == 0
            rgba = indexed_to_rgba(data[pixels:pixels + width * height], data[clut:clut + PALETTE_SIZE],
                                   swizzled=uses_csm1)
            node.image = (width, height, rgba, f'{self.world}_tim2.png')
        node.info = 'world title logo; remastered HD copy: remastered/<world>.wdt/-<pixels offset>.dds'

    def parse_dialog_texture(self, node, section_start, size):
        width = DIALOG_TEXTURE_WIDTH
        height = DIALOG_TEXTURE_HEIGHT
        pixel_bytes = width * height
        if size < pixel_bytes + PALETTE_SIZE:
            node.fields.append(Field(section_start, size, 'Raw data', 'bytes', f'{size} bytes'))
            return
        clut = section_start + pixel_bytes
        texture_end = clut + PALETTE_SIZE
        node.fields.append(Field(section_start, pixel_bytes, 'Pixels', 'bytes', f'{width}x{height} 8bpp',
                                 '', 0))
        node.fields.append(Field(clut, PALETTE_SIZE, 'CLUT', 'bytes', '256 colours RGBA', '', pixel_bytes))
        if size > pixel_bytes + PALETTE_SIZE:
            node.fields.append(Field(texture_end, size - pixel_bytes - PALETTE_SIZE,
                                     'Trailing bytes', 'bytes', ''))
        rgba = indexed_to_rgba(self.data[section_start:clut], self.data[clut:texture_end], True)
        node.image = (width, height, rgba, f'{self.world}_texture.png')
        node.info = ('dialog window / speech bubble / button skin; '
                     'remastered HD copy: remastered/<world>.wdt/-<offset>.png (512x256)')


def raw_hex(data, wdt_field, limit=RAW_HEX_LIMIT):
    shown = min(wdt_field.size, limit)
    text = data[wdt_field.offset:wdt_field.offset + shown].hex(' ').upper()
    if wdt_field.size > limit:
        text += ' ..'
    return text
