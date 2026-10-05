"""Build an .evs file into a copy of the original game script; new message strings go into the set's .binl."""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import evdl_format
import lang
import msgstore

SET_FILE_HEADER_SIZE = 16
SET_FILE_ALIGNMENT = 0x80
EMPTY_ENTRY_OPERAND = 0x10
STUB_ENTRY_COUNT = 8
STUB_KGR = struct.pack('<I', STUB_ENTRY_COUNT) + evdl_format.encode_instruction(evdl_format.YIELD, EMPTY_ENTRY_OPERAND) * STUB_ENTRY_COUNT
APPENDED_KGR_UNKNOWN_0 = 1
APPENDED_KGR_UNKNOWN_1 = 1


def set_file_header(data):
    if len(data) < SET_FILE_HEADER_SIZE:
        return None
    other_count_0, other_count_1, kgr_count, string_offset = struct.unpack_from('<4i', data, 0)
    if other_count_0 < 0 or other_count_1 < 0 or kgr_count < 1:
        return None
    if string_offset != SET_FILE_HEADER_SIZE + 4 * (other_count_0 + other_count_1 + kgr_count):
        return None
    return other_count_0, other_count_1, kgr_count, string_offset


def appended_kgr(stream):
    header = evdl_format.KGR_MAGIC + struct.pack('<II', APPENDED_KGR_UNKNOWN_0, APPENDED_KGR_UNKNOWN_1)
    return header + bytes([evdl_format.count_scripts(stream)]) + stream


def padding_to(length, alignment):
    return bytes(-length % alignment)


def grow_set_file(data, extra_streams):
    other_count_0, other_count_1, kgr_count, string_offset = set_file_header(data)
    table_growth = 4 * len(extra_streams)
    new_string_offset = string_offset + table_growth
    old_entry_count = other_count_0 + other_count_1 + kgr_count
    offset_table = []
    for offset in struct.unpack_from(f'<{old_entry_count}i', data, SET_FILE_HEADER_SIZE):
        offset_table.append(offset + table_growth)
    body = bytearray(data[string_offset:])
    for stream in extra_streams:
        offset_table.append(new_string_offset + len(body))
        body += appended_kgr(stream)
    body += padding_to(new_string_offset + len(body), SET_FILE_ALIGNMENT)
    header = struct.pack('<4i', other_count_0, other_count_1, kgr_count + len(extra_streams), new_string_offset)
    return header + struct.pack(f'<{len(offset_table)}i', *offset_table) + bytes(body)


def repack_existing_kgrs(orig, file_type, streams, kgrs):
    merged_streams = []
    for index, kgr in enumerate(kgrs):
        merged_streams.append(streams.get(index, bytes(kgr['stream'])))
    if file_type == 'ard':
        return evdl_format.repack_ard(orig, kgrs, merged_streams)
    return evdl_format.repack_evdl(orig, kgrs, merged_streams)


def can_append_kgrs(repacked, file_type, kgr_count):
    if file_type == 'ard':
        return False
    header = set_file_header(repacked)
    return header is not None and header[2] == kgr_count


def repack(orig, file_type, streams):
    if file_type == 'ard':
        kgrs = evdl_format.parse_ard(orig)
    else:
        kgrs = evdl_format.parse_evdl(orig)
    repacked = repack_existing_kgrs(orig, file_type, streams, kgrs)
    kgr_count_needed = max(streams) + 1
    if kgr_count_needed <= len(kgrs):
        return repacked
    if not can_append_kgrs(repacked, file_type, len(kgrs)):
        raise ValueError(f'kgr {kgr_count_needed - 1}: cannot add KGRs to this file (has {len(kgrs)})')
    extra_streams = []
    for index in range(len(kgrs), kgr_count_needed):
        extra_streams.append(streams.get(index, STUB_KGR))
    return grow_set_file(repacked, extra_streams)


def compile_evs(evs_path, store):
    lang.COMPILE_WARNINGS.clear()
    blocks = lang.compile_file_text(evs_path.read_text(encoding='utf-8'), store)
    for warning in lang.COMPILE_WARNINGS:
        print(f'  warning: {evs_path.name}: {warning}')
    if not blocks:
        raise ValueError(f'{evs_path.name}: no `kgr N {{ }}` blocks')
    return blocks


def build_file(evs_path, orig_path, out_path):
    evs_path, orig_path, out_path = Path(evs_path), Path(orig_path), Path(out_path)
    if orig_path.suffix.lower() == '.ard':
        file_type = 'ard'
    else:
        file_type = 'evdl'
    store = None
    if file_type != 'ard':
        store = msgstore.store_for(out_path, [out_path.parent, orig_path.parent], out_path.parent)
    blocks = compile_evs(evs_path, store)
    output = repack(orig_path.read_bytes(), file_type, blocks)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(output)
    if store is None:
        return []
    written = []
    for language in store.save():
        written.append(str(store.targets[language]))
    return written


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evs')
    parser.add_argument('original')
    parser.add_argument('out')
    args = parser.parse_args()
    print(build_file(args.evs, args.original, args.out))
