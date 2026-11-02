import json
import math
import sys

import kh1_pose

TOLERANCE = 0.001
MATRIX_TOLERANCE = 0.01
POSITION_TOLERANCE = 0.05
FRAME_STEPS_TO_TRY = (0.0, -1.0, -0.5, 0.5, 1.0)
LINES_TO_SHOW = 12
CHANNEL_GROUPS = (('scale', kh1_pose.SAMPLED_SCALE), ('rotation', kh1_pose.SAMPLED_ROTATION),
                  ('translation', kh1_pose.SAMPLED_TRANSLATION))
ACCUMULATED_GROUP = ('accumulated scale', kh1_pose.SAMPLED_ACCUMULATED_SCALE)


def describe_flags(flags):
    chain_mode = (flags & kh1_pose.CHAIN_MODE_MASK) >> kh1_pose.CHAIN_MODE_SHIFT
    chain_names = {0: 'fk', 1: 'aim-one-bone', 2: 'two-bone-ik', 3: 'two-bone-ik-flipped'}
    rotation_names = {0: 'channels', 1: 'aim-helper', 2: 'copy-helper', 3: 'pole/keep'}
    words = [chain_names[chain_mode], 'rot=' + rotation_names[flags & kh1_pose.ROTATION_MODE_MASK]]
    if flags & kh1_pose.FLAG_LOCAL_SET_ON_MOTION_CHANGE:
        words.append('local-fixed')
    if flags & kh1_pose.FLAG_ROTATE_FROM_ACTOR_ROOT:
        words.append('from-root')
    if flags & kh1_pose.FLAG_KEEP_POSITION_FROM_EARLIER:
        words.append('keep-pos')
    if kh1_pose.own_helper_number(flags):
        words.append('own-helper=' + str(kh1_pose.own_helper_number(flags) - 1))
    if kh1_pose.position_helper_number(flags):
        words.append('pos-helper=' + str(kh1_pose.position_helper_number(flags) - 1))
    return f'0x{flags:08X} ' + ' '.join(words)


def angle_difference(first, second):
    difference = first - second
    while difference > math.pi:
        difference -= 2 * math.pi
    while difference < -math.pi:
        difference += 2 * math.pi
    return abs(difference)


def largest_difference(first, second):
    largest = 0.0
    for index in range(16):
        largest = max(largest, abs(float(first[index]) - float(second[index])))
    return largest


def rotation_difference(first, second):
    largest = 0.0
    for row in range(3):
        for column in range(3):
            index = row * 4 + column
            largest = max(largest, abs(float(first[index]) - float(second[index])))
    return largest


def position_difference(first, second):
    total = 0.0
    for index in range(12, 15):
        total += (float(first[index]) - float(second[index])) ** 2
    return math.sqrt(total)


def actor_matrix_from_dump(dump):
    if 'instance_root_matrix' in dump:
        actor = [float(value) for value in dump['instance_root_matrix']]
        for index in (4, 5, 6, 8, 9, 10):
            actor[index] = -actor[index]
        return actor, 'instance +0x130 (y/z rows negated back)'
    if 'actor_matrix' in dump:
        return [float(value) for value in dump['actor_matrix']], 'actor +0xD0'
    return list(kh1_pose.IDENTITY_ACTOR), 'none in dump, using identity (world stage will not match a placed actor)'


def channel_mismatches(dump, ours, skipped):
    mismatches = []
    for bone in range(dump['bone_count']):
        if bone in skipped:
            continue
        for group_name, start in CHANNEL_GROUPS:
            for axis in range(3):
                game_value = float(dump['sampled_channels'][bone][start + axis])
                our_value = ours['sampled_channels'][bone][start + axis]
                if group_name == 'rotation':
                    difference = angle_difference(game_value, our_value)
                else:
                    difference = abs(game_value - our_value)
                if difference > TOLERANCE:
                    mismatches.append((bone, group_name, axis, our_value, game_value))
    return mismatches


def best_time(dump, model, motion, actor, instance_flags):
    best = None
    for step in FRAME_STEPS_TO_TRY:
        ours = kh1_pose.pose_from_data(model, motion, dump['motion_time'] + step, actor, instance_flags)
        mismatches = channel_mismatches(dump, ours, set(ours['skipped_bones']))
        if best is None or len(mismatches) < len(best[2]):
            best = (step, ours, mismatches)
    return best


def divergence_roots(differing, model):
    differing_set = set(differing)
    roots = []
    for bone in differing:
        parent = model['joints'][bone]['parent']
        if parent not in differing_set:
            roots.append(bone)
    return roots


def stage_one(step, mismatches, ours, dump):
    print(f'stage 1: sampled channels (+0x1B0 scale/rotation/translation): best time offset {step:+}, '
          f'{len(mismatches)} values differ')
    for bone, group_name, axis, our_value, game_value in mismatches[:LINES_TO_SHOW]:
        print(f'  bone {bone} {group_name}[{axis}]: ours {our_value:.5f}, game {game_value:.5f}')
    accumulated = []
    for bone in range(dump['bone_count']):
        if bone in ours['skipped_bones']:
            continue
        start = ACCUMULATED_GROUP[1]
        for axis in range(3):
            game_value = float(dump['sampled_channels'][bone][start + axis])
            if abs(game_value - ours['sampled_channels'][bone][start + axis]) > TOLERANCE:
                accumulated.append(bone)
                break
    print(f'  accumulated scale (+0x10, written by the solver): {len(accumulated)} bones differ {accumulated[:LINES_TO_SHOW]}')


def stage_two(dump, ours, model):
    flags = ours['bone_flags']
    differing = []
    for bone in range(dump['bone_count']):
        if bone in ours['skipped_bones']:
            continue
        if largest_difference(ours['local_matrices'][bone], dump['local_matrices'][bone]) > MATRIX_TOLERANCE:
            differing.append(bone)
    print(f'stage 2: local matrices (+0x1B8): {len(differing)} bones differ')
    for bone in divergence_roots(differing, model)[:LINES_TO_SHOW]:
        difference = largest_difference(ours['local_matrices'][bone], dump['local_matrices'][bone])
        print(f'  first divergence at bone {bone} (parent {model["joints"][bone]["parent"]}): {difference:.4f}  {describe_flags(flags[bone])}')
    euler_checked = 0
    euler_failed = []
    for bone in range(dump['bone_count']):
        bone_flags = flags[bone]
        plain = bone_flags & (kh1_pose.FLAG_SKIP_BONE | kh1_pose.FLAG_LOCAL_SET_ON_MOTION_CHANGE | kh1_pose.FLAG_ROTATE_FROM_ACTOR_ROOT
                              | kh1_pose.CHAIN_MODE_MASK | kh1_pose.ROTATION_MODE_MASK | kh1_pose.FLAG_KEEP_POSITION_FROM_EARLIER) == 0
        if not plain or kh1_pose.position_helper_code(bone_flags) != 0:
            continue
        channels = [float(value) for value in dump['sampled_channels'][bone]]
        rebuilt = kh1_pose.build_rotation_translation(channels[8:11], channels[12:15])
        euler_checked += 1
        if largest_difference(rebuilt, dump['local_matrices'][bone]) > MATRIX_TOLERANCE:
            euler_failed.append(bone)
    print(f'  game channels -> X-then-Y-then-Z local matrix vs game +0x1B8 (plain FK bones): '
          f'{euler_checked - len(euler_failed)} of {euler_checked} match {euler_failed[:LINES_TO_SHOW]}')


def stage_three(dump, ours, model):
    flags = ours['bone_flags']
    differing = []
    for bone in range(dump['bone_count']):
        if bone in ours['skipped_bones']:
            continue
        game_world = dump['world_matrices'][bone]
        if rotation_difference(ours['world_matrices'][bone], game_world) > MATRIX_TOLERANCE \
                or position_difference(ours['world_matrices'][bone], game_world) > POSITION_TOLERANCE:
            differing.append(bone)
    print(f'stage 3: world matrices (+0x1B4): {len(differing)} bones differ')
    for bone in divergence_roots(differing, model)[:LINES_TO_SHOW]:
        rotation_part = rotation_difference(ours['world_matrices'][bone], dump['world_matrices'][bone])
        position_part = position_difference(ours['world_matrices'][bone], dump['world_matrices'][bone])
        print(f'  first divergence at bone {bone} (parent {model["joints"][bone]["parent"]}): rotation {rotation_part:.4f}, '
              f'position {position_part:.3f}  {describe_flags(flags[bone])}')
    worst = []
    for bone in range(dump['bone_count']):
        if bone in ours['skipped_bones']:
            continue
        worst.append((position_difference(ours['world_matrices'][bone], dump['world_matrices'][bone]), bone))
    worst.sort(reverse=True)
    print('  largest position differences:', [(bone, round(distance, 3)) for distance, bone in worst[:6]])


def main():
    if len(sys.argv) < 4:
        print('usage: compare_pose.py <dump.json> <file.mset> <file.mdls>')
        return
    dump = json.load(open(sys.argv[1]))
    model = kh1_pose.read_model(sys.argv[3])
    motion = kh1_pose.read_motion(sys.argv[2], dump['motion_slot'])
    actor, actor_source = actor_matrix_from_dump(dump)
    instance_flags = int(dump.get('instance_flags', 0))
    print(f"actor {dump.get('actor')}, object id {dump.get('object_id')}, slot {dump['motion_slot']}, "
          f"time {dump['motion_time']:.3f}, {dump['bone_count']} bones, instance flags 0x{instance_flags:X}")
    print(f'actor placement: {actor_source}')
    if float(dump.get('blend_timer', 0.0)) > 0.0:
        print('warning: the actor was blending between motions (+0x170 > 0); the blend pass overwrote the pose')
    if instance_flags & (kh1_pose.INSTANCE_GROUND_IK_MASK | kh1_pose.INSTANCE_LOOK_AT_MASK):
        print('warning: ground IK or look-at bits are set; offline floor is absent and look-at is not ported')
    step, ours, mismatches = best_time(dump, model, motion, actor, instance_flags)
    print(f'bones the game never poses (flag 0x4000000): {ours["skipped_bones"]}')
    stage_one(step, mismatches, ours, dump)
    stage_two(dump, ours, model)
    stage_three(dump, ours, model)


if __name__ == '__main__':
    main()
