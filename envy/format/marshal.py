import struct
import binascii

from .helpers import read_byte, read_le, read_bytes, FormatError

class MarshalError(FormatError):
    pass


# nodes

class MarshalNode:
    __slots__ = ()

    def print(self, level):
        print(str(self))


class MarshalNull(MarshalNode):
    __slots__ = ()

    def __str__(self):
        return 'NULL'


# singletons

class MarshalNone(MarshalNode):
    __slots__ = ()

    def __str__(self):
        return 'None'


class MarshalBool(MarshalNode):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return str(self.val)


class MarshalStopIter(MarshalNode):
    __slots__ = ()

    def __str__(self):
        return "StopIteration"


class MarshalEllipsis(MarshalNode):
    __slots__ = ()

    def __str__(self):
        return "..."


# primitive types

class MarshalInt(MarshalNode):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return str(self.val)


class MarshalLong(MarshalNode):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return str(self.val) + 'L'


class MarshalFloat(MarshalNode):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return str(self.val)


class MarshalComplex(MarshalNode):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return str(self.val)


class MarshalString(MarshalNode):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return repr(self.val)


class MarshalUnicode(MarshalNode):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return repr(self.val)


# containers

class MarshalTuple(MarshalNode):
    __slots__ = 'val'

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return '({}{})'.format(', '.join(str(v) for v in self.val), ',' if len(self.val) == 1 else '')


# the following 4 shouldn't ever appear in .pyc

class MarshalList(MarshalNode):
    __slots__ = 'val'

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return '[{}]'.format(', '.join(str(v) for v in self.val))


class MarshalDict(MarshalNode):
    __slots__ = 'val'

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return '{{{}}}'.format(', '.join('{}: {}'.format(k, v) for k, v in self.val.items()))


class MarshalSet(MarshalNode):
    __slots__ = 'val'

    def __init__(self, val):
        self.val = val

    def __str__(self):
        if len(self.val) == 0:
            return 'set()'
        return '{{{}}}'.format(', '.join(str(v) for v in self.val))


class MarshalFrozenset(MarshalNode):
    __slots__ = 'val'

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return 'frozenset([{}])'.format(', '.join(str(v) for v in self.val))


# code

class MarshalCode(MarshalNode):
    __slots__ = (
        'argcount',
        'kwonlyargcount',
        'nlocals',
        'stacksize',
        'flags',
        'code',
        'consts',
        'names',
        'varnames',
        'freevars',
        'cellvars',
        'filename',
        'name',
        'firstlineno',
        'lnotab',
    )

    def __str__(self):
        return '<code>'

    def print(self, level):
        print("CODE")
        pref = (level + 1) * '\t'
        print("{}args: {} + {}, locals: {}, stacksize: {}".format(pref, self.argcount, self.kwonlyargcount, self.nlocals, self.stacksize))
        print("{}flags: {:x}".format(pref, self.flags))
        print("{}code: {}".format(pref, binascii.b2a_hex(self.code)))
        print("{}consts:".format(pref))
        for idx, const in enumerate(self.consts):
            print("{}\t{}:".format(pref, idx), end=' ')
            const.print(level+2)
        print("{}names: {}".format(pref, ', '.join(self.names)))
        print("{}varnames: {}".format(pref, ', '.join(self.varnames)))
        print("{}freevars: {}".format(pref, ', '.join(self.freevars)))
        print("{}cellvars: {}".format(pref, ', '.join(self.cellvars)))
        print("{}filename: {}".format(pref, self.filename))
        print("{}name: {}".format(pref, self.name))
        print("{}lines: {} then {}".format(pref, self.firstlineno, binascii.b2a_hex(self.lnotab)))


# reader

def load_none(ctx, flag):
    return MarshalNone()

def load_true(ctx, flag):
    return MarshalBool(True)

def load_false(ctx, flag):
    return MarshalBool(False)

def load_ellipsis(ctx, flag):
    return MarshalEllipsis()

def load_int(ctx, flag):
    return ctx.ref(MarshalInt(ctx.le4s()), flag)

def load_int64(ctx, flag):
    return ctx.ref(MarshalInt(ctx.le8s()), flag)

def load_long(ctx, flag):
    n = ctx.le4s()
    res = 0
    for x in range(abs(n)):
        res |= ctx.le2() << x * 15
    if n < 0:
        res = -res
    if ctx.version.py3k:
        type_ = MarshalInt
    else:
        type_ = MarshalLong
    return ctx.ref(type_(res), flag)

def load_bin_float(ctx, flag):
    res, = struct.unpack('<d', ctx.bytes(8))
    return ctx.ref(MarshalFloat(res), flag)

def load_bin_complex(ctx, flag):
    r, = struct.unpack('<d', ctx.bytes(8))
    i, = struct.unpack('<d', ctx.bytes(8))
    return ctx.ref(MarshalFloat(complex(r, i)), flag)

def load_string(ctx, flag):
    len_ = ctx.le4()
    res = MarshalString(ctx.bytes(len_))
    return ctx.ref(res, flag)

def _load_ascii(ctx, flag, len_):
    s = ctx.bytes(len_)
    res = MarshalUnicode(s.decode('ascii'))
    return ctx.ref(res, flag)

def load_short_ascii(ctx, flag):
    return _load_ascii(ctx, flag, ctx.byte())

def load_ascii(ctx, flag):
    return _load_ascii(ctx, flag, ctx.le4())

def load_unicode(ctx, flag):
    n = ctx.le4()
    b = ctx.bytes(n)
    res = b.decode('utf-8', 'surrogatepass')
    return ctx.ref(MarshalUnicode(res), flag)

def load_interned(ctx, flag):
    if ctx.version.py3k:
        return load_unicode(ctx, flag)
    else:
        return load_string(ctx, True)

def _load_raw_tuple(ctx, flag, len_):
    res = MarshalTuple([])
    ctx.ref(res, flag)
    for x in range(len_):
        res.val.append(ctx.load_object())
    return res

def load_small_tuple(ctx, flag):
    return _load_raw_tuple(ctx, flag, ctx.byte())

def load_tuple(ctx, flag):
    return _load_raw_tuple(ctx, flag, ctx.le4())

def load_code(ctx, flag):
    res = MarshalCode()
    ctx.ref(res, flag)
    res.argcount = ctx.le4()
    if ctx.version.py3k:
        res.kwonlyargcount = ctx.le4()
    else:
        res.kwonlyargcount = 0
    res.nlocals = ctx.le4()
    res.stacksize = ctx.le4()
    res.flags = ctx.le4()
    res.code = ctx.load_bytes()
    res.consts = ctx.load_tuple()
    res.names = ctx.load_str_tuple()
    res.varnames = ctx.load_str_tuple()
    res.freevars = ctx.load_str_tuple()
    res.cellvars = ctx.load_str_tuple()
    res.filename = ctx.load_str()
    res.name = ctx.load_str()
    res.firstlineno = ctx.le4()
    res.lnotab = ctx.load_bytes()
    return res

def load_ref(ctx, flag):
    idx = ctx.le4()
    try:
        return ctx.refs[idx]
    except IndexError:
        raise MarshalError("Invalid reference")


MARSHAL_CODES = {
    # not supported:
    # '0' (NULL)
    # 'S' (StopIteration)
    # 'f', 'x' (string float and complex)
    # '[', '{', '<', '>' (list, dict, set, frozenset)

    ord('N'): load_none,
    ord('T'): load_true,
    ord('F'): load_false,
    ord('.'): load_ellipsis,

    ord('i'): load_int,
    ord('I'): load_int64,
    ord('l'): load_long,
    ord('g'): load_bin_float,
    ord('y'): load_bin_complex,

    ord('s'): load_string,
    ord('u'): load_unicode,
    ord('t'): load_interned,
    ord('z'): load_short_ascii,
    ord('Z'): load_short_ascii, # interned
    ord('a'): load_ascii,
    ord('A'): load_ascii, # interned
    ord('R'): load_ref, # py2k

    ord(')'): load_small_tuple,
    ord('('): load_tuple,

    ord('c'): load_code,
    ord('r'): load_ref,
}

class MarshalContext:
    def __init__(self, fp, version):
        self.fp = fp
        self.version = version
        self.refs = []
        self.level = 0

    def load_object(self):
        code = self.byte()
        if self.version.py3k:
            ref = bool(code & 0x80)
            code &= 0x7f
        else:
            ref = False
        try:
            fun = MARSHAL_CODES[code]
        except KeyError:
            raise MarshalError("marshal type unknown ({!r})".format(bytes([code])))
        return fun(self, ref)

    def load_tuple(self):
        obj = self.load_object()
        if not isinstance(obj, MarshalTuple):
            raise MarshalError("tuple expected, got {}".format(type(obj)))
        return obj.val

    def load_bytes(self):
        obj = self.load_object()
        if not isinstance(obj, MarshalString):
            raise MarshalError("bytes expected, got {}".format(type(obj)))
        return obj.val

    def pass_str(self, obj):
        if self.version.py3k:
            if not isinstance(obj, MarshalUnicode):
                raise MarshalError("string expected, got {}".format(type(obj)))
            return obj.val
        else:
            if not isinstance(obj, MarshalString):
                raise MarshalError("string expected, got {}".format(type(obj)))
            return obj.val.decode('ascii')

    def load_str(self):
        return self.pass_str(self.load_object())

    def load_str_tuple(self):
        obj = self.load_object()
        if not isinstance(obj, MarshalTuple):
            raise MarshalError("tuple expected, got {}".format(type(obj)))
        return [self.pass_str(x) for x in obj.val]

    def le2(self):
        return read_le(self.fp, 2)

    def le4(self):
        return read_le(self.fp, 4)

    def le4s(self):
        return read_le(self.fp, 4, signed=True)

    def le8s(self):
        return read_le(self.fp, 8, signed=True)

    def bytes(self, len_):
        return read_bytes(self.fp, len_)

    def byte(self):
        return read_byte(self.fp)

    def ref(self, obj, flag):
        if flag:
            self.refs.append(obj)
        return obj


def load_marshal(fp, version):
    return MarshalContext(fp, version).load_object()
