from .helpers import PythonError

from .stmt import *
from .expr import *

class RootExec:
    __slots__ = 'block',

    def __init__(self, block):
        self.block = block

    def show(self):
        return self.block.show()

class RootEval:
    __slots__ = 'expr',

    def __init__(self, expr):
        self.expr = expr

    def show(self):
        yield self.expr.show(None)


def ast_process(deco, version):

    # processing stage 1
    #
    # - convert $buildclass and $classraw to $class, cleans their bodies

    def process_class_body(code, name):
        if code.code.name != name:
            raise PythonError("class name doesn't match code object")
        block = code.block
        if code.varnames:
            raise PythonError("class has fast vars")
        if not block.stmts or not isinstance(block.stmts[-1], StmtEndClass):
            raise PythonError("no $endclass in class def")
        return Block(block.stmts[:-1])

    def process_class_body_new(code, name):
        if code.code.name != name:
            raise PythonError("class name doesn't match code object")
        stmts = code.block.stmts[:]
        if version.has_store_locals:
            if code.varnames != ['__locals__']:
                raise PythonError("class has fast vars")
            if not stmts or not isinstance(stmts[0], StmtStartClass):
                raise PythonError("no $startclass in class def")
            stmts = stmts[1:]
        else:
            if code.varnames != []:
                raise PythonError("class has fast vars")
        if not stmts or not isinstance(stmts[-1], (StmtReturn, StmtReturnClass)):
            raise PythonError("no return at end of class")
        if isinstance(stmts[-1], StmtReturn) and not isinstance(stmts[-1].val, ExprNone):
            raise PythonError("class returns a value")
        return Block(stmts[:-1])

    def process_1(node):
        node = node.subprocess(process_1)
        if isinstance(node, ExprCall) and isinstance(node.expr, ExprBuildClass):
            args = node.args.args
            if (len(args) < 2
                or args[0][0]
                or args[1][0]
                or not isinstance(args[0][1], ExprFunctionRaw)
                or not isinstance(args[1][1], ExprUnicode)
            ):
                raise PythonError("funny args to $buildclass")
            name = args[1][1].val
            fun = args[0][1]
            if fun.defargs or fun.defkwargs:
                raise PythonError("class function has def args")
            # TODO closure information lost here
            return ExprClass(name, CallArgs(args[2:]), process_class_body_new(fun.code, name))
        if isinstance(node, ExprClassRaw):
            return ExprClass(node.name, node.args, process_class_body(node.code, node.name))
        return node

    deco = process_1(deco)

    # processing stage 2
    #
    # - convert $functionraw to $function, cleans their bodies
    # - cleans if statements: empty else suites are discarded, else suites consisting
    #   of a single if statement are changed into elif
    # - get rid of empty else suites on try except statements
    # - converts $loop and $for/$while into proper for/while
    # - for Python 1.0, convert all $print to expression statements

    def process_fun_body(node):
        stmts = node.code.block.stmts
        if version.has_kwargs:
            # new code - simple arguments are determined from code attributes,
            # complex arguments (if any) are handled as assignment statements
            # at the beginning
            args = node.code.code.args.setdefs(node.defargs, node.defkwargs)
            if version.has_complex_args:
                # split leaking on purpose
                for split, stmt in enumerate(stmts):
                    if not (
                        # stmt has to be an assignment...
                        isinstance(stmt, StmtAssign) and
                        # ... with a single destination ...
                        len(stmt.dests) == 1 and
                        # ... that is a tuple ...
                        isinstance(stmt.dests[0], ExprTuple) and
                        # ... with a fast var source ...
                        isinstance(stmt.expr, ExprFast) and
                        # ... that has a strange name ('.123' for 1.5+ or '' for 1.3/1.4) ...
                        (stmt.expr.name.startswith('.') or stmt.expr.name == '') and
                        # ... and is in the args range (this check should be redundant though)
                        stmt.expr.idx < len(args.args)
                    ):
                        break
                    # make sure the arg is still a fast var...
                    if not isinstance(args.args[stmt.expr.idx], ExprFast):
                        raise PythonError("a tuple arg already substituted?")
                    args.args[stmt.expr.idx] = stmt.dests[0]
            else:
                split = 0
            # now validate closures, if any
            if len(node.closures) != len(node.code.code.freevars):
                raise PythonError("closures len mismatch")
            for closure, free in zip(node.closures, node.code.code.freevars):
                if closure.name != free:
                    raise PythonError("closures mismatch")
        else:
            # old code - the first statement should be $args unpacking
            if not stmts or not isinstance(stmts[0], StmtArgs):
                raise PythonError("no $args in function def")
            args = stmts[0].args.setdefs(node.defargs, node.defkwargs)
            split = 1
        return ExprFunction(
            node.code.code.name,
            args,
            Block(stmts[split:])
        )

    def isdecorator(node):
        if isinstance(node, ExprCall):
            node = node.expr
        while isinstance(node, ExprAttr):
            node = node.expr
        return isinstance(node, (ExprName, ExprGlobal, ExprFast, ExprDeref))

    def undecorate(node):
        decorators = []
        while isinstance(node, ExprCall):
            if len(node.args.args) != 1:
                return None, None
            if node.args.args[0][0]:
                return None, None
            if not isdecorator(node.expr):
                return None, None
            decorators.append(node.expr)
            node = node.args.args[0][1]
        return decorators, node

    def process_def(node):
        if len(node.dests) != 1:
            return node
        dst = node.dests[0]

        # TODO allow only ExprName, punt it before name resolve
        if not isinstance(dst, (ExprName, ExprGlobal, ExprFast, ExprDeref)):
            return node
        name = dst.name

        decorators, fun = undecorate(node.expr)

        if isinstance(fun, ExprFunction):
            # TODO change endswith to proper mangling support
            if not fun.name or not name.endswith(fun.name):
                return node
            if decorators and not version.has_fun_deco:
                return node
            stmts = fun.block.stmts
            if stmts and isinstance(stmts[-1], StmtReturn) and isinstance(stmts[-1].val, ExprNone):
                stmts.pop()
            elif not version.has_return_squash:
                raise PythonError("function not terminated by return None")
            return StmtDef(decorators, fun.name, fun.args, fun.block)
        elif isinstance(fun, ExprClass):
            if not name.endswith(fun.name):
                return node
            if decorators and not version.has_cls_deco:
                return node
            return StmtClass(decorators, fun.name, fun.args, fun.body)
        else:
            return node

    def process_if(node):
        if not node.else_ or not node.else_.stmts:
            return StmtIf(node.items, None)
        elif len(node.else_.stmts) == 1:
            subif = node.else_.stmts[0]
            if isinstance(subif, StmtIf):
                return StmtIf(node.items + subif.items, subif.else_)
        return node

    def process_except(node):
        if not node.else_ or not node.else_.stmts:
            return StmtExcept(node.try_, node.items, node.any, None)
        return node

    def process_loop(node):
        stmts = node.body.stmts
        if len(stmts) != 1:
            raise PythonError("funny $loop")
        raw = stmts[0]
        if node.else_.stmts:
            else_ = node.else_
        else:
            else_ = None
        if isinstance(raw, StmtWhileRaw):
            return StmtWhile(raw.expr, raw.body, else_)
        elif isinstance(raw, StmtForRaw):
            return StmtFor(raw.expr, raw.dst, raw.body, else_)
        else:
            raise PythonError("$loop with funny contents")

    def process_2(node):
        node = node.subprocess(process_2)
        if isinstance(node, ExprFunctionRaw):
            return process_fun_body(node)
        if isinstance(node, StmtAssign):
            return process_def(node)
        if isinstance(node, StmtIf):
            return process_if(node)
        if isinstance(node, StmtExcept):
            return process_except(node)
        if isinstance(node, StmtLoop):
            return process_loop(node)
        if version.always_print_expr and isinstance(node, StmtPrintExpr):
            return StmtSingle(node.val)
        return node

    deco = process_2(deco)

    # processing stage 3
    #
    # - makes lambdas
    # - makes sure function/class-related junk is gone

    def process_lambda(node):
        stmts = node.block.stmts
        if node.name is not None and node.name != '<lambda>':
            raise PythonError("lambda with a name: {}".format(node.name))
        if len(stmts) != 1:
            raise PythonError("lambda body too long")
        if not isinstance(stmts[0], StmtReturn):
            raise PythonError("lambda body has no return")
        return ExprLambda(node.args, stmts[0].val)

    def process_3(node):
        node = node.subprocess(process_3)
        if isinstance(node, ExprFunction):
            return process_lambda(node)
        elif isinstance(node, ExprClass):
            raise PythonError("$class still alive")
        elif isinstance(node, StmtArgs):
            raise PythonError("$args still alive")
        elif isinstance(node, StmtEndClass):
            raise PythonError("$endclass still alive")
        return node

    deco = process_3(deco)

    # wrap the top level
    stmts = deco.block.stmts
    if not stmts:
        raise PythonError("empty top")
    ret = stmts[-1]
    if deco.varnames and not version.has_closure:
        raise PythonError("top has fast vars")
    if not isinstance(ret, StmtReturn):
        raise PythonError("top doesn't end in return")
    if not isinstance(ret.val, ExprNone):
        if len(stmts) != 1:
            raise PythonError("top has non-None return and long body")
        return RootEval(ret.expr)
    else:
        return RootExec(Block(stmts[:-1]))
