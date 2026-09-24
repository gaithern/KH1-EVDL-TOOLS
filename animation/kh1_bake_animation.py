import struct, json, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kh1_mset_motion import parse_motion_record, chain_index_from_flags
from kh1_mdls_parse import parse_full as parse_mdls_full


def _segment_slope(kfs, i, j):
    """Slope used for linear-extrapolation mode: the segment's own linear slope if kf[i] is
    flagged linear, else kf[i]'s out_tan - traced from FUN_14038f820 (0x14038f98a /
    0x14038f9fb blocks), same tangent-field convention as the main Hermite evaluator."""
    a, b = kfs[i], kfs[j]
    if a['flag'] == 1:
        iv = b['frame'] - a['frame']
        return (b['value'] - a['value']) / iv if iv != 0 else 0.0
    return a['out_tan']


def _extrapolate(mode, frame, kfs, at_start):
    """Mirrors FUN_14038f820's pre/post extrapolation dispatch (track flag byte bits 4-5 /
    6-7). Returns ('value', v) to return v directly (modes 0/1, matching the game's early
    RET), or ('frame', f) to continue into the normal bracket+interpolate path with a
    (possibly rewritten) frame - modes 2 (wrapped) and 3 (untouched passthrough)."""
    edge = kfs[0] if at_start else kfs[-1]
    if mode == 0:  # hold
        return ('value', edge['value'])
    if mode == 1:  # linear extrapolation along the boundary segment's slope
        slope = _segment_slope(kfs, 0, 1) if at_start else _segment_slope(kfs, -2, -1)
        return ('value', edge['value'] + (frame - edge['frame']) * slope)
    if mode == 2:  # loop: wrap by the total keyframe span
        span = kfs[-1]['frame'] - kfs[0]['frame']
        if span > 0:
            if at_start:
                while frame < kfs[0]['frame']:
                    frame += span
            else:
                while frame > kfs[-1]['frame']:
                    frame -= span
        return ('frame', frame)
    return ('frame', frame)  # mode 3: passthrough, unmodified


def sample_track(track, frame):
    kfs = track['keyframes']
    n = len(kfs)
    if n == 0:
        return None
    if n == 1:
        return kfs[0]['value']
    # Pre- and post-extrapolation are each checked unconditionally in that order (matching
    # FUN_14038f820's fallthrough structure - the post check runs even after a pre-side
    # frame rewrite), see _extrapolate().
    if frame <= kfs[0]['frame']:
        kind, res = _extrapolate(track['pre_mode'], frame, kfs, True)
        if kind == 'value':
            return res
        frame = res
    if frame >= kfs[-1]['frame']:
        kind, res = _extrapolate(track['post_mode'], frame, kfs, False)
        if kind == 'value':
            return res
        frame = res
    # binary search for the bracketing pair
    lo, hi = 0, n - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if kfs[mid]['frame'] <= frame:
            lo = mid
        else:
            hi = mid
    a, b = kfs[lo], kfs[hi]
    t0, t1 = a['frame'], b['frame']
    if t1 == t0:
        return a['value']
    t = (frame - t0) / (t1 - t0)
    # Mode is the *earlier* keyframe's own flag byte directly (re-confirmed from the disassembly:
    # `TEST CL,CL / JZ step` where CL is the low byte of the earlier packed frame+flag dword;
    # `CMP EAX,1 / JZ linear` next; anything else falls through to the Hermite branch). My first
    # pass wrongly bit-shifted this from the track descriptor's byte instead of reading it plainly
    # from the keyframe itself - that made nearly everything resolve to "step" (mode 0), which is
    # why the first bake looked frozen/jerky between poses.
    mode = a['flag']
    p0, p1 = a['value'], b['value']
    if mode == 0:
        return p0  # step
    if mode == 1:
        return p0 + (p1 - p0) * t  # linear
    # Cubic Hermite - traced register-by-register from the disassembly this time (not guessed):
    # the tangent fields are earlier.in_tan_next and later.out_tan (not earlier.out_tan/in_tan_next
    # as first assumed), and the tangent terms are scaled by the raw keyframe interval (t1-t0),
    # not used as unit-interval slopes directly.
    iv = t1 - t0
    m0, m1 = a['in_tan_next'], b['out_tan']
    h00 = 2*t**3 - 3*t**2 + 1
    h10 = t**3 - 2*t**2 + t
    h01 = -2*t**3 + 3*t**2
    h11 = t**3 - t**2
    return h00*p0 + h10*iv*m0 + h01*p1 + h11*iv*m1  # cubic Hermite


# CORRECTED this session: channels 1-3 = scale, 7-9 = translate (swapped from the earlier
# assumption). The old mapping was based only on which memory offset each group landed at in
# tracks1's output slot, which was never actually proof of physical meaning. Independent proof
# this session: FUN_1401db080 (the TRS->matrix builder both tracks2 and the bind-pose setup
# function FUN_1401d5b10 call) writes its *first* arg to the matrix diagonal (indices 0/5/10)
# and its *third* arg to the translation column (indices 12/13/14). FUN_1401d5b10 calls it
# directly from .mdls's own joint fields in their confirmed, unambiguous order - scale (offset
# 0), rotate (offset 0x10), translate (offset 0x20) - in exactly that argument position, proving
# FUN_1401db080's calling convention is (scale, rotate, translate), not (translate, rotate,
# scale). This resolves the earlier "channel 7-9 magnitude looks too big for scale" flag: 7-9 is
# translate (bone position, ±57 is a normal range), and the previous mapping had been feeding
# scale values into forward kinematics as if they were positions (actively wrong) while silently
# dropping the real translate channel (scale was never applied to vertices, so it was inert).
CHANNEL_SLOT = {1: ('scale', 0), 2: ('scale', 1), 3: ('scale', 2),
                4: ('rot', 0), 5: ('rot', 1), 6: ('rot', 2),
                7: ('trans', 0), 8: ('trans', 1), 9: ('trans', 2)}


def _mat3_mul(a, b):
    r = [0.0] * 9
    for i in range(3):
        for j in range(3):
            r[i*3+j] = a[i*3+0]*b[0*3+j] + a[i*3+1]*b[1*3+j] + a[i*3+2]*b[2*3+j]
    return r


def _mat3_vec(m, v):
    return (m[0]*v[0]+m[1]*v[1]+m[2]*v[2], m[3]*v[0]+m[4]*v[1]+m[5]*v[2], m[6]*v[0]+m[7]*v[1]+m[8]*v[2])


def _mat3_transpose(m):
    return [m[0], m[3], m[6], m[1], m[4], m[7], m[2], m[5], m[8]]


def _permute_trans(t):
    """Stored (t0,t1,t2) local-translate triples use the SAME axis permutation as rotation
    (see _local_basis): verified against HyperCrown across 4 joints (3/4/6/65) by comparing
    each joint's raw stored translate against HyperCrown's independently-computed world
    translation column - t[2] is the real X offset, t[0] is Y, t[1] is Z. Apply this any time
    a stored translate triple is about to be used as an actual position/offset vector (not when
    just copying it between pose dicts in its original storage order)."""
    return (t[2], t[0], t[1])


def _vec3_sub(a, b):
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def _vec3_normalize(v):
    import math
    l = math.sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]) or 1.0
    return (v[0]/l, v[1]/l, v[2]/l)


def _vec3_cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


_UP_REF = (0.0, 1.0, 0.0)


def _aim_basis(target_world, own_local_trans, parent_w):
    """uvar10==1's aim/2-bone-IK orientation (traced from FUN_1403900B0's disassembly around
    0x140390e20-0x140390f39): builds an orthonormal basis whose row0 points from this joint's
    own local position toward a secondary-chain target (both expressed in the parent's local
    space, matching the game's own inverse-transform-then-transform pattern - see
    _solve_main_skeleton's bits21-22==1 handling for the same target-position math), with
    row1/row2 completing a right-handed frame via cross products against a world-up reference.
    Re-examined the exact FUN_140386c70 call sites (not just the general pattern): each call's
    RCX/RDX/R8 argument order is dest/a/b computing dest=a x b. The three calls are
    scratch=direction x up, row1=scratch x direction, row2=direction x row1 - note the LAST
    call's operand order is (direction, row1), not (row1, direction). An earlier version of
    this function had row2's operands reversed (row1 x direction), which is off by a sign flip
    (cross product is anti-commutative) - a consistent, whole-axis-mirrored error that matches
    reports of the model looking "twisted" rather than randomly wrong."""
    parent_rot_t = _mat3_transpose(parent_w['rot'])
    target_local = _mat3_vec(parent_rot_t, _vec3_sub(target_world, parent_w['pos']))
    direction = _vec3_normalize(_vec3_sub(target_local, own_local_trans))
    scratch = _vec3_cross(direction, _UP_REF)
    row1 = _vec3_normalize(_vec3_cross(scratch, direction))
    row2 = _vec3_normalize(_vec3_cross(direction, row1))
    return [direction[0], direction[1], direction[2],
            row1[0], row1[1], row1[2],
            row2[0], row2[1], row2[2]]


def _rot_x(a):
    import math
    c, s = math.cos(a), math.sin(a)
    return [1, 0, 0, 0, c, -s, 0, s, c]


def _rot_y(a):
    import math
    c, s = math.cos(a), math.sin(a)
    return [c, 0, s, 0, 1, 0, -s, 0, c]


def _rot_z(a):
    import math
    c, s = math.cos(a), math.sin(a)
    return [c, -s, 0, s, c, 0, 0, 0, 1]


_IDENTITY3 = [1, 0, 0, 0, 1, 0, 0, 0, 1]

# Was diag(1,-1,-1) (Rx(180deg)), derived from a live memory read that found the secondary
# chain's own root always has row1==(0,-1,0) - back when "row1" was assumed to be the
# meaningful/up-ish row. That assumption predates this session's discovery that the engine's
# real axis convention doesn't map stored/read rows to same-named axes the naive way (see
# _local_basis) - re-checked this session: with the diag(1,-1,-1) patch, the character's native
# "up" (Z, since the engine is Z-up - see kh1_mdls_parse.py) maps to (0,0,-1), i.e. upside
# down; with identity it correctly maps to (0,0,1). The old value was compensating for the
# axis-convention bug that's now fixed at its actual source, so it's now a double-correction -
# removed rather than kept as a live-http-verified special case.
ROOT_BASIS = [1, 0, 0, 0, 1, 0, 0, 0, 1]


def _local_basis(rot, scale):
    # Axis convention verified this session against HyperCrown, an independent, mature KH1
    # .mdls/.mset converter (see kh1_mdls_parse.py's forward_kinematics for the full derivation):
    # rot[2] drives rotation about X (outermost), rot[1] drives Z (middle), rot[0] drives Y
    # (innermost) - NOT the same-named-axis mapping this project used previously.
    r = _mat3_mul(_mat3_mul(_rot_x(rot[2]), _rot_z(rot[1])), _rot_y(rot[0]))
    return [r[0]*scale[0], r[1]*scale[1], r[2]*scale[2],
            r[3]*scale[0], r[4]*scale[1], r[5]*scale[2],
            r[6]*scale[0], r[7]*scale[1], r[8]*scale[2]]


def _local_basis_secondary(rot, scale):
    """Same per-field layout as _local_basis (rot/scale from the same Hrc-shaped struct - see
    kh1_mset_motion.parse_secondary_chain), but the secondary/control-rig chain's own composer
    (FUN_1401db080, a DIFFERENT function from the main skeleton's) uses a DIFFERENT axis
    convention - NOT _local_basis's Rx(rot[2])*Rz(rot[1])*Ry(rot[0]). Derived this session
    against OpenKH's real KH2 PS2-emulator ground truth (see project memory for the full
    reproduction steps and pitfalls hit while deriving this): rot[i] maps DIRECTLY to its
    same-named axis here (rot[0]->X, rot[1]->Y, rot[2]->Z - NOT permuted like the main skeleton),
    composed as Rz(rot[2]) @ Ry(rot[1]) @ Rx(rot[0]).

    Found by fitting against the FULLY HIERARCHY-RESOLVED world rotation of 5 secondary-chain
    entries (3/4/5/8/9) against ground truth, not by comparing local bases in isolation - an
    earlier pass of this derivation wrongly treated entries 4/5 as if their parent were identity
    (their real parent is entry 3, which has its own real per-frame rotation) and got a
    different, wrong-in-composition-order answer that regressed entry 3 (previously exact)
    without fully fixing 4/5. Entries 3/4/5 (chain root's grandchildren, one of which - 4/5 - is
    a clean never-animated single-axis rest-only case) now match ground truth to ~0.002 mean /
    0.02 max error (consistent with float32/interpolation noise, not a real remaining bug).
    Entries 8/9 (which have BOTH rot[0] and rot[1] animated simultaneously, on top of a nonzero
    rest rot[2]) still carry a real, larger residual (~0.02-0.03 mean, up to ~0.25 max) that this
    fixed-order-Euler formula doesn't fully explain - flagged as a genuine remaining gap, not
    dismissed as noise. Don't re-attempt fitting this from curve data alone again without also
    tracing FUN_1401db080 directly (this project's rotation conventions have historically been
    fit-then-traced, never fit-and-left, before being fully trusted - see _local_basis's own
    history); the residual most likely means the real composition isn't a plain fixed-order
    3-angle Euler product at all once 2+ axes are simultaneously live.

    Unlike _local_basis, `scale` is accepted but NOT baked into the returned matrix - some
    secondary-chain entries have a real, large, un-tracked rest scale (e.g. entry 3's raw scale
    is a flat (10,10,10), never overridden by any track in any tested motion), and composing
    that into the rotation basis the way _local_basis does for the main skeleton produced a
    magnitude-10 "rotation" matrix, wildly wrong against ground truth (which is unit-magnitude).
    This control-rig chain's world rotation is evidently pure-rotation-only wherever a main-
    skeleton joint snaps to it (flags&3==2) - whatever this chain's own scale field is actually
    for (plausibly an IK reach/length parameter, not vertex scaling), it isn't part of the
    world-rotation matrix that snapped joints copy."""
    return _mat3_mul(_mat3_mul(_rot_z(rot[2]), _rot_y(rot[1])), _rot_x(rot[0]))


def _sample_pose(bind, by_joint, f):
    """Per-frame LOCAL (trans, rot, scale) for every joint key in `bind`: starts from the
    (already instant-override-applied) baseline and overlays whichever keyframe tracks touch
    each joint/channel this frame."""
    pose = {}
    for jidx, base in bind.items():
        trans = list(base['trans'])
        rot = list(base['rot'])
        scale = list(base['scale'])
        for track in by_joint.get(jidx, []):
            kind, axis = CHANNEL_SLOT[track['channel']]
            val = sample_track(track, f)
            if kind == 'trans':
                trans[axis] = val
            elif kind == 'rot':
                rot[axis] = val
            else:
                scale[axis] = val
        pose[jidx] = {'trans': trans, 'rot': rot, 'scale': scale}
    return pose


def _solve_secondary_chain(rec, f):
    """FUN_140391C70's tracks_secondary ("list2") hierarchy-blend loop, per frame - a small
    (Shadow: 11-entry) SEPARATE "control rig" hierarchy, structurally distinct from the main
    84-joint skeleton (confirmed via kh1_mset_motion.parse_secondary_chain: tracks_secondary's
    'joint' field is a position in THIS chain, 0..count-1, not a skeleton joint index - the
    real hierarchy is the static parent-index tree baked into each entry, identical across
    every motion checked). Index 0's parent is -1 (this chain's own root, fed at runtime from
    the actor's own current world transform, DAT_142ef1f50 index 0). Read live: this is NOT
    identity - row1 is always exactly (0,-1,0) regardless of which (differently-facing) actor
    was sampled, while rows 0/2 vary with the actor's yaw. I.e. the "neutral" convention here
    is Rx(180 deg) = diag(1,-1,-1) composed with yaw, not identity - confirmed live after an
    earlier bake (using plain identity) rendered the whole character rotated ~90 degrees (lying
    on its side). Using ROOT_BASIS below as the baseline (no yaw, since a standalone bake has
    no real actor placement) reproduces the fixed part faithfully. Returns
    {index: {'pos':(x,y,z), 'rot':3x3}}."""
    by_chain_pos = {}
    for t in rec['tracks_secondary']:
        by_chain_pos.setdefault(t['joint'], []).append(t)

    local = {}
    for entry in rec['secondary_chain']:
        i = entry['index']
        # Baseline is this entry's own rest scale/rot/trans (see
        # kh1_mset_motion.parse_secondary_chain) - NOT hardcoded identity/zero. Entries with no
        # keyframe track on a given channel this motion (e.g. 4/5's rotation, never animated in
        # any tested motion) still have a real, often-nonzero rest value there that must survive
        # into the composed basis - this is exactly the bug the ground-truth diff found.
        trans = list(entry['trans'])
        rot = list(entry['rot'])
        scale = list(entry['scale'])
        for track in by_chain_pos.get(i, []):
            kind, axis = CHANNEL_SLOT[track['channel']]
            val = sample_track(track, f)
            if kind == 'trans':
                trans[axis] = val
            elif kind == 'rot':
                rot[axis] = val
            else:
                scale[axis] = val
        local[i] = {'trans': trans, 'basis': _local_basis_secondary(rot, scale)}

    world = {}

    def resolve(i):
        if i in world:
            return world[i]
        entry = next(e for e in rec['secondary_chain'] if e['index'] == i)
        parent = entry['parent']
        loc = local[i]
        if parent < 0:
            w = {'pos': _permute_trans(loc['trans']), 'rot': _mat3_mul(ROOT_BASIS, loc['basis'])}
        else:
            p = resolve(parent)
            offset = _mat3_vec(p['rot'], _permute_trans(loc['trans']))
            w = {'pos': (p['pos'][0]+offset[0], p['pos'][1]+offset[1], p['pos'][2]+offset[2]),
                 'rot': _mat3_mul(p['rot'], loc['basis'])}
        world[i] = w
        return w

    for entry in rec['secondary_chain']:
        resolve(entry['index'])
    return world


def _target_chain_index_from_next_flags(next_flags):
    """The bits21-22==0x200000 branch (see _solve_main_skeleton) reads a SECOND, differently
    positioned bit-packed chain-index field - from the NEXT joint's flags dword (jidx+1), at
    bits 11-19 plus bit 28 (vs. chain_index_from_flags's bits 2-10 plus bit 11, read from the
    joint's OWN flags) - traced from FUN_1403900B0's disassembly around 0x140391260."""
    part1 = next_flags & 0xFF800
    part2 = (next_flags >> 8) & 0x100000
    return ((part1 | part2) >> 0xB) - 1


def _simple_aim_basis(target_local, origin_local):
    """Port of FUN_14038fc20's "if (param_6 == NULL)" path - the bits21-22==1 branch's own
    rotation ("Branch A" in the disassembly, e.g. Shadow's joints 0/2/25 - the whole-body root,
    leg hip, and torso/neck root). Re-decompiling the FULL FUN_1403900B0 this session (not
    just branch fragments) showed Branch A does its OWN self-contained call into
    FUN_14038fc20 with no bend matrix (len2=0, a single-bone look-at, not 2-bone IK) - it does
    NOT fall through to share the uvar10 dispatch below the way an earlier pass of this code
    assumed. Missing this meant joint 25 (and everything hanging off it - the entire
    spine/neck/head/arm chain) fell through to plain pass-through instead of actively aiming,
    which was the actual source of the torso/head orientation being wrong even after the
    ROOT_BASIS and leg-IK fixes. Same basis convention as _two_bone_ik (no pole - traced from
    the disassembly that these joints' own uvar10 is never 3, the only case that supplies
    one), just without the reorient/bend step since there's no second bone. Re-checked the
    exact disassembly again this session (not just the general pattern): the "no pole" branch
    only has ONE cross-product call (scratch=cross(dir,perp)) - it does NOT recompute row1 via
    a second cross the way the "with pole" branch does. That second cross exists there because
    an arbitrary supplied pole isn't guaranteed perpendicular to dir; the algebraic
    perp=(-dir.y,dir.x,0) IS already perpendicular to dir by construction (dot product is
    always exactly 0), so it's used directly as row1 with no further correction. An earlier
    version of this function wrongly added that second cross anyway, copying the with-pole
    pattern - a real bug, not just an approximation, found while chasing a reported head/torso
    orientation flip."""
    d = _vec3_sub(target_local, origin_local)
    dist = math.sqrt(d[0]*d[0] + d[1]*d[1] + d[2]*d[2]) or 1.0
    direction = (d[0]/dist, d[1]/dist, d[2]/dist)
    perp = _vec3_normalize((-direction[1], direction[0], 0.0))
    scratch = _vec3_normalize(_vec3_cross(direction, perp))
    return [direction[0], direction[1], direction[2],
            perp[0], perp[1], perp[2],
            scratch[0], scratch[1], scratch[2]]


def _two_bone_ik(target_local, origin_local, len1, len2, flip=False, twist=0.0):
    """Port of FUN_14038fc20 (the bits21-22 in {2,3} branch's 2-bone IK solver, e.g. Shadow's
    joints 5/6 and 15/16 - the thigh/shin bones): classic law-of-cosines 2-bone IK, all done
    in the parent's local space (target_local/origin_local both already parent-relative, same
    convention as elsewhere in this dispatcher). No pole vector is used - traced from the raw
    disassembly that Shadow's joints 5/15/50/69 always hit the "param_9 == NULL" branch - so the
    perpendicular reference for building the aim basis is derived algebraically from the
    direction itself ((-dir.y, dir.x, 0), always perpendicular to dir), not a fixed world-up
    constant (that constant is FUN_1403900B0's OWN inline aim-IK code for uvar10==1/joints
    4/14/49/68, a DIFFERENT routine with a different convention - see _aim_basis).

    `twist`: FUN_14038fc20 takes its own extra twist angle (param_7), composed onto the aim
    basis BEFORE the reorient/bend step - found via live Cheat Engine capture at this
    function's two call sites in FUN_1403900B0 (breakpoints on the CALL instructions
    themselves, reading param_7 off the stack): legs (bits21-22==2, joints 5/15) get an exact
    +/-pi/2 constant (sign mirrors L/R - matches the sign of the joint's own raw bind trans[2],
    the same axis that drives world X per _local_basis's convention), while arms
    (bits21-22==3, joints 50/69) get exactly 0. Not stateful/per-frame like Branch B's twist -
    every captured hit across many frames gave the identical constant per joint. Composed the
    same way as Branch B's twist (thunk_FUN_1400e6ac0 -> FUN_1401db4d0, row-vector-postmultiply
    convention, verified transpose-equivalent to this project's own _rot_x(-twist) - see
    kh1_bake_animation.py's uvar10==1 comment for the full derivation) - i.e. basis @
    _rot_x(-twist), applied to the SAME basis the reorient step later composes onto.

    `flip`: also live-verified at the same call sites (register R9, param_4) - legs are always
    False, arms are always True. This is the real source of the tuner's "flip knee bend
    direction" toggle visibly controlling the arms instead of the knees: legs and arms share
    the exact same code path (see _solve_main_skeleton), but need opposite flip constants, not
    one global toggle.

    Returns (own_basis, child_bend): own_basis is this joint's (the thigh's) own local
    rotation basis - direction-to-target with an added "reorient" correction so the actual
    bent chain (not a straight line) reaches the target - and child_bend is an ADDITIONAL
    local rotation the immediate child (the shin) must use INSTEAD of its own keyframe
    rotation, composed on top of this joint's world rotation (mirrors the disassembly writing
    directly into the next joint's (jidx+1) working-pose slot from within this same branch).
    Matrix layout matches this engine's own convention throughout this branch (row0=[c,s,0],
    row1=[-s,c,0], row2=[0,0,1] for a "Z-rotation-like" matrix - the transpose of the
    textbook layout, but self-consistent since it's only ever composed with matrices built the
    same way here)."""
    d = _vec3_sub(target_local, origin_local)
    dist = math.sqrt(d[0]*d[0] + d[1]*d[1] + d[2]*d[2]) or 1.0
    direction = (d[0]/dist, d[1]/dist, d[2]/dist)
    # Re-checked against the exact disassembly this session (see _simple_aim_basis): the "no
    # pole" branch uses perp directly as row1, with no second cross-product - it's already
    # perpendicular to direction by construction, unlike an arbitrary supplied pole. An earlier
    # version of this function wrongly recomputed row1 via cross(scratch,direction) anyway.
    perp = _vec3_normalize((-direction[1], direction[0], 0.0))
    scratch = _vec3_normalize(_vec3_cross(direction, perp))
    basis = [direction[0], direction[1], direction[2],
             perp[0], perp[1], perp[2],
             scratch[0], scratch[1], scratch[2]]
    if twist:
        basis = _mat3_mul(basis, _rot_x(-twist))

    c = (dist*dist - len1*len1 - len2*len2) / (2*len1*len2)
    c = max(-1.0, min(1.0, c))
    s = math.sqrt(max(0.0, 1.0 - c*c))
    if flip:
        s = -s

    raw_c2 = c*len2 + len1
    raw_s2 = -(s*len2)
    mag2 = math.sqrt(raw_c2*raw_c2 + raw_s2*raw_s2) or 1.0
    c2, s2 = raw_c2/mag2, raw_s2/mag2
    reorient = [c2, s2, 0, -s2, c2, 0, 0, 0, 1]
    own_basis = _mat3_mul(basis, reorient)

    child_bend = [c, s, 0, -s, c, 0, 0, 0, 1]
    return own_basis, child_bend


def _bind_pose_world(joints_by_idx):
    """Seeds the previous-frame world-rotation state used by uvar10==1's stateful twist (see
    _solve_main_skeleton): FUN_14038f550 (the motion-switch handler) unconditionally recopies
    every joint's raw bind pose into the persistent per-actor world buffer before any per-frame
    dispatch runs, so frame 0's "previous frame" twist source is plain parent-composed FK using
    each joint's own bind trans/rot/scale - no aim/IK/pass-through dispatch involved at all."""
    world = {}

    def resolve(jidx):
        if jidx in world:
            return world[jidx]
        j = joints_by_idx[jidx]
        parent = j['parent']
        is_root = parent >= len(joints_by_idx) or parent < 0 or parent not in joints_by_idx
        parent_w = {'pos': (0.0, 0.0, 0.0), 'rot': _IDENTITY3} if is_root else resolve(parent)
        rot = _mat3_mul(parent_w['rot'], _local_basis(j['rot'], j['scale']))
        offset = _mat3_vec(parent_w['rot'], _permute_trans(j['trans']))
        pos = (parent_w['pos'][0]+offset[0], parent_w['pos'][1]+offset[1], parent_w['pos'][2]+offset[2])
        w = {'pos': pos, 'rot': rot}
        world[jidx] = w
        return w

    for jidx in joints_by_idx:
        resolve(jidx)
    return world


def _solve_main_skeleton(rec, pose, joints_by_idx, prev_world=None):
    """FUN_1403900B0's per-joint dispatch, as far as decoded (see
    mdls_mset_model_and_animation_format.md §3.7). Two independent things are decided per
    joint based on its flags (kh1_mset_motion.parse_joint_flags):

    ROTATION - one of: normal FK (own local rotation composed onto the parent's world
    rotation), pass-through (parent's world rotation unchanged, own rotate data never read),
    or a snap to one of the secondary chain's world rotations (own rotate data never read
    either).

    POSITION - bits21-22==1 joints snap directly to a secondary-chain target position (see
    _target_chain_index_from_next_flags). bits21-22==0 joints run their own position dispatch
    keyed off THIS joint's own flags (same bit-layout as _target_chain_index_from_next_flags,
    just applied to the joint's own flags dword instead of the next joint's): a target-index
    field selects a secondary-chain target position if present (rare - confirmed only joint 0
    uses this for a sampled motion), otherwise falls through to ordinary parent-composed FK
    translate (confirmed the overwhelming majority - 71/78 of Shadow's bits21-22==0 joints).

    A bit23 case was investigated and reverted this session: the disassembly reads the joint's
    own last-frame world position and inverse-then-forward transforms it through a reference
    joint's matrix, which looked like "freeze at bind pose forever" - but algebraically that
    reduces to ordinary parent-composed FK using the bind-pose local translate (ignoring any
    translate-channel track override, a no-op for Shadow since no such tracks exist on affected
    joints), NOT a frozen absolute world position. Implementing the latter caused a visibly
    disconnected floating limb (parent moves via chain-snap/IK, frozen-absolute child doesn't
    follow) - confirmed wrong by the user's screenshot, backed out.

    Branch bits21-22 in {2,3} (joints 5/6 and 15/16 - the thigh/shin bones) is a genuine
    2-bone IK solve (FUN_14038fc20, law-of-cosines elbow/knee bend) - see _two_bone_ik().
    Re-decompiling the FULL function this session (not just the branch fragments traced
    earlier) showed this branch is a TOP-LEVEL alternative to the uvar10 dispatch below, not
    something that falls through to share it - an earlier pass of this code wrongly ran the
    same uvar10/pass-through/chain-snap logic for these joints too (silently treating joint
    5/15 as pass-through, inheriting the parent's rotation unchanged - definitely wrong given
    they need their own IK-aimed orientation)."""
    flags = rec['joint_flags']
    secondary = _solve_secondary_chain(rec, pose['__frame__'])
    children_of = {}
    for jidx2, j2 in joints_by_idx.items():
        children_of.setdefault(j2['parent'], []).append(jidx2)

    world = {}
    bend_override = {}  # child joint idx -> local rotation basis, set by a 2-bone-IK parent

    def resolve(jidx):
        if jidx in world:
            return world[jidx]
        j = joints_by_idx[jidx]
        parent = j['parent']
        p = pose[jidx]
        f = flags[jidx] if jidx < len(flags) else 0
        bits2122 = (f >> 21) & 3
        uvar10 = f & 3

        is_root = parent >= len(joints_by_idx) or parent < 0 or parent not in joints_by_idx
        if is_root:
            parent_w = {'pos': (0.0, 0.0, 0.0), 'rot': _IDENTITY3}
        else:
            parent_w = resolve(parent)

        if jidx in bend_override:
            # This joint is the "shin" child of a 2-bone-IK "thigh" joint resolved just above -
            # its own rotation dispatch (whatever its flags would otherwise say) is entirely
            # bypassed in favor of the bend angle the parent's IK solve already computed.
            rot = _mat3_mul(parent_w['rot'], bend_override[jidx])
        elif bits2122 == 1:
            # Branch A's own aim rotation (see _simple_aim_basis) - a single-bone look-at
            # toward the SAME target used for this branch's position snap (next joint's
            # flags), NOT the shared uvar10 dispatch. Missing this made joint 0 (whole body),
            # joint 2 (leg hip), and joint 25 (torso/neck root) all silently pass-through
            # their parent's rotation instead of actively aiming - the actual source of the
            # torso/head orientation bug found this session (after ROOT_BASIS and the leg IK
            # were already fixed).
            next_f = flags[jidx+1] if jidx+1 < len(flags) else 0
            target_idx = _target_chain_index_from_next_flags(next_f)
            if target_idx in secondary:
                parent_rot_t = _mat3_transpose(parent_w['rot'])
                target_local = _mat3_vec(parent_rot_t, _vec3_sub(secondary[target_idx]['pos'], parent_w['pos']))
                origin_local = _permute_trans(p['trans'])
                aim = _simple_aim_basis(target_local, origin_local)
                rot = _mat3_mul(parent_w['rot'], aim)
            else:
                rot = _mat3_mul(parent_w['rot'], _local_basis(p['rot'], p['scale']))
        elif bits2122 in (2, 3):
            children = children_of.get(jidx, [])
            grandchildren = children_of.get(children[0], []) if children else []
            if children and grandchildren:
                child_idx, grandchild_idx = children[0], grandchildren[0]
                len1 = math.sqrt(sum(c*c for c in joints_by_idx[child_idx]['trans']))
                len2 = math.sqrt(sum(c*c for c in joints_by_idx[grandchild_idx]['trans']))
                target_idx = flags[jidx+2] if jidx+2 < len(flags) else 0
                target_idx = _target_chain_index_from_next_flags(target_idx)
                if target_idx in secondary and len1 > 1e-4 and len2 > 1e-4:
                    parent_rot_t = _mat3_transpose(parent_w['rot'])
                    target_local = _mat3_vec(parent_rot_t, _vec3_sub(secondary[target_idx]['pos'], parent_w['pos']))
                    origin_local = _permute_trans(p['trans'])
                    # Live-verified (see _two_bone_ik's docstring): legs (bits2122==2) get a
                    # fixed +/-pi/2 twist whose sign mirrors L/R and flip=False; arms
                    # (bits2122==3) get twist=0 and flip=True - legs and arms share this exact
                    # code path but need opposite constants, which a single global toggle can
                    # never represent. The L/R sign comes from the PARENT joint's raw bind
                    # trans[2] - this joint's (5/15) own trans is exactly (0,0,0) (same
                    # zero-offset-hub pattern as other control joints), so checking jidx's own
                    # trans here always read 0 >= 0 == True and silently gave BOTH legs the
                    # same twist sign - a real bug caught by the user still seeing wrong-facing
                    # feet after the first cut of this fix.
                    if bits2122 == 2:
                        side_sign = 1.0 if joints_by_idx[parent]['trans'][2] >= 0 else -1.0
                        twist = -side_sign * (math.pi / 2)
                        flip = False
                    else:
                        twist = 0.0
                        flip = True
                    own_basis, child_bend = _two_bone_ik(target_local, origin_local, len1, len2,
                                                          flip=flip, twist=twist)
                    rot = _mat3_mul(parent_w['rot'], own_basis)
                    bend_override[child_idx] = child_bend
                else:
                    rot = _mat3_mul(parent_w['rot'], _local_basis(p['rot'], p['scale']))
            else:
                rot = _mat3_mul(parent_w['rot'], _local_basis(p['rot'], p['scale']))
        elif uvar10 == 2:
            chain_idx = chain_index_from_flags(f)
            rot = secondary[chain_idx]['rot'] if chain_idx in secondary else parent_w['rot']
        elif uvar10 == 0 and (f >> 25) & 1 and not ((f >> 24) & 1):
            rot = parent_w['rot']  # pass-through: own rotate data ignored entirely
        elif uvar10 == 1:
            # Aim toward a secondary-chain target (same chain-index field as uvar10==2's snap),
            # plus a "twist" correction composed on top - joints 4/14/49/68 use this. See
            # _aim_basis(). The twist is NOT derived from this joint's own rotate track (an
            # earlier pass of this code used rot[2]/RotX(rot[2]), which was wrong on two counts,
            # both confirmed via live Cheat Engine capture at FUN_1403900B0's twist-load site,
            # 0x140390f64, while a Shadow was on screen):
            #  1. The value read is this SAME joint's own PREVIOUS FRAME world-rotation matrix,
            #     row2's first component (offset+0x20 into the persistent per-actor world
            #     buffer at instance+0x1b0) - a genuinely stateful, frame-sequential dependency,
            #     not anything sampled from this frame's own keyframe tracks. Live values seen
            #     for Shadow were large (joint4 ~-31 deg, joint14 ~171 deg, joint49 ~92 deg,
            #     joint68 ~-112 deg), ruling out "it's usually ~0 so it barely matters".
            #  2. The angle-to-matrix builder (thunk_FUN_1400e6ac0, via its row-transform helper
            #     FUN_1400e5ad0) applies the twist using a row-vector-postmultiply convention
            #     whose matrix layout is the TRANSPOSE of this project's own _rot_x(); composed
            #     through FUN_1401db4d0 (this project's ordinary parent@child convention) that
            #     transpose is equivalent to _rot_x(-twist), i.e. the angle must be negated.
            # prev_world holds the previous frame's fully-resolved world rotations (seeded for
            # frame 0 from plain bind-pose FK - see _bind_pose_world - matching FUN_14038f550
            # recopying raw bind pose into this same buffer on motion switch, before any
            # per-frame dispatch runs).
            chain_idx = chain_index_from_flags(f)
            if chain_idx in secondary:
                aim = _aim_basis(secondary[chain_idx]['pos'], _permute_trans(p['trans']), parent_w)
                twist = prev_world[jidx]['rot'][6] if prev_world and jidx in prev_world else 0.0
                rot = _mat3_mul(parent_w['rot'], _mat3_mul(aim, _rot_x(-twist)))
            else:
                rot = _mat3_mul(parent_w['rot'], _local_basis(p['rot'], p['scale']))
        else:
            rot = _mat3_mul(parent_w['rot'], _local_basis(p['rot'], p['scale']))

        # bit23 ("hold last frame's own position") was tried and reverted this session: it
        # reads the joint's own LAST-FRAME position from the persistent world buffer and
        # inverse-then-forward transforms it through a reference joint's matrix - but critically
        # that reference matrix is captured ONCE (last frame's snapshot) for the inverse and
        # implicitly re-composed against the reference's CURRENT-frame transform for the
        # forward half, which is NOT a no-op cancellation like the other branches' identical-
        # matrix-both-times pattern. Net effect (worked out algebraically): equivalent to
        # ordinary parent-composed FK using the joint's bind-pose local translate - i.e. a
        # no-op for any joint with no translate-channel track (confirmed true for joint 3 in
        # every motion checked), NOT "freeze at an absolute bind-pose world position" as an
        # earlier version of this code wrongly modeled it (that produced a visibly disconnected
        # floating limb - the parent moves via chain-snap/IK but the frozen-absolute child
        # doesn't follow, exactly the "much worse" regression this fix undoes).
        if bits2122 == 1:
            next_f = flags[jidx+1] if jidx+1 < len(flags) else 0
            target_idx = _target_chain_index_from_next_flags(next_f)
            pos = secondary[target_idx]['pos'] if target_idx in secondary else parent_w['pos']
        elif bits2122 == 0 and _target_chain_index_from_next_flags(f) in secondary:
            pos = secondary[_target_chain_index_from_next_flags(f)]['pos']
        else:
            offset = _mat3_vec(parent_w['rot'], _permute_trans(p['trans']))
            pos = (parent_w['pos'][0]+offset[0], parent_w['pos'][1]+offset[1], parent_w['pos'][2]+offset[2])

        w = {'pos': pos, 'rot': rot}
        world[jidx] = w
        return w

    for jidx in joints_by_idx:
        resolve(jidx)
    return world


def bake(mset_path, mdls_path, motion_offset, out_path, frame_stride=1):
    data = open(mset_path, 'rb').read()
    rec = parse_motion_record(data, motion_offset)

    joints = parse_mdls_full(mdls_path)[0]
    joints_by_idx = {j['idx']: j for j in joints}
    bind = {j['idx']: {'trans': list(j['trans']), 'rot': list(j['rot']), 'scale': list(j['scale'])}
            for j in joints}

    # Apply this motion's one-shot (joint, channel, value) overrides on top of raw bind pose,
    # once, before per-frame keyframe sampling - this mirrors FUN_14038f550 (called on motion
    # switch, before FUN_140391C70's per-frame track sampling begins). See
    # kh1_mset_motion.py's parse_instant_overrides(). Note: for joints whose flags mean their
    # own rotate data is never read (pass-through / chain-snap, see _solve_main_skeleton),
    # overrides to the rotate channels are harmless but inert - this is expected.
    for ov in rec['instant_overrides']:
        if ov['joint'] not in bind:
            continue
        kind, axis = CHANNEL_SLOT[ov['channel']]
        bind[ov['joint']][kind][axis] = ov['value']

    by_joint = {}
    for t in rec['tracks']:
        by_joint.setdefault(t['joint'], []).append(t)

    frames_out = []
    n_frames = rec['frame_count']
    # uvar10==1's twist correction is stateful (see _solve_main_skeleton) - it reads each
    # affected joint's OWN world rotation from the previous frame, so frames must be resolved
    # in strict sequence with that state carried forward, seeded from plain bind-pose FK
    # (see _bind_pose_world) to match FUN_14038f550's behavior on motion switch.
    prev_world = _bind_pose_world(joints_by_idx)
    for f in range(0, n_frames + 1, frame_stride):
        pose = _sample_pose(bind, by_joint, f)
        pose['__frame__'] = f
        world = _solve_main_skeleton(rec, pose, joints_by_idx, prev_world)
        frames_out.append(world)
        prev_world = world
        if f % 20 == 0:
            print(f"baked frame {f}/{n_frames}")

    out = {
        'frame_count': n_frames,
        'fps': rec['fps'],
        'frames': [[{'pos': list(frames_out[fi][j['idx']]['pos']), 'rot': frames_out[fi][j['idx']]['rot']}
                    for j in joints] for fi in range(len(frames_out))],
    }
    with open(out_path, 'w') as fh:
        json.dump(out, fh)
    print(f"wrote {len(frames_out)} frames -> {out_path} ({len(json.dumps(out))} bytes)")


if __name__ == '__main__':
    bake(sys.argv[1], sys.argv[2], int(sys.argv[3], 16), sys.argv[4])
