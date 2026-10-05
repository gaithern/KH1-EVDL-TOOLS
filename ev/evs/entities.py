"""Names for EVS scripts: the ARD entity table of a script's set, its .binl message texts,
hand-given names files, and the randomizer's gift locations and item names."""
import json
import os
import re
import struct
import sys
from functools import lru_cache
from pathlib import Path

FIRST_SET_SECTION = 5
SECTION_TABLE_OFFSET = 8
MAX_SUBSECTIONS = 10
MAX_ENTITIES = 2000
ENTITY_RECORD_SIZE = 0x78
ENTITY_NAME_OFFSET = 0x68
ENTITY_NAME_SIZE = 16
BINL_SET_BASE = 0x3E8
DEFAULT_LANGUAGE = 'UK'

SCRIPT_FILE_RE = re.compile(
    r'^(?:[A-Z]{2}_)?(?P<room>[a-z]{2}\d{2})(?:_ard(?P<evdl_set>[0-9a-f]+)\.evdl|(?P<ev_set_letter>[a-z])\.ev)$')
LANGUAGE_PREFIX_RE = re.compile(r'^[A-Z]{2}_')
WORLD_PREFIX_RE = re.compile(r'^(?:[A-Z]{2}_)?([a-z]{2})(?:\d{2}|\.wdt$)')
GIFT_RECORD_RE = re.compile(
    r'name\s*=\s*"([^"]+)",\s*world\s*=\s*(\d+),\s*gift\s*=\s*(0x[0-9A-Fa-f]+|\d+)')
ITEM_ROW_RE = re.compile(r'\[(\d+)\]\s*=\s*\{\s*name\s*=\s*"([^"]*)"[^\n]*?(?:--\s*vanilla:\s*([^\n]+))?\n')

NAMES_DIR = Path(__file__).resolve().parents[1] / 'data' / 'names'
RANDO_DIR = Path(os.environ.get('KH1_RANDO_DIR', Path(__file__).resolve().parents[3] / 'KH1-RANDOMIZER'))


def read_u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


@lru_cache(maxsize=64)
def ard_sets(path: Path) -> dict:
    return set_entities(path.read_bytes())


def set_entities(ard: bytes) -> dict:
    sets = {}
    section_count = read_u32(ard, 0)
    for section_index in range(FIRST_SET_SECTION, section_count):
        entity_table = find_entity_table(ard, section_index)
        if entity_table is not None:
            sets[section_index - FIRST_SET_SECTION] = read_entity_table(ard, entity_table)
    return sets


def find_entity_table(ard, section_index):
    section_start = read_u32(ard, SECTION_TABLE_OFFSET + section_index * 4)
    if not section_start or section_start + 8 > len(ard):
        return None
    subsection_count = read_u32(ard, section_start)
    if subsection_count < 1 or subsection_count > MAX_SUBSECTIONS:
        return None
    entity_table = section_start + read_u32(ard, section_start + 4)
    if entity_table + 4 > len(ard):
        return None
    entity_count = read_u32(ard, entity_table)
    if entity_count < 1 or entity_count > MAX_ENTITIES:
        return None
    return entity_table


def read_entity_table(ard, entity_table):
    entities = {}
    entity_count = read_u32(ard, entity_table)
    for index in range(entity_count):
        record = entity_table + 4 + index * ENTITY_RECORD_SIZE
        if record + ENTITY_RECORD_SIZE > len(ard):
            break
        name_start = record + ENTITY_NAME_OFFSET
        name_field = ard[name_start:name_start + ENTITY_NAME_SIZE]
        entities[read_u32(ard, record)] = name_field.split(b'\0')[0].decode('latin-1')
    return entities


def room_and_set(path: Path):
    match = SCRIPT_FILE_RE.match(path.name)
    if not match:
        return None
    room = match.group('room')
    if match.group('evdl_set') is not None:
        return room, int(match.group('evdl_set'), 16)
    return room, ord(match.group('ev_set_letter')) - ord('a')


def set_binl_name(language, room, set_number):
    return f'{language}_{room}_ard{BINL_SET_BASE + set_number:x}.binl'


def game_data_dir():
    from corpus import GAME_DATA
    return GAME_DATA


def find_ard(path: Path, room: str):
    for parent in path.parents:
        candidate = parent / f'{room}.ard'
        if candidate.is_file():
            return candidate
    candidate = game_data_dir() / f'{room}.ard'
    if candidate.is_file():
        return candidate
    return None


def entities_for(path: Path, kgr=None):
    if path.suffix.lower() == '.ard':
        if kgr is None or kgr.get('ard_section') is None:
            return {}
        return ard_sets(path).get(kgr['ard_section'] - FIRST_SET_SECTION, {})
    room_set = room_and_set(path)
    if not room_set:
        return {}
    room, set_number = room_set
    ard = find_ard(path, room)
    if not ard:
        return {}
    return ard_sets(ard).get(set_number, {})


def world_prefix(path: Path):
    match = WORLD_PREFIX_RE.match(path.name)
    if not match:
        return None
    return match.group(1)


def import_binl_tool():
    repo_root = str(Path(__file__).resolve().parents[2])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    import binl_tool
    return binl_tool


@lru_cache(maxsize=256)
def binl_texts(path: Path) -> dict:
    binl_tool = import_binl_tool()
    return dict(enumerate(binl_tool.BinlFile.load(str(path)).texts()))


def script_language(path: Path):
    if LANGUAGE_PREFIX_RE.match(path.name):
        return path.name[:2]
    return DEFAULT_LANGUAGE


def messages_for(path: Path, kgr=None):
    game_data = game_data_dir()
    path = Path(path)
    if path.suffix.lower() == '.ard':
        return None
    room_set = room_and_set(path)
    if not room_set:
        return None
    room, set_number = room_set
    name = set_binl_name(script_language(path), room, set_number)
    for candidate in (path.parent / name, game_data / 'remastered' / f'{room}.ard' / name):
        if candidate.is_file():
            return binl_texts(candidate)
    if path.suffix.lower() == '.evdl':
        import evdl_format
        return evdl_format.parse_evdl_string_table(path.read_bytes()) or None
    return None


def names_for(path: Path, kgr_index: int):
    script_name = LANGUAGE_PREFIX_RE.sub('', Path(path).name)
    names_file = NAMES_DIR / f'{script_name}.json'
    if not names_file.is_file():
        return None
    return json.loads(names_file.read_text(encoding='utf-8')).get(f'kgr {kgr_index}')


def rando_lua_file(name):
    return RANDO_DIR / 'mod' / 'scripts' / 'io_packages' / name


@lru_cache(maxsize=1)
def gift_locations() -> dict:
    locations_file = rando_lua_file('locations.lua')
    if not locations_file.is_file():
        return {}
    locations = {}
    for name, world, gift in GIFT_RECORD_RE.findall(locations_file.read_text(encoding='utf-8')):
        locations[(int(world), int(gift, 0))] = name
    return locations


def items_table_body(lua_source):
    body = lua_source[lua_source.index('local items = {'):]
    return body[:body.index('\n}')]


@lru_cache(maxsize=1)
def item_names() -> dict:
    items_file = rando_lua_file('items.lua')
    if not items_file.is_file():
        return {}
    names = {}
    for item_id, rando_name, vanilla_note in ITEM_ROW_RE.findall(items_table_body(items_file.read_text(encoding='utf-8'))):
        vanilla_name = vanilla_note.strip()
        if vanilla_name:
            names[int(item_id)] = vanilla_name
        else:
            names[int(item_id)] = rando_name
    return names
