"""KH1 event script binary format: opcode/syscall tables, KGR parsing for EVDL/ARD/WDT files, repacking, string table."""
import json
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).absolute().parent.parent
DATA_DIR = Path(__file__).absolute().parent / 'data'


def load_save_data_labels():
    labels_file = DATA_DIR / 'save_data_labels.json'
    if not labels_file.exists():
        return {}
    try:
        return {int(address, 16): label for address, label in json.loads(labels_file.read_text()).items()}
    except Exception:
        return {}


SAVE_DATA_LABELS = load_save_data_labels()

KH1_CHAR_MAP = {
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

OPCODES = {
    0: 'nop', 1: 'alu', 2: 'jmp', 3: 'beqz', 4: 'nop', 5: 'yield',
    6: 'store_reg', 7: 'cmp_reg_imm', 8: 'dec_reg_idx', 9: 'push',
    10: 'load_local', 11: 'store_local', 12: 'read_byte', 13: 'write_byte',
    14: 'read_word', 15: 'write_word', 16: 'read_dword', 17: 'write_dword',
    18: 'nop', 19: 'nop', 20: 'nop', 21: 'push_cond',
    22: 'init_call', 23: 'await_call', 24: 'syscall', 25: 'flow_ctrl',
    26: 'set_lt', 27: 'set_le', 28: 'set_gt', 29: 'set_ge',
    30: 'read_bit', 31: 'write_bit',
}
VALID_OPS = set(OPCODES)
OPCODE_BY_NAME = {name.lower(): opcode for opcode, name in OPCODES.items()}

ALU_OPS = {
    0: 'add', 1: 'sub', 2: 'mul', 3: 'div', 4: 'mod', 5: 'negate', 6: 'eq', 7: 'gt', 8: 'ge',
    9: 'lt', 10: 'le', 11: 'ne', 12: 'and', 13: 'or', 14: 'xor', 15: 'shr', 16: 'shl',
}
ALU_BY_NAME = {name: number for number, name in ALU_OPS.items()}

SYSCALLS = {0:'Open_window',1:'Display_message',2:'Close_window',3:'Set_window_position',4:'Set_window_size',5:'Set_window_type',6:'Set_window_opening_speed',7:'Set_message_display_speed',8:'Set_wait_timer',9:'Display_register_value',10:'Set_char_ID',11:'Move_char',12:'Rotate_char',13:'Change_motion',14:'Event_occurs',15:'Event_ends',16:'Get_char_pos_X',17:'Get_char_pos_Y',18:'Get_char_pos_Z',19:'Set_char_position',20:'Wait_move_done',21:'Show_char',22:'Hide_char',23:'Show_char_shadow',24:'Hide_char_shadow',25:'Collision_on',26:'Collision_off',27:'Fade_in',28:'Fade_out',29:'White_in',30:'White_out',31:'Blur_on',32:'Blur_off',33:'Wait_message_end',34:'Play_camera_motion',35:'Set_camera_position',36:'Set_camera_focus_position',37:'Rotate_camera',38:'Set_camera_distance',39:'Set_camera_fov',40:'Get_camera_focus_X',41:'Get_camera_focus_Y',42:'Get_camera_focus_Z',43:'Get_camera_rot_X',44:'Get_camera_rot_Y',45:'Get_camera_rot_Z',46:'Get_camera_distance',47:'Get_camera_fov',48:'Start_effect',49:'Move_camera_focus',50:'Move_camera_rotation',51:'Move_camera_distance',52:'Move_camera_fov',53:'Char_jump',54:'Char_ctrl_on',55:'Char_ctrl_off',56:'Motion_ctrl_on',57:'Motion_ctrl_off',58:'Change_motion_interp',59:'Change_map',60:'Change_area',61:'Get_event_starter_ID',62:'Group_display_on',63:'Group_display_off',64:'Set_var_1',65:'Set_var_0',66:'Inc_var',67:'Dec_var',68:'Random_value',69:'Turn_char',70:'Turn_char_left',71:'Turn_char_right',72:'Add_light',73:'Light_type',74:'Light_position',75:'Light_direction',76:'Light_color',77:'Point_light_distance',78:'Spot_light_angle',79:'Remove_light',80:'Set_window_tail_type',81:'Set_window_tail_location',82:'Set_window_tail_rotation',83:'Set_window_close_speed',84:'Widescreen_on',85:'Widescreen_off',86:'Change_motion_frame',87:'Pause_motion',88:'Enter_selection_mode',89:'Wait_selection',90:'Change_char_color',91:'Restore_char_color',92:'Load_event_motion',93:'Wait_file_load',94:'Set_event_motion',95:'Set_battle_motion',96:'Hide_body_parts',97:'Show_body_parts',98:'Wait_turn_end',99:'Turn_to_position',100:'Save_crossfade_image',101:'Start_crossfade',102:'Camera_vibration',103:'Wait_motion_end',104:'Char_bg_on',105:'Char_bg_off',106:'Wait_event_camera_end',107:'Wait_message_end_ID',108:'Motion_change_no_loop',109:'Start_texture_animation',110:'Motion_change_no_loop_interp',111:'Motion_change_no_loop_frame',112:'Gauge_on',113:'Gauge_off',114:'Command_display_on',115:'Command_display_off',116:'Change_blur_alpha',117:'Change_blur_color',118:'Change_blur_width',119:'Change_blur_height',120:'Default_shadow_light_on',121:'Default_shadow_light_off',122:'Change_char_scale',123:'Play_partial_motion',124:'Play_voice',125:'Stop_voice',126:'Trigger_event',127:'Get_world_number',128:'Get_area_number',129:'Get_set_number',130:'Change_map_whiteout',131:'Change_area_whiteout',132:'Set_attribute_on',133:'Set_attribute_off',134:'Write_set_number',135:'Keyhole_fade_out',136:'Event_SRAM_flag_on',137:'Event_SRAM_flag_off',138:'Get_event_SRAM_flag',139:'Widescreen_on_quick',140:'Widescreen_off_quick',141:'Weapon_display_on',142:'Weapon_display_off',143:'Stage_destruction_effect',144:'Check_map_jump_press',145:'Check_map_jump_motion',146:'Check_map_landing',147:'Play_camera_motion_local',148:'Play_camera_motion_local_rot',149:'Force_quit_script',150:'All_char_ctrl_on',151:'All_char_ctrl_off',152:'Check_char_on_stage',153:'Change_window_coords',154:'Restore_camera',155:'Add_bg_light',156:'Restore_camera_default',157:'Move_noturn',158:'Set_valid_key_input',159:'Clear_valid_key_input',160:'Switch_to_battle_mode',161:'Switch_to_normal_mode',162:'Clear_event_effect',163:'Start_resident_effect',164:'Clear_resident_effect',165:'Load_event_effect',166:'Wait_event_effect_load',167:'Change_resident_effect_coords',168:'Blur_on2',169:'Blur_off2',170:'Blur_type',171:'Blur_distance',172:'Get_pad_buttons',173:'Get_pad_trigger',174:'Play_camera_motion_local_rot_2actors',175:'Face_actor',176:'Pauseflag_off',177:'Open_window_no_close',178:'Activate_title_effect',179:'Start_talk_camera',180:'End_talk_camera',181:'Load_model',182:'Wait_model_load',183:'Display_model',184:'Rotate_blur',185:'Move_blur',186:'Clear_loaded_effect_ID',187:'Clear_resident_effect_ID',188:'Set_loaded_effect_location',189:'Set_loaded_effect_location_bone',190:'Play_SE',191:'Stop_SE',192:'Get_distance_2axis',193:'Get_distance_3axis',194:'Get_actor_distance_2axis',195:'Get_actor_distance_3axis',196:'Set_resident_effect_location_bone',197:'Get_current_command',198:'Set_command_speak_range',199:'Set_command_check_range',200:'Enable_menu_display',201:'Disable_menu_display',202:'Get_angle_actor_to_coord',203:'Get_angle_between_actors',204:'Fade_image_in',205:'Fade_image_out',206:'Set_image_offset',207:'Set_image_scale',208:'Set_camera_speed',209:'Set_motion_speed',210:'Set_effect_speed',211:'Set_object_far_clip',212:'Pause_actor',213:'Resume_actor',214:'Backload_test_event_motion',215:'Set_frame_color',216:'Start_frame_coloring',217:'Stop_frame_coloring',218:'Turn_head_angle',219:'Turn_head_coords',220:'Turn_head_actor',221:'Restore_head',222:'Open_shop_buy',223:'Wait_shop_close',224:'Move_jump',225:'Display_record',226:'Hide_record',227:'Show_timer',228:'Hide_timer',229:'Start_timer_up',230:'Start_timer_down',231:'Pause_timer',232:'Restart_timer',233:'Stop_timer',234:'Set_max_counter',235:'Inc_counter',236:'Show_counter',237:'Hide_counter',238:'Start_minigame',239:'End_minigame',240:'Show_ranking',241:'Start_hercules_event',242:'Reset_timer',243:'Message_to_battle_script',244:'Load_image',245:'Wait_image_load',246:'Display_image',247:'Hide_image',248:'Scroll_image_Y',249:'Load_BGM',250:'Wait_BGM_load',251:'Play_BGM',252:'Restore_BGM',253:'Check_bag_item_count',254:'Set_loaded_effect_start_frame',255:'Set_resident_effect_start_frame',256:'Load_voice',257:'Wait_voice_load',258:'Change_bag_items',259:'Check_char_in_area',260:'Start_vibration',261:'Stop_vibration',262:'Clipping_on',263:'Clipping_off',264:'Set_motion_null_to_char_pos',265:'Set_char_run_speed',266:'Reset_char_run_speed',267:'Change_char_weight',268:'Open_shop_sell',269:'Add_party_member',270:'Remove_party_member',271:'Get_motion_null_X',272:'Get_motion_null_Y',273:'Get_motion_null_Z',274:'Go_to_world_map',275:'Hercules_win_menu',276:'Hercules_lose_menu',277:'Hercules_champion_menu',278:'Game_over',279:'Quick_save',280:'Move_slow',281:'Get_part_from_party',282:'Display_black_image',283:'Display_new_record',284:'Push_actor_coord_X',285:'Push_actor_coord_Y',286:'Push_actor_coord_Z',287:'Push_actor_rotation',288:'Push_runlevel',289:'Push_motion_frames',290:'Push_actor_coord_X2',291:'Push_actor_coord_Y2',292:'Push_actor_coord_Z2',293:'Push_actor_rotation2',294:'Push_runlevel2',295:'Push_motion_frames2',296:'Fade_in_image_black_bg',297:'Fade_out_image_black_bg',298:'Cancel_movement',299:'Move_to_actor_pos',300:'Enable_game_over',301:'Disable_game_over',302:'Keyhole_fade_in',303:'End_keyhole_fade',304:'Set_sky_initial_rotation',305:'Get_minigame_menu_selection',306:'Set_char_initial_state',307:'Call_sin',308:'Call_cos',309:'Check_char_in_camera',310:'Check_battle_or_normal_mode',311:'Get_camera_viewpoint_X',312:'Get_camera_viewpoint_Y',313:'Get_camera_viewpoint_Z',314:'Get_attack_type_ID',315:'Erase_all_map_objects',316:'Show_all_map_objects',317:'Fade_in_3D',318:'Fade_out_3D',319:'Discard_object_data',320:'Enable_targeting',321:'Disable_targeting',322:'Get_motion_number',323:'Add_HP',324:'Add_MP',325:'Wait_all_enemies_defeated',326:'Enable_magic_command',327:'Disable_magic_command',328:'Enable_item_command',329:'Disable_item_command',330:'Enable_summon_command',331:'Disable_summon_command',332:'Set_counter_value',333:'Get_holdable_count',334:'Check_first_person_view',335:'Make_not_invincible',336:'Make_invincible',337:'Make_pressable',338:'Make_non_pressable',339:'Set_treasure_flag',340:'Get_treasure_flag',341:'Get_treasure_number',342:'Get_treasure_type',343:'Get_treasure_value',344:'Erase_treasure',345:'Get_treasure_ID',346:'Enemy_ctrl_on',347:'Enemy_ctrl_off',348:'Activate_battle_effects',349:'Set_battle_effect_to_bone',350:'Set_party',351:'Move_smooth_rot',352:'Change_game_speed',353:'Play_SE2',354:'Set_little_mermaid_water_speed',355:'Get_comm_ID',356:'Get_comm_Num',357:'Set_comm_work',358:'Display_item_acquired_message',359:'Display_money_acquired_message',360:'Disable_battle_event_box',361:'Enable_battle_event_box',362:'Disable_all_battle_event_boxes',363:'Enable_all_battle_event_boxes',364:'Set_item_number_in_message',365:'Set_window_width_auto',366:'Get_party_count',367:'Display_prize',368:'Hide_prize',369:'Delete_prize',370:'Return_to_title',371:'Change_effect_rotation',372:'Change_effect_scale',373:'Change_resident_effect_rotation',374:'Change_resident_effect_scale',375:'Make_not_invincible_actor',376:'Make_invincible_actor',377:'Make_inoperable',378:'Make_operable',379:'Get_char_current_area',380:'End_effect_loop',381:'End_resident_effect_loop',382:'Add_event_box',383:'Count_objects_by_part',384:'Load_event_SE',385:'Wait_event_SE_load',386:'Delete_event_box',387:'Get_char_HP',388:'Get_char_MP',389:'Write_set_number_from_table',390:'Start_BGSE',391:'Stop_BGSE',392:'Call_name_input',393:'Get_char_weight',394:'Hold_camera_info',395:'Get_camera_info',396:'Fisheye_on',397:'Fisheye_off',398:'Map_display_on',399:'Map_display_off',400:'Set_camera_parameters',401:'Reset_camera_parameters',402:'Stealth_on',403:'Stealth_off',404:'Get_motion_number_actor',405:'Load_waveform',406:'Wait_waveform_load',407:'Party_gauge_on',408:'Party_gauge_off',409:'Restore_SE',410:'Wait_restore_music',411:'Get_ground_color_from_area',412:'Set_ground_color_to_polygon',413:'Quick_save_on',414:'Quick_save_off',415:'Stop_BGM',416:'Add_battle_item',417:'Pad_ctrl_on',418:'Pad_ctrl_off',419:'GetLength_2',420:'GetLength3_2',421:'GetLengthA_2',422:'GetLength3A_2',423:'Char_request_on',424:'Char_request_off',425:'Stop_SE_all',426:'Erase_all_enemies',427:'Change_BGM_volume',428:'Add_MP_charge',429:'MP_charge_on',430:'MP_charge_off',431:'Motion_sound_on',432:'Motion_sound_off',433:'Ground_sound_on',434:'Ground_sound_off',435:'Play_effect_sound',436:'Stop_effect_sound',437:'Show_object_from_CALLNUM',438:'Check_Sora_on_ground',439:'Get_enemies_killed',440:'Reset_enemies_killed',441:'Disable_battle_mode_entry',442:'Enable_battle_mode_entry',443:'Wait_voice_finish',444:'Increase_money',445:'Load_next_map_texture',446:'Set_effect_rotation_from_bone',447:'Set_effect_rotation_from_bone2',448:'Enemy_view_off',449:'Enemy_view_on',450:'Load_all_objects_CALLNUM',451:'Wait_all_objects_CALLNUM',452:'Get_MAPOBJ_BG_color',453:'Get_distance_to_nearest_enemy',454:'Set_special_command',455:'Get_special_command_count',456:'Display_defeated_enemy_count',457:'Get_enemies_in_zone',458:'Load_magic',459:'Wait_magic_load',460:'Get_magic_level',461:'Load_all_objects_zone',462:'Wait_zone_load',463:'Set_special_thread_return',464:'Move_jump_frame',465:'Change_hercules_ranking',466:'Enable_accel_zone',467:'Disable_accel_zone',468:'Slider_ctrl_on',469:'Slider_ctrl_off',470:'Init_battle_script',471:'Init_all_enemy_battle_scripts',472:'Get_attack_type_received',473:'Get_map_object_damage',474:'Get_battle_count',475:'Set_message_numerical_work',476:'Enable_event_skipping',477:'Disable_event_skipping',478:'Release_object_CALLNUM',479:'Set_growth_type_1',480:'Set_growth_type_2',481:'Change_sora_parameters',482:'Set_magic_minus_flag',483:'Set_item_minus_flag',484:'Set_special_minus_flag',485:'Change_weapon',486:'Force_event_pose',487:'Force_no_event_pose',488:'Open_gummy_menu',489:'Start_movie',490:'Wait_movie_end',491:'Write_other_world_set_number',492:'Clear_history',493:'Set_save_point_flag',494:'Get_save_point_flag',495:'Delete_save_point',496:'Start_map_change',497:'Wait_name_input',498:'Add_party_menu_command',499:'Set_polygon_attribute',500:'Set_polygon_kind',501:'Set_polygon_ground',502:'Get_time_since_start',503:'Learn_magic',504:'Change_song_bank',505:'Wait_music_jump',506:'Change_track_volume',507:'Sky2_display_on',508:'Sky2_display_off',509:'Change_FOG',510:'Set_FOG_default',511:'Enter_event_mode',512:'Exit_event_mode',513:'Event_camera_on',514:'Event_camera_off',515:'MOVE_NOTURN',516:'ROT',517:'Check_map_changeable',518:'Add_char_to_dictionary',519:'Check_char_in_dictionary',520:'Add_dalmatian',521:'Check_dalmatian',522:'Update_minigame_record',523:'Get_minigame_record',524:'Set_story_flag',525:'Get_story_flag',526:'Add_anthem_report',527:'Check_anthem_report',528:'Open_party_menu',529:'Remove_char_from_dictionary',530:'Remove_story_flag',531:'Update_minigame_record_100kills',532:'Change_camera_sora_distance',533:'Get_camera_sora_distance',534:'Set_battle_message_return',535:'Play_OBJ_effect',536:'Change_OBJ_effect_scale',537:'Change_OBJ_effect_coords',538:'Erase_OBJ_effect',539:'Underwater_camera_on',540:'Underwater_camera_off',541:'Get_char_action',542:'Fade_out_MAP_group',543:'Fade_in_MAP_group',544:'Load_world_map_char',545:'Wait_world_map_char_load',546:'Open_world_map_window',547:'Close_world_map_window',548:'Set_world_map_char',549:'Set_world_map_char_motion',550:'Set_world_map_char_texture_animation',551:'Display_world_map_message',554:'Scatter_map_gimmick_prizes',555:'Check_coconuts_erasable',556:'Feel_icon_on',557:'Feel_icon_off',559:'Acquire_ability',560:'Set_gummy_name_message',561:'Set_ability_name_message',562:'Set_magic_name_message',563:'Set_summon_name_message',564:'Enable_limit_technique',565:'Disable_limit_technique',566:'Load_BGM_motion_bank2',567:'Load_wave_motion_bank2',568:'Learn_summon',569:'Summon_end_command',570:'Add_gummy',571:'Restore_HP_MP',572:'Wait_limit_skill_end',573:'Wait_summon_end',575:'Wait_SE_finish',576:'Wait_battle_icon_display',577:'Wait_restore_SE',578:'Transfer_object_SE',579:'Wait_object_SE_transfer',580:'Clear_object_SE',581:'Play_effect_bound_bone',582:'Check_save_menu_opened',583:'Get_item_from_gift_table',584:'Movie_standby',585:'Wait_movie_standby',586:'Set_game_clear_flag',587:'Get_game_clear_flag',588:'Display_gauge_fadein',589:'Remove_gauge_fadeout',590:'Display_command_fadein',591:'Remove_command_fadeout',592:'Remove_invincibility',593:'Make_party_invincible',594:'Set_world_map_flag',595:'Get_world_map_flag',596:'Read_set_number',597:'Start_map_effect',598:'Change_map_effect_pos',599:'Change_map_effect_rot',600:'Change_map_effect_scale',601:'Clear_map_effect',602:'Change_map_effect_start_frame',603:'End_map_effect_loop',604:'Bind_map_effect_to_bone',605:'Display_message_from_gift_table',606:'Change_char_color_from_map_table',607:'Load_all_enemy_SE',608:'Play_object_effect_once',609:'Start_weapon_effect',610:'Clear_weapon_effect',611:'Change_permanent_effect_color',612:'Start_map_change_rewrite_set',613:'Get_char_level',614:'Get_BG_color_R',615:'Get_BG_color_G',616:'Get_BG_color_B',617:'Set_object_BG_color',618:'Extract_set_BG_color',619:'Bind_effect_to_null',620:'Erase_weak_enemies',621:'Enable_blur_no_update',622:'Check_object_touching_zone',623:'Widescreen_on_frame',624:'Widescreen_off_frame',625:'Set_special_command_range',626:'Change_appear_flag',628:'Gummy_shop_buy',629:'Gummy_shop_sell',633:'Set_hercules_victory_flag',634:'Get_hercules_victory_flag',635:'Set_magic_name_message_multi',636:'Change_char_action',637:'Play_effect_bound_bone2',638:'Get_dalmatians_collected',639:'Show_feel_icon',640:'Hide_feel_icon',641:'Speed_fix_MOVE_NOTURN',642:'Load_BGM_on_map_change',643:'No_BGM_load_on_map_change',644:'Get_item_type',645:'Get_owned_money',646:'Wait_hercules_ranking_close',647:'Play_battle_voice',648:'Enable_gummies_in_item_menu',649:'Get_counter_value',650:'Get_timer_value',651:'Restore_music_fadein',652:'Play_music_fadein',654:'Apply_effect_to_bone_pos',655:'Rotate_effect_to_bone_angle',656:'WorldMap_test',657:'Load_weapon',658:'Wait_weapon_load',659:'Fade_out_SE',660:'Show_minigame_info',661:'Hide_minigame_info',662:'End_DH_stage_destruction',673:'Synthesis_shop_menu_open',678:'Minigame_limit_on',679:'Minigame_limit_off',680:'Cancel_ignore_sound',681:'Set_jiminy_memo_flag',682:'Get_jiminy_memo_flag',683:'Equip_weapon',684:'Equip_accessory',685:'Equip_ability',689:'Get_enemies_killed2',690:'Get_enemies_killed_all',692:'Get_hercules_team',693:'Get_hercules_ranking',695:'Scale_window_from_gift',696:'Push_actor_HP',697:'Push_actor_MP',698:'Play_effect_bound_bone3',699:'Play_effect_bound_bone4',700:'Enable_flight',701:'Disable_flight',702:'Enable_polygon_touch_event',703:'Disable_polygon_touch_event',704:'Get_MAPOBJ_BG_color_frames',705:'Extract_set_BG_color_frames',706:'Apply_effect_to_bone_pos2',707:'Rotate_effect_to_bone_angle2',708:'Wait_button_press',709:'Gummi_ship_event_message',710:'Stop_all_enemy_scripts',711:'Run_all_enemy_scripts',712:'Gummi_ship_tutorial',713:'Get_sora_gameover_motion',714:'Load_system_music',715:'Wait_system_music_load',716:'Load_nightmare_effects',717:'Wait_nightmare_effects_load',718:'Get_equipped_weapon',719:'Disable_battle_field_music_switch',720:'Enable_battle_field_music_switch',721:'BeEvSetStickVal',722:'Check_weapon_displayed',723:'Slow_wait',724:'Load_system_music2',725:'Restore_BGM2',726:'Restore_music_fadein2',727:'Set_shadow_steal_flag',728:'Get_synthesiser_progress',729:'Set_BG_color_to_drawing',730:'Stop_SE_3D',731:'Color_change_no_invalidate_floor',732:'Disable_ability',733:'Unlock_ability_disable',734:'Load_map_team_effect',735:'Fill_gummy_parts',736:'BeEvCheckWait',737:'Get_pad_buttons2',738:'Show_party_weapons',739:'Hide_party_weapons',740:'Change_raft_name_highwind',741:'Message_full_gummy_set',742:'Get_player_continues_entering_map',743:'Set_minigame_played_flag',744:'Check_shared_ability_taken',745:'WmEvCheckObjMotion',746:'Get_treasure_chest_full_flag',747:'Check_bag_item_count_only',748:'Enemy_bg_impact_on',749:'Enemy_bg_impact_off',750:'WmEvStartWinTexAnime2',751:'Show_battle_counter_ending',752:'Check_bag_item_count2',753:'Get_window_X',754:'Get_window_Y',755:'Check_expert_mode',756:'White_in_3D',757:'White_out_3D',758:'Check_easy_mode',759:'Set_event_skip_flag',760:'Get_event_skip_flag',761:'Open_event_skip_menu',762:'Get_event_skip_menu_selection',763:'Get_jiminy_memo_complete'}
SYSCALL_BY_NAME = {name.lower(): number for number, name in SYSCALLS.items()}

SCRIPT_HEADER = 0
ALU = 1
JMP = 2
BEQZ = 3
YIELD = 5
PUSH = 9
INIT_CALL = 22
AWAIT_CALL = 23
SYSCALL = 24
BRANCH_OPCODES = {JMP, BEQZ}
CALL_OPCODES = {INIT_CALL, AWAIT_CALL}
LOCAL_VARIABLE_OPCODES = {10, 11}
MEMORY_OPCODES = {12, 13, 14, 15, 16, 17, 30, 31}
OPCODES_THAT_END_A_SCRIPT = {YIELD, JMP, BEQZ, AWAIT_CALL}

KGR_MAGIC = b'KGR\x00'
KGR_HEADER_SIZE = 13
ZERO_WORD = bytes(4)
U32_MASK = 0xFFFFFFFF
U24_MASK = 0xFFFFFF


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def write_u32(data, offset, value):
    struct.pack_into('<I', data, offset, value & U32_MASK)


def sign24(value):
    if value < 0x800000:
        return value
    return value - 0x1000000


def encode_instruction(opcode, operand):
    return (operand & U24_MASK).to_bytes(3, 'little') + bytes([opcode & 0xFF])


def words_of(stream):
    word_count = len(stream) // 4
    return [stream[i * 4:i * 4 + 4] for i in range(word_count)]


def opcode_of(word):
    return word[3]


def operand_of(word):
    return word[0] | word[1] << 8 | word[2] << 16


def is_script_header(pc, opcode, operand, previous_opcode):
    if opcode != SCRIPT_HEADER or operand < 1 or operand > 256:
        return False
    return pc == 0 or previous_opcode in OPCODES_THAT_END_A_SCRIPT


def find_script_headers(words):
    headers = []
    previous_opcode = None
    for pc, word in enumerate(words):
        if is_script_header(pc, opcode_of(word), operand_of(word), previous_opcode):
            headers.append(pc)
        previous_opcode = opcode_of(word)
    return headers


def count_scripts(stream):
    return len(find_script_headers(words_of(stream)))


def decode_khscii(raw):
    return ''.join(KH1_CHAR_MAP.get(byte, f'{{0x{byte:02X}}}') for byte in raw)


def khscii_character_length(table, position):
    byte = table[position]
    if byte in (0x05, 0x06, 0x07):
        return 3
    if byte in (0x0B, 0x0D):
        return 4
    if byte == 0x0A:
        next_byte = table[position + 1] if position + 1 < len(table) else 0x00
        return 4 if next_byte == 0x00 else 2
    if 0x09 <= byte <= 0x1F:
        return 2
    return 1


def find_string_end(table, position):
    while position < len(table) and table[position] not in (0x00, 0x04):
        position += khscii_character_length(table, position)
    return position


def read_subfile_offsets(data):
    offsets = []
    for position in range(12, len(data) - 3, 4):
        offset = u32(data, position)
        if offset in offsets:
            break
        offsets.append(offset)
    return offsets


def parse_evdl_string_table(data):
    if len(data) < 16:
        return {}
    subfile_offsets = read_subfile_offsets(data)
    if not subfile_offsets or subfile_offsets[0] >= len(data):
        return {}
    table_start = subfile_offsets[0]
    table_end = subfile_offsets[1] if len(subfile_offsets) > 1 else len(data)
    table = data[table_start:table_end]
    if len(table) < 4:
        return {}
    string_count = u32(table, 0)
    if string_count > 10000:
        return {}
    strings = {}
    position = 4
    for index in range(string_count):
        if position >= len(table):
            break
        end = find_string_end(table, position)
        strings[index] = decode_khscii(table[position:end])
        position = end + 1
    return strings


def trim_stream(data, start, max_bytes=None):
    if max_bytes is None:
        window = data[start:]
    else:
        window = data[start:start + max_bytes]
    words = words_of(window)

    for index, word in enumerate(words):
        if opcode_of(word) not in VALID_OPS:
            kept = words[:index]
            while kept and kept[-1] == ZERO_WORD:
                kept.pop()
            return window[:len(kept) * 4]

    last_nonzero = 0
    for index, word in enumerate(words):
        if word != ZERO_WORD:
            last_nonzero = index
    return window[:(last_nonzero + 1) * 4]


def looks_like_code(stream):
    if not stream:
        return False
    checked_words = words_of(stream)[:200]
    valid_count = sum(1 for word in checked_words if opcode_of(word) in VALID_OPS)
    return valid_count >= len(checked_words) * 0.8


def make_kgr(data, kgr_offset, stream, ard_section):
    return {
        'kgr_offset': kgr_offset,
        'ard_section': ard_section,
        'unk0': u32(data, kgr_offset + 4),
        'unk1': u32(data, kgr_offset + 8),
        'nn_scripts': data[kgr_offset + 12],
        'stream_abs': kgr_offset + KGR_HEADER_SIZE,
        'stream': bytearray(stream),
        'orig_stream': bytearray(stream),
    }


def find_all_occurrences(data, needle):
    positions = []
    position = data.find(needle)
    while position != -1:
        positions.append(position)
        position = data.find(needle, position + 1)
    return positions


def find_kgrs(data):
    positions = [p for p in find_all_occurrences(data, KGR_MAGIC) if p < len(data) - 4]
    kgrs = []
    for index, kgr_offset in enumerate(positions):
        next_kgr = positions[index + 1] if index + 1 < len(positions) else len(data)
        stream_start = kgr_offset + KGR_HEADER_SIZE
        stream = trim_stream(data, stream_start, next_kgr - stream_start)
        if looks_like_code(stream):
            kgrs.append(make_kgr(data, kgr_offset, stream, None))
    return kgrs


def parse_evdl(data):
    kgrs = find_kgrs(data)
    if not kgrs:
        raise ValueError('No valid KGR sections found')
    return kgrs


def ard_section_end(section_offsets, section_index, data):
    section_start = section_offsets[section_index]
    for later_offset in section_offsets[section_index + 1:]:
        if later_offset > section_start:
            return later_offset
    return len(data)


def add_ard_event_kgrs(kgrs, data, section_offsets, section_index, event_base):
    unknown_count_0 = u32(data, event_base)
    unknown_count_1 = u32(data, event_base + 4)
    kgr_count = u32(data, event_base + 8)
    if kgr_count == 0 or kgr_count > 100:
        return
    kgr_table = event_base + 16 + (unknown_count_0 + unknown_count_1) * 4
    section_end = ard_section_end(section_offsets, section_index, data)

    for index in range(kgr_count):
        kgr_offset = event_base + u32(data, kgr_table + index * 4)
        if data[kgr_offset:kgr_offset + 4] != KGR_MAGIC:
            continue
        if index + 1 < kgr_count:
            next_kgr = event_base + u32(data, kgr_table + (index + 1) * 4)
        else:
            next_kgr = section_end
        stream_start = kgr_offset + KGR_HEADER_SIZE
        max_bytes = next_kgr - stream_start
        if max_bytes <= 0:
            continue
        stream = trim_stream(data, stream_start, max_bytes)
        if looks_like_code(stream):
            kgrs.append(make_kgr(data, kgr_offset, stream, section_index))


def add_ard_section_kgrs(kgrs, data, section_offsets, section_index):
    section_start = section_offsets[section_index]
    if section_start == 0 or section_start >= len(data) - 4:
        return
    part_count = u32(data, section_start)
    if part_count < 4 or part_count > 10:
        return
    event_base = section_start + u32(data, section_start + 16)
    if event_base + 16 >= len(data):
        return
    try:
        add_ard_event_kgrs(kgrs, data, section_offsets, section_index, event_base)
    except (struct.error, IndexError):
        pass


def parse_ard(data):
    section_count = u32(data, 0)
    if section_count != 32:
        raise ValueError(f'Expected 32 sections, got {section_count}')
    section_offsets = [u32(data, 8 + i * 4) for i in range(section_count)]
    kgrs = []
    for section_index in range(section_count):
        add_ard_section_kgrs(kgrs, data, section_offsets, section_index)
    if not kgrs:
        raise ValueError('No valid KGR sections found in ARD')
    return kgrs


def replace_aligned_u32(buffer, old_value, new_value):
    old_bytes = struct.pack('<I', old_value)
    new_bytes = struct.pack('<I', new_value)
    for position in range(0, len(buffer) - 3, 4):
        if buffer[position:position + 4] == old_bytes:
            buffer[position:position + 4] = new_bytes


def rebuild_kgr_block(original, kgrs, index, new_stream):
    kgr = kgrs[index]
    start = kgr['kgr_offset']
    end = kgrs[index + 1]['kgr_offset'] if index + 1 < len(kgrs) else len(original)
    header = bytearray(original[start:start + KGR_HEADER_SIZE])
    body = original[start + KGR_HEADER_SIZE:end]
    old_stream = kgr['orig_stream']
    if bytes(new_stream) == bytes(old_stream):
        return bytes(header + body)
    header[12] = count_scripts(new_stream)
    trailing = body[len(old_stream):]
    return bytes(header + new_stream + trailing)


def offset_shift_at(position, kgrs, new_offsets):
    shift = 0
    for index in range(1, len(kgrs)):
        if kgrs[index]['kgr_offset'] > position:
            break
        shift = new_offsets[index] - kgrs[index]['kgr_offset']
    return shift


def fix_wdt_section_pointers(original, output, kgrs, new_offsets, section_count):
    first_kgr = kgrs[0]['kgr_offset']
    for section_index in range(section_count):
        pointer_offset = 0x10 + section_index * 4
        if pointer_offset + 4 > first_kgr:
            break
        old_pointer = u32(original, pointer_offset)
        if first_kgr <= old_pointer < len(original):
            shift = offset_shift_at(old_pointer, kgrs, new_offsets)
            if shift:
                write_u32(output, pointer_offset, old_pointer + shift)


def fix_wdt_kgr_table(original, output, kgrs, new_offsets, section2):
    base = section2 + 4
    table = section2 + 12
    for entry_number in range(2, len(kgrs) + 1):
        entry_offset = table + entry_number * 4
        if entry_offset + 4 > len(output):
            break
        old_value = u32(original, entry_offset)
        if old_value == 0:
            continue
        shift = offset_shift_at(old_value + base, kgrs, new_offsets)
        if shift:
            write_u32(output, entry_offset, old_value + shift)


def has_wdt_kgr_table(original, kgrs, section2):
    if section2 == 0 or section2 + 16 > len(original):
        return False
    return u32(original, section2 + 8) == len(kgrs)


def fix_wdt_pointers(original, output, kgrs, new_offsets):
    section_count = u32(original, 0)
    if not (2 <= section_count <= 16 and len(original) >= 0x1C):
        return
    section2 = u32(original, 0x18)
    fix_wdt_section_pointers(original, output, kgrs, new_offsets, section_count)
    if has_wdt_kgr_table(original, kgrs, section2):
        fix_wdt_kgr_table(original, output, kgrs, new_offsets, section2)


def repack_evdl(original, kgrs, new_streams):
    prefix = bytearray(original[:kgrs[0]['kgr_offset']])
    blocks = [rebuild_kgr_block(original, kgrs, i, new_streams[i]) for i in range(len(kgrs))]

    new_offsets = []
    position = len(prefix)
    for block in blocks:
        new_offsets.append(position)
        position += len(block)

    for kgr, new_offset in zip(kgrs, new_offsets):
        if kgr['kgr_offset'] != new_offset:
            replace_aligned_u32(prefix, kgr['kgr_offset'], new_offset)

    output = prefix + b''.join(blocks)
    fix_wdt_pointers(original, output, kgrs, new_offsets)
    return bytes(output)


def shift_ard_section_offsets(data, moved_from, delta):
    for section_index in range(u32(data, 0)):
        entry_offset = 8 + section_index * 4
        section_offset = u32(data, entry_offset)
        if section_offset != 0 and section_offset >= moved_from:
            write_u32(data, entry_offset, section_offset + delta)


def fix_ard_section_kgr_tables(data, moved_from, delta):
    section_count = u32(data, 0)
    section_offsets = [u32(data, 8 + i * 4) for i in range(section_count)]
    for section_start in section_offsets:
        if section_start == 0 or section_start >= len(data) - 4:
            continue
        if section_start >= moved_from + delta:
            continue
        part_count = u32(data, section_start)
        if part_count < 1 or part_count > 16:
            continue
        if section_start + 20 > len(data):
            continue
        event_base = section_start + u32(data, section_start + 16)
        if event_base + 16 >= len(data):
            continue
        unknown_count_0 = u32(data, event_base)
        unknown_count_1 = u32(data, event_base + 4)
        kgr_count = u32(data, event_base + 8)
        if kgr_count == 0 or kgr_count > 200:
            continue
        kgr_table = event_base + 16 + (unknown_count_0 + unknown_count_1) * 4
        if kgr_table + kgr_count * 4 > len(data):
            continue
        for index in range(kgr_count):
            entry_offset = kgr_table + index * 4
            relative_offset = u32(data, entry_offset)
            if event_base + relative_offset >= moved_from:
                write_u32(data, entry_offset, relative_offset + delta)


def repack_ard(original, kgrs, new_streams):
    data = bytearray(original)
    for index, kgr in enumerate(kgrs):
        new_stream = new_streams[index]
        stream_start = kgr['stream_abs']
        old_end = stream_start + len(kgr['orig_stream'])
        delta = len(new_stream) - len(kgr['orig_stream'])

        data = data[:stream_start] + new_stream + data[old_end:]
        data[kgr['kgr_offset'] + 12] = count_scripts(new_stream)

        if delta != 0:
            shift_ard_section_offsets(data, old_end, delta)
            fix_ard_section_kgr_tables(data, old_end, delta)
            for later_kgr in kgrs[index + 1:]:
                if later_kgr['stream_abs'] >= old_end:
                    later_kgr['stream_abs'] += delta
                if later_kgr['kgr_offset'] >= old_end:
                    later_kgr['kgr_offset'] += delta

        kgr['orig_stream'] = bytearray(new_stream)
    return bytes(data)
