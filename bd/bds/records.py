"""Named-field text for the typed records of a .bd data area (stat pages, drop tables, attack data,
target weights). Field layouts: vault notes "Enemy stat pages (bd battle params)", "Enemy drop tables
and prize pickup chain", "Enemy target weight tables (bd)" and KH1-DOCUMENTATION hit-parameters.csv.
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'asm'))
import kh1_bd_disasm as bd

INT = 'int'
FLOAT = 'float'

STAT_PAGE_FIELDS = [
    ('hp', INT),
    ('attack_level', INT),
    ('defense_level', INT),
    ('min_damage_taken', INT),
    ('max_damage_taken', INT),
    ('mp_recovery_on_hit', INT),
    ('knockback_weight', FLOAT),
    ('exp', INT),
    ('unknown_20', INT),
    ('outgoing_damage_multiplier', FLOAT),
    ('resist_00_unknown', INT),
    ('resist_01_physical', INT),
    ('resist_02_fire', INT),
    ('resist_03_blizzard', INT),
    ('resist_04_thunder', INT),
    ('resist_05_unknown', INT),
    ('resist_06_unknown', INT),
    ('resist_07_unknown', INT),
    ('resist_08_percent_hp', INT),
    ('resist_09_stop', INT),
    ('resist_0a_stun', INT),
    ('resist_0b_heal', INT),
    ('resist_0c_unknown', INT),
    ('resist_0d_unknown', INT),
    ('resist_0e_unknown', INT),
    ('resist_0f_unknown', INT),
    ('unknown_68', INT),
]

DROP_TABLE_FIELDS = [
    ('small_munny', INT),
    ('medium_munny', INT),
    ('large_munny', INT),
    ('small_hp', INT),
    ('large_hp', INT),
    ('small_mp', INT),
    ('large_mp', INT),
]
DROP_TABLE_PRIZES = 3

HIT_PARAMS_FIELDS = [
    ('damage_source', INT),
    ('hit_type', INT),
    ('non_enemy_reaction_level', INT),
    ('enemy_reaction_level', INT),
    ('hitbox_anchor', INT),
    ('non_enemy_power_bonus', INT),
    ('crit_chance', INT),
    ('crit_damage_bonus', INT),
    ('non_enemy_min_damage', INT),
    ('non_enemy_max_damage', INT),
    ('unknown_28', INT),
    ('unknown_2c', INT),
    ('mp_cost', INT),
    ('unknown_34', INT),
    ('unknown_38', INT),
    ('unknown_3c', INT),
    ('level_6_7_motion_id', INT),
    ('object_damage', INT),
    ('enemy_power_bonus', INT),
    ('enemy_min_damage', INT),
    ('enemy_max_damage', INT),
    ('unknown_54', FLOAT),
    ('unknown_58', FLOAT),
    ('hit_radius', FLOAT),
    ('unknown_60', INT),
    ('unknown_64', FLOAT),
    ('unknown_68', FLOAT),
    ('attack_id', INT),
]

TARGET_WEIGHT_COUNT = 5

KIND_KEYWORDS = {
    'stat page': 'stat_page',
    'drop table': 'drop_table',
    'hit params': 'attack_data',
    'target weights': 'target_weights',
}

RECORD_SIZES = {
    'stat_page': len(STAT_PAGE_FIELDS) * 4,
    'drop_table': len(DROP_TABLE_FIELDS) * 4 + DROP_TABLE_PRIZES * 8,
    'attack_data': len(HIT_PARAMS_FIELDS) * 4,
    'target_weights': TARGET_WEIGHT_COUNT * 4,
}

NAME_PREFIXES = {
    'stat_page': 'stats',
    'drop_table': 'drops',
    'attack_data': 'attack',
    'target_weights': 'weights',
}

RECORD_HEADER_RE = re.compile(r'^    (stat_page|drop_table|attack_data|target_weights) ([A-Za-z_]\w*) \{$')
FIELD_LINE_RE = re.compile(r'^\s*([a-z_0-9]+)\s*=\s*(.+?);\s*$')
CALL_LINE_RE = re.compile(r'^\s*(prize|weights)\((.*)\);\s*$')
RAW_FLOAT_RE = re.compile(r'^__f32\((0x[0-9A-Fa-f]{8})\)$')


def float_text(four_bytes):
    text = bd.f32_text(four_bytes)
    if text.startswith('0x'):
        return f'__f32({text})'
    if not re.search(r'[.en]', text):
        text += '.0'
    return text


def value_text(raw, field_type):
    if field_type == FLOAT:
        return float_text(raw)
    return str(struct.unpack('<i', raw)[0])


def value_bytes(text, field_type):
    text = text.strip()
    if field_type == FLOAT:
        raw_float = RAW_FLOAT_RE.match(text)
        if raw_float:
            return struct.pack('>I', int(raw_float.group(1), 16))[::-1]
        return struct.pack('<f', float(text))
    number = int(text, 0)
    if number < 0:
        number += 1 << 32
    if not 0 <= number < 1 << 32:
        raise ValueError(f'{text} does not fit in 32 bits')
    return struct.pack('<I', number)


def keyword_for(kinds, span):
    if len(kinds) != 1 or kinds[0] not in KIND_KEYWORDS:
        return None
    keyword = KIND_KEYWORDS[kinds[0]]
    if span == 0 or span % RECORD_SIZES[keyword] != 0:
        return None
    return keyword


def field_lines(raw, fields):
    out = []
    for index, (name, field_type) in enumerate(fields):
        out.append(f'        {name} = {value_text(raw[index * 4:index * 4 + 4], field_type)};')
    return out


def body_lines(keyword, raw):
    if keyword == 'stat_page':
        return field_lines(raw, STAT_PAGE_FIELDS)
    if keyword == 'attack_data':
        return field_lines(raw, HIT_PARAMS_FIELDS)
    if keyword == 'drop_table':
        out = field_lines(raw, DROP_TABLE_FIELDS)
        prize_start = len(DROP_TABLE_FIELDS) * 4
        for slot in range(DROP_TABLE_PRIZES):
            position = prize_start + slot * 8
            chance = value_text(raw[position:position + 4], FLOAT)
            item = value_text(raw[position + 4:position + 8], INT)
            out.append(f'        prize({chance}, {item});')
        return out
    weights = []
    for index in range(TARGET_WEIGHT_COUNT):
        weights.append(value_text(raw[index * 4:index * 4 + 4], INT))
    return [f'        weights({", ".join(weights)});']


def record_offsets(keyword, offset, raw):
    size = RECORD_SIZES[keyword]
    return [offset + start for start in range(0, len(raw), size)]


def record_lines(keyword, offset, raw, names):
    size = RECORD_SIZES[keyword]
    out = []
    for start in range(0, len(raw), size):
        out.append(f'    {keyword} {names[offset + start]} {{')
        out += body_lines(keyword, raw[start:start + size])
        out.append('    }')
    return out


def split_arguments(text):
    parts = []
    for part in text.split(','):
        parts.append(part.strip())
    return parts


def fields_bytes(keyword, fields, assignments):
    out = b''
    for name, field_type in fields:
        if name not in assignments:
            raise ValueError(f'{keyword}: missing field {name}')
        out += value_bytes(assignments.pop(name), field_type)
    if assignments:
        raise ValueError(f'{keyword}: unknown field {", ".join(sorted(assignments))}')
    return out


def record_bytes(keyword, body):
    assignments = {}
    calls = []
    for line in body:
        line = line.split('//')[0].rstrip()
        if not line.strip():
            continue
        field_match = FIELD_LINE_RE.match(line)
        call_match = CALL_LINE_RE.match(line)
        if field_match:
            if field_match.group(1) in assignments:
                raise ValueError(f'{keyword}: field {field_match.group(1)} given twice')
            assignments[field_match.group(1)] = field_match.group(2)
        elif call_match:
            calls.append((call_match.group(1), split_arguments(call_match.group(2))))
        else:
            raise ValueError(f'{keyword}: cannot read {line.strip()!r}')
    if keyword == 'stat_page':
        return check_no_calls(keyword, calls, fields_bytes(keyword, STAT_PAGE_FIELDS, assignments))
    if keyword == 'attack_data':
        return check_no_calls(keyword, calls, fields_bytes(keyword, HIT_PARAMS_FIELDS, assignments))
    if keyword == 'drop_table':
        out = fields_bytes(keyword, DROP_TABLE_FIELDS, assignments)
        prizes = [arguments for name, arguments in calls if name == 'prize']
        if len(prizes) != DROP_TABLE_PRIZES or len(calls) != DROP_TABLE_PRIZES:
            raise ValueError(f'drop_table: needs exactly {DROP_TABLE_PRIZES} prize(chance, item) lines')
        for arguments in prizes:
            if len(arguments) != 2:
                raise ValueError('drop_table: prize takes (chance, item)')
            out += value_bytes(arguments[0], FLOAT) + value_bytes(arguments[1], INT)
        return out
    if assignments or len(calls) != 1 or calls[0][0] != 'weights' or len(calls[0][1]) != TARGET_WEIGHT_COUNT:
        raise ValueError(f'target_weights: needs exactly one weights(...) line with {TARGET_WEIGHT_COUNT} numbers')
    out = b''
    for argument in calls[0][1]:
        out += value_bytes(argument, INT)
    return out


def check_no_calls(keyword, calls, out):
    if calls:
        raise ValueError(f'{keyword}: unexpected {calls[0][0]}(...) line')
    return out
