#!/usr/bin/env python3
"""Read-only viewer for KH1 <world>.wdt files: a tkinter GUI plus `dump` and
`verify` command-line modes."""
import base64
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'wdt'))
from wdt_format import DEFAULT_DIR, Wdt, format_hex, raw_hex, walk_nodes
from wdt_music import find_music_csv, load_music
from wdt_images import checker_composite, png_bytes
from wdt_report import dump, verify


HELP_TEXT = """
Usage:
    python wdt_tool.py [--music music.csv] [file.wdt]         open the GUI
    python wdt_tool.py [--music music.csv] dump <file.wdt>    print every field
    python wdt_tool.py [--music music.csv] verify [dir]       check every .wdt in a folder
"""


def run_gui(initial_path: str = None, music_path=None):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    wdt_file_types = [('World data', '*.wdt'), ('All files', '*.*')]
    column_widths = {'Entrance': 80, 'Offset': 70, 'Area': 50, 'Room': 55, 'Sora x, y, z, rot': 190,
                     'Slot 1': 190, 'Slot 2': 190, 'Used by': 160, 'Group': 55, 'Field BGM': 190,
                     'Battle BGM': 190, 'Flags': 50, '+14': 50, '+18': 50, '+1C': 55, '+20': 65,
                     '+24': 65, 'Alt BGM': 300, 'Entrances': 200, 'KGR': 50, 'Size': 70, 'Scripts': 60,
                     'Change_area targets': 420, 'BGM': 80, 'Track': 220, 'File / length': 290,
                     'Field in': 170, 'Battle in': 170, 'Alt (story >= 0x2B) in': 170}
    stretching_columns = ('Value', 'Note', 'Used by', 'Change_area targets', 'Entrances',
                          'Alt (story >= 0x2B) in')
    field_columns = ('File off', 'Rel', 'Size', 'Raw bytes', 'Type', 'Field', 'Value', 'Note')
    field_column_widths = (80, 50, 45, 200, 60, 170, 290, 380)
    hex_limit = 0x10000
    hex_bytes_column = 10
    hex_last_column = 58
    hex_second_half_column = 25
    state = {'wdt': None, 'path': None, 'node': None, 'items': {}, 'rows': {}, 'img': None,
             'hex_base': 0, 'hex_len': 0, 'field_rows': {}, 'music': {}, 'music_path': None,
             'pending': None}

    root = tk.Tk()
    root.title('WDT Viewer')
    root.geometry('1400x860')

    top = tk.Frame(root)
    top.pack(fill='x', padx=6, pady=4)
    open_button = tk.Button(top, text='Open...')
    open_button.pack(side='left')
    reload_button = tk.Button(top, text='Reload')
    reload_button.pack(side='left', padx=4)
    music_button = tk.Button(top, text='Music table...')
    music_button.pack(side='left')
    path_var = tk.StringVar()
    tk.Entry(top, textvariable=path_var, state='readonly', width=70).pack(side='left', fill='x', expand=True, padx=4)
    tk.Label(top, text='Go to offset:').pack(side='left')
    goto_var = tk.StringVar()
    goto_entry = tk.Entry(top, textvariable=goto_var, width=10)
    goto_entry.pack(side='left', padx=4)
    info_var = tk.StringVar(value='no file loaded')
    tk.Label(root, textvariable=info_var, anchor='w', fg='#444').pack(fill='x', padx=8)

    panes = tk.PanedWindow(root, orient='horizontal', sashrelief='raised')
    panes.pack(fill='both', expand=True, padx=6, pady=2)

    left = tk.Frame(panes)
    panes.add(left, minsize=260, width=320)
    tree = ttk.Treeview(left, columns=('range',), selectmode='browse')
    tree.heading('#0', text='Structure')
    tree.heading('range', text='Range')
    tree.column('#0', width=210)
    tree.column('range', width=110, anchor='w')
    tree_scrollbar = ttk.Scrollbar(left, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=tree_scrollbar.set)
    tree.pack(side='left', fill='both', expand=True)
    tree_scrollbar.pack(side='right', fill='y')

    right = tk.PanedWindow(panes, orient='vertical', sashrelief='raised')
    panes.add(right, minsize=500)

    upper = tk.Frame(right)
    right.add(upper, minsize=200, height=470)
    title_var = tk.StringVar()
    tk.Label(upper, textvariable=title_var, anchor='w', font=('Segoe UI', 10, 'bold')).pack(fill='x')
    node_info_var = tk.StringVar()
    tk.Label(upper, textvariable=node_info_var, anchor='w', fg='#555').pack(fill='x')

    image_bar = tk.Frame(upper)
    image_label = tk.Label(image_bar, bd=1, relief='sunken')
    image_label.pack(side='left', padx=2, pady=2)
    save_png_button = tk.Button(image_bar, text='Save PNG...')
    save_png_button.pack(side='left', padx=6, anchor='n')

    table_frame = tk.Frame(upper)
    table_frame.pack(fill='both', expand=True)
    table = ttk.Treeview(table_frame, show='headings', selectmode='browse')
    table_xscroll = ttk.Scrollbar(table_frame, orient='horizontal', command=table.xview)
    table_yscroll = ttk.Scrollbar(table_frame, orient='vertical', command=table.yview)
    table.configure(xscrollcommand=table_xscroll.set, yscrollcommand=table_yscroll.set)
    table.grid(row=0, column=0, sticky='nsew')
    table_yscroll.grid(row=0, column=1, sticky='ns')
    table_xscroll.grid(row=1, column=0, sticky='ew')
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    lower = tk.Frame(right)
    right.add(lower, minsize=120)
    hex_title = tk.StringVar(value='Hex')
    tk.Label(lower, textvariable=hex_title, anchor='w').pack(fill='x')
    hex_box = tk.Text(lower, wrap='none', font=('Consolas', 10), bg='#f7f7f7', cursor='arrow')
    hex_scrollbar = ttk.Scrollbar(lower, orient='vertical', command=hex_box.yview)
    hex_box.configure(yscrollcommand=hex_scrollbar.set)
    hex_box.pack(side='left', fill='both', expand=True)
    hex_scrollbar.pack(side='right', fill='y')
    hex_box.tag_configure('hl', background='#ffd75e')
    hex_box.tag_configure('addr', foreground='#888')
    hex_box.configure(state='disabled')

    def open_file(_event=None):
        if state['path']:
            initial_folder = os.path.dirname(state['path'])
        elif os.path.isdir(DEFAULT_DIR):
            initial_folder = DEFAULT_DIR
        else:
            initial_folder = None
        path = filedialog.askopenfilename(title='Open .wdt', filetypes=wdt_file_types, initialdir=initial_folder)
        if path:
            load(path)

    def reload_file():
        if state['path']:
            load(state['path'])

    def set_music(path, quiet=False):
        try:
            if path:
                state['music'] = load_music(path)
            else:
                state['music'] = {}
            state['music_path'] = path
        except Exception as error:
            state['music'] = {}
            state['music_path'] = None
            if not quiet:
                messagebox.showerror('WDT Viewer', f'Could not read music table {path}:\n{error}')

    def pick_music():
        initial_folder = None
        if state['music_path']:
            initial_folder = os.path.dirname(state['music_path'])
        path = filedialog.askopenfilename(title='Open music.csv', initialdir=initial_folder,
                                          filetypes=[('CSV', '*.csv'), ('All files', '*.*')])
        if path:
            set_music(path)
            if state['path']:
                load(state['path'])

    def status_message(wdt):
        if state['music']:
            music_status = f'{len(state["music"])} tracks from {state["music_path"]}'
        else:
            music_status = 'not loaded (Music table...)'
        message = (f'{len(wdt.data):,} bytes   {len(wdt.sections)} sections   {len(wdt.areas)} areas   '
                   f'{len(wdt.entrances)} entrances   {len(wdt.kgrs)} KGRs   music: {music_status}')
        if wdt.warnings:
            message += '   WARNINGS: ' + '; '.join(wdt.warnings[:3])
        return message

    def add_tree_items(parent, nodes):
        for node in nodes:
            item = tree.insert(parent, 'end', text=node.title, values=(f'{node.start:X}..{node.end:X}',))
            state['items'][item] = node
            add_tree_items(item, node.children)

    def load(path):
        try:
            wdt = Wdt(Path(path).read_bytes(), Path(path).name, state['music'])
        except Exception as error:
            messagebox.showerror('WDT Viewer', f'Could not parse {path}:\n{error}')
            return
        state.update(wdt=wdt, path=path, items={})
        path_var.set(path)
        info_var.set(status_message(wdt))
        tree.delete(*tree.get_children())
        add_tree_items('', wdt.nodes)
        top_items = tree.get_children()
        for item in top_items:
            tree.item(item, open=True)
        if top_items:
            if len(top_items) > 1:
                first_section = top_items[1]
            else:
                first_section = top_items[0]
            tree.selection_set(first_section)
            tree.see(first_section)

    def set_columns(columns, widths):
        table.configure(columns=columns)
        for column, width in zip(columns, widths):
            table.heading(column, text=column)
            table.column(column, width=width, stretch=column in stretching_columns, anchor='w')

    def show_image(node):
        if not node.image:
            image_bar.pack_forget()
            return
        width, height, rgba, _ = node.image
        scale = 1
        if width <= 256:
            scale = 2
        state['img'] = tk.PhotoImage(data=base64.b64encode(checker_composite(width, height, rgba, scale)))
        image_label.configure(image=state['img'])
        image_bar.pack(fill='x', before=table_frame)

    def show_summary_rows(node):
        columns, rows = node.summary
        widths = [column_widths.get(column, max(60, len(column) * 9 + 30)) for column in columns]
        set_columns(columns, widths)
        for target, values in rows:
            item = table.insert('', 'end', values=values)
            state['rows'][item] = ('node', target)

    def colour_tag(colour):
        red, green, blue, _ = colour
        tag = f'c{red:02X}{green:02X}{blue:02X}'
        brightness = (red * 299 + green * 587 + blue * 114) / 1000
        foreground = '#fff'
        if brightness > 128:
            foreground = '#000'
        table.tag_configure(tag, background=f'#{red:02X}{green:02X}{blue:02X}', foreground=foreground)
        return tag

    def show_field_rows(node):
        wdt = state['wdt']
        set_columns(field_columns, field_column_widths)
        for index, node_field in enumerate(node.fields):
            relative = ''
            if node_field.relative_offset is not None:
                relative = f'+{node_field.relative_offset:X}'
            tags = ()
            if node_field.color:
                tags = (colour_tag(node_field.color),)
            raw = ''
            if node_field.size:
                raw = raw_hex(wdt.data, node_field)
            item = table.insert('', 'end', tags=tags, values=(
                format_hex(node_field.offset), relative, node_field.size, raw, node_field.type,
                node_field.name, node_field.value, node_field.note))
            state['rows'][item] = ('field', index)
            state['field_rows'][index] = item
        if node.summary:
            child_count = len(node.summary[1])
            table.insert('', 'end', values=('', '', '', '', '',
                                            f'-- {child_count} children: expand in the tree --', '', ''))

    def show_node(node):
        state['node'] = node
        title_var.set(f'{node.title}    file {format_hex(node.start)}..{format_hex(node.end)}  '
                      f'({node.end - node.start} bytes)')
        node_info_var.set(node.info)
        table.delete(*table.get_children())
        state['rows'] = {}
        state['field_rows'] = {}
        show_image(node)
        if node.summary and not node.fields:
            show_summary_rows(node)
        else:
            show_field_rows(node)
        show_hex(node.start, node.end)

    def hex_line(row_start, start, length):
        cells = []
        characters = []
        for position in range(row_start, row_start + 16):
            if start <= position < start + length:
                value = state['wdt'].data[position]
                cells.append(f'{value:02X}')
                if 32 <= value < 127:
                    characters.append(chr(value))
                else:
                    characters.append('.')
            else:
                cells.append('  ')
                characters.append(' ')
        return f'{row_start:08X}  {" ".join(cells[:8])}  {" ".join(cells[8:])}  {"".join(characters)}'

    def row_start_of(offset):
        return offset - offset % 16

    def show_hex(start, end):
        length = min(end - start, hex_limit)
        state['hex_base'] = start
        state['hex_len'] = length
        hex_box.configure(state='normal')
        hex_box.delete('1.0', 'end')
        lines = []
        for row_start in range(row_start_of(start), start + length, 16):
            lines.append(hex_line(row_start, start, length))
        hex_box.insert('1.0', '\n'.join(lines))
        for line_index in range(len(lines)):
            hex_box.tag_add('addr', f'{line_index + 1}.0', f'{line_index + 1}.8')
        hex_box.configure(state='disabled')
        more = ''
        if end - start > hex_limit:
            more = f'  (first {hex_limit:#x} bytes shown)'
        hex_title.set(f'Hex  {format_hex(start)}..{format_hex(end)}{more}')

    def hex_text_range(offset):
        line = (row_start_of(offset) - row_start_of(state['hex_base'])) // 16 + 1
        byte_in_row = offset % 16
        column = hex_bytes_column + byte_in_row * 3
        if byte_in_row >= 8:
            column += 1
        return f'{line}.{column}', f'{line}.{column + 2}'

    def highlight(offset, size):
        hex_box.tag_remove('hl', '1.0', 'end')
        shown_start = state['hex_base']
        shown_end = shown_start + state['hex_len']
        low = max(offset, shown_start)
        high = min(offset + size, shown_end)
        for position in range(low, high):
            range_start, range_end = hex_text_range(position)
            hex_box.tag_add('hl', range_start, range_end)
        if low < high:
            hex_box.see(hex_text_range(low)[0])

    def select_table_row(item):
        table.selection_set(item)
        table.see(item)

    def on_tree_select(_event=None):
        selection = tree.selection()
        if not selection:
            return
        node = state['items'][selection[0]]
        if node is not state['node']:
            show_node(node)
        pending_offset = state['pending']
        state['pending'] = None
        if pending_offset is not None:
            focus_field(node, pending_offset)

    def focus_field(node, offset):
        hits = []
        for index, node_field in enumerate(node.fields):
            size = max(node_field.size, 1)
            if node_field.offset <= offset < node_field.offset + size:
                hits.append((size, index))
        if hits:
            select_table_row(state['field_rows'][min(hits)[1]])
        else:
            highlight(offset, 1)

    def on_table_select(_event=None):
        selection = table.selection()
        if not selection or selection[0] not in state['rows']:
            return
        kind, target = state['rows'][selection[0]]
        if kind == 'field':
            node_field = state['node'].fields[target]
            highlight(node_field.offset, max(node_field.size, 1))
        else:
            highlight(target.start, target.end - target.start)

    def on_table_open(_event=None):
        selection = table.selection()
        if not selection or selection[0] not in state['rows']:
            return
        kind, target = state['rows'][selection[0]]
        if kind == 'node':
            select_node(target)

    def select_node(target, field_offset=None):
        for item, node in state['items'].items():
            if node is target:
                state['pending'] = field_offset
                if tree.selection() == (item,):
                    on_tree_select()
                else:
                    tree.selection_set(item)
                tree.see(item)
                return

    def smallest_node_containing(offset):
        best = None
        for node in walk_nodes(state['wdt'].nodes):
            if not node.fields:
                continue
            if not node.start <= offset < node.end:
                continue
            if best is None or node.end - node.start <= best.end - best.start:
                best = node
        return best

    def goto_offset(_event=None):
        if not state['wdt']:
            return
        try:
            offset = int(goto_var.get().strip(), 16)
        except ValueError:
            messagebox.showerror('WDT Viewer', 'Enter a hex file offset, e.g. 700 or 0x710')
            return
        node = smallest_node_containing(offset)
        if not node:
            messagebox.showinfo('WDT Viewer', f'{format_hex(offset)} is outside every section')
            return
        select_node(node, offset)

    def hex_click_offset(event):
        index = hex_box.index(f'@{event.x},{event.y}')
        line, column = (int(part) for part in index.split('.'))
        if column < hex_bytes_column or column > hex_last_column:
            return None
        byte_column = column - hex_bytes_column
        if byte_column >= hex_second_half_column:
            byte_column -= 1
        return row_start_of(state['hex_base']) + (line - 1) * 16 + byte_column // 3

    def on_hex_click(event):
        if not state['wdt']:
            return
        offset = hex_click_offset(event)
        if offset is None:
            return
        hits = []
        for index, node_field in enumerate(state['node'].fields):
            if node_field.size and node_field.offset <= offset < node_field.offset + node_field.size:
                hits.append((node_field.size, index))
        if hits:
            item = state['field_rows'].get(min(hits)[1])
            if item:
                select_table_row(item)
            return
        for item, (kind, target) in state['rows'].items():
            if kind == 'node' and target.start <= offset < target.end:
                select_table_row(item)
                return

    def save_png():
        node = state['node']
        if not node or not node.image:
            return
        width, height, rgba, name = node.image
        path = filedialog.asksaveasfilename(title='Save image', defaultextension='.png',
                                            initialfile=name, filetypes=[('PNG', '*.png')])
        if path:
            Path(path).write_bytes(png_bytes(width, height, rgba))

    def focus_goto_entry(_event=None):
        goto_entry.focus_set()

    open_button.configure(command=open_file)
    reload_button.configure(command=reload_file)
    music_button.configure(command=pick_music)
    save_png_button.configure(command=save_png)
    goto_entry.bind('<Return>', goto_offset)
    tree.bind('<<TreeviewSelect>>', on_tree_select)
    table.bind('<<TreeviewSelect>>', on_table_select)
    table.bind('<Double-1>', on_table_open)
    table.bind('<Return>', on_table_open)
    hex_box.bind('<Button-1>', on_hex_click)
    root.bind('<Control-o>', open_file)
    root.bind('<Control-g>', focus_goto_entry)

    if music_path:
        set_music(music_path, quiet=True)
    else:
        set_music(find_music_csv(), quiet=True)
    if initial_path:
        load(initial_path)
    root.mainloop()


def load_cli_music(path):
    if not path:
        path = find_music_csv()
    if not path:
        print('(music.csv not found: BGM ids shown without names; use --music)')
        return {}
    return load_music(path)


def main(argv=None):
    if argv is None:
        args = list(sys.argv[1:])
    else:
        args = list(argv)
    music_path = None
    if '--music' in args:
        flag_index = args.index('--music')
        if flag_index + 1 >= len(args):
            print('--music needs a path to music.csv')
            return 2
        music_path = args[flag_index + 1]
        del args[flag_index:flag_index + 2]
    if args and args[0] in ('-h', '--help'):
        print(HELP_TEXT)
        return 0
    if args and args[0] == 'dump':
        if len(args) < 2:
            print('usage: wdt_tool.py dump <file.wdt>')
            return 2
        dump(args[1], load_cli_music(music_path))
        return 0
    if args and args[0] == 'verify':
        if len(args) > 1:
            folder = args[1]
        else:
            folder = DEFAULT_DIR
        return verify(folder, load_cli_music(music_path))
    run_gui(args[0] if args else None, music_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
