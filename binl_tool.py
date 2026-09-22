#!/usr/bin/env python3
"""
binl_tool.py - viewer/editor for KH1 (HD 1.5 Remix) EvMsg .binl message files.

The remastered game reads room dialogue from `<lang>_<room>_ard<3e8+set>.binl`
(e.g. UK_pp11_ard3e8.binl for set 0), and only falls back to the string table
embedded in the .evdl when no .binl exists.  Verified in the Steam exe:
the event start routine (0x1401a38a0) looks up the ARD entry whose id is
`set + 1000`, skips the 7-byte magic and walks the strings from there.

File layout:
    7 bytes   magic  "EvMsg" + 2-char language ("UK", "US", "FR", ...)
    u32       string count
    strings   KHSCII text, each followed by a terminator byte:
                0x04  interactive dialogue: the window waits for the player
                      (every talk line and every selection menu uses this)
                0x00  timed text: cutscene subtitles with {0x05 ..} timing codes
                      that finish on their own
              Both stop the game's string walker.  A menu string saved with
              0x00 closes instantly and the script deadlocks on Wait_selection,
              so new strings default to 0x04.  Existing terminators are kept.
    padding   0xCD up to a 16-byte boundary (vanilla files are often padded
              further, to a size shared by every language's copy; kept on save)

There is no offset table: the game builds string pointers by walking the
terminators at load time, so strings may change length freely.

Text form used by this tool (round-trips byte-exactly):
    plain characters      via the KHSCII table shared with evdl_tool.py
    {lf}                  0x02 line break
    {iPotion} {mX} ...    named glyphs from the same table
    {0x05 47 00}          a control code with its argument bytes, in hex
    {0x1B}                a control code without arguments

Control codes 0x03-0x1F own the bytes that follow them (0x05-0x07: two,
0x0B/0x0D: three, 0x0A: one or three, others: one), so the usual dialogue
header is a single token {0x07 0C 00} - NOT {0x07}{0x0C}.  The encoder
rejects a control token with the wrong number of argument bytes.

Usage:
  python binl_tool.py                          open the GUI editor
  python binl_tool.py dump <file.binl>         print every string (index, bytes, text)
  python binl_tool.py get  <file.binl> <idx>   print one string (idx decimal or 0x..)
  python binl_tool.py set  <file.binl> <idx> "<text>" [-o out.binl] [--term 04|00]
  python binl_tool.py add  <file.binl> "<text>" [-o out.binl] [--term 04|00]   append, prints index
  python binl_tool.py export <file.binl> <out.txt>   one string per line "idx<TAB>term<TAB>text"
  python binl_tool.py import <file.binl> <in.txt> [-o out.binl]
  python binl_tool.py verify <file-or-dir> ...       decode/encode round-trip check
"""

import os
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evdl_tool import _KH1_CHAR_MAP  # noqa: E402

MAGIC_PREFIX = b'EvMsg'
HEADER_LEN = 11            # 7-byte magic + u32 count
TERMINATOR = 0x04          # default for new strings (dialogue); parsed files keep their own
PAD_BYTE = 0xCD
PAD_ALIGN = 16
DEFAULT_DIR = 'C:/OpenKH/OpenKHEGS/data/kh1/remastered'

# ---------------------------------------------------------------------------
# KHSCII control codes
# ---------------------------------------------------------------------------

def control_arg_len(code: int, nxt: int) -> int:
    """Number of argument bytes that follow control byte `code`.
    Mirrors the walker in the exe (and evdl_tool.parse_evdl_string_table)."""
    if code in (0x05, 0x06, 0x07):
        return 2
    if code == 0x0B:
        return 3
    if code == 0x0A:
        return 1 if nxt != 0 else 3
    if code == 0x0D:
        return 3
    if 0x09 <= code <= 0x1F:
        return 1
    return 0


def _is_control(code: int) -> bool:
    return 0x03 <= code <= 0x1F


# reverse map for plain glyphs; generic {0xNN} entries are handled by the hex path
_ENCODE_MAP = {}
for _b, _s in _KH1_CHAR_MAP.items():
    if _s and not re.fullmatch(r'\{0x[0-9A-Fa-f]{2}\}', _s) and _s not in _ENCODE_MAP:
        _ENCODE_MAP[_s] = _b
_ENCODE_MAP['{lf}'] = 0x02
_ENCODE_MAP[' '] = 0x01
_TOKEN_NAMES = sorted((s for s in _ENCODE_MAP if s.startswith('{')), key=len, reverse=True)

# ---------------------------------------------------------------------------
# decode / encode
# ---------------------------------------------------------------------------

def decode_string(raw: bytes) -> str:
    """Bytes of one string (without terminator) -> editable text."""
    out = []
    i = 0
    n = len(raw)
    while i < n:
        b = raw[i]
        if _is_control(b):
            nxt = raw[i + 1] if i + 1 < n else 0
            alen = control_arg_len(b, nxt)
            args = raw[i + 1:i + 1 + alen]
            if b == 0x04:
                out.append('{0x04}')
            elif alen:
                out.append('{0x%02X %s}' % (b, ' '.join('%02X' % a for a in args)))
            else:
                out.append('{0x%02X}' % b)
            i += 1 + alen
        elif b == 0x02:
            out.append('{lf}')
            i += 1
        else:
            out.append(_KH1_CHAR_MAP.get(b, '{0x%02X}' % b))
            i += 1
    return ''.join(out)


_HEX_TOKEN = re.compile(r'\{0x([0-9A-Fa-f]{2})((?:\s+[0-9A-Fa-f]{2})*)\s*\}')


def encode_string(text: str) -> bytes:
    """Editable text -> KHSCII bytes (no terminator). Raises ValueError on unknown glyphs."""
    out = bytearray()
    i = 0
    n = len(text)
    while i < n:
        if text[i] == '{':
            m = _HEX_TOKEN.match(text, i)
            if m:
                code = int(m.group(1), 16)
                args = [int(h, 16) for h in m.group(2).split()]
                if _is_control(code) and code != 0x04:
                    need = control_arg_len(code, args[0] if args else 0)
                    if len(args) != need:
                        raise ValueError(
                            'control code {0x%02X} takes %d argument byte(s), got %d '
                            '(position %d). Write it as one token, e.g. {0x07 0C 00}.'
                            % (code, need, len(args), i))
                out.append(code)
                out.extend(args)
                i = m.end()
                continue
            for name in _TOKEN_NAMES:
                if text.startswith(name, i):
                    out.append(_ENCODE_MAP[name])
                    i += len(name)
                    break
            else:
                end = text.find('}', i)
                raise ValueError('Unknown token %r at position %d' % (text[i:end + 1 if end >= 0 else i + 8], i))
            continue
        ch = text[i]
        if ch == '\n':
            out.append(0x02)
        elif ch in _ENCODE_MAP:
            out.append(_ENCODE_MAP[ch])
        else:
            raise ValueError('Character %r (U+%04X) has no KHSCII mapping (position %d)' % (ch, ord(ch), i))
        i += 1
    return bytes(out)


# ---------------------------------------------------------------------------
# file parse / build
# ---------------------------------------------------------------------------

class BinlFile:
    def __init__(self, magic: bytes, strings: list, path: str = None, terms: list = None):
        self.magic = magic          # 7 bytes, e.g. b'EvMsgUK'
        self.strings = strings      # list[bytes], no terminators
        self.terms = terms if terms is not None else [TERMINATOR] * len(strings)
        self.path = path
        self.orig_len = 0           # vanilla files are padded to a shared per-room size; keep it

    @property
    def lang(self) -> str:
        return self.magic[5:7].decode('ascii', 'replace')

    @classmethod
    def parse(cls, data: bytes, path: str = None) -> 'BinlFile':
        if len(data) < HEADER_LEN or data[:5] != MAGIC_PREFIX:
            raise ValueError('Not an EvMsg .binl file (bad magic)')
        magic = bytes(data[:7])
        count = struct.unpack_from('<I', data, 7)[0]
        if count > 100000:
            raise ValueError('Implausible string count %d' % count)
        strings = []
        terms = []
        pos = HEADER_LEN
        n = len(data)
        for _ in range(count):
            start = pos
            while pos < n:
                b = data[pos]
                if b == 0x04 or b == 0x00:
                    break
                if _is_control(b):
                    nxt = data[pos + 1] if pos + 1 < n else 0
                    pos += 1 + control_arg_len(b, nxt)
                else:
                    pos += 1
            strings.append(bytes(data[start:min(pos, n)]))
            terms.append(data[pos] if pos < n else TERMINATOR)
            pos += 1
        bf = cls(magic, strings, path, terms)
        bf.orig_len = len(data)
        return bf

    @classmethod
    def load(cls, path: str) -> 'BinlFile':
        with open(path, 'rb') as f:
            return cls.parse(f.read(), path)

    def build(self) -> bytes:
        out = bytearray(self.magic)
        out += struct.pack('<I', len(self.strings))
        for s, t in zip(self.strings, self.terms):
            out += s
            out.append(t)
        target = max(self.orig_len, len(out))
        while len(out) < target or len(out) % PAD_ALIGN:
            out.append(PAD_BYTE)
        return bytes(out)

    def save(self, path: str = None):
        path = path or self.path
        with open(path, 'wb') as f:
            f.write(self.build())
        self.path = path

    def texts(self):
        return [decode_string(s) for s in self.strings]

    def append(self, raw: bytes, term: int = TERMINATOR) -> int:
        self.strings.append(raw)
        self.terms.append(term)
        return len(self.strings) - 1


def verify_file(path: str) -> list:
    """Return a list of problems (empty when the file round-trips exactly)."""
    problems = []
    data = open(path, 'rb').read()
    bf = BinlFile.parse(data, path)
    for i, s in enumerate(bf.strings):
        try:
            enc = encode_string(decode_string(s))
        except ValueError as e:
            problems.append('%s[%#x]: %s' % (os.path.basename(path), i, e))
            continue
        if enc != s:
            problems.append('%s[%#x]: text round-trip mismatch\n  orig %s\n  back %s'
                            % (os.path.basename(path), i, s.hex(), enc.hex()))
    rebuilt = bf.build()
    if rebuilt != data:
        # allow for files whose padding differs; compare the meaningful part
        body_len = HEADER_LEN + sum(len(s) + 1 for s in bf.strings)
        if rebuilt[:body_len] != data[:body_len]:
            problems.append('%s: rebuilt body differs from original' % os.path.basename(path))
        elif len(rebuilt) != len(data):
            problems.append('%s: length %d vs original %d (padding differs)'
                            % (os.path.basename(path), len(rebuilt), len(data)))
    return problems


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_idx(s: str) -> int:
    return int(s, 16) if s.lower().startswith('0x') else int(s, 10)


def _out_path(args: list, default: str) -> str:
    if '-o' in args:
        i = args.index('-o')
        return args[i + 1]
    return default


def _strip_o(args: list) -> list:
    for flag in ('-o', '--term'):
        if flag in args:
            i = args.index(flag)
            args = args[:i] + args[i + 2:]
    return args


def _term_opt(args: list, default):
    if '--term' in args:
        t = int(args[args.index('--term') + 1], 16)
        if t not in (0x00, 0x04):
            raise ValueError('--term must be 00 or 04')
        return t
    return default


def cmd_dump(path: str):
    bf = BinlFile.load(path)
    print('%s  lang=%s  strings=%d' % (path, bf.lang, len(bf.strings)))
    for i, (s, t) in enumerate(zip(bf.strings, bf.terms)):
        print('%#05x %3dB %02X  %s' % (i, len(s), t, decode_string(s)))


def cmd_get(path: str, idx: int):
    bf = BinlFile.load(path)
    s = bf.strings[idx]
    print(decode_string(s))
    print('; %d bytes, terminator %#04x: %s' % (len(s), bf.terms[idx], s.hex(' ')))


def cmd_set(path: str, idx: int, text: str, out: str, term=None):
    bf = BinlFile.load(path)
    if not 0 <= idx < len(bf.strings):
        raise SystemExit('index %#x out of range (file has %d strings)' % (idx, len(bf.strings)))
    bf.strings[idx] = encode_string(text)
    if term is not None:
        bf.terms[idx] = term
    bf.save(out)
    print('wrote %s  [%#x] = %d bytes, terminator %#04x' % (out, idx, len(bf.strings[idx]), bf.terms[idx]))


def cmd_add(path: str, text: str, out: str, term=TERMINATOR):
    bf = BinlFile.load(path)
    idx = bf.append(encode_string(text), term)
    bf.save(out)
    print('wrote %s  new index %#x (%d), terminator %#04x' % (out, idx, idx, term))


def cmd_export(path: str, out_txt: str):
    bf = BinlFile.load(path)
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write('# %s lang=%s\n' % (os.path.basename(path), bf.lang))
        for i, (s, t) in enumerate(zip(bf.strings, bf.terms)):
            f.write('%#x\t%02X\t%s\n' % (i, t, decode_string(s)))
    print('exported %d strings to %s' % (len(bf.strings), out_txt))


def cmd_import(path: str, in_txt: str, out: str):
    bf = BinlFile.load(path)
    with open(in_txt, 'r', encoding='utf-8') as f:
        for ln, line in enumerate(f, 1):
            line = line.rstrip('\r\n')
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t', 2)
            if len(parts) < 2:
                raise SystemExit('%s:%d: expected "idx<TAB>term<TAB>text"' % (in_txt, ln))
            term = None
            if len(parts) == 3 and re.fullmatch(r'[0-9A-Fa-f]{2}', parts[1]):
                idx_s, term, text = parts[0], int(parts[1], 16), parts[2]
            else:
                idx_s, text = parts[0], line.split('\t', 1)[1]
            idx = _parse_idx(idx_s)
            enc = encode_string(text)
            if idx == len(bf.strings):
                bf.append(enc, TERMINATOR if term is None else term)
            elif 0 <= idx < len(bf.strings):
                bf.strings[idx] = enc
                if term is not None:
                    bf.terms[idx] = term
            else:
                raise SystemExit('%s:%d: index %#x out of range' % (in_txt, ln, idx))
    bf.save(out)
    print('wrote %s (%d strings)' % (out, len(bf.strings)))


def cmd_verify(targets: list):
    files = []
    for t in targets:
        p = Path(t)
        if p.is_dir():
            files += sorted(p.rglob('*.binl'))
        else:
            files.append(p)
    total = 0
    bad = 0
    for f in files:
        total += 1
        try:
            probs = verify_file(str(f))
        except Exception as e:  # noqa: BLE001
            probs = ['%s: %s' % (f.name, e)]
        if probs:
            bad += 1
            for p in probs:
                print(p)
    print('%d files checked, %d with problems' % (total, bad))
    return 1 if bad else 0


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

def _run_gui(initial: str = None):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    BINL_FT = [('EvMsg binl files', '*.binl'), ('All files', '*.*')]
    state = {'bf': None, 'dirty': False, 'sel': None}

    root = tk.Tk()
    root.title('BINL Editor')
    root.geometry('1000x640')

    # --- top bar -----------------------------------------------------------
    top = tk.Frame(root)
    top.pack(fill='x', padx=6, pady=4)
    path_var = tk.StringVar()
    tk.Label(top, text='File:').pack(side='left')
    tk.Entry(top, textvariable=path_var, state='readonly', width=80).pack(side='left', fill='x', expand=True, padx=4)
    info_var = tk.StringVar(value='no file loaded')
    tk.Label(top, textvariable=info_var, anchor='w').pack(side='left', padx=6)

    # --- middle: list + editor ----------------------------------------------
    mid = tk.PanedWindow(root, orient='horizontal', sashrelief='raised')
    mid.pack(fill='both', expand=True, padx=6, pady=2)

    left = tk.Frame(mid)
    mid.add(left, minsize=380)
    filt_var = tk.StringVar()
    ff = tk.Frame(left)
    ff.pack(fill='x')
    tk.Label(ff, text='Filter:').pack(side='left')
    tk.Entry(ff, textvariable=filt_var).pack(side='left', fill='x', expand=True, padx=4)

    cols = ('idx', 'len', 'term', 'text')
    tree = ttk.Treeview(left, columns=cols, show='headings', selectmode='browse')
    tree.heading('idx', text='Index')
    tree.heading('len', text='Bytes')
    tree.heading('term', text='End')
    tree.heading('text', text='Text')
    tree.column('idx', width=60, anchor='e', stretch=False)
    tree.column('len', width=50, anchor='e', stretch=False)
    tree.column('term', width=36, anchor='center', stretch=False)
    tree.column('text', width=260)
    tsb = ttk.Scrollbar(left, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=tsb.set)
    tree.pack(side='left', fill='both', expand=True)
    tsb.pack(side='right', fill='y')

    right = tk.Frame(mid)
    mid.add(right, minsize=380)
    tk.Label(right, text='Text  ({lf} or a newline = line break, {0xNN ..} = control code)',
             anchor='w').pack(fill='x')
    editor = tk.Text(right, height=8, wrap='word', undo=True, font=('Consolas', 10))
    editor.pack(fill='both', expand=True)
    stat_var = tk.StringVar()
    tk.Label(right, textvariable=stat_var, anchor='w', fg='#444').pack(fill='x')
    term_var = tk.IntVar(value=1)
    tk.Checkbutton(right, variable=term_var, anchor='w',
                   text='Dialogue string (0x04 end: the window waits for the player). '
                        'Untick only for timed cutscene subtitles (0x00 end).').pack(fill='x')
    tk.Label(right, text='Encoded bytes', anchor='w').pack(fill='x')
    hexbox = tk.Text(right, height=5, wrap='word', font=('Consolas', 9), state='disabled', bg='#f4f4f4')
    hexbox.pack(fill='x')
    tk.Label(right, text='Original bytes', anchor='w').pack(fill='x')
    origbox = tk.Text(right, height=3, wrap='word', font=('Consolas', 9), state='disabled', bg='#f4f4f4')
    origbox.pack(fill='x')

    # --- bottom buttons -------------------------------------------------------
    bot = tk.Frame(root)
    bot.pack(fill='x', padx=6, pady=4)

    def _set_box(box, text):
        box.configure(state='normal')
        box.delete('1.0', 'end')
        box.insert('1.0', text)
        box.configure(state='disabled')

    def _title():
        name = os.path.basename(path_var.get()) if path_var.get() else 'untitled'
        root.title('BINL Editor - %s%s' % (name, ' *' if state['dirty'] else ''))

    def refresh_list(keep=None):
        tree.delete(*tree.get_children())
        bf = state['bf']
        if not bf:
            return
        flt = filt_var.get().lower()
        for i, s in enumerate(bf.strings):
            txt = decode_string(s)
            if flt and flt not in txt.lower() and flt not in ('%#x' % i):
                continue
            tree.insert('', 'end', iid=str(i), values=('%#x' % i, len(s), '%02X' % bf.terms[i],
                                                       txt.replace('{lf}', ' | ')))
        info_var.set('lang=%s  strings=%d' % (bf.lang, len(bf.strings)))
        if keep is not None and tree.exists(str(keep)):
            tree.selection_set(str(keep))
            tree.see(str(keep))

    def current_text():
        return editor.get('1.0', 'end-1c')

    def update_preview(*_):
        bf = state['bf']
        if not bf or state['sel'] is None:
            return
        try:
            enc = encode_string(current_text())
        except ValueError as e:
            stat_var.set('ERROR: %s' % e)
            _set_box(hexbox, '')
            return
        orig = bf.strings[state['sel']]
        delta = len(enc) - len(orig)
        stat_var.set('%d bytes (%s%d vs original)  lines=%d' %
                     (len(enc), '+' if delta >= 0 else '', delta, enc.count(0x02) + 1))
        _set_box(hexbox, enc.hex(' '))

    def on_select(_evt=None):
        sel = tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if state['sel'] is not None and idx != state['sel'] and pending_edit():
            if messagebox.askyesno('Apply edit?', 'Apply the edit to string %#x before switching?' % state['sel']):
                apply_edit()
        state['sel'] = idx
        s = state['bf'].strings[idx]
        editor.delete('1.0', 'end')
        editor.insert('1.0', decode_string(s))
        editor.edit_reset()
        term_var.set(1 if state['bf'].terms[idx] == 0x04 else 0)
        _set_box(origbox, s.hex(' ') + '   | end %02X' % state['bf'].terms[idx])
        update_preview()

    def apply_edit():
        bf = state['bf']
        if not bf or state['sel'] is None:
            return
        try:
            enc = encode_string(current_text())
        except ValueError as e:
            messagebox.showerror('Cannot encode', str(e))
            return
        want = 0x04 if term_var.get() else 0x00
        if enc != bf.strings[state['sel']] or want != bf.terms[state['sel']]:
            bf.strings[state['sel']] = enc
            bf.terms[state['sel']] = want
            state['dirty'] = True
            _title()
        refresh_list(keep=state['sel'])
        on_select()

    def add_string():
        bf = state['bf']
        if not bf:
            return
        bf.append(encode_string('{0x07 0C 00}New string'))
        state['dirty'] = True
        _title()
        refresh_list(keep=len(bf.strings) - 1)
        on_select()

    def open_file(path=None):
        if state['dirty'] and not messagebox.askyesno('Discard changes?',
                                                       'Unsaved changes will be lost. Continue?'):
            return
        if not path:
            path = filedialog.askopenfilename(title='Open .binl', filetypes=BINL_FT,
                                              initialdir=os.path.dirname(path_var.get()) or DEFAULT_DIR)
        if not path:
            return
        try:
            bf = BinlFile.load(path)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror('Open failed', str(e))
            return
        state['bf'] = bf
        state['dirty'] = False
        state['sel'] = None
        path_var.set(path)
        editor.delete('1.0', 'end')
        _set_box(hexbox, '')
        _set_box(origbox, '')
        stat_var.set('')
        refresh_list()
        _title()

    def pending_edit():
        """True when the editor text differs from the selected string as stored."""
        bf = state['bf']
        if not bf or state['sel'] is None:
            return False
        want = 0x04 if term_var.get() else 0x00
        return (current_text() != decode_string(bf.strings[state['sel']])
                or want != bf.terms[state['sel']])

    def save_file(save_as=False):
        bf = state['bf']
        if not bf:
            return
        if pending_edit():
            try:
                enc = encode_string(current_text())
            except ValueError as e:
                messagebox.showerror('Cannot save', 'The edited string does not encode:' + chr(10) + str(e))
                return
            bf.strings[state['sel']] = enc
            bf.terms[state['sel']] = 0x04 if term_var.get() else 0x00
            state['dirty'] = True
            refresh_list(keep=state['sel'])
            on_select()
        path = path_var.get()
        if save_as or not path:
            path = filedialog.asksaveasfilename(title='Save .binl as', filetypes=BINL_FT,
                                                defaultextension='.binl',
                                                initialdir=os.path.dirname(path_var.get()) or DEFAULT_DIR,
                                                initialfile=os.path.basename(path_var.get()))
            if not path:
                return
        try:
            bf.save(path)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror('Save failed', str(e))
            return
        path_var.set(path)
        state['dirty'] = False
        _title()
        info_var.set('saved %s  (%d strings, %d bytes)' % (os.path.basename(path), len(bf.strings), len(bf.build())))

    def on_close():
        if state['dirty'] and not messagebox.askyesno('Discard changes?',
                                                       'Unsaved changes will be lost. Quit anyway?'):
            return
        root.destroy()

    tk.Button(bot, text='Open...', width=10, command=lambda: open_file()).pack(side='left', padx=2)
    tk.Button(bot, text='Save', width=10, command=lambda: save_file(False)).pack(side='left', padx=2)
    tk.Button(bot, text='Save As...', width=10, command=lambda: save_file(True)).pack(side='left', padx=2)
    tk.Button(bot, text='Add string', width=10, command=add_string).pack(side='left', padx=(16, 2))
    tk.Button(bot, text='Apply edit', width=12, command=apply_edit).pack(side='right', padx=2)
    tk.Label(bot, text='Ctrl+Enter applies, Ctrl+S saves (save applies a pending edit)', fg='#666').pack(side='right', padx=8)

    tree.bind('<<TreeviewSelect>>', on_select)
    editor.bind('<KeyRelease>', update_preview)
    editor.bind('<Control-Return>', lambda e: (apply_edit(), 'break')[1])
    root.bind('<Control-s>', lambda e: save_file(False))
    filt_var.trace_add('write', lambda *_: refresh_list(keep=state['sel']))
    root.protocol('WM_DELETE_WINDOW', on_close)

    if initial:
        open_file(initial)
    root.mainloop()


# ---------------------------------------------------------------------------

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        _run_gui()
        return 0
    cmd = argv[0].lower()
    if cmd == 'gui':
        _run_gui(argv[1] if len(argv) > 1 else None)
        return 0
    if cmd == 'dump' and len(argv) == 2:
        cmd_dump(argv[1])
        return 0
    if cmd == 'get' and len(argv) == 3:
        cmd_get(argv[1], _parse_idx(argv[2]))
        return 0
    if cmd == 'set' and len(_strip_o(argv)) == 4:
        a = _strip_o(argv)
        cmd_set(a[1], _parse_idx(a[2]), a[3], _out_path(argv, a[1]), _term_opt(argv, None))
        return 0
    if cmd == 'add' and len(_strip_o(argv)) == 3:
        a = _strip_o(argv)
        cmd_add(a[1], a[2], _out_path(argv, a[1]), _term_opt(argv, TERMINATOR))
        return 0
    if cmd == 'export' and len(argv) == 3:
        cmd_export(argv[1], argv[2])
        return 0
    if cmd == 'import' and len(_strip_o(argv)) == 3:
        a = _strip_o(argv)
        cmd_import(a[1], a[2], _out_path(argv, a[1]))
        return 0
    if cmd == 'verify' and len(argv) >= 2:
        return cmd_verify(argv[1:])
    print(__doc__)
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError) as exc:
        print('Error: %s' % exc, file=sys.stderr)
        sys.exit(1)
