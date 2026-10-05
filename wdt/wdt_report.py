"""Text reports for .wdt files: the dump and verify commands."""
from pathlib import Path

from wdt_format import DEFAULT_DIR, Wdt, format_hex, raw_hex


def print_node_tree(wdt, nodes, depth):
    indent = '  ' * depth
    for node in nodes:
        print(f'{indent}== {node.title}  [{format_hex(node.start)}..{format_hex(node.end)})  {node.info}')
        for node_field in node.fields:
            if node_field.relative_offset is not None:
                relative = f'+{node_field.relative_offset:02X}'
            else:
                relative = '   '
            print(f'{indent}   {node_field.offset:06X} {relative:>5}  {raw_hex(wdt.data, node_field):<24} '
                  f'{node_field.type:<7} {node_field.name:<24} {node_field.value}  {node_field.note}')
        if node.summary and not node.fields:
            columns, rows = node.summary
            print(f'{indent}   ' + ' | '.join(columns))
            for _, values in rows:
                print(f'{indent}   ' + ' | '.join(str(value) for value in values))
        print_node_tree(wdt, node.children, depth + 1)


def dump(path, music=None):
    wdt = Wdt(Path(path).read_bytes(), Path(path).name, music)
    print_node_tree(wdt, wdt.nodes, 0)
    for warning in wdt.warnings:
        print('WARNING:', warning)


def layout_problems(wdt):
    problems = list(wdt.warnings)
    expected_offset = wdt.sections[0][0]
    for index, (offset, size) in enumerate(wdt.sections):
        if offset != expected_offset:
            problems.append(f'section {index} starts at {format_hex(offset)}, '
                            f'expected {format_hex(expected_offset)}')
        expected_offset = offset + size
    if expected_offset != len(wdt.data):
        problems.append(f'sections end at {format_hex(expected_offset)}, file is {format_hex(len(wdt.data))}')
    for entrance in wdt.entrances:
        if entrance['area'] >= len(wdt.areas):
            problems.append(f'entrance {entrance["index"]} -> area {entrance["area"]} '
                            f'(only {len(wdt.areas)} areas)')
        if any(entrance['pad']):
            problems.append(f'entrance {entrance["index"]} has non-zero padding {entrance["pad"]}')
    for kgr in wdt.kgrs:
        for _, entrance, _, world in kgr['targets']:
            if world is None and entrance >= len(wdt.entrances):
                problems.append(f'KGR {kgr["index"]} -> entrance {entrance} (only {len(wdt.entrances)})')
    return problems


def verify(folder=DEFAULT_DIR, music=None):
    files = sorted(Path(folder).glob('*.wdt'))
    if not files:
        print(f'no .wdt files in {folder}')
        return 1
    bad_file_count = 0
    for path in files:
        wdt = Wdt(path.read_bytes(), path.name, music)
        problems = layout_problems(wdt)
        door_count = sum(len(kgr['targets']) for kgr in wdt.kgrs)
        image_count = sum(1 for node in wdt.nodes if node.image)
        if problems:
            status = 'BAD'
            bad_file_count += 1
        else:
            status = 'OK '
        print(f'{status} {path.name}: {len(wdt.areas)} areas, {len(wdt.entrances)} entrances, '
              f'{len(wdt.kgrs)} KGRs, {door_count} Change_area pushes, '
              f'images: {image_count}')
        for problem in problems:
            print('     ', problem)
    if bad_file_count:
        return 1
    return 0
