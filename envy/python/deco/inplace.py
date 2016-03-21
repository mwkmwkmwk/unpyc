from ..stmt import *
from ..expr import *
from ..bytecode import *

from .visitor import visitor
from .stack import *
from .want import WantIfOp

# inplace assignments

def _register_inplace(otype, stype):
    @visitor
    def _visit_inplace(self, op: otype):
        return [Inplace(stype)]

_INPLACE_OPS = {
    OpcodeInplaceAdd: StmtInplaceAdd,
    OpcodeInplaceSubtract: StmtInplaceSubtract,
    OpcodeInplaceMultiply: StmtInplaceMultiply,
    OpcodeInplaceDivide: StmtInplaceDivide,
    OpcodeInplaceModulo: StmtInplaceModulo,
    OpcodeInplacePower: StmtInplacePower,
    OpcodeInplaceLshift: StmtInplaceLshift,
    OpcodeInplaceRshift: StmtInplaceRshift,
    OpcodeInplaceAnd: StmtInplaceAnd,
    OpcodeInplaceOr: StmtInplaceOr,
    OpcodeInplaceXor: StmtInplaceXor,
    OpcodeInplaceTrueDivide: StmtInplaceTrueDivide,
    OpcodeInplaceFloorDivide: StmtInplaceFloorDivide,
    OpcodeInplaceMatrixMultiply: StmtInplaceMatrixMultiply,
}

for op, stmt in _INPLACE_OPS.items():
    _register_inplace(op, stmt)

@visitor
def _visit_inplace_simple(
    self,
    op: Inplace,
    dst: (ExprName, ExprGlobal, ExprFast, ExprDeref),
    src: Expr,
):
    return [InplaceSimple(dst, src, op.stmt)]

@visitor
def _visit_inplace_attr(
    self,
    op: Inplace,
    dup: DupAttr,
    src: Expr,
):
    return [InplaceAttr(dup.expr, dup.name, src, op.stmt)]

@visitor
def _visit_inplace_subscr(
    self,
    op: Inplace,
    dup: DupSubscr,
    src: Expr,
):
    return [InplaceSubscr(dup.expr, dup.index, src, op.stmt)]

@visitor
def _visit_inplace_slice(
    self,
    op: Inplace,
    dup: DupSlice,
    src: Expr,
):
    return [InplaceSlice(dup.expr, dup.start, dup.end, src, op.stmt)]

@visitor
def _visit_load_attr_dup(
    self,
    op: OpcodeLoadAttr,
    expr: Expr,
    _: DupTop,
):
    return [DupAttr(expr, op.param)]

@visitor
def _visit_load_subscr_dup(
    self,
    op: OpcodeBinarySubscr,
    a: Expr,
    b: Expr,
    _dup: DupTwo,
):
    return [DupSubscr(a, b)]

@visitor
def _visit_load_slice_dup(
    self,
    op: (OpcodeSliceNN, OpcodeSliceEN, OpcodeSliceNE, OpcodeSliceEE),
    expr: Expr,
    start: WantIfOp(Expr, (OpcodeSliceEN, OpcodeSliceEE)),
    end: WantIfOp(Expr, (OpcodeSliceNE, OpcodeSliceEE)),
    _dup1: WantIfOp(DupTop, OpcodeSliceNN),
    _dup2: WantIfOp(DupTwo, (OpcodeSliceNE, OpcodeSliceEN)),
    _dup3: WantIfOp(DupThree, OpcodeSliceEE),
):
    return [DupSlice(expr, start, end)]

@visitor
def _visit_inplace_store_simple(
    self,
    op: Store,
    inp: InplaceSimple
):
    if inp.dst != op.dst:
        raise PythonError("simple inplace dest mismatch")
    return [inp.stmt(inp.dst, inp.src)]

@visitor
def _visit_inplace_store_attr(
    self,
    op: OpcodeStoreAttr,
    inp: InplaceAttr,
    _: RotTwo
):
    if inp.name != op.param:
        raise PythonError("inplace name mismatch")
    return [inp.stmt(ExprAttr(inp.expr, inp.name), inp.src)]

@visitor
def _visit_inplace_store_subscr(
    self,
    op: OpcodeStoreSubscr,
    inp: InplaceSubscr,
    _rot: RotThree,
):
    return [inp.stmt(ExprSubscr(inp.expr, inp.index), inp.src)]

@visitor
def _visit_inplace_store_slice(
    self,
    op: (OpcodeStoreSliceNN, OpcodeStoreSliceEN, OpcodeStoreSliceNE, OpcodeStoreSliceEE),
    inp: InplaceSlice,
    _rot2: WantIfOp(RotTwo, OpcodeStoreSliceNN),
    _rot3: WantIfOp(RotThree, (OpcodeStoreSliceEN, OpcodeStoreSliceNE)),
    _rot4: WantIfOp(RotFour, OpcodeStoreSliceEE),
):
    return [inp.stmt(ExprSubscr(inp.expr, ExprSlice2(inp.start, inp.end)), inp.src)]
