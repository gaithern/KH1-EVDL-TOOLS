#!/usr/bin/env python3
"""Extract per-enemy motion/action IDs referenced by .bd behavior scripts, and resolve
each one to the local .mset animation index it actually plays (0-51, the same
numbering as ModelViewerWX's anim0000-anim0051 - see kh1_motion_dict.py for how that
resolution works, entirely offline/statically from the enemy's own .mset file).

Every attack/action in a KH1 enemy behavior script goes through one of THREE native
verbs (all confirmed in Ghidra - see kh1_bd_verbs.json for the full derivation of each):
  - NATIVE_t0_0xd / SetMotion    - overwrites the current action (FUN_14029F980)
  - NATIVE_t0_0xe / QueueMotion  - appends a follow-up action to play next (FUN_14029FA30)
  - NATIVE_t0_0xc / BlendMotion  - smooth crossfade into a motion, skips if already
    playing it (FUN_1402B9F50 -> FUN_14029F7C0) - easy to miss if only grepping for
    SetMotion/QueueMotion (a real mistake made once already, corrected same session -
    see project_ai_motion_id_resolution.md - a label that LOOKED like "no attack, just
    reposition/face-target" turned out to trigger a real attack motion via this verb).
All three funnel into the SAME motion-queue system (behind GetActionState()) and the
SAME resolver (FUN_1402A01E0, see kh1_motion_dict.py). SetMotion/QueueMotion's 2nd
argument packs a small motion ID in the low 16 bits with engine flags in the upper
bits; BlendMotion's 2nd argument is the motion ID directly, unpacked, with its 3rd
argument as a blend/crossfade duration in frames instead of engine flags. A
SetMotion+QueueMotion pair at the same script label is a two-step sequence ("play X
now, then transition to Y") - the same motion_id commonly reappears as any of these
three verbs' argument across different labels/enemies without that being inconsistent.

There is no motion *name* recoverable anywhere in the shipped game data - .mset and
_dic.mset are dense binary keyframe/bone blobs with no embedded strings (confirmed
by an exhaustive printable-ASCII scan). This recovers the numeric IDs, where each one
is used, AND (new) the resolved local animation index via kh1_motion_dict.py, using
the SAME-basename .mset file next to the input .mdls (kh1_motion_dict.py documents how
the resolver works).

Usage:
  python kh1_motion_ids.py <file.mdls> [<file2.mdls> ...] [--json out.json]
"""
import sys, re, json, os, struct
import kh1_bd_disasm as bd
from kh1_motion_dict import read_motion_dict

# Matches the "play motion" native call in kh1_bd_disasm.py --fold output. Historically
# this was always the raw unnamed "NATIVE_t0_0xd(...)"/"NATIVE_t0_0xe(...)" form - naming
# these two verbs "SetMotion"/"QueueMotion" in kh1_bd_verbs.json (see
# project_ai_motion_id_resolution.md) makes --fold print the readable name instead, so
# both forms need matching here or this regex silently finds nothing (a real regression
# hit once already - don't remove either alternative without re-testing extract()).
NATIVE_RE = re.compile(r"(NATIVE_t0_0x0?[cCdDeE]|SetMotion|QueueMotion|BlendMotion)\(([^)]*)\)")
LABEL_RE = re.compile(r"^(@L[0-9A-Fa-f]{4}):$")


def _slot_letter(verb_text):
    if verb_text.startswith("NATIVE_t0_0x"):
        return verb_text[-1].lower()
    return {"SetMotion": "d", "QueueMotion": "e", "BlendMotion": "c"}[verb_text]


def _base(name):
    return name.rsplit(".", 1)[0]


def _is_suffixed(name):
    # "ex_3000.bd" -> ["ex","3000"] (un-suffixed stat/drop block)
    # "ex_3000_04.bd" -> ["ex","3000","04"] (a real per-behavior block)
    return _base(name).count("_") >= 2


def _enemy_id(name):
    return "_".join(_base(name).split("_")[:2])


def _sibling_motion_dict(mdls_path):
    """The enemy's own .mset lives next to its .mdls with the same basename (e.g.
    xa_ex_2020.mdls / xa_ex_2020.mset) - confirmed for Shadow, the only enemy this
    resolver has been live-verified against so far (see
    project_ai_motion_id_resolution.md). Returns {} (not an error) if the sibling
    .mset is missing or doesn't carry a valid dictionary, so callers degrade
    gracefully to just the raw motion_id when resolution isn't possible."""
    mset_path = os.path.splitext(mdls_path)[0] + ".mset"
    try:
        return read_motion_dict(mset_path)
    except (FileNotFoundError, struct.error):
        return {}


def extract(mdls_path):
    data = open(mdls_path, "rb").read()
    motion_dict = _sibling_motion_dict(mdls_path)
    blocks = bd.find_blocks(data)
    # Un-suffixed "stat data + code" blocks (e.g. ex_3000.bd) are only trustworthy
    # as the *sole* block in a simple-enemy layout (Shadow's ex_2020.bd, manually
    # verified this session). In a boss's multi-block layout the real AI lives in
    # the suffixed blocks (ex_3000_04.bd etc.) - the un-suffixed stat block's tail
    # is mostly non-code drop/item data that code_start()/extend_end() can
    # misdecode as plausible-looking-but-fake instructions with no sibling block
    # nearby to bound the walk. Flag those findings as low-confidence rather than
    # silently mixing them in with real script results.
    has_suffixed = any(_is_suffixed(name) for _, name, _ in blocks)
    findings = []
    for block_off, name, size in blocks:
        text = bd.fold(data, block_off, name, size)
        confidence = "high" if (_is_suffixed(name) or not has_suffixed) else "low"
        cur_label = None
        for line in text.split("\n"):
            stripped = line.strip()
            m = LABEL_RE.match(stripped)
            if m:
                cur_label = m.group(1)
                continue
            for verb_text, args in NATIVE_RE.findall(line):
                slot = _slot_letter(verb_text)
                arg_list = [a.strip() for a in args.split(",")]
                if len(arg_list) < 2:
                    continue
                try:
                    raw = int(arg_list[1])
                except ValueError:
                    continue  # non-literal (computed at runtime) - can't decode statically
                motion_id = raw & 0xFFFF
                findings.append({
                    "enemy": _enemy_id(name),
                    "file": mdls_path,
                    "block": name,
                    "label": cur_label,
                    "slot": f"0x0{slot.lower()}",
                    "motion_id": motion_id,
                    "anim_index": motion_dict.get(motion_id),
                    "flags": raw >> 16,
                    "raw": raw,
                    "confidence": confidence,
                })
    return findings


def main():
    args = sys.argv[1:]
    out_json = None
    if "--json" in args:
        i = args.index("--json")
        out_json = args[i + 1]
        args = args[:i] + args[i + 2:]
    if not args:
        print(__doc__)
        return
    all_findings = []
    for path in args:
        try:
            all_findings.extend(extract(path))
        except Exception as e:
            print(f"skipping {path}: {e}", file=sys.stderr)
    if out_json:
        with open(out_json, "w") as f:
            json.dump(all_findings, f, indent=1)
        print(f"wrote {len(all_findings)} findings to {out_json}")
    else:
        print(f"{'enemy':<14} {'block':<18} {'label':<8} {'slot':<6} {'id':>5} {'anim':<8} {'flags':>8}  {'conf':<5} raw")
        for r in all_findings:
            anim = f"anim{r['anim_index']:04d}" if r['anim_index'] is not None else "-"
            print(f"{r['enemy']:<14} {r['block']:<18} {r['label'] or '-':<8} {r['slot']:<6} "
                  f"{r['motion_id']:>5} {anim:<8} {r['flags']:>#8x}  {r['confidence']:<5} {r['raw']}")


if __name__ == "__main__":
    main()
