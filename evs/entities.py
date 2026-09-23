"""ARD entity tables: which entity names a set's scripts can bind with Set_char_ID.

Set N of a room lives in ARD section 5 + N; its sub-section 0 is the entity table
(u32 count, then 0x78-byte records: +0x00 id, +0x68 16-byte name).
Script files map to sets by name: <lang>_<room>_ard<N hex>.evdl and <room><'a'+N>.ev.
"""
import os
import re
import struct
import sys
from functools import lru_cache
from pathlib import Path

ENTRY_SIZE = 0x78
FIRST_SET_SECTION = 5


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


@lru_cache(maxsize=64)
def ard_sets(path: Path) -> dict:
    return set_entities(path.read_bytes())


def set_entities(ard: bytes) -> dict:
    """{set number: {entity id: name}}"""
    out = {}
    nsec = u32(ard, 0)
    for si in range(FIRST_SET_SECTION, nsec):
        ss = u32(ard, 8 + si * 4)
        if not ss or ss + 8 > len(ard):
            continue
        nsub = u32(ard, ss)
        if not 1 <= nsub <= 10:
            continue
        sub0 = ss + u32(ard, ss + 4)
        if sub0 + 4 > len(ard):
            continue
        n = u32(ard, sub0)
        if not 0 < n <= 2000:
            continue
        ents = {}
        for i in range(n):
            o = sub0 + 4 + i * ENTRY_SIZE
            if o + ENTRY_SIZE > len(ard):
                break
            name = ard[o + 0x68:o + 0x78].split(b'\0')[0].decode('latin-1')
            ents[u32(ard, o)] = name
        out[si - FIRST_SET_SECTION] = ents
    return out


FILE_RE = re.compile(r'^(?:[A-Z]{2}_)?([a-z]{2}\d{2})(?:_ard([0-9a-f]+)\.evdl|([a-z])\.ev)$')


def room_and_set(path: Path):
    """('di01', 2) for UK_di01_ard2.evdl / di01c.ev; None if the name does not say."""
    m = FILE_RE.match(path.name)
    if not m:
        return None
    if m.group(2) is not None:
        return m.group(1), int(m.group(2), 16)
    return m.group(1), ord(m.group(3)) - ord('a')


def find_ard(path: Path, room: str):
    """The top-level <room>.ard next to the remastered folder tree."""
    for parent in path.parents:
        cand = parent / f'{room}.ard'
        if cand.is_file():
            return cand
    from corpus import GAME_DATA  # a built mod tree has no .ard; use the game's
    cand = GAME_DATA / f'{room}.ard'
    return cand if cand.is_file() else None


def entities_for(path: Path, kgr=None):
    """Entity table for the set a script file (or an ARD's embedded KGR) belongs to."""
    if path.suffix.lower() == '.ard':
        if kgr is None or kgr.get('ard_section') is None:
            return {}
        return ard_sets(path).get(kgr['ard_section'] - FIRST_SET_SECTION, {})
    rs = room_and_set(path)
    if not rs:
        return {}
    ard = find_ard(path, rs[0])
    if not ard:
        return {}
    return ard_sets(ard).get(rs[1], {})


def world_prefix(path: Path):
    """'tw' for UK_tw01_ard2.evdl, tw01c.ev, tw01.ard, tw.wdt; None otherwise."""
    m = re.match(r'^(?:[A-Z]{2}_)?([a-z]{2})(?:\d{2}|\.wdt$)', path.name)
    return m.group(1) if m else None


BINL_SET_BASE = 0x3E8  # set N's dialogue is <lang>_<room>_ard<3e8+N>.binl


@lru_cache(maxsize=256)
def binl_texts(path: Path) -> dict:
    sys_path = str(Path(__file__).resolve().parent.parent)
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    import binl_tool
    return dict(enumerate(binl_tool.BinlFile.load(str(path)).texts()))


def messages_for(path: Path, kgr=None):
    """{message index: text} the game shows for a script's Display_message: the set's .binl
    (next to the script, else the game's copy), else the string table inside the .evdl.
    Language follows the script's prefix; unprefixed .ev files are shown with UK text."""
    from corpus import GAME_DATA
    path = Path(path)
    if path.suffix.lower() == '.ard':
        return None  # which table the ARD's own (fallback) scripts read is unverified
    rs = room_and_set(path)
    if not rs:
        return None
    room, set_no = rs
    lang = path.name[:2] if re.match(r'^[A-Z]{2}_', path.name) else 'UK'
    name = f'{lang}_{room}_ard{BINL_SET_BASE + set_no:x}.binl'
    for cand in (path.parent / name, GAME_DATA / 'remastered' / f'{room}.ard' / name):
        if cand.is_file():
            return binl_texts(cand)
    if path.suffix.lower() == '.evdl':
        import evdl_tool
        return evdl_tool.parse_evdl_string_table(path.read_bytes()) or None
    return None


NAMES_DIR = Path(__file__).resolve().parent.parent / 'names'


def names_for(path: Path, kgr_index: int):
    """Hand-given names for one KGR of a script, from names/<script without language prefix>.json:
    {"kgr N": {"threads": {...}, "entries": {...}, "vars": {...}, "locals": {...}}}."""
    import json
    name = re.sub(r'^[A-Z]{2}_', '', Path(path).name)
    f = NAMES_DIR / f'{name}.json'
    if not f.is_file():
        return None
    return json.loads(f.read_text(encoding='utf-8')).get(f'kgr {kgr_index}')


RANDO_DIR = Path(os.environ.get('KH1_RANDO_DIR', Path(__file__).resolve().parents[2] / 'KH1-RANDOMIZER'))


@lru_cache(maxsize=1)
def gift_locations() -> dict:
    """{(world number, gift index): location name} from the randomizer's locations.lua."""
    f = RANDO_DIR / 'mod' / 'scripts' / 'io_packages' / 'locations.lua'
    if not f.is_file():
        return {}
    recs = re.findall(r'name\s*=\s*"([^"]+)",\s*world\s*=\s*(\d+),\s*gift\s*=\s*(0x[0-9A-Fa-f]+|\d+)',
                      f.read_text(encoding='utf-8'))
    return {(int(w), int(g, 0)): name for name, w, g in recs}


@lru_cache(maxsize=1)
def item_names() -> dict:
    """{item id: vanilla item name} from the randomizer's items.lua (its `-- vanilla:` note where
    the rando renamed the item)."""
    f = RANDO_DIR / 'mod' / 'scripts' / 'io_packages' / 'items.lua'
    if not f.is_file():
        return {}
    s = f.read_text(encoding='utf-8')
    body = s[s.index('local items = {'):]
    body = body[:body.index('\n}')]
    rows = re.findall(r'\[(\d+)\]\s*=\s*\{\s*name\s*=\s*"([^"]*)"[^\n]*?(?:--\s*vanilla:\s*([^\n]+))?\n', body)
    return {int(i): (v.strip() or n) for i, n, v in rows}
