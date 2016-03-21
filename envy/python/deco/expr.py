from ..expr import *
from ..stmt import StmtSingle
from ..bytecode import *

from .visitor import visitor
from .want import Exprs, WantIfOp
from .stack import DupTop, RotTwo, RotThree, Iter

# expressions - unary

def _register_unary(otype, etype):
    @visitor
    def _visit_unary(
        self,
        op: otype,
        expr: Expr,
    ):
        return [etype(expr)]

for otype, etype in {
    OpcodeUnaryPositive: ExprPos,
    OpcodeUnaryNegative: ExprNeg,
    OpcodeUnaryNot: ExprNot,
    OpcodeUnaryConvert: ExprRepr,
    OpcodeUnaryInvert: ExprInvert,
}.items():
    _register_unary(otype, etype)

# expressions - binary

def _register_binary(otype, etype):
    @visitor
    def _visit_binary(
        self,
        op: otype,
        expr1: Expr,
        expr2: Expr,
    ):
        return [etype(expr1, expr2)]

for otype, etype in {
    OpcodeBinaryPower: ExprPow,
    OpcodeBinaryMultiply: ExprMul,
    OpcodeBinaryDivide: ExprDiv,
    OpcodeBinaryModulo: ExprMod,
    OpcodeBinaryAdd: ExprAdd,
    OpcodeBinarySubtract: ExprSub,
    OpcodeBinaryLshift: ExprShl,
    OpcodeBinaryRshift: ExprShr,
    OpcodeBinaryAnd: ExprAnd,
    OpcodeBinaryOr: ExprOr,
    OpcodeBinaryXor: ExprXor,
    OpcodeBinaryTrueDivide: ExprTrueDiv,
    OpcodeBinaryFloorDivide: ExprFloorDiv,
    OpcodeBinaryMatrixMultiply: ExprMatMul,
}.items():
    _register_binary(otype, etype)

# expressions - build container

@visitor
def _visit_build_tuple(
    self,
    op: OpcodeBuildTuple,
    exprs: Exprs('param', 1),
):
    return [ExprTuple(exprs)]

@visitor
def _visit_build_list(
    self,
    op: OpcodeBuildList,
    exprs: Exprs('param', 1),
):
    return [ExprList(exprs)]

@visitor
def _visit_build_set(
    self,
    op: OpcodeBuildSet,
    exprs: Exprs('param', 1),
):
    return [ExprSet(exprs)]

# building dicts

@visitor
def _visit_build_map(
    self,
    op: OpcodeBuildMap,
):
    if op.param and not self.version.has_store_map:
        raise PythonError("Non-zero param for BUILD_MAP")
    return [ExprDict([])]

@visitor
def _visit_build_map_step_v1(
    self: 'has_reversed_kv',
    op: OpcodeStoreSubscr,
    dict_: ExprDict,
    _1: DupTop,
    val: Expr,
    _2: RotTwo,
    key: Expr
):
    dict_.items.append(DictItem(key, val))
    return [dict_]

@visitor
def _visit_build_map_step_v2(
    self: ('!has_reversed_kv', '!has_store_map'),
    op: OpcodeStoreSubscr,
    dict_: ExprDict,
    _1: DupTop,
    key: Expr,
    val: Expr,
    _2: RotThree,
):
    dict_.items.append(DictItem(key, val))
    return [dict_]

@visitor
def _visit_build_map_step_v3(
    self,
    op: OpcodeStoreMap,
    dict_: ExprDict,
    val: Expr,
    key: Expr,
):
    dict_.items.append(DictItem(key, val))
    return [dict_]

# yield

@visitor
def _visit_yield_stmt(
    self: '!has_yield_expr',
    op: OpcodeYieldValue,
    expr: Expr
):
    return [StmtSingle(ExprYield(expr))]

@visitor
def _visit_yield_expr(
    self: 'has_yield_expr',
    op: OpcodeYieldValue,
    expr: Expr,
):
    return [ExprYield(expr)]

@visitor
def _visit_yield_from(
    self,
    op: OpcodeYieldFrom,
    iter_: Iter,
    _: ExprNone
):
    return [ExprYieldFrom(iter_.expr)]

# expressions - function call

@visitor
def visit_binary_call(
    self,
    op: OpcodeBinaryCall,
    expr: Expr,
    params: ExprTuple,
):
    return [ExprCall(expr, CallArgs([CallArgPos(arg) for arg in params.exprs]))]

@visitor
def visit_call_function(
    self,
    op: (OpcodeCallFunction, OpcodeCallFunctionVar, OpcodeCallFunctionKw, OpcodeCallFunctionVarKw),
    fun: Expr,
    args: Exprs('args', 1),
    kwargs: Exprs('kwargs', 2),
    vararg: WantIfOp(Expr, (OpcodeCallFunctionVar, OpcodeCallFunctionVarKw)),
    varkw: WantIfOp(Expr, (OpcodeCallFunctionKw, OpcodeCallFunctionVarKw)),
):
    return [ExprCall(
        fun,
        CallArgs(
            [CallArgPos(arg) for arg in args] +
            [CallArgKw(arg, self.string(name)) for name, arg in kwargs] +
            ([CallArgVar(vararg)] if vararg else []) +
            ([CallArgVarKw(varkw)] if varkw else [])
        )
    )]
