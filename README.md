# KH1 EVDL Tools

Standalone Python tools for working with **Kingdom Hearts Final Mix (HD 1.5 Remix)**'s
EVDL/ARD/WDT binary script format, extracted from the
[KH1-RANDOMIZER](https://github.com/gaithern/KH1-RANDOMIZER) project so they can be
reused across other KH1 modding projects.

## Contents

- **`evdl_tool.py`** — Disassembler/assembler for KH1's EVDL/ARD/WDT binary script format.
  - `python evdl_tool.py disasm <file.evdl|file.ard>` → writes an editable `.asm` text file.
  - `python evdl_tool.py asm <file.asm>` → reassembles it back into a patched binary (the
    original binary must sit alongside the `.asm`, since its name/header is recorded by `disasm`).
  - Running it with no arguments opens a file-picker GUI.
- **`binl_tool.py`** — Viewer/editor for the remaster's `EvMsg` `.binl` dialogue files
  (`<lang>_<room>_ard<3e8+set>.binl`). The game reads room text from these, not from the
  string table inside the `.evdl`, and it walks the strings at load time, so any string can
  change length. Running it with no arguments opens a GUI (string list, editor with live byte
  count, add/save); the CLI has `dump`, `get`, `set`, `add`, `export`, `import` and `verify`.
  Text uses the same KHSCII table as `evdl_tool.py`, with `{lf}` for line breaks and control
  codes written with their argument bytes as one token, e.g. `{0x07 0C 00}`. Each string also
  carries a terminator byte: `04` for dialogue the player dismisses (talk lines, menus) and `00`
  for timed cutscene subtitles. New strings default to `04`; a menu saved with `00` closes
  instantly and deadlocks the script.
- **`find_replace.py`** — GUI/CLI tool for bulk find-and-replace across `.asm` files, with
  wildcard and regex modes.
- **`save_data_labels.json`** — Known save-data memory offsets, used by `evdl_tool.py` to
  annotate disassembly output with human-readable labels.
- **`find_replace_presets.json`** — Saved find/replace presets for `find_replace.py`'s GUI.

## `enemy_ai/` — enemy behavior scripts (`.mdls` / `.bd`)

Separate from the EVDL event format, KH1 enemies embed a **stack-VM behavior/AI bytecode**
(`ex_XXXX_NN.bd` blocks) inside their `xa_*.mdls` model files, and each enemy's paired
`.mset` file carries a small dictionary resolving the numeric motion IDs that bytecode
references to the local animation they actually play. Together these answer "what does
this enemy's AI actually do, and what does each attack look like" — entirely offline.

- **`kh1_bd_disasm.py`** — Disassembler for the `.bd` behavior bytecode.
  - `python enemy_ai/kh1_bd_disasm.py <file.mdls>` → lists the behavior blocks in the model.
  - `python enemy_ai/kh1_bd_disasm.py <file.mdls> <block|all> [--fold]` → raw instruction listing,
    or `--fold` for readable pseudocode (`push a; push b; Verb()` → `Verb(a, b)`). Native verbs
    are named from `kh1_bd_verbs.json`.
  - Save the output as `.bdasm` to get highlighting, an outline and label navigation from the
    `vscode-evs/` extension.
- **`kh1_bd_verbs.json`** — Native-verb table (name, arg count, engine address and evidence
  notes) used by `kh1_bd_disasm.py`'s `--fold` view.
- **`kh1_bd_verb_survey.py`** — Cross-enemy survey of how each native verb is used.
- **`kh1_motion_dict.py`** — Resolves a raw AI-script motion ID to the local `.mset` animation
  index it plays (`anim0000`-style numbering, matching ModelViewerWX), from the dictionary
  array a header field in the `.mset` points to.
- **`kh1_motion_ids.py`** — Ties the two together: extracts every `SetMotion`/`QueueMotion`/
  `BlendMotion` call from an enemy's `.bd` script and resolves each to its real animation index.
  - `python enemy_ai/kh1_motion_ids.py <file.mdls> [<file2.mdls> ...] [--json out.json]`
  - The enemy's `.mset` must sit alongside its `.mdls` with the same basename.

Worked example outputs are in `docs/enemy_ai/examples/`.

## `animation/` — `.mdls`/`.mset` model and skeletal animation

A from-scratch reimplementation of KH1's skeletal animation format: mesh/skeleton parsing,
keyframe sampling, and the game's own IK dispatch. **Not needed for the `enemy_ai/` tools** —
those resolve motion IDs to animation *indices* without posing a skeleton. Currently has one
known unresolved bug (Branch-A joint orientation).

- **`kh1_mdls_parse.py`** — Parses `.mdls` model files: mesh, skeleton/joint hierarchy, textures.
- **`kh1_mset_motion.py`** — Parses `.mset` motion records (also the `MMTN` blocks of map
  objects embedded in `.ard` files): keyframe tracks, the secondary control-rig chain,
  per-joint dispatch flags, one-shot instant overrides.
- **`kh1_bake_animation.py`** — Bakes a motion record into per-frame world-space joint
  transforms.
  - `python animation/kh1_bake_animation.py <file.mset> <file.mdls> <motion_offset_hex> <out.json>`

## Usage

These tools operate on `.asm`/`.evdl`/`.ard`/`.wdt` files from a modding project (e.g. the
`asm/` directory in KH1-RANDOMIZER). Drop this repo's scripts alongside such a project, or
point them at its files directly.

```
python evdl_tool.py disasm path/to/file.evdl
python evdl_tool.py asm path/to/file.evdl.asm
python find_replace.py --dry-run "Gift Table Idx *\n" "" "asm/**/*.evdl.asm"
python binl_tool.py dump path/to/UK_pp11_ard3e8.binl
python binl_tool.py set path/to/UK_pp11_ard3e8.binl 0x91 "{0x07 0C 00}Let's go!{lf}Not right now." -o out.binl
```
