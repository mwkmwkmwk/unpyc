from ..expr import ExprBuildClass
from ..stmt import StmtBreak

from .visitor import visitor
from .stack import *

# stack ops

def _register_token(otype, ttype):
    @visitor
    def visit_token(
        self,
        op: otype,
    ):
        return [ttype()]

for otype, ttype in {
    OpcodeDupTop: DupTop,
    OpcodeDupTwo: DupTwo,
    OpcodeRotTwo: RotTwo,
    OpcodeRotThree: RotThree,
    OpcodeRotFour: RotFour,
    OpcodePopExcept: PopExcept,
    OpcodeLoadLocals: Locals,
    OpcodeLoadBuildClass: ExprBuildClass,
    OpcodeBreakLoop: StmtBreak,
}.items():
    _register_token(otype, ttype)

@visitor
def _visit_dup_topx(
    self,
    op: OpcodeDupTopX,
):
    if op.param == 2:
        return [DupTwo()]
    elif op.param == 3:
        return [DupThree()]
    else:
        raise PythonError("funny DUP_TOPX parameter")

@visitor
def _visit_want_pop(
    self,
    op: OpcodePopTop,
    want: WantPop,
):
    return []

@visitor
def _visit_want_rot_two(
    self,
    op: OpcodePopTop,
    want: WantRotPop,
    _: RotTwo,
):
    return []

# nop

@visitor
def visit_nop(
    self,
    op: OpcodeNop,
):
    return []

# expressions - load const

@visitor
def _visit_load_const(
    self,
    op: OpcodeLoadConst,
):
    return [op.const]

# line numbers

@visitor
def visit_set_lineno(
    self,
    op: OpcodeSetLineno,
):
    self.lineno = op.param
    return []
