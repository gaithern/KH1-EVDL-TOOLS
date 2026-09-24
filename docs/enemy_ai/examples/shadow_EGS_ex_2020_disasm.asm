; ===== ex_2020.bd  block@0x2BD80  code@0x2C8B6  size=0x1357 =====
      0B36  00 00             end   ; ---- routine end ----
      0B38  00 00             end   ; ---- routine end ----
      0B3A  00 00             end   ; ---- routine end ----
      0B3C  72 01 00 00       pushblk[glob+0] x1
      0B40  72 01 00 00       pushblk[glob+0] x1
      0B44  79 1f             idxadd 31
      0B46  7a 01             pushblk.heap x1
      0B48  78 02 f6 07       call   L1B38 locals=2
      0B4C  78 02 b9 0b       call   L22C2 locals=2
      0B50  62 00 20 00       push   [glob+32]
      0B54  42 00 b0 05 00 00 push   #1456
      0B5A  48 02 bf 09       call   L1EDC locals=2
      0B5E  40 03             tailcall
      0B60  62 00 20 00       push   [glob+32]
      0B64  42 00 01 00 00 00 push   #1
      0B6A  48 02 e1 09       call   L1F30 locals=2
      0B6E  40 08             abort
      0B70  40 03             tailcall
      0B72  72 01 00 00       pushblk[glob+0] x1
      0B76  72 01 00 00       pushblk[glob+0] x1
      0B7A  79 1d             idxadd 29
      0B7C  7a 01             pushblk.heap x1
      0B7E  78 02 db 07       call   L1B38 locals=2
      0B82  78 02 9e 0b       call   L22C2 locals=2
      0B86  62 00 20 00       push   [glob+32]
      0B8A  42 00 cb 05 00 00 push   #1483
      0B90  48 02 a4 09       call   L1EDC locals=2
      0B94  40 03             tailcall
      0B96  48 02 e0 08       call   L1D5A locals=2
      0B9A  03 02 00 00       store  [loc+0]
      0B9E  32 01 00 00       pushblk[loc+0] x1
      0BA2  12 01 00 00 e1 43 push   #450f
      0BA8  11 01             sub.f
      0BAA  17 00             cmp.ltz.f
      0BAC  15 00 04 00       bz     L0BB8
      0BB0  18 02 5b 00       call   L0C6A locals=2
      0BB4  14 02 11 00       jmp    L0BDA
L0BB8: 0BB8  32 01 00 00       pushblk[loc+0] x1
      0BBC  12 01 00 00 48 44 push   #800f
      0BC2  11 01             sub.f
      0BC4  17 00             cmp.ltz.f
      0BC6  15 00 04 00       bz     L0BD2
      0BCA  18 02 46 00       call   L0C5A locals=2
      0BCE  14 02 04 00       jmp    L0BDA
L0BD2: 0BD2  18 02 24 00       call   L0C1E locals=2
      0BD6  14 02 00 00       jmp    L0BDA
L0BDA: 0BDA  62 00 30 00       push   [glob+48]
      0BDE  42 00 01 00 00 00 push   #1
      0BE4  52 00 00 80 3b 45 push   #3000f
      0BEA  42 00 02 00 00 00 push   #2
      0BF0  48 02 48 09       call   L1E84 locals=2
      0BF4  03 02 04 00       store  [loc+4]
      0BF8  72 01 00 00       pushblk[glob+0] x1
      0BFC  32 01 04 00       pushblk[loc+4] x1
      0C00  02 01 04 00 00 00 push   #4
      0C06  08 02 e0 06       call   L19CA locals=2
      0C0A  08 02 5a 0b       call   L22C2 locals=2
      0C0E  62 00 20 00       push   [glob+32]
      0C12  42 00 01 00 00 00 push   #1
      0C18  48 02 8a 09       call   L1F30 locals=2
      0C1C  40 03             tailcall
L0C1E: 0C1E  48 02 dc 00       call   L0DDA locals=2
      0C22  48 02 9a 08       call   L1D5A locals=2
      0C26  52 02 00 00 00 3f push   #0.5f
      0C2C  51 02             mul.f
      0C2E  58 02 02 02       call   L1036 locals=2
      0C32  0b 19             NATIVE t0 #0x19
      0C34  03 19 00 00       store  [loc+0]
      0C38  32 01 00 00       pushblk[loc+0] x1
      0C3C  12 01 cd cc cc 3d push   #0.1f
      0C42  11 01             sub.f
      0C44  17 00             cmp.ltz.f
      0C46  15 00 07 00       bz     L0C58
      0C4A  12 00 00 00 48 44 push   #800f
      0C50  18 02 b8 01       call   L0FC4 locals=2
      0C54  14 02 00 00       jmp    L0C58
L0C58: 0C58  10 03             tailcall
L0C5A: 0C5A  12 03 00 00 e1 43 push   #450f
      0C60  18 02 b0 01       call   L0FC4 locals=2
      0C64  18 02 b9 00       call   L0DDA locals=2
      0C68  10 03             tailcall
L0C6A: 0C6A  18 02 76 08       call   L1D5A locals=2
      0C6E  13 02 04 00       store  [loc+4]
      0C72  32 01 04 00       pushblk[loc+4] x1
      0C76  12 01 00 00 16 43 push   #150f
      0C7C  11 01             sub.f
      0C7E  17 00             cmp.ltz.f
      0C80  15 00 04 00       bz     L0C8C
      0C84  18 02 48 01       call   L0F18 locals=2
      0C88  14 02 35 00       jmp    L0CF6
L0C8C: 0C8C  32 01 04 00       pushblk[loc+4] x1
      0C90  12 01 00 00 96 43 push   #300f
      0C96  11 01             sub.f
      0C98  17 00             cmp.ltz.f
      0C9A  15 00 16 00       bz     L0CCA
      0C9E  0b 19             NATIVE t0 #0x19
      0CA0  03 19 00 00       store  [loc+0]
      0CA4  32 01 00 00       pushblk[loc+0] x1
      0CA8  12 01 66 66 66 3f push   #0.9f
      0CAE  11 01             sub.f
      0CB0  17 00             cmp.ltz.f
      0CB2  15 00 04 00       bz     L0CBE
      0CB6  18 02 5a 01       call   L0F6E locals=2
      0CBA  14 02 04 00       jmp    L0CC6
L0CBE: 0CBE  18 02 a8 00       call   L0E12 locals=2
      0CC2  14 02 00 00       jmp    L0CC6
L0CC6: 0CC6  14 02 16 00       jmp    L0CF6
L0CCA: 0CCA  0b 19             NATIVE t0 #0x19
      0CCC  03 19 00 00       store  [loc+0]
      0CD0  32 01 00 00       pushblk[loc+0] x1
      0CD4  12 01 9a 99 99 3e push   #0.3f
      0CDA  11 01             sub.f
      0CDC  17 00             cmp.ltz.f
      0CDE  15 00 04 00       bz     L0CEA
      0CE2  18 02 7a 00       call   L0DDA locals=2
      0CE6  14 02 04 00       jmp    L0CF2
L0CEA: 0CEA  18 02 92 00       call   L0E12 locals=2
      0CEE  14 02 00 00       jmp    L0CF2
L0CF2: 0CF2  14 02 00 00       jmp    L0CF6
L0CF6: 0CF6  0b 19             NATIVE t0 #0x19
      0CF8  03 19 00 00       store  [loc+0]
      0CFC  32 01 00 00       pushblk[loc+0] x1
      0D00  12 01 cd cc 4c 3f push   #0.8f
      0D06  11 01             sub.f
      0D08  17 00             cmp.ltz.f
      0D0A  15 00 04 00       bz     L0D16
      0D0E  18 02 64 00       call   L0DDA locals=2
      0D12  14 02 00 00       jmp    L0D16
L0D16: 0D16  0b 19             NATIVE t0 #0x19
      0D18  03 19 00 00       store  [loc+0]
      0D1C  32 01 00 00       pushblk[loc+0] x1
      0D20  12 01 33 33 33 3f push   #0.7f
      0D26  11 01             sub.f
      0D28  17 00             cmp.ltz.f
      0D2A  15 00 04 00       bz     L0D36
      0D2E  18 02 5c 01       call   L0FEA locals=2
      0D32  14 02 00 00       jmp    L0D36
L0D36: 0D36  10 03             tailcall
      0D38  72 01 00 00       pushblk[glob+0] x1
      0D3C  78 02 b8 0a       call   L22B0 locals=2
      0D40  62 00 20 00       push   [glob+32]
      0D44  42 00 a8 06 00 00 push   #1704
      0D4A  48 02 c7 08       call   L1EDC locals=2
      0D4E  40 03             tailcall
L0D50: 0D50  48 02 38 00       call   L0DC4 locals=2
      0D54  48 02 03 00       call   L0D5E locals=2
      0D58  44 02 fa ff       jmp    L0D50
      0D5C  40 03             tailcall
L0D5E: 0D5E  48 0a e3 02       call   L1328 locals=10
      0D62  22 00 10 00       push   [loc+16]
      0D66  12 00 00 00 96 43 push   #300f
      0D6C  12 00 00 00 fa 43 push   #500f
      0D72  18 0a fd 08       call   L1F70 locals=10
      0D76  22 00 10 00       push   [loc+16]
      0D7A  72 01 00 00       pushblk[glob+0] x1
      0D7E  79 04             idxadd 4
      0D80  0b 07             VecAdd()
      0D82  22 00 00 00       push   [loc+0]
      0D86  12 00 00 00 2f 44 push   #700f
      0D8C  12 00 00 00 7a 44 push   #1000f
      0D92  18 0a ed 08       call   L1F70 locals=10
      0D96  22 00 00 00       push   [loc+0]
      0D9A  72 01 00 00       pushblk[glob+0] x1
      0D9E  79 04             idxadd 4
      0DA0  0b 07             VecAdd()
      0DA2  22 00 10 00       push   [loc+16]
      0DA6  12 00 00 00 00 00 push   #0f
      0DAC  18 0a 53 01       call   L1056 locals=10
      0DB0  22 00 00 00       push   [loc+0]
      0DB4  12 00 00 00 00 00 push   #0f
      0DBA  18 0a 4c 01       call   L1056 locals=10
      0DBE  18 0a c4 01       call   L114A locals=10
      0DC2  10 03             tailcall
L0DC4: 0DC4  12 03 00 00 96 43 push   #300f
      0DCA  12 03 00 00 c8 43 push   #400f
      0DD0  62 00 10 00       push   [glob+16]
      0DD4  68 02 f6 06       call   L1BC4 locals=2
      0DD8  60 03             tailcall
L0DDA: 0DDA  72 01 00 00       pushblk[glob+0] x1
      0DDE  72 01 00 00       pushblk[glob+0] x1
      0DE2  79 1d             idxadd 29
      0DE4  7a 01             pushblk.heap x1
      0DE6  78 02 8c 0a       call   L2302 locals=2
      0DEA  72 01 00 00       pushblk[glob+0] x1
      0DEE  42 01 cb 00 00 00 push   #203
      0DF4  52 01 00 00 00 41 push   #8f
      0DFA  0b 0c             NATIVE t0 #0x0c
      0DFC  12 0c 00 00 70 41 push   #15f
      0E02  12 0c 00 00 96 42 push   #75f
      0E08  18 02 d5 08       call   L1FB6 locals=2
      0E0C  18 02 62 07       call   L1CD4 locals=2
      0E10  10 03             tailcall
L0E12: 0E12  0b 16             GetActor()
      0E14  03 16 14 00       store  [loc+20]
      0E18  12 16 00 00 16 43 push   #150f
      0E1E  12 16 00 00 00 41 push   #8f
      0E24  12 16 00 00 c8 42 push   #100f
      0E2A  12 16 00 00 a0 41 push   #20f
      0E30  18 06 d0 04       call   L17D4 locals=6
      0E34  12 06 00 00 00 00 push   #0f
      0E3A  13 06 10 00       store  [loc+16]
L0E3E: 0E3E  72 01 00 00       pushblk[glob+0] x1
      0E42  79 1c             idxadd 28
      0E44  7a 01             pushblk.heap x1
      0E46  42 01 02 00 00 00 push   #2
      0E4C  41 01             sub.i
      0E4E  47 02             cmp.eqz.i
      0E50  45 02 61 00       bz     L0F16
      0E54  72 01 00 00       pushblk[glob+0] x1
      0E58  79 1d             idxadd 29
      0E5A  7a 01             pushblk.heap x1
      0E5C  79 04             idxadd 4
      0E5E  7a 04             pushblk.heap x4
      0E60  33 04 00 00       store  [loc+0]
      0E64  22 00 00 00       push   [loc+0]
      0E68  72 01 00 00       pushblk[glob+0] x1
      0E6C  79 04             idxadd 4
      0E6E  0b 08             VecSub()
      0E70  22 00 00 00       push   [loc+0]
      0E74  0b 09             NATIVE t0 #0x09
      0E76  72 01 00 00       pushblk[glob+0] x1
      0E7A  22 00 00 00       push   [loc+0]
      0E7E  0b 24             NATIVE t0 #0x24
      0E80  22 00 00 00       push   [loc+0]
      0E84  29 03             idxadd 3
      0E86  12 03 00 00 00 41 push   #8f
      0E8C  10 07             blkcopy
      0E8E  72 01 00 00       pushblk[glob+0] x1
      0E92  79 08             idxadd 8
      0E94  22 00 00 00       push   [loc+0]
      0E98  2a 04             pushblk.heap x4
      0E9A  20 07             blkcopy
      0E9C  32 01 10 00       pushblk[loc+16] x1
      0EA0  12 01 00 00 80 41 push   #16f
      0EA6  11 01             sub.f
      0EA8  17 04             cmp.gez.f
      0EAA  15 04 2a 00       bz     L0F02
      0EAE  72 01 00 00       pushblk[glob+0] x1
      0EB2  32 01 14 00       pushblk[loc+20] x1
      0EB6  e2 00 1c fb       push   [imm+-1252]
      0EBA  0b 17             MakeAttack()
      0EBC  00 04             pop
      0EBE  72 01 00 00       pushblk[glob+0] x1
      0EC2  32 01 14 00       pushblk[loc+20] x1
      0EC6  e2 00 9c fa       push   [imm+-1380]
      0ECA  0b 17             MakeAttack()
      0ECC  00 04             pop
      0ECE  72 01 00 00       pushblk[glob+0] x1
      0ED2  42 01 c9 00 00 01 push   #16777417
      0ED8  52 01 00 00 00 00 push   #0f
      0EDE  52 01 00 00 00 00 push   #0f
      0EE4  0b 0d             NATIVE t0 #0x0d
      0EE6  72 01 00 00       pushblk[glob+0] x1
      0EEA  42 01 06 00 00 40 push   #1073741830
      0EF0  52 01 00 00 00 00 push   #0f
      0EF6  52 01 00 00 00 00 push   #0f
      0EFC  0b 0e             NATIVE t0 #0x0e
      0EFE  04 0e 00 00       jmp    L0F02
L0F02: 0F02  22 00 10 00       push   [loc+16]
      0F06  20 0c             dup
      0F08  2a 01             pushblk.heap x1
      0F0A  0b 05             NATIVE t0 #0x05
      0F0C  11 00             add.f
      0F0E  10 07             blkcopy
      0F10  10 00             end
      0F12  14 00 94 ff       jmp    L0E3E
L0F16: 0F16  10 03             tailcall
L0F18: 0F18  18 02 2c 07       call   L1D74 locals=2
      0F1C  72 01 00 00       pushblk[glob+0] x1
      0F20  72 01 00 00       pushblk[glob+0] x1
      0F24  79 1d             idxadd 29
      0F26  7a 01             pushblk.heap x1
      0F28  78 02 eb 09       call   L2302 locals=2
      0F2C  72 01 00 00       pushblk[glob+0] x1
      0F30  0b 16             GetActor()
      0F32  e2 00 c0 f9       push   [imm+-1600]
      0F36  0b 17             MakeAttack()
      0F38  00 04             pop
      0F3A  72 01 00 00       pushblk[glob+0] x1
      0F3E  42 01 cc 00 00 01 push   #16777420
      0F44  52 01 00 00 00 41 push   #8f
      0F4A  52 01 00 00 00 00 push   #0f
      0F50  0b 0d             NATIVE t0 #0x0d
      0F52  72 01 00 00       pushblk[glob+0] x1
      0F56  42 01 cb 00 00 40 push   #1073742027
      0F5C  52 01 00 00 00 41 push   #8f
      0F62  52 01 00 00 00 00 push   #0f
      0F68  0b 0e             NATIVE t0 #0x0e
      0F6A  00 00             end   ; ---- routine end ----
      0F6C  00 03             tailcall
L0F6E: 0F6E  08 02 01 07       call   L1D74 locals=2
      0F72  72 01 00 00       pushblk[glob+0] x1
      0F76  72 01 00 00       pushblk[glob+0] x1
      0F7A  79 1d             idxadd 29
      0F7C  7a 01             pushblk.heap x1
      0F7E  78 02 c0 09       call   L2302 locals=2
      0F82  72 01 00 00       pushblk[glob+0] x1
      0F86  0b 16             GetActor()
      0F88  e2 00 fa f8       push   [imm+-1798]
      0F8C  0b 17             MakeAttack()
      0F8E  00 04             pop
      0F90  72 01 00 00       pushblk[glob+0] x1
      0F94  42 01 c8 00 00 01 push   #16777416
      0F9A  52 01 00 00 00 41 push   #8f
      0FA0  52 01 00 00 00 00 push   #0f
      0FA6  0b 0d             NATIVE t0 #0x0d
      0FA8  72 01 00 00       pushblk[glob+0] x1
      0FAC  42 01 cb 00 00 40 push   #1073742027
      0FB2  52 01 00 00 00 41 push   #8f
      0FB8  52 01 00 00 00 00 push   #0f
      0FBE  0b 0e             NATIVE t0 #0x0e
      0FC0  00 00             end   ; ---- routine end ----
      0FC2  00 03             tailcall
L0FC4: 0FC4  03 03 00 00       store  [loc+0]
      0FC8  72 01 00 00       pushblk[glob+0] x1
      0FCC  42 01 01 00 00 00 push   #1
      0FD2  52 01 00 00 f0 42 push   #120f
      0FD8  52 01 00 00 20 41 push   #10f
      0FDE  32 01 00 00       pushblk[loc+0] x1
      0FE2  38 02 c7 09       call   L2374 locals=2
      0FE6  30 04             pop
      0FE8  30 03             tailcall
L0FEA: 0FEA  38 06 9d 01       call   L1328 locals=6
      0FEE  22 00 00 00       push   [loc+0]
      0FF2  12 00 00 00 48 43 push   #200f
      0FF8  12 00 00 00 96 43 push   #300f
      0FFE  18 06 b7 07       call   L1F70 locals=6
      1002  22 00 00 00       push   [loc+0]
      1006  72 01 00 00       pushblk[glob+0] x1
      100A  79 04             idxadd 4
      100C  0b 07             VecAdd()
      100E  22 00 00 00       push   [loc+0]
      1012  12 00 00 00 c8 42 push   #100f
      1018  18 06 1d 00       call   L1056 locals=6
      101C  72 01 00 00       pushblk[glob+0] x1
      1020  79 1d             idxadd 29
      1022  7a 01             pushblk.heap x1
      1024  79 04             idxadd 4
      1026  52 04 00 00 16 43 push   #150f
      102C  58 06 13 00       call   L1056 locals=6
      1030  58 06 8b 00       call   L114A locals=6
      1034  50 03             tailcall
L1036: 1036  13 03 00 00       store  [loc+0]
      103A  18 02 75 01       call   L1328 locals=2
      103E  72 01 00 00       pushblk[glob+0] x1
      1042  79 1d             idxadd 29
      1044  7a 01             pushblk.heap x1
      1046  79 04             idxadd 4
      1048  32 01 00 00       pushblk[loc+0] x1
      104C  38 02 03 00       call   L1056 locals=2
      1050  38 02 7b 00       call   L114A locals=2
      1054  30 03             tailcall
L1056: 1056  33 03 00 00       store  [loc+0]
      105A  33 03 04 00       store  [loc+4]
      105E  12 03 00 00 70 42 push   #60f
      1064  13 03 08 00       store  [loc+8]
L1068: 1068  32 01 08 00       pushblk[loc+8] x1
      106C  12 01 00 00 00 00 push   #0f
      1072  11 01             sub.f
      1074  17 05             cmp.gtz.f
      1076  15 05 25 00       bz     L10C4
      107A  32 01 04 00       pushblk[loc+4] x1
      107E  38 06 22 00       call   L10C6 locals=6
      1082  33 06 0c 00       store  [loc+12]
      1086  22 00 08 00       push   [loc+8]
      108A  20 0c             dup
      108C  2a 01             pushblk.heap x1
      108E  0b 05             NATIVE t0 #0x05
      1090  11 01             sub.f
      1092  10 07             blkcopy
      1094  10 00             end
      1096  12 00 00 00 40 40 push   #3f
      109C  18 06 b6 02       call   L160C locals=6
      10A0  10 0c             dup
      10A2  16 0c 07 00       bnz    L10B4
      10A6  32 01 0c 00       pushblk[loc+12] x1
      10AA  32 01 00 00       pushblk[loc+0] x1
      10AE  11 01             sub.f
      10B0  17 00             cmp.ltz.f
      10B2  01 0b             lor.i
L10B4: 10B4  05 0b 04 00       bz     L10C0
      10B8  04 0b 04 00       jmp    L10C4
      10BC  04 0b 00 00       jmp    L10C0
L10C0: 10C0  04 0b d2 ff       jmp    L1068
L10C4: 10C4  00 03             tailcall
L10C6: 10C6  03 03 00 00       store  [loc+0]
      10CA  32 01 00 00       pushblk[loc+0] x1
      10CE  3a 04             pushblk.heap x4
      10D0  33 04 10 00       store  [loc+16]
      10D4  22 00 10 00       push   [loc+16]
      10D8  72 01 00 00       pushblk[glob+0] x1
      10DC  79 04             idxadd 4
      10DE  0b 08             VecSub()
      10E0  22 00 10 00       push   [loc+16]
      10E4  72 01 38 00       pushblk[glob+56] x1
      10E8  0b 02             SinDeg()
      10EA  12 02 00 00 70 42 push   #60f
      10F0  11 02             mul.f
      10F2  0b 0a             RotateDeg()
      10F4  22 00 10 00       push   [loc+16]
      10F8  72 01 00 00       pushblk[glob+0] x1
      10FC  79 04             idxadd 4
      10FE  0b 07             VecAdd()
      1100  62 00 38 00       push   [glob+56]
      1104  60 0c             dup
      1106  6a 01             pushblk.heap x1
      1108  0b 19             NATIVE t0 #0x19
      110A  12 19 00 00 00 40 push   #2f
      1110  11 02             mul.f
      1112  12 02 00 00 40 40 push   #3f
      1118  11 00             add.f
      111A  11 00             add.f
      111C  10 07             blkcopy
      111E  72 01 00 00       pushblk[glob+0] x1
      1122  79 1b             idxadd 27
      1124  7a 01             pushblk.heap x1
      1126  79 03             idxadd 3
      1128  52 03 00 00 c0 40 push   #6f
      112E  50 07             blkcopy
      1130  72 01 00 00       pushblk[glob+0] x1
      1134  22 00 10 00       push   [loc+16]
      1138  02 00 02 00 00 00 push   #2
      113E  0b 28             NATIVE t0 #0x28
      1140  03 28 04 00       store  [loc+4]
      1144  32 01 04 00       pushblk[loc+4] x1
      1148  30 03             tailcall
L114A: 114A  38 02 13 06       call   L1D74 locals=2
      114E  72 01 00 00       pushblk[glob+0] x1
      1152  42 01 00 00 00 00 push   #0
      1158  42 01 00 00 00 00 push   #0
      115E  42 01 04 00 00 00 push   #4
      1164  0b 75             NATIVE t0 #0x75
      1166  72 01 00 00       pushblk[glob+0] x1
      116A  42 01 00 00 00 00 push   #0
      1170  42 01 00 00 00 00 push   #0
      1176  42 01 08 00 00 00 push   #8
      117C  0b 74             NATIVE t0 #0x74
      117E  72 01 40 00       pushblk[glob+64] x1
      1182  42 01 00 00 00 00 push   #0
      1188  41 01             sub.i
      118A  47 02             cmp.eqz.i
      118C  45 02 0f 00       bz     L11AE
      1190  72 01 00 00       pushblk[glob+0] x1
      1194  78 02 6d 06       call   L1E72 locals=2
      1198  78 02 c8 08       call   L232C locals=2
      119C  72 01 00 00       pushblk[glob+0] x1
      11A0  52 01 00 00 f0 41 push   #30f
      11A6  58 02 e3 09       call   L2570 locals=2
      11AA  54 02 00 00       jmp    L11AE
L11AE: 11AE  72 01 00 00       pushblk[glob+0] x1
      11B2  42 01 45 00 00 00 push   #69
      11B8  52 01 00 00 00 00 push   #0f
      11BE  52 01 00 00 00 00 push   #0f
      11C4  0b 0d             NATIVE t0 #0x0d
      11C6  72 01 00 00       pushblk[glob+0] x1
      11CA  42 01 00 00 00 00 push   #0
      11D0  52 01 00 00 00 41 push   #8f
      11D6  52 01 00 00 00 00 push   #0f
      11DC  0b 0e             NATIVE t0 #0x0e
      11DE  72 01 00 00       pushblk[glob+0] x1
      11E2  42 01 01 00 00 00 push   #1
      11E8  48 02 77 09       call   L24DA locals=2
      11EC  72 01 00 00       pushblk[glob+0] x1
      11F0  42 01 02 00 00 00 push   #2
      11F6  48 02 62 09       call   L24BE locals=2
      11FA  72 01 00 00       pushblk[glob+0] x1
      11FE  42 01 00 01 00 00 push   #256
      1204  48 02 5b 09       call   L24BE locals=2
      1208  72 01 00 00       pushblk[glob+0] x1
      120C  42 01 10 00 00 00 push   #16
      1212  48 02 62 09       call   L24DA locals=2
      1216  72 01 00 00       pushblk[glob+0] x1
      121A  42 01 45 00 00 00 push   #69
      1220  0b 2b             NATIVE t0 #0x2b
      1222  12 2b 00 00 f0 41 push   #30f
      1228  11 01             sub.f
      122A  13 01 04 00       store  [loc+4]
      122E  12 01 00 00 00 00 push   #0f
      1234  13 01 00 00       store  [loc+0]
L1238: 1238  32 01 00 00       pushblk[loc+0] x1
      123C  32 01 04 00       pushblk[loc+4] x1
      1240  11 01             sub.f
      1242  17 00             cmp.ltz.f
      1244  15 00 3b 00       bz     L12BE
      1248  72 01 40 00       pushblk[glob+64] x1
      124C  42 01 00 00 00 00 push   #0
      1252  41 01             sub.i
      1254  47 02             cmp.eqz.i
      1256  45 02 08 00       bz     L126A
      125A  72 01 00 00       pushblk[glob+0] x1
      125E  78 02 08 06       call   L1E72 locals=2
      1262  78 02 4e 08       call   L2302 locals=2
      1266  74 02 16 00       jmp    L1296
L126A: 126A  72 01 00 00       pushblk[glob+0] x1
      126E  79 1d             idxadd 29
      1270  7a 01             pushblk.heap x1
      1272  42 01 00 00 00 00 push   #0
      1278  48 02 90 09       call   L259C locals=2
      127C  47 03             cmp.nez.i
      127E  45 03 08 00       bz     L1292
      1282  72 01 00 00       pushblk[glob+0] x1
      1286  78 02 f4 05       call   L1E72 locals=2
      128A  78 02 3a 08       call   L2302 locals=2
      128E  74 02 00 00       jmp    L1292
L1292: 1292  74 02 00 00       jmp    L1296
L1296: 1296  22 00 00 00       push   [loc+0]
      129A  20 0c             dup
      129C  2a 01             pushblk.heap x1
      129E  0b 05             NATIVE t0 #0x05
      12A0  11 00             add.f
      12A2  10 07             blkcopy
      12A4  72 01 00 00       pushblk[glob+0] x1
      12A8  79 10             idxadd 16
      12AA  79 01             idxadd 1
      12AC  32 01 00 00       pushblk[loc+0] x1
      12B0  32 01 04 00       pushblk[loc+4] x1
      12B4  11 03             div.f
      12B6  10 07             blkcopy
      12B8  10 00             end
      12BA  14 00 bd ff       jmp    L1238
L12BE: 12BE  02 00 01 00 00 00 push   #1
      12C4  43 00 40 00       store  [glob+64]
      12C8  72 01 00 00       pushblk[glob+0] x1
      12CC  79 10             idxadd 16
      12CE  79 01             idxadd 1
      12D0  52 01 00 00 80 3f push   #1f
      12D6  50 07             blkcopy
      12D8  72 01 00 00       pushblk[glob+0] x1
      12DC  42 01 10 00 00 00 push   #16
      12E2  48 02 ec 08       call   L24BE locals=2
      12E6  72 01 00 00       pushblk[glob+0] x1
      12EA  42 01 20 00 00 00 push   #32
      12F0  48 02 e5 08       call   L24BE locals=2
      12F4  72 01 44 00       pushblk[glob+68] x1
      12F8  42 01 01 00 00 00 push   #1
      12FE  41 01             sub.i
      1300  47 03             cmp.nez.i
      1302  45 03 09 00       bz     L1318
      1306  72 01 00 00       pushblk[glob+0] x1
      130A  42 01 40 00 00 00 push   #64
      1310  48 02 d5 08       call   L24BE locals=2
      1314  44 02 00 00       jmp    L1318
L1318: 1318  42 02 00 00 00 00 push   #0
      131E  43 02 3c 00       store  [glob+60]
      1322  48 02 27 05       call   L1D74 locals=2
      1326  40 03             tailcall
L1328: 1328  48 02 24 05       call   L1D74 locals=2
      132C  42 02 01 00 00 00 push   #1
      1332  43 02 3c 00       store  [glob+60]
      1336  72 01 00 00       pushblk[glob+0] x1
      133A  42 01 46 00 00 00 push   #70
      1340  52 01 00 00 00 41 push   #8f
      1346  52 01 00 00 00 00 push   #0f
      134C  0b 0d             NATIVE t0 #0x0d
      134E  72 01 00 00       pushblk[glob+0] x1
      1352  42 01 ca 00 00 00 push   #202
      1358  52 01 00 00 00 00 push   #0f

