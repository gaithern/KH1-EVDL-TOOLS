# KH1 `.mdls` model + `.mset` animation format

A working-notes writeup of reverse-engineering KH1's 3D model and skeletal animation
formats, done live against the running EGS build (Ghidra static analysis + Cheat Engine
live memory tracing). Companion to `mdls_bd_format_and_ai.md` (the `.bd` behavior-script
format) — same enemy (`xa_ex_2020` = Shadow), different file types.

> **Build note:** all `0x140…` executable addresses here are Steam-build provenance
> (same convention as the `.bd` doc). The `.mdls`/`.mset` file formats themselves are
> presumably shared across builds, though this wasn't independently re-verified on EGS
> beyond confirming the tool works against EGS's `.mdls`/`.mset` data files.

---

## 1. `.mdls` — model (skeleton + mesh + textures) — CONFIRMED WORKING

OpenKH's PS2-era `OpenKh.Kh1/Mdls.cs` parses this format for the original PS2 release.
It works **completely unmodified** against the EGS build's `.mdls` files — same `MOBJ`
magic at fixed offset `0x80`, same header layout, same joint/mesh-packet/texture layout.
Ported to Python in `kh1_mdls_parse.py` in this repo.

- **Header** at `0x80`: `MOBJ` magic (`0x4A424F4D`), then `TextureInfoOffset/Size`,
  `TextureDataOffset/Size`, `ClutOffset/Size`, `ModelOffset/Size`, `UnkOffset/Size`.
- **Joints**: `JointCount`, `JointInfoOffset`, `BoneDataOffset`, `MeshCount`, then
  `JointCount` × 48-byte records: scale(3f), index(u32), rotate(3f, radians), padding,
  translate(3f), a `HierarchyBitfield` (u32) whose low 10 bits are `ParentId` (`0x3FF`
  = no parent / root). This field order (scale, then rotate, then translate) is also
  what confirms the `.mset` channel-type correction in §2.5 — `FUN_1401d5b10` (the
  bind-pose setup routine) reads these three fields in this exact order and passes
  them to the same `FUN_1401db080` matrix-builder that the animation sampler uses.
- **Bind-pose forward kinematics** (confirmed correct visually — the reconstructed
  skeleton is an unmistakable, correctly-proportioned Shadow silhouette): local matrix
  = `Translate · RotZ · RotY · RotX`, composed down the parent chain. This rotation
  order was a first guess that turned out right.
- **Mesh packets**: a PS2 VIF-unpack triangle-strip format (ported directly from
  `Mdls.cs`'s `UnpackData()`). Per-vertex: normal(3f), `MatrixId`(u32) → resolved to a
  joint via a per-packet weight-matrix table, translate(3f, **joint-local**, not
  world), weight(f32, unused — single-weight only), UV(2f).
- **Textures**: CLUT/palette-indexed, 128×128, with the PS2 pixel-swizzle correction
  (`IndexFix()` in `Mdls.cs`) needed before palette lookup. Confirmed visually —
  decoded texture 0 clearly shows Shadow's glowing yellow eye.

Shadow (`xa_ex_2020.mdls`): 84 joints, 1422 vertices / 794 faces across 3 textures.

---

## 2. `.mset` — animation — CRACKED, some interpolation details still shaky

### 2.1 Container format

`.mset` files share the game's generic resource-loading machinery with `.mdls` (same
type-dispatch table, `FUN_1402860A0` is the `.mset`-specific handler). After an
outer 128-byte header (`field0=3`, `field@4=0x80`=payload offset), the payload is a
**TLV chunk sequence**: `[4-byte magic][4-byte size][data...]`, walked via
`FUN_1401DF0F0`/`FUN_1401DF170`. Recognized magics: `MOBJ`, `MENV`, `BONE`, `MMTN`,
`TEXA`, `URSL`. Motion data lives in the `MMTN` chunk. No relocation/pointer-patching
is needed to read this chunk statically — see §2.4.

### 2.2 Motion lookup (per motion ID) — **NOT FULLY CRACKED**

Each animated actor has a per-actor field (found at `actor_render_instance + 0x1D4` on
the *rendering/animation-instance* struct — **not** the AI/behavior-script actor
struct; these are two separate pools, see §3) that resolves (via the handle scheme in
§2.4) to an array of per-motion-ID handles. Indexing that array by motion ID and
resolving again gives the 32-byte motion record (§2.3).

**This ID→offset table was never directly decoded.** Everything confirmed about the
record format (§2.3) came from capturing an *already-resolved* record pointer live via
a breakpoint on `FUN_1403948C0` (mid-way through `FUN_1402A0350`, the "switch to this
motion" function) — i.e. we know what a resolved record looks like, but not how to
compute "motion ID 204 → file offset X" ourselves without the live game. Direct reads
of the index array (`actor+0x1D4` resolved, then `+id*4`) produced inconsistent/junk
values in a couple of attempts — worth another pass with a cleaner live capture
(breakpoint the actual second `FUN_14038adc0` call inside `FUN_1402A0350` and log both
the input ID and the output pointer together, rather than reading the array cold).

### 2.3 Motion record (32 bytes) — CONFIRMED BYTE-FOR-BYTE AGAINST THE FILE

Verified by reading a live-captured record's memory and finding the **exact same
bytes**, field-for-field, at file offset `0x35B50` in `xa_ex_2020.mset` (search for the
20-byte prefix `00000000 <frame_count:u32> 0000704200000000 <joint_count:u32>` — the
`0x42700000` is a shared `60.0f` fps constant present in every record; there are 52 of
these in Shadow's file, i.e. 52 distinct motions).

| offset | field |
|---|---|
| `0x00` | 0 (unknown/reserved) |
| `0x04` | frame count (i32) |
| `0x08` | fps, always `60.0f` in observed samples |
| `0x0C` | flags (i32) |
| `0x10` | joint count — **matches the skeleton's joint count exactly** (84 for Shadow); a good sanity check when hunting for records |
| `0x14` | handle → some block (unexplored) |
| `0x18` | count1 (track-list 1 length) |
| `0x1C` | offset → track-list 1 (self-relative to record start) |
| `0x20` | count2 (track-list 2 length) |
| `0x24` | offset → track-list 2 |
| `0x28` | offset → shared curve/keyframe array |
| `0x2C` | count3 (unexplored, ~hierarchy-blend related) |
| `0x30` | offset → another block (unexplored) |
| `0x34` | count4 |
| `0x38` | offset → another block (unexplored) |
| `0x3C` | offset → another block (unexplored) |

All offset fields at `0x14/0x1C/0x24/0x28/0x30/0x38/0x3C` are **self-relative to the
record's own start** — confirmed both live (handles resolve to addresses a small,
fixed number of bytes past the record) and statically (the raw file bytes at those
positions are plain small integers matching the live-decoded relative offsets exactly).

### 2.4 The "handle" scheme (why no relocation table is needed)

`FUN_14038ADC0(handle) → FUN_14038AF40`: `region_bases[(handle & 0x7FFFFFFF) >> 25] |
(handle & 0x1FFFFFF)`. `region_bases` is a table of up to ~64 loaded-resource base
addresses at `DAT_142ee3980` (region 0 = the exe's own image base, `0x140000000`).

Critically: **the on-disk "handle" values are just plain small relative offsets** — the
loader doesn't scramble them, it just uniformly OR's in a region-tag at load time. That
means everything in a motion record (which only ever self-references its own loaded
blob) can be read as plain relative offsets directly from the raw file, no relocation
table required. (`MOBJ`/`MENV` chunks, which reference *external* shared sub-resources
like textures, DO go through a real relocation pass — `FUN_1401D6B30` — but that
function is a no-op for `MMTN` chunks, confirming motion data needs none of that.)

### 2.5 Track descriptor (6 bytes)

| offset | field |
|---|---|
| `0x0` | joint index (u16) — matches the skeleton's joint indices directly |
| `0x2` | flags byte: low nibble = **channel type** (below); bits 4-5 = pre-first-keyframe extrapolation mode; bits 6-7 = post-last-keyframe extrapolation mode — **CONFIRMED**, see §2.7 |
| `0x3` | keyframe count for this track (u8) |
| `0x4` | keyframe start index (u16) — index into the **shared curve array** (`record+0x28` resolved), stride 16 bytes |

**Channel types** — the jump-table dispatch in `FUN_140391C70`'s disassembly (table at
`0x140392510`/`0x140392534`, indexed by `channel-1`) proves channels 1-3, 4-6, 7-9
write to three distinct, non-overlapping 12-byte regions of a 64-byte per-joint output
slot (`-0x4`, `+0x10`, `+0x14` relative offsets respectively) — three genuinely
separate quantities. **Which physical quantity each group is was wrong in an earlier
pass of this doc and is now corrected and independently confirmed:**

- **1-3 = scale** X/Y/Z
- **4-6 = rotate** X/Y/Z (radians; angle-wrapped to `±π` in the sampler)
- **7-9 = translate** X/Y/Z

(Previously documented as 1-3=translate/7-9=scale — that was an unproven assumption
based only on memory-offset *order* within the output slot, which the doc even flagged
as unverified at the time. It was backwards.)

**How this was confirmed:** every motion record's track data is actually split across
*two* track lists per §2.3's field table — `list1`/`count1` (`record+0x1C`/`0x18`,
already covered above: writes straight into the runtime per-joint pose buffer used for
skinning) and a second list, `list2`/`count2` (`record+0x24`/`0x20`), previously
unexplored. Tracing `list2`'s consumer in `FUN_140391C70` (jump table at `0x392534`,
same channel groups but a different store target) shows it writes into a *different*
40-byte-per-joint scratch buffer living inside the motion record itself
(`record+0x30`), which then feeds two calls: `FUN_1401db080` (builds a 64-byte local
transform from a scale/rotate/translate triple) and `FUN_1401db4d0` (a generic
parent-child hierarchy-compose helper used everywhere in this binary, not distinctive
on its own). `FUN_1401db080` writes its **first** argument to the transform's diagonal
entries (indices 0/5/10) and its **third** argument to the translation-column entries
(12/13/14). The proof this is (scale, rotate, translate) and not the reverse: the only
*other* caller of `FUN_1401db080` is `FUN_1401d5b10`, the skeleton's bind-pose setup
routine, which reads directly from `.mdls`'s own joint fields — confirmed unambiguous
in §1 as scale (offset 0), rotate (offset 0x10), translate (offset 0x20) — and passes
them to `FUN_1401db080` in that same argument-position order. Since bind-pose setup
proves arg1=scale/arg3=translate beyond doubt, and the animation sampler's `list2`
path calls the identical function with the identical channel-group-to-argument
mapping, channels 1-3 must be scale and 7-9 must be translate for `list2` — and since
both track lists (`list1`/`list2`) share the same channel-type encoding (same two jump
tables, same 3-groups-of-3 structure, just different store targets), the mapping is
the same for `list1` too.

This also resolves the earlier suspicion cleanly: channel 7-9 values were flagged as
"strange for a scale multiplier" (observed up to `±57` at the time); a full-file scan
this session found channel 7-9 (now translate) ranging up to **`±473`** across
Shadow's 52 motions — obviously a position, never a plausible scale factor. Channel
1-3 (now scale) has never been observed with real data in any of Shadow's 52 motions
(all use bind-pose scale, `1.0`), consistent with it not showing up before either.

Implemented in `kh1_bake_animation.py`'s `CHANNEL_SLOT` mapping; `kh1_mdls_parse.py`'s
`parse_joints()` now also reads the bind-pose scale field (previously ignored, assumed
uniformly `1.0`) so baked frames have a correct scale default for joints/frames a given
motion doesn't animate scale for.

**`list2`/`record+0x30`'s own purpose is still not fully pinned down** — it's a
separate scratch buffer from the main skinning pose, always covering the same handful
of joints (2 through 9 or 10) and a constant `count3` (`record+0x2C`) of `11` across
every one of Shadow's 52 motions, regardless of animation — a strong signature of a
fixed skeletal chain tied to engine mechanics rather than ordinary per-motion content.
Plausible: some kind of secondary/IK chain setup or a root-adjacent bone-chain
mechanism. Not required for the channel-type fix above (which only needed
`FUN_1401db080`'s calling convention, independently nailed down via the bind-pose
caller), but worth revisiting if this joint range turns out to need special handling
in the viewer.

**Correction, same session, after actually re-viewing the fix:** an earlier version of
`kh1_mset_motion.py`'s `parse_motion_record()` merged `list1` and `list2` into one
`'tracks'` list, and the baker applied both to the same per-joint pose. This was the
*actual* cause of the "still not right" visuals (a badly stretched limb on exactly the
joints `list2` touches) — not the channel 1-3/7-9 mapping. Fixed by keeping `list1`
(`'tracks'`) and `list2` (`'tracks_secondary'`) separate in `kh1_mset_motion.py`, and
having the baker use only `'tracks'` (`list1`) for the render skeleton, since that's
the one `FUN_140391C70` actually writes into the runtime skinning-pose buffer.

**This also means the channel 1-3/7-9 correction above turned out to be moot for
Shadow specifically**: a full scan of all 52 motions found `list1` never uses channels
1-3 or 7-9 in *any* of them — every real occurrence of those channels is in `list2`.
The mapping fix is still correct (proven independently via the bind-pose caller, not
retracted) and may matter for other enemies' `.mset` files whose `list1` does use
those channels, but it produces no visible difference for Shadow once `list2` is
correctly excluded from the render skeleton. Don't be surprised if a before/after
comparison built around the channel swap alone shows nothing for this particular file
— the `list1`/`list2` merge is the fix that actually mattered here.

### 2.6 Keyframe record (16 bytes, in the shared curve array)

| offset | field |
|---|---|
| `0x0` | packed `(frame << 16) \| flag` (i32) — **shift is 16, not 8**; frame is a signed int (small negative "anchor" keyframes before frame 0 are normal) |
| `0x4` | value (f32) |
| `0x8` | out-tangent (f32) |
| `0xC` | "in-tangent of next" (f32) — despite the name, this is read as the **outgoing** tangent for interpolating *away from* this keyframe (see §2.7) |

The low byte of `flag` **is** the interpolation mode for the segment starting at this
keyframe (confirmed from the disassembly: `TEST CL,CL / JZ step`, `CMP EAX,1 / JZ
linear`, else Hermite) — not a bit-shifted field elsewhere. (First attempt wrongly bit
-shifted a *different* byte and got step mode for almost everything, causing the
initial "unnatural, jerky" render — flag values observed: `0`=step, `1`=linear,
`2`=Hermite, with `2` by far the most common.)

### 2.7 Interpolation sampler (`FUN_14038F820`)

Binary-searches the sorted keyframe array (each entry's frame `>>16`) for the pair
bracketing the query frame. Given bracketing keyframes `a` (earlier) and `b` (later),
`t0=a.frame`, `t1=b.frame`, `iv=t1-t0`, `s=(frame-t0)/iv`:

- mode `0` (step): return `a.value`
- mode `1` (linear): return `a.value + (b.value - a.value) * s`
- else (Hermite) — **traced register-by-register, not guessed**:
  `h00(s)*a.value + h10(s)*iv*a.in_tan_next + h01(s)*b.value + h11(s)*iv*b.out_tan`
  where `h00/h10/h01/h11` are the standard cubic Hermite basis functions. Two real
  bugs were caught and fixed while deriving this: (1) the tangent *fields* were
  mismatched (used `a.out_tan`/`a.in_tan_next` instead of `a.in_tan_next`/`b.out_tan`),
  and (2) the tangent terms need scaling by the interval `iv` — using them as raw
  per-unit-`s` slopes produced smooth-but-wrong curves ("better but still not right").
  Re-verified this session by tracing the raw disassembly all the way through the
  Hermite block (`0x14038fae7`-`0x14038fba4`): the coefficients resolve exactly to
  `h00/h10/h01/h11` given the shared constants at `0x14042f820`=`1.0f` and
  `0x1403d71a8`=`3.0f` — **no change needed, this part was already correct**.

**Extrapolation modes (bits 4-5 pre / bits 6-7 post of the track flag byte, §2.5) —
CONFIRMED this session** by tracing `FUN_14038f820`'s raw disassembly end-to-end (the
decompiler had dead-code-eliminated the actual computation on several branches because
it mistyped the function `void` — same failure mode flagged in
`mdls_bd_format_and_ai.md`/the live-debugging notes; decompile output for this function
should not be trusted, always read the raw asm). Both pre and post use the same 2-bit
encoding:

- **mode 0 = hold** — return the boundary keyframe's value directly (`0x14038fc03` for
  pre, `0x14038fa63` for post).
- **mode 1 = linear/tangent extrapolation** — extend a straight line past the boundary
  using the slope of the boundary segment: `(next.value - edge.value) / (next.frame -
  edge.frame)` if the edge keyframe's own flag is linear (`1`), else the edge
  keyframe's tangent field directly (`edge.out_tan` for pre using kf0→kf1;
  `edge.in_tan_next` for post using kf[n-2]→kf[n-1] when that segment isn't linear).
  Traced at `0x14038f98a` (pre) / `0x14038f9fb` (post).
- **mode 2 = loop** — wrap the query frame by repeatedly adding (pre) or subtracting
  (post) the total keyframe span (`last.frame - first.frame`) until back in range.
  Traced at `0x14038f87d` (pre) / `0x14038f909` (post); matches the decompile's visible
  `for` loops, which were the only two branches the void-mistyping didn't corrupt
  (loop bodies have no meaningful "return value" for the decompiler to eliminate).
- **mode 3 = passthrough** — no adjustment; falls straight into the normal
  bracket+interpolate path with the frame left out of range, letting the boundary
  segment's own curve run past its domain unclamped.

Implemented in `kh1_mset_motion.py` (`pre_mode`/`post_mode` fields on each track) and
`kh1_bake_animation.py` (`_extrapolate()`/`_segment_slope()`), mirroring the
disassembly's exact control flow (pre-check then post-check unconditionally in that
order, both against the same, possibly pre-rewritten, frame value).

**Verified against real data**: scanning all 52 of Shadow's motion records found only
two `(pre_mode, post_mode)` pairs in practice — `(0, 0)` hold/hold (3614 tracks) and
`(2, 2)` loop/loop (419 tracks). Modes 1 and 3 don't appear in this file. The `(2, 2)`
tracks are a real, previously-unhandled bug: any looping animation was freezing at the
boundary keyframe instead of cycling, since the prior implementation treated every
track as hold at both ends.

**Status as of end of this session:** extrapolation modes and the Hermite math are now
both confirmed correct against the disassembly. The channel-7-9 ambiguity (§2.5) is
the main remaining open question for full visual correctness — re-bake and re-view
Shadow's motions (especially ones using the newly-decoded loop mode) to see how much
of the "still not right" visual issue that alone accounts for.

---

## 3. Two separate live object pools (don't confuse them)

Found two structurally different, address-range-separated struct pools live via Cheat
Engine breakpoints on `KH1_BehaviorScriptInterpreter` (`0x1402CC620`) vs.
`FUN_1402A0350` (motion-switch):

- **AI/behavior-script actor pool** — evenly spaced at exactly `0x758` bytes/slot,
  addresses like `0x142DCxxxx` in one observed session. This is the struct
  `GetActionState()`, the flinch counter (`actor+0x3E8`), etc. all live on (documented
  in `mdls_bd_format_and_ai.md`).
- **Rendering/animation-instance pool** — packed tighter (~`0x4B0`/1200 bytes/slot),
  addresses like `0x142D3xxxx`, clustered near `g_SoraObjPtr`'s own resolved address.
  This is where `actor+0x1D4` (the motion-ID lookup handle, §2.2) lives.

These are **not the same struct** — a lesson learned the hard way when `actor+0x1D4`
read as `0` on every AI-actor-pool address until the mistake was found.

---

## 3.5. The bind pose's wide "T-pose" arms aren't reachable by any `.mset` motion — NEEDS LIVE GAME

Session continuation, 2026-07-15, working from the rebuilt viewer (§6): after fixing
extrapolation, the channel mapping, and the `list1`/`list2` skinning-pose bug, the
model *still* looks "too upright" with arms splayed wide, compared to reference
gameplay footage the user linked (a real Shadow's idle animation looks hunched/compact,
arms close to the body). Isolated this precisely, all via static analysis:

- Added a third "bind pose only" (zero animation) viewport to the comparison tool.
  **The wide-arm stance is present in the raw bind pose itself** — confirmed both
  visually (user: "yeah he looks too upright") and numerically: computing bind-pose
  world positions via `forward_kinematics()` shows the arm chain (joints 46-63 one
  side, mirrored 65-82 the other) reaching all the way to **X = ±58 units** at
  shoulder height, while the antenna/ear chain (30, 33-37 / 40-44) rises well above
  head height (Y up to 147). This isn't a bug — it's genuinely what's stored in the
  file, confirmed byte-for-byte against the raw `.mdls` bytes at the joint records for
  joints 24/46/65 (no parsing error).
- **The joint that aims each entire arm — 46 (and mirror 65), direct children of the
  shoulder-complex root 27 — is never touched by any track in any of Shadow's 52
  motions**, in either `list1` or `list2` (exhaustively confirmed by scanning all 52
  motion records). Its bind rotation (`(-0.2°, 75.7°, 169.7°)`, confirmed from raw
  bytes) is what points the whole arm chain out to the side. No `.mset` motion data
  can ever change this.
- Ruled out as the cause: FK composition order (unchanged from the earlier-validated
  `forward_kinematics()`), the channel-mapping fix (§2.5, doesn't touch these joints),
  extrapolation (§2.7, irrelevant to bind pose), and a parsing bug (raw hex bytes for
  joints 24/46/65 match the parsed values exactly). Also checked
  `FUN_140391550` (the actor's spawn-time bind-pose initializer — builds the render
  buffer directly from `.mdls` joint fields once, before any motion has run) and its
  helper `FUN_1401db430` (a TRS-matrix builder like `FUN_1401db080` but without a
  scale argument, since bind-pose scale is always `1.0` in this file) — both use the
  exact same translation-column convention already confirmed in §2.5, no new bug.

**Conclusion: something other than `.mset` motion-track data must reposition these
"never-animated" joints during real gameplay** — a procedural adjustment, a different
data source entirely, or a genuinely different rendering/rigging path than the one
reconstructed here. This is the point where the doc's long-standing advice (§4 point 5,
now point 6) actually applies: static analysis has been exhausted for this specific
question and further progress needs **live ground truth**.

**Plan for the next live session** (game running, Cheat Engine attached):
1. Get Shadow into its idle/resting stance in-game (the state that looks hunched, not
   mid-attack), then breakpoint or directly read the *runtime* per-joint output buffer
   (`instance+0x1b4` resolved, 64-byte stride, offset `+0x10/+0x14` for the rotate
   fields — see §2.5) for joint 46 (and 65) specifically. Compare its live rotation
   value against the computed bind value (`75.7°` on Y). If it matches bind, the wide
   stance is either accurate (and the visual mismatch has some other cause, e.g. wrong
   camera framing, wrong motion selection, or the reference video shows a different
   creature/state) — if it's substantially different, that's the smoking gun for a
   yet-undiscovered control path for this joint.
2. If it differs from bind, trace backwards from that runtime value: what function
   last wrote to that buffer offset for joint 46 this frame — is it still
   `FUN_140391C70` (meaning some *other* motion, not yet identified, does cover this
   joint — worth re-searching *all* enemy `.mset` files, not just Shadow's, or
   reconsidering whether motion-ID→file-offset resolution, §2.2/§4 point 4, is
   pointing at a different/additional record than assumed), or something else
   entirely (a procedural/physics update, a separate "pose correction" pass).
3. Also worth checking while live: does `GetActionState()` or the AI actor struct
   (`mdls_bd_format_and_ai.md`) reference a persistent "current stance" blend weight or
   secondary animation channel that this investigation hasn't looked at yet.

## 3.6. SOLVED live — a third, previously-unknown per-motion track type

Same day, live session with the Steam build running (multiple Shadows on screen,
Cheat Engine attached). Followed the §3.5 plan exactly and it worked:

**Step 1 — confirmed the discrepancy live.** Found a live render-instance pointer by
breakpointing `FUN_140391C70` at `0x140391FB1` (inside the channel 4-6 dispatch,
which is definitely exercised — unlike the channel 1-3 path, which never hit in
several seconds of live play, itself a nice live confirmation that channel 1-3 truly
never appears in `list1`). Register semantics at function-entry are unreliable (the
prologue reassigns registers before settling — `RSI` holds the stable "output
instance" pointer, not `RCX`/`RDX`, and only after the prologue's `MOV RSI,RDX`).
Resolved the handle at `instance+0x1B0` through the documented scheme
(`region_bases[(h&0x7FFFFFFF)>>25] | (h&0x1FFFFFF)`) to get the live per-joint pose
buffer, then read joint 46's rotation directly: **live `(rotX, rotY, rotZ) ≈ (0°, 0°,
−5.8°)`, nowhere near the computed bind value `(−0.2°, 75.7°, 169.7°)`.** Cross-checked
against joint 47 (known to be `list1`-animated) showing a real, changing value at the
same moment, confirming the buffer is genuinely live, not stale.

**Step 2 — confirmed it's deterministic, not leftover memory.** Reloaded the room
(destroying and respawning all Shadows) twice; the freshly-spawned instance's joint 46
converged to the **exact same bit-pattern** both times. Ruled out simple "leftover pool
memory" — a coincidence wouldn't reproduce bit-for-bit across independent spawns.

**Step 3 — found the mechanism.** Wrote the raw bind-pose rotation directly into the
live joint 46 slot as a forcing experiment. First attempt: got silently corrected back
(not caught by a write breakpoint, since external `WriteProcessMemory`-style writes
don't trip hardware breakpoints — only in-process instructions do). Second attempt:
**stayed corrupted** — proving the correction isn't continuous per-frame, it fires on
a specific event. Between the two checks, joint 47's value had changed (a different
point in its animation, or an actual motion switch), pointing straight at
`FUN_14038f550` — the function `FUN_140391C70` calls at the top whenever
`param_2[1] != param_4` (i.e. **whenever the actor's motion changes**), which had
never been decompiled before this session.

**`FUN_14038f550` does three things, all newly understood:**
1. Unconditionally recopies every joint's raw `.mdls` scale/rotate/translate straight
   into the render buffer (identical mechanics to `FUN_140391550`'s spawn-time init) —
   i.e. **every motion switch resets the whole skeleton to bind pose first**, exactly
   like this repo's baker already does per-frame.
2. **Then applies a previously-undocumented flat override array** at
   `record+0x34` (count) / `record+0x38` (offset) — 8-byte entries, `joint_id:u16 @0`,
   `channel:u16 @2`, `value:f32 @4` — using the *exact same* channel-type encoding and
   output-slot offsets as `list1`/`list2` (1-3=scale, 4-6=rotate, 7-9=translate). This
   is a **third, entirely separate track-type**: not keyframe-curve-animated like
   `list1`/`list2`, just a flat one-shot "set this joint/channel to this value when
   this motion starts" list. **This is the mechanism.** Confirmed structurally against
   the (EGS-copy) file: motion `0x1B0` has 63 such entries, including three for joint
   46 (channels 7/8/9 = translate: `-3.93, -2.52, -1.23`) — a real, motion-specific
   correction for exactly the joint that `list1`/`list2` never touch. (The *exact*
   live values didn't numerically match this EGS-file entry — expected, since the live
   session is the **Steam** build and only the *format*, not the exact bytes, was ever
   cross-build-verified; the structural discovery doesn't depend on an exact match.)
3. A third block re-derives a secondary matrix for joints matching a flag test on
   `record+0x14`'s per-joint array (bits `0x4000000`/`0x2000000`) via `FUN_1401db430`
   into the `param_1+0x37` scratch buffer — doesn't write back to the main pose slot,
   likely feeds whatever `list2`'s `DAT_142ef1f50` mechanism (§2.5) consumes. Not
   pinned down further; not required to explain the bind-pose-arms problem.

**Fixed**: `kh1_mset_motion.py` now parses this as `instant_overrides` on the motion
record (`parse_instant_overrides()`). `kh1_bake_animation.py`'s `bake()` applies these
once, per-motion, on top of raw bind pose, *before* per-frame keyframe-track sampling
— mirroring `FUN_14038f550`'s own order exactly. This should be the last piece needed
for visually-correct single-motion playback; re-view the corrected bake (§6's viewer)
to confirm.

**Update, same day: still not visually correct — found something much bigger.**
Re-viewing (even with a statistically-identified likely-idle motion, `0xAEE0`, and
separately the motion with the best override coverage of joints 46/65, `0x48290`)
still looked wrong — user's diagnosis: "he's not hunched over," i.e. the overall
torso/arm carriage is wrong, not just one joint. That pointed at something upstream of
individual joint fixes: **the real per-frame FK/skinning-matrix walk isn't a simple
parent-child hierarchy compose at all.**

## 3.7. FUN_1403900b0 — the real FK walk is a full IK/constraint solver, not what this
## tool has been assuming

Found by checking who else calls `FUN_1401db4d0` (the hierarchy-compose primitive)
across the whole binary: `FUN_1403900b0`, called from `FUN_140391C70` right after the
track-sampling loops. This is the actual function that turns each joint's local
scale/rotate/translate (in `instance+0x1B0`, populated by `list1`/instant-overrides/
bind, as documented above) into final world-space matrices in `instance+0x1B4` — and
it is a **per-joint dispatch over a previously-mysterious flags array**
(`record+0x14`, resolved — the same array `FUN_14038f550`'s block 3 tests), not a
uniform walk. This repo's tooling (`kh1_bake_animation.py`) has only ever implemented
the simple case; for Shadow's actual rig, most of the joints that matter for arm/torso
carriage take a *different* path entirely.

**The flags array is structural, not per-motion.** Checked identical joints (0, 1, 24,
25, 26, 27, 46, 65) across three different motion records (`0x1B0`, `0x48290`,
`0xAEE0`) — the flag values are byte-for-byte the same in every one. This is rig
configuration baked once per skeleton, duplicated into every motion record's header,
not authored per-animation.

**Decoded flag bits** (`uVar2` = `record+0x14`-resolved array, one `u32` per joint):

| bits | meaning |
|---|---|
| bit 26 (`0x4000000`) | skip this joint entirely this frame (leave whatever was there) |
| bits 21-22 (`0x600000` mask) | selects one of 3 major branches in `FUN_1403900b0` (`0`=see below, `0x200000`=a distinct branch not yet decoded, `0x400000`/`0x600000`=a third, also not yet decoded) |
| within the bits21-22`==0` branch, `uVar2 & 3` | sub-case: `0`=see bit24/25 below; `1`=a tangent/orientation-from-target-delta case (not yet decoded); `2`=**snap this joint's orientation directly to a basis pulled from the `list2` secondary chain** (see below) |
| bit 24 (in the `uVar2&3==0` sub-case) | if set, always builds a local rotation matrix from this joint's own rotate data, but composes it against the chain root (`DAT_142ef1f50`, index 0) instead of the real parent — an "absolute world-space local rotation" mode. Not observed set on any of the joints checked so far. |
| bit 25 (in the `uVar2&3==0` sub-case, bit24 clear) | if set, **skips building a local rotation matrix from this joint's own rotate data entirely** — the scratch matrix stays identity (it was just identity-initialized via `FUN_140386d90`), so the hierarchy-compose (`FUN_1401db4d0(scratch, parent_world, out)`) makes this joint **inherit its parent's world rotation completely unchanged**. If clear, builds the local matrix normally from this joint's own rotate+translate (the "textbook FK" case this repo's tooling has always assumed). |

**Confirmed for Shadow's rig** (decoding the actual flag values for the joints that
matter for arm carriage):

| joint | bits21-22 | `uVar2&3` | bit24 | bit25 | effective behavior |
|---|---|---|---|---|---|
| 0 (root) | 0 | 2 | – | – | **snaps to `list2` chain index 3** |
| 1 | 0 | 2 | – | – | **snaps to `list2` chain index 4** |
| 24 (shoulder-complex root) | 0 | 2 | – | – | **snaps to `list2` chain index 5** |
| 25 | **1** | – | – | – | distinct branch, not yet decoded |
| 26 | 0 | 0 | 0 | **0** | **normal keyframe-driven FK** (matches: the only joint in this chain animated by `list1` in 33/52 motions) |
| 27 | 0 | 0 | 0 | **1** | **inherits parent (26) unchanged — own rotate data ignored** |
| 46 (right shoulder) | 0 | 0 | 0 | **1** | **inherits parent (27) unchanged — own rotate data ignored** |
| 65 (left shoulder, mirror) | 0 | 0 | 0 | **1** | same as 46 |
| 47 | 0 | 0 | 0 | varies by motion (0 or 1) | sometimes normal, sometimes inherits |

**This means the entire arm's real-world orientation is**: the actor's own world
placement (`DAT_142ef1f50` index 0, set from `param_1` at the very top of
`FUN_140391C70` via `FUN_140386ab0(&DAT_142ef1f50, param_1)`) → composed through
`list2`'s secondary chain (feeding joints 0/1/24's snapped basis) → joint 26's single
real keyframed rotation (the *only* actual per-motion contribution in this whole
chain) → joints 27/46/65 just carry that forward unchanged. **Every fix made earlier
this session to joint 46/65's own rotation data (channel mapping, instant-overrides)
was operating on data the game throws away for this specific joint** — it wasn't
wrong to fix (still correct, still needed for joints that *do* use bit25-clear), it
just was never going to fix the arm-carriage problem on its own.

**The `list2` secondary chain, decoded structurally** (this is what joints 0/1/24
actually need): `FUN_140391C70`'s hierarchy-blend loop (previously noted, §2.5) walks
`record+0x30`-resolved buffer entries **sequentially by loop position**
(`iVar6 = 1..count3-1`, stepping the pointer by a flat `0x28`/40 bytes each
iteration) — not by the track descriptor's raw joint-id field. That means the
joint-id values recorded in `list2`'s tracks (§2.2/§2.5, e.g. "joints 2-9/10") are
**local chain positions**, not real skeleton joint indices — a re-reading of earlier
findings. Each 40-byte entry has a `parent chain-position` field at **offset +12** (a
plain `i32`, previously unidentified — sits in the "gap" between the scale block
0-11 and the rotate block starting at 16) that `FUN_1401db4d0` uses to compose against
instead of the `.mdls` hierarchy. `FUN_1401db080(entry+0x28, entry+0x38, entry+0x44,
local)` builds the entry's own local matrix (scale/rotate/translate exactly like
`list1`'s convention), then `FUN_1401db4d0(&DAT_142ef1f50+i*0x40,
&DAT_142ef1f50+parent_i*0x40, local)` composes it onto the chain. Index 0 of
`DAT_142ef1f50` (the implicit root of this chain, never touched by the loop itself) is
the actor's own current world transform.

**Bit-packed "which chain index" extraction** (how `FUN_1403900b0` knows joint 0 wants
index 3, joint 24 wants index 5, etc — decoded and verified against the flags above):
`chain_index = (((flags >> 16) & 0x800) | (flags & 0x7fc)) >> 2, then minus 1`.

**Implemented, same session**: `kh1_bake_animation.py`'s `_solve_main_skeleton()` now
does a real per-joint flag dispatch (replacing the old "just compose local TRS down
the parent hierarchy" approach), backed by `kh1_mset_motion.py`'s new
`parse_joint_flags()`/`parse_secondary_chain()`. See §3.8 for what changed after
initial testing exposed more bugs and undecoded pieces.

This is a separate, larger reverse-engineering project (a real IK/rig constraint
system) layered on top of the keyframe/track system documented in the rest of this
file. The keyframe/track layer (extrapolation, channel mapping, `list1`/`list2` split
as skinning-pose-vs-not, instant-overrides) is solid and confirmed independent of
this.

## 3.8. Live-verifying the IK implementation — a root-basis bug and a dispatch bug

Same session, continued live (game still running). First live check: the actual
rendered result (using the §3.7 implementation as first written) was still visibly
wrong — "hunched but not correctly so," described as looking like it was lying on its
side. Debugged this with two further rounds of live verification plus one purely
static re-trace, each catching a real, distinct bug:

**Bug 1 — the secondary chain's root baseline isn't identity.** `_solve_secondary_chain`
assumed chain index 0 (parent `-1`, fed at runtime from the actor's own current world
transform, `DAT_142ef1f50` index 0) starts from identity for a standalone bake (no real
actor placement to read). Read the live array directly (`0x142ef1f50`, 704 bytes = 11
chain entries, one `read_memory` call) from two different actors at two different
moments: **row 1 of index 0 is always exactly `(0,-1,0)`** regardless of which
(differently-facing) actor was sampled, while rows 0/2 vary with each actor's yaw. I.e.
the chain's neutral/no-yaw baseline is `Rx(180°) = diag(1,-1,-1)`, not identity — a
fixed convention difference between this chain's coordinate system and the main
skeleton's. Fixed: added `ROOT_BASIS = diag(1,-1,-1)` as chain-index-0's baseline.

**Same live read, a second finding**: entries 3+ hold basis vectors scaled by real
magnitudes (bone lengths, up to ~9 units), not unit rotations — confirming the "bone
matrix" convention suspected from the IK math in §3.7 (`FUN_1401db130` explicitly
normalizes each row's length back out before using it as pure rotation). Not
separately actioned (this repo's chain composition already works in plain rotation
matrices throughout, so it never encounters the scaled form).

**Bug 2 — the rotation dispatch (chain-snap / pass-through) is a shared tail, not
`bits21-22==0`-gated.** After fixing bug 1, the result was still wrong — specifically
the legs. Checked the leg joints' flags (joint 2 = hip: `bits21-22==1`; joint 5/15 =
upper leg: `bits21-22==2`) and found BOTH use the two `bits21-22` branches that were
never decoded in §3.7. Traced them from raw disassembly:

- `bits21-22==0x200000` (joint 2): reads a **second, differently-positioned bit-packed
  chain-index field** — from the *next* joint's flags dword (`jidx+1`), at bits 11-19
  plus bit 28 (vs. the bits 2-10 + bit 11 used for the joint's *own* chain-snap index) —
  and uses it as a **position target**: inverse-transform the target through
  `FUN_1401db130`, forward-transform back through the parent via `FUN_1401dad10`. That
  round-trip is a mathematical no-op (a matrix and its inverse cancel), so the net
  effect this Python port implements is simply `world_pos[joint] = secondary_chain[target_idx].pos`
  directly — no matrix inversion needed.
- `bits21-22==0x400000`/`0x600000` (joint 5/15): traced into the **same shared tail**
  (`0x140390d87` onward) that the `bits21-22==0` branch also reaches for its rotation
  handling — i.e. **the `uvar10`/bit24/bit25 rotation dispatch (chain-snap,
  pass-through, normal FK) is not specific to `bits21-22==0` at all; every branch
  funnels into it.** The first implementation had incorrectly gated chain-snap and
  pass-through behind `bits21-22==0`, silently forcing joints 5/15 (bit25 set, meant to
  be pass-through) into the normal-FK fallback instead. This was a real bug, not an
  approximation — fixed by removing the `bits21-22==0` condition from the rotation
  checks entirely.
- Also decoded while tracing this shared tail: for the *translation* side of the
  default (`bits21-22 in {2,3}`) branch specifically, there's a further 3-way split
  per-joint (own current world position if a bit-23 flag is set; a *third* chain-target
  index encoded in the joint's *own* flags at bits 11-19+bit20 if nonzero; else the
  ordinary local-translate-via-parent composition) — joint 5/15 both land in the
  "ordinary" case (their own version of this field is zero), so this doesn't currently
  need implementing for Shadow specifically, but is worth remembering if another
  enemy's rig exercises it.

**Still not decoded**: the `uVar2&3==1` sub-case (tangent/target-delta orientation
referencing bone-length data at `.mdls`-array offsets `+0x50`/`+0x80` — looks like
classic two-bone/law-of-cosines IK); the bit-23/own-current-position and
own-flags-chain-target sub-cases just mentioned (not yet needed for Shadow, but not
implemented either). Both are addressable the same way as everything else in this
section — trace the raw disassembly, verify live if the static trace leaves ambiguity
— just not yet done.

**Practical lesson reinforced twice this round**: static disassembly tracing got the
*structure* right both times (the target-index formula, the shared-tail architecture)
but a live read caught a wrong *assumption* (identity baseline) that no amount of
re-reading the same disassembly would have surfaced, since the baseline value isn't
something the disassembly specifies — it's supplied by the caller at runtime. When a
static trace bottoms out at "this value comes from outside the function," check it
live rather than guessing.

## 4. Next-session TODO

1. ~~**Nail the extrapolation modes**~~ — **DONE** (a later session), see §2.7. All 4
   modes traced from `FUN_14038f820`'s raw disassembly and implemented; verified
   against real data (Shadow uses hold and loop modes, not linear/passthrough).
2. ~~**Resolve the channel 1-3 / 7-9 ambiguity**~~ — **DONE** (a later session), see
   §2.5. The mapping was backwards: 1-3 is scale, 7-9 is translate (not the reverse).
   Independently confirmed via `FUN_1401db080`'s calling convention, proven by its
   bind-pose-setup caller (`FUN_1401d5b10`) which uses `.mdls`'s own unambiguous
   scale/rotate/translate field order. Full-file scan found channel 7-9 (translate)
   ranging up to `±473` — a bone position, never a plausible scale factor. Fixed in
   `kh1_bake_animation.py`'s `CHANNEL_SLOT` and `kh1_mdls_parse.py` (now reads bind
   scale, previously ignored). **This was very likely the actual root cause of the
   "still not right" visuals** — the old mapping fed scale values into forward
   kinematics as positions (actively wrong) while silently dropping the real translate
   channel (scale wasn't applied to vertices, so it had no visible effect either way).
3. ~~**Re-view Shadow's motions with the corrected mapping**~~ — **DONE**, see the
   correction at the end of §2.5. Re-viewing surfaced the *real* bug: `list1`/`list2`
   were being merged into one skinning pose, and `list2` was never supposed to be part
   of it. Fixed by keeping them separate. The channel-mapping fix itself turned out to
   make no visible difference for Shadow (its `list1` never uses channels 1-3/7-9),
   but is still correct and may matter for other enemies' files.
4. **Crack the motion-ID → file-offset table** (§2.2) so specific IDs from
   `kh1_motion_ids.py`'s extraction (e.g. Shadow's `204`) can be mapped to a file
   offset without needing the live game running.
5. ~~**Bind-pose-arms-never-corrected-by-any-motion**~~ — **SOLVED** (a live session),
   see §3.6. A third, previously-undocumented per-motion track type
   (`record+0x34`/`0x38`, flat one-shot joint/channel/value overrides applied on
   motion switch via `FUN_14038f550`) is what corrects joints `list1`/`list2` never
   keyframe-animate. Implemented in `kh1_mset_motion.py`/`kh1_bake_animation.py`.
6. Re-view the bake with all three fixes applied (extrapolation, `list1`-only
   skinning, `instant_overrides`) to confirm it now looks fully natural — this was the
   last known gap.
7. `FUN_14038f550`'s third block (the `record+0x14` flag-gated `FUN_1401db430` call
   into `param_1+0x37`) is still not understood — doesn't affect the main pose slot,
   likely related to `list2`'s still-unexplained `DAT_142ef1f50` mechanism (§2.5).
   Not required for visual correctness as far as currently known.
8. If static/hand-derivation keeps being unreliable, the more trustworthy path is
   **live ground-truth comparison** — as demonstrated decisively in §3.6, breakpointing
   the right location and reading live memory settles questions static analysis alone
   couldn't (register semantics at a function's raw entry point are unreliable due to
   prologue reassignment; pick a breakpoint address past the point where the
   decompile's variable naming is stable, e.g. where a value is actually being read
   from the register you want, not where the function merely begins).

## 5. Key addresses (Steam build)

| Address | What |
|---|---|
| `0x1402CC620` | `KH1_BehaviorScriptInterpreter` (the `.bd` VM) |
| `0x1402860A0` | `.mset` type-handler (resource-dispatch table entry) |
| `0x140286220` | `.mdls` type-handler |
| `0x1401D6B30` | Generic `MOBJ`/`MENV` relocation pass (no-op for `MMTN`) |
| `0x1401DF0F0` / `0x1401DF170` | Generic TLV chunk-walkers (find-by-magic / find-`TEXA`) |
| `0x1402B9F80` / `0x1402B9FB0` | `NATIVE_t0_0xd` / `0xe` wrappers → motion-queue push |
| `0x14029F980` / `0x14029FA30` | Motion-queue push (called by the above) |
| `0x14029FC40` | Per-frame action-state dequeue (`actor+0x164` = `GetActionState()`'s field) |
| `0x1402A0350` | "Switch to this motion" — resolves motion ID via `actor+0x1D4` |
| `0x1403948C0` | Trivial `record+4` frame-count getter (good breakpoint for capturing a resolved record pointer) |
| `0x140391C70` | The real animator/sampler driver (walks tracks, calls the curve evaluator, writes the output pose) |
| `0x14038F820` | Keyframe curve evaluator (binary search + step/linear/Hermite + all 4 extrapolation modes, §2.7) |
| `0x14038ADC0` → `0x14038AF40` | Handle resolver: `region_bases[(h&0x7FFFFFFF)>>25] \| (h&0x1FFFFFF)` |
| `0x142ee3980` (`DAT_142ee3980`) | Region base-address table |
| `0x142D37280` (`g_SoraObjPtr`) | Sora's own actor pointer global |
| `0x1401DB080` | TRS→local-transform builder, calling convention `(scale, rotate, translate, out_matrix)` — proves the §2.5 channel-type correction |
| `0x1401D5B10` | Skeleton bind-pose setup — reads `.mdls` joint fields directly and calls `FUN_1401DB080`, the independent proof of that function's arg order |
| `0x1401DB4D0` | Generic parent-child hierarchy-compose helper (used everywhere in this binary, not distinctive on its own) |

## 6. Files

- `kh1_mdls_parse.py` — `.mdls` parser (skeleton + mesh + textures, exports JSON)
- `kh1_mset_motion.py` — `.mset` motion-record parser (given a known file offset)
- `kh1_bake_animation.py` — bakes a motion record to per-frame joint poses (uses both of the above)
- Live viewer: WebGL model+animation viewer, published as a Claude Artifact this
  session (private, session-scoped — re-publish from a fresh conversation to get a
  usable link again; ask the user if they still have the URL saved).
