from ..helpers import PythonError
from ..bytecode import *
from ..expr import *
from ..stmt import *
from ..code import Code

from .visitor import visitor
from .want import *
from .stack import *

# classes

@visitor
def _visit_unary_call(
    self,
    op: OpcodeUnaryCall,
    fun: ExprFunctionRaw,
):
    if fun.defargs:
        raise PythonError("class call with a function with default arguments")
    return [UnaryCall(fun.code)]

@visitor
def _visit_build_class(
    self,
    op: OpcodeBuildClass,
    name: Expr,
    bases: ExprTuple,
    call: UnaryCall,
):
    return [ExprClassRaw(
        self.string(name),
        CallArgs([CallArgPos(expr) for expr in bases.exprs]),
        call.code,
        []
    )]

@visitor
def _visit_build_class(
    self: 'has_kwargs',
    op: OpcodeBuildClass,
    name: Expr,
    bases: ExprTuple,
    call: ExprCall,
):
    if call.args.args:
        raise PythonError("class call with args")
    fun = call.expr
    if not isinstance(fun, ExprFunctionRaw):
        raise PythonError("class call with non-function")
    if fun.defargs or fun.defkwargs or fun.ann:
        raise PythonError("class call with a function with default arguments")
    return [ExprClassRaw(
        self.string(name),
        CallArgs([CallArgPos(expr) for expr in bases.exprs]),
        fun.code,
        fun.closures
    )]

@visitor
def _visit_return_locals(
    self,
    op: OpcodeReturnValue,
    _: Locals,
):
    return [StmtEndClass()]

@visitor
def _visit_load_build_class(
    self,
    op: OpcodeStoreLocals,
    fast: ExprFast,
):
    if fast.idx != 0 or fast.name != '__locals__':
        raise PythonError("funny locals store")
    return [StmtStartClass()]

@visitor
def _visit_return_locals(
    self,
    op: OpcodeReturnValue,
    closure: Closure,
):
    if closure.var.name != '__class__':
        raise PythonError("returning a funny closure")
    return [StmtReturnClass()]
