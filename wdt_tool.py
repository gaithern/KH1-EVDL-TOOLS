#!/usr/bin/env python3
"""Read-only viewer for KH1 <world>.wdt files: a tkinter GUI plus `dump` and
`verify` command-line modes."""

import base64
import csv
import os
import struct
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path

HELP_TEXT = """
Usage:
    python wdt_tool.py [--music music.csv] [file.wdt]         open the GUI
    python wdt_tool.py [--music music.csv] dump <file.wdt>    print every field
    python wdt_tool.py [--music music.csv] verify [dir]       check every .wdt in a folder
"""

DEFAULT_DIR = r'C:\OpenKH\OpenKHEGS\data\kh1'

SECTION_NAMES = [
    'Areas & entrances',
    'World script (EVDL)',
    'Text colours',
    'Unused',
    'World logo (TIM2)',
    'Dialog window texture',
]

MUSIC_CSV_RELATIVE_PATH = Path('data') / 'sound' / 'music.csv'
MISSING_TRACK_LABEL = 'NOT IN music.csv'

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
PALETTE_COLOURS = 256
PALETTE_SIZE = 0x400

DIALOG_TEXTURE_WIDTH = 256
DIALOG_TEXTURE_HEIGHT = 128

RAW_HEX_LIMIT = 16


def find_music_csv():
    env_path = os.environ.get('KH1_MUSIC_CSV')
    if env_path and Path(env_path).is_file():
        return Path(env_path)
    script_folder = Path(__file__).resolve().parent
    for base in (script_folder.parent, Path.cwd(), Path.cwd().parent):
        candidate = base / 'KH1-DOCUMENTATION' / MUSIC_CSV_RELATIVE_PATH
        if candidate.is_file():
            return candidate
    return None


def load_music(path):
    music = {}
    with open(path, encoding='utf-8-sig', newline='') as csv_file:
        for row in csv.DictReader(csv_file):
            try:
                music[int(row['Music ID'])] = row
            except (KeyError, TypeError, ValueError):
                continue
    return music


def music_label(music, music_id):
    if music_id == 0:
        return 'none'
    if not music:
        return ''
    row = music.get(music_id)
    if row is None:
        return MISSING_TRACK_LABEL
    name = row.get('Name')
    if not name:
        name = '?'
    if name == 'N/A':
        return 'empty stub (N/A)'
    return name


def music_detail(music, music_id):
    if not music:
        return ''
    row = music.get(music_id)
    if not row:
        return ''
    parts = [f'music{music_id:03d}.win32.scd']
    if row.get('Duration (s)'):
        parts.append(f'{float(row["Duration (s)"]):.1f} s')
    if row.get('Loops') == 'Yes' and row.get('Loop Start (s)'):
        parts.append(f'loops from {float(row["Loop Start (s)"]):.1f} s')
    elif row.get('Loops') == 'No':
        parts.append('no loop')
    if row.get('Codec', '').startswith('None'):
        parts.append(row['Codec'])
    return ', '.join(parts)


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
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'ev'))
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


def csm1_palette_index(index):
    bits_0_to_2_and_5_to_7 = index & 0xE7
    bit_4_moved_to_3 = (index & 0x10) >> 1
    bit_3_moved_to_4 = (index & 0x08) << 1
    return bits_0_to_2_and_5_to_7 | bit_4_moved_to_3 | bit_3_moved_to_4


def ps2_alpha_to_8bit(alpha):
    return min(255, alpha * 2)


def indexed_to_rgba(pixels: bytes, clut: bytes, swizzled: bool) -> bytes:
    palette = []
    for index in range(PALETTE_COLOURS):
        clut_index = index
        if swizzled:
            clut_index = csm1_palette_index(index)
        red, green, blue, alpha = clut[clut_index * 4:clut_index * 4 + 4]
        palette.append(bytes((red, green, blue, ps2_alpha_to_8bit(alpha))))
    return b''.join(palette[pixel] for pixel in pixels)


def png_chunk(tag, body):
    checksum = zlib.crc32(tag + body) & 0xFFFFFFFF
    return struct.pack('>I', len(body)) + tag + body + struct.pack('>I', checksum)


def png_bytes(width: int, height: int, rgba: bytes) -> bytes:
    row_size = width * 4
    scanlines = []
    for y in range(height):
        scanlines.append(b'\x00' + rgba[y * row_size:(y + 1) * row_size])
    header = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', header) +
            png_chunk(b'IDAT', zlib.compress(b''.join(scanlines), 9)) + png_chunk(b'IEND', b''))


def checker_background(x, y):
    if ((x // 8) + (y // 8)) % 2 == 1:
        return 0xCC
    return 0x99


def blend_over(channel, alpha, background):
    return (channel * alpha + background * (255 - alpha)) // 255


def checker_composite(width, height, rgba, scale):
    output = bytearray()
    for y in range(height * scale):
        source_y = y // scale
        for x in range(width * scale):
            source_x = x // scale
            pixel = (source_y * width + source_x) * 4
            red, green, blue, alpha = rgba[pixel:pixel + 4]
            background = checker_background(x, y)
            output += bytes((blend_over(red, alpha, background), blend_over(green, alpha, background),
                             blend_over(blue, alpha, background), 255))
    return png_bytes(width * scale, height * scale, bytes(output))


def raw_hex(data, wdt_field, limit=RAW_HEX_LIMIT):
    shown = min(wdt_field.size, limit)
    text = data[wdt_field.offset:wdt_field.offset + shown].hex(' ').upper()
    if wdt_field.size > limit:
        text += ' ..'
    return text


def print_node_tree(wdt, nodes, depth):
    indent = '  ' * depth
    for node in nodes:
        print(f'{indent}== {node.title}  [{format_hex(node.start)}..{format_hex(node.end)})  {node.info}')
        for node_field in node.fields:
            if node_field.relative_offset is not None:
                relative = f'+{node_field.relative_offset:02X}'
            else:
                relative = '   '
            print(f'{indent}   {node_field.offset:06X} {relative:>5}  {raw_hex(wdt.data, node_field):<24} '
                  f'{node_field.type:<7} {node_field.name:<24} {node_field.value}  {node_field.note}')
        if node.summary and not node.fields:
            columns, rows = node.summary
            print(f'{indent}   ' + ' | '.join(columns))
            for _, values in rows:
                print(f'{indent}   ' + ' | '.join(str(value) for value in values))
        print_node_tree(wdt, node.children, depth + 1)


def dump(path, music=None):
    wdt = Wdt(Path(path).read_bytes(), Path(path).name, music)
    print_node_tree(wdt, wdt.nodes, 0)
    for warning in wdt.warnings:
        print('WARNING:', warning)


def layout_problems(wdt):
    problems = list(wdt.warnings)
    expected_offset = wdt.sections[0][0]
    for index, (offset, size) in enumerate(wdt.sections):
        if offset != expected_offset:
            problems.append(f'section {index} starts at {format_hex(offset)}, '
                            f'expected {format_hex(expected_offset)}')
        expected_offset = offset + size
    if expected_offset != len(wdt.data):
        problems.append(f'sections end at {format_hex(expected_offset)}, file is {format_hex(len(wdt.data))}')
    for entrance in wdt.entrances:
        if entrance['area'] >= len(wdt.areas):
            problems.append(f'entrance {entrance["index"]} -> area {entrance["area"]} '
                            f'(only {len(wdt.areas)} areas)')
        if any(entrance['pad']):
            problems.append(f'entrance {entrance["index"]} has non-zero padding {entrance["pad"]}')
    for kgr in wdt.kgrs:
        for _, entrance, _, world in kgr['targets']:
            if world is None and entrance >= len(wdt.entrances):
                problems.append(f'KGR {kgr["index"]} -> entrance {entrance} (only {len(wdt.entrances)})')
    return problems


def verify(folder=DEFAULT_DIR, music=None):
    files = sorted(Path(folder).glob('*.wdt'))
    if not files:
        print(f'no .wdt files in {folder}')
        return 1
    bad_file_count = 0
    for path in files:
        wdt = Wdt(path.read_bytes(), path.name, music)
        problems = layout_problems(wdt)
        door_count = sum(len(kgr['targets']) for kgr in wdt.kgrs)
        image_count = sum(1 for node in wdt.nodes if node.image)
        if problems:
            status = 'BAD'
            bad_file_count += 1
        else:
            status = 'OK '
        print(f'{status} {path.name}: {len(wdt.areas)} areas, {len(wdt.entrances)} entrances, '
              f'{len(wdt.kgrs)} KGRs, {door_count} Change_area pushes, '
              f'images: {image_count}')
        for problem in problems:
            print('     ', problem)
    if bad_file_count:
        return 1
    return 0


def run_gui(initial_path: str = None, music_path=None):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    wdt_file_types = [('World data', '*.wdt'), ('All files', '*.*')]
    column_widths = {'Entrance': 80, 'Offset': 70, 'Area': 50, 'Room': 55, 'Sora x, y, z, rot': 190,
                     'Slot 1': 190, 'Slot 2': 190, 'Used by': 160, 'Group': 55, 'Field BGM': 190,
                     'Battle BGM': 190, 'Flags': 50, '+14': 50, '+18': 50, '+1C': 55, '+20': 65,
                     '+24': 65, 'Alt BGM': 300, 'Entrances': 200, 'KGR': 50, 'Size': 70, 'Scripts': 60,
                     'Change_area targets': 420, 'BGM': 80, 'Track': 220, 'File / length': 290,
                     'Field in': 170, 'Battle in': 170, 'Alt (story >= 0x2B) in': 170}
    stretching_columns = ('Value', 'Note', 'Used by', 'Change_area targets', 'Entrances',
                          'Alt (story >= 0x2B) in')
    field_columns = ('File off', 'Rel', 'Size', 'Raw bytes', 'Type', 'Field', 'Value', 'Note')
    field_column_widths = (80, 50, 45, 200, 60, 170, 290, 380)
    hex_limit = 0x10000
    hex_bytes_column = 10
    hex_last_column = 58
    hex_second_half_column = 25
    state = {'wdt': None, 'path': None, 'node': None, 'items': {}, 'rows': {}, 'img': None,
             'hex_base': 0, 'hex_len': 0, 'field_rows': {}, 'music': {}, 'music_path': None,
             'pending': None}

    root = tk.Tk()
    root.title('WDT Viewer')
    root.geometry('1400x860')

    top = tk.Frame(root)
    top.pack(fill='x', padx=6, pady=4)
    open_button = tk.Button(top, text='Open...')
    open_button.pack(side='left')
    reload_button = tk.Button(top, text='Reload')
    reload_button.pack(side='left', padx=4)
    music_button = tk.Button(top, text='Music table...')
    music_button.pack(side='left')
    path_var = tk.StringVar()
    tk.Entry(top, textvariable=path_var, state='readonly', width=70).pack(side='left', fill='x', expand=True, padx=4)
    tk.Label(top, text='Go to offset:').pack(side='left')
    goto_var = tk.StringVar()
    goto_entry = tk.Entry(top, textvariable=goto_var, width=10)
    goto_entry.pack(side='left', padx=4)
    info_var = tk.StringVar(value='no file loaded')
    tk.Label(root, textvariable=info_var, anchor='w', fg='#444').pack(fill='x', padx=8)

    panes = tk.PanedWindow(root, orient='horizontal', sashrelief='raised')
    panes.pack(fill='both', expand=True, padx=6, pady=2)

    left = tk.Frame(panes)
    panes.add(left, minsize=260, width=320)
    tree = ttk.Treeview(left, columns=('range',), selectmode='browse')
    tree.heading('#0', text='Structure')
    tree.heading('range', text='Range')
    tree.column('#0', width=210)
    tree.column('range', width=110, anchor='w')
    tree_scrollbar = ttk.Scrollbar(left, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=tree_scrollbar.set)
    tree.pack(side='left', fill='both', expand=True)
    tree_scrollbar.pack(side='right', fill='y')

    right = tk.PanedWindow(panes, orient='vertical', sashrelief='raised')
    panes.add(right, minsize=500)

    upper = tk.Frame(right)
    right.add(upper, minsize=200, height=470)
    title_var = tk.StringVar()
    tk.Label(upper, textvariable=title_var, anchor='w', font=('Segoe UI', 10, 'bold')).pack(fill='x')
    node_info_var = tk.StringVar()
    tk.Label(upper, textvariable=node_info_var, anchor='w', fg='#555').pack(fill='x')

    image_bar = tk.Frame(upper)
    image_label = tk.Label(image_bar, bd=1, relief='sunken')
    image_label.pack(side='left', padx=2, pady=2)
    save_png_button = tk.Button(image_bar, text='Save PNG...')
    save_png_button.pack(side='left', padx=6, anchor='n')

    table_frame = tk.Frame(upper)
    table_frame.pack(fill='both', expand=True)
    table = ttk.Treeview(table_frame, show='headings', selectmode='browse')
    table_xscroll = ttk.Scrollbar(table_frame, orient='horizontal', command=table.xview)
    table_yscroll = ttk.Scrollbar(table_frame, orient='vertical', command=table.yview)
    table.configure(xscrollcommand=table_xscroll.set, yscrollcommand=table_yscroll.set)
    table.grid(row=0, column=0, sticky='nsew')
    table_yscroll.grid(row=0, column=1, sticky='ns')
    table_xscroll.grid(row=1, column=0, sticky='ew')
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    lower = tk.Frame(right)
    right.add(lower, minsize=120)
    hex_title = tk.StringVar(value='Hex')
    tk.Label(lower, textvariable=hex_title, anchor='w').pack(fill='x')
    hex_box = tk.Text(lower, wrap='none', font=('Consolas', 10), bg='#f7f7f7', cursor='arrow')
    hex_scrollbar = ttk.Scrollbar(lower, orient='vertical', command=hex_box.yview)
    hex_box.configure(yscrollcommand=hex_scrollbar.set)
    hex_box.pack(side='left', fill='both', expand=True)
    hex_scrollbar.pack(side='right', fill='y')
    hex_box.tag_configure('hl', background='#ffd75e')
    hex_box.tag_configure('addr', foreground='#888')
    hex_box.configure(state='disabled')

    def open_file(_event=None):
        if state['path']:
            initial_folder = os.path.dirname(state['path'])
        elif os.path.isdir(DEFAULT_DIR):
            initial_folder = DEFAULT_DIR
        else:
            initial_folder = None
        path = filedialog.askopenfilename(title='Open .wdt', filetypes=wdt_file_types, initialdir=initial_folder)
        if path:
            load(path)

    def reload_file():
        if state['path']:
            load(state['path'])

    def set_music(path, quiet=False):
        try:
            if path:
                state['music'] = load_music(path)
            else:
                state['music'] = {}
            state['music_path'] = path
        except Exception as error:
            state['music'] = {}
            state['music_path'] = None
            if not quiet:
                messagebox.showerror('WDT Viewer', f'Could not read music table {path}:\n{error}')

    def pick_music():
        initial_folder = None
        if state['music_path']:
            initial_folder = os.path.dirname(state['music_path'])
        path = filedialog.askopenfilename(title='Open music.csv', initialdir=initial_folder,
                                          filetypes=[('CSV', '*.csv'), ('All files', '*.*')])
        if path:
            set_music(path)
            if state['path']:
                load(state['path'])

    def status_message(wdt):
        if state['music']:
            music_status = f'{len(state["music"])} tracks from {state["music_path"]}'
        else:
            music_status = 'not loaded (Music table...)'
        message = (f'{len(wdt.data):,} bytes   {len(wdt.sections)} sections   {len(wdt.areas)} areas   '
                   f'{len(wdt.entrances)} entrances   {len(wdt.kgrs)} KGRs   music: {music_status}')
        if wdt.warnings:
            message += '   WARNINGS: ' + '; '.join(wdt.warnings[:3])
        return message

    def add_tree_items(parent, nodes):
        for node in nodes:
            item = tree.insert(parent, 'end', text=node.title, values=(f'{node.start:X}..{node.end:X}',))
            state['items'][item] = node
            add_tree_items(item, node.children)

    def load(path):
        try:
            wdt = Wdt(Path(path).read_bytes(), Path(path).name, state['music'])
        except Exception as error:
            messagebox.showerror('WDT Viewer', f'Could not parse {path}:\n{error}')
            return
        state.update(wdt=wdt, path=path, items={})
        path_var.set(path)
        info_var.set(status_message(wdt))
        tree.delete(*tree.get_children())
        add_tree_items('', wdt.nodes)
        top_items = tree.get_children()
        for item in top_items:
            tree.item(item, open=True)
        if top_items:
            if len(top_items) > 1:
                first_section = top_items[1]
            else:
                first_section = top_items[0]
            tree.selection_set(first_section)
            tree.see(first_section)

    def set_columns(columns, widths):
        table.configure(columns=columns)
        for column, width in zip(columns, widths):
            table.heading(column, text=column)
            table.column(column, width=width, stretch=column in stretching_columns, anchor='w')

    def show_image(node):
        if not node.image:
            image_bar.pack_forget()
            return
        width, height, rgba, _ = node.image
        scale = 1
        if width <= 256:
            scale = 2
        state['img'] = tk.PhotoImage(data=base64.b64encode(checker_composite(width, height, rgba, scale)))
        image_label.configure(image=state['img'])
        image_bar.pack(fill='x', before=table_frame)

    def show_summary_rows(node):
        columns, rows = node.summary
        widths = [column_widths.get(column, max(60, len(column) * 9 + 30)) for column in columns]
        set_columns(columns, widths)
        for target, values in rows:
            item = table.insert('', 'end', values=values)
            state['rows'][item] = ('node', target)

    def colour_tag(colour):
        red, green, blue, _ = colour
        tag = f'c{red:02X}{green:02X}{blue:02X}'
        brightness = (red * 299 + green * 587 + blue * 114) / 1000
        foreground = '#fff'
        if brightness > 128:
            foreground = '#000'
        table.tag_configure(tag, background=f'#{red:02X}{green:02X}{blue:02X}', foreground=foreground)
        return tag

    def show_field_rows(node):
        wdt = state['wdt']
        set_columns(field_columns, field_column_widths)
        for index, node_field in enumerate(node.fields):
            relative = ''
            if node_field.relative_offset is not None:
                relative = f'+{node_field.relative_offset:X}'
            tags = ()
            if node_field.color:
                tags = (colour_tag(node_field.color),)
            raw = ''
            if node_field.size:
                raw = raw_hex(wdt.data, node_field)
            item = table.insert('', 'end', tags=tags, values=(
                format_hex(node_field.offset), relative, node_field.size, raw, node_field.type,
                node_field.name, node_field.value, node_field.note))
            state['rows'][item] = ('field', index)
            state['field_rows'][index] = item
        if node.summary:
            child_count = len(node.summary[1])
            table.insert('', 'end', values=('', '', '', '', '',
                                            f'-- {child_count} children: expand in the tree --', '', ''))

    def show_node(node):
        state['node'] = node
        title_var.set(f'{node.title}    file {format_hex(node.start)}..{format_hex(node.end)}  '
                      f'({node.end - node.start} bytes)')
        node_info_var.set(node.info)
        table.delete(*table.get_children())
        state['rows'] = {}
        state['field_rows'] = {}
        show_image(node)
        if node.summary and not node.fields:
            show_summary_rows(node)
        else:
            show_field_rows(node)
        show_hex(node.start, node.end)

    def hex_line(row_start, start, length):
        cells = []
        characters = []
        for position in range(row_start, row_start + 16):
            if start <= position < start + length:
                value = state['wdt'].data[position]
                cells.append(f'{value:02X}')
                if 32 <= value < 127:
                    characters.append(chr(value))
                else:
                    characters.append('.')
            else:
                cells.append('  ')
                characters.append(' ')
        return f'{row_start:08X}  {" ".join(cells[:8])}  {" ".join(cells[8:])}  {"".join(characters)}'

    def row_start_of(offset):
        return offset - offset % 16

    def show_hex(start, end):
        length = min(end - start, hex_limit)
        state['hex_base'] = start
        state['hex_len'] = length
        hex_box.configure(state='normal')
        hex_box.delete('1.0', 'end')
        lines = []
        for row_start in range(row_start_of(start), start + length, 16):
            lines.append(hex_line(row_start, start, length))
        hex_box.insert('1.0', '\n'.join(lines))
        for line_index in range(len(lines)):
            hex_box.tag_add('addr', f'{line_index + 1}.0', f'{line_index + 1}.8')
        hex_box.configure(state='disabled')
        more = ''
        if end - start > hex_limit:
            more = f'  (first {hex_limit:#x} bytes shown)'
        hex_title.set(f'Hex  {format_hex(start)}..{format_hex(end)}{more}')

    def hex_text_range(offset):
        line = (row_start_of(offset) - row_start_of(state['hex_base'])) // 16 + 1
        byte_in_row = offset % 16
        column = hex_bytes_column + byte_in_row * 3
        if byte_in_row >= 8:
            column += 1
        return f'{line}.{column}', f'{line}.{column + 2}'

    def highlight(offset, size):
        hex_box.tag_remove('hl', '1.0', 'end')
        shown_start = state['hex_base']
        shown_end = shown_start + state['hex_len']
        low = max(offset, shown_start)
        high = min(offset + size, shown_end)
        for position in range(low, high):
            range_start, range_end = hex_text_range(position)
            hex_box.tag_add('hl', range_start, range_end)
        if low < high:
            hex_box.see(hex_text_range(low)[0])

    def select_table_row(item):
        table.selection_set(item)
        table.see(item)

    def on_tree_select(_event=None):
        selection = tree.selection()
        if not selection:
            return
        node = state['items'][selection[0]]
        if node is not state['node']:
            show_node(node)
        pending_offset = state['pending']
        state['pending'] = None
        if pending_offset is not None:
            focus_field(node, pending_offset)

    def focus_field(node, offset):
        hits = []
        for index, node_field in enumerate(node.fields):
            size = max(node_field.size, 1)
            if node_field.offset <= offset < node_field.offset + size:
                hits.append((size, index))
        if hits:
            select_table_row(state['field_rows'][min(hits)[1]])
        else:
            highlight(offset, 1)

    def on_table_select(_event=None):
        selection = table.selection()
        if not selection or selection[0] not in state['rows']:
            return
        kind, target = state['rows'][selection[0]]
        if kind == 'field':
            node_field = state['node'].fields[target]
            highlight(node_field.offset, max(node_field.size, 1))
        else:
            highlight(target.start, target.end - target.start)

    def on_table_open(_event=None):
        selection = table.selection()
        if not selection or selection[0] not in state['rows']:
            return
        kind, target = state['rows'][selection[0]]
        if kind == 'node':
            select_node(target)

    def select_node(target, field_offset=None):
        for item, node in state['items'].items():
            if node is target:
                state['pending'] = field_offset
                if tree.selection() == (item,):
                    on_tree_select()
                else:
                    tree.selection_set(item)
                tree.see(item)
                return

    def smallest_node_containing(offset):
        best = None
        for node in walk_nodes(state['wdt'].nodes):
            if not node.fields:
                continue
            if not node.start <= offset < node.end:
                continue
            if best is None or node.end - node.start <= best.end - best.start:
                best = node
        return best

    def goto_offset(_event=None):
        if not state['wdt']:
            return
        try:
            offset = int(goto_var.get().strip(), 16)
        except ValueError:
            messagebox.showerror('WDT Viewer', 'Enter a hex file offset, e.g. 700 or 0x710')
            return
        node = smallest_node_containing(offset)
        if not node:
            messagebox.showinfo('WDT Viewer', f'{format_hex(offset)} is outside every section')
            return
        select_node(node, offset)

    def hex_click_offset(event):
        index = hex_box.index(f'@{event.x},{event.y}')
        line, column = (int(part) for part in index.split('.'))
        if column < hex_bytes_column or column > hex_last_column:
            return None
        byte_column = column - hex_bytes_column
        if byte_column >= hex_second_half_column:
            byte_column -= 1
        return row_start_of(state['hex_base']) + (line - 1) * 16 + byte_column // 3

    def on_hex_click(event):
        if not state['wdt']:
            return
        offset = hex_click_offset(event)
        if offset is None:
            return
        hits = []
        for index, node_field in enumerate(state['node'].fields):
            if node_field.size and node_field.offset <= offset < node_field.offset + node_field.size:
                hits.append((node_field.size, index))
        if hits:
            item = state['field_rows'].get(min(hits)[1])
            if item:
                select_table_row(item)
            return
        for item, (kind, target) in state['rows'].items():
            if kind == 'node' and target.start <= offset < target.end:
                select_table_row(item)
                return

    def save_png():
        node = state['node']
        if not node or not node.image:
            return
        width, height, rgba, name = node.image
        path = filedialog.asksaveasfilename(title='Save image', defaultextension='.png',
                                            initialfile=name, filetypes=[('PNG', '*.png')])
        if path:
            Path(path).write_bytes(png_bytes(width, height, rgba))

    def focus_goto_entry(_event=None):
        goto_entry.focus_set()

    open_button.configure(command=open_file)
    reload_button.configure(command=reload_file)
    music_button.configure(command=pick_music)
    save_png_button.configure(command=save_png)
    goto_entry.bind('<Return>', goto_offset)
    tree.bind('<<TreeviewSelect>>', on_tree_select)
    table.bind('<<TreeviewSelect>>', on_table_select)
    table.bind('<Double-1>', on_table_open)
    table.bind('<Return>', on_table_open)
    hex_box.bind('<Button-1>', on_hex_click)
    root.bind('<Control-o>', open_file)
    root.bind('<Control-g>', focus_goto_entry)

    if music_path:
        set_music(music_path, quiet=True)
    else:
        set_music(find_music_csv(), quiet=True)
    if initial_path:
        load(initial_path)
    root.mainloop()


def load_cli_music(path):
    if not path:
        path = find_music_csv()
    if not path:
        print('(music.csv not found: BGM ids shown without names; use --music)')
        return {}
    return load_music(path)


def main(argv=None):
    if argv is None:
        args = list(sys.argv[1:])
    else:
        args = list(argv)
    music_path = None
    if '--music' in args:
        flag_index = args.index('--music')
        if flag_index + 1 >= len(args):
            print('--music needs a path to music.csv')
            return 2
        music_path = args[flag_index + 1]
        del args[flag_index:flag_index + 2]
    if args and args[0] in ('-h', '--help'):
        print(HELP_TEXT)
        return 0
    if args and args[0] == 'dump':
        if len(args) < 2:
            print('usage: wdt_tool.py dump <file.wdt>')
            return 2
        dump(args[1], load_cli_music(music_path))
        return 0
    if args and args[0] == 'verify':
        if len(args) > 1:
            folder = args[1]
        else:
            folder = DEFAULT_DIR
        return verify(folder, load_cli_music(music_path))
    run_gui(args[0] if args else None, music_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
