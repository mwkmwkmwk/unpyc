from envy.show import indent

class Block:
    __slots__ = 'stmts',

    def __init__(self, stmts):
        self.stmts = []

    def show(self):
        for stmt in self.stmts:
            yield from stmt.show()


class Stmt:
    __slots__ = 'version',

    def __init__(self, version):
        self.version = version


class StmtReturn(Stmt):
    __slots__ = 'val',

    def __init__(self, version, val):
        super().__init__(version)
        self.val = val

    def show(self):
        yield "return {}".format(self.val.show(None))


class StmtPrint(Stmt):
    __slots__ = 'vals', 'nl'

    def __init__(self, version, vals, nl=True):
        super().__init__(version)
        self.vals = vals
        self.nl = nl

    def show(self):
        if self.vals:
            yield "print {}{}".format(', '.join(val.show(None) for val in self.vals), '' if self.nl else ',')
        else:
            assert self.nl
            yield "print"


class StmtSingle(Stmt):
    __slots__ = 'val',

    def __init__(self, version, val):
        super().__init__(version)
        self.val = val

    def show(self):
        yield "$single {}".format(self.val.show(None))


class StmtAssign(Stmt):
    __slots__ = 'dests', 'expr'

    def __init__(self, version, dests, expr):
        super().__init__(version)
        self.dests = dests
        self.expr = expr

    def show(self):
        yield '{}{}'.format(
            ''.join(
                '{} = '.format(dest.show(None))
                for dest in self.dests
            ),
            self.expr.show(None)
        )


class StmtDel(Stmt):
    __slots__ = 'val',

    def __init__(self, version, val):
        super().__init__(version)
        self.val = val

    def show(self):
        yield "del {}".format(self.val.show(None))


class StmtRaise(Stmt):
    __slots__ = 'cls', 'val'

    def __init__(self, version, cls, val=None):
        super().__init__(version)
        self.cls = cls
        self.val = val

    def show(self):
        if self.val is None:
            yield "raise {}".format(self.cls.show(None))
        else:
            yield "raise {}, {}".format(self.cls.show(None), self.val.show(None))


class StmtImport(Stmt):
    __slots__ = 'name',

    def __init__(self, version, name):
        super().__init__(version)
        self.name = name

    def show(self):
        yield "import {}".format(self.name)


class StmtFromImport(Stmt):
    __slots__ = 'name', 'items'

    def __init__(self, version, name, items):
        super().__init__(version)
        self.name = name
        self.items = items

    def show(self):
        yield "from {} import {}".format(
            self.name,
            ', '.join(self.items)
        )


class StmtExec(Stmt):
    __slots__ = 'code', 'globals', 'locals'

    def __init__(self, version, code, globals=None, locals=None):
        super().__init__(version)
        self.code = code
        self.globals = globals
        self.locals = locals

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


class StmtIf(Stmt):
    __slots__ = 'items', 'else_'

    def __init__(self, items, else_):
        self.items = items
        self.else_ = else_

    def show(self):
        for idx, (expr, block) in enumerate(self.items):
            yield "{} {}:".format('if' if idx == 0 else 'elif', expr.show(None))
            yield from indent(block.show())
        yield "else:"
        yield from indent(self.else_.show())


class StmtLoop(Stmt):
    __slots__ = 'body'

    def __init__(self, body):
        self.body = body

    def show(self):
        yield "$loop:"
        yield from indent(self.body.show())


class StmtWhile(Stmt):
    __slots__ = 'expr', 'body'

    def __init__(self, expr, body):
        self.expr = expr
        self.body = body

    def show(self):
        yield "$while {}:".format(self.expr.show(None))
        yield from indent(self.body.show())


class StmtFor(Stmt):
    __slots__ = 'expr', 'dst', 'body'

    def __init__(self, expr, dst, body):
        self.expr = expr
        self.dst = dst
        self.body = body

    def show(self):
        yield "$for {} in {}:".format(self.dst.show(None), self.expr.show(None))
        yield from indent(self.body.show())


class StmtFinally(Stmt):
    __slots__ = 'try_', 'finally_'

    def __init__(self, try_, finally_):
        self.try_ = try_
        self.finally_ = finally_

    def show(self):
        yield "try:"
        yield from indent(self.try_.show())
        yield "finally:"
        yield from indent(self.finally_.show())


class StmtBreak(Stmt):
    __slots__ = ()

    def show(self):
        yield 'break'
