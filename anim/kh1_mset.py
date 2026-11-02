import struct
import sys

MMTN_MAGIC = b'MMTN'
MOTION_TABLE_OFFSET = 0x40
END_OF_TABLE = 0xFFFFFFFF
CHANNEL_SIZE = 6
KEY_SIZE = 16
HELPER_SIZE = 40
OVERRIDE_SIZE = 8
TIME_UNITS_PER_FRAME = 256
INTERPOLATION_HOLD = 0
INTERPOLATION_LINEAR = 1
EDGE_HOLD = 0
EDGE_LINEAR = 1
EDGE_REPEAT = 2
SCALE_CHANNELS = (1, 2, 3)
ROTATION_CHANNELS = (4, 5, 6)
TRANSLATION_CHANNELS = (7, 8, 9)
PI_AS_FLOAT32 = 3.1415927410125732
TWO_PI_AS_FLOAT32 = 6.2831854820251465

MOTION_FRAME_COUNT = 0x04
MOTION_FPS = 0x08
MOTION_BONE_COUNT = 0x10
MOTION_BONE_FLAGS = 0x14
MOTION_CHANNEL_COUNT = 0x18
MOTION_CHANNELS = 0x1C
MOTION_HELPER_CHANNEL_COUNT = 0x20
MOTION_HELPER_CHANNELS = 0x24
MOTION_KEYS = 0x28
MOTION_HELPER_COUNT = 0x2C
MOTION_HELPERS = 0x30
MOTION_OVERRIDE_COUNT = 0x34
MOTION_OVERRIDES = 0x38


def read_u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def read_i32(data, offset):
    return struct.unpack_from('<i', data, offset)[0]


def read_u16(data, offset):
    return struct.unpack_from('<H', data, offset)[0]


def read_f32(data, offset):
    return struct.unpack_from('<f', data, offset)[0]


def to_float32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def motion_table_offsets(data):
    section_count = read_u32(data, 0)
    first_section = read_u32(data, 4)
    if section_count == 0 or data[first_section:first_section + 4] != MMTN_MAGIC:
        raise ValueError('section 0 is not MMTN')
    table = first_section + MOTION_TABLE_OFFSET
    offsets = []
    while True:
        value = read_u32(data, table + 4 * len(offsets))
        if value == END_OF_TABLE:
            break
        offsets.append(table + value)
    return offsets


def read_keys(data, keys_start, first_key, key_count):
    keys = []
    for key_number in range(first_key, first_key + key_count):
        position = keys_start + key_number * KEY_SIZE
        head = read_i32(data, position)
        key = {
            'time_units': head >> 8,
            'time': (head >> 8) / TIME_UNITS_PER_FRAME,
            'interpolation': head & 0xFF,
            'value': read_f32(data, position + 4),
            'tangent_8': read_f32(data, position + 8),
            'tangent_c': read_f32(data, position + 12),
        }
        keys.append(key)
    return keys


def read_channels(data, channels_start, channel_count, keys_start):
    channels = []
    for channel_number in range(channel_count):
        position = channels_start + channel_number * CHANNEL_SIZE
        kind_byte = data[position + 2]
        channel = {
            'bone': read_u16(data, position),
            'kind': kind_byte & 0xF,
            'before': (kind_byte >> 4) & 3,
            'after': kind_byte >> 6,
            'keys': read_keys(data, keys_start, read_u16(data, position + 4), data[position + 3]),
        }
        channels.append(channel)
    return channels


def read_helpers(data, helpers_start, helper_count):
    helpers = []
    for helper_number in range(helper_count):
        position = helpers_start + helper_number * HELPER_SIZE
        helper = {
            'scale': list(struct.unpack_from('<3f', data, position)),
            'parent': read_i32(data, position + 0x0C),
            'rotation': list(struct.unpack_from('<3f', data, position + 0x10)),
            'translation': list(struct.unpack_from('<3f', data, position + 0x1C)),
        }
        helpers.append(helper)
    return helpers


def read_overrides(data, overrides_start, override_count):
    overrides = []
    for override_number in range(override_count):
        position = overrides_start + override_number * OVERRIDE_SIZE
        override = {
            'bone': read_u16(data, position),
            'kind': read_u16(data, position + 2),
            'value': read_f32(data, position + 4),
        }
        overrides.append(override)
    return overrides


def read_bone_flags(data, flags_start, bone_count):
    flags = []
    for bone in range(bone_count):
        flags.append(read_u32(data, flags_start + bone * 4))
    return flags


def read_motion(data, start):
    keys_start = start + read_u32(data, start + MOTION_KEYS)
    bone_count = read_u32(data, start + MOTION_BONE_COUNT)
    motion = {
        'start': start,
        'frames': read_u32(data, start + MOTION_FRAME_COUNT),
        'fps': read_f32(data, start + MOTION_FPS),
        'bones': bone_count,
        'bone_flags': read_bone_flags(data, start + read_u32(data, start + MOTION_BONE_FLAGS), bone_count),
        'channels': read_channels(data, start + read_u32(data, start + MOTION_CHANNELS),
                                  read_u32(data, start + MOTION_CHANNEL_COUNT), keys_start),
        'helper_channels': read_channels(data, start + read_u32(data, start + MOTION_HELPER_CHANNELS),
                                         read_u32(data, start + MOTION_HELPER_CHANNEL_COUNT), keys_start),
        'helpers': read_helpers(data, start + read_u32(data, start + MOTION_HELPERS),
                                read_u32(data, start + MOTION_HELPER_COUNT)),
        'overrides': read_overrides(data, start + read_u32(data, start + MOTION_OVERRIDES),
                                    read_u32(data, start + MOTION_OVERRIDE_COUNT)),
    }
    motion['helper_channel_count'] = len(motion['helper_channels'])
    motion['helper_count'] = len(motion['helpers'])
    return motion


def time_units_from_frames(time):
    scaled = to_float32(to_float32(time) * TIME_UNITS_PER_FRAME)
    return int(scaled)


def extrapolate_before(channel, time_units):
    keys = channel['keys']
    first = keys[0]
    second = keys[1]
    gap = second['time_units'] - first['time_units']
    if first['interpolation'] == INTERPOLATION_LINEAR and gap != 0:
        slope = (second['value'] - first['value']) / gap
    else:
        slope = first['tangent_8']
    return first['value'] - (first['time_units'] - time_units) * slope


def extrapolate_after(channel, time_units):
    keys = channel['keys']
    last = keys[-1]
    previous = keys[-2]
    gap = last['time_units'] - previous['time_units']
    if last['interpolation'] == INTERPOLATION_LINEAR and gap != 0:
        slope = (last['value'] - previous['value']) / gap
    else:
        slope = last['tangent_c']
    return last['value'] + (time_units - last['time_units']) * slope


def interpolate(earlier, later, time_units):
    if earlier['interpolation'] == INTERPOLATION_HOLD:
        return earlier['value']
    gap = later['time_units'] - earlier['time_units']
    since_earlier = time_units - earlier['time_units']
    if earlier['interpolation'] == INTERPOLATION_LINEAR:
        return since_earlier * (later['value'] - earlier['value']) / gap + earlier['value']
    progress = since_earlier / gap
    square = progress * progress
    cube = square * progress
    weight_earlier = 2 * cube - 3 * square + 1
    weight_later = 3 * square - 2 * cube
    weight_earlier_tangent = gap * (cube - 2 * square + progress)
    weight_later_tangent = gap * (cube - square)
    value = weight_earlier * earlier['value']
    value += weight_later * later['value']
    value += weight_earlier_tangent * earlier['tangent_c']
    value += weight_later_tangent * later['tangent_8']
    return value


def sample_channel_units(channel, time_units):
    keys = channel['keys']
    first = keys[0]
    if len(keys) == 1:
        return first['value']
    last = keys[-1]
    span = last['time_units'] - first['time_units']
    if not time_units > first['time_units']:
        if channel['before'] == EDGE_HOLD:
            return first['value']
        if channel['before'] == EDGE_LINEAR:
            return extrapolate_before(channel, time_units)
        if channel['before'] == EDGE_REPEAT and span > 0:
            while first['time_units'] > time_units:
                time_units = time_units + span
    if not time_units < last['time_units']:
        if channel['after'] == EDGE_HOLD:
            return last['value']
        if channel['after'] == EDGE_LINEAR:
            return extrapolate_after(channel, time_units)
        if channel['after'] == EDGE_REPEAT and span > 0:
            while time_units > last['time_units']:
                time_units = time_units - span
    low = 0
    high = len(keys) - 1
    while high - low > 1:
        middle = (low + high) // 2
        middle_time = keys[middle]['time_units']
        if time_units < middle_time:
            high = middle
        elif time_units > middle_time:
            low = middle
        else:
            return keys[middle]['value']
    return interpolate(keys[high - 1], keys[high], time_units)


def sample_channel(channel, time):
    if not channel['keys']:
        return None
    return sample_channel_units(channel, time_units_from_frames(time))


def wrap_angle(angle):
    while True:
        while angle > PI_AS_FLOAT32:
            angle = angle - TWO_PI_AS_FLOAT32
        if angle >= -PI_AS_FLOAT32:
            return angle
        angle = angle + TWO_PI_AS_FLOAT32


def sample_motion(motion, time):
    bones = {}
    for channel in motion['channels']:
        value = sample_channel(channel, time)
        if value is None:
            continue
        bone = bones.setdefault(channel['bone'], {'scale': [None] * 3, 'rotation': [None] * 3, 'translation': [None] * 3})
        kind = channel['kind']
        if kind in SCALE_CHANNELS:
            bone['scale'][kind - 1] = value
        elif kind in ROTATION_CHANNELS:
            bone['rotation'][kind - 4] = wrap_angle(value)
        elif kind in TRANSLATION_CHANNELS:
            bone['translation'][kind - 7] = value
    return bones


def main():
    if len(sys.argv) < 2:
        print('usage: kh1_mset.py <file.mset> [slot time]')
        return
    data = open(sys.argv[1], 'rb').read()
    offsets = motion_table_offsets(data)
    if len(sys.argv) < 4:
        for slot, start in enumerate(offsets):
            motion = read_motion(data, start)
            print(slot, 'frames', motion['frames'], 'fps', motion['fps'], 'channels', len(motion['channels']),
                  'helper channels', motion['helper_channel_count'], 'helpers', motion['helper_count'],
                  'overrides', len(motion['overrides']))
        return
    motion = read_motion(data, offsets[int(sys.argv[2])])
    for bone, values in sorted(sample_motion(motion, float(sys.argv[3])).items()):
        print(bone, values)


if __name__ == '__main__':
    main()
