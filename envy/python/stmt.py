from envy.show import indent
from .helpers import PythonError
from .expr import ExprFast

from .ast import *



class StmtReturn(Stmt):
    val = Field(Expr)

    def show(self):
        yield "return {}".format(self.val.show(None))


class StmtPrint(Stmt):
    vals = ListField(Expr)
    nl = Field(bool)

    def show(self):
        if self.vals:
            yield "print {}{}".format(', '.join(val.show(None) for val in self.vals), '' if self.nl else ',')
        else:
            assert self.nl
            yield "print"


class StmtPrintTo(Stmt):
    to = Field(Expr)
    vals = ListField(Expr)
    nl = Field(bool)

    def show(self):
        if self.vals:
            yield "print >>{}, {}{}".format(self.to.show(None), ', '.join(val.show(None) for val in self.vals), '' if self.nl else ',')
        else:
            assert self.nl
            yield "print >>{}".format(self.to.show(None))


class StmtSingle(Stmt):
    val = Field(Expr)

    def show(self):
        yield self.val.show(None)


class StmtPrintExpr(Stmt):
    val = Field(Expr)

    def show(self):
        yield "$print {}".format(self.val.show(None))


class StmtAssign(Stmt):
    dests = ListField(Expr)
    expr = Field(Expr)

    def show(self):
        yield '{}{}'.format(
            ''.join(
                '{} = '.format(dest.show(None))
                for dest in self.dests
            ),
            self.expr.show(None)
        )


class StmtInplace(Stmt, abstract=True):
    dest = Field(Expr)
    src = Field(Expr)

    def show(self):
        yield '{} {} {}'.format(self.dest.show(None), self.sign, self.src.show(None))


class StmtInplaceAdd(StmtInplace):
    sign = '+='


class StmtInplaceSubtract(StmtInplace):
    sign = '-='


class StmtInplaceMultiply(StmtInplace):
    sign = '*='


class StmtInplaceDivide(StmtInplace):
    sign = '/='


class StmtInplaceModulo(StmtInplace):
    sign = '%='


class StmtInplacePower(StmtInplace):
    sign = '**='


class StmtInplaceLshift(StmtInplace):
    sign = '<<='


class StmtInplaceRshift(StmtInplace):
    sign = '>>='


class StmtInplaceAnd(StmtInplace):
    sign = '&='


class StmtInplaceOr(StmtInplace):
    sign = '|='


class StmtInplaceXor(StmtInplace):
    sign = '^='


class StmtInplaceTrueDivide(StmtInplace):
    sign = '$/='


class StmtInplaceFloorDivide(StmtInplace):
    sign = '//='


class StmtInplaceMatrixMultiply(StmtInplace):
    sign = '@='


class StmtDel(Stmt):
    val = Field(Expr)

    def show(self):
        yield "del {}".format(self.val.show(None))


class StmtRaise(Stmt):
    cls = MaybeField(Expr)
    val = MaybeField(Expr)
    tb = MaybeField(Expr)

    def show(self):
        if self.cls is None:
            yield "raise"
        elif self.val is None:
            if self.tb is None:
                yield "raise {}".format(self.cls.show(None))
            else:
                yield "raise {} from {}".format(self.cls.show(None), self.tb.show(None))
        elif self.tb is None:
            yield "raise {}, {}".format(self.cls.show(None), self.val.show(None))
        else:
            yield "raise {}, {}, {}".format(self.cls.show(None), self.val.show(None), self.tb.show(None))


class StmtListAppend(Stmt):
    tmp = Field(Expr)
    val = Field(Expr)

    def show(self):
        yield "$listappend {}, {}".format(self.tmp.show(None), self.val.show(None))


class StmtSetAdd(Stmt):
    tmp = Field(Expr)
    val = Field(Expr)

    def show(self):
        yield "$setadd {}, {}".format(self.tmp.show(None), self.val.show(None))


class StmtMapAdd(Stmt):
    tmp = Field(Expr)
    key = Field(Expr)
    val = Field(Expr)

    def show(self):
        yield "$mapadd {}, {}: {}".format(
            self.tmp.show(None),
            self.key.show(None),
            self.val.show(None)
        )


class StmtAssert(Stmt):
    expr = Field(Expr)
    msg = MaybeField(Expr)

    def show(self):
        if self.msg is None:
            yield "assert {}".format(self.expr.show(None))
        else:
            yield "assert {}, {}".format(self.expr.show(None), self.msg.show(None))


class StmtImport(Stmt):
    level = Field(int)
    name = Field(str)
    attrs = ListField(str)
    as_ = Field(Expr)

    def show(self):
        yield "import {} {} as{} {}".format(self.level, self.name, ''.join('.' + attr for attr in self.attrs), self.as_.show(None))


class FromItem(Node):
    name = Field(str)
    expr = MaybeField(Expr)


class StmtFromImport(Stmt):
    level = Field(int)
    name = Field(str)
    items = ListField(FromItem)

    def show(self):
        yield "from {} {} import {}".format(
            self.level,
            self.name,
            ', '.join(
                "{} as {}".format(item.name, item.expr.show(None)) if item.expr else item.name
                for item in self.items
            )
        )


class StmtImportStar(Stmt):
    level = Field(int)
    name = Field(str)

    def show(self):
        yield "from {} {} import *".format(self.level, self.name)


class StmtExec(Stmt):
    code = Field(Expr)
    globals = MaybeField(Expr)
    locals = MaybeField(Expr)

    def show(self):
        if self.globals is None:
            yield "exec {}".format(
                self.code.show(None)
            )
        elif self.locals is None:
            yield "exec {} in {}".format(
                self.code.show(None),
                self.globals.show(None)
            )
        else:
            yield "exec {} in {}, {}".format(
                self.code.show(None),
                self.globals.show(None),
                self.locals.show(None)
            )


class StmtIfRaw(Stmt):
    cond = Field(Expr)
    body = Field(Block)
    else_ = Field(Block, volatile=True)

    def show(self):
        yield "$if {}:".format(self.cond.show(None))
        yield from indent(self.body.show())
        yield "else:"
        yield from indent(self.else_.show())


class StmtIfDead(Stmt):
    cond = Field(Expr)
    body = Field(Block)

    def show(self):
        yield "$if {}:".format(self.cond.show(None))
        yield from indent(self.body.show())


class StmtJunk(Stmt):
    body = Field(Block)

    def show(self):
        yield "$junk:"
        yield from indent(self.body.show())


class IfItem(Node):
    cond = Field(Expr)
    body = Field(Block)


class StmtIf(Stmt):
    items = ListField(IfItem)
    else_ = MaybeField(Block)

    def show(self):
        for idx, item in enumerate(self.items):
            yield "{} {}:".format('if' if idx == 0 else 'elif', item.cond.show(None))
            yield from indent(item.body.show())
        if self.else_:
            yield "else:"
            yield from indent(self.else_.show())


class StmtLoop(Stmt):
    body = Field(Block)
    else_ = MaybeField(Block, volatile=True)

    def show(self):
        yield "$loop:"
        yield from indent(self.body.show())
        yield "else:"
        yield from indent(self.else_.show())


class StmtWhileRaw(Stmt):
    expr = Field(Expr)
    body = Field(Block)

    def show(self):
        yield "$while {}:".format(self.expr.show(None))
        yield from indent(self.body.show())


class StmtWhile(Stmt):
    expr = Field(Expr)
    body = Field(Block)
    else_ = MaybeField(Block)

    def show(self):
        yield "while {}:".format(self.expr.show(None))
        yield from indent(self.body.show())
        if self.else_ is not None:
            yield "else:"
            yield from indent(self.else_.show())


class StmtForRaw(Stmt):
    expr = Field(Expr)
    dst = Field(Expr)
    body = Field(Block)

    def show(self):
        yield "$for {} in {}:".format(self.dst.show(None), self.expr.show(None))
        yield from indent(self.body.show())


class StmtForTop(Stmt):
    expr = Field(Expr)
    dst = Field(Expr)
    body = Field(Block)

    def show(self):
        yield "$top {} in {}:".format(self.dst.show(None), self.expr.show(None))
        yield from indent(self.body.show())


class StmtFor(Stmt):
    expr = Field(Expr)
    dst = Field(Expr)
    body = Field(Block)
    else_ = MaybeField(Block)

    def show(self):
        yield "for {} in {}:".format(self.dst.show(None), self.expr.show(None))
        yield from indent(self.body.show())
        if self.else_ is not None:
            yield "else:"
            yield from indent(self.else_.show())


class StmtFinally(Stmt):
    try_ = Field(Block)
    finally_  = Field(Block)

    def show(self):
        yield "try:"
        yield from indent(self.try_.show())
        yield "finally:"
        yield from indent(self.finally_.show())


class ExceptClause(Node):
    expr = Field(Expr)
    dst = MaybeField(Expr)
    body = Field(Block)

    def show(self):
        if self.dst is None:
            yield 'except {}:'.format(self.expr.show(None))
        else:
            # TODO as
            yield 'except {}, {}:'.format(self.expr.show(None), self.dst.show(None))
        yield from indent(self.body.show())


class StmtExcept(Stmt):
    try_ = Field(Block)
    items = ListField(ExceptClause)
    any = MaybeField(Block)
    else_ = MaybeField(Block, volatile=True)

    def show(self):
        yield "try:"
        yield from indent(self.try_.show())
        for item in self.items:
            yield from item.show()
        if self.any is not None:
            yield "except:"
            yield from indent(self.any.show())
        if self.else_ is not None:
            yield "else:"
            yield from indent(self.else_.show())


class StmtExceptDead(Stmt):
    try_ = Field(Block)
    items = ListField(ExceptClause)
    any = MaybeField(Block)

    def show(self):
        yield "$trydead:"
        yield from indent(self.try_.show())
        for item in self.items:
            yield from item.show()
        if self.any is not None:
            yield "except:"
            yield from indent(self.any.show())


class StmtBreak(Stmt):
    def show(self):
        yield 'break'


class StmtContinue(Stmt):
    def show(self):
        yield 'continue'


class StmtFinalContinue(Stmt):
    def show(self):
        yield '$finalcontinue'


class StmtAccess(Stmt):
    name = Field(str)
    mode = Field(int)

    def __init__(self, name, mode):
        if mode & ~0o666 or not mode:
            raise PythonError("funny access mode")
        super().__init__(name, mode)

    def show(self):
        chunks = []
        for idx, name in enumerate(['public', 'protected', 'private']):
            acc = self.mode >> idx * 3 & 6
            if acc == 2:
                chunks.append(name + " write")
            elif acc == 4:
                chunks.append(name + " read")
            elif acc == 6:
                chunks.append(name)
        yield 'access {}: {}'.format(self.name, ', '.join(chunks))


class StmtArgs(Stmt):
    args = Field(FunArgs)

    def show(self):
        yield "$args {}".format(self.args.show())


class StmtClass(Stmt):
    deco = ListField(Expr)
    name = Field(str)
    args = Field(CallArgs)
    body = Field(Block)

    def show(self):
        for d in self.deco:
            yield '@{}'.format(d.show(None))
        if self.args.args:
            yield 'class {}({}):'.format(
                self.name,
                self.args.show()
            )
        else:
            yield 'class {}:'.format(self.name)
        yield from indent(self.body.show())


class StmtEndClass(Stmt):
    def show(self):
        yield '$endclass'


class StmtReturnClass(Stmt):
    def show(self):
        yield '$returnclass'


class StmtStartClass(Stmt):
    def show(self):
        yield '$startclass'


class StmtDef(Stmt):
    deco = ListField(Expr)
    name = Field(str)
    args = Field(FunArgs)
    body = Field(Block)

    def show(self):
        for d in self.deco:
            yield '@{}'.format(d.show(None))
        yield 'def {}({}){}:'.format(
            self.name,
            self.args.show(),
            ' -> {}'.format(self.args.ann['return'].show(None)) if 'return' in self.args.ann else '',
        )
        yield from indent(self.body.show())

class StmtWith(Stmt):
    expr = Field(Expr)
    dst = MaybeField(Expr)
    body = Field(Block)

    def show(self):
        if self.dst:
            yield "with {} as {}:".format(self.expr.show(None), self.dst.show(None))
        else:
            yield "with {}:".format(self.expr.show(None))
        yield from indent(self.body.show())
