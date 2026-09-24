# Reading kh1_bd_disasm output

`kh1_bd_disasm.py` has two views of the same behavior bytecode.

## The mental model: a postfix stack machine

The `.bd` VM is a **stack machine**. Instructions *push* values onto a stack, and
operations *consume* whatever is on top. Arguments therefore always appear **before**
the thing that uses them (reverse-Polish / postfix order). To read raw output, when you
reach a call or store, look **upward** at the run of `push`es just above it — those are its
inputs.

## Raw view (default)

`python kh1_bd_disasm.py xa_ex_3000.mdls 04`

Columns: optional `@Lxxxx:` label (present only if something jumps here) · block-relative
offset · raw bytes · decoded instruction. Instruction kinds:

- `push #25` / `push [loc+0]` / `pushblk[glob+0]` — put a literal / variable / block on the stack.
- `idxadd 3` — index into the top value (`.field3`).
- `add.f`, `sub.i`, `cmp.gez.i` — pop operands, push a result (`.f`/`.i` = float/int).
- `store [loc+0]` — pop the top and save it into a variable.
- `SpawnObj()`, `MakeAttack()`, `NATIVE t0 #0x19` — call an engine *verb* (named from
  `kh1_bd_verbs.json`); it consumes the values pushed just above it.
- `call @Lxxxx locals=N` — call a script subroutine; `jmp/bz/bnz @Lxxxx` — control flow
  (bz = branch-if-zero); `end` — routine boundary.

Mnemonic and operand are column-aligned (matching `evdl_tool.py`'s disasm layout), and labels
print on their own line rather than inline, e.g.:

```
@L0032:
      0040  15 00 1c 00       bz             @L007C
```

## Folded view (`--fold`)

`python kh1_bd_disasm.py xa_ex_3000.mdls 04 --fold`

This reconstructs the stack into function-call pseudocode — `push a; push b; Verb()` becomes
`Verb(a, b)`. Verb argument counts come from the harvested arity table in `kh1_bd_verbs.json`.
Example:

```
loc[12] = MakeAttack(GetActor(), globblk[0][4], heapblk[1])
SetFlag2(loc[12], 3)
MoveByVel(heap[0], loc[32], 50f)     ; 50f is the speed FM raises to 300f
```

Symbols: `loc[n]`/`glob[n]`/`heap[n]` = local/global/heap variables; `xblk[n]` = a struct/block
ref; `(a sub b)` = a − b, `(x <0)` = comparison against 0; `goto @Lxxxx` / `if (cond) goto @Lxxxx`
= control flow; `return` = routine end.

**Loop recovery.** The fold pass recognizes the one loop idiom this VM's compiler actually
emits — a labeled test-and-exit immediately followed by a body that jumps straight back to that
same label, with nothing between the back-jump and the exit label — and rewrites it as a real
`while (cond) { ... }` block instead of the raw goto/label pair. It only fires on that exact,
unambiguous shape; anything else (breaks, multiple exits, do-while) is left as flat gotos rather
than risk misrepresenting the control flow.

### Caveats (folded view is best-effort)
- `?` = a value the routine received from its caller, or an unresolved pop.
- `call @Lxxxx(...)` — script-subroutine argument lists are approximate: the VM passes
  subroutine args on the stack and their arity isn't statically known, so the fold shows the
  pending stack as the arg list (usually right, occasionally over-grabs).
- Unnamed verbs show as `NATIVE_tN_0xNN(...)`; name them in `kh1_bd_verbs.json` and both views update.
