from envy.format.marshal import MarshalCode

from .expr import from_marshal

from enum import Enum, IntEnum


class CodeType(Enum):
    """There are 9 kinds of code objects in Python.

    The most basic division is between modules, functions, and classes.

    Modules are the top-level code objects.  They are executed with globals
    equal to locals, have no parameters, return None, and are not optimized.
    They are easily recognised by being the top level.  They also always have
    a name of '<module>'.

    Classes are executed with an arbitrary object as locals, and are not
    optimized.  They are passed to MAKE_FUNCTION, and then to __build_class__.

    Functions have a dedicated local namespance, and are usually optimized
    (always in py3k).  They are passed to MAKE_FUNCTION.  They come in several
    subkinds.

    A generator is a function that has 'generator' set in flags.  As opposed
    to a normal function, it can use the yield expression.

    A genexp is a generator created from a generator expression.  It can be
    recognised by name equal to '<genexp>'.

    Likewise, list/set/dict comprehensions are compiled to functions (in py3k
    only).  They are named '<listcomp>', '<dictcomp>', or '<setcomp>'.

    Finally, lambdas are functions compiled from a lambda expression.  They
    have name equal to '<lambda>'.

    If one is sufficiently evil, it's also perfectly possible to make lambdas
    or comprehensions with yield expressions, thus turning them into
    generators.  This is godawfully ugly, but doesn't actually cause any
    problems for decompilation.

    If names are intact, all these types except function vs class can be
    recognised just by looking at the code object properties.

    The only reliable way to tell a class from a function in py2 is by looking
    whether the parent will pass it to __build_class__.  In py3k, optimization
    could be used instead.

    In the absence of names, it's trivial to tell apart module vs function/class
    vs generator only.  In such case, genexps and comprehensions can be
    recognized by whether they are immediately called after creation with
    result of GET_ITER as an argument.  However, there's no general way to tell
    lambdas apart from functions - a lambda cannot have complex code flow, while
    a function can only be transformed in limitted ways (ie. decorators) before
    being stored to a variable.

    The exact type of comprehension or genexp can be determined by looking
    at the source of the returned value.
    """
    module = ()

    class_ = ()

    function = ()
    lambda_ = ()
    listcomp = ()
    dictcomp = ()
    setcomp = ()
    genexp = ()


class CodeFlag(IntEnum):
    optimized = 1 << 0
    newlocals = 1 << 1
    varargs = 1 << 2
    varkeywords = 1 << 3
    nested = 1 << 4
    generator = 1 << 5
    nofree = 1 << 6
    # future flags
    future_generator = 1 << 12
    future_division = 1 << 13
    future_absolute_import = 1 << 14
    future_with_statement = 1 << 15
    future_print_function = 1 << 16
    future_unicode_literals = 1 << 17
    future_barry_as_flufl = 1 << 18


class Code:
    __slots__ = (
        'version',

        'name',
        'filename',

        'flags',

        'varnames',

        'args',
        'kwargs',
        'varargs',
        'varkw',

        'freevars',
        'cellvars',

        'stacksize',
        'consts',
        'names',

        # XXX
        'code',
        'firstlineno',
        'lnotab',
    )

    def __init__(self, obj, version):
        if not isinstance(obj, MarshalCode):
            raise PythonError("code expected")
        self.version = version
        # name & filename
        self.name = obj.name
        self.filename = obj.filename
        # flags
        reflags = 0
        self.flags = set()
        for flag in CodeFlag:
            if obj.flags & flag:
                self.flags.add(flag)
                reflags |= flag
        if reflags != obj.flags:
            raise PythonError("Unk flags {:x}".format(obj.flags & ~reflags))
        # varnames
        self.varnames = obj.varnames
        if obj.nlocals != len(obj.varnames):
            raise PythonError("Strange nlocals")
        # args
        if obj.argcount + obj.kwonlyargcount > obj.nlocals:
            raise PythonError("More args than locals")
        argidx = 0
        self.args = self.varnames[argidx:argidx + obj.argcount]
        argidx += obj.argcount
        self.kwargs = self.varnames[argidx:argidx + obj.kwonlyargcount]
        argidx += obj.kwonlyargcount
        if CodeFlag.varargs in self.flags:
            if argidx == obj.nlocals:
                raise PythonError("More args than locals")
            self.varargs = self.varnames[argidx]
            argidx += 1
        else:
            self.varargs = None
        if CodeFlag.varkeywords in self.flags:
            if argidx == obj.nlocals:
                raise PythonError("More args than locals")
            self.varkw = self.varnames[argidx]
            argidx += 1
        else:
            self.varkw = None
        # freevars & cellvars
        self.freevars = obj.freevars
        self.cellvars = obj.cellvars
        # stacksize
        self.stacksize = obj.stacksize
        # consts
        self.consts = []
        for const in obj.consts:
            if isinstance(const, MarshalCode):
                self.consts.append(Code(const, version))
            else:
                self.consts.append(from_marshal(const))
        # names
        self.names = obj.names
        # XXX
        self.code = obj.code
        self.firstlineno = obj.firstlineno
        self.lnotab = obj.lnotab
        # XXX code
        # XXX line numbers

    def show(self, level):
        res = []
        res.append('name: {} from {}'.format(self.name, self.filename))
        res.append('flags: {}'.format(', '.join(flag.name for flag in self.flags)))
        args = self.args[:]
        if self.varargs is not None:
            args.append('*{}'.format(self.varargs))
        elif self.kwargs:
            args.append('*')
        if self.kwargs:
            args += self.kwargs
        if self.varkw is not None:
            args.append('**{}'.format(self.varkw))
        if args:
            res.append('args: {}'.format(', '.join(args)))
        if self.varnames:
            res.append('vars: {}'.format(', '.join(self.varnames)))
        if self.freevars:
            res.append('freevars: {}'.format(', '.join(self.freevars)))
        if self.cellvars:
            res.append('cellvars: {}'.format(', '.join(self.cellvars)))
        res.append('consts:')
        for idx, const in enumerate(self.consts):
            if isinstance(const, Code):
                res.append('\t{}: {}'.format(idx, const.show(level+2)))
            else:
                res.append('\t{}: {}'.format(idx, const.show(self.version, None)))
        import binascii
        if self.names:
            res.append('names: {}'.format(', '.join(self.names)))
        res.append("code: {} {}".format(self.stacksize, binascii.hexlify(self.code).decode('ascii')))
        res.append("line: {} {}".format(self.firstlineno, binascii.hexlify(self.lnotab).decode('ascii')))
        return 'CODE\n{}'.format(
            ''.join(
                '{}{}\n'.format(
                    '\t' * (level + 1),
                    line
                )
                for line in res
            )
        )
