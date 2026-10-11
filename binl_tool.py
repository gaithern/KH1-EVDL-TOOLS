#!/usr/bin/env python3
"""
Usage:
  python binl_tool.py                          open the GUI editor
  python binl_tool.py gui [file.binl]          open the GUI editor on a file
  python binl_tool.py dump <file.binl>         print every string (index, bytes, text)
  python binl_tool.py get  <file.binl> <idx>   print one string (idx decimal or 0x..)
  python binl_tool.py set  <file.binl> <idx> "<text>" [-o out.binl] [--term 04|00]
  python binl_tool.py add  <file.binl> "<text>" [-o out.binl] [--term 04|00]   append, prints index
  python binl_tool.py export <file.binl> <out.txt>   one string per line "idx<TAB>term<TAB>text"
  python binl_tool.py import <file.binl> <in.txt> [-o out.binl]
  python binl_tool.py verify <file-or-dir> ...       decode/encode round-trip check
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'binl'))
import binl_commands
from binl_gui import run_gui
from binl_text import END_OF_DIALOGUE_STRING, END_OF_TIMED_STRING


def output_path_option(args, default):
    if '-o' in args:
        return args[args.index('-o') + 1]
    return default


def ending_option(args, default):
    if '--term' not in args:
        return default
    ending = int(args[args.index('--term') + 1], 16)
    if ending != END_OF_TIMED_STRING and ending != END_OF_DIALOGUE_STRING:
        raise ValueError('--term must be 00 or 04')
    return ending


def without_options(args):
    for flag in ('-o', '--term'):
        if flag in args:
            flag_index = args.index(flag)
            args = args[:flag_index] + args[flag_index + 2:]
    return args


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = list(argv)
    if len(args) == 0:
        run_gui()
        return 0
    command = args[0].lower()
    positional = without_options(args)

    if command == 'gui':
        initial_path = None
        if len(args) > 1:
            initial_path = args[1]
        run_gui(initial_path)
        return 0
    if command == 'dump' and len(args) == 2:
        binl_commands.dump(args[1])
        return 0
    if command == 'get' and len(args) == 3:
        binl_commands.get(args[1], binl_commands.parse_index(args[2]))
        return 0
    if command == 'set' and len(positional) == 4:
        path = positional[1]
        index = binl_commands.parse_index(positional[2])
        text = positional[3]
        binl_commands.set_string(path, index, text, output_path_option(args, path), ending_option(args, None))
        return 0
    if command == 'add' and len(positional) == 3:
        path = positional[1]
        text = positional[2]
        ending = ending_option(args, END_OF_DIALOGUE_STRING)
        binl_commands.add_string(path, text, output_path_option(args, path), ending)
        return 0
    if command == 'export' and len(args) == 3:
        binl_commands.export_strings(args[1], args[2])
        return 0
    if command == 'import' and len(positional) == 3:
        path = positional[1]
        binl_commands.import_strings(path, positional[2], output_path_option(args, path))
        return 0
    if command == 'verify' and len(args) >= 2:
        return binl_commands.verify(args[1:])
    print(__doc__)
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print('Error: %s' % error, file=sys.stderr)
        sys.exit(1)
