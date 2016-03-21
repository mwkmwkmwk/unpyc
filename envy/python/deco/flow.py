from ..bytecode import *

from .visitor import visitor
from .want import MaybeWantFlow
from .stack import *

# misc flow

@visitor
def _visit_flow(self, op: FwdFlow, want: WantFlow):
    if op.flow in want.any:
        want.any.remove(op.flow)
    elif op.flow in want.true:
        want.true.remove(op.flow)
    elif op.flow in want.false:
        want.false.remove(op.flow)
    else:
        raise NoMatch
    if not want.any and not want.true and not want.false:
        return []
    else:
        return [want]

@visitor
def _visit_extra(self, op: JumpContinue, extra: WantFlow):
    for x in extra.any[:]:
        if x.dst <= x.src:
            op.flow.append(x)
            extra.any.remove(x)
    if not any(extra):
        return [op]
    return [op, extra]

@visitor
def _visit_extra(self, op: JumpContinue, pop: PopExcept):
    return [op, pop]

@visitor
def _visit_pop_jit(self, op: OpcodeJumpIfTrueOrPop):
    return [JumpIfTrue(op.pos, op.nextpos, [op.flow]), OpcodePopTop(op.pos, op.nextpos)]

@visitor
def _visit_pop_jit(self, op: OpcodeJumpIfFalseOrPop):
    return [JumpIfFalse(op.pos, op.nextpos, [op.flow]), OpcodePopTop(op.pos, op.nextpos)]

@visitor
def _visit_pop_jit(self, op: OpcodeJumpIfTrue):
    return [JumpIfTrue(op.pos, op.nextpos, [op.flow])]

@visitor
def _visit_pop_jit(self, op: OpcodeJumpIfFalse):
    return [JumpIfFalse(op.pos, op.nextpos, [op.flow])]

@visitor
def _visit_pop_jit(self, op: OpcodePopJumpIfTrue):
    return [PopJumpIfTrue(op.pos, op.nextpos, [op.flow])]

@visitor
def _visit_pop_jit(self, op: OpcodePopJumpIfFalse):
    return [PopJumpIfFalse(op.pos, op.nextpos, [op.flow])]

@visitor
def _visit_extra(self, op: JumpIfTrue, extra: WantFlow):
    if extra.false or extra.any:
        raise NoMatch
    return [JumpIfTrue(op.pos, op.nextpos, op.flow + extra.true)]

@visitor
def _visit_extra(self, op: JumpIfFalse, extra: WantFlow):
    if extra.true or extra.any:
        raise NoMatch
    return [JumpIfFalse(op.pos, op.nextpos, op.flow + extra.false)]

@visitor
def _visit_extra(self, op: JumpSkipJunk, extra: WantFlow):
    if extra.true or extra.false:
        raise NoMatch
    return [JumpSkipJunk(op.pos, op.nextpos, op.flow + extra.any)]

@visitor
def _visit_extra(self, op: JumpUnconditional, extra: WantFlow):
    if extra.true or extra.false:
        raise NoMatch
    return [JumpUnconditional(op.pos, op.nextpos, op.flow + extra.any)]

@visitor
def _visit_if_end(
    self,
    op: JumpUnconditional,
    final: FinalElse,
    inner: Block,
):
    return [final.maker(inner), JumpUnconditional(op.pos, op.nextpos, op.flow + final.flow)]

@visitor
def _visit_if_end(
    self,
    op: (FwdFlow, OpcodeEndFinally),
    final: FinalElse,
    inner: Block,
    want: MaybeWantFlow,
):
    return [final.maker(inner), WantFlow(final.flow + want.any, want.true, want.false), op]
