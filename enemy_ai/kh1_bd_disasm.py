#!/usr/bin/env python3
"""KH1 enemy behavior-script (.bd) disassembler.

The .bd bytecode is embedded in xa_ex_*.mdls model files and run by the game's
stack-VM interpreter (KH1_BehaviorScriptInterpreter @ 0x1402CC620, Steam build).

NOTE: the .bd format, opcodes, and native-verb indices are identical on the Steam and
Epic (EGS) builds - this tool needs no executable addresses to run. The 0x140... addresses
cited here and in kh1_bd_verbs.json are Steam-build provenance only.

Layout varies by enemy: bosses split behavior into suffixed blocks (ex_XXXX_NN.bd) held in
a sub-container; simple enemies keep one un-suffixed block (ex_XXXX.bd) = stat/drop data
followed by behavior code. This tool finds .bd blocks anywhere and locates the code region
automatically.

Opcode = little-endian u16:
    class = op & 0x0F ; mode = (op>>4)&3 ; base = (op>>6)&3 ; sub = op>>8
Lengths: class2 push mode00/10 = 6B (inline imm); class2 mode20/30 & class3/4/5/6/8 = 4B; else 2B.

Usage:
  python kh1_bd_disasm.py <file.mdls>            list behavior blocks
  python kh1_bd_disasm.py <file.mdls> <blk|all>  disassemble (blk = name substr or index)
  python kh1_bd_disasm.py <file.mdls> <blk> --fold   fold into function-call pseudocode
Save output as .bdasm to get highlighting/outline from the KH1 EVS VS Code extension
(vscode-evs/ in this repo), e.g. `... all --fold > tz_3000.bdasm`.
"""
import sys, struct, re, os, json

UNARY = {0:"end",1:"iabs",2:"fabs",3:"tailcall",4:"pop",5:"ftoi",6:"ftoi",
         7:"blkcopy",8:"abort",9:"ineg",10:"fneg",11:"bnot",12:"dup",13:"lnot"}
ARITH = {0:"add",1:"sub",2:"mul",3:"div",4:"mod",5:"and",6:"or",7:"xor",8:"shl",9:"shr",10:"land",11:"lor"}
CMP   = {0:"ltz",1:"lez",2:"eqz",3:"nez",4:"gez",5:"gtz"}
BASE  = {0:"loc",1:"glob",2:"heap",3:"imm"}

def load_verbs():
    p=os.path.join(os.path.dirname(os.path.abspath(__file__)),"kh1_bd_verbs.json")
    try:
        d=json.load(open(p)); return {k:v.get("name") for k,v in d.items() if not k.startswith("_")}
    except Exception: return {}
VERBS=load_verbs()
def load_arity():
    p=os.path.join(os.path.dirname(os.path.abspath(__file__)),"kh1_bd_verbs.json")
    try:
        d=json.load(open(p)); a={}
        for t in (0,1):
            for i,pair in enumerate(d.get("_arity_t%d"%t,[])): a[(t,i)]=tuple(pair)
        return a
    except Exception: return {}
ARITY=load_arity()

def ilen(op):
    c=op&0xF
    if c==2: return 6 if (op&0x30) in (0x00,0x10) else 4
    if c in (3,4,5,6,8): return 4
    return 2
def u16(b,i): return struct.unpack_from("<H",b,i)[0]
def s16(b,i): return struct.unpack_from("<h",b,i)[0]
def i32(b,i): return struct.unpack_from("<i",b,i)[0]
def f32(b,i): return struct.unpack_from("<f",b,i)[0]

def _sibling_motion_dict(mdls_path):
    """{motion_id: local_anim_index} from the sibling .mset next to mdls_path, so --fold
    can annotate SetMotion/QueueMotion/BlendMotion calls with the anim they resolve to.
    Empty (not an error) if missing/invalid - see kh1_motion_dict.py for the resolver."""
    mset_path=os.path.splitext(mdls_path)[0]+".mset"
    try:
        from kh1_motion_dict import read_motion_dict
        return read_motion_dict(mset_path)
    except Exception:
        return {}

def _is_bd_name(name):
    return (3<=len(name)<=20 and b"." in name and chr(name[0]).isalpha()
            and all(chr(c) in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_." for c in name))

def find_blocks(data):
    """Find every .bd block (magic 0x0314 + ascii name) anywhere in the file. Handles both
    boss layout (blocks in a sub-container) and simple-enemy layout (a single top-level block)."""
    magic=b"\x14\x03"
    out=[]; seen=set()
    for m in re.finditer(magic, data):
        p=m.start()
        name=data[p+4:p+4+24].split(b"\x00")[0]
        if _is_bd_name(name):
            size=u16(data,p+2)
            if 0<size and p+4+size<=len(data)+16 and p not in seen:
                seen.add(p); out.append((p,name.decode("ascii","replace"),size))
    out.sort()
    return out

def code_start(data,block_off,name,end):
    """Code start = even offset with the longest run of valid instructions. For suffixed
    behavior blocks this is right after the name; for the un-suffixed stat block it is after
    the stat/drop data (data first, then code)."""
    best,bs=None,-1
    lo=block_off+4+len(name)
    if lo%2: lo+=1
    for cand in range(lo,end-2,2):
        pos,nonend,consec=cand,0,0
        while pos<end-1:
            op=u16(data,pos)
            if op==0:                       # END / zero padding
                consec+=1
                if consec>3: break          # >3 in a row => padding, not code
                pos+=2; continue
            consec=0
            if (op&0xF)==0 and (op>>8) not in UNARY: break   # invalid opcode
            nonend+=1; pos+=ilen(op)
        if nonend>bs: best,bs=cand,nonend
    return best if best is not None else lo

def extend_end(data,block_off,start,end):
    """The declared block size can undercount the real code length (observed in
    ex_2020.bd: a NATIVE-call pair got split across the boundary). Walk from
    `start` (always instruction-aligned, unlike `end`) through the declared
    region unconditionally - identical to current behavior, zero regression risk -
    then, once past the declared end, keep decoding only while bytes still look
    like valid instructions (same padding-tolerance as code_start), stopping
    immediately at the start of a sibling .bd block's header so multi-block
    containers (e.g. Sephiroth's suffixed-block layout) never get swallowed."""
    pos,consec=start,0; limit=len(data)
    while pos<limit-1:
        if pos>=end:
            if data[pos:pos+2]==b"\x14\x03" and _is_bd_name(data[pos+4:pos+4+24].split(b"\x00")[0]):
                break
            op=u16(data,pos)
            if op==0:
                consec+=1
                if consec>3: break
                pos+=2; continue
            consec=0
            if (op&0xF)==0 and (op>>8) not in UNARY: break
            pos+=ilen(op)
        else:
            pos+=ilen(u16(data,pos))
    return max(pos,end)

def _rename_roles(text,roles):
    """Substitute a detected glob slot with a readable name (e.g. glob[4]/globblk[4]/
    glob+4 -> self). Bracket/plus-anchored patterns are inherently safe against partial
    matches (glob[4] can't match inside glob[40] - the literal ']' or '+'..non-digit
    boundary that follows rules it out), so no extra word-boundary logic is needed."""
    for role,slot in roles.items():
        label="self" if role=="self" else role
        text=text.replace(f"globblk[{slot}]",label)
        text=text.replace(f"glob[{slot}]",label)
        text=re.sub(rf"glob\+{slot}\b",label,text)
    return text

def disasm(data,block_off,name,size):
    end=min(block_off+4+size,len(data))
    start=code_start(data,block_off,name,end)
    end=extend_end(data,block_off,start,end)
    roles=detect_roles(data,block_off,name,size)
    rows,targets,calls=[],set(),{}; pos=start
    while pos<end-1:
        op=u16(data,pos); c=op&0xF; sub=op>>8; mode=(op>>4)&3; base=(op>>6)&3
        L=ilen(op); raw=data[pos:pos+L]; mnem=""; oper=""
        if c==0: mnem=UNARY.get(sub,f"un{sub:#x}")
        elif c==1: mnem=f"{ARITH.get(sub,'?')}.{'f' if mode==1 else 'i'}"
        elif c==2:
            if (op&0x30)==0x00: mnem="push"; oper=f"#{i32(data,pos+2)}"
            elif (op&0x30)==0x10: mnem="push"; oper=f"#{f32(data,pos+2):g}f"
            elif (op&0x30)==0x20: mnem="push"; oper=f"[{BASE[base]}+{s16(data,pos+2)}]"
            else: mnem="pushblk"; oper=f"[{BASE[base]}+{s16(data,pos+2)}] x{sub}"
        elif c==3: mnem="store"; oper=f"[{BASE[base]}+{s16(data,pos+2)}]"
        elif c in (4,5,6,8):
            tgt=pos+4+s16(data,pos+2)*2; targets.add(tgt)
            if c==8: calls[tgt]=calls.get(tgt,0)+1
            mnem={4:"jmp",5:"bz",6:"bnz",8:"call"}[c]
            oper=f"@L{tgt-block_off:04X}"+(f" locals={sub}" if c==8 else "")
        elif c==7: mnem=f"cmp.{CMP.get(sub,'?')}.{'f' if mode==1 else 'i'}"
        elif c==9: mnem="idxadd"; oper=str(sub)
        elif c==0xA: mnem="pushblk.heap"; oper=f"x{sub}"
        elif c==0xB:
            nm=VERBS.get(f"{base}:{sub:#04x}")
            mnem=nm if nm else "NATIVE"; oper="()" if nm else f"t{base} #{sub:#04x}"
        rows.append((pos,raw,mnem,oper,op)); pos+=L
    header=[f"; ===== {name}  block@0x{block_off:X}  code@0x{start:X}  size=0x{size:X} ====="]
    if roles.get("self") is not None:
        header.append(f"; detected: glob[{roles['self']}] = self (cached actor handle, "
                       f"renamed below) - arg0 of SetMotion/QueueMotion/BlendMotion/MakeAttack")
    L=[]
    for pos,raw,mnem,oper,op in rows:
        r=pos-block_off
        if pos in targets:
            n=calls.get(pos)
            L.append(f"@L{r:04X}:{f'  ; sub, called {n}x' if n else ''}")
        term="  ; ---- routine end ----" if op==0 else ""
        L.append(f"      {r:04X}  {raw.hex(' '):<17} {mnem:<14} {oper:<16}{term}")
    return "\n".join(header)+"\n"+_rename_roles("\n".join(L),roles)


CMPSYM={0:"<0",1:"<=0",2:"==0",3:"!=0",4:">=0",5:">0"}
ARITHSYM={0:"+",1:"-",2:"*",3:"/",4:"%",5:"&",6:"|",7:"^",8:"<<",9:">>",10:"&&",11:"||"}
def _ffmt(v):
    """Float literal for fold's pseudocode: always show a decimal point (50.0, -1.0)
    instead of the raw-view's asm-style 'f' suffix (50f, -1f) - a decimal point alone
    already disambiguates float from int in expression context."""
    s=f"{v:g}"
    return s if any(ch in s for ch in ".en") else s+".0"
MOTION_VERBS={(0,0x0c),(0,0x0d),(0,0x0e)}   # (table,sub): BlendMotion, SetMotion, QueueMotion
ACTOR_ARG0_VERBS={(0,0x0c),(0,0x0d),(0,0x0e),(0,0x17)}  # BlendMotion, SetMotion, QueueMotion, MakeAttack - confirmed arg0=actor

def detect_roles(data,block_off,name,size):
    """Best-effort, conservative auto-detect of which glob[N] slot is this script's own
    cached 'self' actor handle: tally which glob slot appears as arg0 to verbs confirmed
    to always take the actor first (SetMotion/QueueMotion/BlendMotion/MakeAttack), via the
    same stack simulation fold() uses. Only reports a slot when one dominates (>=80% of
    tallied hits, >=2 hits) - silence beats a wrong guess. Runs on raw bytecode; does not
    need the folded pseudocode, so it's available for both disasm() and fold() output."""
    end=min(block_off+4+size,len(data)); start=code_start(data,block_off,name,end)
    end=extend_end(data,block_off,start,end)
    stk=[]; pos=start; tally={}
    while pos<end-1:
        op=u16(data,pos); c=op&0xF; sub=op>>8; base=(op>>6)&3
        if c==2:
            if (op&0x30)==0x20: stk.append(("glob",s16(data,pos+2)) if BASE[base]=="glob" else None)
            elif (op&0x30) in (0x00,0x10): stk.append(None)
            else: stk.append(("glob",s16(data,pos+2)) if BASE[base]=="glob" else None)
        elif c==0xA: stk.append(None)
        elif c==9:
            if stk: stk.pop()
            stk.append(None)
        elif c in (1,7):
            if stk: stk.pop()
            if c==1 and stk: stk.pop()
            stk.append(None)
        elif c==0:
            if sub==0: stk.clear()
            elif sub==12:
                if stk: stk.append(stk[-1])
            elif sub in (1,2,9,10,5,6,11,13):
                if stk: stk.pop()
                stk.append(None)
            elif sub in (3,4):
                if stk: stk.pop()
        elif c==3:
            if stk: stk.pop()
        elif c==8:
            stk.clear()
        elif c==0xB:
            ar=ARITY.get((base,sub)); n=ar[0] if ar else len(stk)
            argv=[stk.pop() if stk else None for _ in range(n)][::-1]
            if (base,sub) in ACTOR_ARG0_VERBS and argv and argv[0]:
                slot=argv[0][1]; tally[slot]=tally.get(slot,0)+1
            if ar and ar[1]: stk.append(None)
        else: pass
        pos+=ilen(op)
    if not tally: return {}
    best=max(tally,key=tally.get); total=sum(tally.values())
    return {"self":best} if tally[best]>=2 and tally[best]>=0.8*total else {}

def _structure_loops(recs):
    # Recognize the "test-at-top" while idiom this VM's compiler emits for countdown/wait
    # loops: a labeled bz-exit immediately followed by a body that ends in an unconditional
    # jump back to that same label, with nothing between the back-jump and the exit label.
    # Only fires on that exact, unambiguous shape - anything else is left as flat goto/labels.
    for i,r in enumerate(recs):
        if not r["labs"]: continue
        m=re.match(r"^if \(!\((.*)\)\) goto (@L[0-9A-Fa-f]{4})$",r["text"])
        if not m: continue
        cond,exit_lab=m.group(1),m.group(2)
        j=next((k for k in range(i+1,len(recs))
                if any(recs[k]["text"]==f"goto {lb}" for lb in r["labs"])),None)
        if j is None or j+1>=len(recs) or exit_lab not in recs[j+1]["labs"]: continue
        r["text"]=f"while ({cond}) {{"
        for k in range(i+1,j): recs[k]["indent"]+=1
        recs[j]["text"]="}"
    return recs

def fold(data,block_off,name,size,motion_dict=None):
    end=min(block_off+4+size,len(data)); start=code_start(data,block_off,name,end)
    end=extend_end(data,block_off,start,end)
    roles=detect_roles(data,block_off,name,size)
    # collect jump/call targets for labels, tallying call counts separately so labels
    # reached only by goto/if-goto (loop heads, if-merges) can be told apart from real
    # call @Lxxxx subroutine entries
    targets=set(); calls={}; pos=start
    while pos<end-1:
        op=u16(data,pos); c=op&0xF
        if c in (4,5,6,8):
            tgt=pos+4+s16(data,pos+2)*2; targets.add(tgt)
            if c==8: calls[tgt]=calls.get(tgt,0)+1
        pos+=ilen(op)
    stk=[]; recs=[]; pending=[]
    def emit(off,text):
        nonlocal pending
        recs.append({"off":off-block_off,"labs":pending,"text":text,"indent":0})
        pending=[]
    def pop(): return stk.pop() if stk else "?"
    def popn(n):
        g=[pop() for _ in range(n)]; return g[::-1]
    pos=start
    while pos<end-1:
        if pos in targets: pending=pending+[f"@L{pos-block_off:04X}"]
        op=u16(data,pos); c=op&0xF; sub=op>>8; mode=(op>>4)&3; base=(op>>6)&3
        if c==2:
            if (op&0x30)==0x00: stk.append(str(i32(data,pos+2)))
            elif (op&0x30)==0x10: stk.append(_ffmt(f32(data,pos+2)))
            elif (op&0x30)==0x20: stk.append(f"{BASE[base]}[{s16(data,pos+2)}]")
            else: stk.append(f"{BASE[base]}blk[{s16(data,pos+2)}]")
        elif c==0xA: stk.append(f"heapblk[{sub}]")
        elif c==1:
            b=pop(); a=pop(); stk.append(f"({a} {ARITHSYM.get(sub,'?')} {b})")
        elif c==7:
            a=pop(); stk.append(f"({a} {CMPSYM.get(sub,'?0')})")
        elif c==9:
            a=pop(); stk.append(f"{a}[{sub}]")
        elif c==0:
            if sub==0:
                for lo in stk: emit(pos,lo)
                stk.clear(); emit(pos,"return")
            elif sub==4: emit(pos,pop())
            elif sub==12:
                if stk: stk.append(stk[-1])
            elif sub in (1,2): stk.append(f"abs({pop()})")
            elif sub in (9,10): stk.append(f"-{pop()}")
            elif sub in (5,6): stk.append(f"int({pop()})")
            elif sub==11: stk.append(f"~{pop()}")
            elif sub==13: stk.append(f"!{pop()}")
            elif sub==3: emit(pos,f"tailcall {pop()}")
            elif sub==8: emit(pos,"abort")
        elif c==3: a=pop(); emit(pos,f"{BASE[base]}[{s16(data,pos+2)}] = {a}")
        elif c==4: emit(pos,f"goto @L{(pos+4+s16(data,pos+2)*2)-block_off:04X}")
        elif c in (5,6):
            cnd=pop(); t=(pos+4+s16(data,pos+2)*2)-block_off
            emit(pos, f"if (!({cnd})) goto @L{t:04X}" if c==5 else f"if ({cnd}) goto @L{t:04X}")
        elif c==8:
            t=(pos+4+s16(data,pos+2)*2)-block_off; args=", ".join(stk); stk.clear()
            emit(pos,f"call @L{t:04X}({args})")
        elif c==0xB:
            nm=VERBS.get(f"{base}:{sub:#04x}") or f"NATIVE_t{base}_{sub:#x}"
            ar=ARITY.get((base,sub))
            if ar is None:
                args=", ".join(stk); stk.clear(); emit(pos,f"{nm}({args})")
            else:
                n,ret=ar; argv=popn(n); call=f"{nm}({', '.join(argv)})"
                if ret: stk.append(call)
                else:
                    note=""
                    if motion_dict is not None and (base,sub) in MOTION_VERBS and len(argv)>=2:
                        try:
                            motion_id=int(argv[1])&0xFFFF
                            idx=motion_dict.get(motion_id)
                            note=f"  ; -> anim{idx:04d}" if idx is not None else f"  ; motion_id {motion_id} (no anim)"
                        except ValueError: pass
                    emit(pos,call+note)
        pos+=ilen(op)
    recs=_structure_loops(recs)
    header=[f"; ===== {name}  (folded)  block@0x{block_off:X}  code@0x{start:X} ====="]
    if roles.get("self") is not None:
        header.append(f"; detected: glob[{roles['self']}] = self (cached actor handle, "
                       f"renamed below) - arg0 of SetMotion/QueueMotion/BlendMotion/MakeAttack")
    call_labels={f"@L{p-block_off:04X}":n for p,n in calls.items()}
    out=[]
    for r in recs:
        if r["labs"]:
            n=max((call_labels[lb] for lb in r["labs"] if lb in call_labels),default=None)
            out.append(f"{','.join(r['labs'])}:{f'  ; sub, called {n}x' if n else ''}")
        out.append(f"      {r['off']:04X}  {'    '*r['indent']}{r['text']}")
    return "\n".join(header)+"\n"+_rename_roles("\n".join(out),roles)

def main():
    if len(sys.argv)<2: print(__doc__); return
    data=open(sys.argv[1],"rb").read(); blocks=find_blocks(data)
    if not blocks: print("No .bd blocks found."); return
    if len(sys.argv)==2:
        print(f"{'idx':>3}  {'name':<18} {'block':>12} {'size':>7}")
        for i,(b,n,s) in enumerate(blocks): print(f"{i:>3}  {n:<18} 0x{b:08X} 0x{s:04X}")
        return
    args=sys.argv[2:]
    folded = any(x in ("fold","--fold","-f") for x in args)
    args=[x for x in args if x not in ("fold","--fold","-f")]
    sel=args[0] if args else "all"
    motion_dict = _sibling_motion_dict(sys.argv[1]) if folded else None
    for i,(b,n,sz) in enumerate(blocks):
        if sel=="all" or sel==str(i) or sel in n:
            print(fold(data,b,n,sz,motion_dict) if folded else disasm(data,b,n,sz)); print()

if __name__=="__main__": main()
