# KH1 EVDL Tools

Standalone Python tools for working with **Kingdom Hearts Final Mix (HD 1.5 Remix)**'s
EVDL/ARD/WDT binary script format, extracted from the
[KH1-RANDOMIZER](https://github.com/gaithern/KH1-RANDOMIZER) project so they can be
reused across other KH1 modding projects.

## Contents

- **`evdl_tool.py`** — Command line and GUI front end for converting KH1's EVDL/ARD/WDT
  scripts to and from text, as ASM (`ev/asm/`) or EVS (`ev/evs/`).
  - `python evdl_tool.py disasm <file.evdl|file.ard>` → writes an editable `.asm` text file.
  - `python evdl_tool.py asm <file.asm>` → reassembles it back into a patched binary (the
    original binary must sit alongside the `.asm`, since its name/header is recorded by `disasm`).
  - Running it with no arguments opens a GUI that can disassemble/assemble ASM or
    decompile/build EVS.
- **`ev/`** — The event script libraries behind `evdl_tool.py`:
  - **`ev/evdl_format.py`** — The binary script format shared by ASM and EVS: opcode and
    syscall tables, KGR parsing for EVDL/ARD/WDT files, repacking edited streams, and the
    KHSCII string table.
  - **`ev/asm/evdl_asm.py`** — The ASM text format: disassembler and assembler.
  - **`ev/evs/`** — The EVS structured script language: decompiler (`lang.py`) and builder
    (`build.py`).
  - **`ev/data/`** — Names for save memory, used by both ASM and EVS:
    `save_data_labels.json` (save-data byte addresses), `bit_labels.json` (bit flags) and
    `save_data_catalog.json` (reference catalog with meanings, value tables and evidence).
    - **`ev/data/names/<script>.json`** — Optional hand-given names for one script's internals,
      per KGR: threads, entry points, memory and locals, e.g. `ev/data/names/di01a.ev.json`:
      `{"kgr 0": {"threads": {"21": "dialogue"}, "vars": {"runtime.dword[0x934]": "KAIRI_MATERIAL_1_MISSING"}}}`.
      The file name is the script's without its language prefix, so it covers every language.
- **`binl_tool.py`** — Viewer/editor for the remaster's `EvMsg` `.binl` dialogue files
  (`<lang>_<room>_ard<3e8+set>.binl`). The game reads room text from these, not from the
  string table inside the `.evdl`, and it walks the strings at load time, so any string can
  change length. Running it with no arguments opens a GUI (string list, editor with live byte
  count, add/save); the CLI has `dump`, `get`, `set`, `add`, `export`, `import` and `verify`.
  Text uses the same KHSCII table as `ev/evdl_format.py`, with `{lf}` for line breaks and control
  codes written with their argument bytes as one token, e.g. `{0x07 0C 00}`. Each string also
  carries a terminator byte: `04` for dialogue the player dismisses (talk lines, menus) and `00`
  for timed cutscene subtitles. New strings default to `04`; a menu saved with `00` closes
  instantly and deadlocks the script.
- **`wdt_tool.py`** — Read-only viewer for the per-world `<world>.wdt` files. Every value is
  shown with its file offset, its offset inside its table entry, and its raw bytes, next to a
  hex pane that highlights the selected field (click a hex byte to jump the other way).
  The parsing lives in `wdt/`: `wdt_format.py` (the parser), `wdt_music.py` (BGM names),
  `wdt_images.py` (image decoding and PNG output) and `wdt_report.py` (`dump` and `verify`);
  `wdt_tool.py` itself is only the command line and GUI.
  - `python wdt_tool.py [file.wdt]` opens the GUI (Ctrl+O to open, Ctrl+G for go-to-offset;
    double-click a row in an overview table to open that record).
  - `python wdt_tool.py dump <file.wdt>` prints every field as text.
  - `python wdt_tool.py verify [dir]` parses every `.wdt` in a folder (default
    `C:\OpenKH\OpenKHEGS\data\kh1`) and checks the layout: sections contiguous to EOF, every
    entrance pointing at a real area, every door target pointing at a real entrance, every
    BGM id present in the music table.
  - BGM ids are named from [KH1-DOCUMENTATION](https://github.com/gaithern/KH1-DOCUMENTATION)'s
    `data/sound/music.csv`. It is found automatically when KH1-DOCUMENTATION is checked out
    next to this repo; otherwise pass `--music <path>`, set `KH1_MUSIC_CSV`, or use the
    GUI's **Music table...** button. Without it the ids are shown unnamed.

  What it decodes: the section table; the **area table** (location group, field/battle BGM
  with track names, flags, Traverse Town's alternate BGM, ...) plus a **Music used** table per
  world (each track, its length/loop point, and which rooms use it as field, battle or
  alternate music); the **entrance table** (area plus Sora / party slot
  1 / party slot 2 spawn x, y, z, rot) with the KGRs that use each entrance; the **world
  script** header, string table and KGRs, with every `push N; Change_area` /
  `Start_map_change_rewrite_set` door target; the 4 text colour sets as swatches; the **world
  title logo** (TIM2) and the **dialog window texture** (256x128 8bpp), both rendered and
  exportable as PNG.
## `bd/` — enemy behavior scripts (`.mdls` / `.bd`)

Separate from the EVDL event format, KH1 enemies embed a **stack-VM behavior/AI bytecode**
(`ex_XXXX_NN.bd` blocks) inside their `xa_*.mdls` model files, and each enemy's paired
`.mset` file carries a small dictionary resolving the numeric motion IDs that bytecode
references to the local animation they actually play. Together these answer "what does
this enemy's AI actually do, and what does each attack look like" — entirely offline.

Like `ev/`, it has a low-level instruction listing (`bd/asm/`) and a C-like language built on
top of it (`bd/bds/`).

### `bd/asm/` — disassembler and assembler

- **`kh1_bd_disasm.py`** — Disassembler for the `.bd` behavior bytecode. Its decoder, stack
  analysis and native-verb table are also used by BDS and the analysis tools.
  - `python bd/asm/kh1_bd_disasm.py <file.mdls>` → lists the behavior blocks in the model.
  - `python bd/asm/kh1_bd_disasm.py <file.mdls> <block|all> [--fold]` → raw instruction listing,
    or `--fold` for readable pseudocode (`push a; push b; Verb()` → `Verb(a, b)`). Native verbs
    are named from `kh1_bd_verbs.json`.
  - Save the output as `.bdasm` to get highlighting, an outline and label navigation from the
    `vscode-evs/` extension.
- **`kh1_bd_asm.py`** — Assembler for the raw listing, so enemy AI can be edited.
  - `python bd/asm/kh1_bd_asm.py patch <in.mdls> <edited listing> <out.mdls>` → re-encodes every
    block in the listing and writes a patched copy. Labels are re-resolved, so instructions can be
    added or removed as long as the block still fits; unchanged lines keep their exact bytes.
  - `python bd/asm/kh1_bd_asm.py roundtrip <file.mdls>` → checks disassemble → assemble gives
    back identical bytes (true for all 317 blocks in the game).
- **`kh1_bd_verbs.json`** — Native-verb table (name, arg count, engine address and evidence
  notes) used by the `--fold` view, BDS and the `vscode-evs/` extension.
- **`kh1_motion_dict.py`** — Resolves a raw AI-script motion ID to the local `.mset` animation
  index it plays (`anim0000`-style numbering, matching ModelViewerWX), from the dictionary
  array a header field in the `.mset` points to. The `--fold` view uses it to annotate motion
  calls.

### `bd/bds/` — enemy AI as editable C-like source (BDS)

BDS is a C-like view of the `.bd` enemy AI bytecode, and it is **fully round-trippable**: compiling
the decompiled text gives back the original bytes exactly. Functions are written as `if`/`else if`/
`while`/`loop`/`switch` with named natives, fields (`self.target.pos`, `self.stats.hp`), glob
aliases from `bd/data/names/<block>.json`, and function references (`SetEventHandlers(@on_hit, @on_message, 0, 0)`). A
function the decompiler can't express exactly is kept as an `asm` instruction listing inside the
same file, and unreachable bytes are kept as a `data { }` hex block. Both of those round-trip too.

```
python bd/bds/lang.py path/to/xa_tz_3000.mdls -o tz_3000.bds         # decompile every .bd block
python bd/bds/build.py tz_3000.bds path/to/xa_tz_3000.mdls out.mdls   # compile back into a copy
python bd/bds/roundtrip.py [xa_tz_3000 ...]                           # check decompile -> compile is exact
```

- `build.py` writes only the blocks present in the `.bds`. Code may grow into the zero padding
  after a block (up to the next section or block); the `.mdls` layout is never moved.
- Threads, event handlers and attack callbacks are started with a function's offset/2. These are
  written as `@name` and follow the function when code moves. `build.py` warns if a moved
  function's old offset/2 still appears as a plain number.
- Rare shapes carry a mark instead of losing exactness: `if.nj`/`else.nj` (a branch without the
  compiler's usual jump to the end), `.i`/`.f` on an operator whose int/float mode isn't the one
  its operands imply, and `seed 0x....` / `~0x....` for opcode bits the compiler carried over
  from the previous instruction.
- Open `.bds` files in VS Code with the `vscode-evs/` extension for highlighting, an outline,
  go-to-definition and find-references.

### `bd/` — analysis tool

- **`kh1_motion_ids.py`** — Extracts every `SetMotion`/`QueueMotion`/`BlendMotion` call from an
  enemy's `.bd` script and resolves each to its real animation index.
  - `python bd/kh1_motion_ids.py <file.mdls> [<file2.mdls> ...] [--json out.json]`
  - The enemy's `.mset` must sit alongside its `.mdls` with the same basename.

### `bd/data/names/<block>.json`

Optional hand-given names for one enemy's script, used by the `--fold` view and BDS: its global
variables by offset and its routines by label, e.g. `bd/data/names/tz_3000.bd.json`:
`{"glob": {"840": "encounter"}, "routines": {"@L1BF4": "break_floor_hole"}}`.

## Usage

These tools operate on `.asm`/`.evdl`/`.ard`/`.wdt` files from a modding project (e.g. the
`asm/` directory in KH1-RANDOMIZER). Drop this repo's scripts alongside such a project, or
point them at its files directly.

```
python evdl_tool.py disasm path/to/file.evdl
python evdl_tool.py asm path/to/file.evdl.asm
python binl_tool.py dump path/to/UK_pp11_ard3e8.binl
python binl_tool.py set path/to/UK_pp11_ard3e8.binl 0x91 "{0x07 0C 00}Let's go!{lf}Not right now." -o out.binl
```
