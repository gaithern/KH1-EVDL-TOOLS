# Understanding Sephiroth's AI from the `.mdls`/`.bd` Files

A practical guide, grounded in what the original-vs-Final-Mix diff actually shows.

> **Build note:** all `0x140…` executable addresses in this document (the interpreter, hit pipeline, flinch-counter code, verb funcptrs) are from the **Steam** build (`KINGDOM HEARTS FINAL MIX.exe`, image base `0x140000000`). The **`.mdls`/`.bd` file format, the opcode set, and the native-verb *indices* are identical on the Epic (EGS) build — only the executable addresses differ. The disassembler needs no addresses to run.

---

## 1. The big mental model: KH1 AI has two layers

You will not find "if 4 flinches, counter" written as a single readable thing in the `.mdls`, because KH1 enemy AI is split across **two** places:

1. **The behavior script** (inside the `.mdls`, in the `ex_XXXX_NN.bd` blocks). This is a **bytecode program** — a list of instructions the engine runs: "play this motion," "push this distance/timer value," "call this routine," "jump to this label." It defines *what Sephiroth does and with what parameters*.

2. **The engine / interpreter** (in the game executable, not the `.mdls`). This is C code that (a) reads and runs the bytecode, and (b) maintains combat state the script reacts to — hitstun, flinch counters, phase, HP thresholds. Trigger conditions like *"4 flinches in a row or 7 total"* are almost certainly counted and tested **here**, in the executable, not in the script.

So: the script is the *screenplay*; the executable is the *director and stage manager*. To fully understand the AI you need both. The diff below tells us which screenplay lines FM rewrote; the executable tells us what the stage directions mean.

**Evidence for this split:** FM's known change is a flinch-counter with thresholds 4 and 7. I scanned Sephiroth's combat script block for the constants 4 and 7 as int and float immediates — they are **not** present as new values. The script changes are all in the *reaction* (what move plays when a counter fires), not in the *counting*. That's the engine's job.

---

## 2. File structure (verified)

`xa_ex_3000.mdls` is an offset-table archive. The parts that matter for AI:

- A sub-container tagged `06` at `0x3B8B00` holding **6 behavior programs**: `ex_3000_00.bd` … `ex_3000_05.bd`. Each begins with a `14 03 <u16 size>` header + name string, then bytecode.
- The stat block `ex_3000.bd` (no suffix) at `0x3BBB84` — HP at header+0x10 (=1800), EXP at header+0x2C (18000 → **10000** in FM).

Which behavior blocks changed between OG and FM:

| Block | Address | Diff bytes | Meaning |
|---|---|---|---|
| `_00`,`_01`,`_03`,`_05` | — | 0 | identical |
| `_02` | 0x3B9B80 | 2 | trivial |
| **`_04`** | **0x3BA500** | **1428** | **Sephiroth's combat AI — all real changes are here** |

Block `_04` grew by exactly 4 bytes (size `0x556 → 0x55A`). Everything interesting happened in this one program.

---

## 3. The bytecode, as far as the diff reveals it

I reverse-engineered these instruction patterns by watching what changed and how. Treat as a working hypothesis until confirmed against the interpreter (Section 5).

| Pattern | Likely meaning | Evidence |
|---|---|---|
| `12 0X 00 00 <4-byte float>` | **push float immediate** | `12 07 00 00 48 42` (=50.0) became `12 07 00 00 96 43` (=300.0) — the one clean float change |
| `?8 16 <u16>` | **branch / jump to script offset** | operands changed −24, −131, +4 exactly matching how much target code moved |
| `?X 0e <u16>` | **motion / action call** (play animation, do move) | `38 0e`, `35 0e`, `18 0e`, `15 0e`, `08 0e`; operands are motion IDs/labels |
| `0b …` | **call routine / invoke** | `0b 3c 03 …`, `0b 41 03 …`, `0b 4a 00 04` |
| `32 01 XX 00` | frequent push/set (register or short const) | appears everywhere between the above |

Floats in this program form a clear "attack tuning" palette: angles (±45, ±90, 120, 180, 360) and distances/timers (50, 100, 200, 300, 500, 1000). These are the knobs — approach ranges, warp distances, wind-up timers.

---

## 4. What FM actually changed in block `_04`

> **SUPERSEDED, 2026-07-16:** item (a) below was a raw-opcode guess made before the
> bytecode interpreter/verb table was solved (see `kh1-behavior-flowchart` skill,
> [[project_ai_motion_id_resolution]]). With the interpreter fully decoded and both the
> true-OG (`KH1 Vanilla Mod`) and FM `xa_ex_3000.mdls` fully traced label-by-label (see
> [[project_sephiroth_ai_og_vs_fm]]), **this is confirmed wrong**: the `50.0 → 300.0`
> edit and the surrounding rewritten bytes are the **orbiting-hazard proximity-detonation
> trigger** inside block `_04`'s summoned-hazard subsystem (a helper that decides whether
> a spawned hazard object is close enough to the player to go off) — moved from a
> ~0–50 unit melee-range band to a ~100–300 unit long-range band, plus one new gating
> native (`NATIVE_t0_0xda`). It has **nothing to do with the flinch-counter
> retaliation** described in Section 9 below. Both OG's and FM's on-hit reaction chain
> (the script routine that fires when the engine's flinch counter hits its threshold) are
> **byte-for-byte identical** — same 24-state `GetActionState` whitelist, same
> `NATIVE_t0_0xbc` checks, same "ultimate" counter-move routine. So the `.bd` script side
> of "what move plays when Sephiroth counters" is unchanged between OG and FM; if OG and
> FM are observed to retaliate differently in-game, the cause is **not** in this script
> data at all. See the note appended to Section 9 for what that implies.

Two edits, both in block `_04`, neither in the counter/reaction area:

**(a) The orbiting-hazard proximity-trigger routine was generalized.** In OG the
trigger band's center/width were hardcoded constants baked into the routine's body. FM
pulled them out into call-site parameters and added one new prerequisite native check
(`NATIVE_t0_0xda`) that didn't exist in OG at all — see the superseded-note above and
[[project_sephiroth_ai_og_vs_fm]] for the full before/after.

**(b) The `50.0 → 300.0` push** at `0x3BAA94` — this is that same routine's trigger-band
*center* parameter (OG: `loc[44]=50f`, melee-range center; FM: `loc[44]=300f`,
long-range center), not a counter-reaction value.

**(c) Jump fixups.** Several `?8 16` branch operands moved by −24 / −131 / +4 — not
gameplay changes, just labels being repointed because the new `NATIVE_t0_0xda` check
routine was inserted above them.

What is *not* here: any 4 or 7 threshold, any HP change (HP stayed 1800). The only
stat-table change is EXP 18000→10000. The counter-reaction/retaliation *move itself*
(what plays when the flinch counter fires) is genuinely unchanged between OG and FM —
see Section 9's follow-up.

---

## 5. How to actually decode the AI — step by step

### Step A — Get the interpreter (this is the key that unlocks everything)
The executable contains one function that reads these `.bd` byte streams: a big dispatch loop / `switch` on the opcode byte. Once you find it, every pattern in Section 3 becomes a known operation.

With a Ghidra project open on the KH1FM executable (and the Ghidra bridge running so I can connect):
- Search for the loader that references the behavior data, or for the dispatch loop — look for a function with a large switch indexed by a byte read from an advancing pointer.
- Map the opcodes we've already isolated: `0x0b` (call), the `0x16` jump family, the `0x0e` motion family, `0x12` (push immediate), `0x32 01` (push/set). Confirm operand widths.
- I can then annotate block `_04` instruction-by-instruction.

### Step B — Find the flinch counter in the engine
The "4 in a row / 7 total" logic lives in the hitstun/damage handler:
- Find Sephiroth's entity/actor struct. Look for a field that increments when he's hit and resets when he acts — that's the flinch counter (probably two fields: consecutive and total).
- Cross-reference the immediates **4** and **7** in comparisons within the combat/hitstun code. FM's change is very likely *right there* — either new compares, or changed constants.
- Whatever that check does on success (set a "please counter now" flag, force a script label) is the bridge back into block `_04`.

### Step C — Correlate script ↔ behavior
- In an emulator, break when Sephiroth's script pointer enters the addresses we rewrote (`0x3BAAE8` region) and watch which on-screen move fires. That confirms which `?X 0e` motion IDs map to step-slash, warp, "dodge this," instant counter.
- Build a motion-ID table (the `0e`-family operands) by matching them to observed animations.

### Step D — Diff-driven shortcut
You already have ground truth (the two behaviors). Use it: the OG reaction routine (warp+stepslash) vs the FM one (instant counter) sit at the same place in `_04`. Decoding just those ~40 bytes against the interpreter will tell you exactly which opcodes mean "warp," "play attack," and "return to idle."

---

## 6. Concrete next actions

1. **Open the KH1FM executable in Ghidra and start the bridge** — then I can connect, find the bytecode interpreter, and label block `_04` for real. This is the highest-leverage step.
2. In parallel, I can produce a **full annotated byte-by-byte listing of block `_04`** (OG and FM side by side) using the hypothesized opcode table, so you have a map to check against the interpreter.
3. Confirm the **EXP 18000→10000** and **HP 1800** by extending your Enemy Stats sheet with a boss row for `xa_ex_3000`.

The short version: the `.mdls` gives you *what Sephiroth does*; the flinch trigger that defines *when* he counters is engine-side. Block `_04` is the entire behavioral battleground, and its counter-reaction routine is exactly what FM rewrote.

---

## 7. Verified engine findings (from Ghidra — KINGDOM HEARTS FINAL MIX.exe, PC/Steam)

Program: `KINGDOM HEARTS FINAL MIX.exe`, x86-64, image base `0x140000000`. Confirmed live, not hypothesis.

### 7.1 The bytecode interpreter — `FUN_1402cc620` @ `0x1402cc620`
This **is** the `.bd` script VM. Found by xref: the string `"ex_3000_04.bd"` (@ `0x1403efa78`) is referenced from inside it. The decompilation confirms the exact encoding we reverse-engineered from raw bytes:

- Reads a **16-bit opcode**, advances PC, then `switch(opcode & 0xF)`.
- **Low nibble = instruction class**, **high byte (`opcode >> 8`) = sub-operation**, **bits 4–5 = mode** (0 = integer, 1 = float).
- It's a **stack machine**. VM state is an array: `[0]` = program counter, `[1]` = locals/data pointer, `[2]` = operand stack pointer, `[3]` = a secondary base, `[4]` = **native function table**.

Opcode class map (verified):

| `& 0xF` | Class | Notes |
|---|---|---|
| 0 | unary / stack ops | high byte selects: 0 = **end script (return)**, 0xC = dup, 0x9/0xA = negate, 0xD = logical-not, 7 = alloc+copy, etc. |
| 1 | **binary arithmetic** | add/sub/mul/div/mod/and/or/xor/shl/shr/logical — int mode (bits4–5=0) or float mode (=1) |
| 2 | **push immediate** | sub-mode `0x00/0x10` = push one float; `0x20` = read a variable; `0x30` = push an immediate block/array |
| 3 | **store / pop to memory** | base select: locals (`[1]`), globals (`[3]`), or heap |
| 4 | **unconditional jump** (relative, 16-bit) | |
| 5 | **branch if zero** | |
| 6 | **branch if non-zero** | |
| 7 | **comparisons** | `<0`, `<=0`, `==0`, `!=0`, `>0`, `>=0` (int & float) |
| 8 | **call subroutine** | sets up a locals frame, records return, jumps by relative offset — *these are the operands that shifted −24/+4 in the OG↔FM diff* |
| 9 | pointer/index add | |
| 0xA | push block copy | |
| 0xB | **call NATIVE engine function** | indexes the native table `[4]` by high byte; args popped from stack — **this is the script→engine bridge** |

So our earlier guesses were right: `12 0X 00 00 <float>` = class 2 push-immediate; `18 16` / `38 0e` = class 8 call-subroutine (jump operands); `0b XX` = class 0xB native call.

### 7.2 The engine hard-codes Sephiroth by name
Inside the interpreter's class-2 handler is a **patch table** keyed on `(script name, offset)`, gated on a mode global (`g_TxtSpeed < 2.0`, almost certainly a mislabeled difficulty/beginner flag since it only touches bosses):

```c
else if (((offset - 0x2FC & 0xFFFFFFEF) == 0) &&
         strcmp("ex_3000_04.bd", scriptName) == 0)   // offset 0x2FC or 0x30C
    value *= 0.5;   // when mode flag < 2.0
```

Other bosses are patched the same way (Atlantica `lm_1…`, Halloween `nm_3…` scripts appear as 8-byte header signatures). Takeaway: the engine reaches into Sephiroth's `_04` script at specific offsets and rescales values by mode — direct proof the two layers are tightly coupled.

### 7.3 Script drivers
The interpreter is driven by four wrappers (`FUN_1402bcc00/bcd60/bcec0/bd540`). `FUN_1402bcc00` shows the pattern: push args to the VM stack, take mutex `DAT_14298c998`, set current actor `DAT_142db7b48`, run `FUN_1402cc620`, release. Per-actor state lives at `actor+0x18` (PC) / `+0x20` (stack). Enemy AI = a cooperative VM stepped per actor per frame.

### 7.4 Where the flinch counter (4 / 7) lives — the next dig
It is **not** a script immediate (confirmed both by the byte scan and by the VM design). It is reached through a **class-0xB native call** into table `[4]`, or maintained directly in the actor's hitstun handler. To pin it:
1. Find where the native table (`actor+0x38`) is populated — that enumerates every "verb" enemy scripts can call (get distance, play motion, get flinch count, is-guarding, …).
2. In that set, find the function that returns a hit/flinch count; xref the constants **4** and **7** near a compare in the combat/hitstun update.
3. Cross-check against block `_04`'s counter-reaction (the routine FM rewrote at ~`0x3BAAE8`) to confirm the call site.

Key addresses to keep (now labeled in the Ghidra project):
- `0x1402cc620` — `KH1_BehaviorScriptInterpreter` (the VM; opcode map is in its plate comment)
- `0x1402cd310` — immediate/operand fetch helper (reads a 16-bit offset, adds a base)
- `0x1402bcc00` — `KH1_RunScriptEntry` (script-runner wrapper)
- `0x1403efa78` — string `"ex_3000_04.bd"`
- `g_pCurrentScriptActor` (`0x142db7b48`), `g_pScriptMutex` (`0x14298c998`)

---

## 8. Verified opcode semantics + decoded lengths

From the interpreter and the fetch helper `FUN_1402cd310`, each opcode is 16-bit LE with a fixed length:

| Class (`op&0xF`) | Length | Meaning |
|---|---|---|
| 0 unary/stack | 2 | operates on the operand stack (subop 0 = END script, 0xC = dup, 9/0xA = negate, 0xD = logical-not) |
| 1 arithmetic | 2 | add/sub/mul/… ; bit4–5 = int vs float mode |
| 2 push, mode `0x00/0x10` | **6** | inline 4-byte float immediate (e.g. the `50.0→300.0` change) |
| 2 push, mode `0x20/0x30` | **4** | 16-bit offset into a base region (locals/globals/heap) — references a variable or data block, *not* inline |
| 3 store | 4 | pop → `[base+off]` |
| 4 jmp / 5 bz / 6 bnz | 4 | 16-bit relative offset (×2 bytes) |
| 7 compare | 2 | `<0,<=0,==0,!=0,>=0,>0` |
| 8 callsub | 4 | relative call, sets up a locals frame |
| 9 idx-add | 2 | |
| 0xA push-block | 2 | copies from heap |
| 0xB **native call** | 2 | `table[sel][index]` — engine "verb"; args popped from stack |

**Why there's no clean flat disassembly:** block `_04` is not one linear routine. It's an entry table + multiple subroutines (reached by class-8 `callsub`) with **data arrays interleaved** (the targets of class-2 `push [base+off]` and `pushblk`). A linear sweep stays in sync through code but desyncs the moment it walks into a data array. A faithful listing requires recursive traversal starting from the block's entry-point table — a follow-up task.

### The confirmed FM changes, decoded precisely
Because we know the exact changed offsets and the opcode lengths, each change decodes cleanly in isolation:

| Offset | OG → FM | Instruction | What it is |
|---|---|---|---|
| `0x3BA502` | size `0x556→0x55A` | block header | block grew 4 bytes |
| `0x3BA5D0` | operand `0x4D2→0x4D6` | class-8 callsub target | target moved +8 bytes |
| `0x3BA61E` | operand `0x4A2→0x4A6` | callsub/branch target | +8 bytes |
| `0x3BA658` | operand `0x35F→0x347` | callsub target | −48 bytes |
| `0x3BA684` | operand `0x324→0x2A1` | callsub target | −262 bytes |
| `0x3BA6AE` | operand `0x369→0x351` | branch target | −48 bytes |
| `0x3BA7BA` | operand `0x2E3→0x2CB` | branch target | −48 bytes |
| `0x3BAA94` | float `50.0→300.0` | class-2 push immediate | a distance/timer 6× larger |
| `0x3BAAE8+` | rewritten | ~routine body | the counter-reaction routine itself |

Every one of the scattered changes is a **branch/call target fixup** — labels being repointed because the counter-reaction routine at `~0x3BAAE8` changed size. The only *gameplay* value changes are the inline float (`50→300`) and the rewritten routine body. This matches the behavioral difference exactly: the reaction Sephiroth performs on a counter was rebuilt, and everything referencing it was repointed.

### The "verbs" (native calls) Sephiroth's script uses
Class-0xB native calls are the script's interface to the engine — the actions and queries Sephiroth's AI can issue (play motion, get distance to target, check state, etc.). Enumerating the native table `g_pCurrentScriptActor → +0x38 → table[sel][index]` and naming each index is the key to reading the AI in English; it's the recommended next Ghidra task (Section 9).

---

## 9. The flinch counter (4 / 7) — status and exact next step

Confirmed **not** in the script (no 4/7 immediates; the counting is engine-side). It is reached one of two ways, and here's how to pin it:

1. **Enumerate the native verb table.** Find where `actor+0x38` (the interpreter's `param_1[4]`) is populated during actor/AI init — that array of `{funcptr, flags}` entries is every verb. One of them returns a hit/flinch count or a "should I counter now" boolean.
2. **Xref the constants.** In the combat/hitstun update that maintains Sephiroth's flinch fields, search for compares against **4** and **7**. Ghidra: search immediate operands `0x4` and `0x7` within the functions that write the actor's flinch fields, then confirm the branch leads to the counter-reaction being triggered.
3. **Tie back to `_04`.** The native verb the script calls right before its counter-reaction routine (`~0x3BAAE8`) is the query; its implementation contains the 4/7 logic.

This is a bounded but multi-step hunt (the native table lives behind actor-init, which has no symbols). It's the natural next session with the Ghidra bridge live.

### 9.1 SOLVED — the flinch counter, found live (Ghidra + Cheat Engine)

Attached Cheat Engine to the running game, value-scanned the counter while flinching Sephiroth (1→2→3→exact-value chaining), landed on a heap address that tracked his flinch tally, then set a write-watchpoint and an access-watchpoint to catch the exact code. Result — fully confirmed:

**The counter is a 16-bit field at `actor + 0x3E8`** (Sephiroth's actor confirmed at runtime as `0x142D37750`). It is *not* in the `.bd` script — it's an engine field, which is why the `4`/`7` constants never appeared in the bytecode.

Three code sites, all now labeled in the project:

1. **Increment — `KH1_RegisterFlinchAndCount` (`0x1402BFE60`)**, called from the hit pipeline:
   ```
   1402BFED1  inc   word [rdi+0x3E8]      ; ++flinch counter
   1402BFED8  movzx eax, word [rdi+0x3E8]
   1402BFEE4  mov   [rsi+0x24], eax       ; mirror to the hit record (this is what the value-scan found)
   ```
2. **Reset — inside `KH1_HitReactionUpdate` (`0x1402B7260`), tail at `0x1402B7792`:**
   ```
   1402B7792  cmp   word [rbx+0x3E8], si  ; si = 0 (observed live)
   1402B7799  jna   1402B77A7            ; if counter <= 0, leave it
   1402B779B  test  byte [rbx], 0x04     ; "in active combo/hitstun" flag
   1402B779E  jne   1402B77A7            ; if still mid-combo, DON'T reset
   1402B77A0  mov   word [rbx+0x3E8], si ; else reset counter to 0
   ```
   So the counter accumulates **only while the combo flag `byte[actor] & 0x04` is set**; the instant the combo lapses, this resets it to 0. That is precisely the "**4 flinches in a row**" (consecutive) behavior.
3. **Retaliation decision — the state-machine branch in `KH1_HitReactionUpdate`** where the hit/state counter reaches 4 (`param_1[0x1c] == 4`, with substate `[0xde] == 5`) fires the counter-attack action via `FUN_14029F7C0` / `FUN_14029FA30` (the engine's "play action / motion" calls). The separate **7-cumulative** trigger is the sibling path that doesn't gate on the `0x04` combo flag (so it survives across retaliations, matching your note that "he keeps track even after retaliating").

**Bottom line:** the `.bd` script defines *what* the counter-attack looks like, while the engine owns the *trigger* — a 16-bit flinch tally at `actor+0x3E8`, incremented by `KH1_RegisterFlinchAndCount`, gated/reset by the combo flag in `KH1_HitReactionUpdate`, and tested against 4 (consecutive) and 7 (cumulative) to launch the retaliation. Two-layer model, confirmed end to end. **Correction (see 9.2): the script routine that plays isn't the one this section originally pointed at** — that guess is now superseded.

### 9.2 Follow-up, 2026-07-16 — OG and FM's `.bd` reaction script are identical; the retaliation difference isn't here

Full label-by-label tracing of both the true-OG `.mdls` (`KH1 Vanilla Mod\xa_ex_3000.mdls`)
and FM's (`OpenKHEGS\data\kh1\xa_ex_3000.mdls`) — see [[project_sephiroth_ai_og_vs_fm]] —
found the `.bd` script's on-hit reaction chain (the routine reached when the engine's
flinch counter fires, arming `glob[20]=5/6/7` for an "ultimate" counter move) is
**byte-for-byte identical** between OG and FM: same `GetActionState` whitelist (24 IDs,
same order), same `NATIVE_t0_0xbc` value checks (24/25/34), same resulting move. The one
real script-side edit in block `_04` (§4 above) is unrelated — it's an orbiting hazard's
proximity-detonation range, not the counter-reaction.

**This means, if OG and FM genuinely retaliate differently in-game (5-in-a-row/7-total
for FM; not observed for OG), the cause has to be one of:**

1. **The engine-side counter/threshold logic differs between the true OG (PS2, a
   completely different executable) and FM** — plausible, since flinch-triggered
   retaliation reads as a FM-added combat mechanic in the first place (§1's framing).
   This is the likely explanation *if* "OG" means the real 2002 PS2 original.
2. **If "OG" instead means the `KH1 Vanilla Mod` .mdls-swap tested here** — per its
   `mod.yml`, that mod only replaces `xa_ex_3000.mdls` inside an existing FM install, so
   it still runs on the *same* FM executable, meaning the exact same `actor+0x3E8`
   counter/`KH1_RegisterFlinchAndCount`/`KH1_HitReactionUpdate` code (§9.1) would still
   apply — and since the `.bd` reaction script is provably identical too, this mod
   *should* retaliate exactly like stock FM. If it's actually observed not to, that's a
   real discrepancy worth settling live (breakpoint `actor+0x3E8` with the mod loaded,
   per §11's recipe) rather than assumed.

**Open question, unresolved:** which of the two is actually being compared when "OG
doesn't retaliate" was observed. Worth clarifying before trusting either explanation.

---

## 10. Combat hit pipeline — mapped (Ghidra, all newly labeled)

I traced the path a hit takes from landing on Sephiroth to notifying his AI:

```
KH1_ProcessHit (0x1402c6c20)
   ├─ fnc_get_btltbl_section          (battle-table lookup; pre-existing label)
   ├─ KH1_BuildHitContext (0x1402b2dc0)
   │      allocates a damage-instance from the pool at DAT_142db4710
   │      (64 slots × 0xC0 bytes), fills damage[0xb], attacker, flags,
   │      knockback, guard/counter bits; dispatches 0x8003 = position query
   ├─ KH1_ApplyDamage_FireOnHitScript (0x1402bf330)
   │      applies damage via g_pBtltbl2 scaling (+0x94/+0x95/+0x96),
   │      awards MP orbs (fnc_handle_mp_prize),
   │      then runs the actor's ON-HIT script event  (*(ctx+0x38))
   └─ sets state flag 0x20 on the actor
```

Damage scaling constants live in the already-labeled battle table `g_pBtltbl2`. The on-hit script event is the moment Sephiroth's `.bd` gets to react to being hit — that handler (a script routine) is where a flinch tally would be bumped.

**What this rules in/out:** the flinch counter (4 consecutive / 7 total) is **not a static constant** anywhere in this pipeline — it's a per-actor field on Sephiroth, incremented on flinch and reset when he acts. Static search can't cleanly isolate it in 16.5k unsymbolized functions.

## 11. The definitive next step — dynamic analysis (Ghidra debugger)

The Ghidra MCP exposes full debugger tools (`debugger_launch`, `debugger_set_breakpoint`, `debugger_read_memory`, `debugger_watch_memory`, `debugger_registers`). For a runtime counter with no symbols, this is the right instrument:

1. Launch KH1FM under the Ghidra debugger and load a save at the Sephiroth fight.
2. Breakpoint `KH1_ApplyDamage_FireOnHitScript` (0x1402bf330). Each time Sephiroth flinches it fires; the target actor pointer is in the args.
3. On the first few hits, dump the actor struct and **diff it between consecutive flinches** — the field that increments by 1 each flinch (and resets to 0 when he attacks/counters) is the flinch counter. Note its offset.
4. `debugger_watch_memory` on that field, then search static code for reads of `[actor+offset]` compared against **4** and **7** — that compare is the FM counter trigger. Set the watchpoint and let it break when the counter hits 4 to catch the exact branch.
5. That branch's "true" path calls the counter-reaction (which we already located in script block `_04` at ~`0x3BAAE8`).

This turns the 4/7 mystery from a needle-in-a-haystack static search into a two-breakpoint runtime observation.

### Functions/labels added to the project this session
- `KH1_BehaviorScriptInterpreter` (0x1402cc620) — the .bd VM, with full opcode map in its plate comment
- `KH1_RunScriptEntry` (0x1402bcc00), plus runner variant at 0x1402bd540
- `KH1_ProcessHit` (0x1402c6c20)
- `KH1_BuildHitContext` (0x1402b2dc0)
- `KH1_ApplyDamage_FireOnHitScript` (0x1402bf330)
- globals `g_pCurrentScriptActor` (0x142db7b48), `g_pScriptMutex` (0x14298c998)

---

## 12. Disassembler + native-verb harvest

Built `kh1_bd_disasm.py` — a working disassembler for the `.bd` bytecode (recursive/linear hybrid; the code stream decodes cleanly with the verified opcode lengths). It emits labeled, `END`-delimited routines with `push`/`store`/`call`/branch and named native calls.

**Native verb table — harvested live.** Breakpointed the interpreter entry, read `param_1[4]` = the global verb registry at **`0x140529FA0`** (two tables: `t0 @ 0x140529180`, `t1 @ 0x1405752D0`; each entry `0x10` bytes = `{funcptr, argcount, flags}`; flag `0x40000000` = returns a value). Then read the funcptr for every verb `_04` uses and decompiled them:

| Verb | funcptr | Meaning |
|---|---|---|
| t0 #0x0a | 0x1402B9AD0 | `RotateDeg` — angle(deg)→rotation |
| t0 #0x10 | 0x1402BB590 | `SetVec` — write a vector field |
| t0 #0x12 | 0x1402B9BF0 | `MoveByVel` — translate by speed×frametime **(the verb FM sped 6× via 50→300)** |
| t0 #0x16 | 0x1402BBA00 | `GetActor` — returns an actor/state handle |
| t0 #0x17 | 0x1402BBA20 | `MakeAttack` — calls `KH1_BuildHitContext` (launches an attack/hitbox) |
| t0 #0x4a | 0x1402BB8B0 | `SpawnObj` — allocate object + copy vector, return handle |
| t0 #0x4c | 0x1402BBAC0 | object op (FaceTarget?) |
| t1 #0x0e | 0x140395100 | `SetTimedMove` — timed directional movement (duration + per-frame velocity) |

Full index→funcptr map (incl. still-unnamed verbs) is in `kh1_bd_verbs.json`; the disassembler reads it, so naming the rest is just editing that file. With names applied, block `_04` now opens legibly:
`SpawnObj() ×2 → GetActor() → MakeAttack() → …` — i.e. Sephiroth sets up his effect objects and an attack hitbox at script start.

**New gameplay insight from this pass:** the `50.0 → 300.0` change FM made isn't an abstract constant — it's the speed argument to `MoveByVel`, so FM made that particular movement action **6× faster**.

### Deliverables
- `kh1_bd_disasm.py` — the disassembler (reads `kh1_bd_verbs.json` for verb names)
- `kh1_bd_verbs.json` — harvested verb table (extend by naming more funcptrs)
- `sephiroth_OG_disasm.asm`, `sephiroth_FM_disasm.asm`, `sephiroth_OG_vs_FM.diff`

---

## 13. Cross-enemy / cross-build validation + the disassembler tool

**The format is shared across enemies and builds.** Disassembling Shadow (`xa_ex_2020.mdls`,
from the **EGS** data set) shows the identical VM, opcodes and native verbs — `MakeAttack`,
`GetActor`, `VecAdd`, `RotateDeg`, etc. all appear. Only the **layout** differs by complexity:
bosses like Sephiroth split behavior into suffixed blocks (`ex_XXXX_NN.bd`) inside a sub-container,
while simple enemies keep a single un-suffixed `ex_XXXX.bd` block = stat/drop data followed by the
behavior code. Same building blocks (`MOBJ`, `CLS`, `ex_XXXX.bd`), arranged differently.

**Tooling (`kh1_bd_disasm.py`, in the repo root):**
- Finds `.bd` blocks anywhere (both layouts) and auto-locates the code region even when stat
  data + zero-padding precede it.
- Raw view = labeled instruction listing; `--fold` view = function-call pseudocode
  (`push a; push b; Verb()` → `Verb(a, b)`), driven by the native **argument-count table**
  harvested from the game and baked into `kh1_bd_verbs.json` (`_arity_t0`/`_arity_t1`).
- Native verbs are named from `kh1_bd_verbs.json`; naming more verbs improves both views.
- See `docs/reading_the_disassembly.md` for how to read the output and its caveats.

**Build independence:** the tool needs no executable addresses to run. The format, opcodes and
verb indices are identical on Steam and EGS; the `0x140…` addresses are Steam provenance only.
