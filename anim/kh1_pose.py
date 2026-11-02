import json
import math
import struct
import sys

import kh1_mset

MODEL_OFFSET_FIELD = 0xA0
MODEL_HEADER_BASE = 0x80
MODEL_JOINTS_FIELD = 0x04
MODEL_INFO_FIELD = 0x08
JOINT_SIZE = 0x30
JOINT_SCALE = 0x00
JOINT_ROTATION = 0x10
JOINT_TRANSLATION = 0x20
JOINT_HIERARCHY = 0x2C
INFO_FOOT_HEIGHTS = 0x00
INFO_LOOK_AT_BONE_FALLBACK = 0x10
INFO_LOOK_AT_BONE = 0x20
INFO_FOOT_BONES = 0x90
FOOT_SLOTS = 4
NO_LOOK_AT_BONE = -1
LOOK_AT_FALLBACK_DISABLED = 1

NO_PARENT = 0x3FF
PARENT_MASK = 0x3FF

FLAG_SKIP_BONE = 0x4000000
FLAG_LOCAL_SET_ON_MOTION_CHANGE = 0x2000000
FLAG_ROTATE_FROM_ACTOR_ROOT = 0x1000000
FLAG_KEEP_POSITION_FROM_EARLIER = 0x800000
CHAIN_MODE_MASK = 0x600000
CHAIN_MODE_ONE_BONE_AIM = 0x200000
CHAIN_MODE_SHIFT = 21
TWO_BONE_BEND_BASE = 2
ROTATION_MODE_MASK = 3
ROTATION_FROM_CHANNELS = 0
ROTATION_AIM_AT_HELPER = 1
ROTATION_COPY_HELPER = 2
ROTATION_USE_POLE_HELPER = 3
ONE_BIT_POSITION_LIMIT = 0x800

INSTANCE_GROUND_IK_MASK = 3
INSTANCE_GROUND_ALWAYS_SNAP = 2
INSTANCE_LOOK_AT_MASK = 0xC
INSTANCE_FEET_ON_GROUND = 0x200000

SAMPLED_SCALE = 0
SAMPLED_SCALE_PAD = 3
SAMPLED_ACCUMULATED_SCALE = 4
SAMPLED_ROTATION = 8
SAMPLED_TRANSLATION = 12
FLOATS_PER_BONE = 16

ACTOR_SCALE_TOLERANCE = 0.005
ZERO_LENGTH_REPLACEMENT = 1e-06

IDENTITY_ACTOR = [1.0, 0.0, 0.0, 0.0,
                  0.0, 1.0, 0.0, 0.0,
                  0.0, 0.0, 1.0, 0.0,
                  0.0, 0.0, 0.0, 1.0]


def read_f32(data, offset):
    return struct.unpack_from('<f', data, offset)[0]


def read_i32(data, offset):
    return struct.unpack_from('<i', data, offset)[0]


def read_u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def read_model(mdls_path):
    data = open(mdls_path, 'rb').read()
    model_start = MODEL_HEADER_BASE + read_i32(data, MODEL_OFFSET_FIELD)
    bone_count = struct.unpack_from('<h', data, model_start)[0]
    joints_start = model_start + read_i32(data, model_start + MODEL_JOINTS_FIELD)
    info_start = model_start + read_i32(data, model_start + MODEL_INFO_FIELD)
    joints = []
    for bone in range(bone_count):
        position = joints_start + bone * JOINT_SIZE
        joint = {
            'scale': list(struct.unpack_from('<3f', data, position + JOINT_SCALE)),
            'rotation': list(struct.unpack_from('<3f', data, position + JOINT_ROTATION)),
            'translation': list(struct.unpack_from('<3f', data, position + JOINT_TRANSLATION)),
            'hierarchy': read_u32(data, position + JOINT_HIERARCHY),
        }
        joint['parent'] = joint['hierarchy'] & PARENT_MASK
        joints.append(joint)
    foot_heights = []
    foot_bones = []
    for slot in range(FOOT_SLOTS):
        foot_heights.append(read_f32(data, info_start + INFO_FOOT_HEIGHTS + slot * 4))
        foot_bones.append(read_i32(data, info_start + INFO_FOOT_BONES + slot * 4))
    model = {
        'bone_count': bone_count,
        'joints': joints,
        'foot_heights': foot_heights,
        'foot_bones': foot_bones,
        'look_at_bone': read_i32(data, info_start + INFO_LOOK_AT_BONE),
        'look_at_bone_fallback': read_i32(data, info_start + INFO_LOOK_AT_BONE_FALLBACK),
    }
    return model


def read_motion(mset_path, slot):
    data = open(mset_path, 'rb').read()
    offsets = kh1_mset.motion_table_offsets(data)
    return kh1_mset.read_motion(data, offsets[slot])


def identity_matrix():
    return list(IDENTITY_ACTOR)


def copy_matrix(matrix):
    return list(matrix)


def multiply_matrices(first, second):
    result = []
    for row in range(4):
        for column in range(4):
            total = 0.0
            for inner in range(4):
                total += first[row * 4 + inner] * second[inner * 4 + column]
            result.append(total)
    return result


def get_row(matrix, row):
    return matrix[row * 4:row * 4 + 4]


def set_row(matrix, row, values):
    for column in range(len(values)):
        matrix[row * 4 + column] = values[column]


def get_translation(matrix):
    return [matrix[12], matrix[13], matrix[14]]


def set_translation(matrix, point):
    matrix[12] = point[0]
    matrix[13] = point[1]
    matrix[14] = point[2]


def transform_vector4(matrix, vector):
    result = []
    for column in range(4):
        total = 0.0
        for row in range(4):
            total += vector[row] * matrix[row * 4 + column]
        result.append(total)
    return result


def transform_point(matrix, point):
    result = transform_vector4(matrix, [point[0], point[1], point[2], 1.0])
    return [result[0], result[1], result[2]]


def rotation_about_x(angle):
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return [1.0, 0.0, 0.0, 0.0, 0.0, cosine, sine, 0.0, 0.0, -sine, cosine, 0.0, 0.0, 0.0, 0.0, 1.0]


def rotation_about_y(angle):
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return [cosine, 0.0, -sine, 0.0, 0.0, 1.0, 0.0, 0.0, sine, 0.0, cosine, 0.0, 0.0, 0.0, 0.0, 1.0]


def rotation_about_z(angle):
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return [cosine, sine, 0.0, 0.0, -sine, cosine, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]


def rotate_matrix(matrix, rotation):
    if rotation[0] != 0.0:
        matrix = multiply_matrices(matrix, rotation_about_x(rotation[0]))
    if rotation[1] != 0.0:
        matrix = multiply_matrices(matrix, rotation_about_y(rotation[1]))
    if rotation[2] != 0.0:
        matrix = multiply_matrices(matrix, rotation_about_z(rotation[2]))
    return matrix


def build_scale_rotation_translation(scale, rotation, translation):
    matrix = identity_matrix()
    matrix[0] = scale[0]
    matrix[5] = scale[1]
    matrix[10] = scale[2]
    matrix = rotate_matrix(matrix, rotation)
    set_translation(matrix, translation)
    return matrix


def build_rotation_translation(rotation, translation):
    matrix = rotate_matrix(identity_matrix(), rotation)
    set_translation(matrix, translation)
    return matrix


def vector_length(vector):
    return math.sqrt(vector[0] * vector[0] + vector[1] * vector[1] + vector[2] * vector[2])


def normalized(vector):
    length = vector_length(vector)
    result = list(vector)
    if length != 0.0:
        result[0] = vector[0] / length
        result[1] = vector[1] / length
        result[2] = vector[2] / length
    return result


def normalized_with_zero_w(vector):
    result = normalized([vector[0], vector[1], vector[2]])
    return [result[0], result[1], result[2], 0.0]


def subtract(first, second):
    return [first[0] - second[0], first[1] - second[1], first[2] - second[2]]


def cross(first, second):
    return [first[1] * second[2] - first[2] * second[1],
            first[2] * second[0] - first[0] * second[2],
            first[0] * second[1] - first[1] * second[0],
            0.0]


def divide_like_float(numerator, denominator):
    if denominator != 0.0:
        return numerator / denominator
    if numerator > 0.0:
        return math.inf
    if numerator < 0.0:
        return -math.inf
    return math.nan


def divide_or_tiny(value, divisor):
    if divisor == 0.0:
        divisor = ZERO_LENGTH_REPLACEMENT
    return value / divisor


def row_scale(matrix, row):
    total = 0.0
    for column in range(3):
        total += matrix[row * 4 + column] * matrix[row * 4 + column]
    return math.sqrt(abs(total))


def split_scale_from_rows(matrix):
    result = copy_matrix(matrix)
    scales = []
    for row in range(3):
        scale = row_scale(matrix, row)
        scales.append(scale)
        for column in range(3):
            result[row * 4 + column] = divide_or_tiny(matrix[row * 4 + column], scale)
    return result, scales


def scale_rows(matrix, scales):
    result = copy_matrix(matrix)
    for row in range(3):
        for column in range(3):
            result[row * 4 + column] = matrix[row * 4 + column] * scales[row]
    return result


def transpose(matrix):
    result = []
    for row in range(4):
        for column in range(4):
            result.append(matrix[column * 4 + row])
    return result


def inverse_affine(matrix):
    unit_rows = copy_matrix(matrix)
    lengths = []
    for row in range(3):
        length = vector_length(get_row(matrix, row))
        lengths.append(length)
        if length != 0.0:
            for column in range(3):
                unit_rows[row * 4 + column] = matrix[row * 4 + column] / length
    result = transpose(unit_rows)
    result[3] = 0.0
    result[7] = 0.0
    result[11] = 0.0
    result[12] = 0.0
    result[13] = 0.0
    result[14] = 0.0
    result[15] = 1.0
    for row in range(3):
        for column in range(3):
            result[row * 4 + column] = divide_or_tiny(result[row * 4 + column], lengths[row])
    moved = transform_vector4(result, get_row(matrix, 3))
    result[12] = -moved[0]
    result[13] = -moved[1]
    result[14] = -moved[2]
    return result


def multiply_components(first, second):
    return [first[0] * second[0], first[1] * second[1], first[2] * second[2]]


class AnimationInstance:
    def __init__(self, bone_count):
        self.bone_count = bone_count
        self.sampled = []
        self.local = []
        self.world = []
        self.rotation = []
        for bone in range(bone_count):
            self.sampled.append([0.0] * FLOATS_PER_BONE)
            self.local.append(identity_matrix())
            self.world.append(identity_matrix())
            self.rotation.append(identity_matrix())
        self.helper_world = []
        self.flags = 0
        self.root_motion = [0.0, 0.0, 0.0]
        self.root_position = [0.0, 0.0, 0.0]
        self.actor_root_copy = identity_matrix()

    def scale(self, bone):
        return self.sampled[bone][SAMPLED_SCALE:SAMPLED_SCALE + 3]

    def accumulated_scale(self, bone):
        return self.sampled[bone][SAMPLED_ACCUMULATED_SCALE:SAMPLED_ACCUMULATED_SCALE + 3]

    def set_accumulated_scale(self, bone, values):
        for axis in range(3):
            self.sampled[bone][SAMPLED_ACCUMULATED_SCALE + axis] = values[axis]

    def channel_rotation(self, bone):
        return self.sampled[bone][SAMPLED_ROTATION:SAMPLED_ROTATION + 3]

    def channel_translation(self, bone):
        return self.sampled[bone][SAMPLED_TRANSLATION:SAMPLED_TRANSLATION + 3]

    def channel_translation_with_pad(self, bone):
        return self.sampled[bone][SAMPLED_TRANSLATION:SAMPLED_TRANSLATION + 4]


class ActorRoot:
    def __init__(self, actor_matrix):
        self.axis_scales = []
        for row in range(3):
            self.axis_scales.append(row_scale(actor_matrix, row))
        root = copy_matrix(actor_matrix)
        for index in (4, 5, 6, 8, 9, 10):
            root[index] = root[index] * -1.0
        self.negated_copy = copy_matrix(root)
        for row in range(3):
            for column in range(4):
                root[row * 4 + column] = divide_or_tiny(root[row * 4 + column], self.axis_scales[row])
        self.translation = get_translation(root)
        set_translation(root, [0.0, 0.0, 0.0])
        self.matrix = root

    def is_scaled(self):
        for scale in self.axis_scales:
            if abs(scale - 1.0) > ACTOR_SCALE_TOLERANCE:
                return True
        return False


def write_channel(values_by_kind, kind, value):
    if kind in kh1_mset.SCALE_CHANNELS:
        values_by_kind['scale'][kind - 1] = value
    elif kind in kh1_mset.ROTATION_CHANNELS:
        values_by_kind['rotation'][kind - 4] = value
    elif kind in kh1_mset.TRANSLATION_CHANNELS:
        values_by_kind['translation'][kind - 7] = value


def write_sampled_value(instance, bone, kind, value):
    sampled = instance.sampled[bone]
    if kind in kh1_mset.SCALE_CHANNELS:
        sampled[SAMPLED_SCALE + kind - 1] = value
    elif kind in kh1_mset.ROTATION_CHANNELS:
        sampled[SAMPLED_ROTATION + kind - 4] = value
    elif kind in kh1_mset.TRANSLATION_CHANNELS:
        sampled[SAMPLED_TRANSLATION + kind - 7] = value


def copy_bind_channels(instance, model):
    for bone in range(model['bone_count']):
        joint = model['joints'][bone]
        for axis in range(3):
            instance.sampled[bone][SAMPLED_SCALE + axis] = joint['scale'][axis]
            instance.sampled[bone][SAMPLED_ROTATION + axis] = joint['rotation'][axis]
            instance.sampled[bone][SAMPLED_TRANSLATION + axis] = joint['translation'][axis]


def actor_init_bind_pose(instance, model, actor_root):
    for bone in range(model['bone_count']):
        parent = model['joints'][bone]['parent']
        if parent == NO_PARENT:
            instance.set_accumulated_scale(bone, instance.scale(bone))
            parent_rotation = actor_root.matrix
            parent_world = actor_root.matrix
        else:
            parent_rotation = instance.rotation[parent]
            parent_world = instance.world[parent]
            instance.set_accumulated_scale(bone, multiply_components(instance.accumulated_scale(parent), instance.scale(bone)))
        world_position = transform_point(parent_world, instance.channel_translation(bone))
        instance.local[bone] = build_rotation_translation(instance.channel_rotation(bone), instance.channel_translation(bone))
        instance.rotation[bone] = multiply_matrices(instance.local[bone], parent_rotation)
        world = scale_rows(instance.rotation[bone], instance.accumulated_scale(bone))
        set_row(world, 3, [world_position[0], world_position[1], world_position[2], 1.0])
        instance.world[bone] = world


def reset_pose_on_motion_change(instance, model, motion, bone_flags):
    copy_bind_channels(instance, model)
    for override in motion['overrides']:
        write_sampled_value(instance, override['bone'], override['kind'], override['value'])
    for bone in range(model['bone_count']):
        flags = bone_flags[bone]
        if flags & FLAG_SKIP_BONE == 0 and flags & FLAG_LOCAL_SET_ON_MOTION_CHANGE != 0:
            instance.local[bone] = build_rotation_translation(instance.channel_rotation(bone), instance.channel_translation(bone))


def sample_bone_channels(instance, motion, time_units):
    for channel in motion['channels']:
        if not channel['keys']:
            continue
        value = kh1_mset.sample_channel_units(channel, time_units)
        if channel['kind'] in kh1_mset.ROTATION_CHANNELS:
            value = kh1_mset.wrap_angle(value)
        write_sampled_value(instance, channel['bone'], channel['kind'], value)


def sample_helper_channels(helpers, motion, time_units):
    for channel in motion['helper_channels']:
        if not channel['keys']:
            continue
        value = kh1_mset.sample_channel_units(channel, time_units)
        if channel['kind'] in kh1_mset.ROTATION_CHANNELS:
            value = kh1_mset.wrap_angle(value)
        write_channel(helpers[channel['bone']], channel['kind'], value)


def build_helper_matrices(helpers, actor_root):
    helper_world = [actor_root.matrix]
    for helper_number in range(1, len(helpers)):
        helper = helpers[helper_number]
        local = build_scale_rotation_translation(helper['scale'], helper['rotation'], helper['translation'])
        helper_world.append(multiply_matrices(local, helper_world[helper['parent']]))
    return helper_world


def own_helper_number(flags):
    return (((flags >> 16) & 0x800) | (flags & 0x7FC)) >> 2


def position_helper_code(flags):
    return ((flags >> 8) & 0x100000) | (flags & 0xFF800)


def position_helper_number(flags):
    return position_helper_code(flags) >> 11


def helper_position(instance, helper_number_plus_one):
    return get_translation(instance.helper_world[helper_number_plus_one - 1])


def flat_floor_query(floor_height, start, length):
    if floor_height is None:
        return None
    if start[1] <= floor_height <= start[1] + length:
        return [start[0], floor_height, start[2]]
    return None


def solve_limb(target, upper_length, lower_length, bend, upper_matrix, lower_wanted, upper_twist, lower_twist, pole):
    origin = get_translation(upper_matrix)
    direction = subtract(target, origin)
    distance = vector_length(direction)
    direction = normalized(direction)
    if pole is None:
        side = normalized([-direction[1], direction[0], 0.0])
        up = normalized_with_zero_w(cross(direction, side))
    else:
        side = normalized(subtract(pole, origin))
        up = normalized(cross(direction, side))
        side = normalized(cross(up, direction))
    basis = [direction[0], direction[1], direction[2], 0.0,
             side[0], side[1], side[2], 0.0,
             up[0], up[1], up[2], 0.0,
             0.0, 0.0, 0.0, 1.0]
    if upper_twist != 0.0:
        basis = multiply_matrices(rotation_about_x(upper_twist), basis)
    lower_matrix = None
    if not lower_wanted:
        upper = copy_matrix(basis)
    else:
        knee_cosine = divide_like_float(distance * distance - upper_length * upper_length - lower_length * lower_length,
                                        (upper_length + upper_length) * lower_length)
        clamped = -1.0
        if -1.0 <= knee_cosine:
            clamped = knee_cosine
        knee_cosine = 1.0
        if clamped <= 1.0:
            knee_cosine = clamped
        sine_squared = 1.0 - knee_cosine * knee_cosine
        if not 0.0 <= sine_squared:
            sine_squared = 0.0
        knee_sine = math.sqrt(abs(sine_squared))
        if bend != 0:
            knee_sine = -knee_sine
        lower_matrix = [knee_cosine, knee_sine, 0.0, 0.0,
                        -knee_sine, knee_cosine, 0.0, 0.0,
                        0.0, 0.0, 1.0, 0.0,
                        upper_length, 0.0, 0.0, 1.0]
        if lower_twist != 0.0:
            lower_matrix = multiply_matrices(rotation_about_x(lower_twist), lower_matrix)
        reach_along = (knee_cosine * lower_length + upper_length) * distance
        reach_across = -(knee_sine * lower_length * distance)
        reach = math.sqrt(abs(reach_across * reach_across + reach_along * reach_along))
        hip_cosine = divide_like_float(reach_along, reach)
        hip_sine = divide_like_float(reach_across, reach)
        hip_turn = [hip_cosine, hip_sine, 0.0, 0.0,
                    -hip_sine, hip_cosine, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    0.0, 0.0, 0.0, 1.0]
        upper = multiply_matrices(hip_turn, basis)
    set_translation(upper, origin)
    return upper, lower_matrix


class SkeletonSolver:
    def __init__(self, instance, model, bone_flags, actor_root, floor_height):
        self.instance = instance
        self.model = model
        self.bone_flags = bone_flags
        self.actor_root = actor_root
        self.floor_height = floor_height

    def joint_translation(self, bone):
        return self.model['joints'][bone]['translation']

    def parent_of(self, bone):
        return self.model['joints'][bone]['parent']

    def parent_world(self, bone):
        parent = self.parent_of(bone)
        if parent == NO_PARENT:
            return self.actor_root.matrix
        return self.instance.world[parent]

    def pole_in_parent_space(self, flags, inverse_parent):
        if flags & ROTATION_MODE_MASK != ROTATION_USE_POLE_HELPER:
            return None
        return transform_point(inverse_parent, helper_position(self.instance, own_helper_number(flags)))

    def clear_look_at_bone_flag(self):
        if self.model['look_at_bone'] != NO_LOOK_AT_BONE:
            look_at_bone = self.model['look_at_bone']
        elif self.model['look_at_bone_fallback'] != LOOK_AT_FALLBACK_DISABLED:
            look_at_bone = self.model['look_at_bone_fallback']
        else:
            return
        self.bone_flags[look_at_bone - 1] = self.bone_flags[look_at_bone - 1] & ~FLAG_LOCAL_SET_ON_MOTION_CHANGE

    def solve(self):
        instance = self.instance
        self.clear_look_at_bone_flag()
        bone = 0
        while bone < self.model['bone_count']:
            flags = self.bone_flags[bone]
            if flags & FLAG_SKIP_BONE != 0:
                bone += 1
                continue
            parent = self.parent_of(bone)
            if parent == NO_PARENT:
                instance.set_accumulated_scale(bone, instance.scale(bone))
                parent_rotation = self.actor_root.matrix
            else:
                parent_rotation = instance.rotation[parent]
                instance.set_accumulated_scale(bone, multiply_components(instance.accumulated_scale(parent), instance.scale(bone)))
            instance.rotation[bone] = identity_matrix()
            chain_mode = flags & CHAIN_MODE_MASK
            next_bone = bone + 1
            if chain_mode == CHAIN_MODE_ONE_BONE_AIM:
                self.solve_one_bone_aim(bone, flags)
            elif chain_mode == 0:
                self.solve_forward(bone, flags, parent_rotation)
            else:
                self.solve_two_bone_limb(bone, flags)
                next_bone = bone + 2
            set_row(instance.rotation[bone], 3, [0.0, 0.0, 0.0, 1.0])
            bone = next_bone

    def solve_one_bone_aim(self, bone, flags):
        instance = self.instance
        parent = self.parent_of(bone)
        set_translation(instance.local[bone], instance.channel_translation(bone))
        inverse_parent = inverse_affine(instance.world[parent])
        target_number = position_helper_number(self.bone_flags[bone + 1])
        target = transform_point(inverse_parent, helper_position(instance, target_number))
        pole = self.pole_in_parent_space(flags, inverse_parent)
        length = self.joint_translation(bone + 1)[0] * instance.scale(bone)[0]
        upper, unused = solve_limb(target, length, 0.0, 0, instance.local[bone], False,
                                   instance.channel_rotation(bone)[0], 0.0, pole)
        instance.local[bone] = upper
        self.compose_from_local(bone, instance.world[parent])
        child_position = transform_point(instance.world[bone], self.joint_translation(bone + 1))
        set_row(instance.world[bone + 1], 3, [child_position[0], child_position[1], child_position[2], 1.0])

    def compose_from_local(self, bone, parent_world):
        instance = self.instance
        scaled_local = scale_rows(instance.local[bone], instance.scale(bone))
        world = multiply_matrices(scaled_local, parent_world)
        position = transform_point(parent_world, instance.channel_translation(bone))
        set_row(world, 3, [position[0], position[1], position[2], 1.0])
        instance.world[bone] = world
        unit_rows, scales = split_scale_from_rows(world)
        instance.rotation[bone] = unit_rows
        instance.set_accumulated_scale(bone, scales)

    def solve_forward(self, bone, flags, parent_rotation):
        instance = self.instance
        position_code = position_helper_code(flags)
        position_number = position_helper_number(flags)
        keep_earlier_position = flags & FLAG_KEEP_POSITION_FROM_EARLIER != 0
        rotation_mode = flags & ROTATION_MODE_MASK
        inverse_parent = None
        if keep_earlier_position or position_code != 0 or flags & (FLAG_ROTATE_FROM_ACTOR_ROOT | ROTATION_MODE_MASK) != 0:
            inverse_parent = inverse_affine(self.parent_world(bone))
        if keep_earlier_position:
            position = get_translation(instance.world[bone])
            set_translation(instance.local[bone], transform_point(inverse_parent, position))
        elif position_number != 0:
            position = helper_position(instance, position_number)
            set_translation(instance.local[bone], transform_point(inverse_parent, position))
        else:
            position = transform_point(self.parent_world(bone), instance.channel_translation(bone))
        if rotation_mode == ROTATION_FROM_CHANNELS:
            if flags & FLAG_ROTATE_FROM_ACTOR_ROOT != 0:
                instance.local[bone] = build_rotation_translation(instance.channel_rotation(bone), instance.channel_translation(bone))
                instance.rotation[bone] = multiply_matrices(instance.local[bone], self.actor_root.matrix)
                instance.rotation[bone][15] = 1.0
            else:
                if flags & FLAG_LOCAL_SET_ON_MOTION_CHANGE == 0:
                    instance.local[bone] = build_rotation_translation(instance.channel_rotation(bone), instance.channel_translation(bone))
                instance.rotation[bone] = multiply_matrices(instance.local[bone], parent_rotation)
            instance.world[bone] = scale_rows(instance.rotation[bone], instance.accumulated_scale(bone))
        elif rotation_mode == ROTATION_AIM_AT_HELPER:
            self.aim_at_helper(bone, flags, parent_rotation, inverse_parent, keep_earlier_position, position_code)
            instance.world[bone] = scale_rows(instance.rotation[bone], instance.accumulated_scale(bone))
        elif rotation_mode == ROTATION_COPY_HELPER:
            helper = instance.helper_world[own_helper_number(flags) - 1]
            rotation = identity_matrix()
            for row in range(3):
                set_row(rotation, row, normalized_with_zero_w(get_row(helper, row)))
            instance.rotation[bone] = rotation
            instance.world[bone] = scale_rows(instance.rotation[bone], instance.accumulated_scale(bone))
        set_row(instance.world[bone], 3, [position[0], position[1], position[2], 1.0])
        if rotation_mode != ROTATION_FROM_CHANNELS or flags & FLAG_ROTATE_FROM_ACTOR_ROOT != 0:
            local = multiply_matrices(instance.world[bone], inverse_parent)
            unit_rows, unused = split_scale_from_rows(local)
            instance.local[bone] = unit_rows

    def aim_at_helper(self, bone, flags, parent_rotation, inverse_parent, keep_earlier_position, position_code):
        instance = self.instance
        target = transform_point(inverse_parent, helper_position(instance, own_helper_number(flags)))
        local = instance.local[bone]
        if not keep_earlier_position and position_code < ONE_BIT_POSITION_LIMIT:
            direction = subtract(target, instance.channel_translation(bone))
            set_row(local, 3, instance.channel_translation_with_pad(bone))
        else:
            direction = subtract(target, get_translation(local))
        up = [0.0, 1.0, 0.0]
        set_row(local, 0, normalized_with_zero_w(direction))
        side = cross(direction, up)
        set_row(local, 1, normalized_with_zero_w(cross(side, direction)))
        set_row(local, 2, normalized_with_zero_w(cross(direction, get_row(local, 1))))
        twist = rotation_about_x(instance.channel_rotation(bone)[0])
        local = multiply_matrices(twist, local)
        instance.local[bone] = local
        instance.rotation[bone] = multiply_matrices(local, parent_rotation)

    def ground_target(self, bone, position):
        instance = self.instance
        if instance.flags & INSTANCE_GROUND_IK_MASK == 0:
            return position
        foot_height = None
        for slot in range(FOOT_SLOTS):
            if bone == self.model['foot_bones'][slot] - 1:
                foot_height = self.model['foot_heights'][slot]
                break
        if foot_height is None:
            return position
        scales = self.actor_root.axis_scales
        offset = self.actor_root.translation
        ankle_length = self.joint_translation(bone + 2)[0]
        start = [position[0] * scales[0] + offset[0],
                 (position[1] - ankle_length) * scales[1] + offset[1],
                 position[2] * scales[2] + offset[2]]
        length = (ankle_length + ankle_length + foot_height) * scales[1]
        hit = flat_floor_query(self.floor_height, start, length)
        if hit is None:
            return position
        foot_bottom = (position[1] + foot_height) * scales[1] + offset[1]
        if instance.flags & INSTANCE_GROUND_ALWAYS_SNAP == 0 and not foot_bottom > hit[1]:
            return position
        instance.flags = instance.flags | INSTANCE_FEET_ON_GROUND
        return [(hit[0] - offset[0]) / scales[0],
                (hit[1] - offset[1]) / scales[1] - foot_height,
                (hit[2] - offset[2]) / scales[2]]

    def solve_two_bone_limb(self, bone, flags):
        instance = self.instance
        parent = self.parent_of(bone)
        lower_bone = bone + 1
        end_bone = bone + 2
        set_translation(instance.local[bone], instance.channel_translation(bone))
        inverse_parent = inverse_affine(instance.world[parent])
        instance.set_accumulated_scale(lower_bone, multiply_components(instance.accumulated_scale(bone), instance.scale(lower_bone)))
        target_number = position_helper_number(self.bone_flags[end_bone])
        position = self.ground_target(bone, helper_position(instance, target_number))
        target = transform_point(inverse_parent, position)
        bend = ((flags >> CHAIN_MODE_SHIFT) & 3) - TWO_BONE_BEND_BASE
        pole = self.pole_in_parent_space(flags, inverse_parent)
        upper_length = self.joint_translation(lower_bone)[0] * instance.scale(bone)[0]
        lower_length = instance.scale(bone)[0] * instance.scale(lower_bone)[0] * self.joint_translation(end_bone)[0]
        upper, lower = solve_limb(target, upper_length, lower_length, bend, instance.local[bone], True,
                                  instance.channel_rotation(bone)[0], instance.channel_rotation(lower_bone)[0], pole)
        instance.local[bone] = upper
        self.compose_from_local(bone, instance.world[parent])
        inverse_scale = identity_matrix()
        inverse_scale[0] = 1.0 / instance.scale(bone)[0]
        inverse_scale[5] = 1.0 / instance.scale(bone)[1]
        inverse_scale[10] = 1.0 / instance.scale(bone)[2]
        lower_local = multiply_matrices(lower, inverse_scale)
        instance.set_accumulated_scale(lower_bone, multiply_components(instance.scale(bone), instance.scale(lower_bone)))
        lower_local = scale_rows(lower_local, instance.accumulated_scale(lower_bone))
        lower_world = multiply_matrices(lower_local, instance.world[bone])
        lower_position = transform_point(instance.world[bone], self.joint_translation(lower_bone))
        set_row(lower_world, 3, [lower_position[0], lower_position[1], lower_position[2], 1.0])
        instance.world[lower_bone] = lower_world
        unit_rows, scales = split_scale_from_rows(lower_world)
        instance.rotation[lower_bone] = unit_rows
        instance.set_accumulated_scale(lower_bone, scales)
        end_position = transform_point(lower_world, self.joint_translation(end_bone))
        set_row(instance.world[end_bone], 3, [end_position[0], end_position[1], end_position[2], 1.0])
        inverse_upper = inverse_affine(instance.world[bone])
        instance.local[lower_bone] = multiply_matrices(lower_world, inverse_upper)
        instance.sampled[lower_bone][SAMPLED_SCALE_PAD] = instance.channel_rotation(lower_bone)[0]


def copy_helpers(motion):
    helpers = []
    for helper in motion['helpers']:
        helpers.append({
            'scale': list(helper['scale']),
            'parent': helper['parent'],
            'rotation': list(helper['rotation']),
            'translation': list(helper['translation']),
        })
    return helpers


def entity_animation_update(instance, model, motion, bone_flags, helpers, actor_matrix, time, floor_height):
    actor_root = ActorRoot(actor_matrix)
    instance.actor_root_copy = actor_root.negated_copy
    time_units = kh1_mset.time_units_from_frames(time)
    sample_bone_channels(instance, motion, time_units)
    sample_helper_channels(helpers, motion, time_units)
    instance.helper_world = build_helper_matrices(helpers, actor_root)
    last_helper = get_translation(instance.helper_world[len(instance.helper_world) - 1])
    instance.root_motion = multiply_components(actor_root.axis_scales, last_helper)
    SkeletonSolver(instance, model, bone_flags, actor_root, floor_height).solve()
    if actor_root.is_scaled():
        actor_scale = identity_matrix()
        actor_scale[0] = actor_root.axis_scales[0]
        actor_scale[5] = actor_root.axis_scales[1]
        actor_scale[10] = actor_root.axis_scales[2]
        for bone in range(model['bone_count']):
            if bone_flags[bone] & FLAG_SKIP_BONE == 0:
                instance.world[bone] = multiply_matrices(instance.world[bone], actor_scale)
    instance.root_position = [actor_root.translation[0] + instance.root_motion[0],
                              actor_root.translation[1] + instance.root_motion[1],
                              actor_root.translation[2] + instance.root_motion[2]]
    for bone in range(model['bone_count']):
        for axis in range(3):
            instance.world[bone][12 + axis] = instance.world[bone][12 + axis] + actor_root.translation[axis]


def skipped_bones(bone_flags):
    skipped = []
    for bone in range(len(bone_flags)):
        if bone_flags[bone] & FLAG_SKIP_BONE != 0:
            skipped.append(bone)
    return skipped


def pose_from_data(model, motion, time, actor_matrix=None, instance_flags=0, floor_height=None, previous_times=()):
    if actor_matrix is None:
        actor_matrix = IDENTITY_ACTOR
    instance = AnimationInstance(model['bone_count'])
    instance.flags = instance_flags
    copy_bind_channels(instance, model)
    actor_init_bind_pose(instance, model, ActorRoot(actor_matrix))
    bone_flags = list(motion['bone_flags'])
    helpers = copy_helpers(motion)
    reset_pose_on_motion_change(instance, model, motion, bone_flags)
    for earlier_time in previous_times:
        entity_animation_update(instance, model, motion, bone_flags, helpers, actor_matrix, earlier_time, floor_height)
    entity_animation_update(instance, model, motion, bone_flags, helpers, actor_matrix, time, floor_height)
    result = {
        'bone_count': model['bone_count'],
        'motion_time': time,
        'actor_matrix': list(actor_matrix),
        'instance_flags': instance.flags,
        'sampled_channels': instance.sampled,
        'local_matrices': instance.local,
        'world_matrices': instance.world,
        'helper_matrices': instance.helper_world,
        'root_motion': instance.root_motion,
        'root_position': instance.root_position,
        'skipped_bones': skipped_bones(bone_flags),
        'bone_flags': bone_flags,
    }
    return result


def pose(mdls_path, mset_path, slot, time, actor_matrix=None, instance_flags=0, floor_height=None):
    model = read_model(mdls_path)
    motion = read_motion(mset_path, slot)
    result = pose_from_data(model, motion, time, actor_matrix, instance_flags, floor_height)
    result['motion_slot'] = slot
    return result


def remove_actor_placement(world_matrix, actor_matrix):
    actor_root = ActorRoot(actor_matrix)
    unplaced = copy_matrix(world_matrix)
    for axis in range(3):
        unplaced[12 + axis] = unplaced[12 + axis] - actor_root.translation[axis]
    inverse_scale = identity_matrix()
    inverse_scale[0] = divide_or_tiny(1.0, actor_root.axis_scales[0])
    inverse_scale[5] = divide_or_tiny(1.0, actor_root.axis_scales[1])
    inverse_scale[10] = divide_or_tiny(1.0, actor_root.axis_scales[2])
    unplaced = multiply_matrices(unplaced, inverse_scale)
    root_at_identity = ActorRoot(IDENTITY_ACTOR).matrix
    undo_actor_rotation = multiply_matrices(transpose(actor_root.matrix), root_at_identity)
    return multiply_matrices(unplaced, undo_actor_rotation)


def write_json(result, path):
    with open(path, 'w') as output:
        json.dump(result, output)


def main():
    if len(sys.argv) < 6:
        print('usage: kh1_pose.py <model.mdls> <motion.mset> <slot> <time> <out.json> [instance_flags]')
        return
    instance_flags = 0
    if len(sys.argv) > 6:
        instance_flags = int(sys.argv[6], 0)
    result = pose(sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4]), None, instance_flags)
    write_json(result, sys.argv[5])
    print(f"wrote {sys.argv[5]}: {result['bone_count']} bones, slot {result['motion_slot']}, time {result['motion_time']}")


if __name__ == '__main__':
    main()
