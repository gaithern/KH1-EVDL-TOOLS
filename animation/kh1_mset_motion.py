import struct, json, sys

def u32(b, o): return struct.unpack_from('<I', b, o)[0]
def i32(b, o): return struct.unpack_from('<i', b, o)[0]
def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def u8(b, o): return b[o]
def f32(b, o): return struct.unpack_from('<f', b, o)[0]


def parse_tracks(data, base, list_off, count):
    """Track descriptor, 6 bytes: joint_id:u16 @0, channel_flags:u8 @2 (channel type = low
    nibble; bits 4-5 = pre-first-keyframe extrapolation mode; bits 6-7 = post-last-keyframe
    extrapolation mode - confirmed from FUN_14038f820's disassembly), keyframe_count:u8 @3,
    keyframe_start_index:u16 @4 (index into the shared curve array for this motion - confirmed
    from the sampler's own field reads).

    Extrapolation modes (both pre and post, same encoding): 0=hold (clamp to the boundary
    keyframe's value), 1=linear extrapolation using the boundary segment's slope (the linear
    slope if that segment interpolates linearly, else the boundary keyframe's own tangent
    field), 2=loop (wrap the query frame by the total keyframe span), 3=passthrough (no
    adjustment - the boundary segment's own curve just runs past its domain)."""
    tracks = []
    pos = base + list_off
    for i in range(count):
        joint_id = u16(data, pos)
        flag_byte = u8(data, pos + 2)
        kf_count = u8(data, pos + 3)
        kf_start = u16(data, pos + 4)
        tracks.append({
            'joint': joint_id, 'channel': flag_byte & 0xF,
            'pre_mode': (flag_byte >> 4) & 0x3, 'post_mode': (flag_byte >> 6) & 0x3,
            'kf_count': kf_count, 'kf_start': kf_start,
        })
        pos += 6
    return tracks


def parse_instant_overrides(data, base, count4, block4_off):
    """record+0x34 (count) / record+0x38 (offset) - a flat array of one-shot (joint, channel,
    value) overrides, 8 bytes each: joint_id:u16 @0, channel:u16 @2, value:f32 @4. Confirmed
    from FUN_14038f550 (called from FUN_140391C70 whenever the actor switches to this motion,
    BEFORE per-frame keyframe sampling begins): applied unconditionally, once, to whichever
    joint/channel slot each entry names, using the exact same channel-type encoding and output
    offsets as list1/list2 (1-3=scale, 4-6=rotate, 7-9=translate - see kh1_bake_animation.py's
    CHANNEL_SLOT). This is a genuinely separate mechanism from the keyframe-curve track lists:
    it's how joints list1/list2 never keyframe-animate (e.g. Shadow's joint 46, the "shoulder"
    that aims its whole arm - never present in any of Shadow's 52 motions' list1/list2) still
    get a sensible, motion-specific resting value instead of the raw .mdls bind-pose T-stance.
    Confirmed live: writing a joint's bind-pose rotation directly into the runtime pose buffer
    got silently overwritten back on the next motion switch, well before this array was found -
    tracing FUN_14038f550 explained why. Apply once, before per-frame track sampling, when
    baking (baseline = bind pose -> apply these -> then keyframe tracks override per-frame)."""
    entries = []
    pos = base + block4_off
    for i in range(count4):
        joint_id = u16(data, pos)
        channel = u16(data, pos + 2)
        value = f32(data, pos + 4)
        entries.append({'joint': joint_id, 'channel': channel, 'value': value})
        pos += 8
    return entries


def parse_joint_flags(data, base, joint_count):
    """record+0x14 - one u32 per skeleton joint (0..joint_count-1), read by FUN_1403900B0
    (the real per-frame FK/skinning-matrix walk) to decide HOW each joint's world matrix is
    built - this is rig configuration, not per-motion data (confirmed identical across every
    motion checked). Bit meanings decoded from FUN_1403900B0's disassembly:
      bit 26 (0x4000000): skip this joint's FK update entirely this frame.
      bits 21-22 (0x600000 mask): selects one of 3 major branches (0 = see below; 0x200000 =
        a look-at/aim-toward-target branch, not fully decoded; 0x400000/0x600000 = a third
        branch, not fully decoded).
      within the bits21-22==0 branch, the low 2 bits (`flags & 3`):
        0 = see bit24/25 below.
        1 = a tangent/target-delta orientation case using bone-length data, not fully decoded
            (looks like classic two-bone IK - see FUN_14038fc20).
        2 = snap this joint's world rotation directly to a chain index of the SECONDARY
            "control rig" hierarchy (see parse_secondary_chain()) - the joint's own
            scale/rotate/translate data (list1/list2/instant_overrides/bind) is not read at
            all for orientation. Which chain index: see chain_index_from_flags().
      bit 24 (only meaningful when flags&3==0): if set, builds a local rotation matrix from
        this joint's own rotate data but composes it against the chain root instead of the
        real parent (not observed set on Shadow's rig so far).
      bit 25 (only meaningful when flags&3==0, bit24 clear): if set, this joint's own
        scale/rotate/translate data is never read for rotation - the scratch matrix stays
        identity, so hierarchy-compose makes it inherit its parent's world rotation exactly,
        unchanged. If clear, normal FK: builds the local rotation matrix from this joint's own
        rotate data (the "textbook" case)."""
    off14 = i32(data, base + 0x14)
    pos = base + off14
    flags = []
    for i in range(joint_count):
        flags.append(u32(data, pos))
        pos += 4
    return flags


def chain_index_from_flags(flags):
    """The bit-packed 'which secondary-chain index' field used when flags&3==2 (see
    parse_joint_flags). Formula traced from FUN_1403900B0's disassembly."""
    return ((((flags >> 16) & 0x800) | (flags & 0x7FC)) >> 2) - 1


def parse_secondary_chain(data, base, count3, block3_off):
    """record+0x2C (count, aka 'count3' elsewhere in this file) / record+0x30 (offset) - a
    SEPARATE, much smaller hierarchy (Shadow: always 11 entries) that FUN_140391C70's
    "list2"/tracks_secondary loop composes via FUN_1401db080+FUN_1401db4d0 into a scratch
    array (DAT_142ef1f50 in the disassembly). Re-reading tracks_secondary's own 'joint' field:
    it is NOT a skeleton joint index - it's a position in THIS chain (0..count3-1). Confirmed
    by decoding each entry's offset+12 (a plain i32, never written by any of channels 1-9's
    offsets - i.e. genuinely static per-entry data, not track-animated): a clean parent-index
    tree (index 0's parent is -1, i.e. the chain's own root - fed from the actor's own current
    world transform at runtime; every other index's parent is another index in 0..count3-1),
    identical across every motion checked. Main-skeleton joints with flags&3==2 (see
    parse_joint_flags) snap their world rotation directly to one of these chain indices'
    composed world rotation instead of using their own keyframe/bind data - this is (most of)
    what actually drives Shadow's torso/arm carriage; the keyframe/override system documented
    elsewhere in this file only ever supplies a minority of the joints that matter for that.

    Each 0x28-byte entry is the SAME scale/parent/rot/trans field layout as a main-skeleton Hrc
    joint (scale @0, parent @0xc, rot @0x10, trans @0x1c) - confirmed against OpenKH's real KH2
    PS2-emulator ground truth (see kh1_bake_animation.py's _local_basis_secondary): entries with
    no keyframe track touching a given rot/trans/scale channel this motion (e.g. index 4/5 never
    have a rotate track at all) still need a REAL, often-nonzero rest value for that channel -
    this was previously read as a hardcoded identity/zero baseline in _solve_secondary_chain,
    which is what made every joint snapped to (or aiming at) an untracked secondary-chain entry
    come out rotated wrong by that entry's own missing rest rotation."""
    entries = []
    pos = base + block3_off
    for i in range(count3):
        scale = (f32(data, pos + 0), f32(data, pos + 4), f32(data, pos + 8))
        parent = i32(data, pos + 12)
        rot = (f32(data, pos + 0x10), f32(data, pos + 0x14), f32(data, pos + 0x18))
        trans = (f32(data, pos + 0x1c), f32(data, pos + 0x20), f32(data, pos + 0x24))
        entries.append({'index': i, 'parent': parent, 'scale': scale, 'rot': rot, 'trans': trans})
        pos += 0x28
    return entries


def parse_keyframes(data, curve_base_abs, start_index, count):
    kfs = []
    pos = curve_base_abs + start_index * 16
    for i in range(count):
        frame_packed = i32(data, pos)
        value = f32(data, pos + 4)
        out_tan = f32(data, pos + 8)
        in_tan_next = f32(data, pos + 12)
        kfs.append({'frame': frame_packed >> 16, 'flag': frame_packed & 0xFF, 'value': value,
                    'out_tan': out_tan, 'in_tan_next': in_tan_next})
        pos += 16
    return kfs


def parse_motion_record(data, off):
    base = off
    frame_count = i32(data, base + 0x04)
    fps = f32(data, base + 0x08)
    flags = i32(data, base + 0x0C)
    joint_count = i32(data, base + 0x10)
    count1 = i32(data, base + 0x18)
    list1_off = i32(data, base + 0x1C)
    count2 = i32(data, base + 0x20)
    list2_off = i32(data, base + 0x24)
    curve_off = i32(data, base + 0x28)
    curve_base_abs = base + curve_off
    count3 = i32(data, base + 0x2C)
    block3_off = i32(data, base + 0x30)
    count4 = i32(data, base + 0x34)
    block4_off = i32(data, base + 0x38)

    tracks1 = parse_tracks(data, base, list1_off, count1)
    tracks2 = parse_tracks(data, base, list2_off, count2)
    for t in tracks1 + tracks2:
        t['keyframes'] = parse_keyframes(data, curve_base_abs, t['kf_start'], t['kf_count'])
    instant_overrides = parse_instant_overrides(data, base, count4, block4_off)
    joint_flags = parse_joint_flags(data, base, joint_count)
    secondary_chain = parse_secondary_chain(data, base, count3, block3_off)

    return {
        'offset': off, 'frame_count': frame_count, 'fps': fps, 'flags': flags,
        'joint_count': joint_count,
        'instant_overrides': instant_overrides,
        'joint_flags': joint_flags,
        'secondary_chain': secondary_chain,
        # tracks1 (list1) writes directly into the runtime per-joint skinning-pose buffer
        # (instance+0x1b0 resolved) - this is the actual render skeleton. tracks2 (list2)
        # writes into a separate scratch buffer living in the motion record itself
        # (record+0x30), which feeds FUN_1401db080/FUN_1401db4d0 into DAT_142ef1f50 - a
        # different mechanism entirely,
        # not the skinning pose. Keep them separate rather than merging: an earlier version
        # of the baker merged tracks1+tracks2 into one per-joint pose, which visibly
        # stretched limbs on the joints tracks2 happens to touch (2-9/10 in Shadow's file).
        'tracks': tracks1,
        'tracks_secondary': tracks2,
    }


if __name__ == '__main__':
    path = sys.argv[1]
    off = int(sys.argv[2], 16)
    data = open(path, 'rb').read()
    rec = parse_motion_record(data, off)
    print(f"frame_count={rec['frame_count']} fps={rec['fps']} flags={rec['flags']} joint_count={rec['joint_count']}")
    print(f"{len(rec['tracks'])} tracks total")
    for t in rec['tracks'][:8]:
        print(f"  joint={t['joint']:3d} channel={t['channel']} kf_count={t['kf_count']} kf_start={t['kf_start']}")
        for kf in t['keyframes'][:4]:
            print(f"      frame={kf['frame']:4d} flag={kf['flag']:#04x} value={kf['value']:.4f} out_tan={kf['out_tan']:.5f}")
