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

UNARY = {0:"yield",1:"iabs",2:"fabs",3:"ret",4:"pop",5:"ftoi",6:"ftoi",
         7:"store.ind",8:"abort",9:"ineg",10:"fneg",11:"bnot",12:"dup",13:"lnot"}
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
    if best is None: return lo
    # Data just before the code can decode as a branch/yield; a real entry starts with its
    # prologue (stores/pushes), never with those - skip up to 4 such leading instructions.
    for _ in range(4):
        op=u16(data,best)
        if (op&0xF) in (4,5,6) or op==0: best+=ilen(op)
        else: break
    return best

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
            elif (op&0x30)==0x20:
                mnem="lea"
                oper=(f"@D{pos+2+s16(data,pos+2)-block_off:04X}" if base==3
                      else f"[{BASE[base]}+{s16(data,pos+2)}]")
            else: mnem="push"; oper=f"[{BASE[base]}+{s16(data,pos+2)}] x{sub}"
        elif c==3: mnem="store"; oper=f"[{BASE[base]}+{s16(data,pos+2)}]"
        elif c in (4,5,6,8):
            tgt=pos+4+s16(data,pos+2)*2; targets.add(tgt)
            if c==8: calls[tgt]=calls.get(tgt,0)+1
            mnem={4:"jmp",5:"bz",6:"bnz",8:"call"}[c]
            oper=f"@L{tgt-block_off:04X}"+(f" locals={sub}" if c==8 else "")
        elif c==7: mnem=f"cmp.{CMP.get(sub,'?')}.{'f' if mode==1 else 'i'}"
        elif c==9: mnem="idxadd"; oper=str(sub)
        elif c==0xA: mnem="load"; oper=f"x{sub}"
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
        term=("  ; ---- return ----" if op==0x0300 else "  ; ---- abort ----" if op==0x0800
              else "  ; resumes here next update" if op==0 else "")
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
# Natives whose engine function is an empty stub (a bare RET) in the retail build - debug
# prints/asserts compiled out. Their table entry still declares arguments, so the VM pops
# them, but the compiler never pushed any; the fold treats them as consuming nothing.
STUB_VERBS={(0,0x42)}
MAX_PARAMS,MAX_RETURNS,MAX_STACK=16,4,64   # sanity caps (only data-as-code ever hits them)
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

# ---------------------------------------------------------------------------------------
# VM semantics (KH1_BehaviorScriptInterpreter, Steam 0x1402CC620) that the fold relies on.
# The interpreter keeps TWO stacks:
#   operand stack  - every item is a value blob followed by its byte size, so one push/pop
#                    moves one item whatever its size (scalars are 1 word, vectors 3, ...).
#   locals stack   - frames. `call @L locals=N` skips the CALLER's N local words, pushes
#                    {N, return address} and jumps; the operand stack is left alone, so
#                    arguments stay on it and the callee pops them into its own locals.
#   unary 3 = ret  - pops the frame and jumps back; whatever the callee left on the operand
#                    stack is its return value.
#   unary 0 = yield - the interpreter returns 0 with PC already advanced: execution resumes
#                    at the next instruction on the actor's next update (not a routine end).
#   unary 8 = abort (interpreter returns -1).   unary 7 = *ptr = value (pops value, ptr).
#   push mode 0x20 = ADDRESS of [base+off] (as a handle); mode 0x30 xN = the N-word VALUE.
#   class 9 = ptr + N words;  class 0xA xN = pop ptr, push the N words it points at.
#   bases: loc = current frame, glob = script globals, heap = fields of the object whose
#   handle is in loc[0], imm = data inside the script at (instruction+2+off).
# ---------------------------------------------------------------------------------------

def _decode(data,start,end):
    ins={}; order=[]; pos=start
    while pos<end-1:
        op=u16(data,pos); L=ilen(op)
        ins[pos]={"pos":pos,"op":op,"c":op&0xF,"sub":op>>8,"mode":(op>>4)&3,
                  "base":(op>>6)&3,"len":L,"arg":s16(data,pos+2) if L>=4 else None}
        order.append(pos); pos+=L
    return ins,order

def _target(i): return i["pos"]+4+i["arg"]*2

def _effect(i,sig):
    """(pops, pushes, flow) for one instruction. flow: fall|jump|branch|ret|stop"""
    c,sub=i["c"],i["sub"]
    if c==0:
        if sub==0: return 0,0,"fall"                 # yield
        if sub==3: return 0,0,"ret"
        if sub==8: return 0,0,"stop"                 # abort
        if sub==4: return 1,0,"fall"
        if sub==7: return 2,0,"fall"
        if sub==12: return 1,2,"fall"                # dup
        if sub in (1,2,5,6,9,10,11,13): return 1,1,"fall"
        return 0,0,"fall"
    if c==1: return 2,1,"fall"
    if c==2: return 0,1,"fall"
    if c==3: return 1,0,"fall"
    if c==4: return 0,0,"jump"
    if c in (5,6): return 1,0,"branch"
    if c==7: return 1,1,"fall"
    if c==8:
        p,r=sig.get(_target(i),(0,0)); return p,r,"fall"
    if c in (9,0xA): return 1,1,"fall"
    if c==0xB:
        if (i["base"],i["sub"]) in STUB_VERBS: return 0,0,"fall"
        ar=ARITY.get((i["base"],i["sub"]))
        return (ar[0],1 if ar[1] else 0,"fall") if ar else (0,0,"fall")
    return 0,0,"fall"

def _analyze(ins,order,entries,sig):
    """Stack depth at every reachable instruction of each function (depth 0 at entry).
    Returns {entry: {"depth":{pc:d}, "min":m, "rets":[d,...], "bad":n}}."""
    out={}
    for e in entries:
        depth={e:0}; work=[e]; mn=0; rets=[]; bad=0
        while work:
            pc=work.pop(); i=ins.get(pc)
            if i is None: continue
            d=depth[pc]; p,r,flow=_effect(i,sig)
            mn=min(mn,d-p); nd=d-p+r
            succ=[]
            if flow=="fall": succ=[pc+i["len"]]
            elif flow=="jump": succ=[_target(i)]
            elif flow=="branch": succ=[pc+i["len"],_target(i)]
            elif flow=="ret": rets.append(d)
            for s in succ:
                if s not in ins: continue
                if s in depth:
                    if depth[s]!=nd: bad+=1
                    continue
                depth[s]=nd; work.append(s)
        out[e]={"depth":depth,"min":mn,"rets":rets,"bad":bad}
    return out

def _orphans(ins,order,entries,sig):
    """Code no entry reaches that starts right after a ret/abort/goto: functions the block
    never calls itself (engine/other-block entry points or dead code). One pass: each new
    entry is analysed once and its reach added."""
    reached=set()
    for a in _analyze(ins,order,entries,sig).values(): reached|=set(a["depth"])
    found=[]; prev=None
    for pc in order:
        if pc not in reached and prev is not None:
            pi=ins[prev]
            if (pi["c"]==0 and pi["sub"] in (3,8)) or pi["c"]==4:
                found.append(pc)
                reached|=set(_analyze(ins,order,[pc],sig)[pc]["depth"])
        prev=pc
    return found

def _signatures(ins,order,start):
    """Fixpoint over call targets: sig[entry] = (params popped from caller, values returned)."""
    calls=sorted({_target(i) for i in ins.values() if i["c"]==8 and _target(i) in ins})
    entries=[start]+[c for c in calls if c!=start]
    entries+= [o for o in _orphans(ins,order,entries,{}) if o not in entries]
    calls=entries[1:]
    sig={}
    for _ in range(12):
        res=_analyze(ins,order,entries,sig); new={}
        for e in entries:
            a=res[e]; p=-a["min"]
            if a["rets"]:
                rd=max(set(a["rets"]),key=a["rets"].count); r=max(rd+p,0)
            else: r=0
            # real compiled routines take a handful of args and return <=1-2 values; anything
            # bigger is data decoded as code - clamp so it can't blow up callers' stacks
            new[e]=(min(p,MAX_PARAMS),min(r,MAX_RETURNS))
        if new==sig: break
        sig=new
    return sig,res,calls

_BASE_ADDR=re.compile(r"^&(loc|glob|heap)\[(-?\d+)\]$")
_GEN_ADDR=re.compile(r"^&(.+)\[(-?\d+)\]$")

def _wrap(e):
    return e if re.fullmatch(r"[\w.&]+(\[[^\[\]]*\])*",e) else f"({e})"

def fold(data,block_off,name,size,motion_dict=None):
    end=min(block_off+4+size,len(data)); start=code_start(data,block_off,name,end)
    end=extend_end(data,block_off,start,end)
    roles=detect_roles(data,block_off,name,size)
    ins,order=_decode(data,start,end)
    sig,ana,calls=_signatures(ins,order,start)
    # owner function of each instruction (first analysis that reached it) and its depth
    # depth is relative to the function entry, where the stack already holds its params
    owner={}; dep={}
    for e in [start]+calls:
        base=sig.get(e,(0,0))[0]
        for pc,d in ana[e]["depth"].items():
            if pc not in owner: owner[pc]=e; dep[pc]=d+base
    ncall={}
    for i in ins.values():
        if i["c"]==8: ncall[_target(i)]=ncall.get(_target(i),0)+1
    targets={_target(i) for i in ins.values() if i["c"] in (4,5,6,8)}|set(calls)
    rel=lambda p: p-block_off
    stk=[]; recs=[]; pending=[]; live=True
    carry={}      # jump target -> stack contents at each jump to it (switch values etc.)
    def remember(t):
        carry.setdefault(t,[]).append(list(stk))
    def emit(off,text):
        nonlocal pending
        recs.append({"off":rel(off),"labs":pending,"text":text,"indent":0}); pending=[]
    ntmp=[0]
    def spill(pc,e):
        """Name e in a temporary instead of copying its text (dup / multi-value returns / huge
        expressions), so evaluation happens once and text can't blow up."""
        if re.fullmatch(r"-?[\w.&]+(\[[^\[\]]*\])*",e): return e
        t=f"t{ntmp[0]}"; ntmp[0]+=1; emit(pc,f"{t} = {e}"); return t
    def pop():
        return stk.pop() if stk else "?"
    def popn(n): return [pop() for _ in range(n)][::-1]
    def var(i,n=1):
        b=BASE[i["base"]]; off=i["arg"]
        return f"{b}[{off}]" if n==1 else f"{b}[{off}:{n}]"
    def addr(i):
        if i["base"]==3: return f"&data_{rel(i['pos']+2+i['arg']):04X}"
        return f"&{BASE[i['base']]}[{i['arg']}]"
    def ptradd(p,n):
        m=_BASE_ADDR.match(p)
        if m: return f"&{m.group(1)}[{int(m.group(2))+4*n}]"
        m=_GEN_ADDR.match(p)
        if m and not p.startswith("&("): return f"&{m.group(1)}[{int(m.group(2))+n}]"
        if p.startswith("&"): return f"&{p[1:]}[{n}]" if n else p
        return f"&{_wrap(p)}[{n}]"
    def deref(p,n):
        if p.startswith("&"): t=p[1:]
        else: t=f"*{_wrap(p)}"
        return t if n==1 else f"{t}:{n}"
    for pc in order:
        if len(stk)>MAX_STACK: stk=stk[-MAX_STACK:]
        for k,e in enumerate(stk):
            if len(e)>300: stk[k]=spill(pc,e)
        i=ins[pc]; c,sub=i["c"],i["sub"]
        if pc in targets: pending=pending+[f"@L{rel(pc):04X}"]
        if pc in sig:                                      # block entry / subroutine entry
            p,r=sig[pc]; stk=[f"a{k}" for k in range(p)]; live=True
            if pc==start and p:
                emit(pc,f"; block entry receives {p} value(s) from the engine: {', '.join(stk)}")
        elif pc in dep and (not live or len(stk)!=dep[pc]):
            d=max(dep[pc],0)
            got=[c_ for c_ in carry.get(pc,[]) if len(c_)==d]
            if not live and got and all(c_==got[0] for c_ in got):
                stk=list(got[0]); live=True
            elif not live or len(stk)<d: stk=(stk if live else [])[:d]
            if len(stk)<d: stk=[f"s{k}" for k in range(d-len(stk))]+stk
            elif len(stk)>d: stk=stk[len(stk)-d:] if d else []
            live=True
        elif not live:
            stk=[]; live=True
        if c==2:
            if (i["op"]&0x30)==0x00: stk.append(str(i32(data,pc+2)))
            elif (i["op"]&0x30)==0x10: stk.append(_ffmt(f32(data,pc+2)))
            elif (i["op"]&0x30)==0x20: stk.append(addr(i))
            else: stk.append(var(i,sub))
        elif c==0xA: stk.append(deref(pop(),sub))
        elif c==9: stk.append(ptradd(pop(),sub))
        elif c==1:
            b=pop(); a=pop(); stk.append(f"({a} {ARITHSYM.get(sub,'?')} {b})")
        elif c==7:
            a=pop(); stk.append(f"({a} {CMPSYM.get(sub,'?0')})")
        elif c==0:
            if sub==0: emit(pc,"yield")
            elif sub==3:
                emit(pc,f"return {', '.join(stk)}" if stk else "return"); stk=[]; live=False
            elif sub==8: emit(pc,"abort"); live=False
            elif sub==4:
                v=pop()
                if re.search(r"[A-Za-z_]\w*\??\(|call @",v): emit(pc,v)   # keep side effects only
            elif sub==7:
                v=pop(); p=pop(); emit(pc,f"{deref(p,1)} = {v}")
            elif sub==12:
                if stk: stk[-1]=spill(pc,stk[-1]); stk.append(stk[-1])
                else: stk.append("?")
            elif sub in (1,2): stk.append(f"abs({pop()})")
            elif sub in (9,10): stk.append(f"-{_wrap(pop())}")
            elif sub in (5,6): stk.append(f"int({pop()})")
            elif sub==11: stk.append(f"~{_wrap(pop())}")
            elif sub==13: stk.append(f"!{_wrap(pop())}")
        elif c==3:
            a=pop(); emit(pc,f"{var(i)} = {a}")
        elif c==4:
            remember(_target(i))
            emit(pc,f"goto @L{rel(_target(i)):04X}"); live=False
        elif c in (5,6):
            cnd=pop(); remember(_target(i)); t=rel(_target(i))
            emit(pc, f"if (!({cnd})) goto @L{t:04X}" if c==5 else f"if ({cnd}) goto @L{t:04X}")
        elif c==8:
            t=_target(i); p,r=sig.get(t,(0,0)); argv=popn(p)
            call=f"call @L{rel(t):04X}({', '.join(argv)})"
            if r==1: stk.append(call)
            elif r>1:
                t=spill(pc,call); stk.extend(f"{t}[{k}]" for k in range(r))
            else: emit(pc,call)
        elif c==0xB:
            nm=VERBS.get(f"{i['base']}:{sub:#04x}") or f"NATIVE_t{i['base']}_{sub:#x}"
            ar=ARITY.get((i["base"],sub))
            if (i["base"],sub) in STUB_VERBS:
                emit(pc,f"{nm}()")
            elif ar is None:
                args=", ".join(stk); stk=[]; emit(pc,f"{nm}({args})")
            else:
                n,ret=ar; argv=popn(n); call=f"{nm}({', '.join(argv)})"
                if ret: stk.append(call)
                else:
                    note=""
                    if motion_dict is not None and (i["base"],sub) in MOTION_VERBS and len(argv)>=2:
                        try:
                            motion_id=int(argv[1])&0xFFFF
                            idx=motion_dict.get(motion_id)
                            note=f"  ; -> anim{idx:04d}" if idx is not None else f"  ; motion_id {motion_id} (no anim)"
                        except ValueError: pass
                    emit(pc,call+note)
    recs=_structure_loops(recs)
    header=[f"; ===== {name}  (folded)  block@0x{block_off:X}  code@0x{start:X} ====="]
    if roles.get("self") is not None:
        header.append(f"; detected: glob[{roles['self']}] = self (cached actor handle, "
                       f"renamed below) - arg0 of SetMotion/QueueMotion/BlendMotion/MakeAttack")
    out=[]
    for r in recs:
        if r["labs"]:
            notes=[]
            for lb in r["labs"]:
                p=int(lb[2:],16)+block_off
                if p in sig and p!=start:
                    pa,re_=sig.get(p,(0,0))
                    params=", ".join(f"a{k}" for k in range(pa))
                    used=f"called {ncall[p]}x" if p in ncall else "not called in this block"
                    notes.append(f"sub({params}){' -> '+str(re_) if re_ else ''}, {used}")
            out.append(f"{','.join(r['labs'])}:{'  ; '+'; '.join(notes) if notes else ''}")
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
