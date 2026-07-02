#!/usr/bin/env python3
"""
evdl-tool.py — KH1 EVDL/ARD binary <-> text roundtrip tool

Usage:
  python evdl-tool.py disasm <input.evdl|input.ard> [output.asm]
  python evdl-tool.py asm    <input.asm>            [output.evdl|output.ard]

"disasm" converts a binary EVDL or ARD file to editable assembly text.
"asm"    assembles that text back into a binary file.

The output format matches the browser editor's ASM mode, so files round-trip
without data loss.  Keep the original binary alongside the .asm file — it is
needed when reassembling (the header comment records its name).
"""

import sys
import os
import re
import struct
import threading
import json
from pathlib import Path

_LABELS_FILE = Path(__file__).parent / 'save_data_labels.json'
_SAVE_DATA_LABELS: dict[int, str] = {}
if _LABELS_FILE.exists():
    try:
        _SAVE_DATA_LABELS = {int(k, 16): v for k, v in json.loads(_LABELS_FILE.read_text()).items()}
    except Exception:
        pass

_KH1_CHAR_MAP = {
    0x00:"",0x01:" ",0x02:"{lf}",0x03:"{0x03}",0x04:"{0x04}",0x05:"{0x05}",
    0x06:"{0x06}",0x07:"{0x07}",0x08:"{0x08}",0x09:"{0x09}",0x0A:"{0x0A}",
    0x0B:"{0x0B}",0x0C:"{0x0C}",0x0D:"{0x0D}",0x0E:"{0x0E}",0x10:"{0x10}",
    0x11:"{0x11}",0x12:"{0x12}",0x13:"{0x13}",0x14:"{0x14}",0x15:"{0x15}",
    0x16:"{0x16}",0x17:"{0x17}",0x18:"{0x18}",0x19:"{0x19}",0x1A:"{0x1A}",
    0x1B:"{0x1B}",0x1C:"{0x1C}",0x1D:"{0x1D}",0x1E:"{0x1E}",0x1F:"{0x1F}",
    0x20:"—",0x21:"0",0x22:"1",0x23:"2",0x24:"3",0x25:"4",0x26:"5",0x27:"6",
    0x28:"7",0x29:"8",0x2A:"9",0x2B:"A",0x2C:"B",0x2D:"C",0x2E:"D",0x2F:"E",
    0x30:"F",0x31:"G",0x32:"H",0x33:"I",0x34:"J",0x35:"K",0x36:"L",0x37:"M",
    0x38:"N",0x39:"O",0x3A:"P",0x3B:"Q",0x3C:"R",0x3D:"S",0x3E:"T",0x3F:"U",
    0x40:"V",0x41:"W",0x42:"X",0x43:"Y",0x44:"Z",0x45:"a",0x46:"b",0x47:"c",
    0x48:"d",0x49:"e",0x4A:"f",0x4B:"g",0x4C:"h",0x4D:"i",0x4E:"j",0x4F:"k",
    0x50:"l",0x51:"m",0x52:"n",0x53:"o",0x54:"p",0x55:"q",0x56:"r",0x57:"s",
    0x58:"t",0x59:"u",0x5A:"v",0x5B:"w",0x5C:"x",0x5D:"y",0x5E:"z",0x5F:"!",
    0x60:"?",0x61:"&",0x62:"%",0x63:"+",0x64:"{-}",0x65:"{mX}",0x66:"/",
    0x67:"*",0x68:".",0x69:",",0x6A:"・",0x6B:":",0x6C:";",0x6D:"…",0x6E:"-",
    0x6F:"ー",0x70:"~",0x71:"'",0x72:"\"",0x73:"{゛b}",0x74:"(",0x75:")",
    0x76:"[",0x77:"]",0x78:"<",0x79:">",0x7A:"{0x7A}",0x7B:"{0x7B}",
    0x7C:"↑",0x7D:"↓",0x7E:"→",0x7F:"←",0x80:"●",0x81:"■",
    0x82:"{iPotion}",0x83:"{iTent}",0x84:"{iGem}",0x85:"{iAbility}",
    0x86:"{iKey}",0x87:"{iStaff}",0x88:"{iShield}",0x89:"{iRing}",
    0x8A:"{iHat}",0x8B:"{iMickey}",0x8C:"○",0x8D:"×",0x8E:"△",0x8F:"□",
    0x90:"▲",0x91:"▼",0x92:"►",0x93:"◄",
    0x94:"{iGummi1}",0x95:"{iGummi2}",0x96:"{iGummi3}",0x97:"{iGummi4}",
    0x98:"{iGummi5}",0x99:"{iGummi6}",0x9A:"{iGummi7}",0x9B:"{iGummi8}",
    0x9C:"{iGummi9}",0x9D:"{iGummi10}",
    0x9E:"{0x9E}",0x9F:"{0x9F}",0xA0:"{0xA0}",0xA1:"{0xA1}",0xA2:"{0xA2}",
    0xA3:"{0xA3}",0xA4:"{0xA4}",0xA5:"{0xA5}",0xA6:"{0xA6}",0xA7:"{0xA7}",
    0xA8:"{0xA8}",0xA9:"®",0xAA:"{0xAA}",0xAB:"{0xAB}",0xAC:"{0xAC}",
    0xAD:"{0xAD}",0xAE:"{0xAE}",0xAF:"{0xAF}",0xB0:"{0xB0}",0xB1:"{0xB1}",
    0xB2:"{0xB2}",0xB3:"{0xB3}",0xB4:"{0xB4}",0xB5:"{0xB5}",0xB6:"{0xB6}",
    0xB7:"{0xB7}",0xB8:"{0xB8}",0xB9:"{0xB9}",0xBA:"{0xBA}",0xBB:"{0xBB}",
    0xBC:"{0xBC}",0xBD:"{0xBD}",0xBE:"{0xBE}",0xBF:"{0xBF}",0xC0:"{0xC0}",
    0xC1:"{0xC1}",0xC2:"{0xC2}",0xC3:"{0xC3}",0xC4:"{III}",0xC5:"{VII}",
    0xC6:"{VIII}",0xC7:"{X}",0xC8:"Œ",0xC9:"œ",0xCA:"¡",0xCB:"¿",
    0xCC:"À",0xCD:"Á",0xCE:"Â",0xCF:"Ä",0xD0:"Ç",0xD1:"È",0xD2:"É",
    0xD3:"Ê",0xD4:"Ë",0xD5:"Ì",0xD6:"Í",0xD7:"Î",0xD8:"Ï",0xD9:"Ñ",
    0xDA:"Ò",0xDB:"Ó",0xDC:"Ô",0xDD:"Ö",0xDE:"Ù",0xDF:"Ú",0xE0:"Û",
    0xE1:"Ü",0xE2:"ß",0xE3:"à",0xE4:"á",0xE5:"â",0xE6:"ä",0xE7:"ç",
    0xE8:"è",0xE9:"é",0xEA:"ê",0xEB:"ë",0xEC:"ì",0xED:"í",0xEE:"î",
    0xEF:"ï",0xF0:"ñ",0xF1:"ò",0xF2:"ó",0xF3:"ô",0xF4:"ö",0xF5:"ù",
    0xF6:"ú",0xF7:"û",0xF8:"ü",0xF9:"°",0xFA:"{---}",0xFB:"》",0xFC:"《",
    0xFD:"{0xFD}",0xFE:"{0xFE}",0xFF:"{0xFF}",
}

_HERE = Path(__file__).parent
WORKING = _HERE / "working"

# ═══════════════════════ TABLES ═══════════════════════════
OPCODES = {
    0:'nop', 1:'alu', 2:'jmp', 3:'beqz', 4:'nop', 5:'yield',
    6:'store_reg', 7:'cmp_reg_imm', 8:'dec_reg_idx', 9:'push',
    10:'load_local', 11:'store_local', 12:'read_byte', 13:'write_byte',
    14:'read_word', 15:'write_word', 16:'read_dword', 17:'write_dword',
    18:'nop', 19:'nop', 20:'nop', 21:'push_cond',
    22:'init_call', 23:'await_call', 24:'syscall', 25:'flow_ctrl',
    26:'set_lt', 27:'set_le', 28:'set_gt', 29:'set_ge',
    30:'read_bit', 31:'write_bit',
}
VALID_OPS = set(OPCODES.keys())
ALU_OPS = {0:'add',1:'sub',2:'mul',3:'div',4:'mod',5:'negate',6:'eq',7:'gt',8:'ge',9:'lt',10:'le',11:'ne',12:'and',13:'or',14:'xor',15:'shr',16:'shl'}
ALU_BY_NAME = {v: k for k, v in ALU_OPS.items()}
OPCODE_BY_NAME = {v.lower(): k for k, v in OPCODES.items()}

SYSCALLS = {0:'Open_window',1:'Display_message',2:'Close_window',3:'Set_window_position',4:'Set_window_size',5:'Set_window_type',6:'Set_window_opening_speed',7:'Set_message_display_speed',8:'Set_wait_timer',9:'Display_register_value',10:'Set_char_ID',11:'Move_char',12:'Rotate_char',13:'Change_motion',14:'Event_occurs',15:'Event_ends',16:'Get_char_pos_X',17:'Get_char_pos_Y',18:'Get_char_pos_Z',19:'Set_char_position',20:'Wait_move_done',21:'Show_char',22:'Hide_char',23:'Show_char_shadow',24:'Hide_char_shadow',25:'Collision_on',26:'Collision_off',27:'Fade_in',28:'Fade_out',29:'White_in',30:'White_out',31:'Blur_on',32:'Blur_off',33:'Wait_message_end',34:'Play_camera_motion',35:'Set_camera_position',36:'Set_camera_focus_position',37:'Rotate_camera',38:'Set_camera_distance',39:'Set_camera_fov',40:'Get_camera_focus_X',41:'Get_camera_focus_Y',42:'Get_camera_focus_Z',43:'Get_camera_rot_X',44:'Get_camera_rot_Y',45:'Get_camera_rot_Z',46:'Get_camera_distance',47:'Get_camera_fov',48:'Start_effect',49:'Move_camera_focus',50:'Move_camera_rotation',51:'Move_camera_distance',52:'Move_camera_fov',53:'Char_jump',54:'Char_ctrl_on',55:'Char_ctrl_off',56:'Motion_ctrl_on',57:'Motion_ctrl_off',58:'Change_motion_interp',59:'Change_map',60:'Change_area',61:'Get_event_starter_ID',62:'Group_display_on',63:'Group_display_off',64:'Set_var_1',65:'Set_var_0',66:'Inc_var',67:'Dec_var',68:'Random_value',69:'Turn_char',70:'Turn_char_left',71:'Turn_char_right',72:'Add_light',73:'Light_type',74:'Light_position',75:'Light_direction',76:'Light_color',77:'Point_light_distance',78:'Spot_light_angle',79:'Remove_light',80:'Set_window_tail_type',81:'Set_window_tail_location',82:'Set_window_tail_rotation',83:'Set_window_close_speed',84:'Widescreen_on',85:'Widescreen_off',86:'Change_motion_frame',87:'Pause_motion',88:'Enter_selection_mode',89:'Wait_selection',90:'Change_char_color',91:'Restore_char_color',92:'Load_event_motion',93:'Wait_file_load',94:'Set_event_motion',95:'Set_battle_motion',96:'Hide_body_parts',97:'Show_body_parts',98:'Wait_turn_end',99:'Turn_to_position',100:'Save_crossfade_image',101:'Start_crossfade',102:'Camera_vibration',103:'Wait_motion_end',104:'Char_bg_on',105:'Char_bg_off',106:'Wait_event_camera_end',107:'Wait_message_end_ID',108:'Motion_change_no_loop',109:'Start_texture_animation',110:'Motion_change_no_loop_interp',111:'Motion_change_no_loop_frame',112:'Gauge_on',113:'Gauge_off',114:'Command_display_on',115:'Command_display_off',116:'Change_blur_alpha',117:'Change_blur_color',118:'Change_blur_width',119:'Change_blur_height',120:'Default_shadow_light_on',121:'Default_shadow_light_off',122:'Change_char_scale',123:'Play_partial_motion',124:'Play_voice',125:'Stop_voice',126:'Trigger_event',127:'Get_world_number',128:'Get_area_number',129:'Get_set_number',130:'Change_map_whiteout',131:'Change_area_whiteout',132:'Set_attribute_on',133:'Set_attribute_off',134:'Write_set_number',135:'Keyhole_fade_out',136:'Event_SRAM_flag_on',137:'Event_SRAM_flag_off',138:'Get_event_SRAM_flag',139:'Widescreen_on_quick',140:'Widescreen_off_quick',141:'Weapon_display_on',142:'Weapon_display_off',143:'Stage_destruction_effect',144:'Check_map_jump_press',145:'Check_map_jump_motion',146:'Check_map_landing',147:'Play_camera_motion_local',148:'Play_camera_motion_local_rot',149:'Force_quit_script',150:'All_char_ctrl_on',151:'All_char_ctrl_off',152:'Check_char_on_stage',153:'Change_window_coords',154:'Restore_camera',155:'Add_bg_light',156:'Restore_camera_default',157:'Move_noturn',158:'Set_valid_key_input',159:'Clear_valid_key_input',160:'Switch_to_battle_mode',161:'Switch_to_normal_mode',162:'Clear_event_effect',163:'Start_resident_effect',164:'Clear_resident_effect',165:'Load_event_effect',166:'Wait_event_effect_load',167:'Change_resident_effect_coords',168:'Blur_on2',169:'Blur_off2',170:'Blur_type',171:'Blur_distance',172:'Get_pad_buttons',173:'Get_pad_trigger',174:'Play_camera_motion_local_rot_2actors',175:'Face_actor',176:'Pauseflag_off',177:'Open_window_no_close',178:'Activate_title_effect',179:'Start_talk_camera',180:'End_talk_camera',181:'Load_model',182:'Wait_model_load',183:'Display_model',184:'Rotate_blur',185:'Move_blur',186:'Clear_loaded_effect_ID',187:'Clear_resident_effect_ID',188:'Set_loaded_effect_location',189:'Set_loaded_effect_location_bone',190:'Play_SE',191:'Stop_SE',192:'Get_distance_2axis',193:'Get_distance_3axis',194:'Get_actor_distance_2axis',195:'Get_actor_distance_3axis',196:'Set_resident_effect_location_bone',197:'Get_current_command',198:'Set_command_speak_range',199:'Set_command_check_range',200:'Enable_menu_display',201:'Disable_menu_display',202:'Get_angle_actor_to_coord',203:'Get_angle_between_actors',204:'Fade_image_in',205:'Fade_image_out',206:'Set_image_offset',207:'Set_image_scale',208:'Set_camera_speed',209:'Set_motion_speed',210:'Set_effect_speed',211:'Set_object_far_clip',212:'Pause_actor',213:'Resume_actor',214:'Backload_test_event_motion',215:'Set_frame_color',216:'Start_frame_coloring',217:'Stop_frame_coloring',218:'Turn_head_angle',219:'Turn_head_coords',220:'Turn_head_actor',221:'Restore_head',222:'Open_shop_buy',223:'Wait_shop_close',224:'Move_jump',225:'Display_record',226:'Hide_record',227:'Show_timer',228:'Hide_timer',229:'Start_timer_up',230:'Start_timer_down',231:'Pause_timer',232:'Restart_timer',233:'Stop_timer',234:'Set_max_counter',235:'Inc_counter',236:'Show_counter',237:'Hide_counter',238:'Start_minigame',239:'End_minigame',240:'Show_ranking',241:'Start_hercules_event',242:'Reset_timer',243:'Message_to_battle_script',244:'Load_image',245:'Wait_image_load',246:'Display_image',247:'Hide_image',248:'Scroll_image_Y',249:'Load_BGM',250:'Wait_BGM_load',251:'Play_BGM',252:'Restore_BGM',253:'Check_bag_item_count',254:'Set_loaded_effect_start_frame',255:'Set_resident_effect_start_frame',256:'Load_voice',257:'Wait_voice_load',258:'Change_bag_items',259:'Check_char_in_area',260:'Start_vibration',261:'Stop_vibration',262:'Clipping_on',263:'Clipping_off',264:'Set_motion_null_to_char_pos',265:'Set_char_run_speed',266:'Reset_char_run_speed',267:'Change_char_weight',268:'Open_shop_sell',269:'Add_party_member',270:'Remove_party_member',271:'Get_motion_null_X',272:'Get_motion_null_Y',273:'Get_motion_null_Z',274:'Go_to_world_map',275:'Hercules_win_menu',276:'Hercules_lose_menu',277:'Hercules_champion_menu',278:'Game_over',279:'Quick_save',280:'Move_slow',281:'Get_part_from_party',282:'Display_black_image',283:'Display_new_record',284:'Push_actor_coord_X',285:'Push_actor_coord_Y',286:'Push_actor_coord_Z',287:'Push_actor_rotation',288:'Push_runlevel',289:'Push_motion_frames',290:'Push_actor_coord_X2',291:'Push_actor_coord_Y2',292:'Push_actor_coord_Z2',293:'Push_actor_rotation2',294:'Push_runlevel2',295:'Push_motion_frames2',296:'Fade_in_image_black_bg',297:'Fade_out_image_black_bg',298:'Cancel_movement',299:'Move_to_actor_pos',300:'Enable_game_over',301:'Disable_game_over',302:'Keyhole_fade_in',303:'End_keyhole_fade',304:'Set_sky_initial_rotation',305:'Get_minigame_menu_selection',306:'Set_char_initial_state',307:'Call_sin',308:'Call_cos',309:'Check_char_in_camera',310:'Check_battle_or_normal_mode',311:'Get_camera_viewpoint_X',312:'Get_camera_viewpoint_Y',313:'Get_camera_viewpoint_Z',314:'Get_attack_type_ID',315:'Erase_all_map_objects',316:'Show_all_map_objects',317:'Fade_in_3D',318:'Fade_out_3D',319:'Discard_object_data',320:'Enable_targeting',321:'Disable_targeting',322:'Get_motion_number',323:'Add_HP',324:'Add_MP',325:'Wait_all_enemies_defeated',326:'Enable_magic_command',327:'Disable_magic_command',328:'Enable_item_command',329:'Disable_item_command',330:'Enable_summon_command',331:'Disable_summon_command',332:'Set_counter_value',333:'Get_holdable_count',334:'Check_first_person_view',335:'Make_not_invincible',336:'Make_invincible',337:'Make_pressable',338:'Make_non_pressable',339:'Set_treasure_flag',340:'Get_treasure_flag',341:'Get_treasure_number',342:'Get_treasure_type',343:'Get_treasure_value',344:'Erase_treasure',345:'Get_treasure_ID',346:'Enemy_ctrl_on',347:'Enemy_ctrl_off',348:'Activate_battle_effects',349:'Set_battle_effect_to_bone',350:'Set_party',351:'Move_smooth_rot',352:'Change_game_speed',353:'Play_SE2',354:'Set_little_mermaid_water_speed',355:'Get_comm_ID',356:'Get_comm_Num',357:'Set_comm_work',358:'Display_item_acquired_message',359:'Display_money_acquired_message',360:'Disable_battle_event_box',361:'Enable_battle_event_box',362:'Disable_all_battle_event_boxes',363:'Enable_all_battle_event_boxes',364:'Set_item_number_in_message',365:'Set_window_width_auto',366:'Get_party_count',367:'Display_prize',368:'Hide_prize',369:'Delete_prize',370:'Return_to_title',371:'Change_effect_rotation',372:'Change_effect_scale',373:'Change_resident_effect_rotation',374:'Change_resident_effect_scale',375:'Make_not_invincible_actor',376:'Make_invincible_actor',377:'Make_inoperable',378:'Make_operable',379:'Get_char_current_area',380:'End_effect_loop',381:'End_resident_effect_loop',382:'Add_event_box',383:'Count_objects_by_part',384:'Load_event_SE',385:'Wait_event_SE_load',386:'Delete_event_box',387:'Get_char_HP',388:'Get_char_MP',389:'Write_set_number_from_table',390:'Start_BGSE',391:'Stop_BGSE',392:'Call_name_input',393:'Get_char_weight',394:'Hold_camera_info',395:'Get_camera_info',396:'Fisheye_on',397:'Fisheye_off',398:'Map_display_on',399:'Map_display_off',400:'Set_camera_parameters',401:'Reset_camera_parameters',402:'Stealth_on',403:'Stealth_off',404:'Get_motion_number_actor',405:'Load_waveform',406:'Wait_waveform_load',407:'Party_gauge_on',408:'Party_gauge_off',409:'Restore_SE',410:'Wait_restore_music',411:'Get_ground_color_from_area',412:'Set_ground_color_to_polygon',413:'Quick_save_on',414:'Quick_save_off',415:'Stop_BGM',416:'Add_battle_item',417:'Pad_ctrl_on',418:'Pad_ctrl_off',419:'GetLength_2',420:'GetLength3_2',421:'GetLengthA_2',422:'GetLength3A_2',423:'Char_request_on',424:'Char_request_off',425:'Stop_SE_all',426:'Erase_all_enemies',427:'Change_BGM_volume',428:'Add_MP_charge',429:'MP_charge_on',430:'MP_charge_off',431:'Motion_sound_on',432:'Motion_sound_off',433:'Ground_sound_on',434:'Ground_sound_off',435:'Play_effect_sound',436:'Stop_effect_sound',437:'Show_object_from_CALLNUM',438:'Check_Sora_on_ground',439:'Get_enemies_killed',440:'Reset_enemies_killed',441:'Disable_battle_mode_entry',442:'Enable_battle_mode_entry',443:'Wait_voice_finish',444:'Increase_money',445:'Load_next_map_texture',446:'Set_effect_rotation_from_bone',447:'Set_effect_rotation_from_bone2',448:'Enemy_view_off',449:'Enemy_view_on',450:'Load_all_objects_CALLNUM',451:'Wait_all_objects_CALLNUM',452:'Get_MAPOBJ_BG_color',453:'Get_distance_to_nearest_enemy',454:'Set_special_command',455:'Get_special_command_count',456:'Display_defeated_enemy_count',457:'Get_enemies_in_zone',458:'Load_magic',459:'Wait_magic_load',460:'Get_magic_level',461:'Load_all_objects_zone',462:'Wait_zone_load',463:'Set_special_thread_return',464:'Move_jump_frame',465:'Change_hercules_ranking',466:'Enable_accel_zone',467:'Disable_accel_zone',468:'Slider_ctrl_on',469:'Slider_ctrl_off',470:'Init_battle_script',471:'Init_all_enemy_battle_scripts',472:'Get_attack_type_received',473:'Get_map_object_damage',474:'Get_battle_count',475:'Set_message_numerical_work',476:'Enable_event_skipping',477:'Disable_event_skipping',478:'Release_object_CALLNUM',479:'Set_growth_type_1',480:'Set_growth_type_2',481:'Change_sora_parameters',482:'Set_magic_minus_flag',483:'Set_item_minus_flag',484:'Set_special_minus_flag',485:'Change_weapon',486:'Force_event_pose',487:'Force_no_event_pose',488:'Open_gummy_menu',489:'Start_movie',490:'Wait_movie_end',491:'Write_other_world_set_number',492:'Clear_history',493:'Set_save_point_flag',494:'Get_save_point_flag',495:'Delete_save_point',496:'Start_map_change',497:'Wait_name_input',498:'Add_party_menu_command',499:'Set_polygon_attribute',500:'Set_polygon_kind',501:'Set_polygon_ground',502:'Get_time_since_start',503:'Learn_magic',504:'Change_song_bank',505:'Wait_music_jump',506:'Change_track_volume',507:'Sky2_display_on',508:'Sky2_display_off',509:'Change_FOG',510:'Set_FOG_default',511:'Enter_event_mode',512:'Exit_event_mode',513:'Event_camera_on',514:'Event_camera_off',515:'MOVE_NOTURN',516:'ROT',517:'Check_map_changeable',518:'Add_char_to_dictionary',519:'Check_char_in_dictionary',520:'Add_dalmatian',521:'Check_dalmatian',522:'Update_minigame_record',523:'Get_minigame_record',524:'Set_story_flag',525:'Get_story_flag',526:'Add_anthem_report',527:'Check_anthem_report',528:'Open_party_menu',529:'Remove_char_from_dictionary',530:'Remove_story_flag',531:'Update_minigame_record_100kills',532:'Change_camera_sora_distance',533:'Get_camera_sora_distance',534:'Set_battle_message_return',535:'Play_OBJ_effect',536:'Change_OBJ_effect_scale',537:'Change_OBJ_effect_coords',538:'Erase_OBJ_effect',539:'Underwater_camera_on',540:'Underwater_camera_off',541:'Get_char_action',542:'Fade_out_MAP_group',543:'Fade_in_MAP_group',544:'Load_world_map_char',545:'Wait_world_map_char_load',546:'Open_world_map_window',547:'Close_world_map_window',548:'Set_world_map_char',549:'Set_world_map_char_motion',550:'Set_world_map_char_texture_animation',551:'Display_world_map_message',554:'Scatter_map_gimmick_prizes',555:'Check_coconuts_erasable',556:'Feel_icon_on',557:'Feel_icon_off',559:'Acquire_ability',560:'Set_gummy_name_message',561:'Set_ability_name_message',562:'Set_magic_name_message',563:'Set_summon_name_message',564:'Enable_limit_technique',565:'Disable_limit_technique',566:'Load_BGM_motion_bank2',567:'Load_wave_motion_bank2',568:'Learn_summon',569:'Summon_end_command',570:'Add_gummy',571:'Restore_HP_MP',572:'Wait_limit_skill_end',573:'Wait_summon_end',575:'Wait_SE_finish',576:'Wait_battle_icon_display',577:'Wait_restore_SE',578:'Transfer_object_SE',579:'Wait_object_SE_transfer',580:'Clear_object_SE',581:'Play_effect_bound_bone',582:'Check_save_menu_opened',583:'Get_item_from_gift_table',584:'Movie_standby',585:'Wait_movie_standby',586:'Set_game_clear_flag',587:'Get_game_clear_flag',588:'Display_gauge_fadein',589:'Remove_gauge_fadeout',590:'Display_command_fadein',591:'Remove_command_fadeout',592:'Remove_invincibility',593:'Make_party_invincible',594:'Set_world_map_flag',595:'Get_world_map_flag',596:'Read_set_number',597:'Start_map_effect',598:'Change_map_effect_pos',599:'Change_map_effect_rot',600:'Change_map_effect_scale',601:'Clear_map_effect',602:'Change_map_effect_start_frame',603:'End_map_effect_loop',604:'Bind_map_effect_to_bone',605:'Display_message_from_gift_table',606:'Change_char_color_from_map_table',607:'Load_all_enemy_SE',608:'Play_object_effect_once',609:'Start_weapon_effect',610:'Clear_weapon_effect',611:'Change_permanent_effect_color',612:'Start_map_change_rewrite_set',613:'Get_char_level',614:'Get_BG_color_R',615:'Get_BG_color_G',616:'Get_BG_color_B',617:'Set_object_BG_color',618:'Extract_set_BG_color',619:'Bind_effect_to_null',620:'Erase_weak_enemies',621:'Enable_blur_no_update',622:'Check_object_touching_zone',623:'Widescreen_on_frame',624:'Widescreen_off_frame',625:'Set_special_command_range',626:'Change_appear_flag',628:'Gummy_shop_buy',629:'Gummy_shop_sell',633:'Set_hercules_victory_flag',634:'Get_hercules_victory_flag',635:'Set_magic_name_message_multi',636:'Change_char_action',637:'Play_effect_bound_bone2',638:'Get_dalmatians_collected',639:'Show_feel_icon',640:'Hide_feel_icon',641:'Speed_fix_MOVE_NOTURN',642:'Load_BGM_on_map_change',643:'No_BGM_load_on_map_change',644:'Get_item_type',645:'Get_owned_money',646:'Wait_hercules_ranking_close',647:'Play_battle_voice',648:'Enable_gummies_in_item_menu',649:'Get_counter_value',650:'Get_timer_value',651:'Restore_music_fadein',652:'Play_music_fadein',654:'Apply_effect_to_bone_pos',655:'Rotate_effect_to_bone_angle',656:'WorldMap_test',657:'Load_weapon',658:'Wait_weapon_load',659:'Fade_out_SE',660:'Show_minigame_info',661:'Hide_minigame_info',662:'End_DH_stage_destruction',673:'Synthesis_shop_menu_open',678:'Minigame_limit_on',679:'Minigame_limit_off',680:'Cancel_ignore_sound',681:'Set_jiminy_memo_flag',682:'Get_jiminy_memo_flag',683:'Equip_weapon',684:'Equip_accessory',685:'Equip_ability',689:'Get_enemies_killed2',690:'Get_enemies_killed_all',692:'Get_hercules_team',693:'Get_hercules_ranking',695:'Scale_window_from_gift',696:'Push_actor_HP',697:'Push_actor_MP',698:'Play_effect_bound_bone3',699:'Play_effect_bound_bone4',700:'Enable_flight',701:'Disable_flight',702:'Enable_polygon_touch_event',703:'Disable_polygon_touch_event',704:'Get_MAPOBJ_BG_color_frames',705:'Extract_set_BG_color_frames',706:'Apply_effect_to_bone_pos2',707:'Rotate_effect_to_bone_angle2',708:'Wait_button_press',709:'Gummi_ship_event_message',710:'Stop_all_enemy_scripts',711:'Run_all_enemy_scripts',712:'Gummi_ship_tutorial',713:'Get_sora_gameover_motion',714:'Load_system_music',715:'Wait_system_music_load',716:'Load_nightmare_effects',717:'Wait_nightmare_effects_load',718:'Get_equipped_weapon',719:'Disable_battle_field_music_switch',720:'Enable_battle_field_music_switch',721:'BeEvSetStickVal',722:'Check_weapon_displayed',723:'Slow_wait',724:'Load_system_music2',725:'Restore_BGM2',726:'Restore_music_fadein2',727:'Set_shadow_steal_flag',728:'Get_synthesiser_progress',729:'Set_BG_color_to_drawing',730:'Stop_SE_3D',731:'Color_change_no_invalidate_floor',732:'Disable_ability',733:'Unlock_ability_disable',734:'Load_map_team_effect',735:'Fill_gummy_parts',736:'BeEvCheckWait',737:'Get_pad_buttons2',738:'Show_party_weapons',739:'Hide_party_weapons',740:'Change_raft_name_highwind',741:'Message_full_gummy_set',742:'Get_player_continues_entering_map',743:'Set_minigame_played_flag',744:'Check_shared_ability_taken',745:'WmEvCheckObjMotion',746:'Get_treasure_chest_full_flag',747:'Check_bag_item_count_only',748:'Enemy_bg_impact_on',749:'Enemy_bg_impact_off',750:'WmEvStartWinTexAnime2',751:'Show_battle_counter_ending',752:'Check_bag_item_count2',753:'Get_window_X',754:'Get_window_Y',755:'Check_expert_mode',756:'White_in_3D',757:'White_out_3D',758:'Check_easy_mode',759:'Set_event_skip_flag',760:'Get_event_skip_flag',761:'Open_event_skip_menu',762:'Get_event_skip_menu_selection',763:'Get_jiminy_memo_complete'}
SYSCALL_BY_NAME = {v.lower(): k for k, v in SYSCALLS.items()}

# ═══════════════════════ BINARY HELPERS ══════════════════
def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from('<I', data, offset)[0]

def sign24(v: int) -> int:
    return v if v < 0x800000 else v - 0x1000000

def enc_instr(opcode: int, operand: int) -> bytes:
    o = operand & 0xFFFFFF
    return bytes([o & 0xFF, (o >> 8) & 0xFF, (o >> 16) & 0xFF, opcode & 0xFF])

def parse_evdl_string_table(data: bytes) -> dict:
    """Parse the KH1 string table from an EVDL binary. Returns {index: decoded_text}."""
    if len(data) < 16:
        return {}
    subfile_offsets = []
    offset = 12
    while offset < len(data) - 3:
        val = int.from_bytes(data[offset:offset+4], byteorder='little')
        if val in subfile_offsets:
            break
        subfile_offsets.append(val)
        offset += 4
    if not subfile_offsets or subfile_offsets[0] >= len(data):
        return {}
    start = subfile_offsets[0]
    end = subfile_offsets[1] if len(subfile_offsets) > 1 else len(data)
    raw = data[start:end]
    if len(raw) < 4:
        return {}
    count = int.from_bytes(raw[0:4], byteorder='little')
    if count > 10000:
        return {}
    strings = {}
    pos = 4
    for i in range(count):
        if pos >= len(raw):
            break
        start_pos = pos
        while pos < len(raw):
            b = raw[pos]
            if b == 0x04 or b == 0x00:
                break
            elif b in (0x05, 0x06, 0x07):
                pos += 3
            elif b == 0x0B:
                pos += 4
            elif b == 0x0A:
                next_b = raw[pos + 1] if pos + 1 < len(raw) else 0x00
                pos += 2 if next_b != 0x00 else 4
            elif b == 0x0D:
                pos += 4
            elif 0x09 <= b <= 0x1F:
                pos += 2
            else:
                pos += 1
        chunk = raw[start_pos:pos]
        text = ''.join(_KH1_CHAR_MAP.get(b, f'{{0x{b:02X}}}') for b in chunk)
        strings[i] = text
        pos += 1
    return strings

# ═══════════════════════ KGR PARSER ══════════════════════
def trim_stream(data: bytes, start: int, max_bytes=None) -> bytes:
    raw = data[start : start + max_bytes] if max_bytes is not None else data[start:]
    n = len(raw) // 4
    fi = None
    for i in range(n):
        if raw[i*4+3] not in VALID_OPS:
            fi = i; break
    if fi is not None:
        e = fi
        while e > 0 and raw[(e-1)*4] == 0 and raw[(e-1)*4+1] == 0 and raw[(e-1)*4+2] == 0 and raw[(e-1)*4+3] == 0:
            e -= 1
        return raw[:e*4]
    last = 0
    for i in range(n):
        if raw[i*4] or raw[i*4+1] or raw[i*4+2] or raw[i*4+3]:
            last = i
    return raw[:(last+1)*4]

def find_kgrs(data: bytes) -> list:
    positions = []
    for i in range(len(data) - 4):
        if data[i] == 0x4B and data[i+1] == 0x47 and data[i+2] == 0x52 and data[i+3] == 0:
            positions.append(i)
    result = []
    for idx, p in enumerate(positions):
        np = positions[idx+1] if idx+1 < len(positions) else len(data)
        mb = np - (p + 13)
        try:
            s = trim_stream(data, p + 13, mb)
            if not s: continue
            n = min(len(s) // 4, 200)
            valid = sum(1 for j in range(n) if s[j*4+3] in VALID_OPS)
            if valid < n * 0.8: continue
            result.append({
                'kgr_offset': p,
                'unk0': u32(data, p+4),
                'unk1': u32(data, p+8),
                'nn_scripts': data[p+12],
                'stream_abs': p + 13,
                'stream': bytearray(s),
                'orig_stream': bytearray(s),
                'ard_section': None,
            })
        except Exception:
            pass
    return result

def parse_evdl(data: bytes) -> list:
    k = find_kgrs(data)
    if not k:
        raise ValueError('No valid KGR sections found')
    return k

def parse_ard(data: bytes) -> list:
    ns = u32(data, 0)
    if ns != 32:
        raise ValueError(f'Expected 32 sections, got {ns}')
    offs = [u32(data, 8 + i*4) for i in range(ns)]
    result = []
    for si in range(ns):
        ss = offs[si]
        if not ss or ss >= len(data) - 4: continue
        nn = u32(data, ss)
        if nn < 4 or nn > 10: continue
        ev_rel = u32(data, ss + 4 + 3*4)
        ev_base = ss + ev_rel
        if ev_base + 16 >= len(data): continue
        try:
            n0 = u32(data, ev_base)
            n1 = u32(data, ev_base + 4)
            n2 = u32(data, ev_base + 8)
            if not n2 or n2 > 100: continue
            kt = ev_base + 16 + (n0 + n1) * 4
            se = len(data)
            for j in range(si+1, ns):
                if offs[j] > ss: se = offs[j]; break
            for i in range(n2):
                kr = u32(data, kt + i*4)
                ka = ev_base + kr
                if data[ka] != 0x4B or data[ka+1] != 0x47 or data[ka+2] != 0x52 or data[ka+3] != 0: continue
                mb = (ev_base + u32(data, kt + (i+1)*4)) - (ka + 13) if i+1 < n2 else se - (ka + 13)
                if mb <= 0: continue
                try:
                    s = trim_stream(data, ka + 13, mb)
                    if not s: continue
                    n = min(len(s) // 4, 200)
                    valid = sum(1 for j in range(n) if s[j*4+3] in VALID_OPS)
                    if valid < n * 0.8: continue
                    result.append({
                        'kgr_offset': ka,
                        'ard_section': si,
                        'unk0': u32(data, ka+4),
                        'unk1': u32(data, ka+8),
                        'nn_scripts': data[ka+12],
                        'stream_abs': ka + 13,
                        'stream': bytearray(s),
                        'orig_stream': bytearray(s),
                    })
                except Exception:
                    pass
        except Exception:
            pass
    if not result:
        raise ValueError('No valid KGR sections found in ARD')
    return result

# ═══════════════════════ DECOMPILER ══════════════════════
def mem_op(iv: int):
    h = format(iv, 'X')
    lbl = _SAVE_DATA_LABELS.get(iv, '')
    sfx = f'  ({lbl})' if lbl else ''
    if iv < 0x800:   return f'[0x{h}]', f'save_data[0x{h}]{sfx}'
    if iv < 0x900:   return f'[0x{h}]', f'save_data[0x{h}]{sfx}'
    if iv < 0xB00:   return f'[0x{h}]', f'runtime?[0x{h}]{sfx}'
    if iv < 0xC80:
        p = format(iv - 0x200, 'X')
        return (f'[0x{h}]', f'save_data[0x{p}]{sfx}') if lbl else (f'[0x{h}]', f'save_data[0x{p}]  (alias, unsigned)')
    if iv < 0xD40:   return f'[0x{h}]', f'runtime?[0x{h}]{sfx}'
    p = format(iv - 0xD40, 'X')
    return f'[0x{h}]', f'save_data2[0x{p}]{sfx}'

def is_sh(pc: int, oc: int, iv: int, prev) -> bool:
    if oc != 0 or iv < 1 or iv > 256: return False
    return pc == 0 or prev in (5, 2, 3, 23)

def fmt_stream(stream: bytes, abs_off: int, label: str, src_name: str = '', kgr_idx: int = 0, str_lookup: dict = None) -> str:
    lines = []
    SEP = '; ' + '─' * 72
    n = len(stream) // 4
    lines += [SEP, f'; KGR  {label}', f'; Stream @ 0x{abs_off:X}  ({n} instructions)', SEP, '']

    lbl_prefix = (src_name + '.asm').replace('.', '_')

    # Blob pre-pass
    skip_pcs = {}
    skip_set = set()
    p2 = 0
    while p2 < n:
        oc = stream[p2*4+3]
        if oc not in VALID_OPS:
            bs = p2
            bb = bytearray()
            while p2 < n and stream[p2*4+3] not in VALID_OPS:
                bb.extend(stream[p2*4:p2*4+4])
                skip_set.add(p2)
                p2 += 1
            while bb and bb[-1] == 0:
                bb.pop()
            try:
                lbl = f"db  '{bb.decode('latin-1')}'"
            except Exception:
                lbl = 'db  ' + bb.hex()
            skip_pcs[bs] = lbl
        else:
            p2 += 1

    # Pre-pass: find push PCs immediately followed by syscall 1 (Display_message)
    display_msg_pushes = {}  # {push_pc: msg_id}
    if str_lookup:
        for _i in range(n - 1):
            if stream[_i*4+3] == 9 and stream[(_i+1)*4+3] == 24:
                _iv_next = stream[(_i+1)*4] | (stream[(_i+1)*4+1] << 8) | (stream[(_i+1)*4+2] << 16)
                if _iv_next == 1:
                    _iv_push = stream[_i*4] | (stream[_i*4+1] << 8) | (stream[_i*4+2] << 16)
                    display_msg_pushes[_i] = _iv_push

    # Collect in-stream branch targets so we can emit @labels
    branch_targets = set()
    for i in range(n):
        oc = stream[i*4+3]
        if oc in (2, 3):
            iv = stream[i*4] | (stream[i*4+1] << 8) | (stream[i*4+2] << 16)
            t = i + sign24(iv)
            if 0 <= t < n:
                branch_targets.add(t)

    # Assign descriptive names to branch target labels
    # Labels are emitted BEFORE is_sh increments si, so simulate in the same order.
    _bt_script: dict[int, int] = {}
    _pre_si = -1
    _pre_prev = None
    for _i in range(n):
        _iv2 = stream[_i*4] | (stream[_i*4+1] << 8) | (stream[_i*4+2] << 16)
        _oc2 = stream[_i*4+3]
        if _i in branch_targets:
            _bt_script[_i] = max(_pre_si, 0)
        if is_sh(_i, _oc2, _iv2, _pre_prev):
            _pre_si += 1
        _pre_prev = _oc2
    _scr_ctr: dict[int, int] = {}
    label_names: dict[int, str] = {}
    for _pc in sorted(branch_targets):
        _s = _bt_script.get(_pc, 0)
        _asc = _scr_ctr.get(_s, 0)
        _scr_ctr[_s] = _asc + 1
        label_names[_pc] = f'{lbl_prefix}_KGR_{kgr_idx}_SCRIPT_{_s}_{_asc}'

    # Build subscript map for init_call/await_call annotations
    sub_script_map = {}
    sh_count = -1
    prev_oc2 = None
    for i in range(n):
        iv2 = stream[i*4] | (stream[i*4+1] << 8) | (stream[i*4+2] << 16)
        oc2 = stream[i*4+3]
        if is_sh(i, oc2, iv2, prev_oc2):
            sh_count += 1
            sub_script_map[sh_count] = {'script_num': sh_count, 'char_id': None, 'pc': i}
        if oc2 == 24 and iv2 == 10 and i > 0 and sh_count >= 0 and not sub_script_map[sh_count].get('char_id'):
            piv = stream[(i-1)*4] | (stream[(i-1)*4+1] << 8) | (stream[(i-1)*4+2] << 16)
            poc = stream[(i-1)*4+3]
            if poc == 9:
                sub_script_map[sh_count]['char_id'] = f'0x{piv:X}'
        prev_oc2 = oc2

    prev_oc = None
    si = -1
    for pc in range(n):
        b = stream[pc*4:pc*4+4]
        iv = b[0] | (b[1] << 8) | (b[2] << 16)
        oc = b[3]
        hx = b.hex().upper()

        if pc in skip_pcs:
            lines.append(f'  {"":8}  ; {skip_pcs[pc]}')
            prev_oc = None
            continue
        if pc in skip_set:
            continue

        if pc in branch_targets:
            lines.append(f'@{label_names[pc]}:')

        if pc in display_msg_pushes:
            msg_text = str_lookup.get(display_msg_pushes[pc], None)
            if msg_text is not None:
                msg_lines = msg_text.split('{lf}')
                lines.append(f'; Message: {msg_lines[0]}')
                for ml in msg_lines[1:]:
                    lines.append(f';          {ml}')

        if is_sh(pc, oc, iv, prev_oc):
            si += 1
            lines += ['', f'; {"─"*72}',
                      f'; Script {si}  |  {iv} subscript(s)  |  PC {pc}  |  file 0x{abs_off + pc*4:X}  |  KGR {kgr_idx}',
                      f'; {"─"*72}', '']
            prev_oc = oc
            continue

        opname = OPCODES.get(oc, f'OP_{oc:02X}')
        ostr = ''
        cmt = ''

        if oc == 1:
            ostr = ALU_OPS.get(iv, f'sub_{iv}')
        elif oc in (2, 3):
            s = sign24(iv)
            t = pc + s
            if t in branch_targets:
                ostr = f'@{label_names[t]}'
                cmt = f'→ PC {t}'
                hx = '????????'
            else:
                ostr = f'{s:+}' if s >= 0 else str(s)
                cmt = f'→ PC {t}'
        elif oc == 24:
            ostr = str(iv)
            cmt = SYSCALLS.get(iv, '')
        elif oc in (12, 13, 14, 15, 16, 17, 30, 31):
            ostr, cmt = mem_op(iv)
        elif oc in (10, 11):
            ostr = f'[{iv}]'
        elif oc == 9:
            ostr = f'0x{iv:X}'
            if iv > 9: cmt = str(iv)
        elif oc in (22, 23):
            ostr = f'0x{iv:X}'
            tgt = sub_script_map.get(iv)
            if tgt:
                cmt = f'→ Script {tgt["script_num"]}'
                if tgt.get('char_id'): cmt += f' ({tgt["char_id"]})'
                cmt += f'  PC {tgt["pc"]}'
            else:
                cmt = f'→ Script {iv} (outside KGR)'
        else:
            ostr = f'0x{iv:X}' if iv else ''

        cs = f'  ; {cmt}' if cmt else ''
        lines.append(f'  {hx}  {opname:<14}  {ostr:<16}{cs}')
        prev_oc = oc

    lines.append('')
    return '\n'.join(lines)

def decomp_kgr(k: dict, idx: int, total: int, src: str, str_lookup: dict = None) -> str:
    label = f'{src}  KGR@0x{k["kgr_offset"]:X}  NN={k["nn_scripts"]}'
    t = ''
    if total > 1:
        t += f'\n\n{"#"*76}\n# KGR[{idx}]'
        if k.get('ard_section') is not None:
            t += f'  section={k["ard_section"]}'
        t += f'  KGR@0x{k["kgr_offset"]:X}  stream@0x{k["stream_abs"]:X}\n{"#"*76}\n'
    t += fmt_stream(k['stream'], k['stream_abs'], label, src, idx, str_lookup)
    return t

# ═══════════════════════ ASSEMBLER ═══════════════════════
PH_RE = re.compile(r'^[?Xx]{8}$')
INSTR_RE = re.compile(r'^\s*(?:\[\s*(?:\d+|new|-|\*)\s*\]\s+)?([0-9A-Fa-f?]{8})\s*(.*)')
LABEL_RE = re.compile(r'^\s*@(\w+)\s*:\s*$')
DB_RE = re.compile(r'^\s*(?:\[\s*(?:\d+|new|-|\*)\s*\]\s+)?;\s+db\s+(.+)$')
BAN_RE = re.compile(r'^(#{10,}|;\s*-{10,}|;\s*KGR\b|;\s*Script\b)')
SH_RE = re.compile(r';\s*Script\s+\d+\s*\|\s*(\d+)\s*subscript')

def parse_int(s: str) -> int:
    s = s.strip().rstrip(',;')
    if s.lower().startswith('0x'):
        return int(s, 16)
    try:
        return int(s, 10)
    except ValueError:
        return int(s, 16)

def enc_from_mnem(mn: str, rest: str, pc: int, label_map: dict) -> bytes:
    m = mn.lower().strip()
    rest = re.sub(r'\s*;.*$', '', rest).strip()
    a0 = (rest.split()[0] if rest.split() else '')
    if m == 'nop':
        op = 0
        try: op = parse_int(a0)
        except Exception: pass
        return enc_instr(OPCODE_BY_NAME.get(m, 0), op)
    if m == 'yield':
        op = 0
        try: op = parse_int(a0)
        except Exception: pass
        return enc_instr(5, op)
    if m == 'push':
        return enc_instr(9, parse_int(a0))
    if m == 'syscall':
        try:
            sid = parse_int(a0)
        except Exception:
            sid = SYSCALL_BY_NAME.get(a0.lower())
        if sid is None:
            raise ValueError(f'Unknown syscall: {a0}')
        return enc_instr(24, sid)
    if m == 'alu':
        sub = a0.lower()
        if sub in ALU_BY_NAME:
            return enc_instr(1, ALU_BY_NAME[sub])
        sm = re.match(r'^sub_(\d+)$', sub)
        if sm:
            return enc_instr(1, int(sm.group(1)))
        return enc_instr(1, parse_int(sub))
    if m in ('jmp', 'beqz'):
        oc = 2 if m == 'jmp' else 3
        if a0.startswith('@'):
            ln = a0[1:]
            tp = label_map.get(ln)
            if tp is None: return None
            return enc_instr(oc, (tp - pc) & 0xFFFFFF)
        return enc_instr(oc, parse_int(a0.lstrip('+')) & 0xFFFFFF)
    oc = OPCODE_BY_NAME.get(m)
    if oc is None:
        raise ValueError(f'Unknown mnemonic: {m}')
    operand = 0
    if rest:
        try:
            operand = parse_int(a0.lstrip('[').rstrip(']'))
        except Exception:
            pass
    return enc_instr(oc, operand)

def parse_asm_sec(text: str) -> list:
    lines = []
    for raw in text.splitlines():
        s = raw.strip()
        shm = SH_RE.search(s)
        if shm:
            lines.append({'kind': 'hdr', 'nn': int(shm.group(1))})
            continue
        if not s or BAN_RE.match(s) or s.startswith('#'):
            continue
        if s.startswith(';') and not s.startswith('; db'):
            continue
        lm = LABEL_RE.match(s)
        if lm:
            lines.append({'kind': 'lbl', 'name': lm.group(1)})
            continue
        dbm = DB_RE.match(raw)
        if dbm:
            lines.append({'kind': 'db', 'spec': dbm.group(1).strip()})
            continue
        im = INSTR_RE.match(raw)
        if im:
            r = im.group(2).strip()
            parts = r.split(None, 1)
            mn = parts[0] if parts else ''
            op = r[len(mn):].strip()
            op = re.sub(r'\s*;.*$', '', op).strip()
            lines.append({'kind': 'ins', 'hex': im.group(1), 'mn': mn, 'op': op})
    return lines

def asm_sec(lines: list, name: str = '') -> tuple:
    out = bytearray()
    fixups = []
    lpc = {}
    errs = []
    cur = 0
    for a in lines:
        if a['kind'] == 'lbl':
            lpc[a['name']] = cur
            continue
        if a['kind'] == 'hdr':
            out.extend(enc_instr(0, a['nn']))
            cur += 1
            continue
        if a['kind'] == 'db':
            spec = a['spec'].strip()
            if re.match(r'^[0-9A-Fa-f]+$', spec) and len(spec) % 2 == 0:
                out.extend(bytes.fromhex(spec))
            else:
                q = spec.strip("'")
                out.extend(q.encode('latin-1', errors='replace'))
            continue
        if a['kind'] == 'ins':
            if not PH_RE.match(a['hex']):
                enc = bytes.fromhex(a['hex'])
            else:
                m = a['mn'].lower()
                ops = a['op'].strip()
                ib = m in ('jmp', 'beqz')
                ilr = ops.startswith('@')
                if ib and ilr:
                    ln = ops[1:].split()[0]
                    oc = 2 if m == 'jmp' else 3
                    if ln in lpc:
                        enc = enc_instr(oc, (lpc[ln] - cur) & 0xFFFFFF)
                    else:
                        enc = enc_instr(oc, 0)
                        fixups.append({'bo': len(out), 'oc': oc, 'ln': ln, 'ip': cur})
                else:
                    try:
                        r = enc_from_mnem(a['mn'], a['op'], cur, lpc)
                        if r is None:
                            ln = ops[1:].split()[0]
                            oc = 2 if m == 'jmp' else 3
                            enc = enc_instr(oc, 0)
                            fixups.append({'bo': len(out), 'oc': oc, 'ln': ln, 'ip': cur})
                        else:
                            enc = r
                    except Exception as e:
                        errs.append(f'PC {cur} ({a["mn"]} {a["op"]}): {e}')
                        enc = b'\x00\x00\x00\x00'
            out.extend(enc)
            cur += 1
    for f in fixups:
        tp = lpc.get(f['ln'])
        if tp is None:
            errs.append(f'Undefined label: @{f["ln"]}')
            continue
        patch = enc_instr(f['oc'], (tp - f['ip']) & 0xFFFFFF)
        out[f['bo']:f['bo']+4] = patch
    return bytes(out), errs

# ═══════════════════════ REPACKER ════════════════════════
def count_scripts(stream: bytes) -> int:
    n = len(stream) // 4
    count = 0
    prev_oc = None
    for i in range(n):
        iv = stream[i*4] | (stream[i*4+1] << 8) | (stream[i*4+2] << 16)
        oc = stream[i*4+3]
        if is_sh(i, oc, iv, prev_oc):
            count += 1
        prev_oc = oc
    return count

def repack_evdl(orig: bytes, kgrs: list, new_streams: list) -> bytes:
    fk = kgrs[0]['kgr_offset']
    prefix = bytearray(orig[:fk])
    blocks = []
    for i, k in enumerate(kgrs):
        ns = new_streams[i]
        orig_s = k['orig_stream']
        changed = len(ns) != len(orig_s) or any(ns[j] != orig_s[j] for j in range(len(ns)))
        h = bytearray(orig[k['kgr_offset']:k['kgr_offset']+13])
        next_kgr = kgrs[i+1]['kgr_offset'] if i+1 < len(kgrs) else len(orig)
        orig_full = bytearray(orig[k['kgr_offset']+13:next_kgr])
        if not changed:
            c = bytearray(13 + len(orig_full))
            c[:13] = h; c[13:] = orig_full
        else:
            h[12] = count_scripts(ns)
            trailing = orig_full[len(orig_s):]
            c = bytearray(13 + len(ns) + len(trailing))
            c[:13] = h; c[13:13+len(ns)] = ns; c[13+len(ns):] = trailing
        blocks.append(bytes(c))

    noffs = []
    patched = bytearray(prefix)
    pos = len(prefix)
    for b in blocks:
        noffs.append(pos); pos += len(b)

    for i, k in enumerate(kgrs):
        oo, no = k['kgr_offset'], noffs[i]
        if oo == no: continue
        ob = struct.pack('<I', oo)
        nb = struct.pack('<I', no)
        j = 0
        while j < len(patched) - 3:
            if patched[j:j+4] == ob:
                patched[j:j+4] = nb
            j += 4

    total = len(patched) + sum(len(b) for b in blocks)
    out = bytearray(total)
    out[:len(patched)] = patched
    off = len(patched)
    for b in blocks:
        out[off:off+len(b)] = b; off += len(b)

    # For WDT files: update section pointers and the KGR offset table.
    # Detection: u32[0x00] = section count (2-16), u32[0x18] = section-2 offset,
    # section 2's u32[+8] = KGR count must match len(kgrs).
    fk = kgrs[0]['kgr_offset']
    sec_count_val = struct.unpack_from('<I', orig, 0)[0]
    if 2 <= sec_count_val <= 16 and 0x1C <= len(orig):
        sec2_off = struct.unpack_from('<I', orig, 0x18)[0]
        kgr_count_match = (sec2_off and sec2_off + 16 <= len(orig) and
                           struct.unpack_from('<I', orig, sec2_off + 8)[0] == len(kgrs))

        def _shift_at(p):
            s = 0
            for ci in range(1, len(kgrs)):
                if kgrs[ci]['kgr_offset'] <= p:
                    s = noffs[ci] - kgrs[ci]['kgr_offset']
                else:
                    break
            return s

        # 1. Section pointers at 0x10..0x24 (safe; 0x28/0x30/0x38 crash if touched).
        for si in range(sec_count_val):
            ptr_off = 0x10 + si * 4
            if ptr_off + 4 > fk:
                break
            old_ptr = struct.unpack_from('<I', orig, ptr_off)[0]
            if old_ptr >= fk and old_ptr < len(orig):
                s = _shift_at(old_ptr)
                if s:
                    struct.pack_into('<I', out, ptr_off, (old_ptr + s) & 0xFFFFFFFF)

        # 2. KGR offset table in section 2 (entries n=2..kgr_count).
        #    Formula: table[n] + base == some position in the KGR data region.
        #    Use shift_at on that position rather than a fixed formula so entries
        #    that point to kgr_header+4 (unk0) are also handled correctly.
        if kgr_count_match:
            base = sec2_off + 4
            table_off = sec2_off + 12
            kgr_count = len(kgrs)
            for n in range(2, kgr_count + 1):
                entry_off = table_off + n * 4
                if entry_off + 4 > len(out):
                    break
                orig_val = struct.unpack_from('<I', orig, entry_off)[0]
                if not orig_val:
                    continue
                s = _shift_at(orig_val + base)
                if s:
                    struct.pack_into('<I', out, entry_off, (orig_val + s) & 0xFFFFFFFF)

    return bytes(out)

def fix_ard_section_kgr_tables(data: bytearray, inserted_at: int, delta: int):
    if delta == 0: return
    ns2 = u32(data, 0)
    sec_offs = [u32(data, 8 + s*4) for s in range(ns2)]
    for si in range(ns2):
        ss = sec_offs[si]
        if not ss or ss >= len(data) - 4: continue
        if ss >= inserted_at + delta: continue  # section was shifted wholesale; relative KGR offsets unchanged
        nn = u32(data, ss)
        if nn < 1 or nn > 16: continue
        try:
            ev_rel = u32(data, ss + 4 + 3*4)
            ev_base = ss + ev_rel
            if ev_base + 16 >= len(data): continue
            n0 = u32(data, ev_base); n1 = u32(data, ev_base+4); n2 = u32(data, ev_base+8)
            if not n2 or n2 > 200: continue
            kt = ev_base + 16 + (n0 + n1) * 4
            if kt + n2*4 > len(data): continue
            for ki in range(n2):
                rel = u32(data, kt + ki*4)
                abs_pos = ev_base + rel
                if abs_pos >= inserted_at:
                    new_abs = (abs_pos + delta) & 0xFFFFFFFF
                    new_rel = (new_abs - ev_base) & 0xFFFFFFFF
                    struct.pack_into('<I', data, kt + ki*4, new_rel)
        except Exception:
            pass

def repack_ard(orig: bytes, kgrs: list, new_streams: list) -> bytes:
    data = bytearray(orig)
    for i, info in enumerate(kgrs):
        ns = new_streams[i]
        orig_len = len(info['orig_stream'])
        delta = len(ns) - orig_len
        new_nn = count_scripts(ns)
        if delta == 0:
            ia = info['stream_abs']
            data[ia:ia+orig_len] = ns
            data[info['kgr_offset']+12] = new_nn
            info['orig_stream'] = bytearray(ns)
            continue
        ia = info['stream_abs']
        nb = bytearray(len(data) + delta)
        nb[:ia+orig_len] = data[:ia+orig_len]
        nb[ia:ia+len(ns)] = ns
        nb[ia+len(ns):] = data[ia+orig_len:]
        nb[info['kgr_offset']+12] = new_nn
        ns2 = u32(nb, 0)
        for s in range(ns2):
            ov = u32(nb, 8 + s*4)
            if ov >= ia + orig_len and ov != 0:
                fv = (ov + delta) & 0xFFFFFFFF
                struct.pack_into('<I', nb, 8 + s*4, fv)
        fix_ard_section_kgr_tables(nb, ia + orig_len, delta)
        for j in range(i+1, len(kgrs)):
            if kgrs[j]['stream_abs'] >= ia + orig_len:
                kgrs[j]['stream_abs'] += delta
            if kgrs[j]['kgr_offset'] >= ia + orig_len:
                kgrs[j]['kgr_offset'] += delta
        info['orig_stream'] = bytearray(ns)
        data = nb
    return bytes(data)

# ═══════════════════════ ASM TEXT SPLITTER ═══════════════
def split_asm_text(text: str) -> list:
    # Each KGR banner is a pair of #### lines with "# KGR[N]" between them.
    # Split only at the *opening* #### of each pair to get one section per KGR.
    banner_re = re.compile(r'^#{10,}[^\n]*\n#\s*KGR\[', re.MULTILINE)
    positions = [m.start() for m in banner_re.finditer(text)]
    if not positions:
        return [text]
    sections = []
    for i, start in enumerate(positions):
        end = positions[i+1] if i+1 < len(positions) else len(text)
        sections.append(text[start:end])
    return sections or [text]

# ═══════════════════════ FILE HEADER ═════════════════════
def make_file_header(input_path: str, file_type: str, kgrs: list) -> str:
    return (
        f'; evdl-tool disassembly\n'
        f'; source: {os.path.basename(input_path)}\n'
        f'; type: {file_type}\n'
        f'; kgr_count: {len(kgrs)}\n'
        f'; --- Do not edit the lines above ---\n'
        '\n'
    )

def parse_file_header(text: str):
    file_type = None
    for line in text.splitlines():
        m = re.match(r'^;\s*type:\s*(\S+)', line)
        if m:
            file_type = m.group(1)
            break
    return {'file_type': file_type}

# ═══════════════════════ COMMANDS ════════════════════════
def die(msg: str):
    print(f'Error: {msg}', file=sys.stderr)
    sys.exit(1)

def cmd_disasm(input_path: str, output_path: str = None):
    if not os.path.exists(input_path):
        die(f'File not found: {input_path}')
    with open(input_path, 'rb') as f:
        data = f.read()
    ext = os.path.splitext(input_path)[1].lower()
    kgrs = None
    file_type = None
    # For .ard try the strict ARD parser first; for everything else try KGR scan first
    if ext == '.ard':
        try:
            kgrs = parse_ard(data)
            file_type = 'ard'
        except Exception:
            pass
    if kgrs is None:
        kgrs_found = find_kgrs(data)
        if kgrs_found:
            kgrs = kgrs_found
            file_type = 'evdl'
    if kgrs is None:
        # Last resort: try strict ARD parse and let its error surface
        try:
            kgrs = parse_ard(data)
            file_type = 'ard'
        except Exception as e:
            die(f'No KGR sections found in {os.path.basename(input_path)}: {e}')
    base_name = os.path.basename(input_path)
    str_lookup = parse_evdl_string_table(data) if file_type == 'evdl' else {}
    parts = [decomp_kgr(k, i, len(kgrs), base_name, str_lookup) for i, k in enumerate(kgrs)]
    header = make_file_header(input_path, file_type, kgrs)
    full = header + ''.join(parts)
    if not output_path:
        working_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'working')
        out_path = os.path.join(working_dir, os.path.basename(input_path) + '.asm')
    else:
        out_path = output_path
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(full)
    print(f'Disassembled {len(kgrs)} KGR section(s) → {out_path}')

def cmd_asm(input_path: str, output_path: str = None, orig_bin_override: str = None):
    if not os.path.exists(input_path):
        die(f'File not found: {input_path}')
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()
    info = parse_file_header(text)
    detected_type = info['file_type']

    if output_path:
        out_ext = os.path.splitext(output_path)[1].lower().lstrip('.') or 'evdl'
    else:
        base = re.sub(r'\.asm$', '', input_path, flags=re.IGNORECASE)
        src_ext = os.path.splitext(base)[1].lower().lstrip('.')
        if src_ext and src_ext not in ('evdl', 'ard', 'ev'):
            # Non-standard extension (e.g. .wdt, .dat) — preserve it as-is.
            output_path = base
            out_ext = src_ext
        else:
            out_ext = detected_type or src_ext or 'evdl'
            stem = re.sub(r'\.(evdl|ard|ev)$', '', base, flags=re.IGNORECASE)
            output_path = stem + '.' + out_ext

    file_type = detected_type or ('ard' if out_ext == 'ard' else 'evdl')
    sections = split_asm_text(text)
    all_errors = []
    new_streams = []
    for i, sec in enumerate(sections):
        parsed = parse_asm_sec(sec)
        stream, errors = asm_sec(parsed, f'KGR[{i}]')
        if errors:
            all_errors.extend(f'KGR[{i}] {e}' for e in errors)
        new_streams.append(stream)

    if all_errors:
        print('Assembly errors:', file=sys.stderr)
        for e in all_errors:
            print(f'  {e}', file=sys.stderr)

    # Find source binary
    orig_bin = orig_bin_override
    if not orig_bin:
        src_line = None
        for line in text.splitlines():
            m = re.match(r'^;\s*source:\s*(.+)', line)
            if m:
                src_line = m.group(1).strip()
                break

        asm_dir = os.path.dirname(os.path.abspath(input_path))
        candidates = []
        if src_line:
            candidates += [
                os.path.join(asm_dir, src_line),
                os.path.abspath(src_line),
            ]
        base_no_asm = re.sub(r'\.asm$', '', input_path, flags=re.IGNORECASE)
        if os.path.exists(base_no_asm):
            candidates.append(base_no_asm)

        for c in candidates:
            if os.path.exists(c):
                orig_bin = c
                break

    if not orig_bin:
        die(
            f'Cannot find original binary to repack into.\n'
            f'Expected "{src_line or "source file"}" next to the .asm file.\n'
            f'Usage: python evdl-tool.py asm <input.asm> [output.evdl]'
        )

    with open(orig_bin, 'rb') as f:
        orig_data = f.read()

    try:
        kgrs = parse_ard(orig_data) if file_type == 'ard' else parse_evdl(orig_data)
    except Exception as e:
        die(f'Failed to parse original binary: {e}')

    if len(new_streams) != len(kgrs):
        print(f'Warning: asm has {len(new_streams)} KGR section(s), binary has {len(kgrs)}. Using available sections.', file=sys.stderr)
        while len(new_streams) < len(kgrs):
            new_streams.append(bytes(kgrs[len(new_streams)]['stream']))

    try:
        if file_type == 'ard':
            out = repack_ard(orig_data, kgrs, new_streams)
        else:
            out = repack_evdl(orig_data, kgrs, new_streams)
    except Exception as e:
        die(f'Repack failed: {e}')

    with open(output_path, 'wb') as f:
        f.write(out)

    if all_errors:
        print(f'Assembled with {len(all_errors)} error(s) → {output_path}')
    else:
        print(f'Assembled {len(kgrs)} KGR section(s) → {output_path}')

# ═══════════════════════ GUI ═════════════════════════════

def _run_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    ASM_FT = [('EVDL ASM files', '*.evdl.asm *.asm'), ('All files', '*.*')]
    BIN_FT = [('All files', '*.*'), ('EVDL/ARD/EV files', '*.evdl *.ard *.ev')]
    asm_dir = str(WORKING)
    bin_dir = 'C:/OpenKH/OpenKHEGS/data/kh1'
    pad = dict(padx=6, pady=3)

    root = tk.Tk()
    root.title('EVDL Workshop')

    nb = ttk.Notebook(root)
    nb.pack(fill='both', expand=True, padx=4, pady=4)

    def _section(p, text, row):
        tk.Label(p, text=text, font=('TkDefaultFont', 9, 'bold'), anchor='w') \
          .grid(row=row, column=0, columnspan=3, sticky='w', padx=6, pady=(8, 0))

    def _filelist(p, row, ft, idir, height=5, width=70):
        frame = tk.Frame(p)
        frame.grid(row=row, column=0, columnspan=3, sticky='ew', padx=6)
        lb = tk.Listbox(frame, width=width, height=height, selectmode=tk.EXTENDED)
        lb.pack(side='left', fill='both', expand=True)
        sb = tk.Scrollbar(frame, orient='vertical', command=lb.yview)
        sb.pack(side='right', fill='y')
        lb.configure(yscrollcommand=sb.set)
        bf = tk.Frame(p)
        bf.grid(row=row + 1, column=0, columnspan=3, sticky='w', padx=6, pady=2)
        def _add():
            paths = filedialog.askopenfilenames(title='Add files', filetypes=ft, initialdir=idir)
            existing = set(lb.get(0, tk.END))
            for path in paths:
                if path not in existing:
                    lb.insert(tk.END, path)
        def _remove():
            for i in reversed(lb.curselection()): lb.delete(i)
        tk.Button(bf, text='Add…',   command=_add).pack(side='left', padx=2)
        tk.Button(bf, text='Remove', command=_remove).pack(side='left', padx=2)
        return lb

    def _outdir_row(p, row):
        _section(p, 'Output directory  (optional)', row)
        var = tk.StringVar()
        tk.Entry(p, textvariable=var, width=50).grid(row=row+1, column=0, columnspan=2, sticky='ew', **pad)
        def _cmd():
            d = filedialog.askdirectory(title='Select output directory', initialdir=str(_HERE))
            if d: var.set(d)
        tk.Button(p, text='Browse…', command=_cmd).grid(row=row+1, column=2, **pad)
        return var

    def _results(p, row, height=10, width=80):
        _section(p, 'Results', row)
        frame = tk.Frame(p)
        frame.grid(row=row+1, column=0, columnspan=3, sticky='ew', padx=6, pady=(0, 4))
        box = tk.Text(frame, width=width, height=height, font=('Courier', 9), state='disabled')
        box.pack(side='left', fill='both', expand=True)
        sb = tk.Scrollbar(frame, orient='vertical', command=box.yview)
        sb.pack(side='right', fill='y')
        box.configure(yscrollcommand=sb.set)
        def _append(text):
            box.configure(state='normal')
            box.insert(tk.END, text + '\n')
            box.see(tk.END)
            box.configure(state='disabled')
            root.update_idletasks()
        def _clear():
            box.configure(state='normal')
            box.delete('1.0', tk.END)
            box.configure(state='disabled')
        return _append, _clear

    def _out_dir(var):
        s = var.get().strip()
        return Path(s) if s else None

    t1 = ttk.Frame(nb)
    nb.add(t1, text='Disasm / Asm')

    _section(t1, 'Disassemble  (.evdl / .ard  →  .asm)', 0)
    dis_lb = _filelist(t1, 1, BIN_FT, bin_dir)

    _section(t1, 'Assemble  (.asm  →  .evdl / .ard)', 3)
    asm_lb = _filelist(t1, 4, ASM_FT, asm_dir)

    tk.Label(t1, text='Original binary\n(override, optional):', anchor='e', justify='right') \
      .grid(row=6, column=0, sticky='e', **pad)
    orig_bin_var = tk.StringVar()
    tk.Entry(t1, textvariable=orig_bin_var, width=50).grid(row=6, column=1, sticky='ew', **pad)
    def _browse_orig():
        p = filedialog.askopenfilename(title='Select original binary to repack into',
                                       filetypes=BIN_FT, initialdir=bin_dir)
        if p: orig_bin_var.set(p)
    tk.Button(t1, text='Browse…', command=_browse_orig).grid(row=6, column=2, **pad)

    t1_outdir_var       = _outdir_row(t1, 7)
    t1_append, t1_clear = _results(t1, 9)

    def _t1_disasm():
        files = list(dis_lb.get(0, tk.END))
        if not files: messagebox.showerror('Bad input', 'Add at least one file to disassemble.'); return
        t1_clear()
        for p in files:
            try:
                cmd_disasm(p)
                t1_append(f'OK  {Path(p).name}')
            except Exception as e:
                t1_append(f'ERR {Path(p).name}: {e}')

    def _t1_asm():
        files = list(asm_lb.get(0, tk.END))
        if not files: messagebox.showerror('Bad input', 'Add at least one .asm file to assemble.'); return
        out_dir  = _out_dir(t1_outdir_var)
        orig_bin = orig_bin_var.get().strip() or None
        t1_clear()
        for p in files:
            try:
                out_path = None
                if out_dir:
                    out_dir.mkdir(parents=True, exist_ok=True)
                    base = re.sub(r'\.asm$', '', Path(p).name, flags=re.IGNORECASE)
                    out_path = str(out_dir / base)
                cmd_asm(p, out_path, orig_bin_override=orig_bin)
                t1_append(f'OK  {Path(p).name}')
            except Exception as e:
                t1_append(f'ERR {Path(p).name}: {e}')

    t1_btns = tk.Frame(t1)
    t1_btns.grid(row=11, column=0, columnspan=3, pady=8)
    tk.Button(t1_btns, text='Disassemble', command=_t1_disasm, width=16).pack(side='left', padx=6)
    tk.Button(t1_btns, text='Assemble',    command=_t1_asm,    width=16).pack(side='left', padx=6)

    # ── Tab 2: Byte Search ────────────────────────────────────────────────────
    t2 = ttk.Frame(nb)
    nb.add(t2, text='Byte Search')

    _section(t2, 'Search directory', 0)
    srch_dir_var = tk.StringVar(value='C:/OpenKH/OpenKHEGS/data/kh1')
    tk.Entry(t2, textvariable=srch_dir_var, width=55).grid(row=1, column=0, columnspan=2, sticky='ew', **pad)
    def _browse_srch_dir():
        d = filedialog.askdirectory(title='Select directory to search', initialdir=srch_dir_var.get() or str(_HERE))
        if d: srch_dir_var.set(d)
    tk.Button(t2, text='Browse…', command=_browse_srch_dir).grid(row=1, column=2, **pad)

    _section(t2, 'Bytes to find  (hex, e.g.  4B 47 52 00)', 2)
    srch_bytes_var = tk.StringVar()
    tk.Entry(t2, textvariable=srch_bytes_var, width=55, font=('Courier', 10)).grid(row=3, column=0, columnspan=3, sticky='ew', **pad)

    _section(t2, 'File extension filter  (space-separated, e.g.  .ev .ard .bin — blank = all files)', 4)
    srch_ext_var = tk.StringVar()
    tk.Entry(t2, textvariable=srch_ext_var, width=40).grid(row=5, column=0, columnspan=2, sticky='w', **pad)

    srch_recursive_var = tk.BooleanVar(value=True)
    tk.Checkbutton(t2, text='Recursive', variable=srch_recursive_var).grid(row=5, column=2, sticky='w', **pad)

    t2_append, t2_clear = _results(t2, 6, height=14)

    _srch_running = [False]
    _srch_stop = [False]

    def _t2_search():
        if _srch_running[0]:
            return
        hex_str = re.sub(r'\s+', '', srch_bytes_var.get().strip())
        if not hex_str:
            messagebox.showerror('Bad input', 'Enter a hex byte string to search for.')
            return
        try:
            needle = bytes.fromhex(hex_str)
        except ValueError:
            messagebox.showerror('Bad input', f'Invalid hex string: {hex_str!r}')
            return
        srch_dir = srch_dir_var.get().strip()
        if not srch_dir or not os.path.isdir(srch_dir):
            messagebox.showerror('Bad input', 'Select a valid directory.')
            return
        ext_filter = {e.strip().lower() for e in srch_ext_var.get().split() if e.strip()}

        t2_clear()
        t2_append(f'Searching for  {hex_str.upper()}  in  {srch_dir} …')
        if ext_filter:
            t2_append(f'Extension filter: {" ".join(sorted(ext_filter))}')
        t2_append('')

        _srch_running[0] = True
        _srch_stop[0] = False
        srch_btn.config(state='disabled')
        stop_btn.config(state='normal')

        recursive = srch_recursive_var.get()

        def _run():
            total_files = 0
            total_hits = 0
            stopped = False
            for root_dir, dirs, files in os.walk(srch_dir):
                if _srch_stop[0]:
                    stopped = True
                    break
                dirs.sort()
                if not recursive:
                    dirs.clear()
                for fname in sorted(files):
                    if _srch_stop[0]:
                        stopped = True
                        break
                    if ext_filter:
                        if os.path.splitext(fname)[1].lower() not in ext_filter:
                            continue
                    fpath = os.path.join(root_dir, fname)
                    try:
                        with open(fpath, 'rb') as fh:
                            data = fh.read()
                    except Exception:
                        continue
                    total_files += 1
                    offsets = []
                    pos = 0
                    while True:
                        idx = data.find(needle, pos)
                        if idx == -1:
                            break
                        offsets.append(idx)
                        pos = idx + 1
                    if offsets:
                        total_hits += len(offsets)
                        rel = os.path.relpath(fpath, srch_dir)
                        root.after(0, t2_append, rel)
                if stopped:
                    break
            summary = 'Stopped' if stopped else 'Done'
            root.after(0, t2_append, f'\n{summary} — {total_hits} match(es) across {total_files} file(s) scanned.')
            _srch_running[0] = False
            root.after(0, srch_btn.config, {'state': 'normal'})
            root.after(0, stop_btn.config, {'state': 'disabled'})

        threading.Thread(target=_run, daemon=True).start()

    t2_btns = tk.Frame(t2)
    t2_btns.grid(row=8, column=0, columnspan=3, pady=8)
    srch_btn = tk.Button(t2_btns, text='Search', command=_t2_search, width=16)
    srch_btn.pack(side='left', padx=6)
    stop_btn = tk.Button(t2_btns, text='Stop', command=lambda: _srch_stop.__setitem__(0, True), width=10, state='disabled')
    stop_btn.pack(side='left', padx=6)

    root.mainloop()


# ═══════════════════════ ENTRY POINT ═════════════════════
HELP = """evdl-tool - KH1 EVDL/ARD binary <-> text roundtrip

Usage:
  python evdl-tool.py disasm <input.evdl|input.ard> [output.asm]
  python evdl-tool.py disasm <file1> <file2> ...
  python evdl-tool.py asm    <input.asm>            [output.evdl|output.ard]

Commands:
  disasm   Convert one or more binary EVDL or ARD files to editable assembly text.
           Output defaults to <input>.<ext>.asm in the working/ directory.
           When a single file is given, an explicit output path may follow it.

  asm      Assemble the text file back to binary.
           The original binary must be present next to the .asm file
           (its name is recorded in the header comment written by disasm).
           Output defaults to <source>_patched.<ext>.

Examples:
  python evdl-tool.py disasm event.evdl
      -> writes event.evdl.asm

  python evdl-tool.py disasm world.ard world.asm
      -> writes world.asm

  python evdl-tool.py asm event.evdl.asm
      -> writes event_patched.evdl  (requires event.evdl alongside)

  python evdl-tool.py asm event.evdl.asm patched.evdl
      -> writes patched.evdl
"""

def _tk_pick_file(title: str, filetypes: list, initial_dir: str = None, multiple: bool = False):
    """Open a Tkinter file-open dialog. Returns a list of paths if multiple=True, else a single path."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        if multiple:
            paths = filedialog.askopenfilenames(
                title=title,
                filetypes=filetypes,
                initialdir=initial_dir or os.getcwd(),
            )
            root.destroy()
            return list(paths) or None
        else:
            path = filedialog.askopenfilename(
                title=title,
                filetypes=filetypes,
                initialdir=initial_dir or os.getcwd(),
            )
            root.destroy()
            return path or None
    except Exception as e:
        die(f'Tkinter file dialog failed: {e}')


def main():
    # Ensure UTF-8 output on Windows terminals
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    args = sys.argv[1:]
    if not args:
        _run_gui()
        return
    if args[0] in ('--help', '-h'):
        print(HELP)
        sys.exit(0)
    cmd = args[0]
    if cmd == 'disasm':
        if len(args) < 2:
            input_paths = _tk_pick_file(
                title='Select file(s) to disassemble',
                filetypes=[('All files', '*.*'), ('EVDL/ARD/EV files', '*.evdl *.ard *.ev')],
                multiple=True,
            )
            if not input_paths:
                die('No file selected.')
            for input_path in input_paths:
                cmd_disasm(input_path)
        elif len(args) == 3 and not os.path.isdir(args[2]) and args[2].endswith('.asm'):
            # single file with explicit output path
            cmd_disasm(args[1], args[2])
        else:
            for input_path in args[1:]:
                cmd_disasm(input_path)
    elif cmd == 'asm':
        if len(args) < 2:
            input_path = _tk_pick_file(
                title='Select ASM file to assemble',
                filetypes=[('ASM files', '*.asm'), ('All files', '*.*')],
            )
            if not input_path:
                die('No ASM file selected.')
            orig_bin = _tk_pick_file(
                title='Select original binary to repack into',
                filetypes=[('All files', '*.*'), ('EVDL/ARD/EV files', '*.evdl *.ard *.ev')],
                initial_dir=os.path.dirname(os.path.abspath(input_path)),
            )
            if not orig_bin:
                die('No original binary selected.')
            cmd_asm(input_path, None, orig_bin_override=orig_bin)
        else:
            cmd_asm(args[1], args[2] if len(args) > 2 else None)
    else:
        die(f'Unknown command: {cmd}. Run with --help for usage.')

if __name__ == '__main__':
    main()
