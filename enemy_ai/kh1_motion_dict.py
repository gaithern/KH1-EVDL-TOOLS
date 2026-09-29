#!/usr/bin/env python3
"""Resolve KH1 AI-script motion_ids (see kh1_motion_ids.py) to local .mset animation
indices (0-51, the same numbering as ModelViewerWX's anim0000-anim0051 and
KH1MsetConverter's own enumeration - see reference_kh1_ground_truth_tools memory).

Every .mset file carries its own motion_id -> local-animation-index dictionary as a
plain array, directly embedded in the file - NO live game/Cheat Engine needed. Found
by live-tracing the engine's resolver (FUN_1402A01E0 in the Steam exe, called from the
per-frame action-dequeue FUN_14029FC40) with Ghidra + Cheat Engine, then confirmed
byte-for-byte identical against the .mset file on disk (see
project_ai_motion_id_resolution.md for the full derivation, including two live-capture
methods and the exact function addresses):

  header @ file+0x08 (u32): absolute file offset where the dictionary array starts
  header @ file+0x0C (u32): absolute file offset where it ends (exclusive)
  (same "small header of absolute offsets bounding a section" convention this project's
  other .mset/.mdls parsers already rely on - see kh1_mset_motion.py's own header
  fields for the equivalent pattern applied to motion records)

Each array entry is one u32, DIRECTLY indexed by raw motion_id (entry = motion_id'th
u32 in the array, no further indirection):
  bits 0-11 (& 0xFFF): resolved local .mset animation index (0-51). 0xFFF = this
    motion_id is unused/invalid for this enemy.
  bits 12-14 (>> 0xC & 7): a difficulty/state "variant mode" selector - modes 3 and 4
    add +2 or +1 to the base index depending on runtime state (g_StateBitFlags &
    0x1000 plus two caller-supplied state bits) - NOT applied here (this reads the
    BASE index only; see project memory if the variant adjustment is ever needed).
  bit 15 (& 0x8000): an extra flag bit in the engine's own packed return value,
    unrelated to which .mset offset ultimately plays - safe to ignore for this purpose.

Verified against 13 live-captured (motion_id -> index) pairs for Shadow (xa_ex_2020)
with zero mismatches - see kh1_motion_id_resolution.md.

Usage:
  python kh1_motion_dict.py <file.mset> [motion_id ...]
"""
import struct
import sys


def read_motion_dict(mset_path):
    """Returns {motion_id: local_animation_index} for every motion_id this .mset
    defines a real (non-0xFFF) entry for."""
    data = open(mset_path, "rb").read()
    dict_off = struct.unpack_from("<I", data, 0x08)[0]
    dict_end = struct.unpack_from("<I", data, 0x0C)[0]
    n = (dict_end - dict_off) // 4
    entries = struct.unpack_from(f"<{n}I", data, dict_off)
    result = {}
    for motion_id, raw in enumerate(entries):
        idx = raw & 0xFFF
        if idx != 0xFFF:
            result[motion_id] = idx
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    mset_path = sys.argv[1]
    table = read_motion_dict(mset_path)
    motion_ids = [int(a) for a in sys.argv[2:]] if len(sys.argv) > 2 else sorted(table)
    for mid in motion_ids:
        if mid in table:
            print(f"motion_id {mid:4d} -> anim{table[mid]:04d}")
        else:
            print(f"motion_id {mid:4d} -> (no entry / invalid for this enemy)")


if __name__ == "__main__":
    main()
