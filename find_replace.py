#!/usr/bin/env python3
"""
find_replace.py - Find and replace text across files with multiline and wildcard support.

Run with no arguments to open the GUI.
Run with arguments for CLI mode (see below).

WILDCARD MODE (default):
    *   matches any text (including newlines, so it spans lines)
    ?   matches any single character (except newline)
    All other characters are matched literally.

REGEX MODE (--regex):
    Full Python regex syntax. re.DOTALL is on by default so . matches newlines.
    TIP: When your pattern contains explicit newlines between lines, turn DOTALL
    OFF (--no-dotall) so .* stays within a single line.

EXAMPLES:
    python find_replace.py --dry-run "Gift Table Idx *\n" "" "asm/**/*.evdl.asm"
    python find_replace.py "Gift Table Idx 57" "Gift Table Idx 42" "asm/**/*.evdl.asm"
    python find_replace.py --regex --no-dotall "push.*\nsyscall.*" "REPLACED" "asm/**/*.evdl.asm"
    python find_replace.py -i -b "syscall" "SYSCALL" "asm/**/*.asm"
"""

import argparse
import glob
import json
import os
import re
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

PRESETS_FILE = Path(__file__).parent / "find_replace_presets.json"

# Special tokens usable in patterns and replacements
_LABEL_TOKEN   = '{label}'    # in Find:   matches @LABEL_NAME (+ optional ; → PC NNN)
_LABEL_RE      = r'@\w+(?:[ \t]*;[^\n]*)?'
_COMMENT_TOKEN = '{comment}'  # in Replace: expands to matched block with ; prepended to every line


# ═══════════════════════════════════════════════════════════════ core logic ══

def wildcard_to_regex(pattern: str, dot_all: bool) -> str:
    """Convert a wildcard pattern to regex, honouring {label} and * / ? tokens."""
    segments = pattern.split(_LABEL_TOKEN)
    parts = []
    for i, seg in enumerate(segments):
        for c in seg:
            if c == '*':
                parts.append('.*?' if dot_all else '[^\n]*?')
            elif c == '?':
                parts.append('[^\n]')
            else:
                parts.append(re.escape(c))
        if i < len(segments) - 1:
            parts.append(_LABEL_RE)
    return ''.join(parts)


def apply_label_token(pattern: str) -> str:
    """Substitute {label} in a raw regex pattern string (regex mode)."""
    return pattern.replace(_LABEL_TOKEN, _LABEL_RE)


def auto_wildlabels(pattern: str) -> str:
    """Replace every @LABEL_NAME (+ optional trailing ; comment) with {label}."""
    return re.sub(r'@\w+(?:[ \t]*;[^\n]*)?', _LABEL_TOKEN, pattern)


def prepare_replacement(template: str):
    """Return a replacement string or callable for re.sub.

    If *template* contains {comment}, returns a callable that prefixes every
    line of the matched text with ';' and splices it into the template.
    Otherwise returns the template string unchanged (for normal re.sub use).
    """
    if _COMMENT_TOKEN not in template:
        return template

    def _fn(m: re.Match) -> str:
        commented = '\n'.join(
            (';' + line) if line else ';'
            for line in m.group().split('\n')
        )
        return template.replace(_COMMENT_TOKEN, commented)

    return _fn


def stamp_change_note(content: str, note_text: str) -> tuple[str, bool]:
    """Insert or replace the What's changed block in the KGR[0] opening.

    Anchors on the ruler immediately after the '; Stream @' line, then
    replaces everything up to the ruler that opens '; Script 0'.
    Returns (new_content, changed).
    """
    m = re.search(r'; Stream @[^\n]+\n; ─+\n', content)
    if not m:
        return content, False
    gap_start = m.end()
    m2 = re.search(r'; ─+\n; Script ', content[gap_start:])
    if not m2:
        return content, False
    gap_end = gap_start + m2.start()

    lines = ["; What's changed:"]
    for line in note_text.splitlines():
        lines.append(('; ' + line) if line else ';')
    note_block = '\n'.join(lines)
    new_content = content[:gap_start] + '\n' + note_block + '\n\n' + content[gap_end:]
    return new_content, True


_SCRIPT_HDR_RE = re.compile(r'^; Script\s+(\d+)\s+\|.*\|\s*KGR\s+(\d+)')
_CINSTR_RE     = re.compile(r'^; +[0-9A-Fa-f?]{8}[ \t]|^;@\w')
_STDCMT_RE     = re.compile(
    r"^; [─]|^; KGR\b|^; Stream\b|^; Script\b|^; What's changed"
    r"|^; -[ \t]|^;   -|^; Message:|^;[ ]{5}|^; ---"
    r"|^; ;|^;;|^; @\w"   # double-commented lines + commented-out labels
)


def detect_script_changes(content: str) -> list[tuple[int, int, list[str]]]:
    """Scan an evdl.asm for commented-out instruction blocks and preceding user
    description comments.  Returns [(kgr, script, [desc, ...]), ...] sorted by
    (kgr, script), one entry per script that has detectable changes."""
    lines = content.splitlines()

    # Map each line to (kgr, script) — None until the first Script header
    line_ctx: list[tuple[int, int] | None] = [None] * len(lines)
    current = (0, 0)
    in_header = True
    for i, line in enumerate(lines):
        m = _SCRIPT_HDR_RE.match(line)
        if m:
            current = (int(m.group(2)), int(m.group(1)))
            in_header = False
        if not in_header:
            line_ctx[i] = current

    def _is_user_desc(line: str) -> bool:
        return (line.startswith('; ')
                and not _CINSTR_RE.match(line)
                and not _STDCMT_RE.match(line)
                and bool(line[2:].strip()))

    script_descs:   dict[tuple, list[str]] = {}
    script_touched: set[tuple] = set()

    for i, line in enumerate(lines):
        ctx = line_ctx[i]
        if ctx is None:
            continue
        if _CINSTR_RE.match(line):
            script_touched.add(ctx)
        elif _is_user_desc(line):
            script_descs.setdefault(ctx, [])
            desc = line[2:]
            if desc not in script_descs[ctx]:
                script_descs[ctx].append(desc)

    all_changed = script_touched | set(script_descs.keys())
    return [
        (kgr, script, script_descs.get((kgr, script), []))
        for kgr, script in sorted(all_changed)
    ]


def generate_change_note(changes: list[tuple[int, int, list[str]]]) -> str | None:
    """Format detected changes as the plain-text body of a What's changed block.
    Returns None if *changes* is empty."""
    if not changes:
        return None
    lines = []
    for kgr, script, descs in changes:
        lines.append(f"- KGR[{kgr}] Script {script}:")
        for desc in descs:
            lines.append(f"  - {desc}")
    return '\n'.join(lines)


def resolve_files(patterns: list[str], root: Path) -> list[Path]:
    seen: set[str] = set()
    files: list[Path] = []
    for pattern in patterns:
        base = pattern if os.path.isabs(pattern) else str(root / pattern)
        for match in sorted(glob.glob(base, recursive=True)):
            p = Path(match)
            key = str(p.resolve())
            if p.is_file() and key not in seen:
                seen.add(key)
                files.append(p)
    return files


def _expand(m: re.Match, replacement) -> str:
    """Apply replacement (string or callable) to a single match."""
    return replacement(m) if callable(replacement) else m.expand(replacement)


def show_match_context(content: str, match: re.Match, replacement, max_lines: int = 10) -> None:
    start_line = content[:match.start()].count('\n') + 1
    matched_lines = match.group().splitlines()
    replaced_lines = _expand(match, replacement).splitlines()
    print(f"    --- line {start_line} ---")
    for line in matched_lines[:max_lines]:
        print(f"    - {line}")
    if len(matched_lines) > max_lines:
        print(f"    - ... ({len(matched_lines) - max_lines} more lines)")
    for line in replaced_lines[:max_lines]:
        print(f"    + {line}")
    if len(replaced_lines) > max_lines:
        print(f"    + ... ({len(replaced_lines) - max_lines} more lines)")


def process_file(filepath, regex, replacement, *, dry_run, backup, verbose):
    try:
        content = filepath.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        print(f"  ERROR reading {filepath}: {e}", file=sys.stderr)
        return 0, False
    matches = list(regex.finditer(content))
    if not matches:
        return 0, False
    print(f"  {filepath}  ({len(matches)} match(es))")
    if verbose or dry_run:
        for m in matches:
            show_match_context(content, m, replacement)
    if dry_run:
        return len(matches), False
    if backup:
        filepath.with_suffix(filepath.suffix + '.bak').write_text(content, encoding='utf-8')
    new_content, _ = regex.subn(replacement, content)
    filepath.write_text(new_content, encoding='utf-8')
    return len(matches), True


# ═══════════════════════════════════════════════════════════════════════ GUI ══

class FindReplaceGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("KH1 Find & Replace")
        self.root.minsize(760, 600)
        self.root.geometry("980x780")
        self.repo_root = Path(__file__).parent
        self._undo_snapshot: dict[Path, str] = {}
        self._tabs: list[dict] = []   # parallel to notebook tabs
        self._build_ui()
        self._load_presets()
        if not self._tabs:
            self._add_tab("New preset")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────────────────────────────────────── UI build ──

    def _build_ui(self) -> None:
        pad = dict(padx=8, pady=3)

        # ── notebook (tabs) ──────────────────────────────────────────────
        nb_frame = ttk.Frame(self.root)
        nb_frame.pack(fill=tk.X, padx=8, pady=(8, 0))

        self.notebook = ttk.Notebook(nb_frame)
        self.notebook.pack(fill=tk.X, expand=True, side=tk.LEFT)
        self.notebook.bind("<Double-Button-1>", self._on_tab_double_click)
        self.notebook.bind("<Button-3>",        self._on_tab_right_click)

        ttk.Button(nb_frame, text="+", width=3, command=lambda: self._add_tab()).pack(
            side=tk.LEFT, padx=(4, 0), pady=2)

        # ── shared: files + root ─────────────────────────────────────────
        shared = ttk.Frame(self.root, padding=(8, 4, 8, 0))
        shared.pack(fill=tk.X)
        shared.columnconfigure(1, weight=1)

        ttk.Label(shared, text="Files:").grid(row=0, column=0, sticky=tk.E, **pad)
        self.glob_var = tk.StringVar(value="asm/**/*.evdl.asm")
        ttk.Entry(shared, textvariable=self.glob_var, font=("Consolas", 10)).grid(
            row=0, column=1, sticky=tk.EW, **pad)
        ttk.Label(
            shared,
            text="Separate multiple globs with  ;  (e.g.  asm/**/*.evdl.asm; mod/scripts/*.lua)",
            foreground="gray",
        ).grid(row=1, column=1, sticky=tk.W, padx=8)

        ttk.Label(shared, text="Root:").grid(row=2, column=0, sticky=tk.E, **pad)
        self.root_var = tk.StringVar(value=str(self.repo_root))
        ttk.Entry(shared, textvariable=self.root_var, font=("Consolas", 10)).grid(
            row=2, column=1, sticky=tk.EW, **pad)
        ttk.Button(shared, text="Browse…", command=self._browse_root).grid(
            row=2, column=2, sticky=tk.W, **pad)

        # ── button bar ───────────────────────────────────────────────────
        bar = ttk.Frame(self.root, padding=(8, 6))
        bar.pack(fill=tk.X)

        self.btn_find    = ttk.Button(bar, text="Find All",     width=12, command=self._on_find)
        self.btn_replace = ttk.Button(bar, text="Replace All",  width=12, command=self._on_replace)
        self.btn_undo    = ttk.Button(bar, text="Undo Replace", width=14, command=self._on_undo,
                                      state=tk.DISABLED)
        btn_save  = ttk.Button(bar, text="Save Presets",  command=self._save_presets)
        btn_clear = ttk.Button(bar, text="Clear Output",  command=self._clear_output)
        btn_stamp = ttk.Button(bar, text="Stamp Note…",   command=self._on_stamp_note)

        self.btn_find.pack(side=tk.LEFT, padx=4)
        self.btn_replace.pack(side=tk.LEFT, padx=4)
        self.btn_undo.pack(side=tk.LEFT, padx=4)
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        btn_save.pack(side=tk.LEFT, padx=4)
        btn_clear.pack(side=tk.LEFT, padx=4)
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        btn_stamp.pack(side=tk.LEFT, padx=4)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(bar, textvariable=self.status_var, foreground="gray").pack(side=tk.RIGHT, padx=8)

        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        self.progress.pack(fill=tk.X, padx=8, pady=(0, 2))

        # ── output area ──────────────────────────────────────────────────
        out = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        out.pack(fill=tk.BOTH, expand=True)

        self.output = scrolledtext.ScrolledText(
            out, font=("Consolas", 9), wrap=tk.NONE, state=tk.DISABLED,
            background="#1e1e1e", foreground="#d4d4d4", insertbackground="#d4d4d4",
        )
        self.output.pack(fill=tk.BOTH, expand=True)
        ox_sb = ttk.Scrollbar(out, orient=tk.HORIZONTAL, command=self.output.xview)
        self.output.configure(xscrollcommand=ox_sb.set)
        ox_sb.pack(fill=tk.X)

        self.output.tag_configure("header",  foreground="#569cd6")
        self.output.tag_configure("file",    foreground="#4ec9b0", font=("Consolas", 9, "bold"))
        self.output.tag_configure("removed", foreground="#f44747")
        self.output.tag_configure("added",   foreground="#b5cea8")
        self.output.tag_configure("info",    foreground="#9cdcfe")
        self.output.tag_configure("success", foreground="#6a9955", font=("Consolas", 9, "bold"))
        self.output.tag_configure("warning", foreground="#dcdcaa")
        self.output.tag_configure("error",   foreground="#f44747", font=("Consolas", 9, "bold"))
        self.output.tag_configure("lineno",  foreground="#858585")

    # ───────────────────────────────────────────────────── tab management ──

    def _make_tab_frame(self, parent: ttk.Frame) -> dict:
        """Build Find/Replace widgets inside a tab frame. Returns the widget dict."""
        pad = dict(padx=8, pady=3)
        parent.columnconfigure(1, weight=1)

        var_regex      = tk.BooleanVar()
        var_ignorecase = tk.BooleanVar()
        var_dotall     = tk.BooleanVar(value=True)
        var_wildlabels = tk.BooleanVar()
        var_backup     = tk.BooleanVar()

        ttk.Label(parent, text="Find:").grid(row=0, column=0, sticky=tk.NE, **pad)
        find_box = tk.Text(parent, height=8, font=("Consolas", 10), wrap=tk.NONE, undo=True)
        find_box.grid(row=0, column=1, sticky=tk.EW, **pad)
        fx_sb = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=find_box.xview)
        find_box.configure(xscrollcommand=fx_sb.set)
        fx_sb.grid(row=1, column=1, sticky=tk.EW, padx=8)

        ttk.Label(parent, text="Replace:").grid(row=2, column=0, sticky=tk.NE, **pad)
        replace_box = tk.Text(parent, height=8, font=("Consolas", 10), wrap=tk.NONE, undo=True)
        replace_box.grid(row=2, column=1, sticky=tk.EW, **pad)
        rx_sb = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=replace_box.xview)
        replace_box.configure(xscrollcommand=rx_sb.set)
        rx_sb.grid(row=3, column=1, sticky=tk.EW, padx=8)

        opts = ttk.LabelFrame(parent, text="Options", padding=6)
        opts.grid(row=0, column=2, rowspan=4, sticky=tk.NS, padx=8, pady=3)
        ttk.Checkbutton(opts, text="Regex mode",      variable=var_regex).pack(anchor=tk.W)
        ttk.Checkbutton(opts, text="Ignore case",     variable=var_ignorecase).pack(anchor=tk.W)
        ttk.Checkbutton(opts, text="* spans lines",   variable=var_dotall).pack(anchor=tk.W)
        ttk.Checkbutton(opts, text="Labels as wilds", variable=var_wildlabels).pack(anchor=tk.W)
        ttk.Separator(opts, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=4)
        ttk.Checkbutton(opts, text="Backup (.bak)",   variable=var_backup).pack(anchor=tk.W)

        return dict(
            frame=parent,
            find_box=find_box,
            replace_box=replace_box,
            var_regex=var_regex,
            var_ignorecase=var_ignorecase,
            var_dotall=var_dotall,
            var_wildlabels=var_wildlabels,
            var_backup=var_backup,
        )

    def _add_tab(self, name: str = "New preset", data: dict | None = None) -> dict:
        """Add a new notebook tab. Populate from data dict if given."""
        frame = ttk.Frame(self.notebook, padding=(4, 4, 4, 4))
        tab = self._make_tab_frame(frame)
        if data:
            tab['find_box'].insert("1.0", data.get('find', ''))
            tab['replace_box'].insert("1.0", data.get('replace', ''))
            tab['var_regex'].set(data.get('regex', False))
            tab['var_ignorecase'].set(data.get('ignorecase', False))
            tab['var_dotall'].set(data.get('dotall', True))
            tab['var_wildlabels'].set(data.get('wildlabels', False))
            tab['var_backup'].set(data.get('backup', False))
        self.notebook.add(frame, text=name)
        self._tabs.append(tab)
        self.notebook.select(len(self._tabs) - 1)
        return tab

    def _close_tab(self, idx: int) -> None:
        if len(self._tabs) <= 1:
            messagebox.showinfo("Can't close", "At least one tab must remain.")
            return
        self.notebook.forget(idx)
        self._tabs.pop(idx)

    def _rename_tab(self, idx: int) -> None:
        current = self.notebook.tab(idx, "text")
        name = simpledialog.askstring("Rename tab", "Tab name:", initialvalue=current, parent=self.root)
        if name:
            self.notebook.tab(idx, text=name)

    def _current_tab(self) -> dict:
        idx = self.notebook.index(self.notebook.select())
        return self._tabs[idx]

    def _on_tab_double_click(self, event: tk.Event) -> None:
        try:
            idx = self.notebook.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return
        self._rename_tab(idx)

    def _on_tab_right_click(self, event: tk.Event) -> None:
        try:
            idx = self.notebook.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Rename",      command=lambda: self._rename_tab(idx))
        menu.add_command(label="Duplicate",   command=lambda: self._duplicate_tab(idx))
        menu.add_separator()
        menu.add_command(label="Close tab",   command=lambda: self._close_tab(idx))
        menu.tk_popup(event.x_root, event.y_root)

    def _duplicate_tab(self, idx: int) -> None:
        src = self._tabs[idx]
        name = self.notebook.tab(idx, "text") + " (copy)"
        data = self._tab_to_dict(idx)
        self._add_tab(name, data)

    # ──────────────────────────────────────────────────────── persistence ──

    def _tab_to_dict(self, idx: int) -> dict:
        tab = self._tabs[idx]
        def _text(box):
            raw = box.get("1.0", tk.END)
            return raw[:-1] if raw.endswith("\n") else raw

        return dict(
            name=self.notebook.tab(idx, "text"),
            find=_text(tab['find_box']),
            replace=_text(tab['replace_box']),
            regex=tab['var_regex'].get(),
            ignorecase=tab['var_ignorecase'].get(),
            dotall=tab['var_dotall'].get(),
            wildlabels=tab['var_wildlabels'].get(),
            backup=tab['var_backup'].get(),
        )

    def _save_presets(self) -> None:
        data = {
            "tabs": [self._tab_to_dict(i) for i in range(len(self._tabs))],
            "globs": self.glob_var.get(),
            "root": self.root_var.get(),
            "active_tab": self.notebook.index(self.notebook.select()),
        }
        try:
            PRESETS_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')
            self.status_var.set(f"Presets saved to {PRESETS_FILE.name}")
        except OSError as e:
            messagebox.showerror("Save error", str(e))

    def _load_presets(self) -> None:
        if not PRESETS_FILE.exists():
            return
        try:
            data = json.loads(PRESETS_FILE.read_text(encoding='utf-8'))
        except Exception:
            return
        for tab_data in data.get("tabs", []):
            self._add_tab(tab_data.get("name", "Preset"), tab_data)
        if "globs" in data:
            self.glob_var.set(data["globs"])
        if "root" in data:
            self.root_var.set(data["root"])
        active = data.get("active_tab", 0)
        if self._tabs and active < len(self._tabs):
            self.notebook.select(active)

    def _on_close(self) -> None:
        self._save_presets()
        self.root.destroy()

    # ────────────────────────────────────────────────────────── helpers ──

    def _browse_root(self) -> None:
        d = filedialog.askdirectory(initialdir=self.root_var.get(), title="Select root directory")
        if d:
            self.root_var.set(d)

    def _get_pattern(self) -> str:
        raw = self._current_tab()['find_box'].get("1.0", tk.END)
        return raw[:-1] if raw.endswith("\n") else raw

    def _get_replacement(self) -> str:
        raw = self._current_tab()['replace_box'].get("1.0", tk.END)
        return raw[:-1] if raw.endswith("\n") else raw

    def _get_globs(self) -> list[str]:
        return [g.strip() for g in self.glob_var.get().split(";") if g.strip()]

    def _log(self, text: str, tag: str = "") -> None:
        def _do() -> None:
            self.output.configure(state=tk.NORMAL)
            self.output.insert(tk.END, text, tag)
            self.output.see(tk.END)
            self.output.configure(state=tk.DISABLED)
        self.root.after(0, _do)

    def _clear_output(self) -> None:
        self.output.configure(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        self.output.configure(state=tk.DISABLED)
        self.status_var.set("Ready")

    def _set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.btn_find.configure(state=state)
        self.btn_replace.configure(state=state)
        self.btn_undo.configure(state=tk.DISABLED if busy or not self._undo_snapshot else tk.NORMAL)
        if busy:
            self.progress.start(10)
        else:
            self.progress.stop()

    def _compile_regex(self) -> re.Pattern | None:
        pattern = self._get_pattern()
        if not pattern:
            messagebox.showwarning("No pattern", "Enter a search pattern first.")
            return None
        tab = self._current_tab()
        dot_all    = tab['var_dotall'].get()
        use_regex  = tab['var_regex'].get()
        wildlabels = tab['var_wildlabels'].get()
        if wildlabels:
            pattern = auto_wildlabels(pattern)
        if use_regex:
            regex_str = apply_label_token(pattern)
        else:
            regex_str = wildcard_to_regex(pattern, dot_all)
        flags = re.DOTALL if dot_all else 0
        if tab['var_ignorecase'].get():
            flags |= re.IGNORECASE
        try:
            return re.compile(regex_str, flags)
        except re.error as e:
            messagebox.showerror("Invalid pattern", f"Regex error: {e}\n\nCompiled pattern:\n{regex_str!r}")
            return None

    # ─────────────────────────────────────────────────── button actions ──

    def _on_stamp_note(self) -> None:
        """Auto-detect changes in matched files and stamp What's changed notes."""
        globs     = self._get_globs()
        root_path = Path(self.root_var.get())

        def _worker() -> None:
            self.root.after(0, lambda: self._set_busy(True))
            try:
                try:
                    files = resolve_files(globs, root_path)
                except Exception as e:
                    self._log(f"  ERROR resolving files: {e}\n", "error")
                    return
                if not files:
                    self._log(f"  No files matched: {globs}\n", "warning")
                    return

                HR = "─" * 70
                self._log(f"\n{HR}\n  STAMP NOTE  (auto-detect)\n{HR}\n", "header")
                self._log(f"  Root:  {root_path}\n", "info")
                self._log(f"  Globs: {globs}\n\n", "info")

                snapshot:    dict[Path, str] = {}
                stamped = no_changes = no_header = 0

                for filepath in files:
                    try:
                        content = filepath.read_text(encoding="utf-8", errors="replace")
                    except OSError as e:
                        self._log(f"  ERROR reading {filepath}: {e}\n", "error")
                        continue

                    changes   = detect_script_changes(content)
                    note_text = generate_change_note(changes)

                    if note_text is None:
                        no_changes += 1
                        continue

                    new_content, ok = stamp_change_note(content, note_text)
                    if not ok:
                        no_header += 1
                        continue

                    try:
                        rel = filepath.relative_to(root_path)
                    except ValueError:
                        rel = filepath

                    self._log(f"  {rel}\n", "file")
                    for kgr, script, descs in changes:
                        self._log(f"    KGR[{kgr}] Script {script}:\n", "lineno")
                        for desc in descs:
                            self._log(f"      - {desc}\n", "added")

                    snapshot[filepath] = content
                    try:
                        filepath.write_text(new_content, encoding="utf-8")
                        stamped += 1
                    except OSError as e:
                        self._log(f"  ERROR writing {filepath}: {e}\n", "error")

                self._log(f"\n{HR}\n", "header")
                parts = [f"Stamped {stamped} file(s)."]
                if no_changes:
                    parts.append(f"{no_changes} skipped (no detectable changes).")
                if no_header:
                    parts.append(f"{no_header} skipped (no KGR[0] header).")
                summary = "  " + "  ".join(parts)
                self._log(f"{summary}\n{HR}\n", "success")

                def _finish() -> None:
                    self._undo_snapshot.update(snapshot)
                    self.status_var.set(summary.strip())
                    if snapshot:
                        self.btn_undo.configure(state=tk.NORMAL)
                self.root.after(0, _finish)
            finally:
                self.root.after(0, lambda: self._set_busy(False))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_find(self) -> None:
        regex = self._compile_regex()
        if regex is None:
            return
        replacement = prepare_replacement(self._get_replacement())
        args = (regex, replacement, self._get_globs(), Path(self.root_var.get()), True)
        threading.Thread(target=self._run, args=args, daemon=True).start()

    def _on_replace(self) -> None:
        regex = self._compile_regex()
        if regex is None:
            return
        root_path = Path(self.root_var.get())
        backup = self._current_tab()['var_backup'].get()
        if not messagebox.askyesno(
            "Confirm Replace All",
            f"Replace all matches in:\n{root_path}\n\n"
            + ("A .bak backup will be made first.\n\n" if backup else
               "WARNING: No backup enabled — changes cannot be undone.\n\n")
            + "Proceed?",
        ):
            return
        replacement = prepare_replacement(self._get_replacement())
        args = (regex, replacement, self._get_globs(), root_path, False)
        threading.Thread(target=self._run, args=args, daemon=True).start()

    def _on_undo(self) -> None:
        if not self._undo_snapshot:
            return
        n = len(self._undo_snapshot)
        if not messagebox.askyesno(
            "Undo Replace",
            f"Restore {n} file(s) to their state before the last Replace All?\n\nThis cannot be undone.",
        ):
            return
        errors = []
        for filepath, original in self._undo_snapshot.items():
            try:
                filepath.write_text(original, encoding="utf-8")
            except OSError as e:
                errors.append(f"{filepath}: {e}")
        self._undo_snapshot.clear()
        self.btn_undo.configure(state=tk.DISABLED)
        HR = "─" * 70
        self._log(f"\n{HR}\n", "header")
        if errors:
            self._log(f"  Undo completed with {len(errors)} error(s):\n", "warning")
            for err in errors:
                self._log(f"    {err}\n", "error")
        else:
            self._log(f"  Undo complete — {n} file(s) restored.\n", "success")
        self._log(f"{HR}\n", "header")
        self.status_var.set(f"Undo complete — {n} file(s) restored.")

    # ──────────────────────────────────────────────── search/replace worker ──

    def _run(self, regex, replacement, globs, root, dry_run) -> None:
        self.root.after(0, lambda: self._set_busy(True))
        try:
            self._do_run(regex, replacement, globs, root, dry_run)
        finally:
            self.root.after(0, lambda: self._set_busy(False))

    def _do_run(self, regex, replacement, globs, root, dry_run) -> None:
        HR = "─" * 70
        mode = "FIND (no changes)" if dry_run else "REPLACE"
        self._log(f"\n{HR}\n", "header")
        self._log(f"  {mode}\n", "header")
        self._log(f"{HR}\n", "header")
        self._log(f"  Root:       {root}\n", "info")
        self._log(f"  Pattern:    {regex.pattern!r}\n", "info")
        self._log(f"  Flags:      {'DOTALL ' if re.DOTALL & regex.flags else ''}"
                  f"{'IGNORECASE' if re.IGNORECASE & regex.flags else ''}\n", "info")
        self._log(f"  Replace:    {replacement!r}\n", "info")
        self._log(f"  Globs:      {globs}\n\n", "info")

        try:
            files = resolve_files(globs, root)
        except Exception as e:
            self._log(f"ERROR resolving files: {e}\n", "error")
            self.root.after(0, lambda: self.status_var.set("Error resolving files"))
            return

        if not files:
            self._log(f"  No files matched: {globs}\n", "warning")
            self.root.after(0, lambda: self.status_var.set("No files matched"))
            return

        self._log(f"  Searching {len(files)} file(s)...\n\n", "info")
        total_matches = 0
        total_changed = 0
        if not dry_run:
            self._undo_snapshot.clear()

        backup = self._current_tab()['var_backup'].get()

        for filepath in files:
            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                self._log(f"  ERROR {filepath}: {e}\n", "error")
                continue

            matches = list(regex.finditer(content))
            if not matches:
                continue

            total_matches += len(matches)
            try:
                rel = filepath.relative_to(root)
            except ValueError:
                rel = filepath

            self._log(f"  {rel}  ({len(matches)} match(es))\n", "file")

            for m in matches:
                start_line = content[:m.start()].count("\n") + 1
                self._log(f"    ── line {start_line} ──\n", "lineno")
                matched_lines = m.group().splitlines() or [""]
                for line in matched_lines[:10]:
                    self._log(f"    - {line}\n", "removed")
                if len(matched_lines) > 10:
                    self._log(f"    - … ({len(matched_lines) - 10} more lines)\n", "removed")
                if not dry_run:
                    try:
                        replaced_lines = _expand(m, replacement).splitlines() or [""]
                    except (re.error, Exception) as e:
                        self._log(f"    ERROR in replacement: {e}\n", "error")
                        replaced_lines = []
                    for line in replaced_lines[:10]:
                        self._log(f"    + {line}\n", "added")
                    if len(replaced_lines) > 10:
                        self._log(f"    + … ({len(replaced_lines) - 10} more lines)\n", "added")

            if not dry_run:
                if backup:
                    bak = filepath.with_suffix(filepath.suffix + ".bak")
                    try:
                        bak.write_text(content, encoding="utf-8")
                    except OSError as e:
                        self._log(f"  WARNING: could not write backup {bak}: {e}\n", "warning")
                self._undo_snapshot[filepath] = content
                new_content, _ = regex.subn(replacement, content)
                try:
                    filepath.write_text(new_content, encoding="utf-8")
                    total_changed += 1
                except OSError as e:
                    self._log(f"  ERROR writing {filepath}: {e}\n", "error")

        self._log(f"\n{HR}\n", "header")
        if dry_run:
            summary = f"Found {total_matches} match(es) across {len(files)} file(s) — no changes made."
        else:
            summary = f"Made {total_matches} replacement(s) across {total_changed} file(s)."
        self._log(f"  {summary}\n", "success")
        self._log(f"{HR}\n", "header")
        self.root.after(0, lambda: self.status_var.set(summary))


# ══════════════════════════════════════════════════════════════════════ CLI ══

def cli_main() -> None:
    parser = argparse.ArgumentParser(
        description='Find and replace text in files with multiline and wildcard support.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('pattern')
    parser.add_argument('replacement')
    parser.add_argument('files', nargs='*', default=['**/*.evdl.asm'])
    parser.add_argument('--regex',      '-r', action='store_true')
    parser.add_argument('--dry-run',    '-n', action='store_true')
    parser.add_argument('--verbose',    '-v', action='store_true')
    parser.add_argument('--ignore-case','-i', action='store_true')
    parser.add_argument('--backup',     '-b', action='store_true')
    parser.add_argument('--no-dotall',        action='store_true')
    parser.add_argument('--wildlabels', '-l', action='store_true',
                        help='Treat every @LABEL in the pattern as a wildcard')
    parser.add_argument('--root', type=Path, default=Path('.'))

    args = parser.parse_args()
    dot_all = not args.no_dotall

    def unescape(s):
        return s.replace('\\n', '\n').replace('\\t', '\t')

    pattern_text = unescape(args.pattern)
    if args.wildlabels:
        pattern_text = auto_wildlabels(pattern_text)
    if args.regex:
        regex_str = apply_label_token(pattern_text)
    else:
        regex_str = wildcard_to_regex(pattern_text, dot_all)
    flags = re.DOTALL if dot_all else 0
    if args.ignore_case:
        flags |= re.IGNORECASE

    try:
        regex = re.compile(regex_str, flags)
    except re.error as e:
        print(f"Invalid pattern: {e}", file=sys.stderr)
        sys.exit(1)

    replacement = prepare_replacement(unescape(args.replacement))
    files = resolve_files(args.files, args.root)
    if not files:
        print(f"No files matched: {args.files}", file=sys.stderr)
        sys.exit(1)

    mode = "[DRY RUN] " if args.dry_run else ""
    print(f"{mode}Searching {len(files)} file(s)...")
    print(f"  Pattern:     {args.pattern!r}")
    if not args.regex:
        print(f"  As regex:    {regex_str!r}")
    print(f"  Replacement: {replacement!r}")
    print(f"  Flags:       dotall={'on' if dot_all else 'off'}  "
          f"ignorecase={'on' if args.ignore_case else 'off'}")
    print()

    total_matches = total_changed = 0
    for filepath in files:
        count, changed = process_file(
            filepath, regex, replacement,
            dry_run=args.dry_run, backup=args.backup, verbose=args.verbose,
        )
        total_matches += count
        if changed:
            total_changed += 1

    print()
    if args.dry_run:
        print(f"Found {total_matches} match(es) — no changes made.")
    else:
        print(f"Made {total_matches} replacement(s) across {total_changed} file(s).")


# ═══════════════════════════════════════════════════════════════════ entry ══

if __name__ == '__main__':
    if len(sys.argv) > 1:
        cli_main()
    else:
        root = tk.Tk()
        FindReplaceGUI(root)
        root.mainloop()
