#!/usr/bin/env python3
"""Viewer/editor for KH1 (HD 1.5 Remix) EvMsg .binl dialogue files:
a tkinter GUI plus dump/get/set/add/export/import/verify commands."""

import os
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'ev'))
from evdl_format import KH1_CHAR_MAP

USAGE = """Usage:
  python binl_tool.py                          open the GUI editor
  python binl_tool.py dump <file.binl>         print every string (index, bytes, text)
  python binl_tool.py get  <file.binl> <idx>   print one string (idx decimal or 0x..)
  python binl_tool.py set  <file.binl> <idx> "<text>" [-o out.binl] [--term 04|00]
  python binl_tool.py add  <file.binl> "<text>" [-o out.binl] [--term 04|00]   append, prints index
  python binl_tool.py export <file.binl> <out.txt>   one string per line "idx<TAB>term<TAB>text"
  python binl_tool.py import <file.binl> <in.txt> [-o out.binl]
  python binl_tool.py verify <file-or-dir> ...       decode/encode round-trip check
"""

MAGIC_PREFIX = b'EvMsg'
MAGIC_LEN = 7
LANG_OFFSET = 5
COUNT_OFFSET = 7
HEADER_LEN = 11
MAX_STRING_COUNT = 100000

END_TIMED = 0x00
END_DIALOGUE = 0x04
TERMINATOR = END_DIALOGUE
SPACE = 0x01
LINE_BREAK = 0x02
FIRST_CONTROL_CODE = 0x03
LAST_CONTROL_CODE = 0x1F

PAD_BYTE = 0xCD
PAD_ALIGN = 16
DEFAULT_DIR = 'C:/OpenKH/OpenKHEGS/data/kh1/remastered'

GENERIC_HEX_GLYPH = re.compile(r'\{0x[0-9A-Fa-f]{2}\}')
HEX_TOKEN = re.compile(r'\{0x([0-9A-Fa-f]{2})((?:\s+[0-9A-Fa-f]{2})*)\s*\}')
TERM_FIELD = re.compile(r'[0-9A-Fa-f]{2}')


def control_arg_len(code: int, next_byte: int) -> int:
    if code in (0x05, 0x06, 0x07):
        return 2
    if code in (0x0B, 0x0D):
        return 3
    if code == 0x0A:
        if next_byte != 0:
            return 1
        return 3
    if 0x09 <= code <= 0x1F:
        return 1
    return 0


def is_control_code(byte: int) -> bool:
    return FIRST_CONTROL_CODE <= byte <= LAST_CONTROL_CODE


def byte_after(data: bytes, position: int) -> int:
    if position + 1 < len(data):
        return data[position + 1]
    return 0


def build_encode_map() -> dict:
    encode_map = {}
    for byte, glyph in KH1_CHAR_MAP.items():
        if not glyph or GENERIC_HEX_GLYPH.fullmatch(glyph) or glyph in encode_map:
            continue
        encode_map[glyph] = byte
    encode_map['{lf}'] = LINE_BREAK
    encode_map[' '] = SPACE
    return encode_map


def token_names_longest_first(encode_map: dict) -> list:
    token_names = [glyph for glyph in encode_map if glyph.startswith('{')]
    return sorted(token_names, key=len, reverse=True)


ENCODE_MAP = build_encode_map()
TOKEN_NAMES = token_names_longest_first(ENCODE_MAP)


def format_control_token(code: int, args: bytes, arg_count: int) -> str:
    if arg_count == 0:
        return '{0x%02X}' % code
    hex_args = ' '.join('%02X' % arg for arg in args)
    return '{0x%02X %s}' % (code, hex_args)


def decode_string(raw: bytes) -> str:
    pieces = []
    position = 0
    while position < len(raw):
        byte = raw[position]
        if is_control_code(byte):
            arg_count = control_arg_len(byte, byte_after(raw, position))
            args = raw[position + 1:position + 1 + arg_count]
            pieces.append(format_control_token(byte, args, arg_count))
            position += 1 + arg_count
        elif byte == LINE_BREAK:
            pieces.append('{lf}')
            position += 1
        else:
            pieces.append(KH1_CHAR_MAP.get(byte, '{0x%02X}' % byte))
            position += 1
    return ''.join(pieces)


def encode_hex_token(match, position: int) -> list:
    code = int(match.group(1), 16)
    args = [int(hex_arg, 16) for hex_arg in match.group(2).split()]
    if is_control_code(code) and code != END_DIALOGUE:
        first_arg = 0
        if args:
            first_arg = args[0]
        needed = control_arg_len(code, first_arg)
        if len(args) != needed:
            raise ValueError(
                'control code {0x%02X} takes %d argument byte(s), got %d '
                '(position %d). Write it as one token, e.g. {0x07 0C 00}.'
                % (code, needed, len(args), position))
    return [code] + args


def unknown_token_error(text: str, position: int) -> ValueError:
    closing_brace = text.find('}', position)
    if closing_brace >= 0:
        shown_end = closing_brace + 1
    else:
        shown_end = position + 8
    return ValueError('Unknown token %r at position %d' % (text[position:shown_end], position))


def encode_named_token(text: str, position: int):
    for name in TOKEN_NAMES:
        if text.startswith(name, position):
            return ENCODE_MAP[name], len(name)
    raise unknown_token_error(text, position)


def encode_character(character: str, position: int) -> int:
    if character == '\n':
        return LINE_BREAK
    if character in ENCODE_MAP:
        return ENCODE_MAP[character]
    raise ValueError('Character %r (U+%04X) has no KHSCII mapping (position %d)'
                     % (character, ord(character), position))


def encode_string(text: str) -> bytes:
    encoded = bytearray()
    position = 0
    while position < len(text):
        if text[position] != '{':
            encoded.append(encode_character(text[position], position))
            position += 1
            continue
        match = HEX_TOKEN.match(text, position)
        if match:
            encoded.extend(encode_hex_token(match, position))
            position = match.end()
        else:
            byte, token_length = encode_named_token(text, position)
            encoded.append(byte)
            position += token_length
    return bytes(encoded)


def find_string_end(data: bytes, start: int) -> int:
    position = start
    while position < len(data):
        byte = data[position]
        if byte == END_DIALOGUE or byte == END_TIMED:
            break
        if is_control_code(byte):
            position += 1 + control_arg_len(byte, byte_after(data, position))
        else:
            position += 1
    return position


class BinlFile:
    def __init__(self, magic: bytes, strings: list, path: str = None, terms: list = None):
        if terms is None:
            terms = [TERMINATOR] * len(strings)
        self.magic = magic
        self.strings = strings
        self.terms = terms
        self.path = path
        self.original_size = 0

    @property
    def lang(self) -> str:
        return self.magic[LANG_OFFSET:MAGIC_LEN].decode('ascii', 'replace')

    @classmethod
    def parse(cls, data: bytes, path: str = None) -> 'BinlFile':
        if len(data) < HEADER_LEN or data[:len(MAGIC_PREFIX)] != MAGIC_PREFIX:
            raise ValueError('Not an EvMsg .binl file (bad magic)')
        magic = bytes(data[:MAGIC_LEN])
        count = struct.unpack_from('<I', data, COUNT_OFFSET)[0]
        if count > MAX_STRING_COUNT:
            raise ValueError('Implausible string count %d' % count)
        strings = []
        terms = []
        position = HEADER_LEN
        for _ in range(count):
            end = find_string_end(data, position)
            strings.append(bytes(data[position:min(end, len(data))]))
            if end < len(data):
                terms.append(data[end])
            else:
                terms.append(TERMINATOR)
            position = end + 1
        binl = cls(magic, strings, path, terms)
        binl.original_size = len(data)
        return binl

    @classmethod
    def load(cls, path: str) -> 'BinlFile':
        with open(path, 'rb') as f:
            return cls.parse(f.read(), path)

    def body_length(self) -> int:
        return HEADER_LEN + sum(len(string) + 1 for string in self.strings)

    def build(self) -> bytes:
        out = bytearray(self.magic)
        out += struct.pack('<I', len(self.strings))
        for string, term in zip(self.strings, self.terms):
            out += string
            out.append(term)
        target_size = max(self.original_size, len(out))
        while len(out) < target_size or len(out) % PAD_ALIGN:
            out.append(PAD_BYTE)
        return bytes(out)

    def save(self, path: str = None):
        if not path:
            path = self.path
        with open(path, 'wb') as f:
            f.write(self.build())
        self.path = path

    def texts(self):
        return [decode_string(string) for string in self.strings]

    def append(self, raw: bytes, term: int = TERMINATOR) -> int:
        self.strings.append(raw)
        self.terms.append(term)
        return len(self.strings) - 1


def string_round_trip_problem(name: str, index: int, string: bytes):
    try:
        reencoded = encode_string(decode_string(string))
    except ValueError as error:
        return '%s[%#x]: %s' % (name, index, error)
    if reencoded != string:
        return ('%s[%#x]: text round-trip mismatch\n  orig %s\n  back %s'
                % (name, index, string.hex(), reencoded.hex()))
    return None


def rebuild_problem(name: str, binl: BinlFile, data: bytes):
    rebuilt = binl.build()
    if rebuilt == data:
        return None
    body_length = binl.body_length()
    if rebuilt[:body_length] != data[:body_length]:
        return '%s: rebuilt body differs from original' % name
    if len(rebuilt) != len(data):
        return '%s: length %d vs original %d (padding differs)' % (name, len(rebuilt), len(data))
    return None


def verify_file(path: str) -> list:
    name = os.path.basename(path)
    with open(path, 'rb') as f:
        data = f.read()
    binl = BinlFile.parse(data, path)
    problems = []
    for index, string in enumerate(binl.strings):
        problem = string_round_trip_problem(name, index, string)
        if problem:
            problems.append(problem)
    problem = rebuild_problem(name, binl, data)
    if problem:
        problems.append(problem)
    return problems


def parse_index(text: str) -> int:
    if text.lower().startswith('0x'):
        return int(text, 16)
    return int(text, 10)


def output_path(args: list, default: str) -> str:
    if '-o' in args:
        return args[args.index('-o') + 1]
    return default


def strip_options(args: list) -> list:
    for flag in ('-o', '--term'):
        if flag in args:
            flag_index = args.index(flag)
            args = args[:flag_index] + args[flag_index + 2:]
    return args


def terminator_option(args: list, default):
    if '--term' not in args:
        return default
    term = int(args[args.index('--term') + 1], 16)
    if term not in (END_TIMED, END_DIALOGUE):
        raise ValueError('--term must be 00 or 04')
    return term


def cmd_dump(path: str):
    binl = BinlFile.load(path)
    print('%s  lang=%s  strings=%d' % (path, binl.lang, len(binl.strings)))
    for index, (string, term) in enumerate(zip(binl.strings, binl.terms)):
        print('%#05x %3dB %02X  %s' % (index, len(string), term, decode_string(string)))


def cmd_get(path: str, index: int):
    binl = BinlFile.load(path)
    string = binl.strings[index]
    print(decode_string(string))
    print('; %d bytes, terminator %#04x: %s' % (len(string), binl.terms[index], string.hex(' ')))


def cmd_set(path: str, index: int, text: str, out: str, term=None):
    binl = BinlFile.load(path)
    if not 0 <= index < len(binl.strings):
        raise SystemExit('index %#x out of range (file has %d strings)' % (index, len(binl.strings)))
    binl.strings[index] = encode_string(text)
    if term is not None:
        binl.terms[index] = term
    binl.save(out)
    print('wrote %s  [%#x] = %d bytes, terminator %#04x'
          % (out, index, len(binl.strings[index]), binl.terms[index]))


def cmd_add(path: str, text: str, out: str, term=TERMINATOR):
    binl = BinlFile.load(path)
    index = binl.append(encode_string(text), term)
    binl.save(out)
    print('wrote %s  new index %#x (%d), terminator %#04x' % (out, index, index, term))


def cmd_export(path: str, out_txt: str):
    binl = BinlFile.load(path)
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write('# %s lang=%s\n' % (os.path.basename(path), binl.lang))
        for index, (string, term) in enumerate(zip(binl.strings, binl.terms)):
            f.write('%#x\t%02X\t%s\n' % (index, term, decode_string(string)))
    print('exported %d strings to %s' % (len(binl.strings), out_txt))


def split_import_line(line: str):
    parts = line.split('\t', 2)
    if len(parts) == 3 and TERM_FIELD.fullmatch(parts[1]):
        return parts[0], int(parts[1], 16), parts[2]
    return parts[0], None, line.split('\t', 1)[1]


def import_line(binl: BinlFile, line: str, location: str):
    if '\t' not in line:
        raise SystemExit('%s: expected "idx<TAB>term<TAB>text"' % location)
    index_text, term, text = split_import_line(line)
    index = parse_index(index_text)
    encoded = encode_string(text)
    if index == len(binl.strings):
        if term is None:
            term = TERMINATOR
        binl.append(encoded, term)
    elif 0 <= index < len(binl.strings):
        binl.strings[index] = encoded
        if term is not None:
            binl.terms[index] = term
    else:
        raise SystemExit('%s: index %#x out of range' % (location, index))


def cmd_import(path: str, in_txt: str, out: str):
    binl = BinlFile.load(path)
    with open(in_txt, 'r', encoding='utf-8') as f:
        for line_number, line in enumerate(f, 1):
            line = line.rstrip('\r\n')
            if not line or line.startswith('#'):
                continue
            import_line(binl, line, '%s:%d' % (in_txt, line_number))
    binl.save(out)
    print('wrote %s (%d strings)' % (out, len(binl.strings)))


def binl_files_in(targets: list) -> list:
    files = []
    for target in targets:
        target_path = Path(target)
        if target_path.is_dir():
            files += sorted(target_path.rglob('*.binl'))
        else:
            files.append(target_path)
    return files


def cmd_verify(targets: list):
    files = binl_files_in(targets)
    files_with_problems = 0
    for file in files:
        try:
            problems = verify_file(str(file))
        except Exception as error:
            problems = ['%s: %s' % (file.name, error)]
        if problems:
            files_with_problems += 1
            for problem in problems:
                print(problem)
    print('%d files checked, %d with problems' % (len(files), files_with_problems))
    if files_with_problems:
        return 1
    return 0


def _run_gui(initial: str = None):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    binl_filetypes = [('EvMsg binl files', '*.binl'), ('All files', '*.*')]
    state = {'binl': None, 'dirty': False, 'selected': None}

    root = tk.Tk()
    root.title('BINL Editor')
    root.geometry('1000x640')

    top_bar = tk.Frame(root)
    top_bar.pack(fill='x', padx=6, pady=4)
    path_var = tk.StringVar()
    tk.Label(top_bar, text='File:').pack(side='left')
    tk.Entry(top_bar, textvariable=path_var, state='readonly', width=80).pack(side='left', fill='x', expand=True, padx=4)
    info_var = tk.StringVar(value='no file loaded')
    tk.Label(top_bar, textvariable=info_var, anchor='w').pack(side='left', padx=6)

    panes = tk.PanedWindow(root, orient='horizontal', sashrelief='raised')
    panes.pack(fill='both', expand=True, padx=6, pady=2)

    left_pane = tk.Frame(panes)
    panes.add(left_pane, minsize=380)
    filter_var = tk.StringVar()
    filter_bar = tk.Frame(left_pane)
    filter_bar.pack(fill='x')
    tk.Label(filter_bar, text='Filter:').pack(side='left')
    tk.Entry(filter_bar, textvariable=filter_var).pack(side='left', fill='x', expand=True, padx=4)

    tree = ttk.Treeview(left_pane, columns=('idx', 'len', 'term', 'text'), show='headings', selectmode='browse')
    tree.heading('idx', text='Index')
    tree.heading('len', text='Bytes')
    tree.heading('term', text='End')
    tree.heading('text', text='Text')
    tree.column('idx', width=60, anchor='e', stretch=False)
    tree.column('len', width=50, anchor='e', stretch=False)
    tree.column('term', width=36, anchor='center', stretch=False)
    tree.column('text', width=260)
    tree_scrollbar = ttk.Scrollbar(left_pane, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=tree_scrollbar.set)
    tree.pack(side='left', fill='both', expand=True)
    tree_scrollbar.pack(side='right', fill='y')

    right_pane = tk.Frame(panes)
    panes.add(right_pane, minsize=380)
    tk.Label(right_pane, text='Text  ({lf} or a newline = line break, {0xNN ..} = control code)',
             anchor='w').pack(fill='x')
    editor = tk.Text(right_pane, height=8, wrap='word', undo=True, font=('Consolas', 10))
    editor.pack(fill='both', expand=True)
    status_var = tk.StringVar()
    tk.Label(right_pane, textvariable=status_var, anchor='w', fg='#444').pack(fill='x')
    dialogue_end_var = tk.IntVar(value=1)
    tk.Checkbutton(right_pane, variable=dialogue_end_var, anchor='w',
                   text='Dialogue string (0x04 end: the window waits for the player). '
                        'Untick only for timed cutscene subtitles (0x00 end).').pack(fill='x')
    tk.Label(right_pane, text='Encoded bytes', anchor='w').pack(fill='x')
    encoded_box = tk.Text(right_pane, height=5, wrap='word', font=('Consolas', 9), state='disabled', bg='#f4f4f4')
    encoded_box.pack(fill='x')
    tk.Label(right_pane, text='Original bytes', anchor='w').pack(fill='x')
    original_box = tk.Text(right_pane, height=3, wrap='word', font=('Consolas', 9), state='disabled', bg='#f4f4f4')
    original_box.pack(fill='x')

    bottom_bar = tk.Frame(root)
    bottom_bar.pack(fill='x', padx=6, pady=4)

    def set_readonly_box(box, text):
        box.configure(state='normal')
        box.delete('1.0', 'end')
        box.insert('1.0', text)
        box.configure(state='disabled')

    def update_title():
        name = 'untitled'
        if path_var.get():
            name = os.path.basename(path_var.get())
        dirty_mark = ''
        if state['dirty']:
            dirty_mark = ' *'
        root.title('BINL Editor - %s%s' % (name, dirty_mark))

    def chosen_terminator():
        if dialogue_end_var.get():
            return END_DIALOGUE
        return END_TIMED

    def refresh_list(keep=None):
        tree.delete(*tree.get_children())
        binl = state['binl']
        if not binl:
            return
        filter_text = filter_var.get().lower()
        for index, string in enumerate(binl.strings):
            text = decode_string(string)
            if filter_text and filter_text not in text.lower() and filter_text not in ('%#x' % index):
                continue
            tree.insert('', 'end', iid=str(index), values=('%#x' % index, len(string), '%02X' % binl.terms[index],
                                                           text.replace('{lf}', ' | ')))
        info_var.set('lang=%s  strings=%d' % (binl.lang, len(binl.strings)))
        if keep is not None and tree.exists(str(keep)):
            tree.selection_set(str(keep))
            tree.see(str(keep))

    def current_text():
        return editor.get('1.0', 'end-1c')

    def update_preview(*_):
        binl = state['binl']
        if not binl or state['selected'] is None:
            return
        try:
            encoded = encode_string(current_text())
        except ValueError as error:
            status_var.set('ERROR: %s' % error)
            set_readonly_box(encoded_box, '')
            return
        original = binl.strings[state['selected']]
        delta = len(encoded) - len(original)
        sign = ''
        if delta >= 0:
            sign = '+'
        status_var.set('%d bytes (%s%d vs original)  lines=%d' %
                       (len(encoded), sign, delta, encoded.count(LINE_BREAK) + 1))
        set_readonly_box(encoded_box, encoded.hex(' '))

    def on_select(_event=None):
        selection = tree.selection()
        if not selection:
            return
        index = int(selection[0])
        previous = state['selected']
        if previous is not None and index != previous and pending_edit():
            if messagebox.askyesno('Apply edit?', 'Apply the edit to string %#x before switching?' % previous):
                apply_edit()
        state['selected'] = index
        binl = state['binl']
        string = binl.strings[index]
        editor.delete('1.0', 'end')
        editor.insert('1.0', decode_string(string))
        editor.edit_reset()
        if binl.terms[index] == END_DIALOGUE:
            dialogue_end_var.set(1)
        else:
            dialogue_end_var.set(0)
        set_readonly_box(original_box, string.hex(' ') + '   | end %02X' % binl.terms[index])
        update_preview()

    def apply_edit():
        binl = state['binl']
        if not binl or state['selected'] is None:
            return
        try:
            encoded = encode_string(current_text())
        except ValueError as error:
            messagebox.showerror('Cannot encode', str(error))
            return
        selected = state['selected']
        term = chosen_terminator()
        if encoded != binl.strings[selected] or term != binl.terms[selected]:
            binl.strings[selected] = encoded
            binl.terms[selected] = term
            state['dirty'] = True
            update_title()
        refresh_list(keep=selected)
        on_select()

    def add_string():
        binl = state['binl']
        if not binl:
            return
        binl.append(encode_string('{0x07 0C 00}New string'))
        state['dirty'] = True
        update_title()
        refresh_list(keep=len(binl.strings) - 1)
        on_select()

    def initial_dir():
        return os.path.dirname(path_var.get()) or DEFAULT_DIR

    def clear_editor():
        editor.delete('1.0', 'end')
        set_readonly_box(encoded_box, '')
        set_readonly_box(original_box, '')
        status_var.set('')

    def open_file(path=None):
        if state['dirty'] and not messagebox.askyesno('Discard changes?',
                                                       'Unsaved changes will be lost. Continue?'):
            return
        if not path:
            path = filedialog.askopenfilename(title='Open .binl', filetypes=binl_filetypes,
                                              initialdir=initial_dir())
        if not path:
            return
        try:
            binl = BinlFile.load(path)
        except Exception as error:
            messagebox.showerror('Open failed', str(error))
            return
        state['binl'] = binl
        state['dirty'] = False
        state['selected'] = None
        path_var.set(path)
        clear_editor()
        refresh_list()
        update_title()

    def pending_edit():
        binl = state['binl']
        if not binl or state['selected'] is None:
            return False
        selected = state['selected']
        if current_text() != decode_string(binl.strings[selected]):
            return True
        return chosen_terminator() != binl.terms[selected]

    def store_pending_edit():
        try:
            encoded = encode_string(current_text())
        except ValueError as error:
            messagebox.showerror('Cannot save', 'The edited string does not encode:\n' + str(error))
            return False
        binl = state['binl']
        binl.strings[state['selected']] = encoded
        binl.terms[state['selected']] = chosen_terminator()
        state['dirty'] = True
        refresh_list(keep=state['selected'])
        on_select()
        return True

    def ask_save_path():
        return filedialog.asksaveasfilename(title='Save .binl as', filetypes=binl_filetypes,
                                            defaultextension='.binl',
                                            initialdir=initial_dir(),
                                            initialfile=os.path.basename(path_var.get()))

    def save_file(save_as=False):
        binl = state['binl']
        if not binl:
            return
        if pending_edit() and not store_pending_edit():
            return
        path = path_var.get()
        if save_as or not path:
            path = ask_save_path()
            if not path:
                return
        try:
            binl.save(path)
        except Exception as error:
            messagebox.showerror('Save failed', str(error))
            return
        path_var.set(path)
        state['dirty'] = False
        update_title()
        info_var.set('saved %s  (%d strings, %d bytes)' % (os.path.basename(path), len(binl.strings), len(binl.build())))

    def on_close():
        if state['dirty'] and not messagebox.askyesno('Discard changes?',
                                                       'Unsaved changes will be lost. Quit anyway?'):
            return
        root.destroy()

    def on_open_button():
        open_file()

    def on_save_button():
        save_file(False)

    def on_save_as_button():
        save_file(True)

    def on_apply_key(_event):
        apply_edit()
        return 'break'

    def on_save_key(_event):
        save_file(False)

    def on_filter_change(*_):
        refresh_list(keep=state['selected'])

    tk.Button(bottom_bar, text='Open...', width=10, command=on_open_button).pack(side='left', padx=2)
    tk.Button(bottom_bar, text='Save', width=10, command=on_save_button).pack(side='left', padx=2)
    tk.Button(bottom_bar, text='Save As...', width=10, command=on_save_as_button).pack(side='left', padx=2)
    tk.Button(bottom_bar, text='Add string', width=10, command=add_string).pack(side='left', padx=(16, 2))
    tk.Button(bottom_bar, text='Apply edit', width=12, command=apply_edit).pack(side='right', padx=2)
    tk.Label(bottom_bar, text='Ctrl+Enter applies, Ctrl+S saves (save applies a pending edit)', fg='#666').pack(side='right', padx=8)

    tree.bind('<<TreeviewSelect>>', on_select)
    editor.bind('<KeyRelease>', update_preview)
    editor.bind('<Control-Return>', on_apply_key)
    root.bind('<Control-s>', on_save_key)
    filter_var.trace_add('write', on_filter_change)
    root.protocol('WM_DELETE_WINDOW', on_close)

    if initial:
        open_file(initial)
    root.mainloop()


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)
    if not argv:
        _run_gui()
        return 0
    command = argv[0].lower()
    if command == 'gui':
        initial = None
        if len(argv) > 1:
            initial = argv[1]
        _run_gui(initial)
        return 0
    if command == 'dump' and len(argv) == 2:
        cmd_dump(argv[1])
        return 0
    if command == 'get' and len(argv) == 3:
        cmd_get(argv[1], parse_index(argv[2]))
        return 0
    positional = strip_options(argv)
    if command == 'set' and len(positional) == 4:
        cmd_set(positional[1], parse_index(positional[2]), positional[3],
                output_path(argv, positional[1]), terminator_option(argv, None))
        return 0
    if command == 'add' and len(positional) == 3:
        cmd_add(positional[1], positional[2], output_path(argv, positional[1]), terminator_option(argv, TERMINATOR))
        return 0
    if command == 'export' and len(argv) == 3:
        cmd_export(argv[1], argv[2])
        return 0
    if command == 'import' and len(positional) == 3:
        cmd_import(positional[1], positional[2], output_path(argv, positional[1]))
        return 0
    if command == 'verify' and len(argv) >= 2:
        return cmd_verify(argv[1:])
    print(USAGE)
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError) as exc:
        print('Error: %s' % exc, file=sys.stderr)
        sys.exit(1)
