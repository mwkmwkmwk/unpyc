from ..helpers import PythonError
from ..bytecode import *
from ..expr import *
from ..stmt import *

from .visitor import visitor
from .want import LoopDammit
from .stack import *

# $loop framing

@visitor
def _visit_setup_loop(self, op: OpcodeSetupLoop):
    return [SetupLoop(op.flow), Block([])]

@visitor
def _visit_pop_loop(
    self,
    op: OpcodePopBlock,
    setup: SetupLoop,
    block: Block,
):
    return [FinalElse([setup.flow], FinalLoop(block)), Block([])]

# actual loops

@visitor
def _visit_loop(self, op: RevFlow):
    return [Loop(op.flow), Block([])]

# continue

CONTINUABLES = (
    ForLoop,
    Block,
    IfStart,
    FinalElse,
    TryExceptMid,
    TryExceptMatch,
    TryExceptAny,
)

@visitor
def _visit_continue(
    self,
    op: JumpContinue,
    loop: Loop,
    items: LoopDammit,
):
    for item in items:
        if isinstance(item, CONTINUABLES) or isinstance(item, (TopForLoop, TryExceptEndTry)):
            pass
        else:
            raise NoMatch
    if not all(flow in loop.flow for flow in op.flow):
        raise NoMatch
    for flow in op.flow:
        loop.flow.remove(flow)
    return [loop] + items + [StmtContinue()]

@visitor
def _visit_continue(
    self,
    op: OpcodeContinueLoop,
    loop: Loop,
    items: LoopDammit,
):
    seen = False
    for item in items:
        if isinstance(item, (SetupExcept, SetupFinally, With)):
            seen = True
        elif isinstance(item, CONTINUABLES):
            pass
        else:
            raise NoMatch
    if not seen:
        raise PythonError("got CONTINUE_LOOP where a JUMP_ABSOLUTE would suffice")
    if op.flow not in loop.flow:
        raise NoMatch
    loop.flow.remove(op.flow)
    return [loop] + items + [StmtContinue()]

# while loop

def _loopit(block):
    if (len(block.stmts) == 1
        and isinstance(block.stmts[0], StmtIfDead)
    ):
        if_ = block.stmts[0]
        return Block([StmtWhileRaw(if_.cond, if_.body)])
    else:
        raise PythonError("weird while loop")

@visitor
def _visit_while(
    self,
    op: OpcodePopBlock,
    setup: SetupLoop,
    empty: Block,
    loop: Loop,
    body: Block,
):
    if empty.stmts:
        raise PythonError("junk before while in loop")
    if loop.flow:
        raise PythonError("loop not dry in pop block")
    return [FinalElse([setup.flow], FinalLoop(_loopit(body))), Block([])]


@visitor
def _visit_while_true(
    self: '!has_while_true_end_opt',
    op: OpcodePopTop,
    loop: Loop,
    body: Block,
):
    if loop.flow:
        raise PythonError("loop not dry in pop block")
    return [StmtWhileRaw(ExprAnyTrue(), self.process_dead_end(body))]


def _split_inf_loop(deco, stmts, cont_ok):
    split = None
    for idx, stmt in enumerate(stmts):
        if isinstance(stmt, StmtContinue):
            if cont_ok:
                split = idx
                sstmt = StmtFinalContinue()
            else:
                break
        elif isinstance(stmt, StmtReturn) and deco.version.has_dead_return:
            split = idx
            sstmt = stmt
    if split is None:
        raise PythonError("no split in optimized infinite loop")
    return Block(stmts[:split] + [sstmt]), Block(stmts[split+1:])

def _make_inf_loop(deco, stmts, cont_ok):
    body, else_ = _split_inf_loop(deco, stmts, cont_ok)
    return StmtLoop(
        Block([StmtWhileRaw(
            ExprAnyTrue(),
            body
        )]),
        else_
    )


@visitor
def _visit_while_true(
    self: 'has_while_true_end_opt',
    op: (JumpUnconditional, FwdFlow),
    setup: SetupLoop,
    block: Block,
    loop: Loop,
    body: Block,
):
    if block.stmts:
        raise PythonError("junk in optimized infinite loop")
    if loop.flow:
        raise PythonError("loop not dry in fake pop block")
    return [_make_inf_loop(self, body.stmts, True), WantFlow([setup.flow], [], []), op]


@visitor
def _visit_while_true(
    self: ('has_while_true_end_opt', 'has_dead_return'),
    op: (JumpUnconditional, FwdFlow),
    setup: SetupLoop,
    body: Block,
):
    return [_make_inf_loop(self, body.stmts, False), WantFlow([setup.flow], [], []), op]

@visitor
def _visit_continue(
    self,
    op: JumpContinue,
    setup: SetupLoop,
    block: Block,
    loop: Loop,
    body: Block,
    items: LoopDammit,
):
    for item in items:
        if isinstance(item, CONTINUABLES) or isinstance(item, (TopForLoop, TryExceptEndTry)):
            pass
        else:
            raise NoMatch
    if loop.flow:
        raise PythonError("got outer continue, but inner loop not dry yet")
    if block.stmts:
        raise PythonError("non-empty loop block in outer continue")
    body, else_ = _split_inf_loop(self, body.stmts, True)
    return [
        FinalElse([setup.flow], FinalLoop(Block([StmtWhileRaw(ExprAnyTrue(), body)]))),
        else_
    ] + items + [op]
