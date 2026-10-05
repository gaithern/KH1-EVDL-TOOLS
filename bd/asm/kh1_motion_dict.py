#!/usr/bin/env python3
# Resolves KH1 AI-script motion_ids to local .mset animation indices, using the
# motion_id -> animation table stored in the enemy's own .mset file.
import struct
import sys

USAGE = """Usage:
  python kh1_motion_dict.py <file.mset> [motion_id ...]
"""

DICTIONARY_START_OFFSET = 0x08
DICTIONARY_END_OFFSET = 0x0C
ENTRY_SIZE = 4
ANIM_INDEX_MASK = 0xFFF
NO_ANIMATION = 0xFFF


def read_motion_dict(mset_path):
    with open(mset_path, "rb") as file:
        data = file.read()
    dictionary_start = struct.unpack_from("<I", data, DICTIONARY_START_OFFSET)[0]
    dictionary_end = struct.unpack_from("<I", data, DICTIONARY_END_OFFSET)[0]
    entry_count = (dictionary_end - dictionary_start) // ENTRY_SIZE
    entries = struct.unpack_from(f"<{entry_count}I", data, dictionary_start)
    result = {}
    for motion_id, entry in enumerate(entries):
        anim_index = entry & ANIM_INDEX_MASK
        if anim_index != NO_ANIMATION:
            result[motion_id] = anim_index
    return result


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        return
    table = read_motion_dict(sys.argv[1])
    if len(sys.argv) > 2:
        motion_ids = []
        for argument in sys.argv[2:]:
            motion_ids.append(int(argument))
    else:
        motion_ids = sorted(table)
    for motion_id in motion_ids:
        if motion_id in table:
            print(f"motion_id {motion_id:4d} -> anim{table[motion_id]:04d}")
        else:
            print(f"motion_id {motion_id:4d} -> (no entry / invalid for this enemy)")


if __name__ == "__main__":
    main()
