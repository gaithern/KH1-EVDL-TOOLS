#!/usr/bin/env python3
"""Command line and GUI for converting KH1 event scripts to and from ASM or EVS text."""
import contextlib
import io
import os
import sys
from pathlib import Path

HERE = Path(__file__).absolute().parent
ASM_DIR = HERE / 'ev' / 'asm'
EVS_DIR = HERE / 'ev' / 'evs'

sys.path.insert(0, str(ASM_DIR))
from evdl_asm import WORKING, EvdlAsmError, assemble_file, disassemble_file, strip_suffix_ignoring_case

GAME_DATA_DIR = 'C:/OpenKH/OpenKHEGS/data/kh1'
ASM_FILETYPES = [('EVDL ASM files', '*.evdl.asm *.asm'), ('All files', '*.*')]
EVS_FILETYPES = [('EVS files', '*.evs'), ('All files', '*.*')]
BINARY_FILETYPES = [('All files', '*.*'), ('EVDL/ARD/EV files', '*.evdl *.ard *.ev')]


def die(message):
    print(f'Error: {message}', file=sys.stderr)
    sys.exit(1)


def import_evs_modules():
    if str(EVS_DIR) not in sys.path:
        sys.path.insert(0, str(EVS_DIR))
    import lang, build
    return lang, build


def find_original_for_evs(evs_path):
    from corpus import GAME_DATA
    name = strip_suffix_ignoring_case(evs_path.name, '.evs')
    for candidate in (evs_path.with_name(name), GAME_DATA / name):
        if candidate.is_file():
            return candidate
    if GAME_DATA.is_dir():
        return next(GAME_DATA.rglob(name), None)
    return None


def decompile_to_evs(lang, path, output_dir):
    destination = (output_dir or WORKING) / (Path(path).name + '.evs')
    destination.write_text(lang.decompile_file(path), encoding='utf-8')
    print(f'-> {destination}')


def build_from_evs(build, path, original_binary, output_dir):
    source = Path(path)
    original = Path(original_binary) if original_binary else find_original_for_evs(source)
    if not original:
        raise FileNotFoundError('original binary not found; set the override')
    destination = (output_dir or source.parent) / strip_suffix_ignoring_case(source.name, '.evs')
    message_files = build.build_file(source, original, destination)
    print(f'-> {destination}  (repacked into {original})')
    for message_file in message_files:
        print(f'-> {message_file}  (new messages)')


def describe_failure(exception):
    if isinstance(exception, EvdlAsmError):
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
    root.title('EVDL Workshop')
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

    mode = tk.StringVar(value='asm')
    mode_row = tk.Frame(window)
    mode_row.grid(row=0, column=0, columnspan=3, sticky='w', padx=6, pady=(6, 0))
    tk.Label(mode_row, text='Format:').pack(side='left', padx=(0, 4))

    def is_evs_mode():
        return mode.get() == 'evs'

    def binary_filetypes():
        return BINARY_FILETYPES

    def text_filetypes():
        if is_evs_mode():
            return EVS_FILETYPES
        return ASM_FILETYPES

    binary_heading = add_heading('', 1)
    binary_list = add_file_list(2, binary_filetypes, GAME_DATA_DIR)
    text_heading = add_heading('', 4)
    text_list = add_file_list(5, text_filetypes, str(WORKING))

    tk.Label(window, text='Original binary\n(override, optional):', anchor='e', justify='right') \
        .grid(row=7, column=0, sticky='e', **padding)
    original_binary = tk.StringVar()
    tk.Entry(window, textvariable=original_binary, width=50).grid(row=7, column=1, sticky='ew', **padding)

    def browse_original_binary():
        chosen = filedialog.askopenfilename(title='Select original binary to repack into',
                                            filetypes=BINARY_FILETYPES, initialdir=GAME_DATA_DIR)
        if chosen:
            original_binary.set(chosen)

    tk.Button(window, text='Browse…', command=browse_original_binary).grid(row=7, column=2, **padding)

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

    def disassemble_selected():
        files = list(binary_list.get(0, tk.END))
        if not files:
            messagebox.showerror('Bad input', 'Add at least one file to disassemble.')
            return
        clear_results()
        output_dir = chosen_output_directory()
        if is_evs_mode():
            lang, _ = import_evs_modules()
            for path in files:
                run_and_report(Path(path).name, report, decompile_to_evs, lang, path, output_dir)
        else:
            for path in files:
                output_path = str(output_dir / (Path(path).name + '.asm')) if output_dir else None
                run_and_report(Path(path).name, report, disassemble_file, path, output_path)

    def assemble_selected():
        files = list(text_list.get(0, tk.END))
        extension = '.evs' if is_evs_mode() else '.asm'
        if not files:
            messagebox.showerror('Bad input', f'Add at least one {extension} file to assemble.')
            return
        clear_results()
        output_dir = chosen_output_directory()
        original = original_binary.get().strip() or None
        if is_evs_mode():
            _, build = import_evs_modules()
            for path in files:
                run_and_report(Path(path).name, report, build_from_evs, build, path, original, output_dir)
        else:
            for path in files:
                output_path = None
                if output_dir:
                    output_path = str(output_dir / strip_suffix_ignoring_case(Path(path).name, '.asm'))
                run_and_report(Path(path).name, report, assemble_file, path, output_path, original)

    buttons = tk.Frame(window)
    buttons.grid(row=12, column=0, columnspan=3, pady=8)
    disassemble_button = tk.Button(buttons, command=disassemble_selected, width=16)
    disassemble_button.pack(side='left', padx=6)
    assemble_button = tk.Button(buttons, command=assemble_selected, width=16)
    assemble_button.pack(side='left', padx=6)

    text_files_by_mode = {'asm': [], 'evs': []}
    current_mode = 'asm'

    def switch_mode():
        nonlocal current_mode
        text_files_by_mode[current_mode] = list(text_list.get(0, tk.END))
        current_mode = mode.get()
        text_list.delete(0, tk.END)
        for path in text_files_by_mode[current_mode]:
            text_list.insert(tk.END, path)
        if current_mode == 'evs':
            binary_heading.config(text='Decompile  (.evdl / .ard / .ev  →  .evs)')
            text_heading.config(text='Build  (.evs  →  .evdl / .ard / .ev)')
            disassemble_button.config(text='Decompile')
            assemble_button.config(text='Build')
        else:
            binary_heading.config(text='Disassemble  (.evdl / .ard  →  .asm)')
            text_heading.config(text='Assemble  (.asm  →  .evdl / .ard)')
            disassemble_button.config(text='Disassemble')
            assemble_button.config(text='Assemble')

    for value, text in (('asm', 'ASM'), ('evs', 'EVS')):
        tk.Radiobutton(mode_row, text=text, value=value, variable=mode, indicatoron=0,
                       width=6, command=switch_mode).pack(side='left')

    switch_mode()
    root.mainloop()


HELP = """Usage:
  python evdl_tool.py                                open the GUI
  python evdl_tool.py disasm <file> [<file> ...]     write working/<file>.asm for each
  python evdl_tool.py disasm <file> <output.asm>     write output.asm
  python evdl_tool.py asm <input.asm> [output]       assemble; the original binary must sit next to the .asm
"""


def pick_files(title, filetypes, initial_dir=None, multiple=False):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        if multiple:
            paths = filedialog.askopenfilenames(title=title, filetypes=filetypes, initialdir=initial_dir or os.getcwd())
            root.destroy()
            return list(paths) or None
        path = filedialog.askopenfilename(title=title, filetypes=filetypes, initialdir=initial_dir or os.getcwd())
        root.destroy()
        return path or None
    except Exception as error:
        die(f'Tkinter file dialog failed: {error}')


def disasm_command(args):
    if not args:
        input_paths = pick_files('Select file(s) to disassemble', BINARY_FILETYPES, multiple=True)
        if not input_paths:
            die('No file selected.')
        for input_path in input_paths:
            disassemble_file(input_path)
    elif len(args) == 2 and not os.path.isdir(args[1]) and args[1].endswith('.asm'):
        disassemble_file(args[0], args[1])
    else:
        for input_path in args:
            disassemble_file(input_path)


def asm_command(args):
    if args:
        assemble_file(args[0], args[1] if len(args) > 1 else None)
        return
    input_path = pick_files('Select ASM file to assemble', [('ASM files', '*.asm'), ('All files', '*.*')])
    if not input_path:
        die('No ASM file selected.')
    original_path = pick_files('Select original binary to repack into', BINARY_FILETYPES,
                               initial_dir=os.path.dirname(os.path.abspath(input_path)))
    if not original_path:
        die('No original binary selected.')
    assemble_file(input_path, None, original_path)


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    args = sys.argv[1:]
    try:
        if not args:
            run_gui()
        elif args[0] in ('--help', '-h'):
            print(HELP)
        elif args[0] == 'disasm':
            disasm_command(args[1:])
        elif args[0] == 'asm':
            asm_command(args[1:])
        else:
            die(f'Unknown command: {args[0]}. Run with --help for usage.')
    except EvdlAsmError as error:
        die(str(error))


if __name__ == '__main__':
    main()
