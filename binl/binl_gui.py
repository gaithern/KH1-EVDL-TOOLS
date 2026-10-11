import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from binl_file import load_binl
from binl_text import END_OF_DIALOGUE_STRING, END_OF_TIMED_STRING, LINE_BREAK, decode_text, encode_text

DEFAULT_DIR = 'C:/OpenKH/OpenKHEGS/data/kh1/remastered'
BINL_FILE_TYPES = [('EvMsg binl files', '*.binl'), ('All files', '*.*')]
NEW_STRING_TEXT = '{0x07 0C 00}New string'


def set_read_only_box(box, text):
    box.configure(state='normal')
    box.delete('1.0', 'end')
    box.insert('1.0', text)
    box.configure(state='disabled')


class BinlEditor:
    def __init__(self, initial_path=None):
        self.binl = None
        self.dirty = False
        self.selected = None

        self.root = tk.Tk()
        self.root.title('BINL Editor')
        self.root.geometry('1000x640')

        self.build_top_bar()
        panes = tk.PanedWindow(self.root, orient='horizontal', sashrelief='raised')
        panes.pack(fill='both', expand=True, padx=6, pady=2)
        self.build_string_list(panes)
        self.build_editor(panes)
        self.build_bottom_bar()

        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        self.editor.bind('<KeyRelease>', self.update_preview)
        self.editor.bind('<Control-Return>', self.on_apply_key)
        self.root.bind('<Control-s>', self.on_save_key)
        self.filter_var.trace_add('write', self.on_filter_change)
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

        if initial_path:
            self.open_file(initial_path)

    def build_top_bar(self):
        top_bar = tk.Frame(self.root)
        top_bar.pack(fill='x', padx=6, pady=4)
        self.path_var = tk.StringVar()
        tk.Label(top_bar, text='File:').pack(side='left')
        path_entry = tk.Entry(top_bar, textvariable=self.path_var, state='readonly', width=80)
        path_entry.pack(side='left', fill='x', expand=True, padx=4)
        self.info_var = tk.StringVar(value='no file loaded')
        tk.Label(top_bar, textvariable=self.info_var, anchor='w').pack(side='left', padx=6)

    def build_string_list(self, panes):
        left_pane = tk.Frame(panes)
        panes.add(left_pane, minsize=380)
        self.filter_var = tk.StringVar()
        filter_bar = tk.Frame(left_pane)
        filter_bar.pack(fill='x')
        tk.Label(filter_bar, text='Filter:').pack(side='left')
        tk.Entry(filter_bar, textvariable=self.filter_var).pack(side='left', fill='x', expand=True, padx=4)

        self.tree = ttk.Treeview(left_pane, columns=('idx', 'len', 'term', 'text'), show='headings',
                                 selectmode='browse')
        self.tree.heading('idx', text='Index')
        self.tree.heading('len', text='Bytes')
        self.tree.heading('term', text='End')
        self.tree.heading('text', text='Text')
        self.tree.column('idx', width=60, anchor='e', stretch=False)
        self.tree.column('len', width=50, anchor='e', stretch=False)
        self.tree.column('term', width=36, anchor='center', stretch=False)
        self.tree.column('text', width=260)
        tree_scrollbar = ttk.Scrollbar(left_pane, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        self.tree.pack(side='left', fill='both', expand=True)
        tree_scrollbar.pack(side='right', fill='y')

    def build_editor(self, panes):
        right_pane = tk.Frame(panes)
        panes.add(right_pane, minsize=380)
        tk.Label(right_pane, text='Text  ({lf} or a newline = line break, {0xNN ..} = control code)',
                 anchor='w').pack(fill='x')
        self.editor = tk.Text(right_pane, height=8, wrap='word', undo=True, font=('Consolas', 10))
        self.editor.pack(fill='both', expand=True)
        self.status_var = tk.StringVar()
        tk.Label(right_pane, textvariable=self.status_var, anchor='w', fg='#444').pack(fill='x')
        self.dialogue_ending_var = tk.IntVar(value=1)
        tk.Checkbutton(right_pane, variable=self.dialogue_ending_var, anchor='w',
                       text='Dialogue string (0x04 end: the window waits for the player). '
                            'Untick only for timed cutscene subtitles (0x00 end).').pack(fill='x')
        tk.Label(right_pane, text='Encoded bytes', anchor='w').pack(fill='x')
        self.encoded_box = tk.Text(right_pane, height=5, wrap='word', font=('Consolas', 9),
                                   state='disabled', bg='#f4f4f4')
        self.encoded_box.pack(fill='x')
        tk.Label(right_pane, text='Original bytes', anchor='w').pack(fill='x')
        self.original_box = tk.Text(right_pane, height=3, wrap='word', font=('Consolas', 9),
                                    state='disabled', bg='#f4f4f4')
        self.original_box.pack(fill='x')

    def build_bottom_bar(self):
        bottom_bar = tk.Frame(self.root)
        bottom_bar.pack(fill='x', padx=6, pady=4)
        tk.Button(bottom_bar, text='Open...', width=10, command=self.on_open_button).pack(side='left', padx=2)
        tk.Button(bottom_bar, text='Save', width=10, command=self.on_save_button).pack(side='left', padx=2)
        tk.Button(bottom_bar, text='Save As...', width=10, command=self.on_save_as_button).pack(side='left', padx=2)
        tk.Button(bottom_bar, text='Add string', width=10, command=self.add_string).pack(side='left', padx=(16, 2))
        tk.Button(bottom_bar, text='Apply edit', width=12, command=self.apply_edit).pack(side='right', padx=2)
        tk.Label(bottom_bar, text='Ctrl+Enter applies, Ctrl+S saves (save applies a pending edit)',
                 fg='#666').pack(side='right', padx=8)

    def run(self):
        self.root.mainloop()

    def update_title(self):
        name = 'untitled'
        if self.path_var.get():
            name = os.path.basename(self.path_var.get())
        dirty_mark = ''
        if self.dirty:
            dirty_mark = ' *'
        self.root.title('BINL Editor - %s%s' % (name, dirty_mark))

    def chosen_ending(self):
        if self.dialogue_ending_var.get():
            return END_OF_DIALOGUE_STRING
        return END_OF_TIMED_STRING

    def current_text(self):
        return self.editor.get('1.0', 'end-1c')

    def matches_filter(self, index, text):
        filter_text = self.filter_var.get().lower()
        if filter_text == '':
            return True
        if filter_text in text.lower():
            return True
        return filter_text in ('%#x' % index)

    def refresh_list(self, keep=None):
        self.tree.delete(*self.tree.get_children())
        if not self.binl:
            return
        for index in range(len(self.binl.strings)):
            string = self.binl.strings[index]
            text = decode_text(string)
            if not self.matches_filter(index, text):
                continue
            row = ('%#x' % index, len(string), '%02X' % self.binl.endings[index], text.replace('{lf}', ' | '))
            self.tree.insert('', 'end', iid=str(index), values=row)
        self.info_var.set('lang=%s  strings=%d' % (self.binl.language(), len(self.binl.strings)))
        if keep is not None and self.tree.exists(str(keep)):
            self.tree.selection_set(str(keep))
            self.tree.see(str(keep))

    def update_preview(self, event=None):
        if not self.binl or self.selected is None:
            return
        try:
            encoded = encode_text(self.current_text())
        except ValueError as error:
            self.status_var.set('ERROR: %s' % error)
            set_read_only_box(self.encoded_box, '')
            return
        original = self.binl.strings[self.selected]
        difference = len(encoded) - len(original)
        sign = ''
        if difference >= 0:
            sign = '+'
        line_count = encoded.count(LINE_BREAK) + 1
        self.status_var.set('%d bytes (%s%d vs original)  lines=%d' % (len(encoded), sign, difference, line_count))
        set_read_only_box(self.encoded_box, encoded.hex(' '))

    def on_select(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return
        index = int(selection[0])
        previous = self.selected
        if previous is not None and index != previous and self.has_pending_edit():
            if messagebox.askyesno('Apply edit?', 'Apply the edit to string %#x before switching?' % previous):
                self.apply_edit()
        self.selected = index
        string = self.binl.strings[index]
        ending = self.binl.endings[index]
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', decode_text(string))
        self.editor.edit_reset()
        if ending == END_OF_DIALOGUE_STRING:
            self.dialogue_ending_var.set(1)
        else:
            self.dialogue_ending_var.set(0)
        set_read_only_box(self.original_box, string.hex(' ') + '   | end %02X' % ending)
        self.update_preview()

    def apply_edit(self):
        if not self.binl or self.selected is None:
            return
        try:
            encoded = encode_text(self.current_text())
        except ValueError as error:
            messagebox.showerror('Cannot encode', str(error))
            return
        selected = self.selected
        ending = self.chosen_ending()
        if encoded != self.binl.strings[selected] or ending != self.binl.endings[selected]:
            self.binl.strings[selected] = encoded
            self.binl.endings[selected] = ending
            self.dirty = True
            self.update_title()
        self.refresh_list(keep=selected)
        self.on_select()

    def add_string(self):
        if not self.binl:
            return
        self.binl.append(encode_text(NEW_STRING_TEXT))
        self.dirty = True
        self.update_title()
        self.refresh_list(keep=len(self.binl.strings) - 1)
        self.on_select()

    def initial_dir(self):
        folder = os.path.dirname(self.path_var.get())
        if folder:
            return folder
        return DEFAULT_DIR

    def clear_editor(self):
        self.editor.delete('1.0', 'end')
        set_read_only_box(self.encoded_box, '')
        set_read_only_box(self.original_box, '')
        self.status_var.set('')

    def open_file(self, path=None):
        if self.dirty:
            if not messagebox.askyesno('Discard changes?', 'Unsaved changes will be lost. Continue?'):
                return
        if not path:
            path = filedialog.askopenfilename(title='Open .binl', filetypes=BINL_FILE_TYPES,
                                              initialdir=self.initial_dir())
        if not path:
            return
        try:
            binl = load_binl(path)
        except Exception as error:
            messagebox.showerror('Open failed', str(error))
            return
        self.binl = binl
        self.dirty = False
        self.selected = None
        self.path_var.set(path)
        self.clear_editor()
        self.refresh_list()
        self.update_title()

    def has_pending_edit(self):
        if not self.binl or self.selected is None:
            return False
        if self.current_text() != decode_text(self.binl.strings[self.selected]):
            return True
        return self.chosen_ending() != self.binl.endings[self.selected]

    def store_pending_edit(self):
        try:
            encoded = encode_text(self.current_text())
        except ValueError as error:
            messagebox.showerror('Cannot save', 'The edited string does not encode:\n' + str(error))
            return False
        self.binl.strings[self.selected] = encoded
        self.binl.endings[self.selected] = self.chosen_ending()
        self.dirty = True
        self.refresh_list(keep=self.selected)
        self.on_select()
        return True

    def ask_save_path(self):
        return filedialog.asksaveasfilename(title='Save .binl as', filetypes=BINL_FILE_TYPES,
                                            defaultextension='.binl',
                                            initialdir=self.initial_dir(),
                                            initialfile=os.path.basename(self.path_var.get()))

    def save_file(self, save_as):
        if not self.binl:
            return
        if self.has_pending_edit():
            if not self.store_pending_edit():
                return
        path = self.path_var.get()
        if save_as or not path:
            path = self.ask_save_path()
            if not path:
                return
        try:
            self.binl.save(path)
        except Exception as error:
            messagebox.showerror('Save failed', str(error))
            return
        self.path_var.set(path)
        self.dirty = False
        self.update_title()
        size = len(self.binl.to_bytes())
        self.info_var.set('saved %s  (%d strings, %d bytes)' % (os.path.basename(path), len(self.binl.strings), size))

    def on_close(self):
        if self.dirty:
            if not messagebox.askyesno('Discard changes?', 'Unsaved changes will be lost. Quit anyway?'):
                return
        self.root.destroy()

    def on_open_button(self):
        self.open_file()

    def on_save_button(self):
        self.save_file(False)

    def on_save_as_button(self):
        self.save_file(True)

    def on_apply_key(self, event):
        self.apply_edit()
        return 'break'

    def on_save_key(self, event):
        self.save_file(False)

    def on_filter_change(self, *trace_arguments):
        self.refresh_list(keep=self.selected)


def run_gui(initial_path=None):
    editor = BinlEditor(initial_path)
    editor.run()
