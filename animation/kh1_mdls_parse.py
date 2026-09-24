import struct, json, sys, base64, io
from PIL import Image

INITIAL_ADDRESS = 0x80
CLUT_SIZE = 256 * 4

def u32(b, o): return struct.unpack_from('<I', b, o)[0]
def i32(b, o): return struct.unpack_from('<i', b, o)[0]
def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def f32(b, o): return struct.unpack_from('<f', b, o)[0]


def parse_header(data):
    assert data[0x80:0x84] == b'MOBJ'
    pos = 0x88
    hdr_fields = ['TextureInfoOffset', 'TextureInfoSize', 'TextureDataOffset', 'TextureDataSize',
                  'ClutOffset', 'ClutSize', 'ModelOffset', 'ModelSize', 'UnkOffset', 'UnkSize']
    header = {}
    for f in hdr_fields:
        header[f] = i32(data, pos); pos += 4
    return header


def parse_joints(data, model_off, joint_count, joint_info_offset):
    joints = []
    jpos = model_off + joint_info_offset
    for i in range(joint_count):
        sx, sy, sz = f32(data, jpos + 0), f32(data, jpos + 4), f32(data, jpos + 8)
        index = u32(data, jpos + 12)
        rx, ry, rz = f32(data, jpos + 16), f32(data, jpos + 20), f32(data, jpos + 24)
        tx, ty, tz = f32(data, jpos + 32), f32(data, jpos + 36), f32(data, jpos + 40)
        hier = u32(data, jpos + 44)
        joints.append({'idx': index, 'parent': hier & 0x3FF, 'trans': (tx, ty, tz), 'rot': (rx, ry, rz),
                        'scale': (sx, sy, sz)})
        jpos += 48
    return joints


def mat3_mul(a, b):
    r = [0.0]*9
    for i in range(3):
        for j in range(3):
            r[i*3+j] = a[i*3+0]*b[0*3+j] + a[i*3+1]*b[1*3+j] + a[i*3+2]*b[2*3+j]
    return r

def mat3_vec(m, v):
    return (m[0]*v[0]+m[1]*v[1]+m[2]*v[2], m[3]*v[0]+m[4]*v[1]+m[5]*v[2], m[6]*v[0]+m[7]*v[1]+m[8]*v[2])

def rot_x(a):
    import math; c, s = math.cos(a), math.sin(a)
    return [1,0,0, 0,c,-s, 0,s,c]

def rot_y(a):
    import math; c, s = math.cos(a), math.sin(a)
    return [c,0,s, 0,1,0, -s,0,c]

def rot_z(a):
    import math; c, s = math.cos(a), math.sin(a)
    return [c,-s,0, s,c,0, 0,0,1]

IDENTITY = [1,0,0, 0,1,0, 0,0,1]

def forward_kinematics(joints):
    world_pos, world_rot = {}, {}
    for j in joints:
        # Axis convention verified this session against HyperCrown (an independent, mature
        # KH1 .mdls/.mset converter): fed the same raw (rx,ry,rz) triples for 3 non-degenerate
        # joints (1, 4, 65) into HyperCrown's own DAE export and brute-force-searched every
        # axis/order permutation for an exact match - rot[2] ("rz") drives rotation about X
        # (outermost), rot[1] ("ry") drives Z (middle), rot[0] ("rx") drives Y (innermost). The
        # previous RotZ(rz)*RotY(ry)*RotX(rx) convention (treating each stored slot as its
        # same-named axis) was wrong for every joint in every motion since this project began.
        local_rot = mat3_mul(mat3_mul(rot_x(j['rot'][2]), rot_z(j['rot'][1])), rot_y(j['rot'][0]))
        # Translation uses the SAME permutation as rotation (verified against HyperCrown across
        # joints 3/4/6/65 by comparing each joint's raw stored translate against HyperCrown's
        # independently-computed world translation column): stored trans[2] is the real X
        # offset, trans[0] is Y, trans[1] is Z.
        trans = (j['trans'][2], j['trans'][0], j['trans'][1])
        is_root = j['parent'] >= len(joints) or j['parent'] < 0
        if is_root:
            world_rot[j['idx']] = local_rot
            world_pos[j['idx']] = trans
        else:
            p_rot = world_rot.get(j['parent'], IDENTITY)
            p_pos = world_pos.get(j['parent'], (0.0, 0.0, 0.0))
            offset = mat3_vec(p_rot, trans)
            world_pos[j['idx']] = (p_pos[0]+offset[0], p_pos[1]+offset[1], p_pos[2]+offset[2])
            world_rot[j['idx']] = mat3_mul(p_rot, local_rot)
    return world_pos, world_rot


def unpack_mesh_packet(raw):
    pos = 0
    n = len(raw)
    weight_matrix = [0]*16
    vertices = []
    faces = []
    while pos < n:
        pos += 16  # MdlsMeshSubPacketHeader
        while u32(raw, pos) != 0x00008000:
            sub_type = u32(raw, pos)
            if sub_type == 0:
                joint_id = i32(raw, pos + 4)
                table_index0 = i32(raw, pos + 8)
                table_index1 = i32(raw, pos + 12)
                pos += 16
                if table_index1 == 0:
                    weight_matrix[table_index0] = joint_id
                    pos += 0x70
            elif sub_type == 1:
                vertex_count = i32(raw, pos + 8)
                unknown = i32(raw, pos + 12)
                pos += 32
                strip_local_indices = []
                for i in range(vertex_count):
                    nx, ny, nz = f32(raw, pos), f32(raw, pos+4), f32(raw, pos+8)
                    matrix_id = u32(raw, pos+12)
                    tx, ty, tz = f32(raw, pos+16), f32(raw, pos+20), f32(raw, pos+24)
                    weight = f32(raw, pos+28)
                    uv_u, uv_v = f32(raw, pos+32), f32(raw, pos+36)
                    pos += 48
                    joint_id = weight_matrix[matrix_id]
                    vidx = len(vertices)
                    vertices.append({'n': (nx, ny, nz), 't': (tx, ty, tz), 'uv': (uv_u, uv_v), 'j': joint_id})
                    strip_local_indices.append(vidx)
                    if len(strip_local_indices) >= 3:
                        c = len(strip_local_indices)
                        a, b, cc = strip_local_indices[-1], strip_local_indices[-2], strip_local_indices[-3]
                        if unknown == 0:
                            faces.append([a, b, cc] if c % 2 == 0 else [a, cc, b])
                        else:
                            faces.append([a, cc, b] if c % 2 == 0 else [a, b, cc])
            else:
                raise Exception(f"unexpected sub-packet type {sub_type} at {pos:#x}")
        pos += 0x20
    return vertices, faces


def index_fix(pixel_index):
    if (pixel_index & 31) >= 8:
        if (pixel_index & 31) < 16:
            pixel_index += 8
        elif (pixel_index & 31) < 24:
            pixel_index -= 8
    return pixel_index & 0xFF


def decode_textures(data, header):
    image_count = header['TextureInfoSize'] // 0x10
    info_pos = INITIAL_ADDRESS + header['TextureInfoOffset']
    infos = []
    for i in range(image_count):
        size = u16(data, info_pos)
        width_exp = data[info_pos+2]
        height_exp = data[info_pos+3]
        width = u16(data, info_pos+4)
        height = u16(data, info_pos+6)
        infos.append({'width': width, 'height': height})
        info_pos += 16

    data_pos = INITIAL_ADDRESS + header['TextureDataOffset']
    pixel_blocks = []
    for info in infos:
        n = info['width'] * info['height']
        pixel_blocks.append(data[data_pos:data_pos+n])
        data_pos += n

    cluts = []
    for i in range(image_count):
        cluts.append(data[data_pos:data_pos+CLUT_SIZE])
        data_pos += CLUT_SIZE

    pngs = []
    for i, info in enumerate(infos):
        w, h = info['width'], info['height']
        pixels = pixel_blocks[i]
        clut = cluts[i]
        img = Image.new('RGBA', (w, h))
        px = img.load()
        for y in range(h):
            row = y * w
            for x in range(w):
                idx = index_fix(pixels[row + x])
                o = idx * 4
                r, g, b, a = clut[o], clut[o+1], clut[o+2], clut[o+3]
                a = (a * 0xFF) >> 7
                px[x, y] = (r, g, b, min(a, 255))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        pngs.append('data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii'))
        print(f"texture {i}: {w}x{h}")
    return pngs


def parse_full(path):
    data = open(path, 'rb').read()
    header = parse_header(data)
    model_off = INITIAL_ADDRESS + header['ModelOffset']
    joint_count = i32(data, model_off)
    joint_info_offset = i32(data, model_off + 4)
    mesh_count = i32(data, model_off + 12)
    joints = parse_joints(data, model_off, joint_count, joint_info_offset)
    world_pos, world_rot = forward_kinematics(joints)

    mh_pos = model_off + 16
    mesh_headers = []
    for i in range(mesh_count):
        mesh_headers.append({'tex': i32(data, mh_pos+4), 'packet_offset': i32(data, mh_pos+12)})
        mh_pos += 16

    # Local (joint-relative) vertex data - kept local rather than pre-skinned to world space so
    # the viewer can re-skin every frame as the skeleton animates.
    all_local_pos, all_local_normal, all_joint_ids, all_uvs = [], [], [], []
    faces_by_tex = {}
    for i, mh in enumerate(mesh_headers):
        start = model_off + mh['packet_offset']
        end = (model_off + mesh_headers[i+1]['packet_offset']) if i+1 < len(mesh_headers) else (INITIAL_ADDRESS + header['UnkOffset'])
        raw = data[start:end]
        verts, faces = unpack_mesh_packet(raw)
        base = len(all_local_pos)
        for v in verts:
            # Same axis permutation as joint trans/rot (see forward_kinematics): stored [2] is
            # the real X, [0] is Y, [1] is Z - vertices are packed in this file with the same
            # convention, confirmed by the mesh looking twisted relative to the now-corrected
            # skeleton until this was applied.
            t, n = v['t'], v['n']
            all_local_pos.append([round(t[2], 4), round(t[0], 4), round(t[1], 4)])
            all_local_normal.append([round(n[2], 4), round(n[0], 4), round(n[1], 4)])
            all_joint_ids.append(v['j'])
            all_uvs.append([round(v['uv'][0], 4), round(v['uv'][1], 4)])
        tex = mh['tex']
        faces_by_tex.setdefault(tex, [])
        for f in faces:
            faces_by_tex[tex].append([f[0]+base, f[1]+base, f[2]+base])
        print(f"mesh {i}: {len(verts)} verts, {len(faces)} faces, tex={tex}")

    textures = decode_textures(data, header)
    return joints, all_local_pos, all_local_normal, all_joint_ids, all_uvs, faces_by_tex, textures


if __name__ == '__main__':
    joints, local_pos, local_normal, joint_ids, uvs, faces_by_tex, textures = parse_full(sys.argv[1])
    out = {
        'joints': joints,
        'localPos': local_pos,
        'localNormal': local_normal,
        'jointIds': joint_ids,
        'uvs': uvs,
        'facesByTex': faces_by_tex,
        'textures': textures,
    }
    with open(sys.argv[2], 'w') as f:
        json.dump(out, f)
    total_faces = sum(len(v) for v in faces_by_tex.values())
    print(f"total: {len(verts)} verts, {total_faces} faces, {len(textures)} textures -> {sys.argv[2]}")
