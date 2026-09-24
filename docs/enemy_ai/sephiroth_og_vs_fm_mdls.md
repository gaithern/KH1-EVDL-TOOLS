# Sephiroth `.mdls` Comparison — Original vs Final Mix

**Files**
- Original: `xa_ex_3000.mdls`
- Final Mix: `xa_ex_3000-ec2fd073.mdls`
- Both exactly **5,867,520 bytes** (identical size → clean byte-aligned diff)

Raw diff: 1,767,276 bytes differ (~30%), but **~99% of that is just a downstream shift**, not real change. Once you account for the shift, the *actual* edits are tiny and concentrated. Here's the real story.

---

## Container layout (`.mdls` = a simple offset-table archive)

The file header is a count + a table of section offsets. There are 8 sections:

| # | Offset (orig) | Tag | Size | What it is | Changed? |
|---|---------------|-----|------|------------|----------|
| 1 | `0x80` | `MOBJ` | 904 KB | 3D model (mesh) | **Identical** |
| 2 | `0xDCC80` | `82…` | 2.99 MB | Model/texture data | **Identical** |
| 3 | `0x3B8B00` | `06…` | 12 KB | **Behavior / AI script** (sub-archive of 6 blocks) | **EDITED** |
| 4 | `0x3B8B00` | (dup ptr) | — | — | — |
| 5 | `0x3BBA00` | `CLS` | 384 B | Collision | pointers relocated only |
| 6 | `0x3BBB80` | `14 03 44 1D` | 16 KB | Param/effect block, refs `ex_3000.bd_1` | **EDITED + grew 0x100** |
| 7 | `0x3BFB00` | `A0 90 01…` | 109 KB | Effect/particle data | **Identical (moved +0x100)** |
| 8 | `0x3DA580` | `32…` | 1.79 MB | Effect/motion data | **Identical (moved +0x100)** |

**Key takeaway:** the model, textures, and the big effect/data blobs are byte-for-byte identical. Final Mix Sephiroth reuses all the original assets. Everything meaningful changed in **two places: the AI script (section 3) and the parameter block (section 6).**

---

## Why 30% of bytes "differ" but almost nothing changed

Section 6 grew by exactly **0x100 (256) bytes**. Because this archive stores sections back-to-back, everything after it slid down 256 bytes:

- Header offsets for sections 7 & 8 updated: `0x3BFB00 → 0x3BFC00`, `0x3DA580 → 0x3DA680`.
- Sections 7 and 8 verified **100% identical** when compared at `+0x100` — pure relocation.
- The `CLS` collision block's four pointers all shifted by exactly **+0x19F80** (they point into a section that moved).

So the giant "differences" at the tail of the file are an artifact of the shift. Ignore them.

---

## The real change #1 — the AI / behavior script (section 3, `0x3B8B00`)

This 12 KB section is a sub-archive of 6 blocks and contains a **bytecode script** that drives Sephiroth's behavior. It's a stack-machine-style instruction stream. Recurring patterns observed:

- `32 01 XX 00` — extremely common (looks like *push short constant*)
- `0b XX` — *call routine XX*
- `18 16 / 28 16 / 38 16 / a8 16` + a 16-bit operand — *branch / jump to script offset*
- Inline **float immediates** used as parameters (angles, distances, timers, durations)

The float "palette" in this script makes its purpose obvious — these are attack/AI tuning values:
`±45, ±90, 120, 180, 360` (turn/attack arc angles), `50, 100, 200, 300, 500, 1000` (distances/ranges), plus small counts and timers.

### What Final Mix actually changed in the script

1. **One routine (~1.8 KB, around `0x3BAAF0`) was rewritten.** The FM instruction stream is the original stream with instructions spliced/swapped in the middle, then it re-syncs — a localized behavior rewrite (new or altered attack logic), not a full replacement.

2. **A float parameter changed `50.0 → 300.0`** at offset `0x3BAA94` — a 6× increase to a range/timer in one routine. This is the single clearest same-offset value change.

3. **Branch/jump operands were recomputed** — the tell-tale signs that logic was inserted above them:
   - `@0x3BA684`: operand `804 → 673` (−131)
   - `@0x3BA6AE`: operand `873 → 849` (−24)
   - `@0x3BA7BA`: operand `739 → 715` (−24)
   - Several `+4` nudges (`@0x3BA5D0`, `@0x3BA61E`, `@0x3BAAB6`, `@0x3BAAE8`, `@0x3BAAEE`)

   Consistent deltas like −24 across multiple jumps = the code they target moved by that many bytes when the routine was edited. These aren't gameplay values; they're the "goto" addresses being fixed up after the edit.

---

## The real change #2 — parameter block (section 6, `0x3BBB80`)

This section references a resource string `ex_3000.bd_1` and holds a small table of round-number parameters. It **grew by 0x100 bytes** and its body was substantially rewritten (only ~16% aligned). The readable header params:

```
size/count field : 0x1D44 → 0x1DE0   (+156, grew with the section)
1800, 20, 20, 4, 25, 70, 1.0
18000 → 10000    <-- the one clean value change in this table
0, 1.0, 50, 100, 0, 0, 0, 100, 100, 100
```

One tunable dropped from **18000 → 10000**. I can't label it definitively (HP/timer/effect-duration/threshold) without the game engine to trace who reads it, but it's a deliberate, clean edit alongside the section's rewrite.

---

## Answering the two things you cared about

**AI / behavior:** This is where nearly all the action is. FM edited Sephiroth's behavior script in section 3 — one routine rewritten, a range/timer bumped 50→300, and jump targets recompiled. The bulk of *new* FM behavior data most likely lives in the section-6 block that grew by 256 bytes (its body is ~84% different). If you want to reverse the FM behavior changes, sections 3 and 6 are the entire battleground; the rest of the file is noise.

**Stat block (HP / attack / defense):** A classic numeric stat table does **not** clearly appear or change in this file. The only round-number stat-like edit is the `18000 → 10000` value in section 6. In Kingdom Hearts 1, enemy combat stats (HP, strength, defense, EXP) generally live in separate battle-parameter data rather than the per-character `.mdls`, so a full stat diff probably needs those files, not this model.

---

## How to dig further

- Focus a disassembler on section 3 (`0x3B8B00`–`0x3BBA00`) — that's the script. Map the opcodes (`32 01`, `0b`, `18 16`, `38 0e`, etc.) and the float immediates to reconstruct the state machine.
- Diff section 6 body (`0x3BBB80`–`0x3BFC00` in FM) against the original to see the 256 bytes of added content.
- If you can grab the KH1 battle/enemy parameter file for Sephiroth (not the `.mdls`), that's where a true HP/stat comparison would come from.
