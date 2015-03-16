from collections import namedtuple

from .helpers import PythonError
from .expr import Expr, ExprNone, CmpOp, ExprTuple, ExprString

Flow = namedtuple('Flow', ['src', 'dst'])

OPCODES = {}

class OpcodeMeta(type):
    def __new__(cls, name, bases, namespace):
        if '__slots__' not in namespace:
            namespace['__slots__'] = ()
        return super(__class__, cls).__new__(cls, name, bases, namespace)

    def __init__(self, name, bases, namespace):
        super().__init__(name, bases, namespace)
        if 'code' in namespace:
            OPCODES.setdefault(self.code, []).append(self)


class Opcode(metaclass=OpcodeMeta):
    __slots__ = 'pos', 'nextpos', 'version', 'outflow', 'inflow'
    end = False
    flag = None

    def __init__(self, bytecode, pos):
        self.pos = pos
        self.outflow = []
        self.inflow = []
        self.version = bytecode.version
        self.read_params(bytecode)
        self.nextpos = bytecode.pos

    def read_params(self, bytecode):
        pass

    def __str__(self):
        params = self.print_params()
        if params:
            pstr = "\t{}".format(params)
        else:
            pstr = ''
        if self.inflow:
            mark = self.pos
        else:
            mark = ''
        return "{}\t{}{}".format(mark, self.name, pstr)

    def print_params(self):
        return None

    @classmethod
    def version_ok(cls, version):
        if cls.flag is None:
            return True
        elif cls.flag.startswith('!'):
            return not getattr(version, cls.flag[1:])
        else:
            return getattr(version, cls.flag)


class OpcodeParamNum(Opcode):
    __slots__ = 'param',

    def read_params(self, bytecode):
        self.param = bytecode.word()

    def print_params(self):
        return str(self.param)


class OpcodeParamAbs(Opcode):
    __slots__ = 'flow',

    def read_params(self, bytecode):
        target = bytecode.word()
        self.flow = Flow(self.pos, target)
        self.outflow.append(target)

    def print_params(self):
        return str(self.flow.dst)


class OpcodeParamRel(Opcode):
    __slots__ = 'flow',

    def read_params(self, bytecode):
        diff = bytecode.word()
        # importantly, bytecode.pos is *end* of the insn
        target = bytecode.pos + diff
        self.flow = Flow(self.pos, target)
        self.outflow.append(target)

    def print_params(self):
        return str(self.flow.dst)


class OpcodeParamName(Opcode):
    __slots__ = 'param',

    def read_params(self, bytecode):
        idx = bytecode.word()
        if idx not in range(len(bytecode.names)):
            raise PythonError("name index out of range")
        self.param = bytecode.names[idx]

    def print_params(self):
        return self.param


# TODO fix this
OpcodeParamFast = OpcodeParamNum


# opcodes start here

class OpcodePopTop(Opcode):
    """$pop

    Used for:

    - from x import y [pops x afterwards]
    - chained comparisons
    - and/or operators
    - if statements
    - while statements
    - try statement: except clause
    """
    code = 1
    name = 'POP_TOP'


class OpcodeRotTwo(Opcode):
    """a, b = b, a

    Used for:

    - dict builder
    - chained comparisons
    """
    code = 2
    name = 'ROT_TWO'


class OpcodeRotThree(Opcode):
    """Used for:

    - chained comparisons
    """
    code = 3
    name = 'ROT_THREE'

class OpcodeDupTop(Opcode):
    """$push($top)

    Used for:

    - multiple assignment statements (a = b = c)
    """
    code = 4
    name = 'DUP_TOP'

class OpcodeUnaryPositive(Opcode):
    """$push +$pop"""
    code = 10
    name = 'UNARY_POSITIVE'

class OpcodeUnaryNegative(Opcode):
    """$push -$pop"""
    code = 11
    name = 'UNARY_NEGATIVE'

class OpcodeUnaryNot(Opcode):
    """$push not $pop"""
    code = 12
    name = 'UNARY_NOT'

class OpcodeUnaryConvert(Opcode):
    """$push `$pop`"""
    code = 13
    name = 'UNARY_CONVERT'

class OpcodeUnaryCall(Opcode):
    """$push $pop()

    Used for class defs.
    """
    code = 14
    name = 'UNARY_CALL'
    flag = '!has_new_code'

class OpcodeUnaryInvert(Opcode):
    """$push ~$pop"""
    code = 15
    name = 'UNARY_INVERT'

class OpcodeBinaryPower(Opcode):
    """$push $pop ** $pop"""
    code = 19
    name = 'BINARY_POWER'
    flag = 'has_power'

class OpcodeBinaryMultiply(Opcode):
    """$push $pop * $pop"""
    code = 20
    name = 'BINARY_MULTIPLY'

class OpcodeBinaryDivide(Opcode):
    """$push $pop / $pop"""
    code = 21
    name = 'BINARY_DIVIDE'

class OpcodeBinaryModulo(Opcode):
    """$push $pop % $pop"""
    code = 22
    name = 'BINARY_MODULO'

class OpcodeBinaryAdd(Opcode):
    """$push $pop + $pop"""
    code = 23
    name = 'BINARY_ADD'

class OpcodeBinarySubstract(Opcode):
    """$push $pop - $pop"""
    code = 24
    name = 'BINARY_SUBSTRACT'

class OpcodeBinarySubscr(Opcode):
    """$push $pop[$pop]"""
    code = 25
    name = 'BINARY_SUBSCR'

class OpcodeBinaryCall(Opcode):
    """$push $pop($pop)"""
    code = 26
    name = 'BINARY_CALL'

class OpcodeSliceNN(Opcode):
    """$push $pop[:]"""
    code = 30
    name = 'SLICE_NN'

class OpcodeSliceEN(Opcode):
    """$push $pop[$pop:]"""
    code = 31
    name = 'SLICE_EN'

class OpcodeSliceNE(Opcode):
    """$push $pop[:$pop]"""
    code = 32
    name = 'SLICE_NE'

class OpcodeSliceEE(Opcode):
    """$push $pop[$pop:$pop]"""
    code = 33
    name = 'SLICE_EE'

class OpcodeStoreSliceNN(Opcode):
    """$pop[:] = $pop"""
    code = 40
    name = 'STORE_SLICE_NN'

class OpcodeStoreSliceEN(Opcode):
    """$pop[$pop:] = $pop"""
    code = 41
    name = 'STORE_SLICE_EN'

class OpcodeStoreSliceNE(Opcode):
    """$pop[:$pop] = $pop"""
    code = 42
    name = 'STORE_SLICE_NE'

class OpcodeStoreSliceEE(Opcode):
    """$pop[$pop:$pop] = $pop"""
    code = 43
    name = 'STORE_SLICE_EE'

class OpcodeDeleteSliceNN(Opcode):
    """del $pop[:]"""
    code = 50
    name = 'DELETE_SLICE_NN'

class OpcodeDeleteSliceEN(Opcode):
    """del $pop[$pop:]"""
    code = 51
    name = 'DELETE_SLICE_EN'

class OpcodeDeleteSliceNE(Opcode):
    """del $pop[:$pop]"""
    code = 52
    name = 'DELETE_SLICE_NE'

class OpcodeDeleteSliceEE(Opcode):
    """del $pop[$pop:$pop]"""
    code = 53
    name = 'DELETE_SLICE_EE'

class OpcodeStoreSubscr(Opcode):
    """$pop[$pop] = $pop"""
    code = 60
    name = 'STORE_SUBSCR'

class OpcodeDeleteSubscr(Opcode):
    """del $pop[$pop]"""
    code = 61
    name = 'DELETE_SUBSCR'

class OpcodeBinaryLshift(Opcode):
    """$push $pop << $pop"""
    code = 62
    name = 'BINARY_LSHIFT'

class OpcodeBinaryRshift(Opcode):
    """$push $pop >> $pop"""
    code = 63
    name = 'BINARY_RSHIFT'

class OpcodeBinaryAnd(Opcode):
    """$push $pop & $pop"""
    code = 64
    name = 'BINARY_AND'

class OpcodeBinaryXor(Opcode):
    """$push $pop ^ $pop"""
    code = 65
    name = 'BINARY_XOR'

class OpcodeBinaryOr(Opcode):
    """$push $pop | $pop"""
    code = 66
    name = 'BINARY_OR'

class OpcodePrintExpr(Opcode):
    """print_expr($pop)

    Interactive implicit print statement.  Emitted for a single expression
    statement (in later Pythons, for interactive mode only).  If expr is None,
    does nothing.  Otherwise, prints its repr.
    """
    code = 70
    name = 'PRINT_EXPR'

class OpcodePrintItem(Opcode):
    """print_item($pop)

    Prints a single expression in a print statement.
    """
    code = 71
    name = 'PRINT_ITEM'

class OpcodePrintNewline(Opcode):
    """print_newline()

    Prints a newline in a print statement.
    """
    code = 72
    name = 'PRINT_NEWLINE'

class OpcodeBreakLoop(Opcode):
    """break"""
    code = 80
    name = 'BREAK_LOOP'
    # could be end = True, but not considered as such by compiler

class OpcodeRaiseException(Opcode):
    """raise $pop, $pop"""
    code = 81
    name = 'RAISE_EXCEPTION'
    flag = '!has_new_raise'
    # could be end = True, but not considered as such by compiler

class OpcodeLoadLocals(Opcode):
    """$push($locals)

    Used at the end of class-building function.
    """
    code = 82
    name = 'LOAD_LOCALS'

class OpcodeReturnValue(Opcode):
    """return $pop"""
    code = 83
    name = 'RETURN_VALUE'
    # could be end = True, but not considered as such by compiler

# TODO: LOAD_GLOBALS - appears unused...

class OpcodeExecStmt(Opcode):
    """exec $pop in $pop, $pop"""
    code = 85
    name = 'EXEC_STMT'

class OpcodeBuildFunction(Opcode):
    """$push function($pop)"""
    code = 86
    name = 'BUILD_FUNCTION'
    flag = '!has_new_code'

class OpcodePopBlock(Opcode):
    code = 87
    name = 'POP_BLOCK'

class OpcodeEndFinally(Opcode):
    code = 88
    name = 'END_FINALLY'

class OpcodeBuildClass(Opcode):
    """$push class($pop, $pop, $pop) - args are name, bases, namespace"""
    code = 89
    name = 'BUILD_CLASS'


class OpcodeStoreName(OpcodeParamName):
    """name = $pop"""
    code = 90
    name = "STORE_NAME"


class OpcodeDeleteName(OpcodeParamName):
    """del name"""
    code = 91
    name = "DELETE_NAME"


class OpcodeUnpackTuple(OpcodeParamNum):
    """$push, $push, $push, [... times arg] = $pop"""
    code = 92
    name = "UNPACK_TUPLE"

    # TODO version_ok


class OpcodeUnpackList(OpcodeParamNum):
    """[$push, $push, $push, [... times arg]] = $args"""
    code = 93
    name = "UNPACK_LIST"

    # TODO version_ok


class OpcodeUnpackArg(OpcodeParamNum):
    """$push, $push, $push, [... times arg] = $args"""
    code = 94
    name = "UNPACK_ARG"

    # TODO version_ok


class OpcodeStoreAttr(OpcodeParamName):
    """$pop.name = $pop"""
    code = 95
    name = "STORE_ATTR"


class OpcodeDeleteAttr(OpcodeParamName):
    """del $pop.name"""
    code = 96
    name = "DELETE_ATTR"


class OpcodeStoreGlobal(OpcodeParamName):
    """$global name = $pop"""
    code = 97
    name = "STORE_GLOBAL"


class OpcodeDeleteGlobal(OpcodeParamName):
    """del $global name"""
    code = 98
    name = "DELETE_GLOBAL"


class OpcodeUnpackVararg(OpcodeParamNum):
    """$push, $push, $push, [... times arg], *$push = $args"""
    code = 99
    name = "UNPACK_VARARG"

    # TODO version_ok


class OpcodeLoadConst(Opcode):
    """$push(const)"""
    __slots__ = 'const', 'idx'
    code = 100
    name = 'LOAD_CONST'

    def read_params(self, bytecode):
        from .code import Code
        self.const, self.idx = bytecode.get_const((Expr, Code))

    def print_params(self):
        from .code import Code
        if isinstance(self.const, Expr):
            return self.const.show(None)
        elif isinstance(self.const, Code):
            return "<code {}>".format(self.idx)
        else:
            raise TypeError("unknown const")


class OpcodeLoadName(OpcodeParamName):
    """$push(name)"""
    code = 101
    name = "LOAD_NAME"


class OpcodeBuildTuple(OpcodeParamNum):
    """$push(($pop, $pop, $pop, [... times arg]))"""
    code = 102
    name = "BUILD_TUPLE"


class OpcodeBuildList(OpcodeParamNum):
    """$push([$pop, $pop, $pop, [... times arg]])"""
    code = 103
    name = "BUILD_LIST"


class OpcodeBuildMap(OpcodeParamNum):
    # TODO: validate param
    """$push({}) - param has to be 0"""
    code = 104
    name = "BUILD_MAP"


class OpcodeLoadAttr(OpcodeParamName):
    """$push($pop.name)"""
    code = 105
    name = "LOAD_ATTR"


class OpcodeCompareOp(Opcode):
    __slots__ = 'mode',
    code = 106
    name = "COMPARE_OP"

    def read_params(self, bytecode):
        try:
            self.mode = CmpOp(bytecode.word())
        except ValueError:
            raise PythonError("invalid cmp op")

    def print_params(self):
        return self.mode.name


class OpcodeImportName(OpcodeParamName):
    """$push(__import__("name"))"""
    code = 107
    name = "IMPORT_NAME"


class OpcodeImportFrom(OpcodeParamName):
    """name = $top.name"""
    code = 108
    name = "IMPORT_FROM"


class OpcodeAccessMode(OpcodeParamName):
    code = 109
    name = "ACCESS_MODE"
    flag = 'has_access'


class OpcodeJumpForward(OpcodeParamRel):
    code = 110
    name = 'JUMP_FORWARD'
    end = True

class OpcodeJumpIfFalse(OpcodeParamRel):
    code = 111
    name = 'JUMP_IF_FALSE'

class OpcodeJumpIfTrue(OpcodeParamRel):
    code = 112
    name = 'JUMP_IF_TRUE'

class OpcodeJumpAbsolute(OpcodeParamAbs):
    code = 113
    name = 'JUMP_ABSOLUTE'

class OpcodeForLoop(OpcodeParamRel):
    code = 114
    name = 'FOR_LOOP'

# TODO: LOAD_LOCAL - appears unused...


class OpcodeLoadGlobal(OpcodeParamName):
    """$push($global name)"""
    code = 116
    name = "LOAD_GLOBAL"

class OpcodeSetFuncArgs(OpcodeParamNum):
    code = 117
    name = "SET_FUNC_ARGS"
    flag = 'has_def_args'


class OpcodeSetupLoop(OpcodeParamRel):
    code = 120
    name = 'SETUP_LOOP'


class OpcodeSetupExcept(OpcodeParamRel):
    code = 121
    name = 'SETUP_EXCEPT'


class OpcodeSetupFinally(OpcodeParamRel):
    code = 122
    name = 'SETUP_FINALLY'


class OpcodeReserveFast(Opcode):
    """Prepares fast slots. Arg is a const: dict or None."""
    __slots__ = 'names',
    code = 123
    name = 'RESERVE_FAST'
    flag = '!has_new_code'

    def read_params(self, bytecode):
        # TODO
        if bytecode.version.consts_is_list:
            from .code import CodeDict
            const, _ = bytecode.get_const((CodeDict, ExprNone))
            if isinstance(const, CodeDict):
                self.names = const.names
            elif isinstance(const, ExprNone):
                self.names = []
            else:
                assert False
        else:
            const, _ = bytecode.get_const((ExprTuple, ExprNone))
            if isinstance(const, ExprTuple):
                self.names = []
                for name in const.exprs:
                    if not isinstance(name, ExprString):
                        raise PythonError("funny var name")
                    self.names.append(name.val.decode('ascii'))
            else:
                self.names = None

    def print_params(self):
        if self.names is None:
            return 'None'
        return ', '.join(self.names)

    # TODO version_ok


class OpcodeLoadFast(OpcodeParamFast):
    code = 124
    name = "LOAD_FAST"

    # TODO version_ok


class OpcodeStoreFast(OpcodeParamFast):
    code = 125
    name = "STORE_FAST"

    # TODO version_ok


class OpcodeDeleteFast(OpcodeParamFast):
    code = 126
    name = "DELETE_FAST"

    # TODO version_ok


class OpcodeSetLineno(OpcodeParamNum):
    code = 127
    name = "SET_LINENO"


class OpcodeRaiseVarargs(OpcodeParamNum):
    code = 130
    name = "RAISE_VARARGS"
    flag = 'has_new_raise'


class OpcodeCallFunction(Opcode):
    __slots__ = 'args', 'kwargs'
    code = 131
    name = "CALL_FUNCTION"
    flag = 'has_new_code'

    def read_params(self, bytecode):
        param = bytecode.word()
        self.args = param & 0xff
        self.kwargs = param >> 8 & 0xff

    def print_params(self):
        return "{}, {}".format(self.args, self.kwargs)


class OpcodeMakeFunction(OpcodeParamNum):
    code = 132
    name = "MAKE_FUNCTION"
    flag = 'has_new_code'


class OpcodeBuildSlice(OpcodeParamNum):
    code = 133
    name = "BUILD_SLICE"
    flag = 'has_new_slice'


class Bytecode:
    def __init__(self, version, code):
        self.version = version
        self.code = code.rawcode
        self.consts = code.consts
        self.names = code.names
        self.pos = 0
        self.opdict = {}
        self.ops = []
        while self.pos != len(self.code):
            pos = self.pos
            opc = self.byte()
            for cls in OPCODES.get(opc, []):
                if cls.version_ok(version):
                    op = cls(self, pos)
                    break
            else:
                raise PythonError("unknown opcode {}".format(opc))
            self.ops.append(op)
            self.opdict[pos] = op
        for op in self.ops:
            for out in op.outflow:
                if out not in self.opdict:
                    raise PythonError("invalid branch target")
                trg = self.opdict[out]
                trg.inflow.append(op.pos)

    def bytes(self, num):
        new = self.pos + num
        if new > len(self.code):
            raise PythonError("bytecode ends in the middle of an opcode")
        res = self.code[self.pos:new]
        self.pos = new
        return res

    def byte(self):
        return self.bytes(1)[0]

    def word(self):
        return int.from_bytes(self.bytes(2), 'little')

    def get_const(self, cls):
        idx = self.word()
        if idx < 0 or idx >= len(self.consts):
            raise PythonError("Const index out of range")
        res = self.consts[idx]
        if not isinstance(res, cls):
            raise PythonError("Const of type {} expected, got {}".format(cls, type(res)))
        return res, idx


def parse_lnotab(firstlineno, lnotab, codelen):
    if len(lnotab) % 2:
        raise PythonError("lnotab length not divisible by 2")
    lit = iter(lnotab)
    res = []
    prev_addr = None
    cur_addr = 0
    cur_line = firstlineno
    for addr_inc, line_inc in zip(lit, lit):
        if addr_inc:
            if prev_addr is None:
                prev_addr = cur_addr
            cur_addr += addr_inc
        if line_inc:
            if prev_addr is not None:
                res.append([cur_line, prev_addr, cur_addr])
                prev_addr = None
            cur_line += line_inc
    if prev_addr is None:
        prev_addr = cur_addr
    res.append([cur_line, prev_addr, codelen])
    return res
