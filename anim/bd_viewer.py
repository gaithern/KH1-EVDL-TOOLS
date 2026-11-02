import base64
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BD_FOLDER = os.path.join(HERE, '..', 'bd')
sys.path.insert(0, BD_FOLDER)
sys.path.insert(0, os.path.join(BD_FOLDER, 'asm'))
sys.path.insert(0, os.path.join(BD_FOLDER, 'bds'))

import lang
import kh1_mesh
import kh1_motion_dict
import kh1_motion_ids
import kh1_mset
import kh1_pose

TEMPLATE_PATH = os.path.join(HERE, 'bd_viewer_template.html')
DATA_PLACEHOLDER = '__VIEWER_DATA__'
DEFAULT_FRAME_STEP = 2
MOTION_ID_MASK = 0xFFFF
VERB_BY_SLOT_LETTER = {'c': 'BlendMotion', 'd': 'SetMotion', 'e': 'QueueMotion'}
USAGE = 'usage: bd_viewer.py <enemy.mdls> [out.html] [--frame-step N]'


def matrix_rows(matrix):
    values = []
    for row in range(4):
        for column in range(3):
            values.append(matrix[row * 4 + column])
    return values


def bake_motion(model, motion, frame_step):
    floats = []
    frame_count = 0
    time = 0
    while time < max(motion['frames'], 1):
        posed = kh1_pose.pose_from_data(model, motion, float(time))
        for matrix in posed['world_matrices']:
            floats.extend(matrix_rows(matrix))
        frame_count = frame_count + 1
        time = time + frame_step
    packed = struct.pack(f'<{len(floats)}f', *floats)
    return frame_count, base64.b64encode(packed).decode('ascii'), posed['skipped_bones']


def motion_ids_by_slot(motion_dict):
    result = {}
    for motion_id, slot in motion_dict.items():
        result.setdefault(slot, []).append(motion_id)
    return result


def read_code(mdls_path, motion_dict):
    data = open(mdls_path, 'rb').read()
    lines = []
    for block_offset, name, size in lang.bd.find_blocks(data):
        text = lang.decompile_block(data, block_offset, name, size)
        function_name = None
        for text_line in text.split('\n'):
            function = lang.FUNC_RE.match(text_line)
            if function:
                function_name = function.group(1)
            calls = []
            for slot_letter, raw in kh1_motion_ids.motion_calls(text_line):
                motion_id = raw & MOTION_ID_MASK
                calls.append({
                    'verb': VERB_BY_SLOT_LETTER.get(slot_letter, slot_letter),
                    'motion_id': motion_id,
                    'slot': motion_dict.get(motion_id),
                })
            lines.append({'text': text_line, 'function': function_name, 'calls': calls})
        lines.append({'text': '', 'function': None, 'calls': []})
    return lines


def build_viewer_data(mdls_path, mset_path, frame_step):
    model = kh1_pose.read_model(mdls_path)
    mesh = kh1_mesh.read_mesh(mdls_path)
    motion_dict = kh1_motion_dict.read_motion_dict(mset_path)
    ids_by_slot = motion_ids_by_slot(motion_dict)
    mset_data = open(mset_path, 'rb').read()
    motions = []
    for slot, start in enumerate(kh1_mset.motion_table_offsets(mset_data)):
        motion = kh1_mset.read_motion(mset_data, start)
        frame_count, matrices, skipped = bake_motion(model, motion, frame_step)
        motions.append({
            'slot': slot,
            'frames': motion['frames'],
            'fps': motion['fps'],
            'baked_frames': frame_count,
            'motion_ids': sorted(ids_by_slot.get(slot, [])),
            'skipped_bones': skipped,
            'matrices': matrices,
        })
        print(f'baked motion {slot}: {motion["frames"]} frames')
    parents = []
    for joint in model['joints']:
        parents.append(joint['parent'])
    vertices = []
    for vertex in mesh['vertices']:
        vertices.append([vertex['bone']] + vertex['position'] + vertex['normal'] + vertex['uv'])
    triangles = []
    for triangle in mesh['triangles']:
        triangles.append(triangle['vertices'] + [triangle['texture']])
    return {
        'name': os.path.basename(mdls_path),
        'bone_count': model['bone_count'],
        'parents': parents,
        'frame_step': frame_step,
        'vertices': vertices,
        'triangles': triangles,
        'textures': mesh['textures'],
        'motions': motions,
        'code': read_code(mdls_path, motion_dict),
    }


def write_viewer(data, out_path):
    template = open(TEMPLATE_PATH, encoding='utf-8').read()
    data_text = json.dumps(data).replace('</', '<\\/')
    with open(out_path, 'w', encoding='utf-8') as output:
        output.write(template.replace(DATA_PLACEHOLDER, data_text))


def main():
    arguments = sys.argv[1:]
    frame_step = DEFAULT_FRAME_STEP
    if '--frame-step' in arguments:
        index = arguments.index('--frame-step')
        frame_step = int(arguments[index + 1])
        arguments = arguments[:index] + arguments[index + 2:]
    if not arguments:
        print(USAGE)
        return
    mdls_path = arguments[0]
    mset_path = os.path.splitext(mdls_path)[0] + '.mset'
    if len(arguments) > 1:
        out_path = arguments[1]
    else:
        out_path = os.path.splitext(os.path.basename(mdls_path))[0] + '_viewer.html'
    data = build_viewer_data(mdls_path, mset_path, frame_step)
    write_viewer(data, out_path)
    print(f'wrote {out_path}')


if __name__ == '__main__':
    main()
