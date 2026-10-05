#!/usr/bin/env python3
"""
wdt_viewer.py - read-only viewer for KH1 (HD 1.5 Remix) <world>.wdt files.

Every value is shown next to its file offset, its offset inside the table it
belongs to, and its raw bytes.  Layout (Steam exe, loader FUN_14017d580):

    0x00  u32  section count (6)
    0x10  6 x (u32 offset, u32 size)

    sec 0  area table + entrance table
             +0x0 area table offset (from sec 0)    +0x4 size  (0x40 per area)
             +0x8 entrance table offset             +0xC size  (0x40 per entrance)
           area[n]      +0x00 location group, +0x08 field BGM, +0x0C battle BGM,
                        +0x10 flags, +0x28/+0x2C Traverse Town alternate BGM, ...
           entrance[n]  +0x00 area, +0x10/+0x20/+0x30 spawn slots 0-2 (x, y, z, rot)
    sec 1  world EVDL script: u32 0, u32 0, u32 KGR count, u32 string table
           offset, KGR offset table.  KGR 0 runs on every room load, KGR 1+ are
           doors / world events (Change_area N = entrance N).
    sec 2  text colours: 4 entries x 4 RGBA (g_pWorldTextPalette)
    sec 3  empty
    sec 4  world title logo, TIM2 8bpp (e.g. "TRAVERSE TOWN" sign)
    sec 5  dialog window / speech bubble / button texture, 256x128 8bpp, CLUT
           at +0x8000, PS2 CSM1 order (FUN_140172ac0); tinted per world

BGM ids are resolved to track names from KH1-DOCUMENTATION's
data/sound/music.csv (found next to this repo, or via --music / the
KH1_MUSIC_CSV environment variable).

Usage:
    python wdt_viewer.py [--music music.csv] [file.wdt]       open the GUI
    python wdt_viewer.py [--music ..] dump <file.wdt>         print every field
    python wdt_viewer.py [--music ..] verify [dir]            parse every .wdt in
                                             a folder, check the layout invariants
                                             and that every BGM id is a known track
"""

import base64
import os
import struct
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_DIR = r'C:\OpenKH\OpenKHEGS\data\kh1'

SECTION_NAMES = [
    'Areas & entrances',
    'World script (EVDL)',
    'Text colours',
    'Unused',
    'World logo (TIM2)',
    'Dialog window texture',
]

MUSIC_CSV_REL = Path('data') / 'sound' / 'music.csv'
TW_WORLD_NUMBER = 3     # FUN_14017d580 switches tw to +0x28/+0x2C once the story byte is >= 0x2B

SYSCALL_CHANGE_AREA = 60
SYSCALL_MAP_CHANGE_REWRITE_SET = 612
OP_PUSH = 0x09
OP_SYSCALL = 0x18


# ---------------------------------------------------------------------------
# Music table (KH1-DOCUMENTATION/data/sound/music.csv)
# ---------------------------------------------------------------------------

def find_music_csv():
    """KH1_MUSIC_CSV, else KH1-DOCUMENTATION next to this repo (or the cwd)."""
    env = os.environ.get('KH1_MUSIC_CSV')
    if env and Path(env).is_file():
        return Path(env)
    here = Path(__file__).resolve().parent
    for base in (here.parent, Path.cwd(), Path.cwd().parent):
        cand = base / 'KH1-DOCUMENTATION' / MUSIC_CSV_REL
        if cand.is_file():
            return cand
    return None


def load_music(path):
    """{music id: row dict} from music.csv (columns: Music ID, Name, Found As, Duration (s), Loops, ...)."""
    import csv
    out = {}
    with open(path, encoding='utf-8-sig', newline='') as fh:
        for row in csv.DictReader(fh):
            try:
                out[int(row['Music ID'])] = row
            except (KeyError, TypeError, ValueError):
                continue
    return out


def music_label(music, v):
    """Short display name for a BGM id: 'Traverse Town', 'none', or '' when there is no table."""
    if v == 0:
        return 'none'
    if not music:
        return ''
    row = music.get(v)
    if row is None:
        return 'NOT IN music.csv'
    name = row.get('Name') or '?'
    return 'empty stub (N/A)' if name == 'N/A' else name


def music_detail(music, v):
    """Longer note: file name, length and loop info."""
    row = music.get(v) if music else None
    if not row:
        return ''
    bits = [f'music{v:03d}.win32.scd']
    if row.get('Duration (s)'):
        bits.append(f'{float(row["Duration (s)"]):.1f} s')
    if row.get('Loops') == 'Yes' and row.get('Loop Start (s)'):
        bits.append(f'loops from {float(row["Loop Start (s)"]):.1f} s')
    elif row.get('Loops') == 'No':
        bits.append('no loop')
    if row.get('Codec', '').startswith('None'):
        bits.append(row['Codec'])
    return ', '.join(bits)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@dataclass
class Field:
    off: int            # absolute file offset
    size: int
    name: str
    type: str
    value: str
    note: str = ''
    rel: int = None     # offset inside the owning table entry / section
    color: tuple = None  # (r, g, b, a) for colour rows


@dataclass
class Node:
    title: str
    start: int
    end: int
    fields: list = field(default_factory=list)
    children: list = field(default_factory=list)
    summary: tuple = None   # (columns, rows) - rows are (child index, values)
    image: tuple = None     # (width, height, rgba bytes, label)
    info: str = ''


def _u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def _f32(d, o):
    return struct.unpack_from('<f', d, o)[0]


def _hex(v):
    return f'0x{v:X}'


def _num(v):
    return f'0x{v:X} ({v})' if v > 9 else str(v)


def _compact_rooms(rooms):
    """['tw01','tw02','tw03','tw05'] -> 'tw01-03, tw05'."""
    nums = sorted({(r[:2], int(r[2:])) for r in rooms})
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1][0] == nums[i][0] and nums[j + 1][1] == nums[j][1] + 1:
            j += 1
        w, a = nums[i]
        out.append(f'{w}{a:02d}' if i == j else f'{w}{a:02d}-{nums[j][1]:02d}')
        i = j + 1
    return ', '.join(out)


def _fmt_f(v):
    return f'{v:.3f}'.rstrip('0').rstrip('.') if v == v else 'nan'


class Wdt:
    """Parsed .wdt.  `nodes` is the tree the GUI shows."""

    def __init__(self, data: bytes, name: str = 'xx.wdt', music: dict = None):
        self.data = data
        self.name = name
        self.music = music or {}
        self.world = Path(name).stem[:2].lower()
        self.warnings = []
        self.sections = []      # (offset, size)
        self.areas = []         # dict per area
        self.entrances = []     # dict per entrance
        self.kgrs = []          # dict per KGR
        self.nodes = []
        self._parse()

    # -- helpers -----------------------------------------------------------
    def room(self, area):
        return f'{self.world}{area + 1:02d}'

    def in_bounds(self, off, size):
        return 0 <= off and off + size <= len(self.data)

    def u32f(self, off, name, note='', rel=None, fmt=_num):
        v = _u32(self.data, off)
        return Field(off, 4, name, 'u32', fmt(v), note, rel)

    # -- parsing -----------------------------------------------------------
    def _parse(self):
        d = self.data
        if len(d) < 0x40:
            raise ValueError(f'{self.name}: {len(d)} bytes is too small for a WDT header')
        count = _u32(d, 0)
        if not 1 <= count <= 16:
            raise ValueError(f'{self.name}: section count {count} does not look like a WDT')

        hdr = Node('File header', 0, 0x10 + count * 8)
        hdr.fields.append(self.u32f(0, 'Section count', rel=0))
        hdr.fields.append(Field(4, 12, 'Unused', 'bytes', '', 'always zero', 4))
        for i in range(count):
            o = 0x10 + i * 8
            off, size = struct.unpack_from('<2I', d, o)
            self.sections.append((off, size))
            nm = SECTION_NAMES[i] if i < len(SECTION_NAMES) else f'section {i}'
            hdr.fields.append(self.u32f(o, f'Sec {i} offset', nm, o, _hex))
            end_note = f'ends at {_hex(off + size)}'
            if not self.in_bounds(off, size):
                end_note += '  (OUT OF FILE)'
                self.warnings.append(f'section {i} runs past the end of the file')
            hdr.fields.append(self.u32f(o + 4, f'Sec {i} size', end_note, o + 4, _hex))
        self.nodes.append(hdr)

        builders = [self._sec0, self._sec1, self._sec2, None, self._sec4, self._sec5]
        for i, (off, size) in enumerate(self.sections):
            nm = SECTION_NAMES[i] if i < len(SECTION_NAMES) else 'unknown'
            node = Node(f'Section {i}: {nm}', off, off + size)
            node.info = f'offset {_hex(off)}, size {_hex(size)}'
            b = builders[i] if i < len(builders) else None
            if size and self.in_bounds(off, size):
                try:
                    if b:
                        b(node, off, size)
                    else:
                        node.fields.append(Field(off, size, 'Raw data', 'bytes', f'{size} bytes'))
                except Exception as e:  # keep the viewer usable on odd files
                    self.warnings.append(f'section {i}: {e}')
                    node.fields.append(Field(off, size, 'Raw data (parse failed)', 'bytes', str(e)))
            elif not size:
                node.info += '  (empty)'
            self.nodes.append(node)

        self._link_doors()

    # Section 0 -------------------------------------------------------------
    AREA_FIELDS = [
        (0x00, 'Location group', 'rooms of one location share it (-> DAT_14233fe88)'),
        (0x04, 'Unknown mask', 'not read by the loader'),
        (0x08, 'Field BGM', 'amusic/musicNNN.dat'),
        (0x0C, 'Battle BGM', 'amusic/musicNNN.dat'),
        (0x10, 'Flags', 'bit1 tint; bit0/2 -> DAT_14233fe08; bit3, bit6 -> engine flags'),
        (0x14, 'Unknown 0x14', '-> DAT_14232d514'),
        (0x18, 'Volume-style 0x18', 'sqrt(v*0x3FFF)*2 -> DAT_1422c9d94'),
        (0x1C, 'Volume-style 0x1C', 'sqrt(v*0x3FFF)*2 -> DAT_1421ab00c'),
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

    def bgm(self, v):
        """'0x68 Traverse Town' for summary columns."""
        label = music_label(self.music, v)
        return f'{v:X} {label}' if label else _hex(v)

    def _sec0(self, node, s0, size):
        d = self.data
        a, b, c, e = struct.unpack_from('<4I', d, s0)
        node.fields += [
            self.u32f(s0, 'Area table offset', f'file {_hex(s0 + a)}', 0, _hex),
            self.u32f(s0 + 4, 'Area table size', f'{b // 0x40} areas', 4, _hex),
            self.u32f(s0 + 8, 'Entrance table offset', f'file {_hex(s0 + c)}', 8, _hex),
            self.u32f(s0 + 12, 'Entrance table size', f'{e // 0x40} entrances', 12, _hex),
        ]

        # areas
        at = Node(f'Area table ({b // 0x40})', s0 + a, s0 + a + b)
        cols = ['Area', 'Room', 'Offset', 'Group', 'Field BGM', 'Battle BGM', 'Flags',
                '+14', '+18', '+1C', '+20', '+24', 'Alt BGM', 'Entrances']
        rows = []
        for n in range(b // 0x40):
            o = s0 + a + n * 0x40
            if not self.in_bounds(o, 0x40):
                self.warnings.append(f'area {n} past end of file')
                break
            vals = struct.unpack_from('<16I', d, o)
            self.areas.append({'index': n, 'off': o, 'vals': vals})
            an = Node(f'Area {n:02d}  {self.room(n)}', o, o + 0x40)
            for rel, nm, note in self.AREA_FIELDS:
                f = self.u32f(o + rel, nm, note, rel, _hex if rel == 0x10 else _num)
                if rel in self.BGM_OFFSETS:
                    v = vals[rel // 4]
                    label = music_label(self.music, v)
                    if label:
                        f.value = f'{f.value}  {label}'
                    detail = music_detail(self.music, v)
                    if detail:
                        f.note = f'{detail}; {note}' if rel >= 0x28 else detail
                    if label == 'NOT IN music.csv':
                        self.warnings.append(f'{self.room(n)} +{rel:02X}: BGM {v} is not in music.csv')
                an.fields.append(f)
            at.children.append(an)
            alt = (f'{self.bgm(vals[10])} / {self.bgm(vals[11])}' if vals[10] or vals[11] else '')
            rows.append((an, [n, self.room(n), _hex(o), vals[0], self.bgm(vals[2]), self.bgm(vals[3]),
                             _hex(vals[4]), _hex(vals[5]), _hex(vals[6]), _hex(vals[7]),
                             _hex(vals[8]), _hex(vals[9]), alt, '']))
        at.summary = (cols, rows)
        node.children.append(at)
        node.children.append(self._music_node(at))

        # entrances
        et = Node(f'Entrance table ({e // 0x40})', s0 + c, s0 + c + e)
        cols = ['Entrance', 'Offset', 'Area', 'Room', 'Sora x, y, z, rot',
                'Slot 1', 'Slot 2', 'Used by']
        rows = []
        for n in range(e // 0x40):
            o = s0 + c + n * 0x40
            if not self.in_bounds(o, 0x40):
                self.warnings.append(f'entrance {n} past end of file')
                break
            area = _u32(d, o)
            slots = [struct.unpack_from('<4f', d, o + 0x10 * (k + 1)) for k in range(3)]
            self.entrances.append({'index': n, 'off': o, 'area': area, 'slots': slots,
                                   'pad': struct.unpack_from('<3I', d, o + 4)})
            en = Node(f'Entrance {n:02d} ({_hex(n)})  -> {self.room(area)}', o, o + 0x40)
            en.fields.append(self.u32f(o, 'Area', f'loads {self.room(area)}.ard', 0))
            for k in range(3):
                en.fields.append(self.u32f(o + 4 + k * 4, f'Unused +{4 + k * 4:X}', '', 4 + k * 4))
            for k, sn in enumerate(self.SLOT_NAMES):
                base = 0x10 * (k + 1)
                for j, axis in enumerate(('x', 'y', 'z', 'rot')):
                    v = _f32(d, o + base + j * 4)
                    note = 'radians' if axis == 'rot' else ''
                    en.fields.append(Field(o + base + j * 4, 4, f'{sn} {axis}', 'f32', _fmt_f(v),
                                           note, base + j * 4))
            et.children.append(en)

            def fs(s):
                return ', '.join(_fmt_f(round(v, 2) if i == 3 else round(v)) for i, v in enumerate(s))
            rows.append((en, [f'{n} ({_hex(n)})', _hex(o), area, self.room(area),
                             fs(slots[0]), fs(slots[1]), fs(slots[2]), '']))
        et.summary = (cols, rows)
        node.children.append(et)

        end = s0 + max(a + b, c + e)
        if end < s0 + size:
            node.fields.append(Field(end, s0 + size - end, 'Trailing bytes', 'bytes', ''))

    def _music_node(self, area_table):
        """One row per BGM id this world uses, with the rooms that use it and how."""
        uses = {}
        for a, an in zip(self.areas, area_table.children):
            for rel, kind in self.BGM_OFFSETS.items():
                v = a['vals'][rel // 4]
                if v:
                    uses.setdefault(v, {}).setdefault(kind, []).append(self.room(a['index']))
        mn = Node(f'Music used ({len(uses)} tracks)', area_table.start, area_table.end)
        mn.info = ('BGM ids from the area table, named from KH1-DOCUMENTATION/data/sound/music.csv'
                   if self.music else 'music.csv not loaded: ids only (see --music / KH1_MUSIC_CSV)')
        cols = ['BGM', 'Track', 'File / length', 'Field in', 'Battle in', 'Alt (story >= 0x2B) in']

        def rooms(lst):
            return _compact_rooms(lst or [])
        rows = []
        for v in sorted(uses):
            u = uses[v]
            alt = sorted(set(u.get('alt field', []) + u.get('alt battle', [])))
            first = next(an for a, an in zip(self.areas, area_table.children)
                         if v in (a['vals'][2], a['vals'][3], a['vals'][10], a['vals'][11]))
            rows.append((first, [f'{v} ({_hex(v)})', music_label(self.music, v) or '?',
                                 music_detail(self.music, v), rooms(u.get('field')),
                                 rooms(u.get('battle')), rooms(alt)]))
        mn.summary = (cols, rows)
        return mn

    # Section 1 -------------------------------------------------------------
    def _sec1(self, node, s1, size):
        d = self.data
        z0, z1, kcount, stroff = struct.unpack_from('<4I', d, s1)
        node.fields += [
            self.u32f(s1, 'Header word 0', 'always 0', 0),
            self.u32f(s1 + 4, 'Header word 1', 'always 0', 4),
            self.u32f(s1 + 8, 'KGR count', '', 8),
            self.u32f(s1 + 12, 'String table offset', f'file {_hex(s1 + stroff)}', 12, _hex),
        ]
        offs = []
        for i in range(kcount):
            o = s1 + 16 + i * 4
            if not self.in_bounds(o, 4):
                break
            v = _u32(d, o)
            offs.append(v)
            node.fields.append(self.u32f(o, f'KGR {i} offset', f'file {_hex(s1 + v)}', 16 + i * 4, _hex))

        # string table
        first_kgr = s1 + min(offs) if offs else s1 + size
        st_start = s1 + stroff
        if st_start < first_kgr:
            st = Node('String table', st_start, first_kgr)
            n = _u32(d, st_start) if self.in_bounds(st_start, 4) else 0
            st.fields.append(self.u32f(st_start, 'String count', '', 0))
            for i, txt in sorted(self._strings(s1, size).items()):
                st.fields.append(Field(st_start, 0, f'String {i}', 'khscii', txt))
            if first_kgr - st_start > 4:
                st.fields.append(Field(st_start + 4, first_kgr - st_start - 4, 'String data',
                                       'bytes', f'{first_kgr - st_start - 4} bytes', f'{n} strings'))
            node.children.append(st)

        ends = sorted(offs) + [size]
        cols = ['KGR', 'Offset', 'Size', 'Scripts', 'Change_area targets']
        rows = []
        for i, rel in enumerate(offs):
            ko = s1 + rel
            nxt = s1 + min([x for x in ends if x > rel] or [size])
            kn = Node(f'KGR {i}', ko, nxt)
            info = {'index': i, 'off': ko, 'end': nxt, 'targets': []}
            if self.in_bounds(ko, 13) and d[ko:ko + 4] == b'KGR\x00':
                kn.fields += [
                    Field(ko, 4, 'Magic', 'char[4]', "'KGR\\0'", '', 0),
                    self.u32f(ko + 4, 'Unknown 0', '', 4),
                    self.u32f(ko + 8, 'Unknown 1', '', 8),
                    Field(ko + 12, 1, 'Script count', 'u8', str(d[ko + 12]), '', 12),
                ]
                info['targets'] = self._door_targets(ko + 13, nxt)
                stream_len = nxt - (ko + 13)
                kn.fields.append(Field(ko + 13, stream_len, 'Instruction stream', 'bytes',
                                       f'{stream_len} bytes',
                                       'disassemble with: evdl_tool.py disasm', 13))
                for at, ent, sc, world in info['targets']:
                    call = 'Change_area' if sc == SYSCALL_CHANGE_AREA else 'Start_map_change_rewrite_set'
                    where = f' of world {world}' if world is not None else ''
                    kn.fields.append(Field(at, 4, 'push (entrance)', 'instr', f'{ent} ({_hex(ent)})',
                                           f'{call} -> entrance {ent}{where}', at - ko))
            else:
                self.warnings.append(f'KGR {i} at {_hex(ko)} has no KGR magic')
                kn.fields.append(Field(ko, nxt - ko, 'Raw data (no KGR magic)', 'bytes', ''))
            if i == 0:
                kn.info = 'runs once per room load (Get_area_number switch)'
            else:
                kn.info = f'Trigger_event {100 + i} / polygon event id {100 + i}'
            self.kgrs.append(info)
            node.children.append(kn)
            rows.append((kn, [i, _hex(ko), _hex(nxt - ko), d[ko + 12] if self.in_bounds(ko, 13) else '', '']))
        overview = Node(f'Door targets ({len(offs)} KGRs)', s1 + min(offs) if offs else s1, s1 + size)
        overview.info = 'every `push N; Change_area` per KGR; double-click a row to open the KGR'
        overview.summary = (cols, rows)
        node.children.insert(0, overview)

    def _strings(self, s1, size):
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from evdl_tool import parse_evdl_string_table
            return parse_evdl_string_table(self.data[s1:s1 + size])
        except Exception:
            return {}

    def _door_targets(self, start, end):
        """(push offset, entrance, syscall, world) for every `push N; Change_area` and
        `...; push N; Start_map_change_rewrite_set`.  world is None when the script passes
        CURRENT_WORLD (read_byte [0xD5C]) or a computed value, else the pushed world number."""
        d = self.data
        words = [(p, _u32(d, p)) for p in range(start, end - 3, 4)]
        out = []
        for i, (p, w) in enumerate(words):
            op, arg = w >> 24, w & 0xFFFFFF
            if op != OP_SYSCALL or arg not in (SYSCALL_CHANGE_AREA, SYSCALL_MAP_CHANGE_REWRITE_SET):
                continue
            if i == 0 or words[i - 1][1] >> 24 != OP_PUSH:
                continue
            world = None
            if arg == SYSCALL_MAP_CHANGE_REWRITE_SET and i >= 4 and words[i - 4][1] >> 24 == OP_PUSH:
                world = words[i - 4][1] & 0xFFFFFF
            out.append((words[i - 1][0], words[i - 1][1] & 0xFFFFFF, arg, world))
        return out

    def _link_doors(self):
        used = {}
        for k in self.kgrs:
            for _, ent, _, world in k['targets']:
                if world is None:
                    used.setdefault(ent, []).append(k['index'])
        by_area = {}
        for e in self.entrances:
            by_area.setdefault(e['area'], []).append(e['index'])
        for node in self._walk(self.nodes):
            if not node.summary:
                continue
            cols, rows = node.summary
            if cols[0] == 'Entrance':
                for idx, (_, vals) in enumerate(rows):
                    ks = sorted(set(used.get(self.entrances[idx]['index'], [])))
                    vals[-1] = ', '.join(f'KGR {k}' for k in ks)
            elif cols[0] == 'Area':
                for idx, (_, vals) in enumerate(rows):
                    vals[-1] = ', '.join(str(x) for x in by_area.get(idx, [])) or '(none)'
            elif cols[0] == 'KGR':
                for _, vals in rows:
                    k = self.kgrs[vals[0]]
                    vals[-1] = ', '.join(self._target_str(ent, world)
                                         for _, ent, _, world in k['targets'])
        for e in self.entrances:
            e['used_by'] = sorted(set(used.get(e['index'], [])))

    def _target_str(self, ent, world):
        if world is not None:
            return f'{ent} (world {world})'
        if ent < len(self.entrances):
            return f'{ent} ({self.room(self.entrances[ent]["area"])})'
        return f'{ent} (?)'

    @staticmethod
    def _walk(nodes):
        for n in nodes:
            yield n
            yield from Wdt._walk(n.children)

    # Section 2 -------------------------------------------------------------
    def _sec2(self, node, s2, size):
        d = self.data
        for e in range(size // 16):
            for c in range(4):
                o = s2 + e * 16 + c * 4
                r, g, b, a = d[o:o + 4]
                node.fields.append(Field(o, 4, f'Colour set {e}, colour {c}', 'RGBA',
                                         f'#{r:02X}{g:02X}{b:02X}  a={_hex(a)}',
                                         'transparent' if a == 0 else '', o - s2, (r, g, b, a)))
        node.info = 'fnc_copy_world_text_palette_entry copies one 16-byte set (4 colours) per text style'

    # Section 4 -------------------------------------------------------------
    def _sec4(self, node, s4, size):
        d = self.data
        if d[s4:s4 + 4] != b'TIM2':
            node.fields.append(Field(s4, size, 'Raw data (no TIM2 magic)', 'bytes', ''))
            return
        node.fields += [
            Field(s4, 4, 'Magic', 'char[4]', "'TIM2'", '', 0),
            Field(s4 + 4, 1, 'Version', 'u8', str(d[s4 + 4]), '', 4),
            Field(s4 + 5, 1, 'Alignment', 'u8', str(d[s4 + 5]), '0 = 16 bytes', 5),
            Field(s4 + 6, 2, 'Picture count', 'u16', str(struct.unpack_from('<H', d, s4 + 6)[0]), '', 6),
            Field(s4 + 8, 8, 'Reserved', 'bytes', '', '', 8),
        ]
        p = s4 + 0x10
        (total, clut_size, img_size, hdr_size, clut_colors, pfmt, mips, clut_type, img_type,
         w, h) = struct.unpack_from('<3I2H4B2H', d, p)
        specs = [
            (0x00, 4, 'Total size', 'u32', _hex(total)),
            (0x04, 4, 'CLUT size', 'u32', _hex(clut_size)),
            (0x08, 4, 'Image size', 'u32', _hex(img_size)),
            (0x0C, 2, 'Header size', 'u16', _hex(hdr_size)),
            (0x0E, 2, 'CLUT colours', 'u16', str(clut_colors)),
            (0x10, 1, 'Picture format', 'u8', str(pfmt)),
            (0x11, 1, 'Mipmaps', 'u8', str(mips)),
            (0x12, 1, 'CLUT type', 'u8', _hex(clut_type)),
            (0x13, 1, 'Image type', 'u8', f'{img_type} ({ {4: "4bpp", 5: "8bpp"}.get(img_type, "?") })'),
            (0x14, 2, 'Width', 'u16', str(w)),
            (0x16, 2, 'Height', 'u16', str(h)),
            (0x18, 8, 'GS TEX0', 'u64', _hex(struct.unpack_from('<Q', d, p + 0x18)[0])),
            (0x20, 8, 'GS TEX1', 'u64', _hex(struct.unpack_from('<Q', d, p + 0x20)[0])),
            (0x28, 4, 'GS regs', 'u32', _hex(_u32(d, p + 0x28))),
            (0x2C, 4, 'GS TEXCLUT', 'u32', _hex(_u32(d, p + 0x2C))),
        ]
        for rel, sz, nm, ty, val in specs:
            node.fields.append(Field(p + rel, sz, nm, ty, val, '', 0x10 + rel))
        img = p + hdr_size
        clut = img + img_size
        node.fields.append(Field(img, img_size, 'Pixels', 'bytes', f'{w}x{h}', '', img - s4))
        node.fields.append(Field(clut, clut_size, 'CLUT', 'bytes', f'{clut_colors} colours', '', clut - s4))
        if img_type == 5 and clut_colors == 256 and self.in_bounds(clut, 0x400):
            rgba = indexed_to_rgba(d[img:img + w * h], d[clut:clut + 0x400],
                                   swizzled=not (clut_type & 0x80))
            node.image = (w, h, rgba, f'{self.world}_tim2.png')
        node.info = 'world title logo; remastered HD copy: remastered/<world>.wdt/-<pixels offset>.dds'

    # Section 5 -------------------------------------------------------------
    def _sec5(self, node, s5, size):
        w, h = 256, 128
        if size < w * h + 0x400:
            node.fields.append(Field(s5, size, 'Raw data', 'bytes', f'{size} bytes'))
            return
        node.fields.append(Field(s5, w * h, 'Pixels', 'bytes', f'{w}x{h} 8bpp', 'FUN_140172ac0(ptr, 0x100, 0x80)', 0))
        node.fields.append(Field(s5 + w * h, 0x400, 'CLUT', 'bytes', '256 colours RGBA', '', w * h))
        if size > w * h + 0x400:
            node.fields.append(Field(s5 + w * h + 0x400, size - w * h - 0x400, 'Trailing bytes', 'bytes', ''))
        d = self.data
        node.image = (w, h, indexed_to_rgba(d[s5:s5 + w * h], d[s5 + w * h:s5 + w * h + 0x400], True),
                      f'{self.world}_texture.png')
        node.info = ('dialog window / speech bubble / button skin; '
                     'remastered HD copy: remastered/<world>.wdt/-<offset>.png (512x256)')


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

def _csm1(i):
    """PS2 CSM1 CLUT order: bits 3 and 4 of the index are swapped."""
    return (i & 0xE7) | ((i & 0x10) >> 1) | ((i & 0x08) << 1)


def indexed_to_rgba(pixels: bytes, clut: bytes, swizzled: bool) -> bytes:
    pal = []
    for i in range(256):
        j = _csm1(i) if swizzled else i
        r, g, b, a = clut[j * 4:j * 4 + 4]
        pal.append(bytes((r, g, b, min(255, a * 2))))
    return b''.join(pal[p] for p in pixels)


def png_bytes(w: int, h: int, rgba: bytes) -> bytes:
    def chunk(tag, body):
        return (struct.pack('>I', len(body)) + tag + body +
                struct.pack('>I', zlib.crc32(tag + body) & 0xFFFFFFFF))
    raw = b''.join(b'\x00' + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def checker_composite(w, h, rgba, scale):
    """Flatten RGBA onto a checkerboard and scale up, for display (tk has no alpha blending)."""
    out = bytearray()
    for y in range(h * scale):
        sy = y // scale
        for x in range(w * scale):
            sx = x // scale
            i = (sy * w + sx) * 4
            r, g, b, a = rgba[i:i + 4]
            bg = 0xCC if ((x // 8) + (y // 8)) & 1 else 0x99
            out += bytes((
                (r * a + bg * (255 - a)) // 255,
                (g * a + bg * (255 - a)) // 255,
                (b * a + bg * (255 - a)) // 255,
                255))
    return png_bytes(w * scale, h * scale, bytes(out))


# ---------------------------------------------------------------------------
# Text dump / verify
# ---------------------------------------------------------------------------

def raw_hex(data, f, limit=16):
    n = min(f.size, limit)
    s = data[f.off:f.off + n].hex(' ').upper()
    return s + (' ..' if f.size > limit else '')


def dump(path, music=None):
    w = Wdt(Path(path).read_bytes(), Path(path).name, music)

    def walk(nodes, depth):
        for n in nodes:
            print(f'{"  " * depth}== {n.title}  [{_hex(n.start)}..{_hex(n.end)})  {n.info}')
            for f in n.fields:
                rel = f'+{f.rel:02X}' if f.rel is not None else '   '
                print(f'{"  " * depth}   {f.off:06X} {rel:>5}  {raw_hex(w.data, f):<24} '
                      f'{f.type:<7} {f.name:<24} {f.value}  {f.note}')
            if n.summary and not n.fields:
                cols, rows = n.summary
                print(f'{"  " * depth}   ' + ' | '.join(cols))
                for _, vals in rows:
                    print(f'{"  " * depth}   ' + ' | '.join(str(x) for x in vals))
            walk(n.children, depth + 1)
    walk(w.nodes, 0)
    for m in w.warnings:
        print('WARNING:', m)


def verify(folder=DEFAULT_DIR, music=None):
    files = sorted(Path(folder).glob('*.wdt'))
    if not files:
        print(f'no .wdt files in {folder}')
        return 1
    bad = 0
    for p in files:
        w = Wdt(p.read_bytes(), p.name, music)
        problems = list(w.warnings)
        # sections are contiguous and end at EOF
        pos = w.sections[0][0]
        for i, (off, size) in enumerate(w.sections):
            if off != pos:
                problems.append(f'section {i} starts at {_hex(off)}, expected {_hex(pos)}')
            pos = off + size
        if pos != len(w.data):
            problems.append(f'sections end at {_hex(pos)}, file is {_hex(len(w.data))}')
        # every entrance points at a real area
        for e in w.entrances:
            if e['area'] >= len(w.areas):
                problems.append(f'entrance {e["index"]} -> area {e["area"]} (only {len(w.areas)} areas)')
            if any(e['pad']):
                problems.append(f'entrance {e["index"]} has non-zero padding {e["pad"]}')
        for k in w.kgrs:
            for _, ent, _, world in k['targets']:
                if world is None and ent >= len(w.entrances):
                    problems.append(f'KGR {k["index"]} -> entrance {ent} (only {len(w.entrances)})')
        doors = sum(len(k['targets']) for k in w.kgrs)
        status = 'OK ' if not problems else 'BAD'
        print(f'{status} {p.name}: {len(w.areas)} areas, {len(w.entrances)} entrances, '
              f'{len(w.kgrs)} KGRs, {doors} Change_area pushes, '
              f'images: {sum(1 for n in w.nodes if n.image)}')
        for m in problems:
            print('     ', m)
        bad += bool(problems)
    return 1 if bad else 0


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

def _run_gui(initial: str = None, music_path=None):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    WDT_FT = [('World data', '*.wdt'), ('All files', '*.*')]
    COL_WIDTHS = {'Entrance': 80, 'Offset': 70, 'Area': 50, 'Room': 55, 'Sora x, y, z, rot': 190,
                  'Slot 1': 190, 'Slot 2': 190, 'Used by': 160, 'Group': 55, 'Field BGM': 75,
                  'Battle BGM': 80, 'Flags': 50, '+14': 50, '+18': 50, '+1C': 55, '+20': 65,
                  '+24': 65, 'Alt BGM': 70, 'Entrances': 200, 'KGR': 50, 'Size': 70, 'Scripts': 60,
                  'Change_area targets': 420, 'Field BGM': 190, 'Battle BGM': 190, 'Alt BGM': 300,
                  'BGM': 80, 'Track': 220, 'File / length': 290, 'Field in': 170, 'Battle in': 170,
                  'Alt (story >= 0x2B) in': 170}
    HEX_LIMIT = 0x10000
    state = {'wdt': None, 'path': None, 'node': None, 'items': {}, 'rows': {}, 'img': None,
             'hex_base': 0, 'hex_len': 0, 'field_rows': {}, 'music': {}, 'music_path': None}

    root = tk.Tk()
    root.title('WDT Viewer')
    root.geometry('1400x860')

    # --- top bar -----------------------------------------------------------
    top = tk.Frame(root)
    top.pack(fill='x', padx=6, pady=4)
    tk.Button(top, text='Open...', command=lambda: open_file()).pack(side='left')
    tk.Button(top, text='Reload', command=lambda: state['path'] and load(state['path'])).pack(side='left', padx=4)
    tk.Button(top, text='Music table...', command=lambda: pick_music()).pack(side='left')
    path_var = tk.StringVar()
    tk.Entry(top, textvariable=path_var, state='readonly', width=70).pack(side='left', fill='x', expand=True, padx=4)
    tk.Label(top, text='Go to offset:').pack(side='left')
    goto_var = tk.StringVar()
    goto_ent = tk.Entry(top, textvariable=goto_var, width=10)
    goto_ent.pack(side='left', padx=4)
    goto_ent.bind('<Return>', lambda e: goto_offset())
    info_var = tk.StringVar(value='no file loaded')
    tk.Label(root, textvariable=info_var, anchor='w', fg='#444').pack(fill='x', padx=8)

    # --- panes -------------------------------------------------------------
    mid = tk.PanedWindow(root, orient='horizontal', sashrelief='raised')
    mid.pack(fill='both', expand=True, padx=6, pady=2)

    left = tk.Frame(mid)
    mid.add(left, minsize=260, width=320)
    tree = ttk.Treeview(left, columns=('range',), selectmode='browse')
    tree.heading('#0', text='Structure')
    tree.heading('range', text='Range')
    tree.column('#0', width=210)
    tree.column('range', width=110, anchor='w')
    tsb = ttk.Scrollbar(left, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=tsb.set)
    tree.pack(side='left', fill='both', expand=True)
    tsb.pack(side='right', fill='y')

    right = tk.PanedWindow(mid, orient='vertical', sashrelief='raised')
    mid.add(right, minsize=500)

    upper = tk.Frame(right)
    right.add(upper, minsize=200, height=470)
    title_var = tk.StringVar()
    tk.Label(upper, textvariable=title_var, anchor='w', font=('Segoe UI', 10, 'bold')).pack(fill='x')
    node_info_var = tk.StringVar()
    tk.Label(upper, textvariable=node_info_var, anchor='w', fg='#555').pack(fill='x')

    imgbar = tk.Frame(upper)
    img_label = tk.Label(imgbar, bd=1, relief='sunken')
    img_label.pack(side='left', padx=2, pady=2)
    tk.Button(imgbar, text='Save PNG...', command=lambda: save_png()).pack(side='left', padx=6, anchor='n')

    tbl_frame = tk.Frame(upper)
    tbl_frame.pack(fill='both', expand=True)
    table = ttk.Treeview(tbl_frame, show='headings', selectmode='browse')
    xsb = ttk.Scrollbar(tbl_frame, orient='horizontal', command=table.xview)
    ysb = ttk.Scrollbar(tbl_frame, orient='vertical', command=table.yview)
    table.configure(xscrollcommand=xsb.set, yscrollcommand=ysb.set)
    table.grid(row=0, column=0, sticky='nsew')
    ysb.grid(row=0, column=1, sticky='ns')
    xsb.grid(row=1, column=0, sticky='ew')
    tbl_frame.rowconfigure(0, weight=1)
    tbl_frame.columnconfigure(0, weight=1)

    lower = tk.Frame(right)
    right.add(lower, minsize=120)
    hex_title = tk.StringVar(value='Hex')
    tk.Label(lower, textvariable=hex_title, anchor='w').pack(fill='x')
    hexbox = tk.Text(lower, wrap='none', font=('Consolas', 10), bg='#f7f7f7', cursor='arrow')
    hsb = ttk.Scrollbar(lower, orient='vertical', command=hexbox.yview)
    hexbox.configure(yscrollcommand=hsb.set)
    hexbox.pack(side='left', fill='both', expand=True)
    hsb.pack(side='right', fill='y')
    hexbox.tag_configure('hl', background='#ffd75e')
    hexbox.tag_configure('addr', foreground='#888')
    hexbox.configure(state='disabled')

    # --- behaviour ---------------------------------------------------------
    def open_file():
        init = os.path.dirname(state['path']) if state['path'] else (DEFAULT_DIR if os.path.isdir(DEFAULT_DIR) else None)
        p = filedialog.askopenfilename(title='Open .wdt', filetypes=WDT_FT, initialdir=init)
        if p:
            load(p)

    def set_music(p, quiet=False):
        try:
            state['music'] = load_music(p) if p else {}
            state['music_path'] = p
        except Exception as e:
            state['music'], state['music_path'] = {}, None
            if not quiet:
                messagebox.showerror('WDT Viewer', f'Could not read music table {p}:\n{e}')

    def pick_music():
        init = os.path.dirname(state['music_path']) if state['music_path'] else None
        p = filedialog.askopenfilename(title='Open music.csv', initialdir=init,
                                       filetypes=[('CSV', '*.csv'), ('All files', '*.*')])
        if p:
            set_music(p)
            if state['path']:
                load(state['path'])

    def load(p):
        try:
            w = Wdt(Path(p).read_bytes(), Path(p).name, state['music'])
        except Exception as e:
            messagebox.showerror('WDT Viewer', f'Could not parse {p}:\n{e}')
            return
        state.update(wdt=w, path=p, items={})
        path_var.set(p)
        msg = (f'{len(w.data):,} bytes   {len(w.sections)} sections   {len(w.areas)} areas   '
               f'{len(w.entrances)} entrances   {len(w.kgrs)} KGRs   music: '
               + (f'{len(state["music"])} tracks from {state["music_path"]}' if state['music']
                  else 'not loaded (Music table...)'))
        if w.warnings:
            msg += '   WARNINGS: ' + '; '.join(w.warnings[:3])
        info_var.set(msg)
        tree.delete(*tree.get_children())

        def add(parent, nodes):
            for n in nodes:
                iid = tree.insert(parent, 'end', text=n.title, values=(f'{n.start:X}..{n.end:X}',))
                state['items'][iid] = n
                add(iid, n.children)
        add('', w.nodes)
        for iid in tree.get_children():
            tree.item(iid, open=True)
        first = tree.get_children()
        if first:
            sec0 = first[1] if len(first) > 1 else first[0]
            tree.selection_set(sec0)
            tree.see(sec0)

    def set_columns(cols, widths):
        table.configure(columns=cols)
        for c, wd in zip(cols, widths):
            table.heading(c, text=c)
            table.column(c, width=wd, stretch=c in ('Value', 'Note', 'Used by', 'Change_area targets',
                                                    'Entrances', 'Alt (story >= 0x2B) in'),
                         anchor='w')

    def show_node(n):
        w = state['wdt']
        state['node'] = n
        title_var.set(f'{n.title}    file {_hex(n.start)}..{_hex(n.end)}  ({n.end - n.start} bytes)')
        node_info_var.set(n.info)
        table.delete(*table.get_children())
        state['rows'] = {}
        state['field_rows'] = {}

        if n.image:
            iw, ih, rgba, _ = n.image
            scale = 2 if iw <= 256 else 1
            state['img'] = tk.PhotoImage(data=base64.b64encode(checker_composite(iw, ih, rgba, scale)))
            img_label.configure(image=state['img'])
            imgbar.pack(fill='x', before=tbl_frame)
        else:
            imgbar.pack_forget()

        if n.summary and not n.fields:
            cols, rows = n.summary
            set_columns(cols, [COL_WIDTHS.get(c, max(60, len(c) * 9 + 30)) for c in cols])
            for target, vals in rows:
                iid = table.insert('', 'end', values=vals)
                state['rows'][iid] = ('node', target)
        else:
            cols = ('File off', 'Rel', 'Size', 'Raw bytes', 'Type', 'Field', 'Value', 'Note')
            set_columns(cols, (80, 50, 45, 200, 60, 170, 290, 380))
            for i, f in enumerate(n.fields):
                rel = f'+{f.rel:X}' if f.rel is not None else ''
                tags = ()
                if f.color:
                    r, g, b, a = f.color
                    tag = f'c{r:02X}{g:02X}{b:02X}'
                    fg = '#000' if (r * 299 + g * 587 + b * 114) / 1000 > 128 else '#fff'
                    table.tag_configure(tag, background=f'#{r:02X}{g:02X}{b:02X}', foreground=fg)
                    tags = (tag,)
                iid = table.insert('', 'end', tags=tags, values=(
                    _hex(f.off), rel, f.size, raw_hex(w.data, f) if f.size else '', f.type,
                    f.name, f.value, f.note))
                state['rows'][iid] = ('field', i)
                state['field_rows'][i] = iid
            if n.summary:
                rows = n.summary[1]
                table.insert('', 'end', values=('', '', '', '', '', f'-- {len(rows)} children: '
                                                 'expand in the tree --', '', ''))
        show_hex(n.start, n.end)

    def show_hex(start, end):
        w = state['wdt']
        length = min(end - start, HEX_LIMIT)
        state['hex_base'], state['hex_len'] = start, length
        hexbox.configure(state='normal')
        hexbox.delete('1.0', 'end')
        lines = []
        row0 = start & ~0xF
        for row in range(row0, start + length, 16):
            cells = []
            asc = []
            for b in range(row, row + 16):
                if start <= b < start + length:
                    v = w.data[b]
                    cells.append(f'{v:02X}')
                    asc.append(chr(v) if 32 <= v < 127 else '.')
                else:
                    cells.append('  ')
                    asc.append(' ')
            lines.append(f'{row:08X}  {" ".join(cells[:8])}  {" ".join(cells[8:])}  {"".join(asc)}')
        hexbox.insert('1.0', '\n'.join(lines))
        for i in range(len(lines)):
            hexbox.tag_add('addr', f'{i + 1}.0', f'{i + 1}.8')
        hexbox.configure(state='disabled')
        more = f'  (first {HEX_LIMIT:#x} bytes shown)' if end - start > HEX_LIMIT else ''
        hex_title.set(f'Hex  {_hex(start)}..{_hex(end)}{more}')

    def hex_pos(off):
        """Text index range of one byte in the hex pane."""
        row = ((off & ~0xF) - (state['hex_base'] & ~0xF)) // 16 + 1
        col = off & 0xF
        c = 10 + col * 3 + (1 if col >= 8 else 0)
        return f'{row}.{c}', f'{row}.{c + 2}'

    def highlight(off, size):
        hexbox.tag_remove('hl', '1.0', 'end')
        b, n = state['hex_base'], state['hex_len']
        lo, hi = max(off, b), min(off + size, b + n)
        for o in range(lo, hi):
            s, e = hex_pos(o)
            hexbox.tag_add('hl', s, e)
        if lo < hi:
            hexbox.see(hex_pos(lo)[0])

    def on_tree(_e=None):
        sel = tree.selection()
        if not sel:
            return
        n = state['items'][sel[0]]
        if n is not state['node']:
            show_node(n)
        off, state['pending'] = state.get('pending'), None
        if off is not None:
            focus_field(n, off)

    def focus_field(n, off):
        hits = [(max(f.size, 1), i) for i, f in enumerate(n.fields)
                if f.off <= off < f.off + max(f.size, 1)]
        if hits:
            r = state['field_rows'][min(hits)[1]]
            table.selection_set(r)
            table.see(r)
        else:
            highlight(off, 1)

    def on_table(_e=None):
        sel = table.selection()
        if not sel or sel[0] not in state['rows']:
            return
        kind, idx = state['rows'][sel[0]]
        n = state['node']
        if kind == 'field':
            f = n.fields[idx]
            highlight(f.off, max(f.size, 1))
        else:
            highlight(idx.start, idx.end - idx.start)

    def on_table_double(_e=None):
        sel = table.selection()
        if not sel or sel[0] not in state['rows']:
            return
        kind, target = state['rows'][sel[0]]
        if kind == 'node':
            select_node(target)

    def select_node(target, field_off=None):
        """Select target in the tree; the tree's select event renders it (and the field)."""
        for iid, n in state['items'].items():
            if n is target:
                state['pending'] = field_off
                if tree.selection() == (iid,):
                    on_tree()
                else:
                    tree.selection_set(iid)
                tree.see(iid)
                return

    def deepest(off):
        best = None
        for n in Wdt._walk(state['wdt'].nodes):
            if not n.fields:
                continue
            if n.start <= off < n.end and (best is None or n.end - n.start <= best.end - best.start):
                best = n
        return best

    def goto_offset():
        if not state['wdt']:
            return
        try:
            off = int(goto_var.get().strip(), 16)
        except ValueError:
            messagebox.showerror('WDT Viewer', 'Enter a hex file offset, e.g. 700 or 0x710')
            return
        n = deepest(off)
        if not n:
            messagebox.showinfo('WDT Viewer', f'{_hex(off)} is outside every section')
            return
        select_node(n, off)

    def on_hex_click(e):
        if not state['wdt']:
            return
        idx = hexbox.index(f'@{e.x},{e.y}')
        row, col = (int(x) for x in idx.split('.'))
        if col < 10 or col > 58:
            return
        c = col - 10
        if c >= 25:
            c -= 1
        byte = c // 3
        off = (state['hex_base'] & ~0xF) + (row - 1) * 16 + byte
        hits = [(f.size, i) for i, f in enumerate(state['node'].fields)
                if f.size and f.off <= off < f.off + f.size]
        if hits:
            r = state['field_rows'].get(min(hits)[1])
            if r:
                table.selection_set(r)
                table.see(r)
            return
        for iid, (k, target) in state['rows'].items():
            if k == 'node' and target.start <= off < target.end:
                table.selection_set(iid)
                table.see(iid)
                return

    def save_png():
        n = state['node']
        if not n or not n.image:
            return
        iw, ih, rgba, name = n.image
        p = filedialog.asksaveasfilename(title='Save image', defaultextension='.png',
                                         initialfile=name, filetypes=[('PNG', '*.png')])
        if p:
            Path(p).write_bytes(png_bytes(iw, ih, rgba))

    tree.bind('<<TreeviewSelect>>', on_tree)
    table.bind('<<TreeviewSelect>>', on_table)
    table.bind('<Double-1>', on_table_double)
    table.bind('<Return>', on_table_double)
    hexbox.bind('<Button-1>', on_hex_click)
    root.bind('<Control-o>', lambda e: open_file())
    root.bind('<Control-g>', lambda e: goto_ent.focus_set())

    set_music(music_path or find_music_csv(), quiet=True)
    if initial:
        load(initial)
    root.mainloop()


def _cli_music(path):
    p = path or find_music_csv()
    if not p:
        print('(music.csv not found: BGM ids shown without names; use --music)')
        return {}
    return load_music(p)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    music_path = None
    if '--music' in args:
        i = args.index('--music')
        if i + 1 >= len(args):
            print('--music needs a path to music.csv')
            return 2
        music_path = args[i + 1]
        del args[i:i + 2]
    if args and args[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    if args and args[0] == 'dump':
        if len(args) < 2:
            print('usage: wdt_viewer.py dump <file.wdt>')
            return 2
        dump(args[1], _cli_music(music_path))
        return 0
    if args and args[0] == 'verify':
        return verify(args[1] if len(args) > 1 else DEFAULT_DIR, _cli_music(music_path))
    _run_gui(args[0] if args else None, music_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
