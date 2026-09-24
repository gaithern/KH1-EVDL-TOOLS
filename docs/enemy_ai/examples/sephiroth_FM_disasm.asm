; ===== ex_3000_00.bd  block@0x3B8B80  code@0x3B8B98  size=0x1DC =====
      0018  13 03 00 00       store  [loc+0]
      001C  72 01 00 00       pushblk[glob+0] x1
      0020  79 03             idxadd 3
      0022  7a 01             pushblk.heap x1
      0024  42 01 05 00 00 00 push   #5
      002A  42 01 20 4e 00 00 push   #20000
      0030  a2 00 00 00       push   [heap+0]
      0034  0b 4a             SpawnObj()
      0036  03 4a 08 00       store  [loc+8]
      003A  32 01 08 00       pushblk[loc+8] x1
      003E  22 00 10 00       push   [loc+16]
      0042  4b 0a             GetRotation()
      0044  22 00 10 00       push   [loc+16]
      0048  29 01             idxadd 1
      004A  12 01 00 00 00 00 push   #0f
      0050  12 01 00 00 b4 43 push   #360f
      0056  18 0a a7 00       call   L01A8 locals=10
      005A  10 07             blkcopy
      005C  32 01 08 00       pushblk[loc+8] x1
      0060  22 00 10 00       push   [loc+16]
      0064  0b 37             SetRotation()
      0066  12 37 00 00 20 41 push   #10f
      006C  18 0a 08 02       call   L0480 locals=10
      0070  72 01 00 00       pushblk[glob+0] x1
      0074  7a 01             pushblk.heap x1
      0076  0b 16             GetActor()
      0078  72 01 00 00       pushblk[glob+0] x1
      007C  79 04             idxadd 4
      007E  7a 01             pushblk.heap x1
      0080  0b 17             MakeAttack()
      0082  03 17 0c 00       store  [loc+12]
      0086  32 01 0c 00       pushblk[loc+12] x1
      008A  02 01 02 00 00 00 push   #2
      0090  08 0a 67 01       call   L0362 locals=10
      0094  32 01 0c 00       pushblk[loc+12] x1
      0098  30 0c             dup
      009A  3a 01             pushblk.heap x1
      009C  02 01 c0 00 00 00 push   #192
      00A2  01 06             or.i
      00A4  00 07             blkcopy
      00A6  32 01 0c 00       pushblk[loc+12] x1
      00AA  39 02             idxadd 2
      00AC  72 01 00 00       pushblk[glob+0] x1
      00B0  79 03             idxadd 3
      00B2  7a 01             pushblk.heap x1
      00B4  70 07             blkcopy
      00B6  32 01 0c 00       pushblk[loc+12] x1
      00BA  a2 00 00 00       push   [heap+0]
      00BE  0b 4c             ObjOp2()
      00C0  32 01 0c 00       pushblk[loc+12] x1
      00C4  39 04             idxadd 4
      00C6  a2 00 00 00       push   [heap+0]
      00CA  aa 04             pushblk.heap x4
      00CC  a0 07             blkcopy
      00CE  32 01 0c 00       pushblk[loc+12] x1
      00D2  39 10             idxadd 16
      00D4  a2 00 00 00       push   [heap+0]
      00D8  aa 04             pushblk.heap x4
      00DA  a0 07             blkcopy
      00DC  32 01 0c 00       pushblk[loc+12] x1
      00E0  39 10             idxadd 16
      00E2  39 01             idxadd 1
      00E4  32 01 0c 00       pushblk[loc+12] x1
      00E8  39 10             idxadd 16
      00EA  39 01             idxadd 1
      00EC  3a 01             pushblk.heap x1
      00EE  12 01 00 00 7a 44 push   #1000f
      00F4  11 01             sub.f
      00F6  10 07             blkcopy
      00F8  32 01 0c 00       pushblk[loc+12] x1
      00FC  39 03             idxadd 3
      00FE  12 03 00 00 96 43 push   #300f
      0104  10 07             blkcopy
      0106  32 01 0c 00       pushblk[loc+12] x1
      010A  39 0f             idxadd 15
      010C  12 0f 00 00 96 43 push   #300f
      0112  10 07             blkcopy
      0114  32 01 0c 00       pushblk[loc+12] x1
      0118  02 01 03 00 00 00 push   #3
      011E  0b d5             SetFlag2()
      0120  32 01 0c 00       pushblk[loc+12] x1
      0124  39 14             idxadd 20
      0126  12 14 00 00 00 41 push   #8f
      012C  10 07             blkcopy
      012E  12 07 00 00 00 00 push   #0f
      0134  13 07 20 00       store  [loc+32]
L0138: 0138  32 01 20 00       pushblk[loc+32] x1
      013C  12 01 00 00 c8 42 push   #100f
      0142  11 01             sub.f
      0144  17 00             cmp.ltz.f
      0146  15 00 13 00       bz     L0170
      014A  32 01 0c 00       pushblk[loc+12] x1
      014E  30 0c             dup
      0150  3a 01             pushblk.heap x1
      0152  02 01 04 00 00 00 push   #4
      0158  01 06             or.i
      015A  00 07             blkcopy
      015C  00 00             end   ; ---- routine end ----
      015E  22 00 20 00       push   [loc+32]
      0162  20 0c             dup
      0164  2a 01             pushblk.heap x1
      0166  0b 05             NATIVE t0 #0x05
      0168  11 00             add.f
      016A  10 07             blkcopy
      016C  14 07 e4 ff       jmp    L0138
L0170: 0170  32 01 0c 00       pushblk[loc+12] x1
      0174  02 01 00 00 00 00 push   #0
      017A  0b d5             SetFlag2()
      017C  0b b2             ClearChainFlags?()
      017E  00 03             tailcall
      0180  03 03 04 00       store  [loc+4]
      0184  03 03 00 00       store  [loc+0]
      0188  32 01 04 00       pushblk[loc+4] x1
      018C  3a 04             pushblk.heap x4
      018E  b3 04 00 00       store  [heap+0]
      0192  a2 00 00 00       push   [heap+0]
      0196  a9 01             idxadd 1
      0198  a0 0c             dup
      019A  aa 01             pushblk.heap x1
      019C  92 01 00 00 20 41 push   #10f
      01A2  91 01             sub.f
      01A4  90 07             blkcopy
      01A6  90 03             tailcall
L01A8: 01A8  13 03 00 00       store  [loc+0]
      01AC  13 03 04 00       store  [loc+4]
      01B0  0b 19             NATIVE t0 #0x19
      01B2  32 01 00 00       pushblk[loc+0] x1
      01B6  32 01 04 00       pushblk[loc+4] x1
      01BA  11 01             sub.f
      01BC  11 02             mul.f
      01BE  32 01 04 00       pushblk[loc+4] x1
      01C2  11 00             add.f
      01C4  10 03             tailcall
      01C6  13 03 04 00       store  [loc+4]
      01CA  13 03 00 00       store  [loc+0]
      01CE  12 03 00 00 00 00 push   #0f
      01D4  32 01 04 00       pushblk[loc+4] x1
      01D8  11 01             sub.f
      01DA  17 00             cmp.ltz.f
      01DC  15 00 17 00       bz     L020E

; ===== ex_3000_01.bd  block@0x3B9080  code@0x3B9098  size=0x1DF =====
      0018  13 03 00 00       store  [loc+0]
      001C  02 03 01 00 00 00 push   #1
      0022  83 03 28 00       store  [heap+40]
      0026  72 01 00 00       pushblk[glob+0] x1
      002A  79 03             idxadd 3
      002C  7a 01             pushblk.heap x1
      002E  42 01 10 00 00 00 push   #16
      0034  42 01 20 4e 00 00 push   #20000
      003A  a2 00 00 00       push   [heap+0]
      003E  0b 4a             SpawnObj()
      0040  03 4a 08 00       store  [loc+8]
      0044  12 4a 00 00 20 41 push   #10f
      004A  18 06 29 05       call   L0AA0 locals=6
      004E  72 01 00 00       pushblk[glob+0] x1
      0052  7a 01             pushblk.heap x1
      0054  0b 16             GetActor()
      0056  72 01 00 00       pushblk[glob+0] x1
      005A  79 04             idxadd 4
      005C  7a 01             pushblk.heap x1
      005E  0b 17             MakeAttack()
      0060  03 17 0c 00       store  [loc+12]
      0064  32 01 0c 00       pushblk[loc+12] x1
      0068  30 0c             dup
      006A  3a 01             pushblk.heap x1
      006C  02 01 80 00 00 00 push   #128
      0072  01 06             or.i
      0074  00 07             blkcopy
      0076  32 01 0c 00       pushblk[loc+12] x1
      007A  39 02             idxadd 2
      007C  72 01 00 00       pushblk[glob+0] x1
      0080  79 03             idxadd 3
      0082  7a 01             pushblk.heap x1
      0084  70 07             blkcopy
      0086  32 01 0c 00       pushblk[loc+12] x1
      008A  a2 00 00 00       push   [heap+0]
      008E  0b 4c             ObjOp2()
      0090  12 4c 00 00 00 00 push   #0f
      0096  13 4c 10 00       store  [loc+16]
L009A: 009A  32 01 10 00       pushblk[loc+16] x1
      009E  b2 01 24 00       pushblk[heap+36] x1
      00A2  91 01             sub.f
      00A4  97 00             cmp.ltz.f
      00A6  95 00 30 00       bz     L010A
      00AA  a2 00 00 00       push   [heap+0]
      00AE  a2 00 10 00       push   [heap+16]
      00B2  b2 01 20 00       pushblk[heap+32] x1
      00B6  0b 12             MoveByVel()
      00B8  32 01 08 00       pushblk[loc+8] x1
      00BC  a2 00 00 00       push   [heap+0]
      00C0  0b 10             SetVec()
      00C2  32 01 0c 00       pushblk[loc+12] x1
      00C6  39 04             idxadd 4
      00C8  a2 00 00 00       push   [heap+0]
      00CC  aa 04             pushblk.heap x4
      00CE  a0 07             blkcopy
      00D0  32 01 0c 00       pushblk[loc+12] x1
      00D4  30 0c             dup
      00D6  3a 01             pushblk.heap x1
      00D8  02 01 04 00 00 00 push   #4
      00DE  01 06             or.i
      00E0  00 07             blkcopy
      00E2  00 00             end   ; ---- routine end ----
      00E4  32 01 0c 00       pushblk[loc+12] x1
      00E8  38 06 45 01       call   L0376 locals=6
      00EC  35 06 04 00       bz     L00F8
      00F0  34 06 0b 00       jmp    L010A
      00F4  34 06 00 00       jmp    L00F8
L00F8: 00F8  22 00 10 00       push   [loc+16]
      00FC  20 0c             dup
      00FE  2a 01             pushblk.heap x1
      0100  0b 05             NATIVE t0 #0x05
      0102  11 00             add.f
      0104  10 07             blkcopy
      0106  14 07 c8 ff       jmp    L009A
L010A: 010A  32 01 08 00       pushblk[loc+8] x1
      010E  12 01 00 00 00 41 push   #8f
      0114  0b 91             NATIVE t0 #0x91
      0116  72 01 00 00       pushblk[glob+0] x1
      011A  79 03             idxadd 3
      011C  7a 01             pushblk.heap x1
      011E  42 01 11 00 00 00 push   #17
      0124  42 01 20 4e 00 00 push   #20000
      012A  a2 00 00 00       push   [heap+0]
      012E  0b 4a             SpawnObj()
      0130  00 04             pop
      0132  32 01 0c 00       pushblk[loc+12] x1
      0136  39 03             idxadd 3
      0138  12 03 00 00 f0 42 push   #120f
      013E  10 07             blkcopy
      0140  12 07 00 00 00 00 push   #0f
      0146  13 07 10 00       store  [loc+16]
L014A: 014A  32 01 10 00       pushblk[loc+16] x1
      014E  12 01 00 00 f0 41 push   #30f
      0154  11 01             sub.f
      0156  17 00             cmp.ltz.f
      0158  15 00 1a 00       bz     L0190
      015C  32 01 0c 00       pushblk[loc+12] x1
      0160  39 04             idxadd 4
      0162  a2 00 00 00       push   [heap+0]
      0166  aa 04             pushblk.heap x4
      0168  a0 07             blkcopy
      016A  32 01 0c 00       pushblk[loc+12] x1
      016E  30 0c             dup
      0170  3a 01             pushblk.heap x1
      0172  02 01 04 00 00 00 push   #4
      0178  01 06             or.i
      017A  00 07             blkcopy
      017C  00 00             end   ; ---- routine end ----
      017E  22 00 10 00       push   [loc+16]
      0182  20 0c             dup
      0184  2a 01             pushblk.heap x1
      0186  0b 05             NATIVE t0 #0x05
      0188  11 00             add.f
      018A  10 07             blkcopy
      018C  14 07 dd ff       jmp    L014A
L0190: 0190  02 07 00 00 00 00 push   #0
      0196  83 07 28 00       store  [heap+40]
      019A  0b b2             ClearChainFlags?()
      019C  00 03             tailcall
      019E  03 03 00 00       store  [loc+0]
      01A2  b2 01 28 00       pushblk[heap+40] x1
      01A6  b0 03             tailcall
      01A8  33 03 00 00       store  [loc+0]
      01AC  72 01 00 00       pushblk[glob+0] x1
      01B0  7a 01             pushblk.heap x1
      01B2  42 01 03 80 00 00 push   #32771
      01B8  52 01 00 00 00 00 push   #0f
      01BE  a2 00 00 00       push   [heap+0]
      01C2  0b 13             NATIVE t0 #0x13
      01C4  a2 00 10 00       push   [heap+16]
      01C8  92 00 00 00 00 00 push   #0f
      01CE  92 00 00 00 00 00 push   #0f
      01D4  92 00 00 00 00 00 push   #0f
      01DA  92 00 00 00 00 00 push   #0f
      01E0  98 02 d2 00       call   L0388 locals=2

; ===== ex_3000_02.bd  block@0x3B9B80  code@0x3B9B98  size=0x151 =====
      0018  13 03 00 00       store  [loc+0]
      001C  72 01 00 00       pushblk[glob+0] x1
      0020  79 03             idxadd 3
      0022  7a 01             pushblk.heap x1
      0024  42 01 20 00 00 00 push   #32
      002A  42 01 20 4e 00 00 push   #20000
      0030  0b 0f             NATIVE t0 #0x0f
      0032  03 0f 0c 00       store  [loc+12]
      0036  72 01 00 00       pushblk[glob+0] x1
      003A  79 03             idxadd 3
      003C  7a 01             pushblk.heap x1
      003E  42 01 21 00 00 00 push   #33
      0044  42 01 20 4e 00 00 push   #20000
      004A  0b 0f             NATIVE t0 #0x0f
      004C  03 0f 08 00       store  [loc+8]
L0050: 0050  32 01 0c 00       pushblk[loc+12] x1
      0054  38 0e ba 00       call   L01CC locals=14
      0058  30 0c             dup
      005A  36 0c 05 00       bnz    L0068
      005E  32 01 08 00       pushblk[loc+8] x1
      0062  38 0e b3 00       call   L01CC locals=14
      0066  01 0b             lor.i
L0068: 0068  05 0b 39 00       bz     L00DE
      006C  72 01 00 00       pushblk[glob+0] x1
      0070  79 01             idxadd 1
      0072  7a 01             pushblk.heap x1
      0074  42 01 03 80 00 00 push   #32771
      007A  52 01 00 00 00 00 push   #0f
      0080  22 00 20 00       push   [loc+32]
      0084  0b 13             NATIVE t0 #0x13
      0086  32 01 0c 00       pushblk[loc+12] x1
      008A  38 0e 9f 00       call   L01CC locals=14
      008E  35 0e 16 00       bz     L00BE
      0092  22 00 20 00       push   [loc+32]
      0096  2a 04             pushblk.heap x4
      0098  23 04 10 00       store  [loc+16]
      009C  22 00 10 00       push   [loc+16]
      00A0  29 01             idxadd 1
      00A2  20 0c             dup
      00A4  2a 01             pushblk.heap x1
      00A6  12 01 00 00 70 42 push   #60f
      00AC  11 01             sub.f
      00AE  10 07             blkcopy
      00B0  32 01 0c 00       pushblk[loc+12] x1
      00B4  22 00 10 00       push   [loc+16]
      00B8  0b 10             SetVec()
      00BA  04 10 00 00       jmp    L00BE
L00BE: 00BE  32 01 08 00       pushblk[loc+8] x1
      00C2  38 0e 83 00       call   L01CC locals=14
      00C6  35 0e 07 00       bz     L00D8
      00CA  32 01 08 00       pushblk[loc+8] x1
      00CE  22 00 20 00       push   [loc+32]
      00D2  0b 10             SetVec()
      00D4  04 10 00 00       jmp    L00D8
L00D8: 00D8  00 00             end   ; ---- routine end ----
      00DA  04 00 b9 ff       jmp    L0050
L00DE: 00DE  00 03             tailcall
      00E0  03 03 00 00       store  [loc+0]
      00E4  03 03 04 00       store  [loc+4]
      00E8  0b 19             NATIVE t0 #0x19
      00EA  32 01 00 00       pushblk[loc+0] x1
      00EE  32 01 04 00       pushblk[loc+4] x1
      00F2  11 01             sub.f
      00F4  11 02             mul.f
      00F6  32 01 04 00       pushblk[loc+4] x1
      00FA  11 00             add.f
      00FC  10 03             tailcall
      00FE  13 03 00 00       store  [loc+0]
      0102  b2 01 88 00       pushblk[heap+136] x1
      0106  82 01 01 00 00 00 push   #1
      010C  81 05             and.i
      010E  80 03             tailcall
      0110  03 03 04 00       store  [loc+4]
      0114  03 03 00 00       store  [loc+0]
      0118  32 01 00 00       pushblk[loc+0] x1
      011C  30 0c             dup
      011E  3a 01             pushblk.heap x1
      0120  02 01 80 00 00 00 push   #128
      0126  01 06             or.i
      0128  00 07             blkcopy
      012A  32 01 00 00       pushblk[loc+0] x1
      012E  39 03             idxadd 3
      0130  32 01 04 00       pushblk[loc+4] x1
      0134  30 07             blkcopy
      0136  30 03             tailcall
      0138  33 03 04 00       store  [loc+4]
      013C  33 03 00 00       store  [loc+0]
      0140  32 01 00 00       pushblk[loc+0] x1
      0144  32 01 04 00       pushblk[loc+4] x1
      0148  38 06 0a 00       call   L0160 locals=6
      014C  32 01 00 00       pushblk[loc+0] x1
      0150  30 0c             dup
      0152  3a 01             pushblk.heap x1

; ===== ex_3000_03.bd  block@0x3BA080  code@0x3BA098  size=0x18A =====
      0018  13 03 00 00       store  [loc+0]
      001C  72 01 00 00       pushblk[glob+0] x1
      0020  7a 01             pushblk.heap x1
      0022  0b 16             GetActor()
      0024  72 01 00 00       pushblk[glob+0] x1
      0028  79 04             idxadd 4
      002A  7a 01             pushblk.heap x1
      002C  0b 17             MakeAttack()
      002E  03 17 08 00       store  [loc+8]
      0032  32 01 08 00       pushblk[loc+8] x1
      0036  30 0c             dup
      0038  3a 01             pushblk.heap x1
      003A  02 01 80 00 00 00 push   #128
      0040  01 06             or.i
      0042  00 07             blkcopy
      0044  32 01 08 00       pushblk[loc+8] x1
      0048  39 02             idxadd 2
      004A  72 01 00 00       pushblk[glob+0] x1
      004E  79 03             idxadd 3
      0050  7a 01             pushblk.heap x1
      0052  70 07             blkcopy
      0054  32 01 08 00       pushblk[loc+8] x1
      0058  a2 00 00 00       push   [heap+0]
      005C  0b 4c             ObjOp2()
      005E  32 01 08 00       pushblk[loc+8] x1
      0062  39 04             idxadd 4
      0064  a2 00 00 00       push   [heap+0]
      0068  aa 04             pushblk.heap x4
      006A  a0 07             blkcopy
      006C  92 07 00 00 70 42 push   #60f
      0072  13 07 0c 00       store  [loc+12]
L0076: 0076  12 07 00 00 00 00 push   #0f
      007C  32 01 0c 00       pushblk[loc+12] x1
      0080  11 01             sub.f
      0082  17 00             cmp.ltz.f
      0084  15 00 5a 00       bz     L013C
      0088  a2 00 00 00       push   [heap+0]
      008C  a2 00 10 00       push   [heap+16]
      0090  92 00 00 00 f0 41 push   #30f
      0096  0b 12             MoveByVel()
      0098  32 01 08 00       pushblk[loc+8] x1
      009C  30 0c             dup
      009E  3a 01             pushblk.heap x1
      00A0  02 01 04 00 00 00 push   #4
      00A6  01 06             or.i
      00A8  00 07             blkcopy
      00AA  32 01 08 00       pushblk[loc+8] x1
      00AE  39 04             idxadd 4
      00B0  a2 00 10 00       push   [heap+16]
      00B4  aa 04             pushblk.heap x4
      00B6  a0 07             blkcopy
      00B8  32 01 08 00       pushblk[loc+8] x1
      00BC  39 10             idxadd 16
      00BE  a2 00 10 00       push   [heap+16]
      00C2  aa 04             pushblk.heap x4
      00C4  a0 07             blkcopy
      00C6  32 01 08 00       pushblk[loc+8] x1
      00CA  39 04             idxadd 4
      00CC  12 04 00 00 7a 43 push   #250f
      00D2  0b 5d             NATIVE t0 #0x5d
      00D4  32 01 08 00       pushblk[loc+8] x1
      00D8  39 10             idxadd 16
      00DA  12 10 00 00 7a c3 push   #-250f
      00E0  0b 5d             NATIVE t0 #0x5d
      00E2  32 01 08 00       pushblk[loc+8] x1
      00E6  39 04             idxadd 4
      00E8  a2 00 00 00       push   [heap+0]
      00EC  0b 07             VecAdd()
      00EE  32 01 08 00       pushblk[loc+8] x1
      00F2  39 10             idxadd 16
      00F4  a2 00 00 00       push   [heap+0]
      00F8  0b 07             VecAdd()
      00FA  32 01 08 00       pushblk[loc+8] x1
      00FE  39 03             idxadd 3
      0100  12 03 00 00 16 43 push   #150f
      0106  10 07             blkcopy
      0108  32 01 08 00       pushblk[loc+8] x1
      010C  39 0f             idxadd 15
      010E  12 0f 00 00 16 43 push   #150f
      0114  10 07             blkcopy
      0116  32 01 08 00       pushblk[loc+8] x1
      011A  30 0c             dup
      011C  3a 01             pushblk.heap x1
      011E  02 01 04 00 00 00 push   #4
      0124  01 06             or.i
      0126  00 07             blkcopy
      0128  00 00             end   ; ---- routine end ----
      012A  22 00 0c 00       push   [loc+12]
      012E  20 0c             dup
      0130  2a 01             pushblk.heap x1
      0132  0b 05             NATIVE t0 #0x05
      0134  11 01             sub.f
      0136  10 07             blkcopy
      0138  14 07 9d ff       jmp    L0076
L013C: 013C  10 03             tailcall
      013E  13 03 04 00       store  [loc+4]
      0142  13 03 00 00       store  [loc+0]
      0146  72 01 00 00       pushblk[glob+0] x1
      014A  7a 01             pushblk.heap x1
      014C  79 04             idxadd 4
      014E  7a 04             pushblk.heap x4
      0150  b3 04 00 00       store  [heap+0]
      0154  72 01 00 00       pushblk[glob+0] x1
      0158  7a 01             pushblk.heap x1
      015A  79 0c             idxadd 12
      015C  7a 04             pushblk.heap x4
      015E  b3 04 10 00       store  [heap+16]
      0162  a2 00 10 00       push   [heap+16]
      0166  32 01 04 00       pushblk[loc+4] x1
      016A  0b 0a             RotateDeg()
      016C  00 03             tailcall
      016E  03 03 00 00       store  [loc+0]
      0172  03 03 04 00       store  [loc+4]
      0176  0b 19             NATIVE t0 #0x19
      0178  32 01 00 00       pushblk[loc+0] x1
      017C  32 01 04 00       pushblk[loc+4] x1
      0180  11 01             sub.f
      0182  11 02             mul.f
      0184  32 01 04 00       pushblk[loc+4] x1
      0188  11 00             add.f
      018A  10 03             tailcall
      018C  13 03 00 00       store  [loc+0]

; ===== ex_3000_04.bd  block@0x3BA500  code@0x3BA518  size=0x55A =====
      0018  13 03 00 00       store  [loc+0]
      001C  72 01 00 00       pushblk[glob+0] x1
      0020  79 03             idxadd 3
      0022  7a 01             pushblk.heap x1
      0024  42 01 19 00 00 00 push   #25
      002A  42 01 20 4e 00 00 push   #20000
      0030  a2 00 00 00       push   [heap+0]
      0034  0b 4a             SpawnObj()
      0036  00 04             pop
      0038  72 01 00 00       pushblk[glob+0] x1
      003C  79 03             idxadd 3
      003E  7a 01             pushblk.heap x1
      0040  42 01 1a 00 00 00 push   #26
      0046  42 01 20 4e 00 00 push   #20000
      004C  a2 00 00 00       push   [heap+0]
      0050  0b 4a             SpawnObj()
      0052  03 4a 08 00       store  [loc+8]
      0056  72 01 00 00       pushblk[glob+0] x1
      005A  7a 01             pushblk.heap x1
      005C  0b 16             GetActor()
      005E  72 01 00 00       pushblk[glob+0] x1
      0062  79 04             idxadd 4
      0064  7a 01             pushblk.heap x1
      0066  0b 17             MakeAttack()
      0068  03 17 0c 00       store  [loc+12]
      006C  32 01 0c 00       pushblk[loc+12] x1
      0070  02 01 03 00 00 00 push   #3
      0076  0b d5             SetFlag2()
      0078  32 01 0c 00       pushblk[loc+12] x1
      007C  39 14             idxadd 20
      007E  12 14 00 00 20 41 push   #10f
      0084  10 07             blkcopy
      0086  32 01 0c 00       pushblk[loc+12] x1
      008A  30 0c             dup
      008C  3a 01             pushblk.heap x1
      008E  02 01 40 00 00 00 push   #64
      0094  01 06             or.i
      0096  00 07             blkcopy
      0098  32 01 0c 00       pushblk[loc+12] x1
      009C  39 02             idxadd 2
      009E  72 01 00 00       pushblk[glob+0] x1
      00A2  79 03             idxadd 3
      00A4  7a 01             pushblk.heap x1
      00A6  70 07             blkcopy
      00A8  32 01 0c 00       pushblk[loc+12] x1
      00AC  a2 00 00 00       push   [heap+0]
      00B0  0b 4c             ObjOp2()
      00B2  22 00 20 00       push   [loc+32]
      00B6  12 00 00 00 00 00 push   #0f
      00BC  12 00 00 00 80 3f push   #1f
      00C2  12 00 00 00 00 00 push   #0f
      00C8  12 00 00 00 00 00 push   #0f
      00CE  18 16 d6 04       call   L0A7E locals=22
      00D2  10 04             pop
L00D4: 00D4  a2 00 00 00       push   [heap+0]
      00D8  22 00 20 00       push   [loc+32]
      00DC  12 00 00 00 48 42 push   #50f
      00E2  0b 12             MoveByVel()
      00E4  32 01 08 00       pushblk[loc+8] x1
      00E8  a2 00 00 00       push   [heap+0]
      00EC  0b 10             SetVec()
      00EE  32 01 08 00       pushblk[loc+8] x1
      00F2  38 16 ce 01       call   L0492 locals=22
      00F6  32 01 0c 00       pushblk[loc+12] x1
      00FA  39 04             idxadd 4
      00FC  a2 00 00 00       push   [heap+0]
      0100  aa 04             pushblk.heap x4
      0102  a0 07             blkcopy
      0104  32 01 0c 00       pushblk[loc+12] x1
      0108  30 0c             dup
      010A  3a 01             pushblk.heap x1
      010C  02 01 04 00 00 00 push   #4
      0112  01 06             or.i
      0114  00 07             blkcopy
      0116  00 00             end   ; ---- routine end ----
      0118  32 01 0c 00       pushblk[loc+12] x1
      011C  38 16 a6 04       call   L0A6C locals=22
      0120  35 16 04 00       bz     L012C
      0124  34 16 04 00       jmp    L0130
      0128  34 16 00 00       jmp    L012C
L012C: 012C  34 16 d2 ff       jmp    L00D4
L0130: 0130  a2 00 00 00       push   [heap+0]
      0134  aa 04             pushblk.heap x4
      0136  23 04 10 00       store  [loc+16]
      013A  22 00 10 00       push   [loc+16]
      013E  29 01             idxadd 1
      0140  20 0c             dup
      0142  2a 01             pushblk.heap x1
      0144  12 01 00 00 7a 44 push   #1000f
      014A  11 01             sub.f
      014C  10 07             blkcopy
      014E  22 00 10 00       push   [loc+16]
      0152  29 01             idxadd 1
      0154  22 00 10 00       push   [loc+16]
      0158  28 16 47 03       call   L07EA locals=22
      015C  20 07             blkcopy
      015E  72 01 00 00       pushblk[glob+0] x1
      0162  79 03             idxadd 3
      0164  7a 01             pushblk.heap x1
      0166  42 01 1b 00 00 00 push   #27
      016C  42 01 20 4e 00 00 push   #20000
      0172  22 00 10 00       push   [loc+16]
      0176  0b 4a             SpawnObj()
      0178  00 04             pop
      017A  a2 00 10 00       push   [heap+16]
      017E  a2 00 00 00       push   [heap+0]
      0182  a8 16 a1 02       call   L06C8 locals=22
      0186  a2 00 10 00       push   [heap+16]
      018A  82 00 7f 02 00 00 push   #639
      0190  0b 14             GetObj?()
      0192  00 04             pop
      0194  a2 00 00 00       push   [heap+0]
      0198  a9 01             idxadd 1
      019A  aa 01             pushblk.heap x1
      019C  23 01 4c 00       store  [loc+76]
      01A0  12 01 00 00 34 43 push   #180f
      01A6  12 01 00 00 48 43 push   #200f
      01AC  18 16 51 03       call   L0852 locals=22
      01B0  10 0a             fneg
      01B2  13 0a 48 00       store  [loc+72]
      01B6  12 0a 00 00 00 00 push   #0f
      01BC  13 0a 50 00       store  [loc+80]
L01C0: 01C0  32 01 50 00       pushblk[loc+80] x1
      01C4  12 01 00 00 f0 41 push   #30f
      01CA  11 01             sub.f
      01CC  17 00             cmp.ltz.f
      01CE  15 00 38 00       bz     L0242
      01D2  a2 00 00 00       push   [heap+0]
      01D6  a9 01             idxadd 1
      01D8  32 01 50 00       pushblk[loc+80] x1
      01DC  12 01 00 00 f0 41 push   #30f
      01E2  11 03             div.f
      01E4  12 03 00 00 b4 42 push   #90f
      01EA  11 02             mul.f
      01EC  0b 02             SinDeg()
      01EE  32 01 48 00       pushblk[loc+72] x1
      01F2  11 02             mul.f
      01F4  32 01 4c 00       pushblk[loc+76] x1
      01F8  11 00             add.f
      01FA  10 07             blkcopy
      01FC  32 01 08 00       pushblk[loc+8] x1
      0200  a2 00 00 00       push   [heap+0]
      0204  0b 10             SetVec()
      0206  32 01 08 00       pushblk[loc+8] x1
      020A  38 16 42 01       call   L0492 locals=22
      020E  32 01 0c 00       pushblk[loc+12] x1
      0212  39 04             idxadd 4
      0214  a2 00 00 00       push   [heap+0]
      0218  aa 04             pushblk.heap x4
      021A  a0 07             blkcopy
      021C  32 01 0c 00       pushblk[loc+12] x1
      0220  30 0c             dup
      0222  3a 01             pushblk.heap x1
      0224  02 01 04 00 00 00 push   #4
      022A  01 06             or.i
      022C  00 07             blkcopy
      022E  00 00             end   ; ---- routine end ----
      0230  22 00 50 00       push   [loc+80]
      0234  20 0c             dup
      0236  2a 01             pushblk.heap x1
      0238  0b 05             NATIVE t0 #0x05
      023A  11 00             add.f
      023C  10 07             blkcopy
      023E  14 07 bf ff       jmp    L01C0
L0242: 0242  b2 01 20 00       pushblk[heap+32] x1
      0246  b0 0d             lnot
      0248  b5 0d 17 00       bz     L027A
      024C  32 01 08 00       pushblk[loc+8] x1
      0250  38 16 1f 01       call   L0492 locals=22
      0254  32 01 0c 00       pushblk[loc+12] x1
      0258  30 0c             dup
      025A  3a 01             pushblk.heap x1
      025C  02 01 04 00 00 00 push   #4
      0262  01 06             or.i
      0264  00 07             blkcopy
      0266  00 00             end   ; ---- routine end ----
      0268  22 00 50 00       push   [loc+80]
      026C  20 0c             dup
      026E  2a 01             pushblk.heap x1
      0270  0b 05             NATIVE t0 #0x05
      0272  11 00             add.f
      0274  10 07             blkcopy
      0276  14 07 e4 ff       jmp    L0242
L027A: 027A  72 01 00 00       pushblk[glob+0] x1
      027E  7a 01             pushblk.heap x1
      0280  79 04             idxadd 4
      0282  7a 04             pushblk.heap x4
      0284  33 04 30 00       store  [loc+48]
      0288  22 00 30 00       push   [loc+48]
      028C  29 01             idxadd 1
      028E  a2 00 00 00       push   [heap+0]
      0292  a9 01             idxadd 1
      0294  aa 01             pushblk.heap x1
      0296  a0 07             blkcopy
      0298  a2 00 00 00       push   [heap+0]
      029C  aa 04             pushblk.heap x4
      029E  23 04 20 00       store  [loc+32]
      02A2  22 00 20 00       push   [loc+32]
      02A6  22 00 30 00       push   [loc+48]
      02AA  0b 08             VecSub()
      02AC  12 08 00 00 40 40 push   #3f
      02B2  12 08 00 00 a0 40 push   #5f
      02B8  18 16 cb 02       call   L0852 locals=22
      02BC  13 16 40 00       store  [loc+64]
      02C0  12 16 00 00 00 00 push   #0f
      02C6  13 16 44 00       store  [loc+68]
      02CA  12 16 00 00 f0 41 push   #30f
      02D0  13 16 50 00       store  [loc+80]
L02D4: 02D4  12 16 00 00 00 00 push   #0f
      02DA  32 01 50 00       pushblk[loc+80] x1
      02DE  11 01             sub.f
      02E0  17 00             cmp.ltz.f
      02E2  15 00 6a 00       bz     L03BA
      02E6  22 00 44 00       push   [loc+68]
      02EA  20 0c             dup
      02EC  2a 01             pushblk.heap x1
      02EE  12 01 cd cc cc 3d push   #0.1f
      02F4  0b 05             NATIVE t0 #0x05
      02F6  11 02             mul.f
      02F8  11 00             add.f
      02FA  10 07             blkcopy
      02FC  32 01 40 00       pushblk[loc+64] x1
      0300  32 01 44 00       pushblk[loc+68] x1
      0304  11 01             sub.f
      0306  17 00             cmp.ltz.f
      0308  15 00 06 00       bz     L0318
      030C  32 01 40 00       pushblk[loc+64] x1
      0310  33 01 44 00       store  [loc+68]
      0314  34 01 00 00       jmp    L0318
L0318: 0318  b2 01 24 00       pushblk[heap+36] x1
      031C  b0 0d             lnot
      031E  b5 0d 07 00       bz     L0330
      0322  22 00 20 00       push   [loc+32]
      0326  32 01 44 00       pushblk[loc+68] x1
      032A  0b 0a             RotateDeg()
      032C  04 0a 0b 00       jmp    L0346
L0330: 0330  22 00 20 00       push   [loc+32]
      0334  32 01 44 00       pushblk[loc+68] x1
      0338  12 01 00 00 80 bf push   #-1f
      033E  11 02             mul.f
      0340  0b 0a             RotateDeg()
      0342  04 0a 00 00       jmp    L0346
L0346: 0346  22 00 30 00       push   [loc+48]
      034A  2a 04             pushblk.heap x4
      034C  a3 04 00 00       store  [heap+0]
      0350  a2 00 00 00       push   [heap+0]
      0354  22 00 20 00       push   [loc+32]
      0358  0b 07             VecAdd()
      035A  32 01 08 00       pushblk[loc+8] x1
      035E  38 16 98 00       call   L0492 locals=22
      0362  32 01 08 00       pushblk[loc+8] x1
      0366  a2 00 00 00       push   [heap+0]
      036A  0b 10             SetVec()
      036C  32 01 0c 00       pushblk[loc+12] x1
      0370  39 04             idxadd 4
      0372  a2 00 00 00       push   [heap+0]
      0376  aa 04             pushblk.heap x4
      0378  a0 07             blkcopy
      037A  32 01 0c 00       pushblk[loc+12] x1
      037E  30 0c             dup
      0380  3a 01             pushblk.heap x1
      0382  02 01 04 00 00 00 push   #4
      0388  01 06             or.i
      038A  00 07             blkcopy
      038C  00 00             end   ; ---- routine end ----
      038E  72 01 00 00       pushblk[glob+0] x1
      0392  7a 01             pushblk.heap x1
      0394  0b 33             GetActionState()
      0396  02 33 e7 00 00 00 push   #231
      039C  01 01             sub.i
      039E  07 03             cmp.nez.i
      03A0  05 03 09 00       bz     L03B6
      03A4  22 00 50 00       push   [loc+80]
      03A8  20 0c             dup
      03AA  2a 01             pushblk.heap x1
      03AC  0b 05             NATIVE t0 #0x05
      03AE  11 01             sub.f
      03B0  10 07             blkcopy
      03B2  14 07 00 00       jmp    L03B6
L03B6: 03B6  14 07 8d ff       jmp    L02D4
L03BA: 03BA  32 01 0c 00       pushblk[loc+12] x1
      03BE  02 01 00 00 00 00 push   #0
      03C4  0b d5             SetFlag2()
      03C6  32 01 08 00       pushblk[loc+8] x1
      03CA  12 01 00 00 00 41 push   #8f
      03D0  0b 91             NATIVE t0 #0x91
      03D2  72 01 00 00       pushblk[glob+0] x1
      03D6  79 03             idxadd 3
      03D8  7a 01             pushblk.heap x1
      03DA  42 01 33 00 00 00 push   #51
      03E0  42 01 20 4e 00 00 push   #20000
      03E6  a2 00 00 00       push   [heap+0]
      03EA  0b 4a             SpawnObj()
      03EC  00 04             pop
      03EE  72 01 00 00       pushblk[glob+0] x1
      03F2  7a 01             pushblk.heap x1
      03F4  0b 16             GetActor()
      03F6  72 01 00 00       pushblk[glob+0] x1
      03FA  79 04             idxadd 4
      03FC  7a 01             pushblk.heap x1
      03FE  0b 17             MakeAttack()
      0400  03 17 0c 00       store  [loc+12]
      0404  32 01 0c 00       pushblk[loc+12] x1
      0408  30 0c             dup
      040A  3a 01             pushblk.heap x1
      040C  02 01 c0 00 00 00 push   #192
      0412  01 06             or.i
      0414  00 07             blkcopy
      0416  32 01 0c 00       pushblk[loc+12] x1
      041A  39 02             idxadd 2
      041C  72 01 00 00       pushblk[glob+0] x1
      0420  79 03             idxadd 3
      0422  7a 01             pushblk.heap x1
      0424  70 07             blkcopy
      0426  32 01 0c 00       pushblk[loc+12] x1
      042A  a2 00 00 00       push   [heap+0]
      042E  0b 4c             ObjOp2()
      0430  32 01 0c 00       pushblk[loc+12] x1
      0434  39 03             idxadd 3
      0436  12 03 00 00 96 43 push   #300f
      043C  10 07             blkcopy
      043E  12 07 00 00 00 00 push   #0f
      0444  13 07 50 00       store  [loc+80]
L0448: 0448  32 01 50 00       pushblk[loc+80] x1
      044C  12 01 00 00 f0 41 push   #30f
      0452  11 01             sub.f
      0454  17 00             cmp.ltz.f
      0456  15 00 1a 00       bz     L048E
      045A  32 01 0c 00       pushblk[loc+12] x1
      045E  39 04             idxadd 4
      0460  a2 00 00 00       push   [heap+0]
      0464  aa 04             pushblk.heap x4
      0466  a0 07             blkcopy
      0468  32 01 0c 00       pushblk[loc+12] x1
      046C  30 0c             dup
      046E  3a 01             pushblk.heap x1
      0470  02 01 04 00 00 00 push   #4
      0476  01 06             or.i
      0478  00 07             blkcopy
      047A  00 00             end   ; ---- routine end ----
      047C  22 00 50 00       push   [loc+80]
      0480  20 0c             dup
      0482  2a 01             pushblk.heap x1
      0484  0b 05             NATIVE t0 #0x05
      0486  11 00             add.f
      0488  10 07             blkcopy
      048A  14 07 dd ff       jmp    L0448
L048E: 048E  0b b2             ClearChainFlags?()
      0490  00 03             tailcall
L0492: 0492  03 03 00 00       store  [loc+0]
      0496  32 01 00 00       pushblk[loc+0] x1
      049A  22 00 10 00       push   [loc+16]
      049E  4b 0a             GetRotation()
      04A0  22 00 10 00       push   [loc+16]
      04A4  29 01             idxadd 1
      04A6  20 0c             dup
      04A8  2a 01             pushblk.heap x1
      04AA  12 01 b1 fb 0e 3c push   #0.008727f
      04B0  0b 05             NATIVE t0 #0x05
      04B2  11 02             mul.f
      04B4  11 00             add.f
      04B6  10 07             blkcopy
      04B8  32 01 00 00       pushblk[loc+0] x1
      04BC  22 00 10 00       push   [loc+16]
      04C0  0b 37             SetRotation()
      04C2  00 03             tailcall
      04C4  03 03 00 00       store  [loc+0]
      04C8  02 03 01 00 00 00 push   #1
      04CE  83 03 20 00       store  [heap+32]
      04D2  80 03             tailcall
      04D4  03 03 04 00       store  [loc+4]
      04D8  03 03 08 00       store  [loc+8]
      04DC  03 03 00 00       store  [loc+0]
      04E0  32 01 08 00       pushblk[loc+8] x1
      04E4  3a 04             pushblk.heap x4
      04E6  b3 04 00 00       store  [heap+0]
      04EA  82 04 00 00 00 00 push   #0
      04F0  83 04 20 00       store  [heap+32]
      04F4  32 01 04 00       pushblk[loc+4] x1
      04F8  b3 01 24 00       store  [heap+36]
      04FC  b0 03             tailcall
      04FE  33 03 00 00       store  [loc+0]
      0502  72 01 00 00       pushblk[glob+0] x1
      0506  79 03             idxadd 3
      0508  7a 01             pushblk.heap x1
      050A  42 01 1d 00 00 00 push   #29
      0510  42 01 20 4e 00 00 push   #20000
      0516  a2 00 00 00       push   [heap+0]
      051A  0b 4a             SpawnObj()
      051C  00 04             pop
      051E  12 04 00 00 a0 41 push   #20f
      0524  12 04 00 00 80 40 push   #4f
      052A  12 04 00 00 00 00 push   #0f
      0530  12 04 00 00 80 40 push   #4f
      0536  02 04 01 00 00 00 push   #1
      053C  4b 0e             SetTimedMove()
      053E  72 01 00 00       pushblk[glob+0] x1
      0542  7a 01             pushblk.heap x1
      0544  42 01 00 00 00 00 push   #0
      054A  72 01 00 00       pushblk[glob+0] x1
      054E  79 05             idxadd 5
      0550  7a 01             pushblk.heap x1
      0552  0b 17             MakeAttack()
      0554  03 17 20 00       store  [loc+32]
      0558  32 01 20 00       pushblk[loc+32] x1
      055C  30 0c             dup

; ===== ex_3000_05.bd  block@0x3BB200  code@0x3BB218  size=0x3AE =====
      0018  13 03 00 00       store  [loc+0]
      001C  12 03 00 00 00 00 push   #0f
      0022  13 03 48 00       store  [loc+72]
      0026  72 01 00 00       pushblk[glob+0] x1
      002A  79 03             idxadd 3
      002C  7a 01             pushblk.heap x1
      002E  42 01 13 00 00 00 push   #19
      0034  42 01 20 4e 00 00 push   #20000
      003A  a2 00 00 00       push   [heap+0]
      003E  0b 4a             SpawnObj()
      0040  03 4a 18 00       store  [loc+24]
      0044  72 01 00 00       pushblk[glob+0] x1
      0048  79 03             idxadd 3
      004A  7a 01             pushblk.heap x1
      004C  42 01 14 00 00 00 push   #20
      0052  42 01 20 4e 00 00 push   #20000
      0058  a2 00 00 00       push   [heap+0]
      005C  0b 4a             SpawnObj()
      005E  03 4a 14 00       store  [loc+20]
      0062  72 01 00 00       pushblk[glob+0] x1
      0066  79 03             idxadd 3
      0068  7a 01             pushblk.heap x1
      006A  42 01 18 00 00 00 push   #24
      0070  42 01 20 4e 00 00 push   #20000
      0076  0b 0f             NATIVE t0 #0x0f
      0078  03 0f 10 00       store  [loc+16]
      007C  a2 00 00 00       push   [heap+0]
      0080  aa 04             pushblk.heap x4
      0082  23 04 20 00       store  [loc+32]
      0086  22 00 20 00       push   [loc+32]
      008A  29 01             idxadd 1
      008C  a2 00 00 00       push   [heap+0]
      0090  a8 16 38 02       call   L0504 locals=22
      0094  92 16 00 00 20 41 push   #10f
      009A  91 01             sub.f
      009C  90 07             blkcopy
      009E  72 01 00 00       pushblk[glob+0] x1
      00A2  7a 01             pushblk.heap x1
      00A4  0b 16             GetActor()
      00A6  72 01 00 00       pushblk[glob+0] x1
      00AA  79 04             idxadd 4
      00AC  7a 01             pushblk.heap x1
      00AE  0b 17             MakeAttack()
      00B0  03 17 08 00       store  [loc+8]
      00B4  32 01 08 00       pushblk[loc+8] x1
      00B8  30 0c             dup
      00BA  3a 01             pushblk.heap x1
      00BC  02 01 c0 00 00 00 push   #192
      00C2  01 06             or.i
      00C4  00 07             blkcopy
      00C6  32 01 08 00       pushblk[loc+8] x1
      00CA  39 02             idxadd 2
      00CC  72 01 00 00       pushblk[glob+0] x1
      00D0  79 03             idxadd 3
      00D2  7a 01             pushblk.heap x1
      00D4  70 07             blkcopy
      00D6  32 01 08 00       pushblk[loc+8] x1
      00DA  a2 00 00 00       push   [heap+0]
      00DE  0b 4c             ObjOp2()
      00E0  22 00 30 00       push   [loc+48]
      00E4  12 00 00 00 00 00 push   #0f
      00EA  12 00 00 00 80 bf push   #-1f
      00F0  12 00 00 00 00 00 push   #0f
      00F6  12 00 00 00 00 00 push   #0f
      00FC  18 16 13 03       call   L0726 locals=22
      0100  10 04             pop
      0102  12 04 00 00 00 00 push   #0f
      0108  13 04 44 00       store  [loc+68]
L010C: 010C  b2 01 10 00       pushblk[heap+16] x1
      0110  b0 0d             lnot
      0112  b5 0d 93 00       bz     L023C
      0116  92 0d 00 00 f0 42 push   #120f
      011C  32 01 44 00       pushblk[loc+68] x1
      0120  11 01             sub.f
      0122  17 00             cmp.ltz.f
      0124  15 00 0a 00       bz     L013C
      0128  a2 00 00 00       push   [heap+0]
      012C  22 00 30 00       push   [loc+48]
      0130  12 00 00 00 00 3f push   #0.5f
      0136  0b 12             MoveByVel()
      0138  04 12 00 00       jmp    L013C
L013C: 013C  32 01 18 00       pushblk[loc+24] x1
      0140  a2 00 00 00       push   [heap+0]
      0144  0b 10             SetVec()
      0146  32 01 14 00       pushblk[loc+20] x1
      014A  a2 00 00 00       push   [heap+0]
      014E  0b 10             SetVec()
      0150  32 01 08 00       pushblk[loc+8] x1
      0154  39 03             idxadd 3
      0156  12 03 00 00 fa 43 push   #500f
      015C  32 01 48 00       pushblk[loc+72] x1
      0160  11 02             mul.f
      0162  10 07             blkcopy
      0164  32 01 08 00       pushblk[loc+8] x1
      0168  39 04             idxadd 4
      016A  a2 00 00 00       push   [heap+0]
      016E  aa 04             pushblk.heap x4
      0170  a0 07             blkcopy
      0172  32 01 08 00       pushblk[loc+8] x1
      0176  30 0c             dup
      0178  3a 01             pushblk.heap x1
      017A  02 01 04 00 00 00 push   #4
      0180  01 06             or.i
      0182  00 07             blkcopy
      0184  22 00 48 00       push   [loc+72]
      0188  20 0c             dup
      018A  2a 01             pushblk.heap x1
      018C  12 01 6f 12 03 3b push   #0.002f
      0192  0b 05             NATIVE t0 #0x05
      0194  11 02             mul.f
      0196  11 00             add.f
      0198  10 07             blkcopy
      019A  12 07 00 00 80 3f push   #1f
      01A0  32 01 48 00       pushblk[loc+72] x1
      01A4  11 01             sub.f
      01A6  17 00             cmp.ltz.f
      01A8  15 00 07 00       bz     L01BA
      01AC  12 00 00 00 80 3f push   #1f
      01B2  13 00 48 00       store  [loc+72]
      01B6  14 00 00 00       jmp    L01BA
L01BA: 01BA  12 00 00 00 b4 42 push   #90f
      01C0  32 01 48 00       pushblk[loc+72] x1
      01C4  11 02             mul.f
      01C6  0b 02             SinDeg()
      01C8  03 02 40 00       store  [loc+64]
      01CC  22 00 20 00       push   [loc+32]
      01D0  32 01 40 00       pushblk[loc+64] x1
      01D4  32 01 40 00       pushblk[loc+64] x1
      01D8  32 01 40 00       pushblk[loc+64] x1
      01DC  12 01 00 00 00 00 push   #0f
      01E2  18 16 a0 02       call   L0726 locals=22
      01E6  10 04             pop
      01E8  32 01 14 00       pushblk[loc+20] x1
      01EC  22 00 20 00       push   [loc+32]
      01F0  0b 27             NATIVE t0 #0x27
      01F2  32 01 10 00       pushblk[loc+16] x1
      01F6  22 00 20 00       push   [loc+32]
      01FA  0b 27             NATIVE t0 #0x27
      01FC  a2 00 00 00       push   [heap+0]
      0200  aa 04             pushblk.heap x4
      0202  23 04 20 00       store  [loc+32]
      0206  22 00 20 00       push   [loc+32]
      020A  29 01             idxadd 1
      020C  a2 00 00 00       push   [heap+0]
      0210  a8 16 78 01       call   L0504 locals=22
      0214  92 16 00 00 20 41 push   #10f
      021A  91 01             sub.f
      021C  90 07             blkcopy
      021E  32 01 10 00       pushblk[loc+16] x1
      0222  22 00 20 00       push   [loc+32]
      0226  0b 10             SetVec()
      0228  00 00             end   ; ---- routine end ----
      022A  22 00 44 00       push   [loc+68]
      022E  20 0c             dup
      0230  2a 01             pushblk.heap x1
      0232  0b 05             NATIVE t0 #0x05
      0234  11 00             add.f
      0236  10 07             blkcopy
      0238  14 07 68 ff       jmp    L010C
L023C: 023C  32 01 18 00       pushblk[loc+24] x1
      0240  12 01 00 00 00 41 push   #8f
      0246  0b 91             NATIVE t0 #0x91
      0248  72 01 00 00       pushblk[glob+0] x1
      024C  79 01             idxadd 1
      024E  7a 01             pushblk.heap x1
      0250  42 01 03 80 00 00 push   #32771
      0256  52 01 00 00 00 00 push   #0f
      025C  22 00 30 00       push   [loc+48]
      0260  0b 13             NATIVE t0 #0x13
      0262  22 00 30 00       push   [loc+48]
      0266  a2 00 00 00       push   [heap+0]
      026A  0b 08             VecSub()
      026C  22 00 30 00       push   [loc+48]
      0270  29 01             idxadd 1
      0272  12 01 00 00 00 00 push   #0f
      0278  10 07             blkcopy
      027A  22 00 30 00       push   [loc+48]
      027E  0b 09             NATIVE t0 #0x09
      0280  12 09 00 00 00 00 push   #0f
      0286  13 09 44 00       store  [loc+68]
L028A: 028A  32 01 44 00       pushblk[loc+68] x1
      028E  12 01 00 00 70 43 push   #240f
      0294  11 01             sub.f
      0296  17 00             cmp.ltz.f
      0298  15 00 6d 00       bz     L0376
      029C  72 01 00 00       pushblk[glob+0] x1
      02A0  79 01             idxadd 1
      02A2  7a 01             pushblk.heap x1
      02A4  42 01 03 80 00 00 push   #32771
      02AA  52 01 00 00 00 00 push   #0f
      02B0  22 00 20 00       push   [loc+32]
      02B4  0b 13             NATIVE t0 #0x13
      02B6  22 00 20 00       push   [loc+32]
      02BA  a2 00 00 00       push   [heap+0]
      02BE  0b 08             VecSub()
      02C0  22 00 20 00       push   [loc+32]
      02C4  0b 06             NATIVE t0 #0x06
      02C6  12 06 00 00 96 43 push   #300f
      02CC  11 01             sub.f
      02CE  17 00             cmp.ltz.f
      02D0  15 00 04 00       bz     L02DC
      02D4  14 00 4f 00       jmp    L0376
      02D8  14 00 00 00       jmp    L02DC
L02DC: 02DC  12 00 00 00 96 c3 push   #-300f
      02E2  a2 00 00 00       push   [heap+0]
      02E6  a9 01             idxadd 1
      02E8  aa 01             pushblk.heap x1
      02EA  a2 00 00 00       push   [heap+0]
      02EE  a8 16 09 01       call   L0504 locals=22
      02F2  91 01             sub.f
      02F4  91 01             sub.f
      02F6  97 00             cmp.ltz.f
      02F8  95 00 04 00       bz     L0304
      02FC  94 00 3b 00       jmp    L0376
      0300  94 00 00 00       jmp    L0304
L0304: 0304  a2 00 00 00       push   [heap+0]
      0308  22 00 30 00       push   [loc+48]
      030C  12 00 00 00 70 41 push   #15f
      0312  0b 12             MoveByVel()
      0314  a2 00 00 00       push   [heap+0]
      0318  a9 01             idxadd 1
      031A  a0 0c             dup
      031C  aa 01             pushblk.heap x1
      031E  92 01 00 00 40 41 push   #12f
      0324  0b 05             NATIVE t0 #0x05
      0326  11 02             mul.f
      0328  11 00             add.f
      032A  10 07             blkcopy
      032C  32 01 14 00       pushblk[loc+20] x1
      0330  a2 00 00 00       push   [heap+0]
      0334  0b 10             SetVec()
      0336  a2 00 00 00       push   [heap+0]
      033A  aa 04             pushblk.heap x4
      033C  23 04 20 00       store  [loc+32]
      0340  22 00 20 00       push   [loc+32]
      0344  29 01             idxadd 1
      0346  a2 00 00 00       push   [heap+0]
      034A  a8 16 db 00       call   L0504 locals=22
      034E  92 16 00 00 20 41 push   #10f
      0354  91 01             sub.f
      0356  90 07             blkcopy
      0358  32 01 10 00       pushblk[loc+16] x1
      035C  22 00 20 00       push   [loc+32]
      0360  0b 10             SetVec()
      0362  00 00             end   ; ---- routine end ----
      0364  22 00 44 00       push   [loc+68]
      0368  20 0c             dup
      036A  2a 01             pushblk.heap x1
      036C  0b 05             NATIVE t0 #0x05
      036E  11 00             add.f
      0370  10 07             blkcopy
      0372  14 07 8a ff       jmp    L028A
L0376: 0376  32 01 14 00       pushblk[loc+20] x1
      037A  12 01 00 00 00 41 push   #8f
      0380  0b 91             NATIVE t0 #0x91
      0382  32 01 10 00       pushblk[loc+16] x1
      0386  12 01 00 00 00 41 push   #8f
      038C  0b 91             NATIVE t0 #0x91
      038E  72 01 00 00       pushblk[glob+0] x1
      0392  79 03             idxadd 3
      0394  7a 01             pushblk.heap x1
      0396  42 01 16 00 00 00 push   #22
      039C  42 01 20 4e 00 00 push   #20000
      03A2  a2 00 00 00       push   [heap+0]
      03A6  0b 4a             SpawnObj()
      03A8  03 4a 0c 00       store  [loc+12]
      03AC  22 00 20 00       push   [loc+32]
      03B0  12 00 00 00 80 3f push   #1f

; ===== ex_3000.bd  block@0x3BBB80  code@0x3BC4B8  size=0x1DE0 =====
      0938  00 00             end   ; ---- routine end ----
      093A  00 00             end   ; ---- routine end ----
      093C  97 4e             cmp.?.f
      093E  00 00             end   ; ---- routine end ----
      0940  62 00 04 00       push   [glob+4]
      0944  42 00 a8 04 00 00 push   #1192
      094A  48 02 c6 13       call   L30DA locals=2
      094E  40 03             tailcall
      0950  72 01 14 00       pushblk[glob+20] x1
      0954  42 01 04 00 00 00 push   #4
      095A  41 01             sub.i
      095C  47 02             cmp.eqz.i
      095E  45 02 37 00       bz     L09D0
      0962  72 01 10 00       pushblk[glob+16] x1
      0966  42 01 02 00 00 00 push   #2
      096C  41 01             sub.i
      096E  47 03             cmp.nez.i
      0970  45 03 23 00       bz     L09BA
      0974  48 02 ff 12       call   L2F76 locals=2
      0978  52 02 00 00 2f 44 push   #700f
      097E  51 01             sub.f
      0980  57 00             cmp.ltz.f
      0982  55 00 14 00       bz     L09AE
      0986  0b 19             NATIVE t0 #0x19
      0988  03 19 00 00       store  [loc+0]
      098C  32 01 00 00       pushblk[loc+0] x1
      0990  12 01 cd cc 4c 3f push   #0.8f
      0996  11 01             sub.f
      0998  17 00             cmp.ltz.f
      099A  15 00 04 00       bz     L09A6
      099E  18 02 95 0d       call   L24CC locals=2
      09A2  14 02 00 00       jmp    L09A6
L09A6: 09A6  18 02 8d 0e       call   L26C4 locals=2
      09AA  14 02 04 00       jmp    L09B6
L09AE: 09AE  18 02 04 0e       call   L25BA locals=2
      09B2  14 02 00 00       jmp    L09B6
L09B6: 09B6  14 02 09 00       jmp    L09CC
L09BA: 09BA  12 02 00 00 00 00 push   #0f
      09C0  18 02 eb 09       call   L1D9A locals=2
      09C4  18 02 a8 04       call   L1318 locals=2
      09C8  14 02 00 00       jmp    L09CC
L09CC: 09CC  14 02 06 01       jmp    L0BDC
L09D0: 09D0  72 01 14 00       pushblk[glob+20] x1
      09D4  42 01 05 00 00 00 push   #5
      09DA  41 01             sub.i
      09DC  47 02             cmp.eqz.i
      09DE  45 02 30 00       bz     L0A42
      09E2  72 01 10 00       pushblk[glob+16] x1
      09E6  42 01 02 00 00 00 push   #2
      09EC  41 01             sub.i
      09EE  47 03             cmp.nez.i
      09F0  45 03 1f 00       bz     L0A32
      09F4  0b 19             NATIVE t0 #0x19
      09F6  03 19 00 00       store  [loc+0]
      09FA  32 01 00 00       pushblk[loc+0] x1
      09FE  12 01 9a 99 99 3e push   #0.3f
      0A04  11 01             sub.f
      0A06  17 00             cmp.ltz.f
      0A08  15 00 04 00       bz     L0A14
      0A0C  18 02 5a 0e       call   L26C4 locals=2
      0A10  14 02 0d 00       jmp    L0A2E
L0A14: 0A14  32 01 00 00       pushblk[loc+0] x1
      0A18  12 01 9a 99 19 3f push   #0.6f
      0A1E  11 01             sub.f
      0A20  17 00             cmp.ltz.f
      0A22  15 00 04 00       bz     L0A2E
      0A26  18 02 c8 0d       call   L25BA locals=2
      0A2A  14 02 00 00       jmp    L0A2E
L0A2E: 0A2E  14 02 04 00       jmp    L0A3A
L0A32: 0A32  18 02 47 0e       call   L26C4 locals=2
      0A36  14 02 00 00       jmp    L0A3A
L0A3A: 0A3A  18 02 47 0d       call   L24CC locals=2
      0A3E  14 02 cd 00       jmp    L0BDC
L0A42: 0A42  72 01 14 00       pushblk[glob+20] x1
      0A46  42 01 06 00 00 00 push   #6
      0A4C  41 01             sub.i
      0A4E  47 02             cmp.eqz.i
      0A50  45 02 b5 00       bz     L0BBE
      0A54  72 01 10 00       pushblk[glob+16] x1
      0A58  42 01 02 00 00 00 push   #2
      0A5E  41 01             sub.i
      0A60  47 03             cmp.nez.i
      0A62  45 03 55 00       bz     L0B10
      0A66  0b 19             NATIVE t0 #0x19
      0A68  03 19 00 00       store  [loc+0]
      0A6C  32 01 00 00       pushblk[loc+0] x1
      0A70  12 01 00 00 80 3e push   #0.25f
      0A76  11 01             sub.f
      0A78  17 00             cmp.ltz.f
      0A7A  15 00 04 00       bz     L0A86
      0A7E  18 02 9c 0d       call   L25BA locals=2
      0A82  14 02 0d 00       jmp    L0AA0
L0A86: 0A86  32 01 00 00       pushblk[loc+0] x1
      0A8A  12 01 9a 99 19 3f push   #0.6f
      0A90  11 01             sub.f
      0A92  17 00             cmp.ltz.f
      0A94  15 00 04 00       bz     L0AA0
      0A98  18 02 18 0d       call   L24CC locals=2
      0A9C  14 02 00 00       jmp    L0AA0
L0AA0: 0AA0  12 02 00 00 c8 41 push   #25f
      0AA6  18 02 78 09       call   L1D9A locals=2
      0AAA  0b 19             NATIVE t0 #0x19
      0AAC  03 19 00 00       store  [loc+0]
      0AB0  32 01 00 00       pushblk[loc+0] x1
      0AB4  12 01 00 00 00 3f push   #0.5f
      0ABA  11 01             sub.f
      0ABC  17 00             cmp.ltz.f
      0ABE  15 00 04 00       bz     L0ACA
      0AC2  18 02 7a 0d       call   L25BA locals=2
      0AC6  14 02 11 00       jmp    L0AEC
L0ACA: 0ACA  32 01 00 00       pushblk[loc+0] x1
      0ACE  12 01 cd cc 4c 3f push   #0.8f
      0AD4  11 01             sub.f
      0AD6  17 00             cmp.ltz.f
      0AD8  15 00 04 00       bz     L0AE4
      0ADC  18 02 f6 0c       call   L24CC locals=2
      0AE0  14 02 04 00       jmp    L0AEC
L0AE4: 0AE4  18 02 ee 0d       call   L26C4 locals=2
      0AE8  14 02 00 00       jmp    L0AEC
L0AEC: 0AEC  0b 19             NATIVE t0 #0x19
      0AEE  03 19 00 00       store  [loc+0]
      0AF2  32 01 00 00       pushblk[loc+0] x1
      0AF6  12 01 cd cc cc 3e push   #0.4f
      0AFC  11 01             sub.f
      0AFE  17 00             cmp.ltz.f
      0B00  15 00 04 00       bz     L0B0C
      0B04  18 02 59 0d       call   L25BA locals=2
      0B08  14 02 00 00       jmp    L0B0C
L0B0C: 0B0C  14 02 55 00       jmp    L0BBA
L0B10: 0B10  0b 19             NATIVE t0 #0x19
      0B12  03 19 00 00       store  [loc+0]
      0B16  32 01 00 00       pushblk[loc+0] x1
      0B1A  12 01 00 00 80 3e push   #0.25f
      0B20  11 01             sub.f
      0B22  17 00             cmp.ltz.f
      0B24  15 00 04 00       bz     L0B30
      0B28  18 02 47 0d       call   L25BA locals=2
      0B2C  14 02 0d 00       jmp    L0B4A
L0B30: 0B30  32 01 00 00       pushblk[loc+0] x1
      0B34  12 01 9a 99 19 3f push   #0.6f
      0B3A  11 01             sub.f
      0B3C  17 00             cmp.ltz.f
      0B3E  15 00 04 00       bz     L0B4A
      0B42  18 02 91 0b       call   L2268 locals=2
      0B46  14 02 00 00       jmp    L0B4A
L0B4A: 0B4A  12 02 00 00 0c 42 push   #35f
      0B50  18 02 23 09       call   L1D9A locals=2
      0B54  0b 19             NATIVE t0 #0x19
      0B56  03 19 00 00       store  [loc+0]
      0B5A  32 01 00 00       pushblk[loc+0] x1
      0B5E  12 01 9a 99 19 3f push   #0.6f
      0B64  11 01             sub.f
      0B66  17 00             cmp.ltz.f
      0B68  15 00 04 00       bz     L0B74
      0B6C  18 02 d9 0b       call   L2322 locals=2
      0B70  14 02 11 00       jmp    L0B96
L0B74: 0B74  32 01 00 00       pushblk[loc+0] x1
      0B78  12 01 cd cc 4c 3f push   #0.8f
      0B7E  11 01             sub.f
      0B80  17 00             cmp.ltz.f
      0B82  15 00 04 00       bz     L0B8E
      0B86  18 02 a1 0c       call   L24CC locals=2
      0B8A  14 02 04 00       jmp    L0B96
L0B8E: 0B8E  18 02 14 0d       call   L25BA locals=2
      0B92  14 02 00 00       jmp    L0B96
L0B96: 0B96  0b 19             NATIVE t0 #0x19
      0B98  03 19 00 00       store  [loc+0]
      0B9C  32 01 00 00       pushblk[loc+0] x1
      0BA0  12 01 cd cc cc 3e push   #0.4f
      0BA6  11 01             sub.f
      0BA8  17 00             cmp.ltz.f
      0BAA  15 00 04 00       bz     L0BB6
      0BAE  18 02 89 0d       call   L26C4 locals=2
      0BB2  14 02 00 00       jmp    L0BB6
L0BB6: 0BB6  14 02 00 00       jmp    L0BBA
L0BBA: 0BBA  14 02 0f 00       jmp    L0BDC
L0BBE: 0BBE  72 01 14 00       pushblk[glob+20] x1
      0BC2  42 01 07 00 00 00 push   #7
      0BC8  41 01             sub.i
      0BCA  47 02             cmp.eqz.i
      0BCC  45 02 06 00       bz     L0BDC
      0BD0  48 02 e1 0d       call   L2796 locals=2
      0BD4  48 02 0b 00       call   L0BEE locals=2
      0BD8  44 02 00 00       jmp    L0BDC
L0BDC: 0BDC  62 00 04 00       push   [glob+4]
      0BE0  42 00 00 00 00 00 push   #0
      0BE6  48 02 a2 12       call   L312E locals=2
      0BEA  40 08             abort
      0BEC  40 03             tailcall
L0BEE: 0BEE  48 0a c9 15       call   L3784 locals=10
      0BF2  72 01 00 00       pushblk[glob+0] x1
      0BF6  22 00 10 00       push   [loc+16]
      0BFA  12 00 00 00 00 00 push   #0f
      0C00  12 00 00 00 00 00 push   #0f
      0C06  12 00 00 00 00 00 push   #0f
      0C0C  12 00 00 00 80 3f push   #1f
      0C12  18 0a ba 17       call   L3B8A locals=10
      0C16  0b 87             NATIVE t0 #0x87
      0C18  72 01 00 00       pushblk[glob+0] x1
      0C1C  79 1c             idxadd 28
      0C1E  7a 01             pushblk.heap x1
      0C20  42 01 00 00 00 00 push   #0
      0C26  41 01             sub.i
      0C28  47 02             cmp.eqz.i
      0C2A  45 02 07 00       bz     L0C3C
      0C2E  42 02 48 00 00 00 push   #72
      0C34  03 02 00 00       store  [loc+0]
      0C38  04 02 07 00       jmp    L0C4A
L0C3C: 0C3C  02 02 4e 00 00 00 push   #78
      0C42  03 02 00 00       store  [loc+0]
      0C46  04 02 00 00       jmp    L0C4A
L0C4A: 0C4A  72 01 00 00       pushblk[glob+0] x1
      0C4E  32 01 00 00       pushblk[loc+0] x1
      0C52  02 01 00 00 01 00 push   #65536
      0C58  01 06             or.i
      0C5A  12 06 00 00 00 00 push   #0f
      0C60  12 06 00 00 00 40 push   #2f
      0C66  0b 0d             NATIVE t0 #0x0d
      0C68  08 0a 95 0d       call   L2796 locals=10
      0C6C  72 01 00 00       pushblk[glob+0] x1
      0C70  42 01 2b 00 00 00 push   #43
      0C76  0b a8             NATIVE t0 #0xa8
      0C78  12 a8 cd cc 4c 3d push   #0.05f
      0C7E  12 a8 00 00 00 41 push   #8f
      0C84  18 0a a9 0f       call   L2BDA locals=10
      0C88  72 01 00 00       pushblk[glob+0] x1
      0C8C  42 01 03 00 00 00 push   #3
      0C92  0b 4b             NATIVE t0 #0x4b
      0C94  00 04             pop
      0C96  12 04 00 00 16 43 push   #150f
      0C9C  18 0a d3 19       call   L4046 locals=10
      0CA0  18 0a 3b 0f       call   L2B1A locals=10
      0CA4  10 03             tailcall
      0CA6  13 03 00 00       store  [loc+0]
      0CAA  72 01 10 00       pushblk[glob+16] x1
      0CAE  42 01 03 00 00 00 push   #3
      0CB4  41 01             sub.i
      0CB6  47 03             cmp.nez.i
      0CB8  40 0c             dup
      0CBA  45 0c 0a 00       bz     L0CD2
      0CBE  72 01 00 00       pushblk[glob+0] x1
      0CC2  79 1f             idxadd 31
      0CC4  7a 01             pushblk.heap x1
      0CC6  78 02 e2 11       call   L308E locals=2
      0CCA  78 02 01 15       call   L36D0 locals=2
      0CCE  47 02             cmp.eqz.i
      0CD0  41 0a             land.i
L0CD2: 0CD2  45 0a 22 00       bz     L0D1A
      0CD6  32 01 00 00       pushblk[loc+0] x1
      0CDA  02 01 00 00 00 00 push   #0
      0CE0  08 02 ed 16       call   L3ABE locals=2
      0CE4  72 01 00 00       pushblk[glob+0] x1
      0CE8  42 01 04 00 00 00 push   #4
      0CEE  48 02 80 14       call   L35F2 locals=2
      0CF2  42 02 03 00 00 00 push   #3
      0CF8  43 02 10 00       store  [glob+16]
      0CFC  42 02 07 00 00 00 push   #7
      0D02  43 02 14 00       store  [glob+20]
      0D06  62 00 04 00       push   [glob+4]
      0D0A  42 00 01 00 00 00 push   #1
      0D10  48 02 0d 12       call   L312E locals=2
      0D14  40 08             abort
      0D16  44 08 0b 00       jmp    L0D30
L0D1A: 0D1A  72 01 00 00       pushblk[glob+0] x1
      0D1E  79 1b             idxadd 27
      0D20  7a 01             pushblk.heap x1
      0D22  79 0f             idxadd 15
      0D24  42 0f 01 00 00 00 push   #1
      0D2A  40 07             blkcopy
      0D2C  44 07 00 00       jmp    L0D30
L0D30: 0D30  40 03             tailcall
      0D32  62 00 04 00       push   [glob+4]
      0D36  42 00 a1 06 00 00 push   #1697
      0D3C  48 02 cd 11       call   L30DA locals=2
      0D40  40 03             tailcall
L0D42: 0D42  72 01 10 00       pushblk[glob+16] x1
      0D46  42 01 00 00 00 00 push   #0
      0D4C  41 01             sub.i
      0D4E  47 02             cmp.eqz.i
      0D50  45 02 04 00       bz     L0D5C
      0D54  48 02 1b 02       call   L118E locals=2
      0D58  44 02 11 00       jmp    L0D7E
L0D5C: 0D5C  72 01 10 00       pushblk[glob+16] x1
      0D60  42 01 01 00 00 00 push   #1
      0D66  41 01             sub.i
      0D68  47 02             cmp.eqz.i
      0D6A  45 02 04 00       bz     L0D76
      0D6E  48 02 2e 01       call   L0FCE locals=2
      0D72  44 02 04 00       jmp    L0D7E
L0D76: 0D76  48 02 06 00       call   L0D86 locals=2
      0D7A  44 02 00 00       jmp    L0D7E
L0D7E: 0D7E  40 00             end
      0D80  44 00 df ff       jmp    L0D42
      0D84  40 03             tailcall
L0D86: 0D86  52 03 00 00 c8 41 push   #25f
      0D8C  13 03 00 00       store  [loc+0]
      0D90  62 00 18 00       push   [glob+24]
      0D94  60 0c             dup
      0D96  6a 01             pushblk.heap x1
      0D98  42 01 01 00 00 00 push   #1
      0D9E  41 00             add.i
      0DA0  40 07             blkcopy
      0DA2  72 01 18 00       pushblk[glob+24] x1
      0DA6  42 01 02 00 00 00 push   #2
      0DAC  41 01             sub.i
      0DAE  47 01             cmp.lez.i
      0DB0  45 01 4c 00       bz     L0E4C
      0DB4  48 02 b0 02       call   L1318 locals=2
      0DB8  72 01 18 00       pushblk[glob+24] x1
      0DBC  42 01 02 00 00 00 push   #2
      0DC2  41 01             sub.i
      0DC4  47 03             cmp.nez.i
      0DC6  45 03 04 00       bz     L0DD2
      0DCA  48 02 38 09       call   L203E locals=2
      0DCE  44 02 00 00       jmp    L0DD2
L0DD2: 0DD2  48 02 db 06       call   L1B8C locals=2
      0DD6  48 02 a4 0a       call   L2322 locals=2
      0DDA  0b 19             NATIVE t0 #0x19
      0DDC  03 19 04 00       store  [loc+4]
      0DE0  32 01 04 00       pushblk[loc+4] x1
      0DE4  12 01 cd cc cc 3e push   #0.4f
      0DEA  11 01             sub.f
      0DEC  17 00             cmp.ltz.f
      0DEE  15 00 04 00       bz     L0DFA
      0DF2  18 02 67 0c       call   L26C4 locals=2
      0DF6  14 02 0d 00       jmp    L0E14
L0DFA: 0DFA  32 01 04 00       pushblk[loc+4] x1
      0DFE  12 01 cd cc 4c 3f push   #0.8f
      0E04  11 01             sub.f
      0E06  17 00             cmp.ltz.f
      0E08  15 00 04 00       bz     L0E14
      0E0C  18 02 d5 0b       call   L25BA locals=2
      0E10  14 02 00 00       jmp    L0E14
L0E14: 0E14  18 02 70 07       call   L1CF8 locals=2
      0E18  18 02 83 0a       call   L2322 locals=2
      0E1C  0b 19             NATIVE t0 #0x19
      0E1E  03 19 04 00       store  [loc+4]
      0E22  32 01 04 00       pushblk[loc+4] x1
      0E26  12 01 9a 99 19 3f push   #0.6f
      0E2C  11 01             sub.f
      0E2E  17 00             cmp.ltz.f
      0E30  15 00 06 00       bz     L0E40
      0E34  18 02 aa 06       call   L1B8C locals=2
      0E38  18 02 73 0a       call   L2322 locals=2
      0E3C  14 02 00 00       jmp    L0E40
L0E40: 0E40  18 02 40 0c       call   L26C4 locals=2
      0E44  18 02 6d 0a       call   L2322 locals=2
      0E48  14 02 c0 00       jmp    L0FCC
L0E4C: 0E4C  72 01 18 00       pushblk[glob+24] x1
      0E50  42 01 04 00 00 00 push   #4
      0E56  41 01             sub.i
      0E58  47 01             cmp.lez.i
      0E5A  45 01 58 00       bz     L0F0E
      0E5E  48 02 4b 07       call   L1CF8 locals=2
      0E62  48 02 fa 05       call   L1A5A locals=2
      0E66  48 02 a8 0b       call   L25BA locals=2
      0E6A  48 02 45 07       call   L1CF8 locals=2
      0E6E  0b 19             NATIVE t0 #0x19
      0E70  03 19 04 00       store  [loc+4]
      0E74  32 01 04 00       pushblk[loc+4] x1
      0E78  12 01 33 33 33 3f push   #0.7f
      0E7E  11 01             sub.f
      0E80  17 00             cmp.ltz.f
      0E82  15 00 06 00       bz     L0E92
      0E86  32 01 00 00       pushblk[loc+0] x1
      0E8A  38 02 86 07       call   L1D9A locals=2
      0E8E  34 02 00 00       jmp    L0E92
L0E92: 0E92  38 02 46 0a       call   L2322 locals=2
      0E96  38 02 f2 05       call   L1A7E locals=2
      0E9A  12 02 00 00 00 00 push   #0f
      0EA0  18 02 7b 07       call   L1D9A locals=2
      0EA4  18 02 89 0b       call   L25BA locals=2
      0EA8  18 02 e9 05       call   L1A7E locals=2
      0EAC  0b 19             NATIVE t0 #0x19
      0EAE  03 19 04 00       store  [loc+4]
      0EB2  32 01 04 00       pushblk[loc+4] x1
      0EB6  12 01 33 33 33 3f push   #0.7f
      0EBC  11 01             sub.f
      0EBE  17 00             cmp.ltz.f
      0EC0  15 00 07 00       bz     L0ED2
      0EC4  12 00 00 00 00 00 push   #0f
      0ECA  18 02 74 07       call   L1DB6 locals=2
      0ECE  14 02 00 00       jmp    L0ED2
L0ED2: 0ED2  18 02 26 0a       call   L2322 locals=2
      0ED6  18 02 f5 0b       call   L26C4 locals=2
      0EDA  18 02 22 0a       call   L2322 locals=2
      0EDE  18 02 0b 07       call   L1CF8 locals=2
      0EE2  0b 19             NATIVE t0 #0x19
      0EE4  03 19 04 00       store  [loc+4]
      0EE8  32 01 04 00       pushblk[loc+4] x1
      0EEC  12 01 33 33 33 3f push   #0.7f
      0EF2  11 01             sub.f
      0EF4  17 00             cmp.ltz.f
      0EF6  15 00 06 00       bz     L0F06
      0EFA  32 01 00 00       pushblk[loc+0] x1
      0EFE  38 02 4c 07       call   L1D9A locals=2
      0F02  34 02 00 00       jmp    L0F06
L0F06: 0F06  38 02 e1 0a       call   L24CC locals=2
      0F0A  34 02 5f 00       jmp    L0FCC
L0F0E: 0F0E  72 01 18 00       pushblk[glob+24] x1
      0F12  42 01 05 00 00 00 push   #5
      0F18  41 01             sub.i
      0F1A  47 01             cmp.lez.i
      0F1C  45 01 30 00       bz     L0F80
      0F20  32 01 00 00       pushblk[loc+0] x1
      0F24  38 02 39 07       call   L1D9A locals=2
      0F28  38 02 f6 01       call   L1318 locals=2
      0F2C  32 01 00 00       pushblk[loc+0] x1
      0F30  38 02 33 07       call   L1D9A locals=2
      0F34  38 02 f0 01       call   L1318 locals=2
      0F38  38 02 f3 09       call   L2322 locals=2
      0F3C  38 02 dc 06       call   L1CF8 locals=2
      0F40  38 02 c0 0b       call   L26C4 locals=2
      0F44  38 02 d8 06       call   L1CF8 locals=2
      0F48  38 02 eb 09       call   L2322 locals=2
      0F4C  38 02 8c 09       call   L2268 locals=2
      0F50  38 02 1c 06       call   L1B8C locals=2
      0F54  0b 19             NATIVE t0 #0x19
      0F56  03 19 04 00       store  [loc+4]
      0F5A  32 01 04 00       pushblk[loc+4] x1
      0F5E  12 01 9a 99 19 3f push   #0.6f
      0F64  11 01             sub.f
      0F66  17 00             cmp.ltz.f
      0F68  15 00 04 00       bz     L0F74
      0F6C  18 02 25 0b       call   L25BA locals=2
      0F70  14 02 04 00       jmp    L0F7C
L0F74: 0F74  18 02 a6 0b       call   L26C4 locals=2
      0F78  14 02 00 00       jmp    L0F7C
L0F7C: 0F7C  14 02 26 00       jmp    L0FCC
L0F80: 0F80  72 01 18 00       pushblk[glob+24] x1
      0F84  42 01 06 00 00 00 push   #6
      0F8A  41 01             sub.i
      0F8C  47 01             cmp.lez.i
      0F8E  45 01 14 00       bz     L0FBA
      0F92  48 02 1c 02       call   L13CE locals=2
      0F96  0b 19             NATIVE t0 #0x19
      0F98  03 19 04 00       store  [loc+4]
      0F9C  32 01 04 00       pushblk[loc+4] x1
      0FA0  12 01 9a 99 99 3e push   #0.3f
      0FA6  11 01             sub.f
      0FA8  17 00             cmp.ltz.f
      0FAA  15 00 04 00       bz     L0FB6
      0FAE  18 02 0e 02       call   L13CE locals=2
      0FB2  14 02 00 00       jmp    L0FB6
L0FB6: 0FB6  14 02 09 00       jmp    L0FCC
L0FBA: 0FBA  02 02 00 00 00 00 push   #0
      0FC0  43 02 18 00       store  [glob+24]
      0FC4  48 02 50 09       call   L2268 locals=2
      0FC8  44 02 00 00       jmp    L0FCC
L0FCC: 0FCC  40 03             tailcall
L0FCE: 0FCE  52 03 00 00 c8 41 push   #25f
      0FD4  13 03 00 00       store  [loc+0]
      0FD8  62 00 18 00       push   [glob+24]
      0FDC  60 0c             dup
      0FDE  6a 01             pushblk.heap x1
      0FE0  42 01 01 00 00 00 push   #1
      0FE6  41 00             add.i
      0FE8  40 07             blkcopy
      0FEA  72 01 18 00       pushblk[glob+24] x1
      0FEE  42 01 01 00 00 00 push   #1
      0FF4  41 01             sub.i
      0FF6  47 02             cmp.eqz.i
      0FF8  45 02 06 00       bz     L1008
      0FFC  48 02 7c 06       call   L1CF8 locals=2
      1000  48 02 32 09       call   L2268 locals=2
      1004  44 02 a9 00       jmp    L115A
L1008: 1008  72 01 18 00       pushblk[glob+24] x1
      100C  42 01 03 00 00 00 push   #3
      1012  41 01             sub.i
      1014  47 01             cmp.lez.i
      1016  45 01 97 00       bz     L1148
      101A  48 02 6d 06       call   L1CF8 locals=2
      101E  48 02 51 0b       call   L26C4 locals=2
      1022  48 02 b3 05       call   L1B8C locals=2
      1026  0b 19             NATIVE t0 #0x19
      1028  03 19 04 00       store  [loc+4]
      102C  32 01 04 00       pushblk[loc+4] x1
      1030  12 01 9a 99 19 3f push   #0.6f
      1036  11 01             sub.f
      1038  17 00             cmp.ltz.f
      103A  15 00 06 00       bz     L104A
      103E  32 01 00 00       pushblk[loc+0] x1
      1042  38 02 aa 06       call   L1D9A locals=2
      1046  34 02 00 00       jmp    L104A
L104A: 104A  38 02 b6 0a       call   L25BA locals=2
      104E  38 02 53 06       call   L1CF8 locals=2
      1052  0b 19             NATIVE t0 #0x19
      1054  03 19 04 00       store  [loc+4]
      1058  32 01 04 00       pushblk[loc+4] x1
      105C  12 01 33 33 33 3f push   #0.7f
      1062  11 01             sub.f
      1064  17 00             cmp.ltz.f
      1066  15 00 08 00       bz     L107A
      106A  32 01 00 00       pushblk[loc+0] x1
      106E  38 02 94 06       call   L1D9A locals=2
      1072  38 02 a2 0a       call   L25BA locals=2
      1076  34 02 08 00       jmp    L108A
L107A: 107A  38 02 00 05       call   L1A7E locals=2
      107E  38 02 3b 06       call   L1CF8 locals=2
      1082  38 02 23 0a       call   L24CC locals=2
      1086  34 02 00 00       jmp    L108A
L108A: 108A  38 02 7f 05       call   L1B8C locals=2
      108E  0b 19             NATIVE t0 #0x19
      1090  03 19 04 00       store  [loc+4]
      1094  32 01 04 00       pushblk[loc+4] x1
      1098  12 01 9a 99 99 3e push   #0.3f
      109E  11 01             sub.f
      10A0  17 00             cmp.ltz.f
      10A2  15 00 06 00       bz     L10B2
      10A6  32 01 00 00       pushblk[loc+0] x1
      10AA  38 02 76 06       call   L1D9A locals=2
      10AE  34 02 00 00       jmp    L10B2
L10B2: 10B2  38 02 07 0b       call   L26C4 locals=2
      10B6  0b 19             NATIVE t0 #0x19
      10B8  03 19 04 00       store  [loc+4]
      10BC  32 01 04 00       pushblk[loc+4] x1
      10C0  12 01 9a 99 99 3e push   #0.3f
      10C6  11 01             sub.f
      10C8  17 00             cmp.ltz.f
      10CA  15 00 0a 00       bz     L10E2
      10CE  18 02 13 06       call   L1CF8 locals=2
      10D2  32 01 00 00       pushblk[loc+0] x1
      10D6  38 02 60 06       call   L1D9A locals=2
      10DA  38 02 6e 0a       call   L25BA locals=2
      10DE  34 02 17 00       jmp    L1110
L10E2: 10E2  32 01 04 00       pushblk[loc+4] x1
      10E6  12 01 9a 99 19 3f push   #0.6f
      10EC  11 01             sub.f
      10EE  17 00             cmp.ltz.f
      10F0  15 00 08 00       bz     L1104
      10F4  18 02 b1 04       call   L1A5A locals=2
      10F8  18 02 fe 05       call   L1CF8 locals=2
      10FC  18 02 e2 0a       call   L26C4 locals=2
      1100  14 02 06 00       jmp    L1110
L1104: 1104  18 02 f8 05       call   L1CF8 locals=2
      1108  18 02 e0 09       call   L24CC locals=2
      110C  14 02 00 00       jmp    L1110
L1110: 1110  18 02 b5 04       call   L1A7E locals=2
      1114  18 02 3a 05       call   L1B8C locals=2
      1118  18 02 a6 08       call   L2268 locals=2
      111C  0b 19             NATIVE t0 #0x19
      111E  03 19 04 00       store  [loc+4]
      1122  32 01 04 00       pushblk[loc+4] x1
      1126  12 01 cd cc cc 3e push   #0.4f
      112C  11 01             sub.f
      112E  17 00             cmp.ltz.f
      1130  15 00 06 00       bz     L1140
      1134  32 01 00 00       pushblk[loc+0] x1
      1138  38 02 2f 06       call   L1D9A locals=2
      113C  34 02 00 00       jmp    L1140
L1140: 1140  38 02 3b 0a       call   L25BA locals=2
      1144  34 02 09 00       jmp    L115A
L1148: 1148  38 02 41 01       call   L13CE locals=2
      114C  02 02 00 00 00 00 push   #0
      1152  43 02 18 00       store  [glob+24]
      1156  44 02 00 00       jmp    L115A
L115A: 115A  72 01 00 00       pushblk[glob+0] x1
      115E  78 02 5c 11       call   L341A locals=2
      1162  52 02 9a 99 99 3e push   #0.3f
      1168  51 01             sub.f
      116A  57 00             cmp.ltz.f
      116C  55 00 0e 00       bz     L118C
      1170  42 00 00 00 00 00 push   #0
      1176  43 00 18 00       store  [glob+24]
      117A  42 00 02 00 00 00 push   #2
      1180  43 00 10 00       store  [glob+16]
      1184  48 02 73 00       call   L126E locals=2
      1188  44 02 00 00       jmp    L118C
L118C: 118C  40 03             tailcall
L118E: 118E  48 02 b3 05       call   L1CF8 locals=2
      1192  0b 19             NATIVE t0 #0x19
      1194  03 19 00 00       store  [loc+0]
      1198  32 01 00 00       pushblk[loc+0] x1
      119C  12 01 33 33 33 3f push   #0.7f
      11A2  11 01             sub.f
      11A4  17 00             cmp.ltz.f
      11A6  15 00 04 00       bz     L11B2
      11AA  18 02 8b 0a       call   L26C4 locals=2
      11AE  14 02 04 00       jmp    L11BA
L11B2: 11B2  18 02 02 0a       call   L25BA locals=2
      11B6  14 02 00 00       jmp    L11BA
L11BA: 11BA  18 02 ec 00       call   L1396 locals=2
      11BE  18 02 5e 04       call   L1A7E locals=2
      11C2  0b 19             NATIVE t0 #0x19
      11C4  03 19 00 00       store  [loc+0]
      11C8  32 01 00 00       pushblk[loc+0] x1
      11CC  12 01 33 33 33 3f push   #0.7f
      11D2  11 01             sub.f
      11D4  17 00             cmp.ltz.f
      11D6  15 00 04 00       bz     L11E2
      11DA  18 02 73 0a       call   L26C4 locals=2
      11DE  14 02 04 00       jmp    L11EA
L11E2: 11E2  18 02 ea 09       call   L25BA locals=2
      11E6  14 02 00 00       jmp    L11EA
L11EA: 11EA  18 02 d4 00       call   L1396 locals=2
      11EE  18 02 83 05       call   L1CF8 locals=2
      11F2  18 02 e2 09       call   L25BA locals=2
      11F6  18 02 ce 00       call   L1396 locals=2
      11FA  0b 19             NATIVE t0 #0x19
      11FC  03 19 00 00       store  [loc+0]
      1200  32 01 00 00       pushblk[loc+0] x1
      1204  12 01 33 33 33 3f push   #0.7f
      120A  11 01             sub.f
      120C  17 00             cmp.ltz.f
      120E  15 00 06 00       bz     L121E
      1212  18 02 71 05       call   L1CF8 locals=2
      1216  18 02 55 0a       call   L26C4 locals=2
      121A  14 02 08 00       jmp    L122E
L121E: 121E  18 02 1c 04       call   L1A5A locals=2
      1222  18 02 69 05       call   L1CF8 locals=2
      1226  18 02 c8 09       call   L25BA locals=2
      122A  14 02 00 00       jmp    L122E
L122E: 122E  18 02 4d 09       call   L24CC locals=2
      1232  18 02 b0 00       call   L1396 locals=2
      1236  72 01 00 00       pushblk[glob+0] x1
      123A  78 02 ee 10       call   L341A locals=2
      123E  52 02 66 66 26 3f push   #0.65f
      1244  51 01             sub.f
      1246  57 00             cmp.ltz.f
      1248  55 00 10 00       bz     L126C
      124C  42 00 00 00 00 00 push   #0
      1252  43 00 18 00       store  [glob+24]
      1256  42 00 01 00 00 00 push   #1
      125C  43 00 10 00       store  [glob+16]
      1260  48 02 fb 03       call   L1A5A locals=2
      1264  48 02 58 00       call   L1318 locals=2
      1268  44 02 00 00       jmp    L126C
L126C: 126C  40 03             tailcall
L126E: 126E  48 02 8f 0e       call   L2F90 locals=2
      1272  72 01 00 00       pushblk[glob+0] x1
      1276  42 01 40 00 00 00 push   #64
      127C  48 02 c7 11       call   L360E locals=2
      1280  72 01 00 00       pushblk[glob+0] x1
      1284  72 01 00 00       pushblk[glob+0] x1
      1288  79 1d             idxadd 29
      128A  7a 01             pushblk.heap x1
      128C  78 02 d3 10       call   L3436 locals=2
      1290  72 01 00 00       pushblk[glob+0] x1
      1294  42 01 07 00 00 00 push   #7
      129A  0b 4b             NATIVE t0 #0x4b
      129C  00 04             pop
      129E  72 01 00 00       pushblk[glob+0] x1
      12A2  42 01 08 00 00 00 push   #8
      12A8  0b 4b             NATIVE t0 #0x4b
      12AA  00 04             pop
      12AC  72 01 00 00       pushblk[glob+0] x1
      12B0  42 01 f0 00 00 00 push   #240
      12B6  52 01 00 00 00 41 push   #8f
      12BC  52 01 00 00 00 00 push   #0f
      12C2  0b 0d             NATIVE t0 #0x0d
      12C4  12 0d 00 00 70 42 push   #60f
      12CA  18 02 bc 16       call   L4046 locals=2
      12CE  72 01 00 00       pushblk[glob+0] x1
      12D2  42 01 27 00 00 00 push   #39
      12D8  0b a8             NATIVE t0 #0xa8
      12DA  12 a8 00 00 dc 42 push   #110f
      12E0  18 02 b1 16       call   L4046 locals=2
      12E4  18 02 1d 12       call   L3722 locals=2
      12E8  72 01 00 00       pushblk[glob+0] x1
      12EC  78 02 86 10       call   L33FC locals=2
      12F0  72 01 00 00       pushblk[glob+0] x1
      12F4  42 01 40 00 00 00 push   #64
      12FA  48 02 7a 11       call   L35F2 locals=2
      12FE  72 01 00 00       pushblk[glob+0] x1
      1302  42 01 00 00 00 00 push   #0
      1308  52 01 00 00 00 41 push   #8f
      130E  52 01 00 00 00 00 push   #0f
      1314  0b 0d             NATIVE t0 #0x0d
      1316  00 03             tailcall
L1318: 1318  08 02 43 16       call   L3FA2 locals=2
      131C  05 02 3a 00       bz     L1394
      1320  08 02 36 0e       call   L2F90 locals=2
      1324  72 01 00 00       pushblk[glob+0] x1
      1328  42 01 f1 00 00 00 push   #241
      132E  52 01 00 00 00 41 push   #8f
      1334  52 01 00 00 00 00 push   #0f
      133A  0b 0d             NATIVE t0 #0x0d
      133C  08 02 8c 0a       call   L2858 locals=2
      1340  12 02 00 00 f0 41 push   #30f
      1346  18 02 b9 0d       call   L2EBC locals=2
      134A  72 01 00 00       pushblk[glob+0] x1
      134E  42 01 2c 00 00 00 push   #44
      1354  0b a8             NATIVE t0 #0xa8
      1356  08 02 db 0d       call   L2F10 locals=2
      135A  72 01 00 00       pushblk[glob+0] x1
      135E  42 01 00 00 00 00 push   #0
      1364  52 01 00 00 00 41 push   #8f
      136A  52 01 00 00 00 00 push   #0f
      1370  0b 0d             NATIVE t0 #0x0d
      1372  72 01 18 00       pushblk[glob+24] x1
      1376  42 01 01 00 00 00 push   #1
      137C  41 01             sub.i
      137E  47 03             cmp.nez.i
      1380  45 03 06 00       bz     L1390
      1384  48 02 07 00       call   L1396 locals=2
      1388  48 02 05 00       call   L1396 locals=2
      138C  44 02 00 00       jmp    L1390
L1390: 1390  44 02 00 00       jmp    L1394
L1394: 1394  40 03             tailcall
L1396: 1396  48 02 04 16       call   L3FA2 locals=2
      139A  45 02 17 00       bz     L13CC
      139E  48 02 f7 0d       call   L2F90 locals=2
      13A2  72 01 00 00       pushblk[glob+0] x1
      13A6  42 01 00 00 00 00 push   #0
      13AC  52 01 00 00 00 41 push   #8f
      13B2  0b 0c             NATIVE t0 #0x0c
      13B4  12 0c 00 00 00 00 push   #0f
      13BA  12 0c 00 00 f0 41 push   #30f
      13C0  18 02 f8 0e       call   L31B4 locals=2
      13C4  18 02 3f 16       call   L4046 locals=2
      13C8  14 02 00 00       jmp    L13CC
L13CC: 13CC  10 03             tailcall
L13CE: 13CE  02 03 03 00 00 00 push   #3
      13D4  03 03 00 00       store  [loc+0]
      13D8  08 02 e3 15       call   L3FA2 locals=2
      13DC  05 02 1c 00       bz     L1418
      13E0  08 02 f1 01       call   L17C6 locals=2
L13E4: 13E4  32 01 00 00       pushblk[loc+0] x1
      13E8  02 01 00 00 00 00 push   #0
      13EE  01 01             sub.i
      13F0  07 05             cmp.gtz.i
      13F2  05 05 0d 00       bz     L1410
      13F6  08 02 48 01       call   L168A locals=2
      13FA  22 00 00 00       push   [loc+0]
      13FE  20 0c             dup
      1400  2a 01             pushblk.heap x1
      1402  02 01 01 00 00 00 push   #1
      1408  01 01             sub.i
      140A  00 07             blkcopy
      140C  04 07 ea ff       jmp    L13E4
L1410: 1410  08 02 03 00       call   L141A locals=2
      1414  04 02 00 00       jmp    L1418
L1418: 1418  00 03             tailcall
L141A: 141A  72 01 00 00       pushblk[glob+0] x1
      141E  79 08             idxadd 8
      1420  79 03             idxadd 3
      1422  52 03 00 00 00 00 push   #0f
      1428  50 07             blkcopy
      142A  72 01 00 00       pushblk[glob+0] x1
      142E  0b 16             GetActor()
      1430  e2 00 ae f0       push   [imm+-3922]
      1434  0b 17             MakeAttack()
      1436  00 04             pop
      1438  72 01 00 00       pushblk[glob+0] x1
      143C  0b 16             GetActor()
      143E  e2 00 10 f1       push   [imm+-3824]
      1442  0b 17             MakeAttack()
      1444  00 04             pop
      1446  72 01 00 00       pushblk[glob+0] x1
      144A  42 01 d2 00 00 00 push   #210
      1450  52 01 00 00 00 00 push   #0f
      1456  52 01 00 00 00 00 push   #0f
      145C  0b 0d             NATIVE t0 #0x0d
      145E  72 01 00 00       pushblk[glob+0] x1
      1462  42 01 1b 00 00 00 push   #27
      1468  0b a8             NATIVE t0 #0xa8
      146A  12 a8 00 00 48 42 push   #50f
      1470  13 a8 10 00       store  [loc+16]
L1474: 1474  32 01 10 00       pushblk[loc+16] x1
      1478  12 01 00 00 00 00 push   #0f
      147E  11 01             sub.f
      1480  17 04             cmp.gez.f
      1482  15 04 0c 00       bz     L149E
      1486  22 00 10 00       push   [loc+16]
      148A  20 0c             dup
      148C  2a 01             pushblk.heap x1
      148E  0b 05             NATIVE t0 #0x05
      1490  11 01             sub.f
      1492  10 07             blkcopy
      1494  18 06 04 02       call   L18A0 locals=6
      1498  10 00             end
      149A  14 00 eb ff       jmp    L1474
L149E: 149E  18 06 71 11       call   L3784 locals=6
L14A2: 14A2  72 01 00 00       pushblk[glob+0] x1
      14A6  0b ac             NATIVE t0 #0xac
      14A8  00 0d             lnot
      14AA  05 0d 05 00       bz     L14B8
      14AE  08 06 f7 01       call   L18A0 locals=6
      14B2  00 00             end   ; ---- routine end ----
      14B4  04 00 f5 ff       jmp    L14A2
L14B8: 14B8  72 01 00 00       pushblk[glob+0] x1
      14BC  42 01 2d 00 00 00 push   #45
      14C2  0b 4b             NATIVE t0 #0x4b
      14C4  00 04             pop
      14C6  72 01 00 00       pushblk[glob+0] x1
      14CA  72 01 00 00       pushblk[glob+0] x1
      14CE  79 1d             idxadd 29
      14D0  7a 01             pushblk.heap x1
      14D2  78 06 b0 0f       call   L3436 locals=6
      14D6  72 01 00 00       pushblk[glob+0] x1
      14DA  0b 16             GetActor()
      14DC  e2 00 e2 f0       push   [imm+-3870]
      14E0  0b 17             MakeAttack()
      14E2  00 04             pop
      14E4  72 01 00 00       pushblk[glob+0] x1
      14E8  42 01 11 00 00 00 push   #17
      14EE  0b a8             NATIVE t0 #0xa8
      14F0  08 06 4e 11       call   L3790 locals=6
      14F4  72 01 00 00       pushblk[glob+0] x1
      14F8  42 01 d3 00 00 00 push   #211
      14FE  52 01 00 00 00 00 push   #0f
      1504  52 01 00 00 00 00 push   #0f
      150A  0b 0d             NATIVE t0 #0x0d
      150C  72 01 00 00       pushblk[glob+0] x1
      1510  79 1b             idxadd 27
      1512  7a 01             pushblk.heap x1
      1514  79 05             idxadd 5
      1516  52 05 66 66 66 3f push   #0.9f
      151C  50 07             blkcopy
L151E: 151E  72 01 00 00       pushblk[glob+0] x1
      1522  0b ac             NATIVE t0 #0xac
      1524  00 0d             lnot
      1526  05 0d 6b 00       bz     L1600
      152A  72 01 00 00       pushblk[glob+0] x1
      152E  0b 59             NATIVE t0 #0x59
      1530  12 59 00 00 20 41 push   #10f
      1536  11 01             sub.f
      1538  17 01             cmp.lez.f
      153A  15 01 10 00       bz     L155E
      153E  72 01 00 00       pushblk[glob+0] x1
      1542  79 08             idxadd 8
      1544  79 03             idxadd 3
      1546  52 03 00 00 00 00 push   #0f
      154C  50 07             blkcopy
      154E  72 01 00 00       pushblk[glob+0] x1
      1552  42 01 00 00 00 00 push   #0
      1558  0b 58             NATIVE t0 #0x58
      155A  04 58 4e 00       jmp    L15FA
L155E: 155E  72 01 00 00       pushblk[glob+0] x1
      1562  79 1d             idxadd 29
      1564  7a 01             pushblk.heap x1
      1566  79 04             idxadd 4
      1568  7a 04             pushblk.heap x4
      156A  33 04 00 00       store  [loc+0]
      156E  22 00 00 00       push   [loc+0]
      1572  29 01             idxadd 1
      1574  12 01 00 00 a0 c1 push   #-20f
      157A  10 07             blkcopy
      157C  22 00 00 00       push   [loc+0]
      1580  72 01 00 00       pushblk[glob+0] x1
      1584  79 04             idxadd 4
      1586  0b 08             VecSub()
      1588  72 01 00 00       pushblk[glob+0] x1
      158C  22 00 00 00       push   [loc+0]
      1590  0b 0b             NATIVE t0 #0x0b
      1592  22 00 00 00       push   [loc+0]
      1596  0b 09             NATIVE t0 #0x09
      1598  72 01 00 00       pushblk[glob+0] x1
      159C  79 08             idxadd 8
      159E  22 00 00 00       push   [loc+0]
      15A2  2a 04             pushblk.heap x4
      15A4  20 07             blkcopy
      15A6  72 01 00 00       pushblk[glob+0] x1
      15AA  79 08             idxadd 8
      15AC  79 01             idxadd 1
      15AE  70 0c             dup
      15B0  7a 01             pushblk.heap x1
      15B2  52 01 00 00 80 40 push   #4f
      15B8  51 02             mul.f
      15BA  50 07             blkcopy
      15BC  72 01 00 00       pushblk[glob+0] x1
      15C0  79 08             idxadd 8
      15C2  70 0c             dup
      15C4  7a 01             pushblk.heap x1
      15C6  52 01 00 00 80 40 push   #4f
      15CC  51 02             mul.f
      15CE  50 07             blkcopy
      15D0  72 01 00 00       pushblk[glob+0] x1
      15D4  79 08             idxadd 8
      15D6  79 02             idxadd 2
      15D8  70 0c             dup
      15DA  7a 01             pushblk.heap x1
      15DC  52 01 00 00 80 40 push   #4f
      15E2  51 02             mul.f
      15E4  50 07             blkcopy
      15E6  72 01 00 00       pushblk[glob+0] x1
      15EA  79 08             idxadd 8
      15EC  79 03             idxadd 3
      15EE  52 03 00 00 70 41 push   #15f
      15F4  50 07             blkcopy
      15F6  54 07 00 00       jmp    L15FA
L15FA: 15FA  50 00             end
      15FC  54 00 8f ff       jmp    L151E
L1600: 1600  72 01 00 00       pushblk[glob+0] x1
      1604  42 01 03 00 00 00 push   #3
      160A  72 01 00 00       pushblk[glob+0] x1
      160E  79 1d             idxadd 29
      1610  7a 01             pushblk.heap x1
      1612  e2 00 1c f0       push   [imm+-4068]
      1616  c2 00 00 00 00 00 push   #0
      161C  0b 5e             NATIVE t0 #0x5e
      161E  00 04             pop
      1620  72 01 00 00       pushblk[glob+0] x1
      1624  42 01 2d 00 00 00 push   #45
      162A  0b 4b             NATIVE t0 #0x4b
      162C  00 04             pop
      162E  72 01 00 00       pushblk[glob+0] x1
      1632  42 01 00 00 00 00 push   #0
      1638  0b 58             NATIVE t0 #0x58
      163A  08 06 a3 10       call   L3784 locals=6
      163E  72 01 00 00       pushblk[glob+0] x1
      1642  42 01 40 00 00 00 push   #64
      1648  48 06 d3 0f       call   L35F2 locals=6
      164C  48 06 20 09       call   L2890 locals=6
      1650  72 01 00 00       pushblk[glob+0] x1
      1654  42 01 d4 00 00 00 push   #212
      165A  52 01 00 00 00 00 push   #0f
      1660  52 01 00 00 00 00 push   #0f
      1666  0b 0d             NATIVE t0 #0x0d
      1668  72 01 00 00       pushblk[glob+0] x1
      166C  78 06 c6 0e       call   L33FC locals=6
      1670  72 01 00 00       pushblk[glob+0] x1
      1674  42 01 00 00 00 00 push   #0
      167A  52 01 00 00 00 41 push   #8f
      1680  52 01 00 00 00 00 push   #0f
      1686  0b 0d             NATIVE t0 #0x0d
      1688  00 03             tailcall
L168A: 168A  08 06 65 01       call   L1958 locals=6
      168E  02 06 ce 00 00 00 push   #206
      1694  03 06 08 00       store  [loc+8]
L1698: 1698  32 01 08 00       pushblk[loc+8] x1
      169C  02 01 d1 00 00 00 push   #209
      16A2  01 01             sub.i
      16A4  07 01             cmp.lez.i
      16A6  05 01 8d 00       bz     L17C4
      16AA  0b 19             NATIVE t0 #0x19
      16AC  03 19 0c 00       store  [loc+12]
      16B0  32 01 0c 00       pushblk[loc+12] x1
      16B4  12 01 cd cc cc 3e push   #0.4f
      16BA  11 01             sub.f
      16BC  17 00             cmp.ltz.f
      16BE  15 00 07 00       bz     L16D0
      16C2  02 00 03 00 00 00 push   #3
      16C8  03 00 04 00       store  [loc+4]
      16CC  04 00 17 00       jmp    L16FE
L16D0: 16D0  32 01 0c 00       pushblk[loc+12] x1
      16D4  12 01 33 33 33 3f push   #0.7f
      16DA  11 01             sub.f
      16DC  17 00             cmp.ltz.f
      16DE  15 00 07 00       bz     L16F0
      16E2  02 00 06 00 00 00 push   #6
      16E8  03 00 04 00       store  [loc+4]
      16EC  04 00 07 00       jmp    L16FE
L16F0: 16F0  02 00 07 00 00 00 push   #7
      16F6  03 00 04 00       store  [loc+4]
      16FA  04 00 00 00       jmp    L16FE
L16FE: 16FE  72 01 00 00       pushblk[glob+0] x1
      1702  32 01 04 00       pushblk[loc+4] x1
      1706  0b a8             NATIVE t0 #0xa8
      1708  32 01 08 00       pushblk[loc+8] x1
      170C  02 01 ce 00 00 00 push   #206
      1712  01 01             sub.i
      1714  07 02             cmp.eqz.i
      1716  05 02 06 00       bz     L1726
      171A  e2 00 04 ec       push   [imm+-5116]
      171E  23 00 00 00       store  [loc+0]
      1722  24 00 24 00       jmp    L176E
L1726: 1726  32 01 08 00       pushblk[loc+8] x1
      172A  02 01 cf 00 00 00 push   #207
      1730  01 01             sub.i
      1732  07 02             cmp.eqz.i
      1734  05 02 06 00       bz     L1744
      1738  e2 00 56 ec       push   [imm+-5034]
      173C  23 00 00 00       store  [loc+0]
      1740  24 00 15 00       jmp    L176E
L1744: 1744  32 01 08 00       pushblk[loc+8] x1
      1748  02 01 d0 00 00 00 push   #208
      174E  01 01             sub.i
      1750  07 02             cmp.eqz.i
      1752  05 02 06 00       bz     L1762
      1756  e2 00 a8 ec       push   [imm+-4952]
      175A  23 00 00 00       store  [loc+0]
      175E  24 00 06 00       jmp    L176E
L1762: 1762  e2 00 0c ed       push   [imm+-4852]
      1766  23 00 00 00       store  [loc+0]
      176A  24 00 00 00       jmp    L176E
L176E: 176E  72 01 00 00       pushblk[glob+0] x1
      1772  0b 16             GetActor()
      1774  32 01 00 00       pushblk[loc+0] x1
      1778  0b 17             MakeAttack()
      177A  00 04             pop
      177C  72 01 00 00       pushblk[glob+0] x1
      1780  32 01 08 00       pushblk[loc+8] x1
      1784  12 01 00 00 00 00 push   #0f
      178A  0b 0c             NATIVE t0 #0x0c
L178C: 178C  72 01 00 00       pushblk[glob+0] x1
      1790  0b ac             NATIVE t0 #0xac
      1792  00 0d             lnot
      1794  05 0d 05 00       bz     L17A2
      1798  08 06 82 00       call   L18A0 locals=6
      179C  00 00             end   ; ---- routine end ----
      179E  04 00 f5 ff       jmp    L178C
L17A2: 17A2  32 01 08 00       pushblk[loc+8] x1
      17A6  02 01 01 00 00 00 push   #1
      17AC  01 00             add.i
      17AE  03 00 08 00       store  [loc+8]
      17B2  72 01 00 00       pushblk[glob+0] x1
      17B6  42 01 2d 00 00 00 push   #45
      17BC  0b 4b             NATIVE t0 #0x4b
      17BE  00 04             pop
      17C0  04 04 6a ff       jmp    L1698
L17C4: 17C4  00 03             tailcall
L17C6: 17C6  0b 19             NATIVE t0 #0x19
      17C8  03 19 10 00       store  [loc+16]
      17CC  32 01 10 00       pushblk[loc+16] x1
      17D0  12 01 cd cc cc 3e push   #0.4f
      17D6  11 01             sub.f
      17D8  17 00             cmp.ltz.f
      17DA  15 00 07 00       bz     L17EC
      17DE  02 00 1f 00 00 00 push   #31
      17E4  03 00 14 00       store  [loc+20]
      17E8  04 00 07 00       jmp    L17FA
L17EC: 17EC  02 00 20 00 00 00 push   #32
      17F2  03 00 14 00       store  [loc+20]
      17F6  04 00 00 00       jmp    L17FA
L17FA: 17FA  08 06 c9 0b       call   L2F90 locals=6
      17FE  72 01 00 00       pushblk[glob+0] x1
      1802  32 01 14 00       pushblk[loc+20] x1
      1806  0b a8             NATIVE t0 #0xa8
      1808  08 06 48 08       call   L289C locals=6
      180C  72 01 00 00       pushblk[glob+0] x1
      1810  42 01 40 00 00 00 push   #64
      1816  48 06 fa 0e       call   L360E locals=6
      181A  72 01 00 00       pushblk[glob+0] x1
      181E  79 1b             idxadd 27
      1820  7a 01             pushblk.heap x1
      1822  79 05             idxadd 5
      1824  52 05 cd cc cc 3d push   #0.1f
      182A  50 07             blkcopy
      182C  72 01 00 00       pushblk[glob+0] x1
      1830  22 00 00 00       push   [loc+0]
      1834  12 00 00 00 00 00 push   #0f
      183A  12 00 00 00 00 00 push   #0f
      1840  12 00 00 00 00 00 push   #0f
      1846  12 00 00 00 80 3f push   #1f
      184C  18 06 9d 11       call   L3B8A locals=6
      1850  0b a9             NATIVE t0 #0xa9
      1852  72 01 00 00       pushblk[glob+0] x1
      1856  72 01 00 00       pushblk[glob+0] x1
      185A  79 1d             idxadd 29
      185C  7a 01             pushblk.heap x1
      185E  78 06 ea 0d       call   L3436 locals=6
      1862  72 01 00 00       pushblk[glob+0] x1
      1866  42 01 cd 00 00 00 push   #205
      186C  52 01 00 00 00 41 push   #8f
      1872  52 01 00 00 00 00 push   #0f
      1878  0b 0d             NATIVE t0 #0x0d
      187A  72 01 00 00       pushblk[glob+0] x1
      187E  78 06 bd 0d       call   L33FC locals=6
      1882  78 06 85 0f       call   L3790 locals=6
      1886  72 01 00 00       pushblk[glob+0] x1
      188A  42 01 ce 00 00 00 push   #206
      1890  52 01 00 00 00 00 push   #0f
      1896  52 01 00 00 00 00 push   #0f
      189C  0b 0d             NATIVE t0 #0x0d
      189E  00 03             tailcall
L18A0: 18A0  72 01 00 00       pushblk[glob+0] x1
      18A4  72 01 00 00       pushblk[glob+0] x1
      18A8  79 1d             idxadd 29
      18AA  7a 01             pushblk.heap x1
      18AC  78 0a c3 0d       call   L3436 locals=10
      18B0  72 01 00 00       pushblk[glob+0] x1
      18B4  79 1d             idxadd 29
      18B6  7a 01             pushblk.heap x1
      18B8  79 04             idxadd 4
      18BA  7a 04             pushblk.heap x4
      18BC  33 04 00 00       store  [loc+0]
      18C0  22 00 00 00       push   [loc+0]
      18C4  29 01             idxadd 1
      18C6  20 0c             dup
      18C8  2a 01             pushblk.heap x1
      18CA  12 01 00 00 f0 41 push   #30f
      18D0  11 01             sub.f
      18D2  10 07             blkcopy
      18D4  22 00 00 00       push   [loc+0]
      18D8  2a 04             pushblk.heap x4
      18DA  23 04 10 00       store  [loc+16]
      18DE  22 00 10 00       push   [loc+16]
      18E2  72 01 00 00       pushblk[glob+0] x1
      18E6  79 04             idxadd 4
      18E8  0b 08             VecSub()
      18EA  22 00 10 00       push   [loc+16]
      18EE  0b 09             NATIVE t0 #0x09
      18F0  22 00 10 00       push   [loc+16]
      18F4  29 03             idxadd 3
      18F6  12 03 00 00 00 41 push   #8f
      18FC  10 07             blkcopy
      18FE  72 01 00 00       pushblk[glob+0] x1
      1902  79 08             idxadd 8
      1904  22 00 10 00       push   [loc+16]
      1908  2a 04             pushblk.heap x4
      190A  20 07             blkcopy
      190C  28 0a 33 0b       call   L2F76 locals=10
      1910  12 0a 00 00 a5 43 push   #330f
      1916  11 01             sub.f
      1918  17 00             cmp.ltz.f
      191A  15 00 1c 00       bz     L1956
      191E  72 01 00 00       pushblk[glob+0] x1
      1922  79 08             idxadd 8
      1924  79 01             idxadd 1
      1926  70 0c             dup
      1928  7a 01             pushblk.heap x1
      192A  52 01 00 00 00 3f push   #0.5f
      1930  51 02             mul.f
      1932  50 07             blkcopy
      1934  72 01 00 00       pushblk[glob+0] x1
      1938  79 08             idxadd 8
      193A  52 08 00 00 00 00 push   #0f
      1940  50 07             blkcopy
      1942  72 01 00 00       pushblk[glob+0] x1
      1946  79 08             idxadd 8
      1948  79 02             idxadd 2
      194A  52 02 00 00 00 00 push   #0f
      1950  50 07             blkcopy
      1952  54 07 00 00       jmp    L1956
L1956: 1956  50 03             tailcall
L1958: 1958  72 01 00 00       pushblk[glob+0] x1
      195C  79 1d             idxadd 29
      195E  7a 01             pushblk.heap x1
      1960  79 04             idxadd 4
      1962  7a 04             pushblk.heap x4
      1964  33 04 20 00       store  [loc+32]
      1968  22 00 20 00       push   [loc+32]
      196C  72 01 00 00       pushblk[glob+0] x1
      1970  79 04             idxadd 4
      1972  0b 08             VecSub()
      1974  22 00 20 00       push   [loc+32]
      1978  0b 09             NATIVE t0 #0x09
      197A  22 00 20 00       push   [loc+32]
      197E  12 00 00 00 96 43 push   #300f
      1984  0b 5d             NATIVE t0 #0x5d
      1986  22 00 20 00       push   [loc+32]
      198A  72 01 00 00       pushblk[glob+0] x1
      198E  79 1d             idxadd 29
      1990  7a 01             pushblk.heap x1
      1992  79 04             idxadd 4
      1994  0b 07             VecAdd()
      1996  72 01 00 00       pushblk[glob+0] x1
      199A  79 1b             idxadd 27
      199C  7a 01             pushblk.heap x1
      199E  79 05             idxadd 5
      19A0  52 05 00 00 80 3f push   #1f
      19A6  50 07             blkcopy
      19A8  52 07 00 00 20 41 push   #10f
      19AE  13 07 00 00       store  [loc+0]
L19B2: 19B2  32 01 00 00       pushblk[loc+0] x1
      19B6  12 01 00 00 00 00 push   #0f
      19BC  11 01             sub.f
      19BE  17 05             cmp.gtz.f
      19C0  15 05 41 00       bz     L1A46
      19C4  22 00 20 00       push   [loc+32]
      19C8  2a 04             pushblk.heap x4
      19CA  23 04 10 00       store  [loc+16]
      19CE  22 00 10 00       push   [loc+16]
      19D2  72 01 00 00       pushblk[glob+0] x1
      19D6  79 04             idxadd 4
      19D8  0b 08             VecSub()
      19DA  72 01 00 00       pushblk[glob+0] x1
      19DE  22 00 10 00       push   [loc+16]
      19E2  0b 24             NATIVE t0 #0x24
      19E4  22 00 10 00       push   [loc+16]
      19E8  0b 09             NATIVE t0 #0x09
      19EA  22 00 10 00       push   [loc+16]
      19EE  29 03             idxadd 3
      19F0  12 03 00 00 48 42 push   #50f
      19F6  10 07             blkcopy
      19F8  72 01 00 00       pushblk[glob+0] x1
      19FC  79 08             idxadd 8
      19FE  22 00 10 00       push   [loc+16]
      1A02  2a 04             pushblk.heap x4
      1A04  20 07             blkcopy
      1A06  22 00 00 00       push   [loc+0]
      1A0A  20 0c             dup
      1A0C  2a 01             pushblk.heap x1
      1A0E  0b 05             NATIVE t0 #0x05
      1A10  11 01             sub.f
      1A12  10 07             blkcopy
      1A14  10 00             end
      1A16  22 00 10 00       push   [loc+16]
      1A1A  0b 06             NATIVE t0 #0x06
      1A1C  12 06 00 00 96 43 push   #300f
      1A22  11 01             sub.f
      1A24  17 00             cmp.ltz.f
      1A26  15 00 0c 00       bz     L1A42
      1A2A  72 01 00 00       pushblk[glob+0] x1
      1A2E  79 08             idxadd 8
      1A30  79 03             idxadd 3
      1A32  52 03 00 00 00 00 push   #0f
      1A38  50 07             blkcopy
      1A3A  54 07 04 00       jmp    L1A46
      1A3E  54 07 00 00       jmp    L1A42
L1A42: 1A42  54 07 b6 ff       jmp    L19B2
L1A46: 1A46  72 01 00 00       pushblk[glob+0] x1
      1A4A  79 1b             idxadd 27
      1A4C  7a 01             pushblk.heap x1
      1A4E  79 05             idxadd 5
      1A50  52 05 cd cc cc 3d push   #0.1f
      1A56  50 07             blkcopy
      1A58  50 03             tailcall
L1A5A: 1A5A  52 03 00 00 82 42 push   #65f
      1A60  52 03 00 00 00 00 push   #0f
      1A66  52 03 00 00 96 43 push   #300f
      1A6C  52 03 00 00 70 42 push   #60f
      1A72  42 03 01 00 00 00 push   #1
      1A78  48 02 18 00       call   L1AAC locals=2
      1A7C  40 03             tailcall
L1A7E: 1A7E  52 03 00 00 48 42 push   #50f
      1A84  52 03 00 00 a0 c1 push   #-20f
      1A8A  52 03 00 00 a0 41 push   #20f
      1A90  58 02 90 0b       call   L31B4 locals=2
      1A94  52 02 00 00 20 42 push   #40f
      1A9A  52 02 00 00 c8 41 push   #25f
      1AA0  42 02 00 00 00 00 push   #0
      1AA6  48 02 01 00       call   L1AAC locals=2
      1AAA  40 03             tailcall
L1AAC: 1AAC  03 03 00 00       store  [loc+0]
      1AB0  03 03 04 00       store  [loc+4]
      1AB4  03 03 08 00       store  [loc+8]
      1AB8  03 03 0c 00       store  [loc+12]
      1ABC  03 03 10 00       store  [loc+16]
      1AC0  08 0e 6f 12       call   L3FA2 locals=14
      1AC4  05 0e 61 00       bz     L1B8A
      1AC8  08 0e 62 0a       call   L2F90 locals=14
      1ACC  72 01 00 00       pushblk[glob+0] x1
      1AD0  72 01 00 00       pushblk[glob+0] x1
      1AD4  79 1d             idxadd 29
      1AD6  7a 01             pushblk.heap x1
      1AD8  78 0e c2 0c       call   L3460 locals=14
      1ADC  72 01 00 00       pushblk[glob+0] x1
      1AE0  79 0c             idxadd 12
      1AE2  7a 04             pushblk.heap x4
      1AE4  33 04 20 00       store  [loc+32]
      1AE8  22 00 20 00       push   [loc+32]
      1AEC  32 01 10 00       pushblk[loc+16] x1
      1AF0  0b 5d             NATIVE t0 #0x5d
      1AF2  22 00 20 00       push   [loc+32]
      1AF6  32 01 0c 00       pushblk[loc+12] x1
      1AFA  0b 0a             RotateDeg()
      1AFC  22 00 20 00       push   [loc+32]
      1B00  29 01             idxadd 1
      1B02  32 01 08 00       pushblk[loc+8] x1
      1B06  30 07             blkcopy
      1B08  72 01 00 00       pushblk[glob+0] x1
      1B0C  42 01 03 00 00 00 push   #3
      1B12  52 01 00 00 00 00 push   #0f
      1B18  52 01 00 00 00 00 push   #0f
      1B1E  0b 0d             NATIVE t0 #0x0d
      1B20  72 01 00 00       pushblk[glob+0] x1
      1B24  78 0e 6a 0c       call   L33FC locals=14
      1B28  72 01 00 00       pushblk[glob+0] x1
      1B2C  32 01 00 00       pushblk[loc+0] x1
      1B30  0b a8             NATIVE t0 #0xa8
      1B32  72 01 00 00       pushblk[glob+0] x1
      1B36  42 01 04 00 00 00 push   #4
      1B3C  52 01 00 00 00 00 push   #0f
      1B42  52 01 00 00 00 00 push   #0f
      1B48  0b 0d             NATIVE t0 #0x0d
      1B4A  72 01 00 00       pushblk[glob+0] x1
      1B4E  22 00 20 00       push   [loc+32]
      1B52  12 00 66 66 66 3f push   #0.9f
      1B58  32 01 04 00       pushblk[loc+4] x1
      1B5C  0b 52             NATIVE t0 #0x52
      1B5E  72 01 00 00       pushblk[glob+0] x1
      1B62  42 01 03 00 00 00 push   #3
      1B68  0b 53             NATIVE t0 #0x53
L1B6A: 1B6A  72 01 00 00       pushblk[glob+0] x1
      1B6E  79 1c             idxadd 28
      1B70  7a 01             pushblk.heap x1
      1B72  42 01 00 00 00 00 push   #0
      1B78  41 01             sub.i
      1B7A  47 03             cmp.nez.i
      1B7C  45 03 03 00       bz     L1B86
      1B80  40 00             end
      1B82  44 00 f2 ff       jmp    L1B6A
L1B86: 1B86  44 00 00 00       jmp    L1B8A
L1B8A: 1B8A  40 03             tailcall
L1B8C: 1B8C  52 03 00 00 34 42 push   #45f
      1B92  52 03 00 00 f0 42 push   #120f
      1B98  58 0e 0c 0b       call   L31B4 locals=14
      1B9C  13 0e 20 00       store  [loc+32]
      1BA0  12 0e 00 00 b4 42 push   #90f
      1BA6  13 0e 24 00       store  [loc+36]
      1BAA  12 0e 33 33 f3 3f push   #1.9f
      1BB0  13 0e 28 00       store  [loc+40]
      1BB4  18 0e f5 11       call   L3FA2 locals=14
      1BB8  15 0e 95 00       bz     L1CE6
      1BBC  18 0e e8 09       call   L2F90 locals=14
      1BC0  18 0e 14 06       call   L27EC locals=14
      1BC4  0b 19             NATIVE t0 #0x19
      1BC6  03 19 2c 00       store  [loc+44]
      1BCA  32 01 2c 00       pushblk[loc+44] x1
      1BCE  12 01 00 00 00 3f push   #0.5f
      1BD4  11 01             sub.f
      1BD6  17 00             cmp.ltz.f
      1BD8  15 00 10 00       bz     L1BFC
      1BDC  22 00 24 00       push   [loc+36]
      1BE0  20 0c             dup
      1BE2  2a 01             pushblk.heap x1
      1BE4  12 01 00 00 80 bf push   #-1f
      1BEA  11 02             mul.f
      1BEC  10 07             blkcopy
      1BEE  02 07 dc 00 00 00 push   #220
      1BF4  03 07 00 00       store  [loc+0]
      1BF8  04 07 10 00       jmp    L1C1C
L1BFC: 1BFC  22 00 28 00       push   [loc+40]
      1C00  20 0c             dup
      1C02  2a 01             pushblk.heap x1
      1C04  12 01 00 00 80 bf push   #-1f
      1C0A  11 02             mul.f
      1C0C  10 07             blkcopy
      1C0E  02 07 dd 00 00 00 push   #221
      1C14  03 07 00 00       store  [loc+0]
      1C18  04 07 00 00       jmp    L1C1C
L1C1C: 1C1C  72 01 00 00       pushblk[glob+0] x1
      1C20  72 01 00 00       pushblk[glob+0] x1
      1C24  79 1d             idxadd 29
      1C26  7a 01             pushblk.heap x1
      1C28  78 0e 1a 0c       call   L3460 locals=14
      1C2C  72 01 00 00       pushblk[glob+0] x1
      1C30  79 0c             idxadd 12
      1C32  7a 04             pushblk.heap x4
      1C34  33 04 10 00       store  [loc+16]
      1C38  22 00 10 00       push   [loc+16]
      1C3C  32 01 24 00       pushblk[loc+36] x1
      1C40  0b 0a             RotateDeg()
L1C42: 1C42  32 01 20 00       pushblk[loc+32] x1
      1C46  12 01 00 00 00 00 push   #0f
      1C4C  11 01             sub.f
      1C4E  17 05             cmp.gtz.f
      1C50  15 05 45 00       bz     L1CDE
      1C54  72 01 00 00       pushblk[glob+0] x1
      1C58  32 01 00 00       pushblk[loc+0] x1
      1C5C  12 01 00 00 00 41 push   #8f
      1C62  0b 0c             NATIVE t0 #0x0c
      1C64  22 00 10 00       push   [loc+16]
      1C68  32 01 28 00       pushblk[loc+40] x1
      1C6C  0b 05             NATIVE t0 #0x05
      1C6E  11 02             mul.f
      1C70  0b 0a             RotateDeg()
      1C72  72 01 00 00       pushblk[glob+0] x1
      1C76  22 00 10 00       push   [loc+16]
      1C7A  0b 0b             NATIVE t0 #0x0b
      1C7C  72 01 00 00       pushblk[glob+0] x1
      1C80  79 08             idxadd 8
      1C82  22 00 10 00       push   [loc+16]
      1C86  2a 04             pushblk.heap x4
      1C88  20 07             blkcopy
      1C8A  72 01 00 00       pushblk[glob+0] x1
      1C8E  79 08             idxadd 8
      1C90  79 03             idxadd 3
      1C92  52 03 00 00 70 41 push   #15f
      1C98  50 07             blkcopy
      1C9A  22 00 20 00       push   [loc+32]
      1C9E  20 0c             dup
      1CA0  2a 01             pushblk.heap x1
      1CA2  0b 05             NATIVE t0 #0x05
      1CA4  11 01             sub.f
      1CA6  10 07             blkcopy
      1CA8  10 00             end
      1CAA  18 0e 64 09       call   L2F76 locals=14
      1CAE  12 0e 00 00 96 43 push   #300f
      1CB4  11 01             sub.f
      1CB6  17 00             cmp.ltz.f
      1CB8  10 0c             dup
      1CBA  15 0c 08 00       bz     L1CCE
      1CBE  32 01 20 00       pushblk[loc+32] x1
      1CC2  12 01 00 00 f0 41 push   #30f
      1CC8  11 01             sub.f
      1CCA  17 00             cmp.ltz.f
      1CCC  01 0a             land.i
L1CCE: 1CCE  05 0a 04 00       bz     L1CDA
      1CD2  04 0a 04 00       jmp    L1CDE
      1CD6  04 0a 00 00       jmp    L1CDA
L1CDA: 1CDA  04 0a b2 ff       jmp    L1C42
L1CDE: 1CDE  08 0e 5a 05       call   L2796 locals=14
      1CE2  04 0e 00 00       jmp    L1CE6
L1CE6: 1CE6  72 01 00 00       pushblk[glob+0] x1
      1CEA  72 01 00 00       pushblk[glob+0] x1
      1CEE  79 1d             idxadd 29
      1CF0  7a 01             pushblk.heap x1
      1CF2  78 0e a0 0b       call   L3436 locals=14
      1CF6  70 03             tailcall
L1CF8: 1CF8  72 01 00 00       pushblk[glob+0] x1
      1CFC  79 1b             idxadd 27
      1CFE  7a 01             pushblk.heap x1
      1D00  79 01             idxadd 1
      1D02  52 01 00 00 80 40 push   #4f
      1D08  50 07             blkcopy
      1D0A  72 01 00 00       pushblk[glob+0] x1
      1D0E  79 1b             idxadd 27
      1D10  7a 01             pushblk.heap x1
      1D12  79 02             idxadd 2
      1D14  52 02 00 00 70 41 push   #15f
      1D1A  50 07             blkcopy
      1D1C  58 02 38 09       call   L2F90 locals=2
      1D20  72 01 10 00       pushblk[glob+16] x1
      1D24  42 01 00 00 00 00 push   #0
      1D2A  41 01             sub.i
      1D2C  47 02             cmp.eqz.i
      1D2E  45 02 07 00       bz     L1D40
      1D32  42 02 00 00 01 00 push   #65536
      1D38  03 02 00 00       store  [loc+0]
      1D3C  04 02 07 00       jmp    L1D4E
L1D40: 1D40  02 02 01 00 01 00 push   #65537
      1D46  03 02 00 00       store  [loc+0]
      1D4A  04 02 00 00       jmp    L1D4E
L1D4E: 1D4E  08 02 12 09       call   L2F76 locals=2
      1D52  12 02 00 00 dc 43 push   #440f
      1D58  11 01             sub.f
      1D5A  17 05             cmp.gtz.f
      1D5C  10 0c             dup
      1D5E  15 0c 03 00       bz     L1D68
      1D62  18 02 1e 11       call   L3FA2 locals=2
      1D66  01 0a             land.i
L1D68: 1D68  05 0a 16 00       bz     L1D98
      1D6C  08 02 3e 05       call   L27EC locals=2
      1D70  72 01 00 00       pushblk[glob+0] x1
      1D74  32 01 00 00       pushblk[loc+0] x1
      1D78  12 01 00 00 34 43 push   #180f
      1D7E  12 01 00 00 00 00 push   #0f
      1D84  12 01 00 00 c8 43 push   #400f
      1D8A  18 02 8d 0b       call   L34A8 locals=2
      1D8E  10 04             pop
      1D90  18 02 01 05       call   L2796 locals=2
      1D94  14 02 00 00       jmp    L1D98
L1D98: 1D98  10 03             tailcall
L1D9A: 1D9A  13 03 00 00       store  [loc+0]
      1D9E  18 02 f1 00       call   L1F84 locals=2
      1DA2  32 01 00 00       pushblk[loc+0] x1
      1DA6  38 02 4e 11       call   L4046 locals=2
      1DAA  12 02 00 00 16 43 push   #150f
      1DB0  18 02 34 00       call   L1E1C locals=2
      1DB4  10 03             tailcall
L1DB6: 1DB6  13 03 00 00       store  [loc+0]
      1DBA  18 02 e3 00       call   L1F84 locals=2
      1DBE  32 01 00 00       pushblk[loc+0] x1
      1DC2  38 02 40 11       call   L4046 locals=2
      1DC6  12 02 00 00 7a 44 push   #1000f
      1DCC  18 02 26 00       call   L1E1C locals=2
      1DD0  10 03             tailcall
      1DD2  72 01 00 00       pushblk[glob+0] x1
      1DD6  42 01 00 02 00 00 push   #512
      1DDC  48 06 17 0c       call   L360E locals=6
      1DE0  48 06 d0 00       call   L1F84 locals=6

