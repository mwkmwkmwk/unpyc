from ..expr import *
from ..bytecode import *

from .visitor import visitor, lsd_visitor
from .want import WantIfOp, Exprs

# expressions - storable

@lsd_visitor
def _visit_lsd_name(
    self,
    op: (OpcodeLoadName, OpcodeStoreName, OpcodeDeleteName),
):
    return ExprName(op.param)

@lsd_visitor
def _visit_lsd_global(
    self,
    op: (OpcodeLoadGlobal, OpcodeStoreGlobal, OpcodeDeleteGlobal),
):
    return ExprGlobal(op.param)

@lsd_visitor
def _visit_lsd_fast(
    self,
    op: (OpcodeLoadFast, OpcodeStoreFast, OpcodeDeleteFast),
):
    return self.fast(op.param)

@lsd_visitor
def _visit_lsd_deref(
    self,
    op: (OpcodeLoadDeref, OpcodeStoreDeref, None),
):
    return self.deref(op.param)

@lsd_visitor
def _visit_lsd_attr(
    self,
    op: (OpcodeLoadAttr, OpcodeStoreAttr, OpcodeDeleteAttr),
    expr: Expr,
):
    return ExprAttr(expr, op.param)

@lsd_visitor
def _visit_lsd_subscr(
    self,
    op: (OpcodeBinarySubscr, OpcodeStoreSubscr, OpcodeDeleteSubscr),
    expr: Expr,
    idx: Expr
):
    return ExprSubscr(expr, idx)

@lsd_visitor
def _visit_lsd_slice(
    self,
    op: (
        (OpcodeSliceNN, OpcodeSliceEN, OpcodeSliceNE, OpcodeSliceEE),
        (OpcodeStoreSliceNN, OpcodeStoreSliceEN, OpcodeStoreSliceNE, OpcodeStoreSliceEE),
        (OpcodeDeleteSliceNN, OpcodeDeleteSliceEN, OpcodeDeleteSliceNE, OpcodeDeleteSliceEE),
    ),
    expr: Expr,
    start: WantIfOp(Expr, (
        OpcodeSliceEN, OpcodeStoreSliceEN, OpcodeDeleteSliceEN,
        OpcodeSliceEE, OpcodeStoreSliceEE, OpcodeDeleteSliceEE,
    )),
    end: WantIfOp(Expr, (
        OpcodeSliceNE, OpcodeStoreSliceNE, OpcodeDeleteSliceNE,
        OpcodeSliceEE, OpcodeStoreSliceEE, OpcodeDeleteSliceEE,
    )),
):
    return ExprSubscr(expr, ExprSlice2(start, end))

@visitor
def _visit_build_slice(
    self,
    op: OpcodeBuildSlice,
    exprs: Exprs('param', 1),
):
    params = [None if isinstance(expr, ExprNone) else expr for expr in exprs]
    if op.param == 2:
        return [ExprSlice2(*params)]
    elif op.param == 3:
        return [ExprSlice3(*params)]
    else:
        raise PythonError("funny slice length")
