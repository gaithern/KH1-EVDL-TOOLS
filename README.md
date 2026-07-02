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
- **`find_replace.py`** — GUI/CLI tool for bulk find-and-replace across `.asm` files, with
  wildcard and regex modes.
- **`save_data_labels.json`** — Known save-data memory offsets, used by `evdl_tool.py` to
  annotate disassembly output with human-readable labels.
- **`find_replace_presets.json`** — Saved find/replace presets for `find_replace.py`'s GUI.

## Usage

These tools operate on `.asm`/`.evdl`/`.ard`/`.wdt` files from a modding project (e.g. the
`asm/` directory in KH1-RANDOMIZER). Drop this repo's scripts alongside such a project, or
point them at its files directly.

```
python evdl_tool.py disasm path/to/file.evdl
python evdl_tool.py asm path/to/file.evdl.asm
python find_replace.py --dry-run "Gift Table Idx *\n" "" "asm/**/*.evdl.asm"
```
