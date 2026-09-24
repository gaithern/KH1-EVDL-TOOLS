# Heartless field-spawn investigation (Traverse Town 2nd District, tw02)

Status as of 2026-07-22 (session 12): the fresh-load fallback path AND the
"already loaded elsewhere this session" reuse path are now **both**
deliberately disabled in `l_spawn_enemy` -- the reuse path was believed safe
since session 8, but crashed live this session (Soldier, Accessory Shop and
`tw11`, reproduced three times across two process restarts). Root cause
finally identified via Ghidra decompile, not guessed: the constructor's
universal `record+8` self-heal mints a handle wrapping a per-species
resource-blob table (`DAT_140d2ada0 + species*0x40000`) whose CONTENT is
keyed by the same room-local slot NUMBER this whole investigation has always
known has no fixed meaning across rooms -- so it can silently hold a
different creature's real leftover data instead of Soldier's. Two other
real, unrelated bugs were found and fixed along the way (a stale resource-
handle bug specific to the reuse path, and two more missing phantom-record
rollbacks) and remain fixed/kept. Native-record-reuse (a creature already
native to the current room) remains the only spawn path confirmed safe
across the WHOLE investigation and is fully unaffected. See "Session 12"
below before touching `l_spawn_enemy` again.

Status as of 2026-07-22 (session 9): the fresh-load fallback path (spawning
a creature with zero native presence loaded in the CURRENT room) is now
**deliberately disabled** in `l_spawn_enemy` -- it always refuses cleanly.
A real root-cause theory was found and looked compelling (see "Session 9"
below), but the attempted fix made things WORSE live (an actual game crash,
not just a caught exception) and was reverted the same session. Read the
full "Session 9" section before re-attempting any fix here -- it documents
both the theory and exactly why/how it failed live, so the next attempt
doesn't repeat the same mistake. Native-record-reuse (a creature already
present in the current room) is completely unaffected and still works.

Status as of 2026-07-22 (session 8): the species-number API is gone --
`spawn_enemy(model_path, motion_path, x, y, z)` identifies creatures by their
real, stable model/motion filenames, figures out a local slot number
entirely on its own, and now **auto-learns** any creature it finds native to
a room (real char-id/weight/record, straight from live memory, no manual
capture) so it becomes spawnable anywhere else that session. Native-record-
reuse and Soldier's original fallback path are both confirmed solid. **The
fresh-load fallback path (a genuinely new species slot, first load this
session) is confirmed broken in general, not just for one creature**:
session 7 found it froze the whole game for Large Body; session 8 confirmed
a second, unrelated creature (Alleyway's local slot 30, `xa_ex_2020`)
crashes the process outright from the identical code path in a different
room. A debugger-armed repro pinned the crash to somewhere at-or-after the
`fnc_spawn_world_gimmick_entity` constructor call (not the mint/load-trigger
machinery). Static analysis of that constructor initially found a
plausible-looking candidate (`entity+0x138` read via an unbounded handle
resolve without ever being initialized) -- **but a further live test
disproved it, and then live-confirmed the constructor actually completes
and returns a valid entity pointer in BOTH the working and the crashing
case.** The bug is not in the constructor at all -- it's in whatever
per-frame system touches the entity AFTER construction (rendering, AI tick,
animation, physics), the same "entity became visible, then broke" shape as
Large Body's freeze, just crashing here instead of hanging. This is the
next-session starting point -- see "Session 8 continued again" below before
touching `l_spawn_enemy` again.

## Goal

Find the native function (or mechanism) that spawns an ambient field
Heartless, and expose it as a callable Lua function in KH1-LUA-LIBRARY.
**Done**: `spawn_enemy(x, y, z, species)` ships in `kh1_lua_library.lua`,
backed by a native primitive (`kh1_native.spawn_enemy` / `l_spawn_enemy` in
`dllmain.cpp`), and produces a fully live, combat-interactable Heartless.
Remaining work is generality -- supporting species with zero native presence
in the current room -- not correctness.

## Session 3 summary: from "crashes every time" to "works"

Session 2 found the real static Heartless placement table (`tw02.ard`
section 7, `KAGE_*` records) and the constructor (`fnc_spawn_world_gimmick_entity`)
but every live attempt to call it crashed the game. Session 3 spent most of
its length root-causing that crash, then fixed it.

### The crash was never about Shadows or bad data

Six full game crashes were needed to establish this conclusively:

1. First splice attempt crashed. Investigation of the crash uncovered that
   Cheat Engine's own Lua `copyMemory()` **silently corrupts large copies**
   -- the very first splice's "clone" was actually garbled in ~30-48 bytes
   per 120-byte record, invalidating that test. Fixed by switching to a
   plain byte-by-byte `readBytes`/`writeBytes` loop, verified with an
   explicit zero-diff byte compare before ever touching the live globals
   again. This fix should be remembered generally: **never trust
   `copyMemory()` in this CE Lua environment for anything non-trivial.**
2. A second attempt with a byte-verified, correct clone of a real live
   `KAGE_1_1` record still crashed (froze, then died) -- ruling out
   "corrupted data" as the cause.
3. A third attempt using a **completely untouched real record's own id**
   (an actual `mo_2tbox_00` chest, zero fabricated data at all) also
   crashed, shortly after returning cleanly with `0` -- ruling out "wrong
   data" and "wrong id" entirely.
4. Systematic isolation (each step confirmed safe or unsafe against a live,
   watched game session): a bare `RET` stub via `execute_code` -- safe. A
   simple real function (`fnc_find_gimmick_type_def`) -- safe, stable 12s+.
   A medium-complexity real function (`FUN_140285ee0`) -- safe, stable 10s+.
   Repointing the live placement table to an unmodified clone, no new
   record, no call -- safe (user-observed). Splicing a new record into the
   table, still no call -- safe (user-observed). **Only actually invoking
   `fnc_spawn_world_gimmick_entity`'s full construction path crashed --
   every single time, regardless of what data it was given.**

Conclusion: the crash was caused by *how* the function was being called, not
by anything about Heartless or the placement-table technique. Cheat Engine's
`execute_code`/`execute_code_ex` runs the call from a CE-injected foreign
thread. This specific function -- large, ~150 nested helper calls, heavy
local stack use -- reliably froze then crashed when invoked that way, while
trivial and medium-complexity calls via the identical mechanism did not.
Note: even "the process still responds to `get_opened_process_id`/
`read_memory` a few seconds later" turned out to be an **unreliable signal**
of safety at least once this session -- CE's view of a dying process can lag
behind the user's own observation. Trust the user watching the screen over
tool-side health polling when the two disagree.

### The fix: call it in-process instead of via Cheat Engine

KH1-LUA-LIBRARY already had a working precedent: `spawn_prize()` calls real
game code via `kh1_native.call_function`, which runs the call as a plain
in-process function-pointer invocation (wrapped in SEH `__try/__except`)
from whatever thread the Lua script is already executing on -- LuaBackend's
own hook into the game's real thread, not a foreign injected one. That is
architecturally the fix for the CE crash: same call, correct execution
context.

A new native primitive, `l_spawn_enemy` (`native/KH1Native/dllmain.cpp`),
does the whole splice-and-call sequence in one in-process C++ call:
1. Reads the live placement-table pointer/count (RVAs supplied from Lua, so
   the DLL stays version-agnostic).
2. Scans the *current* table for an existing record whose species byte
   (`record+0x55`) matches the requested species, and uses it as a
   template (most fields still aren't independently understood well enough
   to synthesize from scratch -- see the record-format section below).
3. Allocates a fresh `(count+1)`-record buffer (real in-process `VirtualAlloc`
   + `memcpy`, not the CE Lua path that was proven corrupting), clones the
   template into the new slot, overwrites the id (category byte forced to
   `0x99`, outside the values `fnc_find_gimmick_type_def` treats specially)
   and the position floats.
4. Repoints the two live globals and calls
   `fnc_spawn_world_gimmick_entity(newId)` via the same `SafeCall` helper
   `call_function` uses.

Exposed as `spawn_enemy(x, y, z, species)` in `kh1_lua_library.lua`
(`species` defaults to 30/Shadow), with EGS addresses matched and both DLLs
(`kh1_native.dll` and the debug overlay's `kh1_native_debug.dll`, which
grew a matching "Spawn Enemy" button) rebuilt and deployed to both Steam and
EGS mod folders.

**Confirmed live, 2026-07-20**: called from the F6 debug overlay in tw02
with `species=30`, position near Sora. A Shadow appeared at the correct
world position, fully rendered/animated, with **no crash** -- the debug
result even returned a valid entity pointer. This is the first successful
programmatic Heartless spawn in this entire multi-session investigation.

### Known limitation: species must already be native to the room

`spawn_enemy` clones an *existing* placement record of the requested
species from the current room's own table. It cannot yet conjure a species
with zero presence in the room (e.g. no Shadow record anywhere in a room
that never has Shadows) -- that would need either a hand-built record per
species (most of the ~30 fields per record are still unmapped) or captured
template records shipped as static data. Not attempted this session.

## Session 4 (2026-07-21): non-interactability root-caused and fixed

Session 3 ended believing the spawned entity got silently invalidated a
few minutes post-spawn by some missing "registration" step, plausibly the
wave/population-budget system. Session 4 disproved that theory, found the
real cause, fixed it, and confirmed live: **the entity is now fully
interactable -- lock-on works, it can be damaged and defeated, and it
attacks the player back.**

### The budget/despawn theory was wrong

Re-traced the two functions session 3 flagged:
- `FUN_1402aa3f0` -- confirmed NOT an allocator. It only manages per-group
  spawn-budget counters against entities that are already constructed
  (gated on `entity+0x374` bit `0x80000`). Its own plate comment now
  reflects this.
- `FUN_140292390` -- confirmed to be a **generic despawn/cleanup utility**
  with dozens of unrelated callers throughout the binary (every per-species
  behavior/tick function calls it when *that entity* decides to end), not
  something specific to ambient Heartless.

Found the actual missing piece from session 3 ("the allocate-on-budget
call site was never found"): **`FUN_1402aacd0`** is the real per-frame
ambient-wave scheduler (registered via `FUN_140284660`/`670`). Each frame
it walks the room's placement-table records and, for the first one whose
group is enabled, off cooldown, not already spawned, and under budget,
calls **the exact same `fnc_spawn_world_gimmick_entity`** that
`spawn_enemy()` already uses, then stops for the frame. So
`fnc_spawn_world_gimmick_entity` was never the wrong constructor.

### The reload behavior is a separate, expected non-issue

Live-tested with a Cheat Engine hardware write-watchpoint (all 37 threads,
since a single global watchpoint doesn't reliably fire in this game --
confirmed again this session) on the spawned entity's id field
(`entity+4`). No write occurred over several real-time minutes of normal
play -- ruling out a passive timer. Reloading the room (leaving and
re-entering tw02) triggered it instantly: the write came from inside
`fnc_spawn_world_gimmick_entity` (RVA `0x290e7d`, ~0x11d bytes past its
start) via a `memset` immediately before it, and the new id was a real
`category=4` (map object) record -- i.e. the room's normal reconstruction
pass reached our slot and built real room furniture into it. **This is
expected, not a bug**: a synthetic entity only exists in the currently
loaded, RAM-side splice of the placement table, and any room reload
rebuilds the entity pool from scratch from the room's real data. It has
nothing to do with the actual "not interactable" problem, which was
present even in a fresh spawn with no reload involved.

### The real cause: the synthetic category byte broke kind-based dispatch

`spawn_enemy`'s native code forced the spliced record's category byte
(and therefore its id) to `0x99`, specifically so the id wouldn't collide
with any real record (see the record-format section below). But
`fnc_spawn_world_gimmick_entity` derives the constructed entity's **"kind"
byte directly from that same category byte**, and every place in that
constructor that does real per-kind setup branches on kind:
- `kind == 3` -- party-linkage check (only does real work if it resolves
  to an actual party slot 0/1/2)
- `kind == 2` -- calls `FUN_1402a10b0` (an AI/motion-activation call)
- `kind == 0x99` (our synthetic value) -- **matches neither branch**, so
  none of that per-kind setup ever ran.

The entity got a transform, animation pointers, and rendered correctly,
but skipped every piece of kind-specific registration a real actor needs
to be targetable/hittable -- exactly matching the observed symptom
(renders fine, zero interaction).

### The fix

`l_spawn_enemy` (`native/KH1Native/dllmain.cpp`) now builds the new
record's id from a **real category (`3`, character/actor, matching the
Shadow template)** and **a real slot index (this record's own position in
the resized table)**, instead of the out-of-band `0x99`. Rebuilt and
redeployed to both Steam and EGS `scripts/io_packages/kh1_native.dll`.
**Confirmed live 2026-07-21**: spawned Shadow can be locked onto, damaged,
defeated, and attacks the player back -- the first fully-functional
programmatic Heartless spawn in this entire investigation.

Note for future sessions: `fnc_select_tgt_entity`'s id-resolution (used
for the scheduler's own "already spawned" dedup check) treats category `3`
identically to the old `0x99` -- both fall through to its default
exact-id-match linear scan, since only categories `0`, `1`, and `0xb` get
dedicated fast paths. So the id-resolution mechanics were never actually
the problem; the kind-byte/dispatch mechanism was.

### Known limitation (unchanged, next real open item)

`spawn_enemy` clones an *existing* placement record of the requested
species from the current room's own table. It still cannot conjure a
species with zero presence in the room (e.g. no Shadow record anywhere in
a room that never has Shadows) -- that would need either a hand-built
record per species (most of the ~30 fields per record are still unmapped)
or captured template records shipped as static data. Not attempted yet.

## Session 5 (2026-07-21): captured fallback template + asset-streaming attempt

Goal: spawn a species with zero native presence in the current room at all
(the "known limitation" above). Progress made, but the core mechanism
(triggering an on-demand asset load) crashed the game twice and is
currently disabled, unresolved.

### Captured a real Soldier (species 34) template, found a transcription bug

Captured a live Soldier placement record (from a room with native Soldiers)
via Cheat Engine and hand-typed it into a new static fallback table in
`l_spawn_enemy` (`kFallbackTemplate_Species34_Soldier`). First live test in a
Soldier-less room came back `false, "exception during constructor call"` --
traced to a resolved-handle field at `record+0x08` carrying over a
session/room-local value from the capture room; `fnc_spawn_world_gimmick_entity`
only self-heals that field when it resolves to exactly 0, and the stale
handle apparently resolved to something non-zero-but-wrong instead. Fixed by
explicitly zeroing `record+8` before construction (forces the constructor's
own existing fallback path every time, whether the template came from the
current room or a captured one).

Second live test came back "targetable but invisible and inert" --
different symptom, traced to a genuine hand-transcription error: the
species byte at `record+0x55` read `0` (Sora) instead of `34`, confirmed by
reading the compiled static array directly out of the loaded DLL via a
Cheat Engine AOB scan (`03 00 03 00 22 1C 00 00 A0 AD 3F 81` found the array
at a known offset, then every field read directly rather than trusted from
memory) -- NOT a wholesale byte shift, just one localized slip while typing
120 bytes by hand. Fixed two ways: (1) `l_spawn_enemy` now force-writes
`newRec[PLACEMENT_SPECIES_OFFSET] = species` unconditionally after cloning
ANY template (in-room or fallback), sidestepping the need for the template
array to be byte-perfect at that specific offset; (2) confirmed the
neighboring char-id field (`record+0x4c`, see below) was untouched by the
same error and genuinely reads `0` in the real captured record.

**Lesson for next time**: don't hand-transcribe a 120-byte captured record
into a C array again. Two independent manual retypes of the same 120 bytes
this session each introduced a different small error. If another template
needs capturing, have the capture tool itself emit a ready-to-paste C array
literal (with an assertion on exact byte count) rather than typing a hex
dump by hand.

### Found the real asset-streaming mechanism (still unsafe to call)

Traced why a record-format-correct fallback spawn still rendered nothing
and never moved even after the species-byte fix: `fnc_spawn_world_gimmick_entity`'s
self-heal for `record+8` only resolves a HANDLE into the shared per-species
resource table (`DAT_140d2ada0 + species*0x40000`, up to species index
`0x40`/64 -- confirmed via `FUN_140285db0`'s bounds check) -- it never
*triggers a load* if nothing in the current room's own script/load sequence
ever queued that species. The table entry exists but is empty in a room
that was never going to have that species.

The actual loader trigger is **`FUN_140285ee0(type_id, completion_callback)`**
(Steam RVA `0x285EE0`) -- confirmed to be the exact function real EVDL room
scripts use via its caller `fnc_0B5_load_model` (an already-named opcode
handler from an earlier session), which calls it identically:
`FUN_140285ee0(type_id, callback)`, having first set `g_EVSystemFlags |= 0x2000`
(`DAT_142382590`, Steam RVA `0x2382590`). Internally it resolves a
species-def via `fnc_find_gimmick_type_def`, marks a per-species load-state
byte (`DAT_142869dd3`, 0x50-byte stride), and queues a job via
`FUN_14028a900` whose eventual callback is `FUN_140286420` (checks a cached
filename against the species-def's own, dispatches the actual file load via
`FUN_14028bc10` if different, and on completion the job's own callback
`FUN_140286290` stores a resolved pointer into `DAT_142869e18`, 0x50-byte
stride per species -- this is the thing to poll for "is the load done").

**Two live attempts to call this ourselves both crashed the whole game
process, uncaught by `SafeCall`:**

1. First attempt: `l_spawn_enemy` called `FUN_140285ee0(newId, 0)` right
   after splicing the record, then polled `DAT_142869e18` for the result
   before constructing. Crashed instantly, no debugger attached -- no
   diagnostic information recovered.
2. Second attempt: same call, but with `g_EVSystemFlags |= 0x2000` set
   first (matching `fnc_0B5_load_model`), and this time with Cheat Engine's
   debugger attached plus logging breakpoints armed on every stage of the
   chain (`FUN_140285ee0`, `FUN_140286420`, `FUN_14028bc10`, `FUN_140286290`).
   Crashed again -- but with **zero hits on any of the four breakpoints,
   including `FUN_140285ee0`'s own entry**. That means execution never
   even reached the loader function this time. The only new code between
   the record splice and that call was the `g_EVSystemFlags` write itself
   -- a raw pointer write with NO `SafeCall`/`__try` protection, unlike
   every other memory access in this file. Current best theory: that
   specific unprotected write is what crashed attempt 2, which means
   **attempt 1's actual crash cause (presumably somewhere in the real
   async callback chain) is still unconfirmed** -- attempt 2 failed for an
   unrelated reason before ever re-testing it.

`FUN_14028a900` (the job dispatcher) was decompiled and confirmed to be a
plain synchronous, single-threaded priority-queue insert into a fixed-size
pool -- no thread creation, no OS calls. It's called by dozens of totally
ordinary systems (visual/particle effect opcodes, in particular) that
obviously run without issue constantly during normal play, so "it's an
inherently dangerous background-thread system" is probably the wrong
framing. The real cause is still unknown.

**Disabled as of this session** -- `l_spawn_enemy` accepts
`loadAssetsFnRva`/`loadedPtrTableRva`/`evSystemFlagsRva` as parameters
(plumbed through from `kh1_lua_library.lua`/`SteamGlobal_1_0_0_2.lua`) but
does not act on them; they're cast to `(void)` with a comment explaining
why. **Do not re-enable without**:
1. Verifying `g_EVSystemFlags`/`DAT_142382590` is really a plain, mapped,
   writable global at that address -- confirmed only via `list_globals`,
   never independently read/written live before the write that (probably)
   crashed attempt 2.
2. Getting a real, confirmed breakpoint hit on `FUN_140285ee0`'s own entry
   before trusting anything about what happens further down the chain --
   attempt 2 never even got that far.
3. Ideally, disassembling `fnc_0B5_load_model`'s surrounding EVDL opcode
   dispatch to understand what scriptCtx state it has available that a
   bare native call doesn't -- the real caller runs inside the script
   interpreter with a live scriptCtx; our call site has none of that.

EGS twins of `fnc_load_gimmick_assets`, `loadedSpeciesPtrTable`, and
`evSystemFlags` not yet located (Steam-only investigation this session).

### Attempt 3: the asset-streaming mechanism actually works now -- but a separate, more severe bug surfaced

Traced the real cause of both earlier crashes via pure static analysis (no
game running): `FUN_140285ee0` itself is clean (disassembly confirms the
type_id argument really does flow through RCX into `fnc_find_gimmick_type_def`
-- the decompiler's "zero-argument" display was cosmetic). The job-queue
dispatcher (`FUN_14028a900`) is a plain synchronous, single-threaded
priority-queue insert processed once per frame on the main thread via a
completely ordinary per-frame-callback registration (`FUN_140286200` ->
`fnc_____main_loop`) -- not a background thread, ruling that theory out.

The real cause: `FUN_140286420` (the load-dispatch callback) resolves
`record+0x60`/`record+0x64` via `FUN_14038adc0` and dereferences the result
as null-terminated filename strings (model/motion). `FUN_14038adc0`'s
resolver (`FUN_14038aee0`, decompiled) encodes a handle as `bucket_table[(h &
0x7FFFFFFF) >> 25] | (h & 0x1FFFFFF)` with **no bounds check** on the bucket
index -- and the bucket table itself is a fresh, per-session list of
32MB-aligned heap regions. A captured template's raw handle number for these
fields is therefore presumptively invalid in any other session; resolving it
very likely produced the wild pointer that crashed attempt 1.

Live-verified (2026-07-21, all 13 Soldier records in a room where the
species is genuinely native) that the underlying filename strings ARE
species-constant, not per-record: `"xa_ex_2010.mdls"` / `"xa_ex_2010.mset"`
for species 34. That made a real fix possible: rather than ever reuse a
captured handle number, `l_spawn_enemy` now ships those strings as static
data and mints a **fresh, this-session-valid handle** for them via
`FUN_14038ad90` (`fnc_mint_resource_handle`, Steam RVA `0x38AD90`) --
confirmed via decompiling its callees (`FUN_14038ae10`/`FUN_14038aee0`) to be
a generic, self-registering pointer-to-handle encoder with no requirement
the pointer belong to any pre-existing game allocation. Only species with a
verified string pair in `kSpeciesResourceStrings` (species 34 only so far)
attempt the load trigger at all.

**This worked.** Live-confirmed in a room with zero other species-34
presence: `loadedSpeciesPtrTable[34]` populated with a real pointer,
per-species load-state reached `6` (fully processed), entity constructed
alive with the correct `kind`, **no crash**. First real end-to-end success
of the streaming mechanism.

Two follow-on problems surfaced immediately, in order of severity:

1. **Position stuck at (0,0,0).** The record itself correctly held Sora's
   position (verified live), and the full position-copy path was traced
   start to finish (`FUN_140292660` -> `FUN_140292bc0` ->
   `FUN_140386ad0(entity+0x10, positionStruct)`, confirmed unconditional
   regardless of the `record+0x5A` orientation-branch value) -- yet the
   live entity's `+0x10` still read zero. Not yet resolved; suspected either
   a later-frame overwrite (same class of question as the reload-slot-reuse
   investigation in session 4) or a side effect of problem 2 below. A
   write-watchpoint on the live entity's `+0x10` (same per-thread technique
   used successfully in session 4 for `entity+4`) was proposed as the next
   step but not yet run.

2. **Far more serious: `record+0x4c` ("character id", read by
   `fnc_spawn_world_gimmick_entity` for any `kind==3` entity) is `0` in the
   captured fallback template, and `0` resolves as party slot 0 -- Sora
   himself.** Confirmed live: spawning a second Soldier via this template
   **overwrote `g_SoraObjPtr[0]`, replacing the game's own reference to the
   real Sora entity with the new Soldier.** Symptoms matched exactly: HUD
   face vanished, the spawned entity was uninteractable, and the game
   crashed shortly after (very plausibly something else dereferencing
   "Sora" through the hijacked pointer and finding a Soldier's data instead
   of a player character's). This is likely serious enough to also explain
   problem 1, if whatever reads "Sora's position" elsewhere got confused
   once `g_SoraObjPtr[0]` no longer pointed at the real player.

   **Fixed the same session.** Checked live against 3 real, natively-placed
   species-34 records: all read `0x12C` (300) at `record+0x4c`, uniformly --
   a fixed, species-constant value like the model/motion filename strings,
   not session-local data (also caught `record+0x59` weight wrong: template
   had `39`, real records read `4`). `l_spawn_enemy` now force-writes both
   (`kSpeciesCharId` table, currently just species 34 -> charId 300/weight 4)
   whenever the fallback template is used -- never for an in-room clone,
   which already carries a correct real value. If a future species has a
   fallback template but no verified char-id entry, `l_spawn_enemy` now
   refuses to spawn rather than risk an unknown-value hijack.
   `FindFallbackTemplate` is re-enabled. **Re-tested live: confirmed the
   hijack is gone** (`g_SoraObjPtr[0]` unchanged after a spawn that would
   previously have overwritten it) -- but the position-stuck-at-zero problem
   was still present on this retest, proving it's a separate bug, not a side
   effect of the char-id hijack.

### The position bug was the asset-load timeout, and is now fixed

Live pattern noticed by the user: the *first* spawn of species 34 in a
session always came out invisible/immobile (position stuck at `(0,0,0)`,
matching the original observation), but every subsequent spawn attempt
worked correctly. That's exactly consistent with the asset-load poll
timeout being too short: `l_spawn_enemy` triggers the load and polls
`loadedSpeciesPtrTable[species]` for up to ~2 seconds, then **constructed
the entity anyway** if that timed out, just logging a warning. A genuinely
cold, first-time-this-session load is plausibly slower than 2 seconds (real
disk I/O); building the entity against not-yet-ready data produced the
invisible/immobile symptom even though every record field was correct. The
second attempt worked because the species was already cached from the first
load finishing in the background after the timeout.

Fixed by (1) extending the poll timeout to ~10 seconds, generous for a cold
load, and (2) more importantly, changing the timeout behavior from
"construct anyway" to **refuse to construct and return an error** -- the
caller can simply retry rather than ever getting a silently-broken entity.
**Re-tested live and confirmed working**: first spawn of a session froze
briefly then cleanly returned the "try again" error (no broken entity), and
a follow-up attempt succeeded immediately (species already cached from the
first load completing in the background).

### Foundational correction: "species" is a per-room LOCAL slot index, not a global monster ID

User observation that broke this open: spawning `species=30` (documented
all session as "Shadow") in a different room ("Green Room") produced a
**Soldier** instead, and it wasn't fightable (presumably the room's own
cutscene-specific instance). Verified directly and decisively: Green Room's
`species=30` resolves to model file `xa_ex_2010.mdls` -- the exact same file
independently confirmed (identically, across 13 real records) to be
Soldier's model in the room this session's whole species-34 investigation
was done in. Green Room's own species histogram is `{0, 12, 21, 30, 32, 35,
40, 45}` -- no `34` present at all.

**So "species" is not a global creature ID.** It's a small, per-room-local
slot index into whatever roster of creature types that specific room
happens to use, assigned independently room by room -- Shadow being 30 in
tw02 and Soldier being 34 in the room this session tested it in were both
just local coincidences, not a fixed convention. The real, stable identity
of a creature is the filename number itself (`xa_ex_2010` = Soldier,
wherever it appears; presumably tw02's Shadow has its own equivalent
`xa_ex_NNNN` identity not yet captured).

**This means the whole species-34-based fallback-template fix from this
session has a real, previously-unrecognized gap.** Forcing `record+0x55` (and
the self-healed `record+8` resource table lookup, which is keyed by this
same byte) to `34` only works safely in a room where local slot 34 happens
to be unused -- true in every room tested this session by coincidence, but
nothing prevents some other room from already using slot 34 for a
completely different creature, in which case the synthetic Soldier would
collide with whatever that room actually assigns to slot 34 (untested,
unknown consequences -- could range from cosmetic wrongness to another
crash class entirely).

**Not yet done, the real next step for this whole feature**: before
forcing a hardcoded species byte, verify the target room doesn't already
use that slot for something else (scan the placement table's species
histogram, matching this session's diagnostic technique), and either pick a
genuinely free slot dynamically or refuse cleanly if none exists. Not
attempted this session -- this is where a future session should start.

## Record format (two different layouts: file vs. runtime)

Both layouts use a 0x78-byte (120-byte) stride, confirmed by both static
file math and the live loop bound (`DAT_14296b628` count * 0x78 exactly
spans the array).

**File layout** (as stored in `tw02.ard`):
- `+0x00..0x07`: name string, up to 8 ASCII chars, zero-padded, no null
  terminator if exactly 8 chars
- `+0x10`: two u16s - low u16 = sequential slot index, high u16 = category
  (3 = character/actor incl. party AND all KAGE entries, 4 = map object)
- `+0x2c/0x30/0x34`: position X/Y/Z floats (file layout only)
- `+0x3c/0x40/0x44`: scale (always 1.0/1.0/1.0 in samples seen)

**Runtime layout** (the loaded, live version of the same table -- fields
are reordered, do not assume file offsets apply):
- `+0x1C/+0x20/+0x24`: position X/Y/Z floats (RUNTIME layout -- this is
  what `spawn_enemy`'s native code writes)
- `+0x2C`: scale (constant 1.0)
- `+0x54`: "def-kind" byte, branches game logic (values seen: 0, 1, 2, 5, 6)
- `+0x55`: **species/type index** -- Shadow confirmed = 30
- `+0x5A`: orientation-branch selector (values seen: 1; 2/3/4 trigger
  Sora-relative aim-vector math not otherwise exercised)
- `+0x59`: a "weight" byte used by the global and per-group population
  budget checks
- name string near offset `+0x68` (variable, not fixed-width the way the
  file layout is)

## Live-confirmed global state (Steam build)

- `DAT_14296b630` (static `0x14296b630`, RVA `0x296b630`) = pointer to the
  current room's active placement table
- `DAT_14296b628` (static `0x14296b628`, RVA `0x296b628`) = record count
- EGS twins: `DAT_14296c030` / `DAT_14296c028` (RVA `0x296c030`/`0x296c028`)
- `fnc_spawn_world_gimmick_entity`: Steam `0x140290d60` (RVA `0x290d60`),
  EGS `0x14028ebd0` (RVA `0x28ebd0`), fuzzy-match score 0.60
- `fnc_find_gimmick_type_def`: Steam `0x140287b40`, EGS `0x1402859c0`
  (score 1.0, identical)
- `fnc_select_tgt_entity`: Steam `0x140291d30` -- id-to-entity resolver.
  Fast paths only for category `0` (party array), `1` (species-def+0x4c
  character-id search), `0xb` (species-def+0x4e search); every other
  category, including both the old `0x99` and the new `3`, falls through
  to a linear scan matching the entity's own `+4`/`+0` id field exactly.
- `FUN_1402aacd0`: Steam `0x1402aacd0` -- **the real per-frame ambient-wave
  spawn scheduler** (session 2/3's "not yet found" allocate-on-budget call
  site). Walks the room's placement records each frame; for the first
  eligible one (group enabled, off cooldown, not already spawned, under
  budget) calls `fnc_spawn_world_gimmick_entity` and stops for the frame.
  Registered as a callback via `FUN_140284660`/`670`, itself invoked from
  `FUN_1402a9c40` (the per-room encounter-config loader/reset, runs on
  room load).
- `FUN_1402aa3f0`: Steam `0x1402aa3f0` -- per-group spawn-budget
  bookkeeping only, NOT an allocator (corrects session 3's working theory).
- `FUN_140292390`: Steam `0x140292390` -- generic despawn/cleanup utility
  with dozens of unrelated callers throughout the binary; not specific to
  ambient Heartless.

All of the above are named and plate-commented in Ghidra on both builds,
including corrections to two previously-stale comments that claimed the
default placement table was navmesh/collision data (it isn't -- see the
comments themselves for the full history).

## What shipped this session (KH1-LUA-LIBRARY + KH1-LUA-LIBRARY-DEBUG)

- `native/KH1Native/dllmain.cpp`: new `l_spawn_enemy` primitive, registered
  as `kh1_native.spawn_enemy`. Rebuilt, deployed to both Steam and EGS mod
  folders.
- `scripts/io_packages/kh1_lua_library.lua`: new `spawn_enemy(x, y, z,
  species)` function, exported.
- `scripts/io_packages/SteamGlobal_1_0_0_2.lua` /
  `EGSGlobal_1_0_0_10.lua`: new RVAs (`fnc_spawn_world_gimmick_entity`,
  `placementTablePtr`, `placementTableCount`).
- `KH1-LUA-LIBRARY-DEBUG/native/KH1NativeDebug/dllmain.cpp`: new "Spawn
  Enemy" F6-overlay button (X/Y/Z/species fields) under a new "Enemies"
  category. Rebuilt, deployed to both mod folders.
- `KH1-LUA-LIBRARY-DEBUG/scripts/kh1_native_test.lua`: dispatch branch for
  the new action.

**Not yet done:** KH1-VERSION-FINDER address-database sync (standing
project rule for every new address -- AOB patterns for the three new RVAs
above still need adding to `version_files/*.lua` + `patterns.json`).

## What shipped session 4 (2026-07-21)

- `native/KH1Native/dllmain.cpp`: `l_spawn_enemy` now builds the spliced
  record's id from category `3` + a real slot index instead of an
  out-of-band `0x99` -- see "The fix" above. Rebuilt, redeployed to both
  Steam and EGS mod folders. No Lua-facing signature change.

**Not yet done:** KH1-VERSION-FINDER sync for `fnc_select_tgt_entity`,
`FUN_1402aacd0`, `FUN_1402aa3f0`, `FUN_140292390` (found/confirmed this
session, Steam addresses only -- EGS twins not yet located), in addition
to the three RVAs still pending from session 3.

## Tooling notes worth remembering generally

- Cheat Engine's Lua `copyMemory()` silently corrupts large copies in this
  environment -- confirmed twice. Use a plain byte-by-byte
  `readBytes`/`writeBytes` loop and verify with an explicit diff before
  trusting any bulk memory clone done through CE Lua.
- `execute_code`/`execute_code_ex` (CE-injected foreign-thread calls) are
  unsafe for anything beyond trivial/shallow game functions -- this cost 6
  full crashes to nail down. For anything that touches real game object
  construction/state, prefer an in-process native call (a small addition to
  `kh1_native.dll`, following the `SafeCall`/`call_function` pattern) over
  CE injection.
- CE's own post-call health checks (`get_opened_process_id`, `read_memory`
  a few seconds later) are not fully reliable evidence a call was safe --
  confirmed at least once this session where tooling reported the process
  alive shortly before the user observed a real crash. When in doubt, ask
  the user to watch the screen directly.
- Steam module base stable at `0x7FF729E50000` across every relaunch this
  session (many relaunches, same base every time -- this game has no
  observed runtime ASLR).
- (Session 4) Per-thread hardware write-watchpoints reconfirmed necessary
  across all ~37 threads, same as session 3's finding for read/write
  breakpoints generally. But watch the *value*, not just any field that
  sounds relevant: a watchpoint on the entity's `+0x374` flags word
  produced 70k+ hits in under two minutes from routine per-frame
  bookkeeping unrelated to occupancy, making the hit log useless. Watching
  a field the constructor only ever writes once (`entity+4`, the id) gave
  a clean, single, actionable hit instead. When picking a watch target,
  prefer a field with a known write-once code path over one that merely
  changes when the bug happens.
- (Session 4) `get_breakpoint_hits`' `registers` block includes `RIP` at
  the moment of each hit -- mapping that back to a Ghidra RVA
  (`runtime_addr - module_base`) identified the exact writing instruction
  without needing to single-step or re-attach a full debugger session;
  useful generally for "who wrote this address" questions in this game.

## Session 7 (2026-07-22): species-number API replaced with filename identity, auto-learn shipped, new freeze bug found (unresolved)

**Trigger**: user pushback on the whole session-5/6 design -- "we shouldn't
assume Soldier is always 34, it's just slots." Correct, and already
foreshadowed by session 6's own foundational-correction note. This session
removed the numeric species param from the public API entirely.

### What shipped and is confirmed working live

- **`spawn_enemy(model_path, motion_path, x, y, z)`** (`kh1_lua_library.lua`)
  and **`l_spawn_enemy`** (`dllmain.cpp`) no longer take a species number at
  all. On every call:
  1. Scan the CURRENT room's own placement table for a record whose model
     handle resolves (see below) to the requested filename -- if found,
     clone it as-is and reuse its own local slot number. No mint, no load
     trigger, no risk at all. **Confirmed live**: Soldier, Shadow, and Large
     Body all spawn correctly this way, in rooms that already have them.
  2. If not found, and the creature is verified (see auto-learn below), scan
     `loadedSpeciesPtrTable` for a slot already holding this exact creature
     this session (reuse it) or the first slot untouched this session (state
     byte `== 0`, claim it -- `needsLoad`).
  3. Refuses cleanly (no guessing) if the creature is native to nowhere
     reachable and isn't verified yet.
- **Found and documented `fnc_resolve_resource_handle`** (Steam RVA
  `0x38ADC0` -> `0x38AF40`; EGS `0x38B0B0` -> `0x38B230`), the counterpart to
  `fnc_mint_resource_handle` -- given an encoded handle, resolves it back to
  the real pointer/string. This is what makes step 1 above possible: resolve
  a room's own placement record's model handle and compare the string
  directly (no external memory read needed, this DLL runs in-process).
  Confirmed live via Cheat Engine against real Alleyway records (species 34
  resolved to `xa_ex_2010.mdls` = Soldier; species 30 resolved to
  `xa_ex_2020.mdls` = a different creature -- yet more confirmation species
  is a per-room-local slot, not an identity). Renamed/commented in Ghidra on
  both Steam and EGS programs, synced to KH1-VERSION-FINDER (new AOB pattern,
  only 4 wildcard bytes out of 256 -- very tight).
- **Real Ghidra gotcha hit and resolved this session**: after calling
  `open_program` for the EGS binary, several subsequent tool calls *without
  an explicit `program` parameter* silently targeted EGS instead of Steam --
  produced a completely wrong decompile (an unrelated Unicode-normalization
  function) at an address that's actually `fnc_mint_resource_handle` on
  Steam, briefly looking like Ghidra database corruption. It wasn't --
  re-running the same calls with explicit `program="/KINGDOM HEARTS FINAL
  MIX.exe"` gave the correct, expected result. **Always pass `program`
  explicitly once more than one Ghidra program is open**, for every call,
  not just the ones that seem ambiguous.
- **Auto-learn** (`LearnCreatureIfNew`/`FindCreatureFallbackData` in
  `dllmain.cpp`): every time step 1 above finds a creature natively in a
  room, its real char-id/weight/full 0x78-byte record are captured straight
  from live memory into an in-memory table (`g_learnedCreatures`, session-
  only, lost on restart, no disk persistence) -- no manual Cheat Engine
  capture, no hand-transcription risk (unlike the original Soldier capture
  in session 5, which took two rounds of bugs from exactly that). Once
  learned, a creature can use the fallback path (step 2/3 above) in ANY
  other room, not just the one it was learned in. **Confirmed live**: Large
  Body learned in a room with natives, then successfully spawned (visible,
  correct) in a different room with zero native Large Body presence --
  *until* the freeze described below.
- **Found and fixed a real, previously-unknown bug in
  `fnc_spawn_world_gimmick_entity` itself**: a global concurrent-entity
  spawn budget. Decompile shows `return 0` (no crash) whenever
  `g_nGimmickSpawnBudgetUsed + species_def->weight (record+0x59) >
  g_nGimmickSpawnBudgetCap (record... global, currently observed value 18
  in one room)`. Confirmed live: spawning failed silently (`true, 0`) while
  a room's own ambient Heartless was still alive, and the identical call
  succeeded once it was cleared -- consistent with the despawn path
  decrementing the used counter (not directly traced). This is DIFFERENT
  from the per-encounter-group ambient-wave budget
  (`DAT_142d60ca8`/`DAT_142d60cac`) session 4 already found -- this one
  (`DAT_142d60c98`/`DAT_142d60c9c`, now named+commented in Ghidra on Steam)
  gates every single call to the constructor, not just ambient waves.
  **Fixed**: `l_spawn_enemy` now checks `result == 0` after a clean
  `SafeCall` and reports a clear refusal ("budget is likely full") instead
  of the previous misleading `ok=true, entityPtr=0`.
- Debug overlay (`KH1-LUA-LIBRARY-DEBUG`) updated to match: two text fields
  (model/motion filename) instead of a species spinner, packed into
  `param_text` as `"model|motion"` since the shared debug-action struct only
  has one string field.

### Dead end investigated and ruled out: loading creature data from raw game files

User asked whether char-id/weight (needed for the fallback path on a
never-visited-live creature) could come from the `.ard` room files or the
`.mdls`/`.mset` model files directly, without ever needing the live game.
Investigated properly, not assumed:

- The `.ard`'s **file** layout for the placement/encounter record (with
  char-id/weight, analogous to runtime record+0x4c/+0x59) is still NOT
  reverse-engineered -- session 2's file-layout notes (see "Record format"
  above) only ever mapped name/category/position/scale, explicitly leaving
  char-id and weight as runtime-only knowledge.
- The user's "KH1FM Documentation" Google Sheet's **MDLS Map** tab gives a
  per-room, per-creature raw file offset for the model/motion filename
  strings (e.g. Soldier in `tw05.ard` at `0xE7200`) -- genuinely useful for
  building a creature-name -> filename lookup with zero live capture. But
  reading the raw bytes at that exact offset (confirmed directly against the
  real file) shows it's just a flat, back-to-back `.mdls`/`.mset` filename
  table -- NOT the per-instance placement record. No char-id/weight there.
  Two other tabs with this data exist only in stale June-2025 spreadsheet
  snapshots ("Copy of KH1FM Documentation - June 15/June 8"), not the live
  doc -- worth checking with the user whether those tabs still exist
  somewhere current.
- The `.mdls`/`.mset` model/animation files themselves (format fully mapped
  in `docs/animation/mdls_mset_model_and_animation_format.md`) contain
  **nothing** resembling char-id or weight -- confirmed by reading that
  entire doc. They're pure geometry/animation data (skeleton, mesh, textures,
  keyframe curves, even a full IK/rig-constraint system) with no
  encounter-design metadata of any kind. This avenue is a dead end;
  char-id/weight are placement/encounter properties, not model properties.
- **Conclusion**: live auto-learn (shipped this session) is the practical
  path until/unless the `.ard` placement-record file layout gets properly
  reverse-engineered. That reverse-engineering is real, open work -- start
  by diffing a known room's raw `.ard` bytes against its already-mapped
  runtime record (e.g. Alleyway/`tw05.ard`, Soldier species 34 and Shadow
  species 30, both live-dumped this session -- see below) to find where
  char-id/weight actually live on disk.

### NOT YET RESOLVED -- the real next-session starting point: a game freeze

Reproduced live: auto-learned Large Body (learned in a room with natives),
spawned successfully via the native-reuse path there, THEN taken to a
different room with **zero** native Large Body presence and spawned via the
full fallback path (fresh slot claim, `needsLoad=true`, mint handles, trigger
load, poll, construct) -- **the entity became visible, then the whole game
froze** (not a crash -- unresponsive, had to force-close).

**What's been ruled out, confirmed live from the frozen process**:
- The learned data itself is correct: char-id 304, weight 6, def-kind byte 5
  (same value as Soldier's own template, so not an exotic/untested
  def-kind branch in the constructor) -- read directly from the spliced
  record still sitting in the room's live placement table.
- The asset load itself completed successfully: `loadedSpeciesPtrTable`
  slot 30's state byte reads `6` (the real terminal/fully-loaded value, per
  session 6's own finding) with the correct cached filename
  (`xa_ex_2050.mdls`) -- so this is NOT a stuck/incomplete load.

**What's NOT confirmed, despite trying**: which exact thread/instruction is
actually hung. One live thread's context was captured with `RIP` sitting
exactly at the entry of `FUN_140286420` (the async-load callback, the same
function documented in session 5/6) -- suggestive, but **`debug_get_context`
returned byte-for-byte identical register state after breaking three
different, genuinely distinct thread IDs via `debug_break_thread`**, meaning
that tool is not reliably reporting per-thread context the way assumed (see
[[feedback_ce_live_code_injection_safety]]). This finding should be treated
as unconfirmed, not a lead to trust.

**What's confirmed NOT the cause**: this is not a data-integrity problem
(char-id/weight/def-kind all check out) and not an incomplete load. The bug
is specific to the *fresh-load* fallback path (a genuinely new, never-
touched-this-session slot) -- native-record-reuse is unaffected and was
retested working for the same creature (Large Body) minutes earlier. Whether
this is specific to Large Body, or would reproduce with any non-Soldier
creature going through the fresh-load path for the first time, is untested
-- Soldier is the only creature that's ever exercised this exact path before
today, and it always worked.

**Next session should start here**:
1. Get a clean live repro with a debugger attached BEFORE triggering the
   spawn (not after, like this session) -- set a hardware breakpoint on a
   specific suspect address (e.g. `FUN_140286420`'s entry, or the
   string-copy loop inside it) rather than trying to catch a thread
   mid-freeze after the fact.
2. Verify what `debug_get_context`/`debug_break_thread` actually do in this
   CE MCP bridge version before trusting per-thread results again -- the
   identical-context finding this session was never explained.
3. Consider whether the fix belongs in `l_spawn_enemy` (e.g. gate the
   fresh-load path behind something safer) or reveals a real gap in what
   session 5/6 verified about the mint+load-trigger sequence generally.

### Session 8 (2026-07-22): confirmed NOT Large-Body-specific -- a second creature crashed outright (different symptom, same path)

Answered next-step item 3 above. Method: rather than hand-parsing the live
placement table (the approach that produced garbled results earlier this
same session, see the tooling note below), wrote a small `pymem`-based
Python script to dump the current room's placement table programmatically
(species/char-id/weight/model+motion handles, cross-referenced against
`loadedSpeciesPtrTable`'s cached filename per slot) -- avoids the
hand-transcription failure mode documented repeatedly for this project (see
[[feedback_ce_live_code_injection_safety]]).

Found a genuinely new, never-before-tested creature native to Alleyway
(`tw05`): local slot 30, model `xa_ex_2020.mdls` / motion `xa_ex_2020.mset`
(confirmed by resolving both handles live via `fnc_resolve_resource_handle`
through a direct `execute_code` call -- safe here specifically because this
resolver is a trivial, leaf, side-effect-free bucket-table lookup, the same
class of function session 3 confirmed safe for foreign-thread `execute_code`
calls, unlike the deep constructor that isn't), char-id 301, weight 3,
def-kind 5 (same def-kind as Soldier and Large Body).

Procedure:
1. Spawned `xa_ex_2020` natively in Alleyway (native-record-reuse path,
   zero risk) -- worked cleanly, auto-learned.
2. Traveled to `tw11` (the Moogle/Cid item-shop room -- confirmed via the
   same dump script to have zero Heartless placement records of any kind,
   and confirmed `loadedSpeciesPtrTable` slot 30's state byte was back to
   `0` there, i.e. a genuinely untouched-this-room slot, not a stale
   cross-room cache hit).
3. Spawned `xa_ex_2020` again in `tw11` -- forces the exact same fresh-load
   fallback path (mint handles, trigger load, poll, construct) that froze
   on Large Body.

**Result: the game crashed outright (process gone, confirmed via
`get_process_list`) -- not a freeze/hang like Large Body.** No debugger was
attached this attempt (deliberately -- this session prioritized the
"is it creature-specific" question over forensics), so no exception/stack
information was captured.

**This resolves next-step item 3 conclusively: the fresh-load fallback path
is unsafe in general, not a Large-Body-specific bug.** But the two known
failure instances differ in kind (Large Body hung the whole process; this
creature crashed it outright) rather than reproducing the same symptom --
consistent with a shared root cause (most likely still somewhere in the
mint-handle + `fnc_load_gimmick_assets` trigger + poll sequence, or the
`fnc_spawn_world_gimmick_entity` construction call itself once the load
resolves) whose exact failure shape depends on incidental memory-layout
differences between creatures/rooms, not with two unrelated bugs -- but this
is inference, not confirmed by a debugger yet.

**Next session should start here** (supersedes item 3 above, items 1-2 and
4 from before this still stand):
1. Get a clean live repro with a debugger attached BEFORE triggering the
   spawn, per item 1 above -- now doubly motivated, since we have two
   distinct symptoms (hang vs. crash) that both need explaining, and a
   crash (unlike a hang) should leave real exception/fault information if
   caught while debugged.
2. Consider trying the SAME creature (`xa_ex_2020`/Alleyway slot 30) again
   in a different zero-presence room, and/or Large Body again, to see if
   either failure mode is at least consistent per-creature (i.e. does
   `xa_ex_2020` reliably crash and Large Body reliably hang, or is it
   nondeterministic) -- not yet known.

### Session 8 continued: attached a debugger and got a real answer -- a strong, specific, falsifiable lead in `fnc_spawn_world_gimmick_entity` itself

Same session, continued after the section above. Attached CE's debugger to
the relaunched game (no ASLR -- module base stable at `0x7FF729E50000`
again) and armed four **non-blocking logging** hardware execution
breakpoints (`set_breakpoint`'s logging mode -- captures registers/stack on
hit without pausing the process, so normal gameplay wasn't disrupted) on the
whole suspect chain before reproducing: `fnc_load_gimmick_assets`, the async
load callback (`FUN_140286420`), `fnc_mint_resource_handle`, and
`fnc_spawn_world_gimmick_entity` itself.

Reproduced the exact same crash (relearned `xa_ex_2020` in Alleyway,
fresh-fallback-spawned it in `tw11` again). Two of the four breakpoints
(`load_gimmick_assets`, `mint_resource_handle`) turned out to be *far* too
hot to use as signal on their own -- both fire roughly a million times during
completely ordinary gameplay (confirmed: `mint_resource_handle` alone is
called by dozens of unrelated engine systems per session 5's own finding,
and `load_gimmick_assets` similarly). But the fourth breakpoint
(`fnc_spawn_world_gimmick_entity`, only ~200 hits per session -- real,
meaningful signal) gave a decisive result: **its last recorded hit before
the process died had `RCX = 0x00030010`, which is exactly
`(category=3 << 16) | 0x10`, and `0x10` (16) is precisely `tw11`'s
placement-table record count from BEFORE our spawn spliced a new record
in.** That's an unambiguous match for our own call -- proving the entire
load pipeline (mint, trigger, poll) succeeded this time, and the crash
happens AT OR AFTER the constructor call itself, not before it (unlike
session 5's second attempt, which crashed before ever reaching
`fnc_load_gimmick_assets`'s own entry).

This directly rules out the mint-handle/load-trigger machinery as the
culprit and points squarely at `fnc_spawn_world_gimmick_entity`'s own body
(or something that runs immediately after it returns) -- consistent with
Large Body's session-7 symptom too, which also got as far as "entity became
visible" (construction succeeded) before the freeze.

**Full decompile of `fnc_spawn_world_gimmick_entity` (Steam `0x140290d60`)
found a strong, structurally distinct candidate.** After the def-kind byte
(`species_def+0x54`, the SAME field the placement-record layout notes
already documented) is read, there's a per-def-kind dispatch:

```c
cVar1 = *(char *)(lVar6 + 0x54);   // species-def's def-kind byte
if (cVar1 == '\x01') { FUN_1401d0550(puVar13); }
else if (cVar1 == '\x02' || cVar1 == '\x05') { goto LAB_14029142d; }
else if (cVar1 == '\x06') { ... }
...
LAB_14029142d:
puVar13[0xdd] = puVar13[0xdd] | 0x10000;   // sets a flag bit -- entity+0x138 (puVar13[0x4e]) is NEVER written on this path

if ((puVar13[0xdd] >> 0x10 & 1) != 0) {
    lVar6 = fnc_resolve_resource_handle(puVar13[0x4e]);   // resolves whatever's sitting in entity+0x138
    if (lVar6 == 0) {
        puVar13[0xdd] = puVar13[0xdd] & 0xfffeffff;        // clears the flag, bails safely
    } else {
        uVar8 = fnc_resolve_resource_handle(puVar13[0x4e]);
        uVar8 = FUN_1402bd420(uVar8);                       // dereferences/uses the resolved pointer
        uVar9 = FUN_14038ad90(uVar8);
        puVar13[0x51] = uVar9;
        uVar8 = fnc_resolve_resource_handle(uVar9);
        FUN_1402bd3f0(uVar8,puVar13,8);
    }
}
```

**Every single creature tested this whole investigation (Soldier, Large
Body, `xa_ex_2020`) has def-kind 5** -- all three always take this exact
branch. Checked the ENTIRE function body for every other handle-shaped
entity field written earlier in the constructor (`0x4d`, `0x4f`, `0x50`,
`0x51`, `0x52`, `0x53`, `0x76`, `0x110`, `0x122`, `0x12a`, etc.) -- every
one of them is explicitly initialized to `fnc_mint_resource_handle(0)` (a
"minted null", which resolves cleanly back to exactly 0) somewhere earlier
in this same function, confirmed by re-scanning the full decompile.
**`entity+0x138` (`puVar13[0x4e]`) is the one exception** -- for def-kind
2/5 creatures specifically, it's read and resolved WITHOUT ever being
written first anywhere in this function.

The entity pool (`DAT_142d372a0`..`DAT_142d5349f`, 96 slots stride 0x4b0)
only gets `memset`'d to zero on a slot's very first-ever allocation this
session (confirmed from the same decompile: the slot-scan loop only
`memset`s when it falls through to allocating a brand-new slot, not when it
reuses a previously-freed one) -- so a REUSED slot's `+0x138` field carries
over whatever the slot's *previous occupant* left there. If that stale
32-bit value isn't a real minted handle, `fnc_resolve_resource_handle`'s
underlying bucket-table lookup (`FUN_14038aee0`, already documented in
session 5: `bucket_table[(h & 0x7FFFFFFF) >> 25] | (h & 0x1FFFFFF)`, **no
bounds check on the bucket index**) can index far outside the real table --
exactly the same bug CLASS session 5 already found and fixed for the
placement record's own `+0x60`/`+0x64` fields, just showing up here inside
the live ENTITY structure instead. A wildly out-of-range index faults
immediately (this session's crash); a less-wild-but-still-wrong one can land
on mapped-but-nonsensical memory, explaining a hang instead (Large Body) --
same root cause, different incidental outcome depending on whatever
leftover bytes happen to be at that stale bucket index. Checked
`FUN_1402bd420`/`FUN_1402bd5b0` (what the resolved pointer feeds into if the
resolve itself doesn't already fault) -- they store the value opaquely into
a 64-slot object pool without dereferencing it as a pointer, so the crash
is most likely inside `fnc_resolve_resource_handle`'s own bucket lookup, not
in these two downstream functions.

**This is not yet live-confirmed** -- it's a strong, structurally-supported
static-analysis finding, not a proven root cause. The decisive next step:

1. Read `entity+0x138` live, right before this check runs, for BOTH a
   known-working spawn (native-record-reuse, e.g. Soldier in Alleyway) and
   a fresh-load spawn about to crash/freeze -- confirm it's reliably 0 (or
   at least a valid-resolving handle) in the working case and garbage in
   the failing case. A hardware breakpoint at the exact instruction that
   reads `puVar13[0xdd]` right after `LAB_14029142d` (need the precise
   address via `disassemble_function`, not yet looked up) would let this be
   read directly out of the RCX/RDI-equivalent register or by computing the
   entity pointer from context.
2. If confirmed, the real fix is almost certainly NOT inside
   `l_spawn_enemy` in the way prior fixes were (we don't control which pool
   slot the constructor picks, that scan is entirely internal to
   `fnc_spawn_world_gimmick_entity`) -- it would need either: (a)
   pre-scanning the same 96-slot entity pool ourselves before calling the
   constructor, predicting which slot it will reuse, and zeroing that
   slot's `+0x138` field defensively first: or (b) determining whether this
   is actually a bug the real game ever hits too (i.e. does normal ambient
   Heartless respawn-into-a-freed-slot ever hit a non-Soldier def-kind
   2/5 creature reusing a slot whose previous occupant also set `+0x138`
   for some other reason) -- if it's genuinely dormant in real play, that
   would explain why this was never noticed before this investigation.
3. `FUN_1402bd420`/`FUN_1402bd5b0`/`FUN_1402bd3f0` are still unnamed --
   worth renaming/commenting once their role is confirmed live (structure
   suggests some kind of secondary object-pool/state-machine registration,
   64 slots at `DAT_142dc7be0`, stride 0x758, distinct from both the 96-slot
   entity pool and the placement table).

### Session 8 continued again: live-confirmed, and it's NOT what the static analysis predicted -- the constructor completes cleanly; the bug is post-construction

Same session, live verification of the `entity+0x138` theory above. Found the
exact instruction via `disassemble_function` (Steam
`fnc_spawn_world_gimmick_entity` @ `0x140290d60`): `0x140291443`
(`MOV ECX,[RDI+0x138]`) immediately followed by `0x140291449`
(`CALL fnc_resolve_resource_handle`) -- `RDI` is the live entity pointer
throughout this whole function (confirmed from disassembly, e.g.
`MOV dword ptr [RDI+0x4],EBX` matching the decompile's `puVar13[1]=param_1`
early on). Relaunched, reattached CE's debugger (module base stable at
`0x7FF729E50000` again, no ASLR), armed a single non-blocking logging
breakpoint at `0x7FF72A0E1449` (`base+0x291449`).

**First test (control): a native-record-reuse spawn in Alleyway (known to
work).** Identified our own call unambiguously in the hit log by matching
`R12`/the id register against `(3<<16)|recordCount` for the room (Alleyway's
count was 45 at spawn time) -- found `R12=0x0003002D` (0x2D=45, exact
match), `RCX (entity+0x138) = 0x81326B20`. Not zero, not obvious garbage --
a plausible, real-looking handle.

**Second test: the fresh-load fallback spawn in `tw11` (known to crash).**
Reproduced the crash again with the breakpoint still armed. Its hit was
unambiguous the same way (`R12=0x00030010`, matching `tw11`'s pre-spawn
record count of 16) -- and **`RCX (entity+0x138)` was `0x81326B20`, the
EXACT SAME VALUE as the working Alleyway spawn**, not garbage, not
different in any way. **This directly refutes the "stale/uninitialized
pool-slot garbage" theory** -- the field holds the identical value in both
the working and failing case, so it cannot be what's distinguishing them.
(Mildly curious on its own that two different entity-pool slots -- different
`RDI` each time -- carried the identical value here, but that's a footnote,
not the cause; not investigated further.)

**Third test: bisected the rest of the function.** Set two more breakpoints
from the same disassembly: `0x140291498` (right after the entire
def-kind-2/5 block finishes, confirms "survived past the suspect area") and
`0x1402918d3` (the function's own `RET`, confirms "constructor fully
completed"). Reproduced the crash a third time (relaunch required, `tw11`
again). **Both breakpoints fired for our exact call** (identified the same
way via `R12=0x00030010`, plus a consistent entity pointer `0x7FF72CB8A630`
appearing as `RDI` at the first breakpoint and as `RAX` -- the return value
register -- at the `RET` breakpoint). **The constructor's `RET` returned a
valid, non-null entity pointer for the exact call that went on to crash the
whole game moments later.**

**Conclusion, live-confirmed (not just static analysis): `fnc_spawn_world_gimmick_entity`
itself is NOT the bug.** It completes cleanly end-to-end, every time, for
both the working and the crashing case. The crash happens strictly AFTER
this function returns -- either in `l_spawn_enemy`'s own trivial post-call
code (a null check and two Lua pushes -- low-risk, but not literally
impossible) or, far more likely, in some OTHER per-frame system that
processes the freshly-built entity on a later frame (rendering, AI tick,
animation, physics/collision). This reframes Large Body's session-7 symptom
identically: "entity became visible, then the game froze" was always
consistent with "construction succeeded, something AFTER it broke" -- now
confirmed for this creature too, just with a crash instead of a hang as the
downstream outcome.

**Next session should start here**: the search space is no longer "one
function's decompile" -- it's "whatever per-frame subsystem(s) touch a
newly-constructed entity next frame." Concrete approach: rather than
guessing which system, set a broad net of non-blocking breakpoints (or use
`FUN_1402aacd0`'s registration mechanism, `FUN_140284660`/`670`, as a model
for finding per-frame callback registration generally) on whatever
functions read the entity's def-kind-2/5-specific fields set up in this
constructor (`entity+0x134`, `+0x144`/`+0x148`/`+0x14c`, the `+0x374` flag
bits set along this path) shortly after construction, OR -- probably more
tractable -- reproduce with a debugger set to break (not just log) on the
FIRST unhandled exception/access violation system-wide once armed right
before the spawn call, so CE's own crash-catching stops execution AT the
fault instead of after the process is already gone. This wasn't tried this
session (only non-blocking logging breakpoints were used, which don't catch
unhandled exceptions -- they just log addresses already known to be
interesting). Also worth trying: does the SAME entity pointer/slot crash
consistently if spawned again with a hardware WRITE watchpoint armed on
some of its own fields, the same per-thread-across-all-37-threads technique
sessions 3/4 already validated for a different question.

**Tooling note reinforced this session**: earlier in this same session, an
attempt to identify a room's native creatures by requesting a large
`read_memory` dump and visually scanning/hand-indexing into the returned
byte array (to guess record boundaries and field offsets by eye) produced
unreliable results (a `read_string` at a hand-computed offset came back
empty/garbage where a real name string should have been). Switching to a
small `pymem` script that parses the table programmatically (proper struct
offsets, not eyeballed array indices) immediately gave clean, consistent
results. This is the same lesson as the hand-transcription warnings already
in [[feedback_ce_live_code_injection_safety]], but generalized: it's not
just hand-*typing* a memory dump that's unreliable, hand-*parsing* one
(manually indexing into a large tool-returned byte array) is the same
failure mode and should be avoided the same way -- write a script.

## Session 9 (2026-07-22): a second, earlier bug found and live-confirmed -- `fnc_spawn_world_gimmick_entity`'s kind==3 setup reads garbage from an unpopulated per-species resource table

Picked up at session 8's stopping point (search per-frame consumers of the
def-kind-2/5 fields). CE's MCP bridge only exposes non-blocking *logging*
hardware breakpoints or per-thread breakpoints -- no "break on first
unhandled exception system-wide" primitive -- so this session followed the
doc's alternate plan instead: find what reads the fields the constructor
sets up, via Ghidra cross-references, and arm logging breakpoints on the
real candidates.

### First, a full static sweep of the def-kind-2/5 post-construction chain (three NEW bugs found, not yet live-confirmed)

`get_xrefs_to` on the entity pool base turned up a cluster of sibling
functions right after `fnc_spawn_world_gimmick_entity`/`fnc_select_tgt_entity`
in address space. `FUN_140292470` is the real per-frame entity-tick function
(iterates the same 96-slot pool every frame for every category-3 entity) --
near its end it checks `entity+0x374` bit `0x10000` (the EXACT flag the
def-kind-2/5 branch sets) and, if set, resolves `entity+0x144`
(`entity+0x51*4`, the EXACT field that branch writes) and passes it to
`FUN_1402bd390`. This is the "next frame" consumer session 8 was looking
for. Tracing the whole chain found three previously-unknown bugs, all the
same bug CLASS already established twice in this investigation (an
unbounded/unchecked resource-pool lookup):

- **`FUN_1402bd5b0`** (a 64-slot state-record pool at `DAT_142dc7be0`,
  stride 0x758): if all 64 slots are in use, the scan loop falls through to
  `ret` (disassembly-confirmed at Steam runtime `base+0x2bd5d4`) with `RAX`
  still pointing at the LAST (already-in-use) slot -- hands the caller
  someone else's live slot instead of failing.
- **`FUN_1402bd420`**: its own 32-slot byte-buffer scan (bitmap at
  `DAT_142de51e0`, buffers at `DAT_142db7be0`, stride 0x800) has no true
  exhaustion check either -- full pool writes one byte past the 32-byte
  bitmap and `memset`s 0x800 bytes just past the buffer region.
- **`FUN_1402bd390`**: if the resolved pointer's computed pool index isn't
  in `[0, 0x20)`, it calls `__report_rangecheckfailure()` (disassembly-
  confirmed call site at `base+0x2bd3e4`) -- a hard, unrecoverable abort.

Armed all three as non-blocking logging breakpoints (`bd390_entry`,
`bd390_rangecheckfail`, `bd5b0_pool_exhausted`) and ran a control
(native-reuse) spawn: only the harmless entry breakpoint fired (twice, on
unrelated entities' normal despawns) -- neither failure path fired, matching
the theory that these paths are silent in ordinary play. **The actual
fresh-load-fallback repro was never re-run with these three armed** -- the
session pivoted (see below) before getting back to it. These three bugs are
real (disassembly-confirmed) but still unconfirmed as an ACTUAL live crash
cause -- next session should re-arm them during a real fresh-load-fallback
repro.

### CE MCP bridge instability (recurring lesson, see also session 5)

Mid-session, after a repro attempt, the CE MCP bridge entered the same
degraded state documented in session 5 (repeated internal Lua errors,
`table.insert: bad argument #1 ... got nil`) -- this time bad enough that
the bridge's own error-dialog window kept stealing OS focus, blocking the
user from even navigating in-game. Fix: `clear_all_breakpoints` +
`debug_detach` immediately (don't keep querying the bridge while it's
spewing) -- this stopped the focus-stealing. Confirms session 5's lesson
generalizes: treat ANY bridge error spam as a signal to stop and reset
(clear breakpoints, detach, reattach), not just after a full process crash --
in this case the game process was still alive (a hang, matching Large
Body's session-7 symptom) and the bridge still degraded.

### The real find: Soldier's own "already solid" fallback path crashes too, from a DIFFERENT, earlier cause

While re-establishing a clean debugging state, the user (deliberately)
tested Soldier's fresh-load-fallback path itself -- species/creature data
that's been verified and "working" since session 5 -- in a genuinely
Soldier-less room (Accessory Shop) after a fresh save reload. Result:
`spawn_enemy` returned `false, "exception during constructor call"` -- a
real SEH-caught access violation INSIDE the direct `SafeCall` around
`fnc_spawn_world_gimmick_entity` itself (this exact message only comes from
`l_spawn_enemy`'s final constructor call, `dllmain.cpp` ~line 818-826), not
a crash or hang. Since `SafeCall` catches this cleanly (game process stays
alive and playable), this is safe to reproduce repeatedly with a debugger
attached, unlike the session-8 bugs.

Live-traced with four non-blocking logging breakpoints across the
constructor's own body (entry, the entity+0x138 read site, right after the
def-kind-2/5 block, and the constructor's `RET`): identified the crashing
call unambiguously via the `R12`/id register (`(category<<16)|slot`,
matching each room's own placement-table count at spawn time, same
technique as session 8). Result: entry hit, but the entity+0x138 checkpoint
and the post-def-kind-block checkpoint had NOT been hit by this specific
call, and RET never fired -- **the fault happens BEFORE the def-kind-2/5
branch entirely**, a different, earlier location than session 8's bug.

Two plausible early-fault theories were raised and ruled out by pure static
analysis (no live risk needed) from the full decompile of
`fnc_spawn_world_gimmick_entity` (Steam `0x140290d60`):

- **Party-member hijack** (the same bug CLASS session 5 found for
  `record+0x4c` char-id `<3`): ruled out. `FUN_140285030(charId)` linear-
  scans `g_pInventory->party_base[0..3]` (a 4-BYTE array) for an exact
  match against the char-id; Soldier's char-id (300) can never equal any
  single byte (0-255), so it always returns `0xffffffff` (not found), which
  fails the branch's `< 3` check. This branch cannot fire for Soldier, in
  any room, ever.
- **Species-resource-table out-of-bounds** (the `record+8` self-heal:
  `FUN_14038ad90(&DAT_140d2ada0 + (species << 0x12))`, a table session 5
  already documented as bounded to species index `0x40`/64 via
  `FUN_140285db0`'s bounds check): ruled out for THIS specific repro --
  the claimed slot (23, `0x17`) is well within the documented 64-slot
  bound, so the bounds check should pass cleanly. (Not proven the bounds
  check is bulletproof in general, just that it's not the cause here.)

### The confirmed root cause: a second, DIFFERENT bug -- the per-species resource-blob table itself is unpopulated garbage for a dynamically-claimed slot

Re-armed four fresh breakpoints, narrower: constructor entry, `FUN_140288460`
entry (the function the constructor calls right after resolving `record+8`
-- dispatches on the entity's own kind byte), `FUN_140287e40` entry (the
`default:` case of that dispatch, taken for kind==3/character entities), and
the constructor's `RET`. A single clean repro (one attempt, no retry needed)
gave an unambiguous result: entry, `FUN_140288460`, and `FUN_140287e40` all
fired exactly once, all matching the same call via `R12=0x00030017` (slot
23) -- but `RET` fired zero times. The fault is inside `FUN_140287e40` or
one of its callees.

`FUN_140287e40(entity, resourceTablePtr, boundsCheckResult)` decompiles to a
resource-section parser: it reads a series of small `int` fields at
`resourceTablePtr+4/+8/+0xc/+0x10/+0x14/+0x18/+0x1c/+0x20/+0x24`, treats
consecutive non-zero deltas between them as "this sub-section exists," and
for each one computes `resourceTablePtr + offset` and mints/resolves a
handle from it, then hands the result to several callees
(`FUN_1401d6760`, `FUN_1401d6230`, `FUN_14027f6c0`, `FUN_140292970`,
`FUN_1401db560`) that presumably dereference it as real structured data
(stats, animation-linkage, etc.).

The live breakpoint hit's own registers gave the exact resolved
`resourceTablePtr` value for the crashing call (`RDX` at `FUN_140288460`'s
entry = `0x7FF72B3FADA0`). Reading 64 bytes directly from that address
(`read_memory`, a safe, non-executing check) showed a smooth, monotonic
gradient of byte values (`ED ED ED ED ED E8 E8 E8 E8 E8 E8 E8 E6 E5 E5 E5 E5
E6 E5 E2 E5 E5 E2 D7 D5 D5 CC C7 C3 BB B7 AB A3 96 8F 85 7F 7A ED ED ED...`)
-- nothing like the small structured integer section-offsets
`FUN_140287e40` expects to find there. This is very likely raw
texture/animation-curve bytes or otherwise unrelated heap content, not a
real per-species resource blob at all.

**Root cause, live-confirmed today**: for a species/slot claimed via the
dynamic fresh-load path (`FindFreeLoadedSlot` + the mint-handle/
`fnc_load_gimmick_assets` trigger sequence `l_spawn_enemy` already drives),
the per-species resource-blob table entry
(`DAT_140d2ada0 + slot*0x40000`) that `fnc_spawn_world_gimmick_entity`'s
kind==3 setup path (`FUN_140288460` -> `FUN_140287e40`) reads from is
**never actually populated with real per-species metadata** by that
streaming path -- it evidently only drives the model/motion filename
resolution and `loadedSpeciesPtrTable`'s own "is it loaded" signal, NOT this
separate resource-blob table. `FUN_140287e40` then blindly parses whatever
garbage happens to be sitting there as if it were a valid section-offset
table, computing and dereferencing pointers from it -- explaining the
crash. This is DIFFERENT from (and earlier in the function than) session
8's `entity+0x144`/`FUN_1402bd390` theory, which remains plausible for the
LATER def-kind-2/5-specific bug but wasn't re-tested live this session --
both may be real, independently-unsafe gaps in the same fresh-load
fallback path.

Not yet done: single-step or narrower-breakpoint to find the EXACT
faulting instruction inside `FUN_140287e40`'s callees (not critical -- the
underlying data being garbage is already a sufficient, well-evidenced
explanation); trace what SHOULD populate `DAT_140d2ada0`'s per-species
entries for a normal, room-file-driven encounter (only real static
placement records ever seem to get valid data here -- the dynamic
on-demand streaming path this whole fallback feature depends on was never
built to also prime this table); re-test whether this reproduces
identically for other species (Large Body, `xa_ex_2020`) and whether it's
distinct from or the same underlying issue as session 8's crash/hang for
those creatures.

**Next session's real starting point (superseded below -- keep reading)**:
the plan at the time was to try priming `DAT_140d2ada0 + slot*0x40000` with
real captured data as the actual fix. This WAS attempted, twice, later the
same session -- see "Session 9 continued: the fix attempt, and why it made
things worse" immediately below for what actually happened before starting
any new work here.

### Session 9 continued: the fix attempt, and why it made things worse

Same session, continued live (user explicitly asked to keep going rather
than end the session). Implemented the theorized fix in
`native/KH1Native/dllmain.cpp`:

- A new session-lifetime cache (`g_resourceBlobs`, keyed by model filename,
  independent of `kKnownCreatures`/`g_learnedCreatures`) that heap-allocates
  a `RESOURCE_BLOB_SIZE` (0x40000-byte) buffer and captures a byte-for-byte
  copy of `DAT_140d2ada0 + species*0x40000` (Steam) /
  `DAT_140d2b880 + species*0x40000` (EGS, found this session via the EGS
  decompile of `fnc_spawn_world_gimmick_entity`'s own twin at `0x28EBD0` --
  same call site `&DAT_140d2b880 + (species << 0x12)`) whenever
  `FindNativeRecordByModel` finds a creature genuinely native to the
  current room (`CaptureResourceBlobIfNew`, called alongside the existing
  `LearnCreatureIfNew`).
- A new `speciesResourceTableRva` parameter (position 8, shifting
  model/motion/x/y/z each back by one) threaded through
  `kh1_lua_library.lua` -> `SteamGlobal_1_0_0_2.lua`/`EGSGlobal_1_0_0_10.lua`
  (`speciesResourceTable = 0xD2ADA0` Steam / `0xD2B880` EGS).
- In the fallback-template path, before ever calling the constructor: refuse
  cleanly if no captured blob exists for this creature yet ("visit a room
  where it's native once this session"), otherwise `memcpy` the captured
  blob into the CURRENT room's `DAT_140d2ada0 + species*0x40000` entry.

**First live test (after rebuild/redeploy, full game restart): still
crashed, identically.** Checked `kh1_native.log`: `CaptureResourceBlobIfNew`
HAD run successfully in Alleyway (species 34, real data captured) -- but the
crash log line came from the SAME code path as before the fix. Root cause of
THIS failure: the priming memcpy was only wired into the
`FindFreeLoadedSlot` (genuinely-fresh-slot) branch, but this specific
test's species (34) had ALREADY been marked "loaded" globally in
`loadedSpeciesPtrTable` from the earlier Alleyway visit -- so
`FindLoadedSlotByFilename` matched first and reused that slot via the
"already loaded, no need to reload" path, which never ran the priming code
at all. This revealed a real, previously-unknown fact about the engine:
**`loadedSpeciesPtrTable`'s own load-state is session-global (persists
across room transitions), but the separate `DAT_140d2ada0`-family
resource-blob table apparently resets PER ROOM** -- a slot marked "loaded"
in one room does NOT mean its resource-blob entry is populated in a
DIFFERENT room's own instance of that table.

**Fixed the ordering bug** (moved the priming check/write to run
unconditionally after either branch, not just the fresh-slot one),
rebuilt, redeployed (had to wait for the user to fully close the game --
the DLL file was locked while the process held it open), and re-tested with
the exact same repro.

**Second live test: same crash message initially, but the user then
reported the game had actually crashed** (not just the clean, SafeCall-
caught `false` return the debug panel showed) -- a delayed failure after an
apparently-clean result, the exact same "looks fine, breaks on a later
frame" shape as session 8's original bug. This is a strictly WORSE outcome
than before this fix existed (previously: a clean, safe, SEH-caught `false`
every time; now: an actual process crash at least once). Strong signal that
the 256KB `memcpy` into `DAT_140d2ada0 + species*0x40000` corrupted
something else in memory, rather than fixing the real problem.

Sanity-checked the write address arithmetic after the fact (`base +
0xD2ADA0 + 34*0x40000` = RVA `0x15AADA0`, ~21.7MB into the module) --
within the module's own ~47.5MB mapped size, so not wildly out of bounds
relative to the executable image. But "within the module" doesn't prove
this specific byte range is safe to overwrite -- the session 5 claim that
this table is bounded to 64 species slots (via `FUN_140285db0`'s bounds
check) was never independently re-verified by actually decompiling that
function this session, and `species` is a per-ROOM-LOCAL slot index (proven
elsewhere in this investigation to have no fixed global meaning) -- using
it as a raw index into what might be a differently-sized or differently-
purposed table is exactly the kind of assumption that's bitten this
investigation before (see the record+0x60/+0x64 and record+8 bucket-table
bugs, sessions 3-5).

**Reverted immediately** -- the fallback-template path (any creature not
already native to the current room) now unconditionally refuses with a
clear error message explaining why, rather than attempting the priming
write at all. This matches the SAFE (if incomplete) behavior the whole
fallback path had before this session's fix attempt: no crash, no
corruption risk, just a clean `false`. Rebuilt, redeployed to both Steam
and EGS mod folders, and RE-CONFIRMED live: the exact same repro (Soldier,
Accessory Shop, after a real Alleyway visit) now returns a clean `false`
with no crash, game fully stable afterward. `CaptureResourceBlobIfNew`
itself (a pure read into our own heap buffer, never written back to game
memory) was left in place -- it's harmless and the captured data could be
useful diagnostic material for a future session.

**Next session's real starting point**: do NOT re-enable the resource-blob
priming write without first (1) actually decompiling `FUN_140285db0` (the
bounds-check function session 5 only referenced, never inspected directly)
to independently confirm the table's real per-entry size and slot count,
rather than trusting the "0x40/64" figure secondhand; (2) considering
whether `species` (per-room-local) is even the RIGHT index into this table,
or whether the table might actually be indexed some other way that happens
to coincide with `species` in the cases tested so far; (3) if a future
attempt is made, testing it with a hardware WRITE watchpoint armed on the
target address range BEFORE the write (to see if anything else touches
that memory unexpectedly) rather than a blind live memcpy against a
real, actively-played save file -- this session's second crash put a real
save session at risk for a hypothesis that turned out to be incomplete.
Also worth revisiting: are the three `FUN_1402bd5b0`/`FUN_1402bd420`/
`FUN_1402bd390` pool bugs found earlier this session actually relevant here
at all, or was this whole investigation chasing an interaction between
TWO separate, still only partially-understood bugs in the same fallback
path?

## Session 10 (2026-07-22): the resource-blob theory was wrong -- the real bug is earlier, in the asset-load job never being serviced

Followed session 9's own checklist first, as static analysis, no game
running yet: **decompiled `FUN_140285db0`** (the bounds-check function
session 5 only ever cited secondhand):

```c
undefined8 FUN_140285db0(longlong param_1) {
  int iVar1 = (int)(param_1 - 0x140d2ada0U >> 0x12);
  if (0x40 < iVar1) return 0;
  return (&DAT_142869e18)[(longlong)iVar1 * 10];
}
```

Confirms the `0x40000` stride is real and, more importantly, that
`species` cleanly indexes BOTH the resource-blob table and
`loadedSpeciesPtrTable` (`DAT_142869e18`, stride `0x50`, matching session
6's struct math) via the exact same arithmetic -- **`species` is the
correct index**, closing session 9's other open question. Minor
correction: the real bound is `iVar1 <= 0x40` (65 valid slots, 0-64), not
"64 slots" as previously assumed -- not the crash cause, just a
documentation fix. Also decompiled the actual consumer, `FUN_140287e40`
(the `default:` case of `FUN_140288460`'s kind==3 dispatch): it only reads
NINE 4-byte ints at fixed small offsets (`+4/+8/+0xc/+0x10/+0x14/+0x18/
+0x1c/+0x20/+0x24` -- a 0x28-byte header) and treats each as a
SELF-RELATIVE offset into the same blob to compute sub-pointers, which
then get minted as handles and dereferenced. Garbage in just this small
header -- not the other ~255KB -- is what produces the wild out-of-range
pointers that crash.

**Implemented a much narrower fix than session 9's**: instead of memcpy'ing
an entire captured 256KB blob (which session 9 found corrupted something
else), zero just the 0x28-byte header before construction, so every
computed sub-pointer resolves to the blob's own base address (real, mapped
memory) instead of an unbounded jump. Also added two safety fixes session
9's version lacked: (1) a bounds check refusing any `species > 0x40`
before writing (since `FindFreeLoadedSlot` scans the full 256-slot
`loadedSpeciesPtrTable` range, a different, larger table than the 65-slot
resource-blob table -- a busy room could in principle hand back a slot
outside the blob table's real bounds); (2) wrapped the write itself in
`__try`/`__except` (it had no `SafeCall`-equivalent protection before).

**Live-tested three times** (Steam, room `tw11`, Soldier/`xa_ex_2010`,
species slot chosen fresh each time -- confirmed via `loadedSpeciesPtrTable`
state==0 read live immediately before each attempt, following session 6's
"forge before first attempt" lesson). All three: freeze (~10s), then a
clean `false` return, then the game crashed shortly after (once genuinely
dead each time except one attempt where the process happened to survive
the freeze -- CE could still read its memory afterward, suggesting the
"crash" symptom during a 10-second full-thread block is partly just
Windows/the user perceiving a hard hang, not necessarily distinguishable
from a real crash without checking).

**The header-zero write itself never crashed anything** -- confirmed via
the native log (`spawn_enemy: primed resource-blob header...` always
logged cleanly). But this attempt's failure turned out to be a completely
different bug than the one this fix targeted:

- Added diagnostic-only logging (no behavior change) to the existing 10s
  poll loop, printing the per-species state byte every ~2 seconds. Result,
  identical every attempt: `state=0` at every checkpoint (i=0/100/200/300/
  400) for the ENTIRE wait. The load isn't slow -- **it never starts
  progressing at all**.
- Armed a hardware logging breakpoint on `fnc_spawn_world_gimmick_entity`'s
  own entry (`base+0x290D60`) before a test attempt. **Zero hits, every
  time.** The constructor -- and therefore `FUN_140287e40`, session 9's
  entire theory about what's unsafe -- is never even reached. Whatever
  crashes, it isn't the code this session's fix (or session 9's) touched.
- The eventual crash happens strictly AFTER `l_spawn_enemy` already
  returned `false` to Lua (confirmed via the log timestamps) -- something
  outside our own call, running later, is what actually dies.

**Traced the real asset-load pipeline via decompile**, since session 5's
characterization of it turned out to be wrong in an important way:

- `fnc_load_gimmick_assets` (`FUN_140285ee0`) resolves the record via
  `fnc_find_gimmick_type_def(newId)` (a previously-documented function,
  confirmed here to correctly do an exact 32-bit id match against the
  live placement table -- NOT a wrong-record bug), zeroes the per-species
  state byte, mints a handle for the resource-blob table ADDRESS itself
  into the record's `+8` field (this is what that field's handle actually
  points at -- not model data), then calls
  `FUN_14028a900(&DAT_142868bb0, 0, FUN_140286420, 0)`.
- `FUN_14028a900` is a generic priority-queue insert (fixed-size slot
  array + sorted-linked-list overflow) -- **a genuine asynchronous job
  queue, not the synchronous call session 5 stated as "confirmed via
  decompile"**. That earlier note was wrong.
- The queue is drained once per frame by `FUN_140286200` ->
  `fnc_____main_loop(&DAT_142868bb0, 0)`, registered once via
  `FUN_140285de0` (called from `FUN_14028ac10`, a large one-time
  subsystem-init routine alongside `fnc_give_sora_all_spells` and several
  other resets -- looks like a boot/continue-load routine, not something
  scoped to specific room types).
- **Live-confirmed the drain is NOT dead**: armed a logging breakpoint on
  `FUN_140286200` and saw **thousands of hits** (1361 in a few idle
  seconds; 16924 across one full test attempt) -- the per-frame job pump
  is unambiguously running constantly. This rules out the plausible
  "periodic pump never registered in this room type" theory.
- So the drain runs, but OUR specific queued job apparently never gets
  its callback (`FUN_140286420`) invoked while we're watching (confirmed
  by the state byte staying at exactly 0). Root cause of THAT is not yet
  found -- candidates not yet checked: whether `FUN_14028a900`'s insert
  actually linked our job into the same list `fnc_____main_loop` reads
  (a byte-offset/pointer-unit re-check of both functions together
  suggested it should, but this was reasoned from decompile, not
  independently live-verified with a memory read of the pool's own list
  head); job starvation by priority ordering (we always pass priority 0);
  or whether `FUN_140286420` DOES eventually get invoked well after our
  10s poll gives up (consistent with the delayed crash), and faults on
  its own the first time it actually runs, on the game's own thread with
  no `SafeCall` equivalent protecting it.

**Reverted again**: the fresh-load fallback path once more unconditionally
refuses, with a message explaining the real (still open) root cause.
Rebuilt and redeployed (Steam + EGS). `kh1_native.dll`'s
`l_spawn_enemy` comment block has the full session 10 postmortem inline.

**Next session's real starting point**: arm a hardware logging breakpoint
directly on `FUN_140286420`'s own entry (not just the drain/constructor)
before a test attempt, and let the game sit for well over 10 seconds
(maybe a full minute) after the expected freeze+refusal to see if it ever
fires at all, and with what register state, to finally confirm whether
this job is (a) never dispatched at all (a queue-linkage bug), (b)
dispatched but repeatedly re-queuing itself without progressing, or (c)
dispatched exactly once, late, and faults there uncaught. Also worth an
independent live read of `DAT_142868bb0+0x10` (the list head
`fnc_____main_loop` reads) immediately after triggering `spawn_enemy`, to
directly confirm whether our job is actually linked in at all, rather than
inferring it from decompile alone.

## Session 11 (2026-07-22): three real bugs found and fixed, one false lead caught and retracted, and session 10's exact open question finally answered live

Long session, several distinct threads. Summarized in the order they
actually happened, including a real methodology mistake, because the
correction matters for future sessions.

### Bug 1 (fixed): the phantom-record-on-refusal bug session 6 flagged and never fixed

Session 6 explicitly flagged this ("Next session should apply the same
hoist-before-mutation fix to these paths too") and it sat unfixed for five
sessions. `l_spawn_enemy` was publishing the spliced placement-table
record (`*tablePtrAddr = newTable; *tableCountAddr = oldCount + 1;`)
**before** the load-trigger/poll/timeout logic that follows it. Any
refusal after that point -- the asset-load-timeout refusal in particular --
left a permanent, half-built, never-constructed phantom record spliced
into the room's LIVE placement table. Live-reproduced this session: a
genuinely fresh-slot spawn attempt timed out, logged and returned a clean
`false`, and the game froze then crashed moments later anyway -- the
exact "clean false now, crash later" shape every session since 8 has
observed, this time with the table left in a half-mutated state as a
concrete contributing hazard. **Fixed**: every refusal path from the
record-build point onward now either happens before the publish, or
explicitly rolls the publish back (`*tablePtrAddr = oldTable;
*tableCountAddr = oldCount;`) before returning `false`, so a refusal is a
true no-op on the live table again.

### A false lead, caught and retracted: "loadAssetsFnRva is garbage" was wrong

While investigating why the trigger call inside the `needsLoad` block
sometimes threw a `SafeCall`-caught exception, disassembling around
`loadAssetsFnRva` (`0x285EE0` Steam, cited since session 5 as
"`FUN_140285ee0` in Ghidra") via the Ghidra MCP tools found what looked
like a smoking gun: `0x285EE0` fell inside the 4-byte relative-displacement
operand of a `CALL 0x140286c10` instruction belonging to a different,
larger function (`FUN_140285eb0`, 0x285EB0-0x2862C8) -- not on any
instruction boundary at all. This was written up, and the fresh-load path
was disabled again on the theory that this address had been undefined
behavior for six sessions.

**This was wrong**, caught by live-verifying before trusting it further:
disassembling the same address directly in the *running game process*
(via the CE MCP bridge, not Ghidra) showed a completely different, clean,
valid function prologue (`mov [rsp+08],rbx`, immediately preceded by
proper `CC CC CC CC` alignment padding after the prior function's own
`RET`) -- a textbook real function entry, matching everything sessions
5-10 already documented about it (species-byte read at `+0x55`, a call to
the real, correct `fnc_resolve_resource_handle` at `0x38ADC0`, etc. -- see
the full live trace below). **Ghidra's loaded project database does not
match the actual currently-installed game build** -- its function-boundary
analysis has apparently drifted (possibly stale from before a Steam
update, or from a different capture) relative to the real live bytes.
Every prior Ghidra-only conclusion in this whole investigation happened to
still hold up when spot-checked live, but this is the first time they
actually diverged, and it produced a completely wrong root-cause theory
that would have been shipped if not for the live cross-check.

**Lesson for future sessions, elevated to a hard rule**: never trust a
Ghidra disassembly/decompile of this binary as ground truth for what the
*live, running* game actually executes without spot-checking the same
address's raw bytes via the CE MCP bridge's own `disassemble` tool first.
Ghidra is fine for exploring call graphs, xrefs, and getting oriented, but
the live process is the only real source of truth for "is this address
actually correct" -- the same "smoking gun" caution already applied to
live memory captures ([[feedback_ce_live_code_injection_safety]]) turns
out to apply to static analysis tooling too, just via a different failure
mode (stale database instead of misleading data).

The real cause of the crash that prompted this detour was simpler: an
earlier fix *this same session* had deferred the table publish (see Bug 1
above) too far -- past the load-trigger call itself. But
`fnc_load_gimmick_assets` resolves its own target record by looking it up
via `newId` in the live placement table (confirmed by live trace below,
the `CALL 0x7FF72A0D7B40` at the very top of the function) -- it needs the
record already published to find it. Deferring the publish past this call
broke the trigger's own internal lookup, which is what actually crashed.
Fixed by publishing early again (before the trigger) and rolling back on
every refusal after that point instead of deferring the publish itself
(see Bug 1's fix).

### Bug 2 (fixed): the "already loaded elsewhere this session" reuse path had zero room-local collision checking

Discovered live, and it's a real, previously-unrecognized hazard distinct
from anything chased before. Repro: a Soldier fallback-spawn succeeded
earlier in one room (native there), marking local slot 28 as loaded
session-globally with cached filename `xa_ex_2010.mdls`. A later
fallback-spawn of Soldier in Accessory Shop (where Soldier is not native)
went through `FindLoadedSlotByFilename`, which matched slot 28 purely from
the session-global `loadedSpeciesPtrTable` scan -- with **no check
whatsoever** for whether Accessory Shop's own placement table already used
local slot 28 for a real, unrelated native record. It did. First call:
something invisible, uninteractable, no model, but battle mode triggered
(a genuine collision -- our clone spliced on top of Accessory Shop's own
slot-28 occupant). Second identical call: game crashed outright.

This is the same collision-risk *class* session 5's "Foundational
correction" already named (species is a per-room-LOCAL slot index with no
fixed global meaning) but had only ever been guarded for the `needsLoad`
(`FindFreeLoadedSlot`) branch, and even there only against the
session-global table, never against the *current room's own* placement
table. **Fixed**: added `RoomHasNativeSpecies(oldTable, oldCount,
species)`, which scans the current room's own placement records for the
chosen species number, applied to both the `FindLoadedSlotByFilename`
reuse branch and the `FindFreeLoadedSlot` branch. Refuses cleanly if the
room already has a different creature natively using that local slot
number.

### The original mystery, finally answered live: session 10's exact open question

Session 10 ended not knowing whether the queued asset-load job was (a)
never dispatched, (b) dispatched but stuck re-queuing, or (c) dispatched
exactly once, late, and faults there uncaught. Answered this session with
a two-breakpoint live trace, using the full live disassembly of
`fnc_load_gimmick_assets` (`0x285EE0`, now confirmed genuinely correct --
see above) to find the exact instruction that hands off per-job context:

```
7FF72A0D5EED - call fnc_find_gimmick_type_def   ; resolve record by newId (rbx = result)
7FF72A0D5EF5 - movsx eax,[rbx+55]               ; species byte
7FF72A0D5F23 - mov byte [DAT_142869dd3+species*0x50],00   ; zero the state byte (loadedSpeciesPtrTable-3)
7FF72A0D5F27..5F34 - mint a handle for (DAT_140d2ada0 + species*0x40000), store at [rbx+8]
7FF72A0D5F3F - lea r8,[FUN_140286420]           ; the callback
7FF72A0D5F48 - lea rcx,[DAT_142868bb0]          ; the queue
7FF72A0D5F4F - call FUN_14028a900               ; enqueue (returns job slot in RAX)
7FF72A0D5F54 - mov [rax+20],rbx                 ; <-- job slot's +0x20 = OUR RECORD POINTER
```

Armed one breakpoint at `0x7FF72A0D5F54` (captures the job-slot address in
`RAX` at the moment it's linked to our record) and a second at
`FUN_140286420`'s own entry (`0x7FF72A0D6420`). Triggered a genuine
fresh-load repro (Soldier, Accessory Shop, fresh game session so nothing
was preloaded). Result:

- `job_slot_capture` hit once: `RAX = 0x7FF72C6B8C00` (our job's slot),
  `RBX = 0x1F087320780` (our record), timestamp `T`.
- `job_callback_entry` hit once: `RCX`/`RDI = 0x7FF72C6B8C00` -- **the
  exact same job-slot address** -- at timestamp `T+10` (ten seconds
  later, matching the poll loop's own ~10s timeout almost exactly).

**Answer: (c).** The job is genuinely dispatched, not stuck and not
dropped -- just late, arriving right around the same moment our poll loop
gives up and refuses. `l_spawn_enemy` had already returned `false` to Lua
well before this callback fired. `FUN_140286420` then runs on the game's
own thread with no `SafeCall`/`__try` equivalent protecting it, for a
species whose data is presumably still incompletely set up (the state
byte never got past 0 during our whole 10s watch) -- this is almost
certainly where the actual fault happens, though the exact faulting
instruction inside `FUN_140286420`'s own body (or whatever it calls) was
not pinned down this session.

**Next session's real starting point**: `FUN_140286420` itself was never
decompiled/traced this session (only its entry address was confirmed
correct and its dispatch confirmed real) -- do that first, live-verifying
against actual running bytes the same way this session's correction did,
not trusting Ghidra's static labels for it blindly. Use the same
job-slot-capture technique (the `+0x20` record-pointer field is a reliable
way to identify OUR specific invocation among any ambient/unrelated jobs
using the same shared callback) to arm a breakpoint deep enough inside to
catch the actual fault, or to watch what specifically it reads from the
still-`state==0` record it's handed. Also worth checking: does the
~10-second delay scale with anything (poll timeout is coincidental, or is
there a real ~10s latency somewhere in the engine's own asset-streaming
pipeline for a cold load?) -- try a much longer poll (60s+) once to see if
the callback ever fires EARLIER than 10s when nothing is racing it.

The fresh-load fallback path remains deliberately disabled (clean refusal
before ever reaching `fnc_spawn_world_gimmick_entity`) -- this session
did not change that decision, just added two real bug fixes (phantom
record, room-local collision) that apply regardless of whether/when that
path is eventually re-enabled, and finally identified the precise
mechanism (not just the symptom) of the delayed-crash mystery.

## Session 12 (2026-07-22)

Picked up mid-stream: session 11's phantom-record-rollback and room-local
collision-guard fixes were already applied in the working tree but never
committed. Continued from there, initially planning only to finish
session 10/11's leftover thread (trace `FUN_140286420`'s body to find the
exact faulting instruction in the delayed-async-job mystery).

### A real bug found first, before any live tracing

Re-reading `l_spawn_enemy` while setting up, `kh1_lua_library.lua`'s own
doc comment for `spawn_enemy` was found to describe session 9's ALREADY-
REVERTED active-priming behavior for the fresh-load path (claims it primes
`speciesResourceTable` and calls the constructor) -- pure doc/code drift,
never updated when the C++ was reverted back to a clean refusal. Confirmed
the actually-deployed DLL matched the repo's current (reverted) source via
a SHA256 hash compare, ruling out a stale-deploy explanation. **Not yet
fixed this session** -- the Lua doc comment still needs updating to match
reality.

### Bug found and fixed: the stale-handle re-mint was scoped too narrowly

While setting up to trace `FUN_140286420`, the user tried a routine
fallback spawn of Soldier in `tw11` (no debugger attached yet) and got
`spawn_enemy: exception during constructor call` -- a SafeCall-caught
crash, not the expected clean fresh-load refusal. The debug log showed
`spawn_enemy crashed: spawnFnRva=0x290d60 id=0x30010 species=28`, with NO
preceding "captured resource blob" line -- meaning it did NOT take the
native-match branch (`FindNativeRecordByModel`), and no poll-loop log
lines either -- meaning it did NOT take the fresh-load (`needsLoad`)
branch. Only one branch fits: `FindLoadedSlotByFilename`, "already loaded
elsewhere this session" -- believed fully solid since session 8, now
crashing for the first time.

Read the room's live placement table directly (17 records after the
crash -- see the phantom-record finding below) and confirmed `tw11`'s 16
real native records have NO species=28 among them (natives: 45, 47, 0, 12,
21, eleven `255`s) -- ruling out a native-record false-positive match.
Read `loadedSpeciesPtrTable`'s state/cached-filename for slot 28 directly:
`state=6`, `cachedName="xa_ex_2010.mdls"` -- a completely legitimate-
looking "already loaded" hit, exactly what `FindLoadedSlotByFilename` is
supposed to trust.

Root cause, found by direct comparison rather than more live tracing: read
the crashed record's `record+0x60`/`+0x64` (model/motion filename resource
handles) back from live memory -- `0xB020808E`/`0x414B808E` -- and compared
byte-for-byte against `kKnownCreatures`' hardcoded Soldier template bytes
at the same offsets (`dllmain.cpp` lines ~349-357). **Identical.** Session
5 already established (and fixed, but only for the `needsLoad` branch) that
a raw captured handle number is presumptively invalid outside the session
that minted it -- the bucket table is rebuilt fresh every process launch.
`kKnownCreatures`' bytes are baked in at COMPILE TIME, from whatever
session originally captured them; using them unminted in the reuse-
elsewhere branch is exactly the bug class session 5 fixed elsewhere, just
never extended to this branch because that branch's re-mint block was
gated on `needsLoad` (false here) instead of the broader `usedFallback`.

**Fix**: broadened the existing re-mint-fresh-handles block (previously
`if (needsLoad)`) to run for `if (usedFallback)` instead -- covers both
the reuse-elsewhere and fresh-load sub-cases. Added the
`mintHandleFnRva == 0` guard (previously only checked for the fresh-load
sub-case) to the shared `usedFallback = true;` point so it protects both.
Re-tested live: the mint now genuinely produces different bytes each
session (confirmed via a temporary diagnostic log -- see below) -- **but
the SAME crash still happened**, proving this was a real, worth-keeping
fix, but not the (sole) cause.

### Bug found and fixed: phantom-record rollback missing in two more refusal paths

While reading the crash path, noticed the final `!ok` (constructor
crashed) and `result == 0` (constructor refused, budget full) refusal
paths never rolled `*tablePtrAddr`/`*tableCountAddr` back to `oldTable`/
`oldCount`, unlike every other refusal in the function (a bug class first
found and partially fixed in session 11). Confirmed live: after the
species=28 crash, the room's placement table read back at count=17 (one
phantom record) instead of the real 16. Fixed both paths to roll back,
matching the established pattern; re-tested and confirmed the count
correctly returns to 16 after a refused/crashed attempt.

### Build/deploy gotcha: stale mspdbsrv/PDB lock

Rebuilding after these fixes hit `LINK : fatal error LNK1201: error
writing to program database` even with 885GB free disk space. Cause: a
leftover `mspdbsrv.exe` (MSBuild's shared PDB-writer helper process) or a
stale `.pdb` from an earlier build held the file open. Fix: kill
`mspdbsrv.exe` (safe -- MSBuild respawns it) and delete the stale `.pdb`
before rebuilding. Hit this same issue on a later rebuild too; the fix
worked both times. Worth trying first before assuming a build config
problem.

### Diagnostic added: pre-construct field dump

Before the next test, added a temporary `LogDebug` call right before the
`fnc_spawn_world_gimmick_entity` call, dumping `species`/`usedFallback`/
`needsLoad`/`handlesMinted`/`record+8`/`record+0x60`/`record+0x64`/
char-id/weight -- since a crash here rolls the table back (the record
itself is never freed, per session 5's "intentionally leaked" `newTable`,
but nothing else points at it once rolled back, making live forensic
reads after the fact unreliable). This directly confirmed the re-mint fix
above was working (fresh handle bytes each attempt, no "minting crashed"
log line) while the crash persisted -- ruling out the stale-handle theory
as the sole cause without more guessing. Left in place; harmless for
future sessions.

### Live bisection found the fault predates session 8's whole investigated region

Retested (new process launch, so nothing pre-loaded -- the very first
attempt took the STILL-DISABLED fresh-load path instead, species=1,
refused cleanly after the 10s poll timeout as expected, then the async
job crashed the WHOLE PROCESS after `l_spawn_enemy` already returned --
this is the pre-existing, still-open session 9-11 mystery, unrelated to
today's fix; not investigated further this session). Relaunched, got
Soldier loaded via a real native encounter first (so its global slot
reaches `state==6` through ordinary gameplay), then retried the fallback
spawn in `tw11` -- SafeCall-caught crash again (`species=34` this launch,
different slot number, same shape).

Armed the same four-checkpoint bisection session 8 used successfully on a
DIFFERENT crash: `fnc_spawn_world_gimmick_entity` entry (`0x290d60`), the
`entity+0x138` resolve call (`0x291449`), a post-block checkpoint
(`0x291498`), and the constructor's own `RET` (`0x2918d3`) -- all
reverified live via disassembly first, matching session 8's addresses
exactly (Ghidra's static labels for this function are still correct).
Retriggered the crash: **only the entry breakpoint fired** (confirmed
ours via `RCX == newId`). None of the three deeper checkpoints fired at
all. This narrows the fault to somewhere between the constructor's entry
and the `entity+0x138` resolve -- a region session 8 never needed to
examine, because that region is specific to the `kind==2/5` branch and
our spawn is `kind==3` (character/actor), a different setup path
entirely.

### Ghidra decompile found the real, universal mechanism

Rather than keep bisecting blind with only 4 hardware breakpoint slots,
decompiled `fnc_spawn_world_gimmick_entity` (`0x140290d60`) directly via
Ghidra. Found the real shared logic, unconditional on kind: right after
the kind-specific setup block, EVERY construction does

```c
lVar6 = fnc_resolve_resource_handle(*(undefined4 *)(lVar5 + 8));  // lVar5 = our record, +8 = the field we memset(0) defensively
if (lVar6 == 0) {
    uVar4 = FUN_14038ad90(&DAT_140d2ada0 + ((int)*(char *)(lVar5 + 0x55) << 0x12));  // species << 18 == species * 0x40000
    *(undefined4 *)(lVar5 + 8) = uVar4;
}
uVar8 = fnc_resolve_resource_handle(*(undefined4 *)(lVar5 + 8));
FUN_140288460(puVar13, uVar8);
```

`l_spawn_enemy` unconditionally `memset(newRec + 8, 0, 4)`s for EVERY
spawn (session 5's original defensive fix, still correct for native
clones -- see below), which means this self-heal ALWAYS fires for any
fallback-template spawn, always minting a handle wrapping the raw address
`&DAT_140d2ada0 + species*0x40000` -- a per-species 0x40000-byte "resource
blob" table, the exact one session 9 already suspected and session 10
already found a real consumer for. `FUN_140288460`'s `switch` on the kind
byte (`entity+6`) confirmed kind==3 (ours) falls into `default:`, calling
`FUN_140285db0` (the bounds-check function) then `FUN_140287e40` -- the
EXACT function pair session 9/10 already investigated, now confirmed
reachable from the reuse-elsewhere branch too, not just fresh-load.
Decompiling `FUN_140287e40` reconfirmed session 10's own finding: it reads
nine 4-byte self-relative offsets at `+4/+8/+0xc/+0x10/+0x14/+0x18/+0x1c/
+0x20/+0x24` (a 0x28-byte header) and computes further pointers from them
with no bounds checking -- garbage header data produces wild pointers that
get dereferenced by the sub-calls it makes.

Why does this never bite a NATIVE record (branch 1)? Because a natively-
placed creature's `record+8` already holds a real, valid handle from the
room's own genuine EVDL-triggered load -- the `memset(newRec+8,0,4)` still
runs for that path too, but the self-heal harmlessly re-resolves the SAME
already-correct data (matching the original session-5 comment on that
memset). The bug is specific to any FALLBACK-template spawn, where
`record+8`'s self-heal is the only thing standing between construction and
a genuinely game-controlled resource-blob region.

### Ghidra xrefs found who actually populates the blob, and why it's still unsafe

Searched Ghidra for cross-references TO `DAT_140d2ada0` (not just reads --
who WRITES real content) and found `FUN_140286290` among the hits -- the
same function identified only by raw disassembly earlier this session as
`FUN_14028bc10`'s own "stage 2" completion callback (see the abandoned
`FUN_140286420` tracing detour above). Decompiling it found the real
population mechanism:

```c
void FUN_140286290(int param_1, undefined8 param_2, longlong param_3)
{
  // ... parses param_3's own header fields, calls sub-functions with derived offsets ...
  lVar1 = (longlong)(int)(param_3 - 0x140d2ada0U >> 0x12);   // species index recovered from WHICH 0x40000 slice param_3 points into
  (&DAT_142869dd3)[lVar1 * 0x50] += 1;                        // the loadedSpeciesPtrTable state byte we've been polling all session
  (&DAT_142869e18)[lVar1 * 10] = /* aligned pointer INTO param_3's own blob */;  // the loadedPtr field l_spawn_enemy polls for non-zero
}
```

This is decisive: `loadedSpeciesPtrTable`'s state reaching 6 and its
pointer field going non-zero (the exact two things `FindLoadedSlotByFilename`
and `l_spawn_enemy`'s poll loop both trust) are BOTH written by this same
function, keyed PURELY by which 0x40000-byte slice of `DAT_140d2ada0` a
pointer happens to fall into -- i.e., by the room-local slot NUMBER, the
same value this entire investigation has repeatedly proven has no fixed
meaning across rooms (sessions 5-6's foundational finding, re-confirmed at
the placement-table level in session 11's room-local collision bug). A
different creature using local slot 28 in some OTHER room this session
would write ITS OWN real data into this exact same global `DAT_140d2ada0`
slice and mark the exact same global state/pointer fields "complete" --
with nothing anywhere checking whether the cached filename string still
matches at the moment of read (there IS such a check in
`FindLoadedSlotByFilename`, but only against the SEPARATE cached-filename
field at `loadedSpeciesPtrTable`, not against the resource-blob's own
content, which can apparently drift independently).

Confirmed live, not just theorized: read `DAT_140d2ada0 + 28*0x40000`'s
first 40 bytes directly from the crashed process --
`00 00 00 00 00 00 00 00 02 00 F0 FF 07 37 08 41 00 3A 07 3B 00 3A 07 3B
02 00 26 00 6B 4C BB 41 76 01 FA BA 76 01 FA BA`. The header ints this
implies (`+4=0`, `+8=0xFFF00002`, `+0xc=0x41083707`, ...) are NOT small
ascending self-relative offsets the way `FUN_140287e40` expects -- some
look like floats, none look like a sane "offset table" for a 0x40000-byte
blob. This is real (non-zero, structured-looking) data, just the WRONG
shape for what's being parsed -- consistent with a different creature's
leftover data occupying this exact slot from earlier in the session, not
with plain uninitialized garbage.

### Decision: broaden the disable rather than attempt a fix

Session 9 already demonstrated live that attempting to prime this table
with real captured data is a live-tested trap (made the crash WORSE --
an actual uncaught process crash instead of a caught exception). No new
information this session changes that risk assessment; if anything it's
reinforced it, since the true owner of a given global slot number can
change moment-to-moment as the player moves between rooms, with no
mechanism currently identified for `l_spawn_enemy` to know whether IT
still owns a slot at construction time. Rather than guess at a fix,
broadened the existing `if (needsLoad) { refuse }` block to
`if (usedFallback) { refuse }` -- covering the reuse-elsewhere branch too,
with an updated message/comment. Native-record-reuse (branch 1) is
untouched and remains the only proven-safe path.

**Live-confirmed the fix**: after rebuilding and redeploying (to both
Steam and EGS, hash-verified), a native-room Soldier spawn still worked
normally (no regression), and the exact same Accessory Shop fallback
attempt that used to crash now logs
`spawn_enemy: fallback-template construction is still disabled for
species=34 (see Session 9/10/12)` and returns a clean `false` -- no
crash, no invisible entity, table count unaffected.

### Other notes from this session

- The Steam module's "stable, non-ASLR'd base" claim (first made session
  4, repeated since) held for every relaunch THIS session
  (`0x7FF6C5520000`, confirmed across 5+ relaunches) but is a DIFFERENT
  value than the `0x7FF729E50000` cited in sessions 4-11. The base is
  evidently stable within a given install/boot state but NOT a permanent
  constant across time -- don't hardcode a specific base value across
  sessions; always re-verify via `enum_modules` at the start of a new
  session before reusing any previously-recorded absolute address.
- The CE MCP bridge's debugger can be left attached to a PID that's since
  exited (observed at the start of this session, from the previous
  session's final crash) with `debug_is_debugging` still reporting `true`
  -- always check `enum_modules`/`get_process_info` actually returns real
  data before trusting a "still attached" state, not just the boolean.
- `kh1_lua_library.lua`'s `spawn_enemy` doc comment is now confirmed
  stale (describes session 9's reverted behavior) -- flagged but not
  fixed this session; a real cleanup item for next time.

### Next session's real starting point

Two independent things remain open, neither attempted this session:

1. **The pre-existing fresh-load async-crash mystery** (sessions 9-11):
   still not root-caused down to an instruction. This session's
   Ghidra-decompile technique (rather than blind breakpoint bisection)
   proved much faster and should be applied here too -- decompile
   `FUN_140286420` directly instead of re-attempting live tracing from
   scratch.
2. **Whether the resource-blob table can ever be made safe to reuse
   across rooms.** No mechanism is currently known for determining
   whether the CURRENT process still "owns" a given global slot number
   at construction time; this may require a completely different
   strategy (e.g., only trusting `FindLoadedSlotByFilename` immediately
   after triggering a fresh load in the SAME room/session, never
   reusing a slot loaded via a DIFFERENT room) rather than a targeted
   code fix. Not attempted -- flagged as a real design question, not
   just an unfixed bug.

Both the stale-handle-remint and phantom-record-rollback fixes from this
session are real, live-confirmed, and independent of either open item
above -- they should be kept regardless of how the resource-blob question
is eventually resolved.

**Session 13 (2026-07-22), pure static analysis via Ghidra (no game process
was running this session -- nothing live-tested, everything below is
decompile-only).** Picked up session 12's item 1 (decompile `FUN_140286420`
directly) and it fully resolved item 1, and unexpectedly also explains item 2.

- **Decompiled `FUN_140286420` in full.** It's the per-species async load
  *tick* function, called once per frame per in-flight species by the job
  drainer (`FUN_140286200`, per session 10). Confirmed every struct offset
  sessions 5-12 already inferred: state byte at `header+3`, model-filename
  cache at `header+4` (32 bytes), a previously-undocumented **motion**-filename
  cache at `header+0x24` (32 bytes, mirrors the model one), and a flags byte
  at `header+2`. It progresses state 0 -> 2 (model filename load/verify) ->
  4 (motion filename load/verify) -> [a `FUN_140295f60` size-check/queue
  step] -> 6 (fully done, fires the original caller's completion callback
  stored at `job+0x28`).
- **A real, previously-undocumented self-heal exists, but only at state 0.**
  When ticked with state==0, the function checks whether `header+0`
  (the slot's own "owner species" byte) still equals the species we expect;
  if not (another species claimed this local slot number since), it
  discards the stale cache and restarts the model load. **This same
  re-validation is never repeated once state reaches 2 or 4** -- a slot
  hijacked by a different room/species AFTER this species' first tick but
  before its 6th (i.e., during the outstanding several-second window) would
  go undetected by this function. Real, but not itself sessions 9-11's
  crash (see below).
- **Chased `&LAB_140286410`** (the callback address `FUN_140295f60` queues
  for later, i.e. exactly the "~10s late" dispatch session 11 caught) all
  the way down to raw bytes. It is a genuine two-instruction thunk sitting
  in the INT3 padding gap between `FUN_140286320` and `FUN_140286420`
  (`get_function_by_address` returns nothing for it -- never promoted to a
  real Ghidra Function, hence invisible to normal xref/caller tooling until
  disassembled by raw address range):
  ```
  140286410: INC byte ptr [RCX + 0x3]   ; header->state++
  140286413: RET
  ```
  **This callback is completely benign** -- it's the state++ for whichever
  async stage `FUN_140295f60` was guarding. Rules out the deferred-callback
  mechanism itself as sessions 9-11's crash site.
- **The real finding: decompiled `FUN_140285ee0` (`fnc_load_gimmick_assets`,
  the load TRIGGER, not the tick) and found it does something sessions 9/12
  never connected to this specific call site.** On every fresh load,
  *synchronously, unconditionally, before any async job is even queued*:
  ```c
  lVar3 = fnc_find_gimmick_type_def(param_1);   // = our own spliced record
  cVar1 = *(char *)(lVar3 + 0x55);               // species byte
  (&DAT_142869dd3)[(longlong)cVar1 * 0x50] = 0;  // state = 0 (session 9 already knew this)
  uVar2 = FUN_14038ad90(&DAT_140d2ada0 + ((int)cVar1 << 0x12));  // mint handle to the resource-blob slice
  *(undefined4 *)(lVar3 + 8) = uVar2;             // -> record+8
  lVar4 = FUN_14028a900(&DAT_142868bb0,0,FUN_140286420,0);  // THEN queue the model/motion tick job
  ```
  I.e. `record+8`'s handle (the field whose self-heal session 12 pinned as
  the trigger for reading `DAT_140d2ada0+species*0x40000`) is minted
  **immediately**, pointing at that resource-blob slice, completely
  decoupled from and prior to the model/motion async streaming this whole
  investigation (sessions 9-12) had been scrutinizing. The async job only
  ever governs the model/motion MESH/ANIM files -- it has no code path that
  writes real content into `DAT_140d2ada0` at all.
- **Also decompiled `fnc_find_gimmick_type_def`** (already partially
  documented from an earlier session, plate comment dated 2026-07-20) to
  rule out a simpler null-deref theory: its default table, `DAT_14296b630`,
  is confirmed to be **the current room's own live placement table**, found
  by exact 32-bit id match. Since `l_spawn_enemy` always splices its
  synthetic record into that exact table before triggering the load,
  `fnc_find_gimmick_type_def` always resolves back to our own record --
  never null, no null-deref. This function is unrelated to `DAT_140d2ada0`;
  it's a completely different, id-keyed table.

**Conclusion -- sessions 8-12's clues unify into one root cause, fully
explaining both of session 12's "next session" items as the same bug:**

`DAT_140d2ada0` is a fixed-size global table addressed purely by LOCAL SLOT
NUMBER (0-64, the same room-local `species` byte proven meaningless across
rooms since session 5), holding real per-species type-info that appears to
be populated **only** by each room's own synchronous, upfront, `.ard`-driven
initialization at room-load time -- never by the async streaming pipeline
this whole investigation has been tracing (that pipeline mints a handle
pointing INTO this table immediately and unconditionally, then spends
several seconds loading a completely separate asset -- the model/motion
mesh/animation files -- with zero interaction with the blob's actual byte
content). A fresh-load/fallback spawn requests a species the CURRENT room
never natively uses, so nothing in this session's whole call graph ever
writes real data for it into that slot; whatever's there is either
zero (never touched) or a previous room's leftover data for a different
species that happened to share the same local slot number -- exactly
matching session 9's live read (`real-looking, wrong-shaped data`) and
session 12's (`real-looking-but-wrong-shaped ... consistent with another
creature's leftovers`).

This also finally explains the "async"/"~10s late"/"post-construction"
shape of the crash (sessions 8, 10, 11) as a **red herring of timing, not
mechanism**: `l_spawn_enemy` polls for the *unrelated* model/motion state
to reach 6 before proceeding to construct the entity, so however long that
genuinely-async file load takes is simply how long the crash is delayed --
the actual fault is the entity constructor's already-documented (session 12)
`kind==3` self-heal on `record+8` blindly parsing whatever stale bytes sit
at `DAT_140d2ada0+species*0x40000`, computing a bad pointer/index that
(per session 8's own live proof that the constructor itself returns a
valid, non-crashed entity) gets stored into the entity rather than
dereferenced immediately, and only actually crashes later when some other
per-frame subsystem (rendering/animation/physics -- never identified,
and probably not worth identifying now) touches that stored bad value.

**This does not change the recommended action.** Session 9 already
live-tested priming this exact table and made the crash strictly worse (an
uncaught process crash instead of a caught, clean exception); nothing found
this session weakens that lesson -- if anything it explains WHY priming
failed: writing plausible-looking bytes into someone else's slot doesn't
help if a different room can reclaim/repopulate that exact global slot
index at any moment with no way for `l_spawn_enemy` to detect the
takeover. The `usedFallback` disable from session 12 should stay in place.
Both of session 12's flagged open items are now considered answered/closed
without further need for live debugging; the only two remaining loose
threads for a future session are the still-unfixed stale `spawn_enemy` doc
comment (flagged sessions 12 and now still not fixed) and the never-
investigated death->continue crash from session 5.

## Session 13 (2026-07-22)

Pure static Ghidra analysis, no game process running. Fixed the stale
`spawn_enemy` doc comment (finally closing that session-12 item). Decompiled
`FUN_140286420` and `FUN_140285ee0` and concluded the async model/motion
streaming pipeline never writes real content into the resource-blob table at
all -- a conclusion **session 14 partially overturned** (see below): the
pipeline *can* populate it correctly for a genuinely fresh slot, session 13
just hadn't traced the mint call far enough. No code change; the
`usedFallback` disable stayed in place either way.

## Session 14 (2026-07-23)

User re-framed the goal directly: stop treating "spawn something not native
to the current room" as closed-with-a-safe-refusal and actually pursue it as
the investigation's real target. Full session, live game running throughout
via the CE MCP bridge, many process relaunches (the bug reliably crashes the
whole game, no recovery).

### Finding 1: `fnc_load_gimmick_assets` really does mint `record+8` correctly for a fresh slot

Re-decompiled `FUN_140285ee0` (the load trigger) fresh, ignoring session 13's
conclusion, and found it does exactly this, unconditionally, every call:

```c
(&DAT_142869dd3)[species * 0x50] = 0;                    // force-reset per-slot load state to 0
uVar2 = FUN_14038ad90(&DAT_140d2ada0 + species*0x40000);  // mint a handle -> blob slice
*(record + 8) = uVar2;                                    // overwrite record+8 with it
```

This directly contradicts the assumption baked into `l_spawn_enemy`'s
existing refusal comment ("record+8 resolves to 0... [the constructor]
mints a handle wrapping `DAT_140d2ada0+species*0x40000`" as if that only
happens inside the constructor's session-12 self-heal). It doesn't need to
-- the trigger already does exactly that, correctly, for any spawn where
`needsLoad` is true, before construction is ever attempted. Traced the async
pipeline it kicks off (`FUN_140286420` -> `FUN_14028bc10` -> `FUN_140286290`,
the exact chain session 13 examined) and confirmed live (see Finding 2)
that it's a real file-load: the model filename resolves, the file loads, and
the completion callback (`FUN_140286290`) writes parsed content into that
exact blob slice.

**Practical implication**: the `needsLoad==true` (genuinely fresh species)
path and the `needsLoad==false` ("already loaded elsewhere", the one
session 12 actually live-crashed and diagnosed) are NOT the same bug. Only
the reuse path skips the trigger entirely (gated on `needsLoad` at
`dllmain.cpp`'s load-trigger call site) and so leaves `record+8` at our
forced 0 all the way to construction, which is what triggers the
constructor's session-12 self-heal into stale blob content. The fresh-load
path was never actually proven unsafe for *that specific* mechanism -- it
was bundled into the same blanket refusal.

### Finding 2 (the session's real bug): `model_path`/`motion_path` were raw, dangling Lua string pointers

Live-reproduced the crash repeatedly with `xa_ex_2010.mdls`/`.mset`
(Soldier) as a genuinely fresh species in a room without it. Armed hardware
logging breakpoints on the load-trigger entry, the async tick entry
(`FUN_140286420`), and the blob-finalize callback (`FUN_140286290`). Only
the first two ever fired -- the crash happens *inside* `FUN_140286420`
itself, on its very first tick, well after `l_spawn_enemy` had already
returned to Lua.

Disassembling `FUN_140286420` found the real mechanism: it resolves
`record+0x60` (the model-filename handle) and passes the resolved pointer
directly into `FUN_14028bc10` (a generic "queue async file load" utility),
which immediately dereferences it (`strcmp(param_1, "xl_limit.dat")`).
`dllmain.cpp` was minting that handle straight from
`p_lua_tolstring(L, 9, ...)` -- a raw pointer into the Lua VM's own string
storage, valid only for the duration of the `l_spawn_enemy` call. The async
tick that actually dereferences it runs up to ~10 seconds later (matching
the poll timeout), by which point Lua's GC is free to have collected or
reused that string. This is a genuine use-after-free in `l_spawn_enemy`
itself, unrelated to any engine mechanism sessions 8-13 spent so long on --
and since EVERY prior live crash test in this investigation went through
this exact same load-trigger path with the same raw-pointer minting, it's
plausible this bug (not the resource-blob content theory) was the real
cause behind some of those earlier crashes too, though that's not provable
in hindsight.

**Fix shipped** (`native/KH1Native/dllmain.cpp`): added a small fixed-array
string-interning cache (`InternPath`, mirroring the existing
`g_resourceBlobs` "must outlive this call" pattern already in the file --
plain `char[64]` slots in a static array, not `std::vector<std::string>`,
specifically to avoid a reallocation-invalidates-previous-pointers bug of
exactly the same shape as the one being fixed). `modelPath`/`motionPath`
are interned immediately after the null-check, before anything else uses
them. Rebuilt, redeployed to the Steam mod folder (`build.ps1` already
existed and worked cleanly). **Live-confirmed fixed**: a breakpoint at
`FUN_14028bc10`'s entry showed the resolved pointer now lands inside
`kh1_native.dll`'s own loaded module range, and a second breakpoint on the
string-copy loop inside `FUN_140286420` logged all 15 bytes of
`"xa_ex_2010.mdls"` read back correctly, one hardware hit per character,
zero corruption. Also confirmed live that `record+8` resolves to exactly
`blob_table_base + species*0x40000` (species=1 that test), matching
Finding 1 -- the destination context is correct too.

**This fix alone did not stop the crash.** Same exact symptom (game dies,
`kh1_native.log`'s last line is a clean `asset load ... did not complete
within 10000ms, refusing to construct` for the timed-out poll, nothing
logged after) reproduced 3 more times post-fix. So this was a real, worth-
keeping bug, but not *the* bug blocking the fresh-load path.

### Finding 3: the exact fault site, via Windows' own crash telemetry (a technique not used in 13 prior sessions)

After the interning fix didn't help, checked `Get-WinEvent` for Application
log Event ID 1000 ("Application Error") instead of continuing to guess
breakpoint placement blind. **This should be the first thing checked after
any KH1 crash in future sessions** -- it gives the exact faulting
module+RVA+exception code immediately, no live debugging required:

```powershell
Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000} -MaxEvents 5 |
  Where-Object { $_.Message -match 'KINGDOM HEARTS' } | Format-List TimeCreated, Message
```

Every crash after the interning fix faulted at the **identical** address:
exception code `0xc0000005` (access violation), module
`KINGDOM HEARTS FINAL MIX.exe`, fault offset `0x2b5e66` -- reproduced
**5 times in a row**, fully deterministic. (The one crash *before* the fix
faulted at a different offset, `0x10de0a`, confirming the interning fix did
genuinely change behavior, just not enough to fix it.)

RVA `0x2b5e66` resolves (Ghidra) to `FUN_1402b5e50` (`0x1402b5e50` -
`0x1402b5ee8`), a small per-frame **velocity/motion-blend utility**, called
from 11 different, unrelated sites across the entity system
(`FUN_1402998a0`, `FUN_14029b260`, `FUN_1402a9960`, `FUN_1402b4460`,
`FUN_1402b6390`, `FUN_1402b6af0`, `FUN_1402b6c10`, `FUN_1402c3960`,
`FUN_1402c4270`, `FUN_1402ca640`, plus `FUN_14029eb20`) -- not spawn-
specific code. Its 3rd argument's home struct (RSI, saved from RCX) has a
flags test at `+0x374` (`TEST dword ptr [RSI+0x374],0x2000`) and floats at
`+0x40`/`+0x44`, matching the `entity+0x374` flags field session 9 already
identified as read by the real per-frame entity tick
(`FUN_140292470`) -- strong circumstantial evidence this really is a
generic per-entity movement update, not something spawn-specific. The
faulting instruction itself, `0x1402b5e66`
(`MOVZX EDX, word ptr [RDX+2]`), dereferences the function's own 2nd
argument -- apparently null or garbage for whatever call this is.

**Leading theory (not yet live-confirmed):** `fnc_load_gimmick_assets`
unconditionally force-resets the *room-shared, session-global* per-slot
load state (Finding 1's `(&DAT_142869dd3)[species*0x50] = 0`) for whatever
species/slot number a fallback spawn picks, with no check for whether some
other currently-active, ticking entity depends on that exact slot number
right now (the existing `RoomHasNativeSpecies` guard only checks the
*current room's own placement table*, not session-wide live entity state).
If our target slot collides with something already alive and ticking,
stomping its asset-load state mid-session could corrupt data this unrelated
motion-blend function reads on a later frame -- which would finally explain
the "crash happens later, on an unrelated-looking code path" shape every
session since #8 has run into, independent of both the model-path bug and
the original resource-blob-content theory.

### Finding 4: hardware breakpoints on the exact fault instruction never fired, even across all 40 threads

Armed a hardware execute breakpoint on `0x1402b5e66` -- first via the
single-thread `set_breakpoint` tool, then (after that predictably missed
it) via `debug_set_breakpoint_for_thread` looped across **all 40 threads**
`get_thread_list` returned. Reproduced the crash an additional time with
all 40 armed (plus the original single-thread one, 41 total watch points on
the same address) -- **zero hits**, despite Windows' crash log confirming
the identical fault address for that exact attempt. `debug_is_debugging`
still reported true afterward (the CE bridge's attached-state doesn't
reliably clear on target death -- don't trust it as a liveness check,
use `get_process_list` instead).

Leading explanation: the actual crash happens on a thread that **did not
exist yet** when `get_thread_list` was called and breakpoints were armed --
i.e. a transient worker/job thread spun up specifically to service this
rarely-exercised fresh-load path, created *after* arming. A static
"enumerate once, arm those" approach structurally cannot catch a thread
that doesn't exist yet. This is a new, generalizable lesson for this
project, extending the existing per-thread-breakpoint lesson from sessions
3-4.

**Next session should start here**: either (a) hook thread creation
(`CreateThread`/`CreateRemoteThread` or a `debugger_set_breakpoint_2`-style
approach via the Ghidra debugger, which is a separate engine from the CE
MCP bridge and may have different capabilities) to arm the fault-site
breakpoint dynamically on every new thread as it's created, or (b) pursue
the room-shared-slot-collision theory statically first (check what,
concretely, native-room slot 1 -- or whatever slot a test picks -- maps to,
and whether anything else is plausibly alive and using it) before another
round of live bisection. The `usedFallback` disable should stay in place
until one of these actually confirms a fix; do not attempt to re-enable
fresh-load construction blind.

**Left in place, not yet reverted**: the `InternPath` fix (Finding 2) is a
real, independent improvement and should stay regardless of how the
`0x2b5e66` crash gets resolved -- it removes a genuine use-after-free that
was silently possible on every `usedFallback` spawn, not just the ones that
happened to trigger it visibly this session.
