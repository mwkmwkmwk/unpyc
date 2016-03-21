from ..helpers import PythonError
from ..bytecode import *
from ..expr import *
from ..code import Code

from .visitor import visitor
from .want import *
from .stack import *
from . import deco_code

# make function - py 1.0 - 1.2

@visitor
def _visit_build_function(
    self,
    op: OpcodeBuildFunction,
    code: Code,
):
    return [ExprFunctionRaw(deco_code(code), [], {}, {}, [])]

@visitor
def _visit_set_func_args(
    self,
    op: OpcodeSetFuncArgs,
    args: ExprTuple,
    fun: ExprFunctionRaw,
):
    # bug alert: def f(a, b=1) is compiled as def f(a=1, b)
    return [ExprFunctionRaw(fun.code, args.exprs, {}, {}, [])]

# make function - py 1.3+

@visitor
def _visit_make_function(
    self: '!has_sane_closure',
    op: (OpcodeMakeFunction, OpcodeMakeClosure),
    args: Exprs('param', 1),
    closures: WantIfOp(UglyClosures, OpcodeMakeClosure),
    code: Code,
):
    return [ExprFunctionRaw(deco_code(code), args, {}, {}, closures or [])]

@visitor
def _visit_make_function(
    self: 'has_sane_closure',
    op: (OpcodeMakeFunction, OpcodeMakeClosure),
    args: Exprs('param', 1),
    closures: WantIfOp(ClosuresTuple, OpcodeMakeClosure),
    code: Code,
):
    return [ExprFunctionRaw(deco_code(code), args, {}, {}, closures.vars if closures else [])]

@visitor
def _visit_make_function(
    self: '!has_qualname',
    op: (OpcodeMakeFunctionNew, OpcodeMakeClosureNew),
    kwargs: Exprs('kwargs', 2),
    args: Exprs('args', 1),
    ann: Exprs('ann', 1),
    closures: WantIfOp(ClosuresTuple, OpcodeMakeClosureNew),
    code: Code,
):
    return [ExprFunctionRaw(
        deco_code(code),
        args,
        {self.string(name): arg for name, arg in kwargs},
        self.make_ann(ann),
        closures.vars if closures else [],
    )]

@visitor
def _visit_make_function(
    self: ('has_qualname', 'has_reversed_def_kwargs'),
    op: (OpcodeMakeFunctionNew, OpcodeMakeClosureNew),
    kwargs: Exprs('kwargs', 2),
    args: Exprs('args', 1),
    ann: Exprs('ann', 1),
    closures: WantIfOp(ClosuresTuple, OpcodeMakeClosureNew),
    code: Code,
    qualname: ExprUnicode,
):
    # XXX qualname
    return [ExprFunctionRaw(
        deco_code(code),
        args,
        {self.string(name): arg for name, arg in kwargs},
        self.make_ann(ann),
        closures.vars if closures else [],
    )]

@visitor
def _visit_make_function(
    self: ('has_qualname', '!has_reversed_def_kwargs'),
    op: (OpcodeMakeFunctionNew, OpcodeMakeClosureNew),
    args: Exprs('args', 1),
    kwargs: Exprs('kwargs', 2),
    ann: Exprs('ann', 1),
    closures: WantIfOp(ClosuresTuple, OpcodeMakeClosureNew),
    code: Code,
    qualname: ExprUnicode,
):
    # XXX qualname
    return [ExprFunctionRaw(
        deco_code(code),
        args,
        {self.string(name): arg for name, arg in kwargs},
        self.make_ann(ann),
        closures.vars if closures else [],
    )]

@visitor
def visit_closure_tuple(
    self,
    op: OpcodeBuildTuple,
    closures: Closures,
):
    if not op.param:
        raise NoMatch
    return [ClosuresTuple(closures)]

@visitor
def visit_load_closure(
    self,
    op: OpcodeLoadClosure,
):
    return [Closure(self.deref(op.param))]

@visitor
def _visit_reserve_fast(
    self,
    op: OpcodeReserveFast,
):
    if self.varnames is not None:
        raise PythonError("duplicate RESERVE_FAST")

    self.varnames = op.param
    return []
