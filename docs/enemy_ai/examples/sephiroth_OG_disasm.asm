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

; ===== ex_3000_04.bd  block@0x3BA500  code@0x3BA518  size=0x556 =====
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
      00CE  18 16 d2 04       call   L0A76 locals=22
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
      011C  38 16 a2 04       call   L0A64 locals=22
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
      0158  28 16 5f 03       call   L081A locals=22
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
      0182  a8 16 24 03       call   L07CE locals=22
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
      01AC  18 16 69 03       call   L0882 locals=22
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
      02B8  18 16 e3 02       call   L0882 locals=22
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

; ===== ex_3000.bd  block@0x3BBB80  code@0x3BC4B8  size=0x1D44 =====
      0938  00 00             end   ; ---- routine end ----
      093A  00 00             end   ; ---- routine end ----
      093C  97 4e             cmp.?.f
      093E  00 00             end   ; ---- routine end ----
      0940  62 00 04 00       push   [glob+4]
      0944  42 00 a8 04 00 00 push   #1192
      094A  48 02 2a 13       call   L2FA2 locals=2
      094E  40 03             tailcall
      0950  72 01 14 00       pushblk[glob+20] x1
      0954  42 01 04 00 00 00 push   #4
      095A  41 01             sub.i
      095C  47 02             cmp.eqz.i
      095E  45 02 1a 00       bz     L0996
      0962  72 01 10 00       pushblk[glob+16] x1
      0966  42 01 02 00 00 00 push   #2
      096C  41 01             sub.i
      096E  47 03             cmp.nez.i
      0970  45 03 06 00       bz     L0980
      0974  48 02 13 0d       call   L239E locals=2
      0978  48 02 0d 0e       call   L2596 locals=2
      097C  44 02 09 00       jmp    L0992
L0980: 0980  52 02 00 00 00 00 push   #0f
      0986  58 02 71 09       call   L1C6C locals=2
      098A  58 02 2e 04       call   L11EA locals=2
      098E  54 02 00 00       jmp    L0992
L0992: 0992  54 02 8e 00       jmp    L0AB2
L0996: 0996  72 01 14 00       pushblk[glob+20] x1
      099A  42 01 05 00 00 00 push   #5
      09A0  41 01             sub.i
      09A2  47 02             cmp.eqz.i
      09A4  45 02 30 00       bz     L0A08
      09A8  72 01 10 00       pushblk[glob+16] x1
      09AC  42 01 02 00 00 00 push   #2
      09B2  41 01             sub.i
      09B4  47 03             cmp.nez.i
      09B6  45 03 1f 00       bz     L09F8
      09BA  0b 19             NATIVE t0 #0x19
      09BC  03 19 00 00       store  [loc+0]
      09C0  32 01 00 00       pushblk[loc+0] x1
      09C4  12 01 9a 99 99 3e push   #0.3f
      09CA  11 01             sub.f
      09CC  17 00             cmp.ltz.f
      09CE  15 00 04 00       bz     L09DA
      09D2  18 02 e0 0d       call   L2596 locals=2
      09D6  14 02 0d 00       jmp    L09F4
L09DA: 09DA  32 01 00 00       pushblk[loc+0] x1
      09DE  12 01 9a 99 19 3f push   #0.6f
      09E4  11 01             sub.f
      09E6  17 00             cmp.ltz.f
      09E8  15 00 04 00       bz     L09F4
      09EC  18 02 4e 0d       call   L248C locals=2
      09F0  14 02 00 00       jmp    L09F4
L09F4: 09F4  14 02 04 00       jmp    L0A00
L09F8: 09F8  18 02 cd 0d       call   L2596 locals=2
      09FC  14 02 00 00       jmp    L0A00
L0A00: 0A00  18 02 cd 0c       call   L239E locals=2
      0A04  14 02 55 00       jmp    L0AB2
L0A08: 0A08  72 01 14 00       pushblk[glob+20] x1
      0A0C  42 01 06 00 00 00 push   #6
      0A12  41 01             sub.i
      0A14  47 02             cmp.eqz.i
      0A16  45 02 3d 00       bz     L0A94
      0A1A  72 01 10 00       pushblk[glob+16] x1
      0A1E  42 01 02 00 00 00 push   #2
      0A24  41 01             sub.i
      0A26  47 03             cmp.nez.i
      0A28  45 03 19 00       bz     L0A5E
      0A2C  52 03 00 00 c8 41 push   #25f
      0A32  58 02 1b 09       call   L1C6C locals=2
      0A36  58 02 29 0d       call   L248C locals=2
      0A3A  0b 19             NATIVE t0 #0x19
      0A3C  03 19 00 00       store  [loc+0]
      0A40  32 01 00 00       pushblk[loc+0] x1
      0A44  12 01 cd cc cc 3e push   #0.4f
      0A4A  11 01             sub.f
      0A4C  17 00             cmp.ltz.f
      0A4E  15 00 04 00       bz     L0A5A
      0A52  18 02 1b 0d       call   L248C locals=2
      0A56  14 02 00 00       jmp    L0A5A
L0A5A: 0A5A  14 02 19 00       jmp    L0A90
L0A5E: 0A5E  12 02 00 00 0c 42 push   #35f
      0A64  18 02 02 09       call   L1C6C locals=2
      0A68  18 02 c4 0b       call   L21F4 locals=2
      0A6C  0b 19             NATIVE t0 #0x19
      0A6E  03 19 00 00       store  [loc+0]
      0A72  32 01 00 00       pushblk[loc+0] x1
      0A76  12 01 cd cc cc 3e push   #0.4f
      0A7C  11 01             sub.f
      0A7E  17 00             cmp.ltz.f
      0A80  15 00 04 00       bz     L0A8C
      0A84  18 02 87 0d       call   L2596 locals=2
      0A88  14 02 00 00       jmp    L0A8C
L0A8C: 0A8C  14 02 00 00       jmp    L0A90
L0A90: 0A90  14 02 0f 00       jmp    L0AB2
L0A94: 0A94  72 01 14 00       pushblk[glob+20] x1
      0A98  42 01 07 00 00 00 push   #7
      0A9E  41 01             sub.i
      0AA0  47 02             cmp.eqz.i
      0AA2  45 02 06 00       bz     L0AB2
      0AA6  48 02 df 0d       call   L2668 locals=2
      0AAA  48 02 0b 00       call   L0AC4 locals=2
      0AAE  44 02 00 00       jmp    L0AB2
L0AB2: 0AB2  62 00 04 00       push   [glob+4]
      0AB6  42 00 00 00 00 00 push   #0
      0ABC  48 02 9b 12       call   L2FF6 locals=2
      0AC0  40 08             abort
      0AC2  40 03             tailcall
L0AC4: 0AC4  48 0a c2 15       call   L364C locals=10
      0AC8  72 01 00 00       pushblk[glob+0] x1
      0ACC  22 00 10 00       push   [loc+16]
      0AD0  12 00 00 00 00 00 push   #0f
      0AD6  12 00 00 00 00 00 push   #0f
      0ADC  12 00 00 00 00 00 push   #0f
      0AE2  12 00 00 00 80 3f push   #1f
      0AE8  18 0a b3 17       call   L3A52 locals=10
      0AEC  0b 87             NATIVE t0 #0x87
      0AEE  72 01 00 00       pushblk[glob+0] x1
      0AF2  79 1c             idxadd 28
      0AF4  7a 01             pushblk.heap x1
      0AF6  42 01 00 00 00 00 push   #0
      0AFC  41 01             sub.i
      0AFE  47 02             cmp.eqz.i
      0B00  45 02 07 00       bz     L0B12
      0B04  42 02 48 00 00 00 push   #72
      0B0A  03 02 00 00       store  [loc+0]
      0B0E  04 02 07 00       jmp    L0B20
L0B12: 0B12  02 02 4e 00 00 00 push   #78
      0B18  03 02 00 00       store  [loc+0]
      0B1C  04 02 00 00       jmp    L0B20
L0B20: 0B20  72 01 00 00       pushblk[glob+0] x1
      0B24  32 01 00 00       pushblk[loc+0] x1
      0B28  02 01 00 00 01 00 push   #65536
      0B2E  01 06             or.i
      0B30  12 06 00 00 00 00 push   #0f
      0B36  12 06 00 00 00 40 push   #2f
      0B3C  0b 0d             NATIVE t0 #0x0d
      0B3E  72 01 00 00       pushblk[glob+0] x1
      0B42  42 01 2b 00 00 00 push   #43
      0B48  0b a8             NATIVE t0 #0xa8
      0B4A  12 a8 cd cc 4c 3d push   #0.05f
      0B50  12 a8 00 00 00 41 push   #8f
      0B56  18 0a 9e 0f       call   L2A96 locals=10
      0B5A  72 01 00 00       pushblk[glob+0] x1
      0B5E  42 01 03 00 00 00 push   #3
      0B64  0b 4b             NATIVE t0 #0x4b
      0B66  00 04             pop
      0B68  12 04 00 00 16 43 push   #150f
      0B6E  18 0a c8 19       call   L3F02 locals=10
      0B72  18 0a 30 0f       call   L29D6 locals=10
      0B76  10 03             tailcall
      0B78  13 03 00 00       store  [loc+0]
      0B7C  72 01 10 00       pushblk[glob+16] x1
      0B80  42 01 03 00 00 00 push   #3
      0B86  41 01             sub.i
      0B88  47 03             cmp.nez.i
      0B8A  40 0c             dup
      0B8C  45 0c 0a 00       bz     L0BA4
      0B90  72 01 00 00       pushblk[glob+0] x1
      0B94  79 1f             idxadd 31
      0B96  7a 01             pushblk.heap x1
      0B98  78 02 dd 11       call   L2F56 locals=2
      0B9C  78 02 fc 14       call   L3598 locals=2
      0BA0  47 02             cmp.eqz.i
      0BA2  41 0a             land.i
L0BA4: 0BA4  45 0a 22 00       bz     L0BEC
      0BA8  32 01 00 00       pushblk[loc+0] x1
      0BAC  02 01 00 00 00 00 push   #0
      0BB2  08 02 e8 16       call   L3986 locals=2
      0BB6  72 01 00 00       pushblk[glob+0] x1
      0BBA  42 01 04 00 00 00 push   #4
      0BC0  48 02 7b 14       call   L34BA locals=2
      0BC4  42 02 03 00 00 00 push   #3
      0BCA  43 02 10 00       store  [glob+16]
      0BCE  42 02 07 00 00 00 push   #7
      0BD4  43 02 14 00       store  [glob+20]
      0BD8  62 00 04 00       push   [glob+4]
      0BDC  42 00 01 00 00 00 push   #1
      0BE2  48 02 08 12       call   L2FF6 locals=2
      0BE6  40 08             abort
      0BE8  44 08 0b 00       jmp    L0C02
L0BEC: 0BEC  72 01 00 00       pushblk[glob+0] x1
      0BF0  79 1b             idxadd 27
      0BF2  7a 01             pushblk.heap x1
      0BF4  79 0f             idxadd 15
      0BF6  42 0f 01 00 00 00 push   #1
      0BFC  40 07             blkcopy
      0BFE  44 07 00 00       jmp    L0C02
L0C02: 0C02  40 03             tailcall
      0C04  62 00 04 00       push   [glob+4]
      0C08  42 00 0a 06 00 00 push   #1546
      0C0E  48 02 c8 11       call   L2FA2 locals=2
      0C12  40 03             tailcall
L0C14: 0C14  72 01 10 00       pushblk[glob+16] x1
      0C18  42 01 00 00 00 00 push   #0
      0C1E  41 01             sub.i
      0C20  47 02             cmp.eqz.i
      0C22  45 02 04 00       bz     L0C2E
      0C26  48 02 1b 02       call   L1060 locals=2
      0C2A  44 02 11 00       jmp    L0C50
L0C2E: 0C2E  72 01 10 00       pushblk[glob+16] x1
      0C32  42 01 01 00 00 00 push   #1
      0C38  41 01             sub.i
      0C3A  47 02             cmp.eqz.i
      0C3C  45 02 04 00       bz     L0C48
      0C40  48 02 2e 01       call   L0EA0 locals=2
      0C44  44 02 04 00       jmp    L0C50
L0C48: 0C48  48 02 06 00       call   L0C58 locals=2
      0C4C  44 02 00 00       jmp    L0C50
L0C50: 0C50  40 00             end
      0C52  44 00 df ff       jmp    L0C14
      0C56  40 03             tailcall
L0C58: 0C58  52 03 00 00 c8 41 push   #25f
      0C5E  13 03 00 00       store  [loc+0]
      0C62  62 00 18 00       push   [glob+24]
      0C66  60 0c             dup
      0C68  6a 01             pushblk.heap x1
      0C6A  42 01 01 00 00 00 push   #1
      0C70  41 00             add.i
      0C72  40 07             blkcopy
      0C74  72 01 18 00       pushblk[glob+24] x1
      0C78  42 01 02 00 00 00 push   #2
      0C7E  41 01             sub.i
      0C80  47 01             cmp.lez.i
      0C82  45 01 4c 00       bz     L0D1E
      0C86  48 02 b0 02       call   L11EA locals=2
      0C8A  72 01 18 00       pushblk[glob+24] x1
      0C8E  42 01 02 00 00 00 push   #2
      0C94  41 01             sub.i
      0C96  47 03             cmp.nez.i
      0C98  45 03 04 00       bz     L0CA4
      0C9C  48 02 38 09       call   L1F10 locals=2
      0CA0  44 02 00 00       jmp    L0CA4
L0CA4: 0CA4  48 02 db 06       call   L1A5E locals=2
      0CA8  48 02 a4 0a       call   L21F4 locals=2
      0CAC  0b 19             NATIVE t0 #0x19
      0CAE  03 19 04 00       store  [loc+4]
      0CB2  32 01 04 00       pushblk[loc+4] x1
      0CB6  12 01 cd cc cc 3e push   #0.4f
      0CBC  11 01             sub.f
      0CBE  17 00             cmp.ltz.f
      0CC0  15 00 04 00       bz     L0CCC
      0CC4  18 02 67 0c       call   L2596 locals=2
      0CC8  14 02 0d 00       jmp    L0CE6
L0CCC: 0CCC  32 01 04 00       pushblk[loc+4] x1
      0CD0  12 01 cd cc 4c 3f push   #0.8f
      0CD6  11 01             sub.f
      0CD8  17 00             cmp.ltz.f
      0CDA  15 00 04 00       bz     L0CE6
      0CDE  18 02 d5 0b       call   L248C locals=2
      0CE2  14 02 00 00       jmp    L0CE6
L0CE6: 0CE6  18 02 70 07       call   L1BCA locals=2
      0CEA  18 02 83 0a       call   L21F4 locals=2
      0CEE  0b 19             NATIVE t0 #0x19
      0CF0  03 19 04 00       store  [loc+4]
      0CF4  32 01 04 00       pushblk[loc+4] x1
      0CF8  12 01 9a 99 19 3f push   #0.6f
      0CFE  11 01             sub.f
      0D00  17 00             cmp.ltz.f
      0D02  15 00 06 00       bz     L0D12
      0D06  18 02 aa 06       call   L1A5E locals=2
      0D0A  18 02 73 0a       call   L21F4 locals=2
      0D0E  14 02 00 00       jmp    L0D12
L0D12: 0D12  18 02 40 0c       call   L2596 locals=2
      0D16  18 02 6d 0a       call   L21F4 locals=2
      0D1A  14 02 c0 00       jmp    L0E9E
L0D1E: 0D1E  72 01 18 00       pushblk[glob+24] x1
      0D22  42 01 04 00 00 00 push   #4
      0D28  41 01             sub.i
      0D2A  47 01             cmp.lez.i
      0D2C  45 01 58 00       bz     L0DE0
      0D30  48 02 4b 07       call   L1BCA locals=2
      0D34  48 02 fa 05       call   L192C locals=2
      0D38  48 02 a8 0b       call   L248C locals=2
      0D3C  48 02 45 07       call   L1BCA locals=2
      0D40  0b 19             NATIVE t0 #0x19
      0D42  03 19 04 00       store  [loc+4]
      0D46  32 01 04 00       pushblk[loc+4] x1
      0D4A  12 01 33 33 33 3f push   #0.7f
      0D50  11 01             sub.f
      0D52  17 00             cmp.ltz.f
      0D54  15 00 06 00       bz     L0D64
      0D58  32 01 00 00       pushblk[loc+0] x1
      0D5C  38 02 86 07       call   L1C6C locals=2
      0D60  34 02 00 00       jmp    L0D64
L0D64: 0D64  38 02 46 0a       call   L21F4 locals=2
      0D68  38 02 f2 05       call   L1950 locals=2
      0D6C  12 02 00 00 00 00 push   #0f
      0D72  18 02 7b 07       call   L1C6C locals=2
      0D76  18 02 89 0b       call   L248C locals=2
      0D7A  18 02 e9 05       call   L1950 locals=2
      0D7E  0b 19             NATIVE t0 #0x19
      0D80  03 19 04 00       store  [loc+4]
      0D84  32 01 04 00       pushblk[loc+4] x1
      0D88  12 01 33 33 33 3f push   #0.7f
      0D8E  11 01             sub.f
      0D90  17 00             cmp.ltz.f
      0D92  15 00 07 00       bz     L0DA4
      0D96  12 00 00 00 00 00 push   #0f
      0D9C  18 02 74 07       call   L1C88 locals=2
      0DA0  14 02 00 00       jmp    L0DA4
L0DA4: 0DA4  18 02 26 0a       call   L21F4 locals=2
      0DA8  18 02 f5 0b       call   L2596 locals=2
      0DAC  18 02 22 0a       call   L21F4 locals=2
      0DB0  18 02 0b 07       call   L1BCA locals=2
      0DB4  0b 19             NATIVE t0 #0x19
      0DB6  03 19 04 00       store  [loc+4]
      0DBA  32 01 04 00       pushblk[loc+4] x1
      0DBE  12 01 33 33 33 3f push   #0.7f
      0DC4  11 01             sub.f
      0DC6  17 00             cmp.ltz.f
      0DC8  15 00 06 00       bz     L0DD8
      0DCC  32 01 00 00       pushblk[loc+0] x1
      0DD0  38 02 4c 07       call   L1C6C locals=2
      0DD4  34 02 00 00       jmp    L0DD8
L0DD8: 0DD8  38 02 e1 0a       call   L239E locals=2
      0DDC  34 02 5f 00       jmp    L0E9E
L0DE0: 0DE0  72 01 18 00       pushblk[glob+24] x1
      0DE4  42 01 05 00 00 00 push   #5
      0DEA  41 01             sub.i
      0DEC  47 01             cmp.lez.i
      0DEE  45 01 30 00       bz     L0E52
      0DF2  32 01 00 00       pushblk[loc+0] x1
      0DF6  38 02 39 07       call   L1C6C locals=2
      0DFA  38 02 f6 01       call   L11EA locals=2
      0DFE  32 01 00 00       pushblk[loc+0] x1
      0E02  38 02 33 07       call   L1C6C locals=2
      0E06  38 02 f0 01       call   L11EA locals=2
      0E0A  38 02 f3 09       call   L21F4 locals=2
      0E0E  38 02 dc 06       call   L1BCA locals=2
      0E12  38 02 c0 0b       call   L2596 locals=2
      0E16  38 02 d8 06       call   L1BCA locals=2
      0E1A  38 02 eb 09       call   L21F4 locals=2
      0E1E  38 02 8c 09       call   L213A locals=2
      0E22  38 02 1c 06       call   L1A5E locals=2
      0E26  0b 19             NATIVE t0 #0x19
      0E28  03 19 04 00       store  [loc+4]
      0E2C  32 01 04 00       pushblk[loc+4] x1
      0E30  12 01 9a 99 19 3f push   #0.6f
      0E36  11 01             sub.f
      0E38  17 00             cmp.ltz.f
      0E3A  15 00 04 00       bz     L0E46
      0E3E  18 02 25 0b       call   L248C locals=2
      0E42  14 02 04 00       jmp    L0E4E
L0E46: 0E46  18 02 a6 0b       call   L2596 locals=2
      0E4A  14 02 00 00       jmp    L0E4E
L0E4E: 0E4E  14 02 26 00       jmp    L0E9E
L0E52: 0E52  72 01 18 00       pushblk[glob+24] x1
      0E56  42 01 06 00 00 00 push   #6
      0E5C  41 01             sub.i
      0E5E  47 01             cmp.lez.i
      0E60  45 01 14 00       bz     L0E8C
      0E64  48 02 1c 02       call   L12A0 locals=2
      0E68  0b 19             NATIVE t0 #0x19
      0E6A  03 19 04 00       store  [loc+4]
      0E6E  32 01 04 00       pushblk[loc+4] x1
      0E72  12 01 9a 99 99 3e push   #0.3f
      0E78  11 01             sub.f
      0E7A  17 00             cmp.ltz.f
      0E7C  15 00 04 00       bz     L0E88
      0E80  18 02 0e 02       call   L12A0 locals=2
      0E84  14 02 00 00       jmp    L0E88
L0E88: 0E88  14 02 09 00       jmp    L0E9E
L0E8C: 0E8C  02 02 00 00 00 00 push   #0
      0E92  43 02 18 00       store  [glob+24]
      0E96  48 02 50 09       call   L213A locals=2
      0E9A  44 02 00 00       jmp    L0E9E
L0E9E: 0E9E  40 03             tailcall
L0EA0: 0EA0  52 03 00 00 c8 41 push   #25f
      0EA6  13 03 00 00       store  [loc+0]
      0EAA  62 00 18 00       push   [glob+24]
      0EAE  60 0c             dup
      0EB0  6a 01             pushblk.heap x1
      0EB2  42 01 01 00 00 00 push   #1
      0EB8  41 00             add.i
      0EBA  40 07             blkcopy
      0EBC  72 01 18 00       pushblk[glob+24] x1
      0EC0  42 01 01 00 00 00 push   #1
      0EC6  41 01             sub.i
      0EC8  47 02             cmp.eqz.i
      0ECA  45 02 06 00       bz     L0EDA
      0ECE  48 02 7c 06       call   L1BCA locals=2
      0ED2  48 02 32 09       call   L213A locals=2
      0ED6  44 02 a9 00       jmp    L102C
L0EDA: 0EDA  72 01 18 00       pushblk[glob+24] x1
      0EDE  42 01 03 00 00 00 push   #3
      0EE4  41 01             sub.i
      0EE6  47 01             cmp.lez.i
      0EE8  45 01 97 00       bz     L101A
      0EEC  48 02 6d 06       call   L1BCA locals=2
      0EF0  48 02 51 0b       call   L2596 locals=2
      0EF4  48 02 b3 05       call   L1A5E locals=2
      0EF8  0b 19             NATIVE t0 #0x19
      0EFA  03 19 04 00       store  [loc+4]
      0EFE  32 01 04 00       pushblk[loc+4] x1
      0F02  12 01 9a 99 19 3f push   #0.6f
      0F08  11 01             sub.f
      0F0A  17 00             cmp.ltz.f
      0F0C  15 00 06 00       bz     L0F1C
      0F10  32 01 00 00       pushblk[loc+0] x1
      0F14  38 02 aa 06       call   L1C6C locals=2
      0F18  34 02 00 00       jmp    L0F1C
L0F1C: 0F1C  38 02 b6 0a       call   L248C locals=2
      0F20  38 02 53 06       call   L1BCA locals=2
      0F24  0b 19             NATIVE t0 #0x19
      0F26  03 19 04 00       store  [loc+4]
      0F2A  32 01 04 00       pushblk[loc+4] x1
      0F2E  12 01 33 33 33 3f push   #0.7f
      0F34  11 01             sub.f
      0F36  17 00             cmp.ltz.f
      0F38  15 00 08 00       bz     L0F4C
      0F3C  32 01 00 00       pushblk[loc+0] x1
      0F40  38 02 94 06       call   L1C6C locals=2
      0F44  38 02 a2 0a       call   L248C locals=2
      0F48  34 02 08 00       jmp    L0F5C
L0F4C: 0F4C  38 02 00 05       call   L1950 locals=2
      0F50  38 02 3b 06       call   L1BCA locals=2
      0F54  38 02 23 0a       call   L239E locals=2
      0F58  34 02 00 00       jmp    L0F5C
L0F5C: 0F5C  38 02 7f 05       call   L1A5E locals=2
      0F60  0b 19             NATIVE t0 #0x19
      0F62  03 19 04 00       store  [loc+4]
      0F66  32 01 04 00       pushblk[loc+4] x1
      0F6A  12 01 9a 99 99 3e push   #0.3f
      0F70  11 01             sub.f
      0F72  17 00             cmp.ltz.f
      0F74  15 00 06 00       bz     L0F84
      0F78  32 01 00 00       pushblk[loc+0] x1
      0F7C  38 02 76 06       call   L1C6C locals=2
      0F80  34 02 00 00       jmp    L0F84
L0F84: 0F84  38 02 07 0b       call   L2596 locals=2
      0F88  0b 19             NATIVE t0 #0x19
      0F8A  03 19 04 00       store  [loc+4]
      0F8E  32 01 04 00       pushblk[loc+4] x1
      0F92  12 01 9a 99 99 3e push   #0.3f
      0F98  11 01             sub.f
      0F9A  17 00             cmp.ltz.f
      0F9C  15 00 0a 00       bz     L0FB4
      0FA0  18 02 13 06       call   L1BCA locals=2
      0FA4  32 01 00 00       pushblk[loc+0] x1
      0FA8  38 02 60 06       call   L1C6C locals=2
      0FAC  38 02 6e 0a       call   L248C locals=2
      0FB0  34 02 17 00       jmp    L0FE2
L0FB4: 0FB4  32 01 04 00       pushblk[loc+4] x1
      0FB8  12 01 9a 99 19 3f push   #0.6f
      0FBE  11 01             sub.f
      0FC0  17 00             cmp.ltz.f
      0FC2  15 00 08 00       bz     L0FD6
      0FC6  18 02 b1 04       call   L192C locals=2
      0FCA  18 02 fe 05       call   L1BCA locals=2
      0FCE  18 02 e2 0a       call   L2596 locals=2
      0FD2  14 02 06 00       jmp    L0FE2
L0FD6: 0FD6  18 02 f8 05       call   L1BCA locals=2
      0FDA  18 02 e0 09       call   L239E locals=2
      0FDE  14 02 00 00       jmp    L0FE2
L0FE2: 0FE2  18 02 b5 04       call   L1950 locals=2
      0FE6  18 02 3a 05       call   L1A5E locals=2
      0FEA  18 02 a6 08       call   L213A locals=2
      0FEE  0b 19             NATIVE t0 #0x19
      0FF0  03 19 04 00       store  [loc+4]
      0FF4  32 01 04 00       pushblk[loc+4] x1
      0FF8  12 01 cd cc cc 3e push   #0.4f
      0FFE  11 01             sub.f
      1000  17 00             cmp.ltz.f
      1002  15 00 06 00       bz     L1012
      1006  32 01 00 00       pushblk[loc+0] x1
      100A  38 02 2f 06       call   L1C6C locals=2
      100E  34 02 00 00       jmp    L1012
L1012: 1012  38 02 3b 0a       call   L248C locals=2
      1016  34 02 09 00       jmp    L102C
L101A: 101A  38 02 41 01       call   L12A0 locals=2
      101E  02 02 00 00 00 00 push   #0
      1024  43 02 18 00       store  [glob+24]
      1028  44 02 00 00       jmp    L102C
L102C: 102C  72 01 00 00       pushblk[glob+0] x1
      1030  78 02 57 11       call   L32E2 locals=2
      1034  52 02 9a 99 99 3e push   #0.3f
      103A  51 01             sub.f
      103C  57 00             cmp.ltz.f
      103E  55 00 0e 00       bz     L105E
      1042  42 00 00 00 00 00 push   #0
      1048  43 00 18 00       store  [glob+24]
      104C  42 00 02 00 00 00 push   #2
      1052  43 00 10 00       store  [glob+16]
      1056  48 02 73 00       call   L1140 locals=2
      105A  44 02 00 00       jmp    L105E
L105E: 105E  40 03             tailcall
L1060: 1060  48 02 b3 05       call   L1BCA locals=2
      1064  0b 19             NATIVE t0 #0x19
      1066  03 19 00 00       store  [loc+0]
      106A  32 01 00 00       pushblk[loc+0] x1
      106E  12 01 33 33 33 3f push   #0.7f
      1074  11 01             sub.f
      1076  17 00             cmp.ltz.f
      1078  15 00 04 00       bz     L1084
      107C  18 02 8b 0a       call   L2596 locals=2
      1080  14 02 04 00       jmp    L108C
L1084: 1084  18 02 02 0a       call   L248C locals=2
      1088  14 02 00 00       jmp    L108C
L108C: 108C  18 02 ec 00       call   L1268 locals=2
      1090  18 02 5e 04       call   L1950 locals=2
      1094  0b 19             NATIVE t0 #0x19
      1096  03 19 00 00       store  [loc+0]
      109A  32 01 00 00       pushblk[loc+0] x1
      109E  12 01 33 33 33 3f push   #0.7f
      10A4  11 01             sub.f
      10A6  17 00             cmp.ltz.f
      10A8  15 00 04 00       bz     L10B4
      10AC  18 02 73 0a       call   L2596 locals=2
      10B0  14 02 04 00       jmp    L10BC
L10B4: 10B4  18 02 ea 09       call   L248C locals=2
      10B8  14 02 00 00       jmp    L10BC
L10BC: 10BC  18 02 d4 00       call   L1268 locals=2
      10C0  18 02 83 05       call   L1BCA locals=2
      10C4  18 02 e2 09       call   L248C locals=2
      10C8  18 02 ce 00       call   L1268 locals=2
      10CC  0b 19             NATIVE t0 #0x19
      10CE  03 19 00 00       store  [loc+0]
      10D2  32 01 00 00       pushblk[loc+0] x1
      10D6  12 01 33 33 33 3f push   #0.7f
      10DC  11 01             sub.f
      10DE  17 00             cmp.ltz.f
      10E0  15 00 06 00       bz     L10F0
      10E4  18 02 71 05       call   L1BCA locals=2
      10E8  18 02 55 0a       call   L2596 locals=2
      10EC  14 02 08 00       jmp    L1100
L10F0: 10F0  18 02 1c 04       call   L192C locals=2
      10F4  18 02 69 05       call   L1BCA locals=2
      10F8  18 02 c8 09       call   L248C locals=2
      10FC  14 02 00 00       jmp    L1100
L1100: 1100  18 02 4d 09       call   L239E locals=2
      1104  18 02 b0 00       call   L1268 locals=2
      1108  72 01 00 00       pushblk[glob+0] x1
      110C  78 02 e9 10       call   L32E2 locals=2
      1110  52 02 66 66 26 3f push   #0.65f
      1116  51 01             sub.f
      1118  57 00             cmp.ltz.f
      111A  55 00 10 00       bz     L113E
      111E  42 00 00 00 00 00 push   #0
      1124  43 00 18 00       store  [glob+24]
      1128  42 00 01 00 00 00 push   #1
      112E  43 00 10 00       store  [glob+16]
      1132  48 02 fb 03       call   L192C locals=2
      1136  48 02 58 00       call   L11EA locals=2
      113A  44 02 00 00       jmp    L113E
L113E: 113E  40 03             tailcall
L1140: 1140  48 02 8a 0e       call   L2E58 locals=2
      1144  72 01 00 00       pushblk[glob+0] x1
      1148  42 01 40 00 00 00 push   #64
      114E  48 02 c2 11       call   L34D6 locals=2
      1152  72 01 00 00       pushblk[glob+0] x1
      1156  72 01 00 00       pushblk[glob+0] x1
      115A  79 1d             idxadd 29
      115C  7a 01             pushblk.heap x1
      115E  78 02 ce 10       call   L32FE locals=2
      1162  72 01 00 00       pushblk[glob+0] x1
      1166  42 01 07 00 00 00 push   #7
      116C  0b 4b             NATIVE t0 #0x4b
      116E  00 04             pop
      1170  72 01 00 00       pushblk[glob+0] x1
      1174  42 01 08 00 00 00 push   #8
      117A  0b 4b             NATIVE t0 #0x4b
      117C  00 04             pop
      117E  72 01 00 00       pushblk[glob+0] x1
      1182  42 01 f0 00 00 00 push   #240
      1188  52 01 00 00 00 41 push   #8f
      118E  52 01 00 00 00 00 push   #0f
      1194  0b 0d             NATIVE t0 #0x0d
      1196  12 0d 00 00 70 42 push   #60f
      119C  18 02 b1 16       call   L3F02 locals=2
      11A0  72 01 00 00       pushblk[glob+0] x1
      11A4  42 01 27 00 00 00 push   #39
      11AA  0b a8             NATIVE t0 #0xa8
      11AC  12 a8 00 00 dc 42 push   #110f
      11B2  18 02 a6 16       call   L3F02 locals=2
      11B6  18 02 18 12       call   L35EA locals=2
      11BA  72 01 00 00       pushblk[glob+0] x1
      11BE  78 02 81 10       call   L32C4 locals=2
      11C2  72 01 00 00       pushblk[glob+0] x1
      11C6  42 01 40 00 00 00 push   #64
      11CC  48 02 75 11       call   L34BA locals=2
      11D0  72 01 00 00       pushblk[glob+0] x1
      11D4  42 01 00 00 00 00 push   #0
      11DA  52 01 00 00 00 41 push   #8f
      11E0  52 01 00 00 00 00 push   #0f
      11E6  0b 0d             NATIVE t0 #0x0d
      11E8  00 03             tailcall
L11EA: 11EA  08 02 38 16       call   L3E5E locals=2
      11EE  05 02 3a 00       bz     L1266
      11F2  08 02 31 0e       call   L2E58 locals=2
      11F6  72 01 00 00       pushblk[glob+0] x1
      11FA  42 01 f1 00 00 00 push   #241
      1200  52 01 00 00 00 41 push   #8f
      1206  52 01 00 00 00 00 push   #0f
      120C  0b 0d             NATIVE t0 #0x0d
      120E  08 02 81 0a       call   L2714 locals=2
      1212  12 02 00 00 f0 41 push   #30f
      1218  18 02 b4 0d       call   L2D84 locals=2
      121C  72 01 00 00       pushblk[glob+0] x1
      1220  42 01 2c 00 00 00 push   #44
      1226  0b a8             NATIVE t0 #0xa8
      1228  08 02 d6 0d       call   L2DD8 locals=2
      122C  72 01 00 00       pushblk[glob+0] x1
      1230  42 01 00 00 00 00 push   #0
      1236  52 01 00 00 00 41 push   #8f
      123C  52 01 00 00 00 00 push   #0f
      1242  0b 0d             NATIVE t0 #0x0d
      1244  72 01 18 00       pushblk[glob+24] x1
      1248  42 01 01 00 00 00 push   #1
      124E  41 01             sub.i
      1250  47 03             cmp.nez.i
      1252  45 03 06 00       bz     L1262
      1256  48 02 07 00       call   L1268 locals=2
      125A  48 02 05 00       call   L1268 locals=2
      125E  44 02 00 00       jmp    L1262
L1262: 1262  44 02 00 00       jmp    L1266
L1266: 1266  40 03             tailcall
L1268: 1268  48 02 f9 15       call   L3E5E locals=2
      126C  45 02 17 00       bz     L129E
      1270  48 02 f2 0d       call   L2E58 locals=2
      1274  72 01 00 00       pushblk[glob+0] x1
      1278  42 01 00 00 00 00 push   #0
      127E  52 01 00 00 00 41 push   #8f
      1284  0b 0c             NATIVE t0 #0x0c
      1286  12 0c 00 00 00 00 push   #0f
      128C  12 0c 00 00 f0 41 push   #30f
      1292  18 02 f3 0e       call   L307C locals=2
      1296  18 02 34 16       call   L3F02 locals=2
      129A  14 02 00 00       jmp    L129E
L129E: 129E  10 03             tailcall
L12A0: 12A0  02 03 03 00 00 00 push   #3
      12A6  03 03 00 00       store  [loc+0]
      12AA  08 02 d8 15       call   L3E5E locals=2
      12AE  05 02 1c 00       bz     L12EA
      12B2  08 02 f1 01       call   L1698 locals=2
L12B6: 12B6  32 01 00 00       pushblk[loc+0] x1
      12BA  02 01 00 00 00 00 push   #0
      12C0  01 01             sub.i
      12C2  07 05             cmp.gtz.i
      12C4  05 05 0d 00       bz     L12E2
      12C8  08 02 48 01       call   L155C locals=2
      12CC  22 00 00 00       push   [loc+0]
      12D0  20 0c             dup
      12D2  2a 01             pushblk.heap x1
      12D4  02 01 01 00 00 00 push   #1
      12DA  01 01             sub.i
      12DC  00 07             blkcopy
      12DE  04 07 ea ff       jmp    L12B6
L12E2: 12E2  08 02 03 00       call   L12EC locals=2
      12E6  04 02 00 00       jmp    L12EA
L12EA: 12EA  00 03             tailcall
L12EC: 12EC  72 01 00 00       pushblk[glob+0] x1
      12F0  79 08             idxadd 8
      12F2  79 03             idxadd 3
      12F4  52 03 00 00 00 00 push   #0f
      12FA  50 07             blkcopy
      12FC  72 01 00 00       pushblk[glob+0] x1
      1300  0b 16             GetActor()
      1302  e2 00 dc f1       push   [imm+-3620]
      1306  0b 17             MakeAttack()
      1308  00 04             pop
      130A  72 01 00 00       pushblk[glob+0] x1
      130E  0b 16             GetActor()
      1310  e2 00 3e f2       push   [imm+-3522]
      1314  0b 17             MakeAttack()
      1316  00 04             pop
      1318  72 01 00 00       pushblk[glob+0] x1
      131C  42 01 d2 00 00 00 push   #210
      1322  52 01 00 00 00 00 push   #0f
      1328  52 01 00 00 00 00 push   #0f
      132E  0b 0d             NATIVE t0 #0x0d
      1330  72 01 00 00       pushblk[glob+0] x1
      1334  42 01 1b 00 00 00 push   #27
      133A  0b a8             NATIVE t0 #0xa8
      133C  12 a8 00 00 48 42 push   #50f
      1342  13 a8 10 00       store  [loc+16]
L1346: 1346  32 01 10 00       pushblk[loc+16] x1
      134A  12 01 00 00 00 00 push   #0f
      1350  11 01             sub.f
      1352  17 04             cmp.gez.f
      1354  15 04 0c 00       bz     L1370
      1358  22 00 10 00       push   [loc+16]
      135C  20 0c             dup
      135E  2a 01             pushblk.heap x1
      1360  0b 05             NATIVE t0 #0x05
      1362  11 01             sub.f
      1364  10 07             blkcopy
      1366  18 06 04 02       call   L1772 locals=6
      136A  10 00             end
      136C  14 00 eb ff       jmp    L1346
L1370: 1370  18 06 6c 11       call   L364C locals=6
L1374: 1374  72 01 00 00       pushblk[glob+0] x1
      1378  0b ac             NATIVE t0 #0xac
      137A  00 0d             lnot
      137C  05 0d 05 00       bz     L138A
      1380  08 06 f7 01       call   L1772 locals=6
      1384  00 00             end   ; ---- routine end ----
      1386  04 00 f5 ff       jmp    L1374
L138A: 138A  72 01 00 00       pushblk[glob+0] x1
      138E  42 01 2d 00 00 00 push   #45
      1394  0b 4b             NATIVE t0 #0x4b
      1396  00 04             pop
      1398  72 01 00 00       pushblk[glob+0] x1
      139C  72 01 00 00       pushblk[glob+0] x1
      13A0  79 1d             idxadd 29
      13A2  7a 01             pushblk.heap x1
      13A4  78 06 ab 0f       call   L32FE locals=6
      13A8  72 01 00 00       pushblk[glob+0] x1
      13AC  42 01 03 00 00 00 push   #3
      13B2  72 01 00 00       pushblk[glob+0] x1
      13B6  79 1d             idxadd 29
      13B8  7a 01             pushblk.heap x1
      13BA  e2 00 74 f2       push   [imm+-3468]
      13BE  c2 00 00 00 00 00 push   #0
      13C4  0b 5e             NATIVE t0 #0x5e
      13C6  00 04             pop
      13C8  72 01 00 00       pushblk[glob+0] x1
      13CC  0b 16             GetActor()
      13CE  e2 00 f0 f1       push   [imm+-3600]
      13D2  0b 17             MakeAttack()
      13D4  00 04             pop
      13D6  72 01 00 00       pushblk[glob+0] x1
      13DA  42 01 11 00 00 00 push   #17
      13E0  0b a8             NATIVE t0 #0xa8
      13E2  08 06 39 11       call   L3658 locals=6
      13E6  72 01 00 00       pushblk[glob+0] x1
      13EA  42 01 d3 00 00 00 push   #211
      13F0  52 01 00 00 00 00 push   #0f
      13F6  52 01 00 00 00 00 push   #0f
      13FC  0b 0d             NATIVE t0 #0x0d
      13FE  72 01 00 00       pushblk[glob+0] x1
      1402  79 1b             idxadd 27
      1404  7a 01             pushblk.heap x1
      1406  79 05             idxadd 5
      1408  52 05 66 66 66 3f push   #0.9f
      140E  50 07             blkcopy
L1410: 1410  72 01 00 00       pushblk[glob+0] x1
      1414  0b ac             NATIVE t0 #0xac
      1416  00 0d             lnot
      1418  05 0d 6b 00       bz     L14F2
      141C  72 01 00 00       pushblk[glob+0] x1
      1420  0b 59             NATIVE t0 #0x59
      1422  12 59 00 00 20 41 push   #10f
      1428  11 01             sub.f
      142A  17 01             cmp.lez.f
      142C  15 01 10 00       bz     L1450
      1430  72 01 00 00       pushblk[glob+0] x1
      1434  79 08             idxadd 8
      1436  79 03             idxadd 3
      1438  52 03 00 00 00 00 push   #0f
      143E  50 07             blkcopy
      1440  72 01 00 00       pushblk[glob+0] x1
      1444  42 01 00 00 00 00 push   #0
      144A  0b 58             NATIVE t0 #0x58
      144C  04 58 4e 00       jmp    L14EC
L1450: 1450  72 01 00 00       pushblk[glob+0] x1
      1454  79 1d             idxadd 29
      1456  7a 01             pushblk.heap x1
      1458  79 04             idxadd 4
      145A  7a 04             pushblk.heap x4
      145C  33 04 00 00       store  [loc+0]
      1460  22 00 00 00       push   [loc+0]
      1464  29 01             idxadd 1
      1466  12 01 00 00 a0 c1 push   #-20f
      146C  10 07             blkcopy
      146E  22 00 00 00       push   [loc+0]
      1472  72 01 00 00       pushblk[glob+0] x1
      1476  79 04             idxadd 4
      1478  0b 08             VecSub()
      147A  72 01 00 00       pushblk[glob+0] x1
      147E  22 00 00 00       push   [loc+0]
      1482  0b 0b             NATIVE t0 #0x0b
      1484  22 00 00 00       push   [loc+0]
      1488  0b 09             NATIVE t0 #0x09
      148A  72 01 00 00       pushblk[glob+0] x1
      148E  79 08             idxadd 8
      1490  22 00 00 00       push   [loc+0]
      1494  2a 04             pushblk.heap x4
      1496  20 07             blkcopy
      1498  72 01 00 00       pushblk[glob+0] x1
      149C  79 08             idxadd 8
      149E  79 01             idxadd 1
      14A0  70 0c             dup
      14A2  7a 01             pushblk.heap x1
      14A4  52 01 00 00 80 40 push   #4f
      14AA  51 02             mul.f
      14AC  50 07             blkcopy
      14AE  72 01 00 00       pushblk[glob+0] x1
      14B2  79 08             idxadd 8
      14B4  70 0c             dup
      14B6  7a 01             pushblk.heap x1
      14B8  52 01 00 00 80 40 push   #4f
      14BE  51 02             mul.f
      14C0  50 07             blkcopy
      14C2  72 01 00 00       pushblk[glob+0] x1
      14C6  79 08             idxadd 8
      14C8  79 02             idxadd 2
      14CA  70 0c             dup
      14CC  7a 01             pushblk.heap x1
      14CE  52 01 00 00 80 40 push   #4f
      14D4  51 02             mul.f
      14D6  50 07             blkcopy
      14D8  72 01 00 00       pushblk[glob+0] x1
      14DC  79 08             idxadd 8
      14DE  79 03             idxadd 3
      14E0  52 03 00 00 70 41 push   #15f
      14E6  50 07             blkcopy
      14E8  54 07 00 00       jmp    L14EC
L14EC: 14EC  50 00             end
      14EE  54 00 8f ff       jmp    L1410
L14F2: 14F2  72 01 00 00       pushblk[glob+0] x1
      14F6  42 01 2d 00 00 00 push   #45
      14FC  0b 4b             NATIVE t0 #0x4b
      14FE  00 04             pop
      1500  72 01 00 00       pushblk[glob+0] x1
      1504  42 01 00 00 00 00 push   #0
      150A  0b 58             NATIVE t0 #0x58
      150C  08 06 9e 10       call   L364C locals=6
      1510  72 01 00 00       pushblk[glob+0] x1
      1514  42 01 40 00 00 00 push   #64
      151A  48 06 ce 0f       call   L34BA locals=6
      151E  48 06 15 09       call   L274C locals=6
      1522  72 01 00 00       pushblk[glob+0] x1
      1526  42 01 d4 00 00 00 push   #212
      152C  52 01 00 00 00 00 push   #0f
      1532  52 01 00 00 00 00 push   #0f
      1538  0b 0d             NATIVE t0 #0x0d
      153A  72 01 00 00       pushblk[glob+0] x1
      153E  78 06 c1 0e       call   L32C4 locals=6
      1542  72 01 00 00       pushblk[glob+0] x1
      1546  42 01 00 00 00 00 push   #0
      154C  52 01 00 00 00 41 push   #8f
      1552  52 01 00 00 00 00 push   #0f
      1558  0b 0d             NATIVE t0 #0x0d
      155A  00 03             tailcall
L155C: 155C  08 06 65 01       call   L182A locals=6
      1560  02 06 ce 00 00 00 push   #206
      1566  03 06 08 00       store  [loc+8]
L156A: 156A  32 01 08 00       pushblk[loc+8] x1
      156E  02 01 d1 00 00 00 push   #209
      1574  01 01             sub.i
      1576  07 01             cmp.lez.i
      1578  05 01 8d 00       bz     L1696
      157C  0b 19             NATIVE t0 #0x19
      157E  03 19 0c 00       store  [loc+12]
      1582  32 01 0c 00       pushblk[loc+12] x1
      1586  12 01 cd cc cc 3e push   #0.4f
      158C  11 01             sub.f
      158E  17 00             cmp.ltz.f
      1590  15 00 07 00       bz     L15A2
      1594  02 00 03 00 00 00 push   #3
      159A  03 00 04 00       store  [loc+4]
      159E  04 00 17 00       jmp    L15D0
L15A2: 15A2  32 01 0c 00       pushblk[loc+12] x1
      15A6  12 01 33 33 33 3f push   #0.7f
      15AC  11 01             sub.f
      15AE  17 00             cmp.ltz.f
      15B0  15 00 07 00       bz     L15C2
      15B4  02 00 06 00 00 00 push   #6
      15BA  03 00 04 00       store  [loc+4]
      15BE  04 00 07 00       jmp    L15D0
L15C2: 15C2  02 00 07 00 00 00 push   #7
      15C8  03 00 04 00       store  [loc+4]
      15CC  04 00 00 00       jmp    L15D0
L15D0: 15D0  72 01 00 00       pushblk[glob+0] x1
      15D4  32 01 04 00       pushblk[loc+4] x1
      15D8  0b a8             NATIVE t0 #0xa8
      15DA  32 01 08 00       pushblk[loc+8] x1
      15DE  02 01 ce 00 00 00 push   #206
      15E4  01 01             sub.i
      15E6  07 02             cmp.eqz.i
      15E8  05 02 06 00       bz     L15F8
      15EC  e2 00 32 ed       push   [imm+-4814]
      15F0  23 00 00 00       store  [loc+0]
      15F4  24 00 24 00       jmp    L1640
L15F8: 15F8  32 01 08 00       pushblk[loc+8] x1
      15FC  02 01 cf 00 00 00 push   #207
      1602  01 01             sub.i
      1604  07 02             cmp.eqz.i
      1606  05 02 06 00       bz     L1616
      160A  e2 00 84 ed       push   [imm+-4732]
      160E  23 00 00 00       store  [loc+0]
      1612  24 00 15 00       jmp    L1640
L1616: 1616  32 01 08 00       pushblk[loc+8] x1
      161A  02 01 d0 00 00 00 push   #208
      1620  01 01             sub.i
      1622  07 02             cmp.eqz.i
      1624  05 02 06 00       bz     L1634
      1628  e2 00 d6 ed       push   [imm+-4650]
      162C  23 00 00 00       store  [loc+0]
      1630  24 00 06 00       jmp    L1640
L1634: 1634  e2 00 3a ee       push   [imm+-4550]
      1638  23 00 00 00       store  [loc+0]
      163C  24 00 00 00       jmp    L1640
L1640: 1640  72 01 00 00       pushblk[glob+0] x1
      1644  0b 16             GetActor()
      1646  32 01 00 00       pushblk[loc+0] x1
      164A  0b 17             MakeAttack()
      164C  00 04             pop
      164E  72 01 00 00       pushblk[glob+0] x1
      1652  32 01 08 00       pushblk[loc+8] x1
      1656  12 01 00 00 00 00 push   #0f
      165C  0b 0c             NATIVE t0 #0x0c
L165E: 165E  72 01 00 00       pushblk[glob+0] x1
      1662  0b ac             NATIVE t0 #0xac
      1664  00 0d             lnot
      1666  05 0d 05 00       bz     L1674
      166A  08 06 82 00       call   L1772 locals=6
      166E  00 00             end   ; ---- routine end ----
      1670  04 00 f5 ff       jmp    L165E
L1674: 1674  32 01 08 00       pushblk[loc+8] x1
      1678  02 01 01 00 00 00 push   #1
      167E  01 00             add.i
      1680  03 00 08 00       store  [loc+8]
      1684  72 01 00 00       pushblk[glob+0] x1
      1688  42 01 2d 00 00 00 push   #45
      168E  0b 4b             NATIVE t0 #0x4b
      1690  00 04             pop
      1692  04 04 6a ff       jmp    L156A
L1696: 1696  00 03             tailcall
L1698: 1698  0b 19             NATIVE t0 #0x19
      169A  03 19 10 00       store  [loc+16]
      169E  32 01 10 00       pushblk[loc+16] x1
      16A2  12 01 cd cc cc 3e push   #0.4f
      16A8  11 01             sub.f
      16AA  17 00             cmp.ltz.f
      16AC  15 00 07 00       bz     L16BE
      16B0  02 00 1f 00 00 00 push   #31
      16B6  03 00 14 00       store  [loc+20]
      16BA  04 00 07 00       jmp    L16CC
L16BE: 16BE  02 00 20 00 00 00 push   #32
      16C4  03 00 14 00       store  [loc+20]
      16C8  04 00 00 00       jmp    L16CC
L16CC: 16CC  08 06 c4 0b       call   L2E58 locals=6
      16D0  72 01 00 00       pushblk[glob+0] x1
      16D4  32 01 14 00       pushblk[loc+20] x1
      16D8  0b a8             NATIVE t0 #0xa8
      16DA  08 06 3d 08       call   L2758 locals=6
      16DE  72 01 00 00       pushblk[glob+0] x1
      16E2  42 01 40 00 00 00 push   #64
      16E8  48 06 f5 0e       call   L34D6 locals=6
      16EC  72 01 00 00       pushblk[glob+0] x1
      16F0  79 1b             idxadd 27
      16F2  7a 01             pushblk.heap x1
      16F4  79 05             idxadd 5
      16F6  52 05 cd cc cc 3d push   #0.1f
      16FC  50 07             blkcopy
      16FE  72 01 00 00       pushblk[glob+0] x1
      1702  22 00 00 00       push   [loc+0]
      1706  12 00 00 00 00 00 push   #0f
      170C  12 00 00 00 00 00 push   #0f
      1712  12 00 00 00 00 00 push   #0f
      1718  12 00 00 00 80 3f push   #1f
      171E  18 06 98 11       call   L3A52 locals=6
      1722  0b a9             NATIVE t0 #0xa9
      1724  72 01 00 00       pushblk[glob+0] x1
      1728  72 01 00 00       pushblk[glob+0] x1
      172C  79 1d             idxadd 29
      172E  7a 01             pushblk.heap x1
      1730  78 06 e5 0d       call   L32FE locals=6
      1734  72 01 00 00       pushblk[glob+0] x1
      1738  42 01 cd 00 00 00 push   #205
      173E  52 01 00 00 00 41 push   #8f
      1744  52 01 00 00 00 00 push   #0f
      174A  0b 0d             NATIVE t0 #0x0d
      174C  72 01 00 00       pushblk[glob+0] x1
      1750  78 06 b8 0d       call   L32C4 locals=6
      1754  78 06 80 0f       call   L3658 locals=6
      1758  72 01 00 00       pushblk[glob+0] x1
      175C  42 01 ce 00 00 00 push   #206
      1762  52 01 00 00 00 00 push   #0f
      1768  52 01 00 00 00 00 push   #0f
      176E  0b 0d             NATIVE t0 #0x0d
      1770  00 03             tailcall
L1772: 1772  72 01 00 00       pushblk[glob+0] x1
      1776  72 01 00 00       pushblk[glob+0] x1
      177A  79 1d             idxadd 29
      177C  7a 01             pushblk.heap x1
      177E  78 0a be 0d       call   L32FE locals=10
      1782  72 01 00 00       pushblk[glob+0] x1
      1786  79 1d             idxadd 29
      1788  7a 01             pushblk.heap x1
      178A  79 04             idxadd 4
      178C  7a 04             pushblk.heap x4
      178E  33 04 00 00       store  [loc+0]
      1792  22 00 00 00       push   [loc+0]
      1796  29 01             idxadd 1
      1798  20 0c             dup
      179A  2a 01             pushblk.heap x1
      179C  12 01 00 00 f0 41 push   #30f
      17A2  11 01             sub.f
      17A4  10 07             blkcopy
      17A6  22 00 00 00       push   [loc+0]
      17AA  2a 04             pushblk.heap x4
      17AC  23 04 10 00       store  [loc+16]
      17B0  22 00 10 00       push   [loc+16]
      17B4  72 01 00 00       pushblk[glob+0] x1
      17B8  79 04             idxadd 4
      17BA  0b 08             VecSub()
      17BC  22 00 10 00       push   [loc+16]
      17C0  0b 09             NATIVE t0 #0x09
      17C2  22 00 10 00       push   [loc+16]
      17C6  29 03             idxadd 3
      17C8  12 03 00 00 00 41 push   #8f
      17CE  10 07             blkcopy
      17D0  72 01 00 00       pushblk[glob+0] x1
      17D4  79 08             idxadd 8
      17D6  22 00 10 00       push   [loc+16]
      17DA  2a 04             pushblk.heap x4
      17DC  20 07             blkcopy
      17DE  28 0a 2e 0b       call   L2E3E locals=10
      17E2  12 0a 00 00 a5 43 push   #330f
      17E8  11 01             sub.f
      17EA  17 00             cmp.ltz.f
      17EC  15 00 1c 00       bz     L1828
      17F0  72 01 00 00       pushblk[glob+0] x1
      17F4  79 08             idxadd 8
      17F6  79 01             idxadd 1
      17F8  70 0c             dup
      17FA  7a 01             pushblk.heap x1
      17FC  52 01 00 00 00 3f push   #0.5f
      1802  51 02             mul.f
      1804  50 07             blkcopy
      1806  72 01 00 00       pushblk[glob+0] x1
      180A  79 08             idxadd 8
      180C  52 08 00 00 00 00 push   #0f
      1812  50 07             blkcopy
      1814  72 01 00 00       pushblk[glob+0] x1
      1818  79 08             idxadd 8
      181A  79 02             idxadd 2
      181C  52 02 00 00 00 00 push   #0f
      1822  50 07             blkcopy
      1824  54 07 00 00       jmp    L1828
L1828: 1828  50 03             tailcall
L182A: 182A  72 01 00 00       pushblk[glob+0] x1
      182E  79 1d             idxadd 29
      1830  7a 01             pushblk.heap x1
      1832  79 04             idxadd 4
      1834  7a 04             pushblk.heap x4
      1836  33 04 20 00       store  [loc+32]
      183A  22 00 20 00       push   [loc+32]
      183E  72 01 00 00       pushblk[glob+0] x1
      1842  79 04             idxadd 4
      1844  0b 08             VecSub()
      1846  22 00 20 00       push   [loc+32]
      184A  0b 09             NATIVE t0 #0x09
      184C  22 00 20 00       push   [loc+32]
      1850  12 00 00 00 96 43 push   #300f
      1856  0b 5d             NATIVE t0 #0x5d
      1858  22 00 20 00       push   [loc+32]
      185C  72 01 00 00       pushblk[glob+0] x1
      1860  79 1d             idxadd 29
      1862  7a 01             pushblk.heap x1
      1864  79 04             idxadd 4
      1866  0b 07             VecAdd()
      1868  72 01 00 00       pushblk[glob+0] x1
      186C  79 1b             idxadd 27
      186E  7a 01             pushblk.heap x1
      1870  79 05             idxadd 5
      1872  52 05 00 00 80 3f push   #1f
      1878  50 07             blkcopy
      187A  52 07 00 00 20 41 push   #10f
      1880  13 07 00 00       store  [loc+0]
L1884: 1884  32 01 00 00       pushblk[loc+0] x1
      1888  12 01 00 00 00 00 push   #0f
      188E  11 01             sub.f
      1890  17 05             cmp.gtz.f
      1892  15 05 41 00       bz     L1918
      1896  22 00 20 00       push   [loc+32]
      189A  2a 04             pushblk.heap x4
      189C  23 04 10 00       store  [loc+16]
      18A0  22 00 10 00       push   [loc+16]
      18A4  72 01 00 00       pushblk[glob+0] x1
      18A8  79 04             idxadd 4
      18AA  0b 08             VecSub()
      18AC  72 01 00 00       pushblk[glob+0] x1
      18B0  22 00 10 00       push   [loc+16]
      18B4  0b 24             NATIVE t0 #0x24
      18B6  22 00 10 00       push   [loc+16]
      18BA  0b 09             NATIVE t0 #0x09
      18BC  22 00 10 00       push   [loc+16]
      18C0  29 03             idxadd 3
      18C2  12 03 00 00 48 42 push   #50f
      18C8  10 07             blkcopy
      18CA  72 01 00 00       pushblk[glob+0] x1
      18CE  79 08             idxadd 8
      18D0  22 00 10 00       push   [loc+16]
      18D4  2a 04             pushblk.heap x4
      18D6  20 07             blkcopy
      18D8  22 00 00 00       push   [loc+0]
      18DC  20 0c             dup
      18DE  2a 01             pushblk.heap x1
      18E0  0b 05             NATIVE t0 #0x05
      18E2  11 01             sub.f
      18E4  10 07             blkcopy
      18E6  10 00             end
      18E8  22 00 10 00       push   [loc+16]
      18EC  0b 06             NATIVE t0 #0x06
      18EE  12 06 00 00 96 43 push   #300f
      18F4  11 01             sub.f
      18F6  17 00             cmp.ltz.f
      18F8  15 00 0c 00       bz     L1914
      18FC  72 01 00 00       pushblk[glob+0] x1
      1900  79 08             idxadd 8
      1902  79 03             idxadd 3
      1904  52 03 00 00 00 00 push   #0f
      190A  50 07             blkcopy
      190C  54 07 04 00       jmp    L1918
      1910  54 07 00 00       jmp    L1914
L1914: 1914  54 07 b6 ff       jmp    L1884
L1918: 1918  72 01 00 00       pushblk[glob+0] x1
      191C  79 1b             idxadd 27
      191E  7a 01             pushblk.heap x1
      1920  79 05             idxadd 5
      1922  52 05 cd cc cc 3d push   #0.1f
      1928  50 07             blkcopy
      192A  50 03             tailcall
L192C: 192C  52 03 00 00 82 42 push   #65f
      1932  52 03 00 00 00 00 push   #0f
      1938  52 03 00 00 96 43 push   #300f
      193E  52 03 00 00 70 42 push   #60f
      1944  42 03 01 00 00 00 push   #1
      194A  48 02 18 00       call   L197E locals=2
      194E  40 03             tailcall
L1950: 1950  52 03 00 00 48 42 push   #50f
      1956  52 03 00 00 a0 c1 push   #-20f
      195C  52 03 00 00 a0 41 push   #20f
      1962  58 02 8b 0b       call   L307C locals=2
      1966  52 02 00 00 20 42 push   #40f
      196C  52 02 00 00 c8 41 push   #25f
      1972  42 02 00 00 00 00 push   #0
      1978  48 02 01 00       call   L197E locals=2
      197C  40 03             tailcall
L197E: 197E  03 03 00 00       store  [loc+0]
      1982  03 03 04 00       store  [loc+4]
      1986  03 03 08 00       store  [loc+8]
      198A  03 03 0c 00       store  [loc+12]
      198E  03 03 10 00       store  [loc+16]
      1992  08 0e 64 12       call   L3E5E locals=14
      1996  05 0e 61 00       bz     L1A5C
      199A  08 0e 5d 0a       call   L2E58 locals=14
      199E  72 01 00 00       pushblk[glob+0] x1
      19A2  72 01 00 00       pushblk[glob+0] x1
      19A6  79 1d             idxadd 29
      19A8  7a 01             pushblk.heap x1
      19AA  78 0e bd 0c       call   L3328 locals=14
      19AE  72 01 00 00       pushblk[glob+0] x1
      19B2  79 0c             idxadd 12
      19B4  7a 04             pushblk.heap x4
      19B6  33 04 20 00       store  [loc+32]
      19BA  22 00 20 00       push   [loc+32]
      19BE  32 01 10 00       pushblk[loc+16] x1
      19C2  0b 5d             NATIVE t0 #0x5d
      19C4  22 00 20 00       push   [loc+32]
      19C8  32 01 0c 00       pushblk[loc+12] x1
      19CC  0b 0a             RotateDeg()
      19CE  22 00 20 00       push   [loc+32]
      19D2  29 01             idxadd 1
      19D4  32 01 08 00       pushblk[loc+8] x1
      19D8  30 07             blkcopy
      19DA  72 01 00 00       pushblk[glob+0] x1
      19DE  42 01 03 00 00 00 push   #3
      19E4  52 01 00 00 00 00 push   #0f
      19EA  52 01 00 00 00 00 push   #0f
      19F0  0b 0d             NATIVE t0 #0x0d
      19F2  72 01 00 00       pushblk[glob+0] x1
      19F6  78 0e 65 0c       call   L32C4 locals=14
      19FA  72 01 00 00       pushblk[glob+0] x1
      19FE  32 01 00 00       pushblk[loc+0] x1
      1A02  0b a8             NATIVE t0 #0xa8
      1A04  72 01 00 00       pushblk[glob+0] x1
      1A08  42 01 04 00 00 00 push   #4
      1A0E  52 01 00 00 00 00 push   #0f
      1A14  52 01 00 00 00 00 push   #0f
      1A1A  0b 0d             NATIVE t0 #0x0d
      1A1C  72 01 00 00       pushblk[glob+0] x1
      1A20  22 00 20 00       push   [loc+32]
      1A24  12 00 66 66 66 3f push   #0.9f
      1A2A  32 01 04 00       pushblk[loc+4] x1
      1A2E  0b 52             NATIVE t0 #0x52
      1A30  72 01 00 00       pushblk[glob+0] x1
      1A34  42 01 03 00 00 00 push   #3
      1A3A  0b 53             NATIVE t0 #0x53
L1A3C: 1A3C  72 01 00 00       pushblk[glob+0] x1
      1A40  79 1c             idxadd 28
      1A42  7a 01             pushblk.heap x1
      1A44  42 01 00 00 00 00 push   #0
      1A4A  41 01             sub.i
      1A4C  47 03             cmp.nez.i
      1A4E  45 03 03 00       bz     L1A58
      1A52  40 00             end
      1A54  44 00 f2 ff       jmp    L1A3C
L1A58: 1A58  44 00 00 00       jmp    L1A5C
L1A5C: 1A5C  40 03             tailcall
L1A5E: 1A5E  52 03 00 00 34 42 push   #45f
      1A64  52 03 00 00 f0 42 push   #120f
      1A6A  58 0e 07 0b       call   L307C locals=14
      1A6E  13 0e 20 00       store  [loc+32]
      1A72  12 0e 00 00 b4 42 push   #90f
      1A78  13 0e 24 00       store  [loc+36]
      1A7C  12 0e 33 33 f3 3f push   #1.9f
      1A82  13 0e 28 00       store  [loc+40]
      1A86  18 0e ea 11       call   L3E5E locals=14
      1A8A  15 0e 95 00       bz     L1BB8
      1A8E  18 0e e3 09       call   L2E58 locals=14
      1A92  18 0e 09 06       call   L26A8 locals=14
      1A96  0b 19             NATIVE t0 #0x19
      1A98  03 19 2c 00       store  [loc+44]
      1A9C  32 01 2c 00       pushblk[loc+44] x1
      1AA0  12 01 00 00 00 3f push   #0.5f
      1AA6  11 01             sub.f
      1AA8  17 00             cmp.ltz.f
      1AAA  15 00 10 00       bz     L1ACE
      1AAE  22 00 24 00       push   [loc+36]
      1AB2  20 0c             dup
      1AB4  2a 01             pushblk.heap x1
      1AB6  12 01 00 00 80 bf push   #-1f
      1ABC  11 02             mul.f
      1ABE  10 07             blkcopy
      1AC0  02 07 dc 00 00 00 push   #220
      1AC6  03 07 00 00       store  [loc+0]
      1ACA  04 07 10 00       jmp    L1AEE
L1ACE: 1ACE  22 00 28 00       push   [loc+40]
      1AD2  20 0c             dup
      1AD4  2a 01             pushblk.heap x1
      1AD6  12 01 00 00 80 bf push   #-1f
      1ADC  11 02             mul.f
      1ADE  10 07             blkcopy
      1AE0  02 07 dd 00 00 00 push   #221
      1AE6  03 07 00 00       store  [loc+0]
      1AEA  04 07 00 00       jmp    L1AEE
L1AEE: 1AEE  72 01 00 00       pushblk[glob+0] x1
      1AF2  72 01 00 00       pushblk[glob+0] x1
      1AF6  79 1d             idxadd 29
      1AF8  7a 01             pushblk.heap x1
      1AFA  78 0e 15 0c       call   L3328 locals=14
      1AFE  72 01 00 00       pushblk[glob+0] x1
      1B02  79 0c             idxadd 12
      1B04  7a 04             pushblk.heap x4
      1B06  33 04 10 00       store  [loc+16]
      1B0A  22 00 10 00       push   [loc+16]
      1B0E  32 01 24 00       pushblk[loc+36] x1
      1B12  0b 0a             RotateDeg()
L1B14: 1B14  32 01 20 00       pushblk[loc+32] x1
      1B18  12 01 00 00 00 00 push   #0f
      1B1E  11 01             sub.f
      1B20  17 05             cmp.gtz.f
      1B22  15 05 45 00       bz     L1BB0
      1B26  72 01 00 00       pushblk[glob+0] x1
      1B2A  32 01 00 00       pushblk[loc+0] x1
      1B2E  12 01 00 00 00 41 push   #8f
      1B34  0b 0c             NATIVE t0 #0x0c
      1B36  22 00 10 00       push   [loc+16]
      1B3A  32 01 28 00       pushblk[loc+40] x1
      1B3E  0b 05             NATIVE t0 #0x05
      1B40  11 02             mul.f
      1B42  0b 0a             RotateDeg()
      1B44  72 01 00 00       pushblk[glob+0] x1
      1B48  22 00 10 00       push   [loc+16]
      1B4C  0b 0b             NATIVE t0 #0x0b
      1B4E  72 01 00 00       pushblk[glob+0] x1
      1B52  79 08             idxadd 8
      1B54  22 00 10 00       push   [loc+16]
      1B58  2a 04             pushblk.heap x4
      1B5A  20 07             blkcopy
      1B5C  72 01 00 00       pushblk[glob+0] x1
      1B60  79 08             idxadd 8
      1B62  79 03             idxadd 3
      1B64  52 03 00 00 70 41 push   #15f
      1B6A  50 07             blkcopy
      1B6C  22 00 20 00       push   [loc+32]
      1B70  20 0c             dup
      1B72  2a 01             pushblk.heap x1
      1B74  0b 05             NATIVE t0 #0x05
      1B76  11 01             sub.f
      1B78  10 07             blkcopy
      1B7A  10 00             end
      1B7C  18 0e 5f 09       call   L2E3E locals=14
      1B80  12 0e 00 00 96 43 push   #300f
      1B86  11 01             sub.f
      1B88  17 00             cmp.ltz.f
      1B8A  10 0c             dup
      1B8C  15 0c 08 00       bz     L1BA0
      1B90  32 01 20 00       pushblk[loc+32] x1
      1B94  12 01 00 00 f0 41 push   #30f
      1B9A  11 01             sub.f
      1B9C  17 00             cmp.ltz.f
      1B9E  01 0a             land.i
L1BA0: 1BA0  05 0a 04 00       bz     L1BAC
      1BA4  04 0a 04 00       jmp    L1BB0
      1BA8  04 0a 00 00       jmp    L1BAC
L1BAC: 1BAC  04 0a b2 ff       jmp    L1B14
L1BB0: 1BB0  08 0e 5a 05       call   L2668 locals=14
      1BB4  04 0e 00 00       jmp    L1BB8
L1BB8: 1BB8  72 01 00 00       pushblk[glob+0] x1
      1BBC  72 01 00 00       pushblk[glob+0] x1
      1BC0  79 1d             idxadd 29
      1BC2  7a 01             pushblk.heap x1
      1BC4  78 0e 9b 0b       call   L32FE locals=14
      1BC8  70 03             tailcall
L1BCA: 1BCA  72 01 00 00       pushblk[glob+0] x1
      1BCE  79 1b             idxadd 27
      1BD0  7a 01             pushblk.heap x1
      1BD2  79 01             idxadd 1
      1BD4  52 01 00 00 80 40 push   #4f
      1BDA  50 07             blkcopy
      1BDC  72 01 00 00       pushblk[glob+0] x1
      1BE0  79 1b             idxadd 27
      1BE2  7a 01             pushblk.heap x1
      1BE4  79 02             idxadd 2
      1BE6  52 02 00 00 70 41 push   #15f
      1BEC  50 07             blkcopy
      1BEE  58 02 33 09       call   L2E58 locals=2
      1BF2  72 01 10 00       pushblk[glob+16] x1
      1BF6  42 01 00 00 00 00 push   #0
      1BFC  41 01             sub.i
      1BFE  47 02             cmp.eqz.i
      1C00  45 02 07 00       bz     L1C12
      1C04  42 02 00 00 01 00 push   #65536
      1C0A  03 02 00 00       store  [loc+0]
      1C0E  04 02 07 00       jmp    L1C20
L1C12: 1C12  02 02 01 00 01 00 push   #65537
      1C18  03 02 00 00       store  [loc+0]
      1C1C  04 02 00 00       jmp    L1C20
L1C20: 1C20  08 02 0d 09       call   L2E3E locals=2
      1C24  12 02 00 00 dc 43 push   #440f
      1C2A  11 01             sub.f
      1C2C  17 05             cmp.gtz.f
      1C2E  10 0c             dup
      1C30  15 0c 03 00       bz     L1C3A
      1C34  18 02 13 11       call   L3E5E locals=2
      1C38  01 0a             land.i
L1C3A: 1C3A  05 0a 16 00       bz     L1C6A
      1C3E  08 02 33 05       call   L26A8 locals=2
      1C42  72 01 00 00       pushblk[glob+0] x1
      1C46  32 01 00 00       pushblk[loc+0] x1
      1C4A  12 01 00 00 34 43 push   #180f
      1C50  12 01 00 00 00 00 push   #0f
      1C56  12 01 00 00 c8 43 push   #400f
      1C5C  18 02 88 0b       call   L3370 locals=2
      1C60  10 04             pop
      1C62  18 02 01 05       call   L2668 locals=2
      1C66  14 02 00 00       jmp    L1C6A
L1C6A: 1C6A  10 03             tailcall
L1C6C: 1C6C  13 03 00 00       store  [loc+0]
      1C70  18 02 f1 00       call   L1E56 locals=2
      1C74  32 01 00 00       pushblk[loc+0] x1
      1C78  38 02 43 11       call   L3F02 locals=2
      1C7C  12 02 00 00 16 43 push   #150f
      1C82  18 02 34 00       call   L1CEE locals=2
      1C86  10 03             tailcall
L1C88: 1C88  13 03 00 00       store  [loc+0]
      1C8C  18 02 e3 00       call   L1E56 locals=2
      1C90  32 01 00 00       pushblk[loc+0] x1
      1C94  38 02 35 11       call   L3F02 locals=2
      1C98  12 02 00 00 7a 44 push   #1000f
      1C9E  18 02 26 00       call   L1CEE locals=2
      1CA2  10 03             tailcall
      1CA4  72 01 00 00       pushblk[glob+0] x1
      1CA8  42 01 00 02 00 00 push   #512
      1CAE  48 06 12 0c       call   L34D6 locals=6
      1CB2  48 06 d0 00       call   L1E56 locals=6
      1CB6  22 00 00 00       push   [loc+0]
      1CBA  12 00 00 00 00 00 push   #0f
      1CC0  10 07             blkcopy
      1CC2  22 00 00 00       push   [loc+0]
      1CC6  29 01             idxadd 1
      1CC8  12 01 00 00 a0 c1 push   #-20f
      1CCE  10 07             blkcopy
      1CD0  22 00 00 00       push   [loc+0]
      1CD4  29 02             idxadd 2
      1CD6  12 02 00 00 00 00 push   #0f
      1CDC  10 07             blkcopy
      1CDE  72 01 00 00       pushblk[glob+0] x1
      1CE2  22 00 00 00       push   [loc+0]
      1CE6  0b 56             NATIVE t0 #0x56
      1CE8  08 06 7c 00       call   L1DE4 locals=6
      1CEC  00 03             tailcall
L1CEE: 1CEE  03 03 00 00       store  [loc+0]
      1CF2  72 01 00 00       pushblk[glob+0] x1
      1CF6  79 1d             idxadd 29
      1CF8  7a 01             pushblk.heap x1
      1CFA  79 04             idxadd 4
      1CFC  7a 04             pushblk.heap x4
      1CFE  33 04 10 00       store  [loc+16]
      1D02  22 00 10 00       push   [loc+16]
      1D06  29 01             idxadd 1
      1D08  12 01 00 00 a0 c1 push   #-20f
      1D0E  10 07             blkcopy
      1D10  22 00 10 00       push   [loc+16]
      1D14  72 01 00 00       pushblk[glob+0] x1
      1D18  79 04             idxadd 4
      1D1A  0b 08             VecSub()
      1D1C  22 00 10 00       push   [loc+16]
      1D20  0b 09             NATIVE t0 #0x09
      1D22  22 00 10 00       push   [loc+16]
      1D26  29 01             idxadd 1
      1D28  12 01 00 00 00 00 push   #0f
      1D2E  10 07             blkcopy
      1D30  22 00 10 00       push   [loc+16]
      1D34  32 01 00 00       pushblk[loc+0] x1
      1D38  0b 5d             NATIVE t0 #0x5d
      1D3A  22 00 10 00       push   [loc+16]
      1D3E  72 01 00 00       pushblk[glob+0] x1
      1D42  79 1d             idxadd 29
      1D44  7a 01             pushblk.heap x1
      1D46  79 04             idxadd 4

