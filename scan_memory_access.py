#!/usr/bin/env python3
"""
scan_memory_access.py - map every save-memory read and write across all KH1 event scripts.

Disassembles every script in the extracted game data (remastered *.evdl and *.ev,
top-level *.wdt and *.ard, loose *.ev such as gameover.ev) with evdl_tool, then
records for each save byte: which file / KGR / script reads or writes it, at what
width, and which bit for read_bit / write_bit.  Cross-references the result with:

  - save_data_labels.json (this repo)                    -> known label per var id
  - a Lua memory map (e.g. KH1-LUA-LIBRARY SteamGlobal)  -> Lua symbols living in the block
  - the randomizer's locations.lua                       -> AP location checks per byte

Address model (Steam 1.0.0.2, from fnc_ev_0C_read_byte):
  var id 0x000-0x8FF        save_data1[var]              (exe+0x2DE9F60 + var)
  var id 0xB00-0xC7F        save_data1[var - 0x200]
  var id 0x900-0xAFF        item/equipment data           (not part of the save block)
  var id 0xC80-0xD3F        DAT_1423baf70 region          (not part of the save block)
  var id >= 0xD40           save_data2[var - 0xD40]      (exe+0x2DEAF60 + ...)
  read_bit/write_bit n      save_data2[(n >> 3) - 0xD40], bit n & 7

save_data2 sits exactly 0x1000 bytes after save_data1, so everything is reported as one
"save offset" from exe+0x2DE9F60: save_data1[x] = x, save_data2[y] = 0x1000 + y.

Usage:
  python scan_memory_access.py --game-data C:/OpenKH/OpenKHSteam/data/kh1 --out working/memory_scan
  python scan_memory_access.py --addr 0x120                # who touches save offset 0x120
  python scan_memory_access.py --free 0x100-0x200          # untouched runs in a range
  python scan_memory_access.py --file UK_tw23d.ev          # everything one script touches
  python scan_memory_access.py --lua-globals <SteamGlobal_1_0_0_2.lua> --locations-lua <locations.lua>

Outputs (in --out): memory_map.json, accesses.csv, memory_map.md.
Queries read memory_map.json if it exists and is newer than the cache, else rescan.
"""
import argparse
import csv
import glob
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import evdl_tool  # noqa: E402

SAVE_BASE_RVA = 0x2DE9F60
SAVE2_OFFSET = 0x1000              # save_data2 = save_data1 + 0x1000
LANGS = ("UK", "US", "FR", "GR", "IT", "SP", "JP")
DEFAULT_GAME_DATA = os.environ.get("KH1_GAME_DATA", "C:/OpenKH/OpenKHSteam/data/kh1")
DEFAULT_OUT = HERE / "working" / "memory_scan"
CACHE_DIR = HERE / "working" / "scan_cache"

# Lua base symbols used by the randomizer's locations.lua (item_location_handlers) -> (global, delta)
LUA_LOCATION_BASES = {
    "chests_opened_address":        ("chestsOpened", -0x04C),
    "world_progress_array_address": ("cutsceneFlags", +0x004),
    "atlantica_clams_address":      ("OCCupUnlock", -0x057),
    "world_flags_address":          ("waterwayCutsceneFlag", -0x005),
    "soras_level_address":          ("soraStats", +0x002),
    "ansems_reports_address":       ("reports", 0),
    "olympus_flags_address":        ("continue", +0xF36),
    "event_flags":                  ("evidence", 0),
}

INS_RE = re.compile(r"^\s+(?:[0-9A-Fa-f]{8}|\?{8})\s+(\S+)(?:\s+(\S+))?")
ACCESS_RE = re.compile(r"^\s+(?:[0-9A-Fa-f]{8}|\?{8})\s+(read|write)_(byte|word|dword|bit)\s+\[(0x[0-9A-Fa-f]+)\]")
KGR_RE = re.compile(r"^# KGR\[(\d+)\]")
SCRIPT_RE = re.compile(r"^; Script (\d+)\s+\|")
WIDTH = {"byte": 1, "word": 2, "dword": 4}


# ---------------------------------------------------------------------------
# address model
# ---------------------------------------------------------------------------

def classify(var: int):
    """Return (region, save_offset or None) for a byte/word/dword var id."""
    if var < 0x900:
        return "save_data1", var
    if 0x900 <= var < 0xB00:
        return "item_data", None
    if 0xB00 <= var < 0xC80:
        return "save_data1", var - 0x200
    if 0xC80 <= var < 0xD40:
        return "dat_1423baf70", None
    return "save_data2", SAVE2_OFFSET + (var - 0xD40)


def classify_bit(bitnum: int):
    if bitnum < 0:
        sign = 7
        adj = bitnum + sign
        return SAVE2_OFFSET + ((adj >> 3) - 0xD40), (adj & 7) - sign
    return SAVE2_OFFSET + ((bitnum >> 3) - 0xD40), bitnum & 7


def fmt_off(off: int) -> str:
    if off >= SAVE2_OFFSET:
        return f"save_data2[0x{off - SAVE2_OFFSET:03X}]"
    return f"save_data1[0x{off:03X}]"


def rva_of(off: int) -> str:
    return f"KINGDOM HEARTS FINAL MIX.exe+{SAVE_BASE_RVA + off:X}"


# ---------------------------------------------------------------------------
# discovery + disassembly
# ---------------------------------------------------------------------------

def is_language_file(name: str) -> bool:
    return len(name) > 3 and name[:2] in LANGS and name[2] == "_"


def discover(game_data: Path, lang: str, include_ard: bool):
    files = []
    for ext in ("evdl", "ev", "wdt", "ard"):
        for p in game_data.rglob(f"*.{ext}"):
            if p.is_dir():
                continue
            if ext == "ard" and not include_ard:
                continue
            if is_language_file(p.name) and not p.name.startswith(lang + "_"):
                continue
            files.append(p)
    return sorted(files)


def disassemble(files, cache: Path, game_data: Path, quiet=False):
    cache.mkdir(parents=True, exist_ok=True)
    out = []
    failed = []
    for p in files:
        rel = p.relative_to(game_data).as_posix().replace("/", "__")
        target = cache / (rel + ".asm")
        if not target.exists() or target.stat().st_mtime < p.stat().st_mtime:
            old_out, old_err = sys.stdout, sys.stderr
            try:
                sys.stdout = sys.stderr = open(os.devnull, "w", encoding="utf-8")
                evdl_tool.cmd_disasm(str(p), str(target))
            except (Exception, SystemExit) as e:  # evdl_tool sys.exit()s on unreadable files
                failed.append((p.name, str(e)))
                if target.exists():
                    target.unlink()
                continue
            finally:
                sys.stdout, sys.stderr = old_out, old_err
        out.append((p, target))
    if failed and not quiet:
        print(f"{len(failed)} file(s) failed to disassemble (listed in memory_map.json meta.failed):", file=sys.stderr)
        for n, e in failed[:15]:
            print(f"  {n}: {e.splitlines()[0] if e else '?'}", file=sys.stderr)
        if len(failed) > 15:
            print(f"  ... {len(failed) - 15} more", file=sys.stderr)
    return out, failed


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

def layer_of(name: str) -> str:
    """evdl / ev = what the remastered game actually loads; wdt = world script; ard = PS2-era embedded
    copy, shadowed for English whenever a remastered .evdl/.ev of the same set exists."""
    return name.rsplit(".", 1)[-1].lower()


def parse_asm(source_name: str, asm_path: Path):
    """Yield access records from one disassembly."""
    layer = layer_of(source_name)
    kgr = -1
    script = -1
    pc = -1
    with open(asm_path, encoding="utf-8", errors="replace") as f:
        for lineno, line in enumerate(f, 1):
            m = KGR_RE.match(line)
            if m:
                kgr = int(m.group(1)); script = -1; pc = -1
                continue
            m = SCRIPT_RE.match(line)
            if m:
                script = int(m.group(1)); pc += 1   # the script header occupies one PC
                continue
            if not INS_RE.match(line):
                continue
            pc += 1
            m = ACCESS_RE.match(line)
            if not m:
                continue
            op, kind, var_s = m.group(1), m.group(2), m.group(3)
            var = int(var_s, 16)
            if kind == "bit":
                off, bit = classify_bit(var)
                yield dict(file=source_name, layer=layer, kgr=kgr, script=script, pc=pc, line=lineno,
                           op=op, width=1, bit=bit, var=var, region="save_data2", offset=off)
            else:
                region, off = classify(var)
                yield dict(file=source_name, layer=layer, kgr=kgr, script=script, pc=pc, line=lineno,
                           op=op, width=WIDTH[kind], bit=None, var=var, region=region, offset=off)


# ---------------------------------------------------------------------------
# cross references
# ---------------------------------------------------------------------------

def load_labels():
    p = HERE / "save_data_labels.json"
    labels = {}
    if p.exists():
        for k, v in json.load(open(p, encoding="utf-8")).items():
            region, off = classify(int(k, 16))
            if off is not None:
                labels.setdefault(off, []).append(v)
    return labels


def load_lua_globals(path: Path):
    """Lua memory-map symbols that fall inside the save block, keyed by save offset."""
    syms = {}
    by_off = defaultdict(list)
    if not path:
        return syms, by_off
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"\s*([A-Za-z_]\w*)\s*=\s*(0x[0-9A-Fa-f]+)", line)
        if m:
            syms[m.group(1)] = int(m.group(2), 16)
    for name, rva in syms.items():
        off = rva - SAVE_BASE_RVA
        if 0 <= off < 0x8000:
            by_off[off].append(name)
    return syms, by_off


def load_locations(path: Path, syms: dict):
    """AP locations from the randomizer's locations.lua, keyed by save offset."""
    by_off = defaultdict(list)
    if not path or not syms:
        return by_off
    txt = open(path, encoding="utf-8", errors="replace").read()
    rec_re = re.compile(r"\[(\d+)\] = \{(.*?)\n        \},", re.S)
    addr_re = re.compile(r"address = ([a-z_]+) ([+-]) (0x[0-9A-Fa-f]+),\s*bit = (\d+),\s*value = (0x[0-9A-Fa-f]+|\d+)")
    for m in rec_re.finditer(txt):
        loc = int(m.group(1)); body = m.group(2)
        name = re.search(r'name = "([^"]*)"', body)
        for a in addr_re.finditer(body):
            base, sign, off_s, bit, value = a.groups()
            if base not in LUA_LOCATION_BASES:
                continue
            g, delta = LUA_LOCATION_BASES[base]
            if g not in syms:
                continue
            rva = syms[g] + delta + (int(off_s, 16) if sign == "+" else -int(off_s, 16))
            off = rva - SAVE_BASE_RVA
            if not 0 <= off < 0x8000:
                continue   # flag lives outside the save block (e.g. soraStats, OCCupUnlock, reports)
            # locations.lua bit numbers are Lua byte_to_bits indexes (1 = LSB); 0 means "compare the byte"
            lua_bit = int(bit)
            by_off[off].append(dict(location=loc, name=name.group(1) if name else "",
                                    bit=(lua_bit - 1) if lua_bit > 0 else None, lua_bit=lua_bit,
                                    value=int(value, 0)))
    return by_off


# ---------------------------------------------------------------------------
# build + report
# ---------------------------------------------------------------------------

def build(args):
    game_data = Path(args.game_data)
    files = discover(game_data, args.lang, args.include_ard)
    pairs, failed = disassemble(files, CACHE_DIR, game_data)
    accesses = []
    for p, asm in pairs:
        accesses.extend(parse_asm(p.name, asm))

    labels = load_labels()
    syms, lua_by_off = load_lua_globals(Path(args.lua_globals) if args.lua_globals else None)
    loc_by_off = load_locations(Path(args.locations_lua) if args.locations_lua else None, syms)

    # Per-byte summary: accessors keyed by file -> {layer, reads, writes, bits, scripts}.
    # Every individual access stays in accesses.csv; --addr reads the detail from there.
    bytes_map = {}
    for a in accesses:
        if a["offset"] is None:
            continue
        for i in range(a["width"]):
            off = a["offset"] + i
            e = bytes_map.setdefault(off, {"reads": 0, "writes": 0, "accessors": {}})
            e["reads" if a["op"] == "read" else "writes"] += 1
            f = e["accessors"].setdefault(a["file"], {"layer": a["layer"], "reads": 0, "writes": 0, "bits": set(), "scripts": set()})
            f["reads" if a["op"] == "read" else "writes"] += 1
            if a["bit"] is not None:
                f["bits"].add(a["bit"])
            f["scripts"].add(f"KGR[{a['kgr']}]/S{a['script']}")
    for off in set(labels) | set(lua_by_off) | set(loc_by_off):
        bytes_map.setdefault(off, {"reads": 0, "writes": 0, "accessors": {}})
    for off, e in bytes_map.items():
        e["name"] = fmt_off(off)
        e["rva"] = rva_of(off)
        e["labels"] = labels.get(off, [])
        e["lua_symbols"] = lua_by_off.get(off, [])
        e["ap_locations"] = loc_by_off.get(off, [])
        for f in e["accessors"].values():
            f["bits"] = sorted(f["bits"]); f["scripts"] = sorted(f["scripts"])
        e["writer_files"] = sorted(n for n, f in e["accessors"].items() if f["writes"])
        e["reader_files"] = sorted(n for n, f in e["accessors"].items() if f["reads"])
        live = [n for n, f in e["accessors"].items() if f["layer"] != "ard"]
        e["live_access"] = bool(live)   # touched by a file the remastered English game actually loads

    other = defaultdict(lambda: {"reads": 0, "writes": 0, "files": set()})
    for a in accesses:
        if a["offset"] is None:
            k = f'{a["region"]}[0x{a["var"]:03X}]'
            other[k]["reads" if a["op"] == "read" else "writes"] += 1
            other[k]["files"].add(a["file"])

    result = {
        "meta": {"game_data": str(game_data), "lang": args.lang, "files": len(pairs),
                 "failed": failed, "accesses": len(accesses), "save_base_rva": hex(SAVE_BASE_RVA),
                 "save_data2_offset": hex(SAVE2_OFFSET)},
        "bytes": {f"0x{off:04X}": bytes_map[off] for off in sorted(bytes_map)},
        "non_save_vars": {k: {"reads": v["reads"], "writes": v["writes"], "files": sorted(v["files"])}
                          for k, v in sorted(other.items())},
    }
    return result, accesses


def engine_regions(lua_globals: Path):
    """Known engine structures inside the save block, from the Lua memory map.  Each symbol is
    assumed to extend to the next symbol (an approximation, but it tells you whose table a
    'free' byte sits in).  The world-flags and event-flags arrays are widened to the highest
    offsets the randomizer's location table reads from them."""
    syms, _ = load_lua_globals(lua_globals)
    pts = sorted((rva - SAVE_BASE_RVA, n) for n, rva in syms.items() if 0 <= rva - SAVE_BASE_RVA < 0x8000)
    regions = []
    for i, (off, name) in enumerate(pts):
        end = pts[i + 1][0] - 1 if i + 1 < len(pts) else off + 0x100
        regions.append({"start": off, "end": end, "name": name})
    if "waterwayCutsceneFlag" in syms:
        regions.append({"start": syms["waterwayCutsceneFlag"] - 5 - SAVE_BASE_RVA, "end": syms["waterwayCutsceneFlag"] - 5 - SAVE_BASE_RVA + 0x11A4, "name": "world flags array (locations.lua world_flags_address)"})
    if "evidence" in syms:
        regions.append({"start": syms["evidence"] - SAVE_BASE_RVA, "end": syms["evidence"] - SAVE_BASE_RVA + 0x108D, "name": "event / evidence flags (locations.lua event_flags)"})
    return regions


def write_html(result, path: Path, lua_globals: Path = None, dump: Path = None):
    """Standalone interactive viewer (memory_map_viewer.html template + embedded compact data)."""
    import datetime
    tpl = (HERE / "memory_map_viewer.html").read_text(encoding="utf-8")
    nonzero = {}
    if dump and dump.exists():
        raw = dump.read_bytes()
        nonzero = {i: b for i, b in enumerate(raw) if b}
    compact = {}
    for k, e in result["bytes"].items():
        compact[k] = {
            "a": [[f, v["layer"], v["reads"], v["writes"], v["bits"], v["scripts"]] for f, v in e["accessors"].items()],
            "t": {"l": e["labels"], "s": e["lua_symbols"],
                  "p": [{"id": l["location"], "name": l["name"], "bit": l["bit"], "value": l["value"]} for l in e["ap_locations"]]},
        }
    meta = {"files": result["meta"]["files"], "accesses": result["meta"]["accesses"], "lang": result["meta"]["lang"],
            "base_rva": SAVE_BASE_RVA, "generated": datetime.date.today().isoformat(),
            "dump": dump.name if dump and dump.exists() else None, "dump_size": len(nonzero) and (dump.stat().st_size)}
    payload = {"meta": meta, "bytes": compact,
               "regions": engine_regions(lua_globals) if lua_globals else [],
               "nz": {f"{k:X}": v for k, v in nonzero.items()}}
    data = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    path.write_text(tpl.replace("__DATA__", data), encoding="utf-8")
    print(f"wrote {path} ({path.stat().st_size // 1024} KB)")


def write_outputs(result, accesses, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    json.dump(result, open(out / "memory_map.json", "w", encoding="utf-8"), indent=1)
    with open(out / "accesses.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "layer", "kgr", "script", "pc", "line", "op", "width", "bit", "var", "region", "save_offset", "name"])
        for a in accesses:
            w.writerow([a["file"], a["layer"], a["kgr"], a["script"], a["pc"], a["line"], a["op"], a["width"],
                        "" if a["bit"] is None else a["bit"], f"0x{a['var']:X}", a["region"],
                        "" if a["offset"] is None else f"0x{a['offset']:04X}",
                        "" if a["offset"] is None else fmt_off(a["offset"])])
    with open(out / "memory_map.md", "w", encoding="utf-8") as f:
        m = result["meta"]
        f.write(f"# KH1 save-memory access map ({m['lang']}, {m['files']} scripts, {m['accesses']} accesses)\n\n")
        f.write("Files ending in .ard are the PS2-era embedded copies; for English they are shadowed wherever a "
                "remastered .evdl/.ev of the same set exists, so treat them as secondary evidence.\n\n")
        f.write("| offset | name | labels / Lua / AP | writes | reads | writers | readers |\n|---|---|---|---|---|---|---|\n")
        for k, e in result["bytes"].items():
            tags = e["labels"] + e["lua_symbols"] + [f"AP {l['location']}" for l in e["ap_locations"]]
            f.write(f"| {k} | {e['name']} | {', '.join(tags)} | {e['writes']} | {e['reads']} | "
                    f"{' '.join(e['writer_files'])} | {' '.join(e['reader_files'])} |\n")
    m = result["meta"]
    print(f"scanned {m['files']} scripts, {m['accesses']} accesses, {len(result['bytes'])} save bytes touched or tagged, "
          f"{len(m['failed'])} files skipped")
    print(f"wrote {out / 'memory_map.json'}, accesses.csv, memory_map.md")


# ---------------------------------------------------------------------------
# queries
# ---------------------------------------------------------------------------

def load_result(out: Path):
    p = out / "memory_map.json"
    if not p.exists():
        sys.exit(f"{p} not found; run a scan first")
    return json.load(open(p, encoding="utf-8"))


def parse_off(s: str) -> int:
    s = s.strip().lower()
    if s.startswith("save_data2[") or s.startswith("sd2["):
        return SAVE2_OFFSET + int(s.split("[")[1].rstrip("]"), 16)
    if s.startswith("save_data1[") or s.startswith("sd1["):
        return int(s.split("[")[1].rstrip("]"), 16)
    return int(s, 16)


def csv_rows(out: Path, offset: int = None, file: str = None):
    """Stream matching rows from accesses.csv (multi-byte accesses match every byte they span)."""
    with open(out / "accesses.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if file and r["file"] != file:
                continue
            if offset is not None:
                if not r["save_offset"]:
                    continue
                start = int(r["save_offset"], 16)
                if not start <= offset < start + int(r["width"]):
                    continue
            yield r


def q_addr(result, out: Path, off: int, live_only: bool):
    e = result["bytes"].get(f"0x{off:04X}")
    print(f"{fmt_off(off)}  {rva_of(off)}")
    if not e:
        print("  no script access, no label, no Lua symbol, no AP location"); return
    for k in ("labels", "lua_symbols"):
        if e[k]: print(f"  {k}: {', '.join(e[k])}")
    for l in e["ap_locations"]:
        cond = f"bit {l['bit']} set" if l["bit"] is not None else f"byte >= 0x{l['value']:X}"
        print(f"  AP location {l['location']} ({cond})  {l['name']}")
    rows = [r for r in csv_rows(out, offset=off) if not (live_only and r["layer"] == "ard")]
    for kind in ("write", "read"):
        recs = [r for r in rows if r["op"] == kind]
        print(f"  {kind}s: {len(recs)}")
        for r in recs:
            extra = f" bit {r['bit']}" if r["bit"] else ""
            if int(r["width"]) > 1:
                extra += f" ({int(r['width'])}-byte access at {r['save_offset']})"
            shadow = "  [embedded PS2 copy]" if r["layer"] == "ard" else ""
            print(f"    {r['file']:<24} KGR[{r['kgr']}] Script {r['script']} PC {r['pc']} (line {r['line']}){extra}{shadow}")


def q_free(result, lo: int, hi: int, live_only: bool):
    used = {int(k, 16) for k, e in result["bytes"].items()
            if (e["live_access"] if live_only else (e["reads"] or e["writes"]))}
    tagged = {int(k, 16) for k, e in result["bytes"].items() if e["labels"] or e["lua_symbols"] or e["ap_locations"]}
    start = None
    for off in range(lo, hi + 2):
        free = off <= hi and off not in used
        if free and start is None:
            start = off
        if not free and start is not None:
            end = off - 1
            note = " (has label/Lua/AP tag)" if any(x in tagged for x in range(start, end + 1)) else ""
            print(f"  {fmt_off(start)} - {fmt_off(end)}  ({end - start + 1} byte(s)){note}")
            start = None


def q_file(result, out: Path, name: str):
    rows = [r for r in csv_rows(out, file=name) if r["save_offset"]]
    if not rows:
        print(f"no save accesses recorded for {name}"); return
    for r in sorted(rows, key=lambda r: (int(r["save_offset"], 16), r["op"])):
        e = result["bytes"].get(f"0x{int(r['save_offset'], 16):04X}", {})
        tags = e.get("labels", []) + e.get("lua_symbols", []) + [f"AP {l['location']}" for l in e.get("ap_locations", [])]
        bit = f" bit {r['bit']}" if r["bit"] else ""
        print(f"  {r['op']:<5} {r['name']:<20}{bit:<8} KGR[{r['kgr']}] Script {r['script']} line {r['line']}  {', '.join(tags)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game-data", default=DEFAULT_GAME_DATA)
    ap.add_argument("--lang", default="UK")
    ap.add_argument("--include-ard", action="store_true", help="also scan the PS2-era *.ard files (their event data is normally shadowed by remastered .evdl/.ev)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--lua-globals", help="Lua memory map, e.g. KH1-LUA-LIBRARY/scripts/io_packages/SteamGlobal_1_0_0_2.lua")
    ap.add_argument("--locations-lua", help="randomizer mod/scripts/io_packages/locations.lua")
    ap.add_argument("--rescan", action="store_true", help="force a rescan even if memory_map.json exists")
    ap.add_argument("--addr", help="query one save offset (0x120, save_data1[0x120], save_data2[0x5DEE])")
    ap.add_argument("--free", help="list untouched runs in a range, e.g. 0x100-0x200")
    ap.add_argument("--file", help="list everything one script touches, e.g. UK_tw23d.ev")
    ap.add_argument("--live-only", action="store_true", help="queries ignore accesses from *.ard embedded copies")
    ap.add_argument("--html", nargs="?", const="", help="write the interactive viewer (default: <out>/memory_map.html)")
    ap.add_argument("--dump", help="raw dump of the save block starting at exe+2DE9F60 (e.g. from Cheat Engine); "
                                   "nonzero bytes are shown in the viewer as 'set in this save'")
    args = ap.parse_args()
    out = Path(args.out)

    query = args.addr or args.free or args.file or args.html is not None
    if args.rescan or not query or not (out / "memory_map.json").exists():
        result, accesses = build(args)
        write_outputs(result, accesses, out)
    else:
        result = load_result(out)

    if args.html is not None:
        write_html(result, Path(args.html) if args.html else out / "memory_map.html",
                   Path(args.lua_globals) if args.lua_globals else None,
                   Path(args.dump) if args.dump else None)

    if args.addr:
        q_addr(result, out, parse_off(args.addr), args.live_only)
    if args.free:
        lo, hi = args.free.split("-")
        q_free(result, parse_off(lo), parse_off(hi), args.live_only)
    if args.file:
        q_file(result, out, args.file)


if __name__ == "__main__":
    main()
