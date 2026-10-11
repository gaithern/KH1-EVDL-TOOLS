import os
from pathlib import Path

from binl_file import load_binl, parse_binl
from binl_text import END_OF_DIALOGUE_STRING, END_OF_TIMED_STRING, decode_text, encode_text, is_hex_digits


def parse_index(text):
    if text.lower().startswith('0x'):
        return int(text, 16)
    return int(text, 10)


def check_index_in_range(binl, index):
    if index < 0 or index >= len(binl.strings):
        raise SystemExit('index %#x out of range (file has %d strings)' % (index, len(binl.strings)))


def dump(path):
    binl = load_binl(path)
    print('%s  lang=%s  strings=%d' % (path, binl.language(), len(binl.strings)))
    for index in range(len(binl.strings)):
        string = binl.strings[index]
        ending = binl.endings[index]
        print('%#05x %3dB %02X  %s' % (index, len(string), ending, decode_text(string)))


def get(path, index):
    binl = load_binl(path)
    string = binl.strings[index]
    print(decode_text(string))
    print('; %d bytes, terminator %#04x: %s' % (len(string), binl.endings[index], string.hex(' ')))


def set_string(path, index, text, output_path, ending=None):
    binl = load_binl(path)
    check_index_in_range(binl, index)
    binl.strings[index] = encode_text(text)
    if ending is not None:
        binl.endings[index] = ending
    binl.save(output_path)
    print('wrote %s  [%#x] = %d bytes, terminator %#04x'
          % (output_path, index, len(binl.strings[index]), binl.endings[index]))


def add_string(path, text, output_path, ending=END_OF_DIALOGUE_STRING):
    binl = load_binl(path)
    index = binl.append(encode_text(text), ending)
    binl.save(output_path)
    print('wrote %s  new index %#x (%d), terminator %#04x' % (output_path, index, index, ending))


def export_strings(path, text_path):
    binl = load_binl(path)
    with open(text_path, 'w', encoding='utf-8') as file:
        file.write('# %s lang=%s\n' % (os.path.basename(path), binl.language()))
        for index in range(len(binl.strings)):
            text = decode_text(binl.strings[index])
            file.write('%#x\t%02X\t%s\n' % (index, binl.endings[index], text))
    print('exported %d strings to %s' % (len(binl.strings), text_path))


def split_import_line(line):
    parts = line.split('\t', 2)
    if len(parts) == 3 and len(parts[1]) == 2 and is_hex_digits(parts[1]):
        return parts[0], int(parts[1], 16), parts[2]
    index_text = parts[0]
    text = line.split('\t', 1)[1]
    return index_text, None, text


def import_line(binl, line, location):
    if '\t' not in line:
        raise SystemExit('%s: expected "idx<TAB>term<TAB>text"' % location)
    index_text, ending, text = split_import_line(line)
    index = parse_index(index_text)
    encoded = encode_text(text)
    if index == len(binl.strings):
        if ending is None:
            ending = END_OF_DIALOGUE_STRING
        binl.append(encoded, ending)
    elif 0 <= index < len(binl.strings):
        binl.strings[index] = encoded
        if ending is not None:
            binl.endings[index] = ending
    else:
        raise SystemExit('%s: index %#x out of range' % (location, index))


def import_strings(path, text_path, output_path):
    binl = load_binl(path)
    with open(text_path, 'r', encoding='utf-8') as file:
        line_number = 0
        for line in file:
            line_number = line_number + 1
            line = line.rstrip('\r\n')
            if line == '' or line.startswith('#'):
                continue
            import_line(binl, line, '%s:%d' % (text_path, line_number))
    binl.save(output_path)
    print('wrote %s (%d strings)' % (output_path, len(binl.strings)))


def string_round_trip_problem(name, index, string):
    try:
        encoded_again = encode_text(decode_text(string))
    except ValueError as error:
        return '%s[%#x]: %s' % (name, index, error)
    if encoded_again != string:
        return ('%s[%#x]: text round-trip mismatch\n  orig %s\n  back %s'
                % (name, index, string.hex(), encoded_again.hex()))
    return None


def rebuild_problem(name, binl, data):
    rebuilt = binl.to_bytes()
    if rebuilt == data:
        return None
    body_length = binl.body_length()
    if rebuilt[:body_length] != data[:body_length]:
        return '%s: rebuilt body differs from original' % name
    if len(rebuilt) != len(data):
        return '%s: length %d vs original %d (padding differs)' % (name, len(rebuilt), len(data))
    return None


def problems_in_file(path):
    name = os.path.basename(path)
    with open(path, 'rb') as file:
        data = file.read()
    binl = parse_binl(data, path)
    problems = []
    for index in range(len(binl.strings)):
        problem = string_round_trip_problem(name, index, binl.strings[index])
        if problem:
            problems.append(problem)
    problem = rebuild_problem(name, binl, data)
    if problem:
        problems.append(problem)
    return problems


def binl_files_in(targets):
    files = []
    for target in targets:
        target_path = Path(target)
        if target_path.is_dir():
            files = files + sorted(target_path.rglob('*.binl'))
        else:
            files.append(target_path)
    return files


def verify(targets):
    files = binl_files_in(targets)
    files_with_problems = 0
    for file in files:
        try:
            problems = problems_in_file(str(file))
        except Exception as error:
            problems = ['%s: %s' % (file.name, error)]
        if problems:
            files_with_problems = files_with_problems + 1
            for problem in problems:
                print(problem)
    print('%d files checked, %d with problems' % (len(files), files_with_problems))
    if files_with_problems:
        return 1
    return 0
