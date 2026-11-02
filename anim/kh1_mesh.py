import base64
import struct
import sys

HEADER_BASE = 0x80
MOBJ_MAGIC = b'MOBJ'
TEXTURE_INFO_OFFSET_FIELD = 0x88
TEXTURE_INFO_SIZE_FIELD = 0x8C
TEXTURE_DATA_OFFSET_FIELD = 0x90
MODEL_OFFSET_FIELD = 0xA0
MODEL_END_OFFSET_FIELD = 0xA8
TEXTURE_INFO_SIZE = 0x10
TEXTURE_WIDTH = 0x04
TEXTURE_HEIGHT = 0x06
PALETTE_SIZE = 256 * 4
MODEL_MESH_COUNT = 0x0C
MODEL_MESH_HEADERS = 0x10
MESH_HEADER_SIZE = 0x10
MESH_HEADER_TEXTURE = 0x04
MESH_HEADER_PACKET = 0x0C
PACKET_HEADER_SIZE = 0x10
PACKET_TRAILER_SIZE = 0x20
PACKET_END_MARKER = 0x00008000
SUB_PACKET_BONE = 0
SUB_PACKET_STRIP = 1
BONE_SUB_PACKET_SIZE = 0x10
BONE_MATRIX_SIZE = 0x70
STRIP_HEADER_SIZE = 0x20
STRIP_VERTEX_SIZE = 0x30
BONE_SLOTS = 16
FULL_ALPHA_IN_FILE = 0x80
FULL_ALPHA = 0xFF


def read_i32(data, offset):
    return struct.unpack_from('<i', data, offset)[0]


def read_u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def read_u16(data, offset):
    return struct.unpack_from('<H', data, offset)[0]


def read_f32(data, offset):
    return struct.unpack_from('<f', data, offset)[0]


def add_strip_triangle(triangles, strip, winding_flipped, texture):
    newest = strip[-1]
    middle = strip[-2]
    oldest = strip[-3]
    even = len(strip) % 2 == 0
    if even != winding_flipped:
        triangles.append({'vertices': [newest, middle, oldest], 'texture': texture})
    else:
        triangles.append({'vertices': [newest, oldest, middle], 'texture': texture})


def read_strip(data, position, bone_slots, vertices, triangles, texture):
    vertex_count = read_i32(data, position + 8)
    winding_flipped = read_i32(data, position + 12) != 0
    position = position + STRIP_HEADER_SIZE
    strip = []
    for vertex_number in range(vertex_count):
        bone_slot = read_u32(data, position + 12)
        vertex = {
            'bone': bone_slots[bone_slot],
            'normal': list(struct.unpack_from('<3f', data, position)),
            'position': list(struct.unpack_from('<3f', data, position + 16)),
            'uv': list(struct.unpack_from('<2f', data, position + 32)),
        }
        strip.append(len(vertices))
        vertices.append(vertex)
        if len(strip) >= 3:
            add_strip_triangle(triangles, strip, winding_flipped, texture)
        position = position + STRIP_VERTEX_SIZE
    return position


def read_packets(data, start, end, vertices, triangles, texture):
    bone_slots = [0] * BONE_SLOTS
    position = start
    while position < end:
        position = position + PACKET_HEADER_SIZE
        while read_u32(data, position) != PACKET_END_MARKER:
            sub_packet = read_u32(data, position)
            if sub_packet == SUB_PACKET_BONE:
                bone = read_i32(data, position + 4)
                slot = read_i32(data, position + 8)
                second_slot = read_i32(data, position + 12)
                position = position + BONE_SUB_PACKET_SIZE
                if second_slot == 0:
                    bone_slots[slot] = bone
                    position = position + BONE_MATRIX_SIZE
            elif sub_packet == SUB_PACKET_STRIP:
                position = read_strip(data, position, bone_slots, vertices, triangles, texture)
            else:
                raise ValueError(f'unknown mesh sub-packet {sub_packet} at 0x{position:X}')
        position = position + PACKET_TRAILER_SIZE


def unswizzle_index(index):
    column = index & 31
    if 8 <= column < 16:
        index = index + 8
    elif 16 <= column < 24:
        index = index - 8
    return index & 0xFF


def read_textures(data):
    texture_count = read_i32(data, TEXTURE_INFO_SIZE_FIELD) // TEXTURE_INFO_SIZE
    info_start = HEADER_BASE + read_i32(data, TEXTURE_INFO_OFFSET_FIELD)
    pixel_position = HEADER_BASE + read_i32(data, TEXTURE_DATA_OFFSET_FIELD)
    textures = []
    for texture_number in range(texture_count):
        info = info_start + texture_number * TEXTURE_INFO_SIZE
        width = read_u16(data, info + TEXTURE_WIDTH)
        height = read_u16(data, info + TEXTURE_HEIGHT)
        textures.append({'width': width, 'height': height, 'pixels': pixel_position})
        pixel_position = pixel_position + width * height
    for texture in textures:
        texture['palette'] = pixel_position
        pixel_position = pixel_position + PALETTE_SIZE
    return textures


def texture_rgba(data, texture):
    width = texture['width']
    height = texture['height']
    rgba = bytearray()
    for pixel in range(width * height):
        index = unswizzle_index(data[texture['pixels'] + pixel])
        color = texture['palette'] + index * 4
        alpha = min(data[color + 3] * FULL_ALPHA // FULL_ALPHA_IN_FILE, FULL_ALPHA)
        rgba.extend((data[color], data[color + 1], data[color + 2], alpha))
    return bytes(rgba)


def read_mesh(mdls_path):
    data = open(mdls_path, 'rb').read()
    if data[HEADER_BASE:HEADER_BASE + 4] != MOBJ_MAGIC:
        raise ValueError('not an MDLS model')
    model_start = HEADER_BASE + read_i32(data, MODEL_OFFSET_FIELD)
    model_end = HEADER_BASE + read_i32(data, MODEL_END_OFFSET_FIELD)
    mesh_count = read_i32(data, model_start + MODEL_MESH_COUNT)
    mesh_headers = []
    for mesh_number in range(mesh_count):
        header = model_start + MODEL_MESH_HEADERS + mesh_number * MESH_HEADER_SIZE
        mesh_headers.append({
            'texture': read_i32(data, header + MESH_HEADER_TEXTURE),
            'start': model_start + read_i32(data, header + MESH_HEADER_PACKET),
        })
    vertices = []
    triangles = []
    for mesh_number in range(mesh_count):
        start = mesh_headers[mesh_number]['start']
        if mesh_number + 1 < mesh_count:
            end = mesh_headers[mesh_number + 1]['start']
        else:
            end = model_end
        read_packets(data, start, end, vertices, triangles, mesh_headers[mesh_number]['texture'])
    images = []
    for texture in read_textures(data):
        images.append({
            'width': texture['width'],
            'height': texture['height'],
            'rgba': base64.b64encode(texture_rgba(data, texture)).decode('ascii'),
        })
    return {'vertices': vertices, 'triangles': triangles, 'textures': images}


def main():
    if len(sys.argv) < 2:
        print('usage: kh1_mesh.py <model.mdls>')
        return
    mesh = read_mesh(sys.argv[1])
    print(len(mesh['vertices']), 'vertices', len(mesh['triangles']), 'triangles', len(mesh['textures']), 'textures')


if __name__ == '__main__':
    main()
