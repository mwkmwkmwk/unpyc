from ..stmt import *
from ..bytecode import *

from .visitor import visitor
from .stack import *

# try finally

# need block to make sure we're not inside with
@visitor
def _visit_setup_finally(self, op: OpcodeSetupFinally, block: Block):
    return [block, SetupFinally(op.flow), Block([])]

@visitor
def _visit_finally_pop(
    self,
    op: OpcodePopBlock,
    setup: SetupFinally,
    block: Block,
):
    return [TryFinallyPending(block, setup.flow)]

@visitor
def _visit_finally(
    self,
    op: FwdFlow,
    try_: TryFinallyPending,
    _: ExprNone,
):
    if try_.flow != op.flow:
        raise PythonError("funny finally")
    return [TryFinally(try_.body), Block([])]

@visitor
def _visit_finally_end(
    self,
    op: OpcodeEndFinally,
    try_: TryFinally,
    inner: Block,
):
    return [StmtFinally(try_.body, inner)]
