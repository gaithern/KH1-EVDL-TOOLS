# KH1 EVDL Tools

Python tools for modding **Kingdom Hearts Final Mix (HD 1.5 Remix)** scripts and data, extracted from
[KH1-RANDOMIZER](https://github.com/gaithern/KH1-RANDOMIZER).

| Path | What it's for |
|---|---|
| `evdl_tool.py` | Event scripts (`.evdl`/`.ard`/`.wdt`/`.ev`) to and from text, as ASM or EVS. No arguments opens a GUI. |
| `binl_tool.py` | View and edit `.binl` dialogue files. No arguments opens a GUI. |
| `wdt_tool.py` | Read-only viewer for `<world>.wdt` files. No arguments opens a GUI. |
| `ev/` | Event script code: the binary format, `asm/` (assembler) and `evs/` (C-like language), plus `data/` labels and names. |
| `bd/` | Enemy AI bytecode (`.bd` inside `xa_*.mdls`): `asm/` (disassembler/assembler) and `bds/` (C-like language). |
| `wdt/` | `.wdt` parsing behind `wdt_tool.py`. |
| `vscode-evs/` | VS Code extension for `.evs`, `.bds` and `.bdasm` files. |

## Event scripts

```
python evdl_tool.py disasm <file.evdl>            # writes working/<file>.asm
python evdl_tool.py asm <file.asm> [output]       # original binary must sit next to the .asm
python ev/evs/lang.py <file.evdl> [-o out.evs]    # decompile to EVS
python ev/evs/build.py <file.evs> <original> <out>
```

EVS output uses names from `ev/data/` (save memory and bit flags) and, per script,
`ev/data/names/<script>.json`.

## Dialogue (`.binl`)

```
python binl_tool.py dump <file.binl>
python binl_tool.py set <file.binl> <index> "<text>" [-o out.binl] [--term 04|00]
python binl_tool.py add <file.binl> "<text>" [-o out.binl] [--term 04|00]
```

Also `get`, `export`, `import` and `verify`. Control codes are written with their argument bytes as
one token, e.g. `{0x07 0C 00}`, and `{lf}` is a line break. Use terminator `04` for dialogue and
menus and `00` only for timed subtitles: a menu saved with `00` deadlocks the script.

## World files (`.wdt`)

```
python wdt_tool.py dump <file.wdt>
python wdt_tool.py verify [dir]
```

BGM names come from [KH1-DOCUMENTATION](https://github.com/gaithern/KH1-DOCUMENTATION)'s
`data/sound/music.csv`. It's found automatically when that repo is checked out next to this one;
otherwise pass `--music <path>` or set `KH1_MUSIC_CSV`.

## Enemy AI (`.bd`)

```
python bd/asm/kh1_bd_disasm.py <file.mdls> [<block>|all]            # raw instruction listing
python bd/asm/kh1_bd_asm.py patch <in.mdls> <listing> <out.mdls>
python bd/bds/lang.py <file.mdls> -o <out.bds>                       # decompile to BDS
python bd/bds/build.py <file.bds> <original.mdls> <out.mdls>
python bd/kh1_motion_ids.py <file.mdls> [--json out.json]            # which animation each attack plays
```

BDS and the assembler round-trip exactly. BDS marks each motion call with the animation it plays
(`// -> anim0048`). Per-enemy names go in `bd/data/names/<block>.json`.
`kh1_motion_ids.py` needs the enemy's `.mset` next to its `.mdls`.
