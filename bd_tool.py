#!/usr/bin/env python3
"""Command line and GUI for converting KH1 enemy AI (.bd blocks inside .mdls) to and from ASM or BDS text."""
import contextlib
import io
import os
import sys
from pathlib import Path

HERE = Path(__file__).absolute().parent
BD_DIR = HERE / 'bd'
ASM_DIR = BD_DIR / 'asm'
BDS_DIR = BD_DIR / 'bds'
WORKING = HERE / 'working'

sys.path.insert(0, str(ASM_DIR))
sys.path.insert(0, str(BDS_DIR))
sys.path.insert(0, str(BD_DIR))
import kh1_bd_disasm
import kh1_bd_asm
import lang
import build
import kh1_motion_ids

GAME_DATA = Path(os.environ.get('KH1_GAME_DATA', 'C:/OpenKH/OpenKHEGS/data/kh1'))
ASM_EXTENSION = '.bdasm'
BDS_EXTENSION = '.bds'
ASM_FILETYPES = [('BD ASM files', '*.bdasm'), ('All files', '*.*')]
BDS_FILETYPES = [('BDS files', '*.bds'), ('All files', '*.*')]
MDLS_FILETYPES = [('Enemy models', '*.mdls'), ('All files', '*.*')]
KNOWN_ERRORS = (kh1_bd_asm.AsmError, lang.PartError, ValueError, SyntaxError, OSError)


def die(message):
    print(f'Error: {message}', file=sys.stderr)
    sys.exit(1)


def strip_suffix_ignoring_case(name, suffix):
    if name.lower().endswith(suffix.lower()):
        return name[:len(name) - len(suffix)]
    return name


def output_folder(output_dir):
    if output_dir:
        return Path(output_dir)
    WORKING.mkdir(exist_ok=True)
    return WORKING


def find_original_mdls(text_path, extension):
    text_path = Path(text_path)
    name = strip_suffix_ignoring_case(text_path.name, extension)
    if not name.lower().endswith('.mdls'):
        name = name + '.mdls'
    for candidate in (text_path.with_name(name), GAME_DATA / name):
        if candidate.is_file():
            return candidate
    if GAME_DATA.is_dir():
        return next(GAME_DATA.rglob(name), None)
    return None


def choose_original(text_path, extension, original_mdls):
    if original_mdls:
        return Path(original_mdls)
    original = find_original_mdls(text_path, extension)
    if not original:
        raise FileNotFoundError(f'original .mdls for {Path(text_path).name} not found; pass it explicitly')
    return original


def rebuilt_destination(text_path, extension, output_dir):
    text_path = Path(text_path)
    name = strip_suffix_ignoring_case(text_path.name, extension)
    if not name.lower().endswith('.mdls'):
        name = name + '.mdls'
    if output_dir:
        return Path(output_dir) / name
    return text_path.with_name(name)


def disassemble_to_asm(mdls_path, output_dir=None, block_selector='all'):
    data = Path(mdls_path).read_bytes()
    listings = []
    for index, (block_off, name, size) in enumerate(kh1_bd_disasm.find_blocks(data)):
        if block_selector == 'all' or block_selector == str(index) or block_selector in name:
            listings.append(kh1_bd_disasm.disasm(data, block_off, name, size))
    if not listings:
        raise ValueError(f'{Path(mdls_path).name}: no .bd block matches {block_selector!r}')
    destination = output_folder(output_dir) / (Path(mdls_path).name + ASM_EXTENSION)
    destination.write_text('\n\n'.join(listings) + '\n', encoding='utf-8')
    print(f'-> {destination}')


def assemble_from_asm(asm_path, original_mdls=None, output_dir=None):
    original = choose_original(asm_path, ASM_EXTENSION, original_mdls)
    destination = rebuilt_destination(asm_path, ASM_EXTENSION, output_dir)
    kh1_bd_asm.patch(str(original), str(asm_path), str(destination))
    print(f'-> {destination}  (patched into {original})')


def decompile_to_bds(mdls_path, output_dir=None, block_name=None):
    text = lang.decompile_file(mdls_path, block_name)
    if not text and block_name:
        raise ValueError(f'{Path(mdls_path).name}: no .bd block named {block_name!r}')
    if not text:
        raise ValueError(f'{Path(mdls_path).name}: no .bd blocks found')
    destination = output_folder(output_dir) / (Path(mdls_path).name + BDS_EXTENSION)
    destination.write_text(text, encoding='utf-8')
    print(f'-> {destination}')


def build_from_bds(bds_path, original_mdls=None, output_dir=None):
    original = choose_original(bds_path, BDS_EXTENSION, original_mdls)
    destination = rebuilt_destination(bds_path, BDS_EXTENSION, output_dir)
    build.build_file(bds_path, original, destination)
    print(f'-> {destination}  (built into {original})')


def describe_failure(exception):
    if isinstance(exception, KNOWN_ERRORS):
        return str(exception)
    return f'{type(exception).__name__}: {exception}'


def run_and_report(name, report, action, *arguments):
    captured = io.StringIO()
    error = None
    try:
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            action(*arguments)
    except Exception as exception:
        error = describe_failure(exception)
    if error:
        report(f'ERR {name}: {error}')
    else:
        report(f'OK  {name}')
    for line in captured.getvalue().strip().splitlines():
        report(f'      {line}')


def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox

    padding = dict(padx=6, pady=3)
    root = tk.Tk()
    root.title('BD Workshop')
    window = tk.Frame(root)
    window.pack(fill='both', expand=True, padx=4, pady=4)

    def add_heading(text, row):
        heading = tk.Label(window, text=text, font=('TkDefaultFont', 9, 'bold'), anchor='w')
        heading.grid(row=row, column=0, columnspan=3, sticky='w', padx=6, pady=(8, 0))
        return heading

    def add_file_list(row, get_filetypes, initial_dir):
        frame = tk.Frame(window)
        frame.grid(row=row, column=0, columnspan=3, sticky='ew', padx=6)
        file_list = tk.Listbox(frame, width=70, height=5, selectmode=tk.EXTENDED)
        file_list.pack(side='left', fill='both', expand=True)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=file_list.yview)
        scrollbar.pack(side='right', fill='y')
        file_list.configure(yscrollcommand=scrollbar.set)

        def add_files():
            paths = filedialog.askopenfilenames(title='Add files', filetypes=get_filetypes(), initialdir=initial_dir)
            existing = set(file_list.get(0, tk.END))
            for path in paths:
                if path not in existing:
                    file_list.insert(tk.END, path)

        def remove_selected():
            for index in reversed(file_list.curselection()):
                file_list.delete(index)

        buttons = tk.Frame(window)
        buttons.grid(row=row + 1, column=0, columnspan=3, sticky='w', padx=6, pady=2)
        tk.Button(buttons, text='Add…', command=add_files).pack(side='left', padx=2)
        tk.Button(buttons, text='Remove', command=remove_selected).pack(side='left', padx=2)
        return file_list

    def add_results_box(row):
        add_heading('Results', row)
        frame = tk.Frame(window)
        frame.grid(row=row + 1, column=0, columnspan=3, sticky='ew', padx=6, pady=(0, 4))
        box = tk.Text(frame, width=80, height=10, font=('Courier', 9), state='disabled')
        box.pack(side='left', fill='both', expand=True)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=box.yview)
        scrollbar.pack(side='right', fill='y')
        box.configure(yscrollcommand=scrollbar.set)

        def append(text):
            box.configure(state='normal')
            box.insert(tk.END, text + '\n')
            box.see(tk.END)
            box.configure(state='disabled')
            root.update_idletasks()

        def clear():
            box.configure(state='normal')
            box.delete('1.0', tk.END)
            box.configure(state='disabled')

        return append, clear

    mode = tk.StringVar(value='bds')
    mode_row = tk.Frame(window)
    mode_row.grid(row=0, column=0, columnspan=3, sticky='w', padx=6, pady=(6, 0))
    tk.Label(mode_row, text='Format:').pack(side='left', padx=(0, 4))

    def is_bds_mode():
        return mode.get() == 'bds'

    def mdls_filetypes():
        return MDLS_FILETYPES

    def text_filetypes():
        if is_bds_mode():
            return BDS_FILETYPES
        return ASM_FILETYPES

    mdls_heading = add_heading('', 1)
    mdls_list = add_file_list(2, mdls_filetypes, str(GAME_DATA))
    text_heading = add_heading('', 4)
    text_list = add_file_list(5, text_filetypes, str(WORKING))

    tk.Label(window, text='Original .mdls\n(override, optional):', anchor='e', justify='right') \
        .grid(row=7, column=0, sticky='e', **padding)
    original_mdls = tk.StringVar()
    tk.Entry(window, textvariable=original_mdls, width=50).grid(row=7, column=1, sticky='ew', **padding)

    def browse_original_mdls():
        chosen = filedialog.askopenfilename(title='Select original .mdls to build into',
                                            filetypes=MDLS_FILETYPES, initialdir=str(GAME_DATA))
        if chosen:
            original_mdls.set(chosen)

    tk.Button(window, text='Browse…', command=browse_original_mdls).grid(row=7, column=2, **padding)

    add_heading('Output directory  (optional)', 8)
    output_directory = tk.StringVar()
    tk.Entry(window, textvariable=output_directory, width=50).grid(row=9, column=0, columnspan=2, sticky='ew', **padding)

    def browse_output_directory():
        chosen = filedialog.askdirectory(title='Select output directory', initialdir=str(HERE))
        if chosen:
            output_directory.set(chosen)

    tk.Button(window, text='Browse…', command=browse_output_directory).grid(row=9, column=2, **padding)

    report, clear_results = add_results_box(10)

    def chosen_output_directory():
        text = output_directory.get().strip()
        if not text:
            return None
        directory = Path(text)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def convert_selected():
        files = list(mdls_list.get(0, tk.END))
        if not files:
            messagebox.showerror('Bad input', 'Add at least one .mdls file.')
            return
        clear_results()
        output_dir = chosen_output_directory()
        for path in files:
            if is_bds_mode():
                run_and_report(Path(path).name, report, decompile_to_bds, path, output_dir)
            else:
                run_and_report(Path(path).name, report, disassemble_to_asm, path, output_dir)

    def rebuild_selected():
        files = list(text_list.get(0, tk.END))
        if not files:
            if is_bds_mode():
                messagebox.showerror('Bad input', 'Add at least one .bds file to build.')
            else:
                messagebox.showerror('Bad input', 'Add at least one .bdasm file to assemble.')
            return
        clear_results()
        output_dir = chosen_output_directory()
        original = original_mdls.get().strip() or None
        for path in files:
            if is_bds_mode():
                run_and_report(Path(path).name, report, build_from_bds, path, original, output_dir)
            else:
                run_and_report(Path(path).name, report, assemble_from_asm, path, original, output_dir)

    buttons = tk.Frame(window)
    buttons.grid(row=12, column=0, columnspan=3, pady=8)
    convert_button = tk.Button(buttons, command=convert_selected, width=16)
    convert_button.pack(side='left', padx=6)
    rebuild_button = tk.Button(buttons, command=rebuild_selected, width=16)
    rebuild_button.pack(side='left', padx=6)

    text_files_by_mode = {'asm': [], 'bds': []}
    current_mode = 'bds'

    def switch_mode():
        nonlocal current_mode
        text_files_by_mode[current_mode] = list(text_list.get(0, tk.END))
        current_mode = mode.get()
        text_list.delete(0, tk.END)
        for path in text_files_by_mode[current_mode]:
            text_list.insert(tk.END, path)
        if current_mode == 'bds':
            mdls_heading.config(text='Decompile  (.mdls  →  .bds)')
            text_heading.config(text='Build  (.bds  →  .mdls)')
            convert_button.config(text='Decompile')
            rebuild_button.config(text='Build')
        else:
            mdls_heading.config(text='Disassemble  (.mdls  →  .bdasm)')
            text_heading.config(text='Assemble  (.bdasm  →  .mdls)')
            convert_button.config(text='Disassemble')
            rebuild_button.config(text='Assemble')

    for value, text in (('bds', 'BDS'), ('asm', 'ASM')):
        tk.Radiobutton(mode_row, text=text, value=value, variable=mode, indicatoron=0,
                       width=6, command=switch_mode).pack(side='left')

    switch_mode()
    root.mainloop()


HELP = """Usage:
  python bd_tool.py                                        open the GUI
  python bd_tool.py list <file.mdls>                       list the .bd blocks in a model
  python bd_tool.py decompile <file.mdls> ... [--block NAME] [-o dir]
                                                           write working/<file>.mdls.bds
  python bd_tool.py build <file.bds> [original.mdls] [-o dir]
                                                           build into a copy of the original .mdls
  python bd_tool.py disasm <file.mdls> ... [--block NAME|INDEX] [-o dir]
                                                           write working/<file>.mdls.bdasm
  python bd_tool.py asm <file.bdasm> [original.mdls] [-o dir]
                                                           patch into a copy of the original .mdls
  python bd_tool.py motions <file.mdls> ... [--json out.json]
                                                           which animation each motion call plays
  python bd_tool.py verify <file.mdls> [block|all]         check the assembler round-trips exactly

The original .mdls is looked for next to the text file, then in KH1_GAME_DATA
(default C:/OpenKH/OpenKHEGS/data/kh1). Rebuilt .mdls files are written next to the text file
unless -o is given.
"""


def take_option(args, flag):
    if flag not in args:
        return args, None
    flag_index = args.index(flag)
    if flag_index + 1 >= len(args):
        die(f'{flag} needs a value')
    value = args[flag_index + 1]
    remaining = args[:flag_index] + args[flag_index + 2:]
    return remaining, value


def list_command(args):
    if len(args) != 1:
        die('usage: bd_tool.py list <file.mdls>')
    data = Path(args[0]).read_bytes()
    blocks = kh1_bd_disasm.find_blocks(data)
    if not blocks:
        print('No .bd blocks found.')
        return
    print(f"{'idx':>3}  {'name':<18} {'block':>12} {'size':>7}")
    for index, (block_off, name, size) in enumerate(blocks):
        print(f'{index:>3}  {name:<18} 0x{block_off:08X} 0x{size:04X}')


def decompile_command(args):
    args, block_name = take_option(args, '--block')
    args, output_dir = take_option(args, '-o')
    if not args:
        die('usage: bd_tool.py decompile <file.mdls> ... [--block NAME] [-o dir]')
    for mdls_path in args:
        decompile_to_bds(mdls_path, output_dir, block_name)


def disasm_command(args):
    args, block_selector = take_option(args, '--block')
    args, output_dir = take_option(args, '-o')
    if not args:
        die('usage: bd_tool.py disasm <file.mdls> ... [--block NAME|INDEX] [-o dir]')
    if block_selector is None:
        block_selector = 'all'
    for mdls_path in args:
        disassemble_to_asm(mdls_path, output_dir, block_selector)


def build_command(args):
    args, output_dir = take_option(args, '-o')
    if len(args) < 1 or len(args) > 2:
        die('usage: bd_tool.py build <file.bds> [original.mdls] [-o dir]')
    original = None
    if len(args) == 2:
        original = args[1]
    build_from_bds(args[0], original, output_dir)


def asm_command(args):
    args, output_dir = take_option(args, '-o')
    if len(args) < 1 or len(args) > 2:
        die('usage: bd_tool.py asm <file.bdasm> [original.mdls] [-o dir]')
    original = None
    if len(args) == 2:
        original = args[1]
    assemble_from_asm(args[0], original, output_dir)


def motions_command(args):
    sys.argv = ['kh1_motion_ids.py'] + args
    kh1_motion_ids.main()


def verify_command(args):
    if len(args) < 1 or len(args) > 2:
        die('usage: bd_tool.py verify <file.mdls> [block|all]')
    block_selector = 'all'
    if len(args) == 2:
        block_selector = args[1]
    if kh1_bd_asm.roundtrip(args[0], block_selector):
        return 0
    return 1


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    args = sys.argv[1:]
    if not args:
        run_gui()
        return 0
    command = args[0]
    rest = args[1:]
    try:
        if command in ('--help', '-h'):
            print(HELP)
        elif command == 'list':
            list_command(rest)
        elif command == 'decompile':
            decompile_command(rest)
        elif command == 'build':
            build_command(rest)
        elif command == 'disasm':
            disasm_command(rest)
        elif command == 'asm':
            asm_command(rest)
        elif command == 'motions':
            motions_command(rest)
        elif command == 'verify':
            return verify_command(rest)
        else:
            die(f'Unknown command: {command}. Run with --help for usage.')
    except KNOWN_ERRORS as error:
        die(str(error))
    return 0


if __name__ == '__main__':
    sys.exit(main())
