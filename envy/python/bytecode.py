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

def _opcode(opc, flag=None):
    def inner(cls):
        OPCODES.setdefault(opc, []).append((cls, flag))
        return cls
    return inner


class Opcode(metaclass=OpcodeMeta):
    __slots__ = 'pos', 'ext', 'nextpos', 'version', 'outflow', 'inflow'

    def __init__(self, bytecode, pos, ext):
        self.pos = pos
        self.ext = ext or 0
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


class OpcodeParamNum(Opcode):
    __slots__ = 'param',

    def read_params(self, bytecode):
        self.param = bytecode.word(self.ext)

    def print_params(self):
        return str(self.param)


class OpcodeParamAbs(Opcode):
    __slots__ = 'flow',

    def read_params(self, bytecode):
        target = bytecode.word(self.ext)
        self.flow = Flow(self.pos, target)
        self.outflow.append(target)

    def print_params(self):
        return str(self.flow.dst)


class OpcodeParamRel(Opcode):
    __slots__ = 'flow',

    def read_params(self, bytecode):
        diff = bytecode.word(self.ext)
        # importantly, bytecode.pos is *end* of the insn
        target = bytecode.pos + diff
        self.flow = Flow(self.pos, target)
        self.outflow.append(target)

    def print_params(self):
        return str(self.flow.dst)


class OpcodeParamName(Opcode):
    __slots__ = 'param',

    def read_params(self, bytecode):
        idx = bytecode.word(self.ext)
        if idx not in range(len(bytecode.names)):
            raise PythonError("name index out of range")
        self.param = bytecode.names[idx]

    def print_params(self):
        return self.param


# TODO fix this
OpcodeParamFast = OpcodeParamNum


# opcodes start here

@_opcode(1)
class OpcodePopTop(Opcode):
    name = 'POP_TOP'

@_opcode(2)
class OpcodeRotTwo(Opcode):
    name = 'ROT_TWO'

@_opcode(3)
class OpcodeRotThree(Opcode):
    name = 'ROT_THREE'

@_opcode(4)
class OpcodeDupTop(Opcode):
    name = 'DUP_TOP'

@_opcode(5, 'has_rot_four')
class OpcodeRotFour(Opcode):
    name = 'ROT_FOUR'

@_opcode(10)
class OpcodeUnaryPositive(Opcode):
    name = 'UNARY_POSITIVE'

@_opcode(11)
class OpcodeUnaryNegative(Opcode):
    name = 'UNARY_NEGATIVE'

@_opcode(12)
class OpcodeUnaryNot(Opcode):
    name = 'UNARY_NOT'

@_opcode(13, 'has_repr')
class OpcodeUnaryConvert(Opcode):
    name = 'UNARY_CONVERT'

@_opcode(14, '!has_new_code')
class OpcodeUnaryCall(Opcode):
    name = 'UNARY_CALL'

@_opcode(15)
class OpcodeUnaryInvert(Opcode):
    name = 'UNARY_INVERT'

@_opcode(18, 'has_list_append')
class OpcodeListAppend(Opcode):
    name = 'LIST_APPEND'

@_opcode(19, 'has_power')
class OpcodeBinaryPower(Opcode):
    name = 'BINARY_POWER'

@_opcode(20)
class OpcodeBinaryMultiply(Opcode):
    name = 'BINARY_MULTIPLY'

@_opcode(21, 'has_old_divide')
class OpcodeBinaryDivide(Opcode):
    name = 'BINARY_DIVIDE'

@_opcode(22)
class OpcodeBinaryModulo(Opcode):
    name = 'BINARY_MODULO'

@_opcode(23)
class OpcodeBinaryAdd(Opcode):
    name = 'BINARY_ADD'

@_opcode(24)
class OpcodeBinarySubstract(Opcode):
    name = 'BINARY_SUBSTRACT'

@_opcode(25)
class OpcodeBinarySubscr(Opcode):
    name = 'BINARY_SUBSCR'

@_opcode(26, '!has_new_code')
class OpcodeBinaryCall(Opcode):
    name = 'BINARY_CALL'

@_opcode(26, 'has_new_divide')
class OpcodeBinaryFloorDivide(Opcode):
    name = 'BINARY_FLOOR_DIVIDE'

@_opcode(27, 'has_new_divide')
class OpcodeBinaryTrueDivide(Opcode):
    name = 'BINARY_TRUE_DIVIDE'

@_opcode(28, 'has_new_divide')
class OpcodeInplaceFloorDivide(Opcode):
    name = 'INPLACE_FLOOR_DIVIDE'

@_opcode(29, 'has_new_divide')
class OpcodeInplaceTrueDivide(Opcode):
    name = 'INPLACE_TRUE_DIVIDE'

@_opcode(30, 'has_old_slice')
class OpcodeSliceNN(Opcode):
    name = 'SLICE_NN'

@_opcode(31, 'has_old_slice')
class OpcodeSliceEN(Opcode):
    name = 'SLICE_EN'

@_opcode(32, 'has_old_slice')
class OpcodeSliceNE(Opcode):
    name = 'SLICE_NE'

@_opcode(33, 'has_old_slice')
class OpcodeSliceEE(Opcode):
    name = 'SLICE_EE'

@_opcode(40, 'has_old_slice')
class OpcodeStoreSliceNN(Opcode):
    name = 'STORE_SLICE_NN'

@_opcode(41, 'has_old_slice')
class OpcodeStoreSliceEN(Opcode):
    name = 'STORE_SLICE_EN'

@_opcode(42, 'has_old_slice')
class OpcodeStoreSliceNE(Opcode):
    name = 'STORE_SLICE_NE'

@_opcode(43, 'has_old_slice')
class OpcodeStoreSliceEE(Opcode):
    name = 'STORE_SLICE_EE'

@_opcode(50, 'has_old_slice')
class OpcodeDeleteSliceNN(Opcode):
    name = 'DELETE_SLICE_NN'

@_opcode(51, 'has_old_slice')
class OpcodeDeleteSliceEN(Opcode):
    name = 'DELETE_SLICE_EN'

@_opcode(52, 'has_old_slice')
class OpcodeDeleteSliceNE(Opcode):
    name = 'DELETE_SLICE_NE'

@_opcode(53, 'has_old_slice')
class OpcodeDeleteSliceEE(Opcode):
    name = 'DELETE_SLICE_EE'

@_opcode(55, 'has_inplace')
class OpcodeInplaceAdd(Opcode):
    name = 'INPLACE_ADD'

@_opcode(56, 'has_inplace')
class OpcodeInplaceSubstract(Opcode):
    name = 'INPLACE_SUBSTRACT'

@_opcode(57, 'has_inplace')
class OpcodeInplaceMultiply(Opcode):
    name = 'INPLACE_MULTIPLY'

@_opcode(58, ('has_inplace', 'has_old_divide'))
class OpcodeInplaceDivide(Opcode):
    name = 'INPLACE_DIVIDE'

@_opcode(59, 'has_inplace')
class OpcodeInplaceModulo(Opcode):
    name = 'INPLACE_MODULO'

@_opcode(60)
class OpcodeStoreSubscr(Opcode):
    name = 'STORE_SUBSCR'

@_opcode(61)
class OpcodeDeleteSubscr(Opcode):
    name = 'DELETE_SUBSCR'

@_opcode(62)
class OpcodeBinaryLshift(Opcode):
    name = 'BINARY_LSHIFT'

@_opcode(63)
class OpcodeBinaryRshift(Opcode):
    name = 'BINARY_RSHIFT'

@_opcode(64)
class OpcodeBinaryAnd(Opcode):
    name = 'BINARY_AND'

@_opcode(65)
class OpcodeBinaryXor(Opcode):
    name = 'BINARY_XOR'

@_opcode(66)
class OpcodeBinaryOr(Opcode):
    name = 'BINARY_OR'

@_opcode(67, 'has_inplace')
class OpcodeInplacePower(Opcode):
    name = 'INPLACE_POWER'

@_opcode(68, 'has_iter')
class OpcodeGetIter(Opcode):
    name = 'GET_ITER'

@_opcode(70)
class OpcodePrintExpr(Opcode):
    name = 'PRINT_EXPR'

@_opcode(71, 'has_print')
class OpcodePrintItem(Opcode):
    name = 'PRINT_ITEM'

@_opcode(72, 'has_print')
class OpcodePrintNewline(Opcode):
    name = 'PRINT_NEWLINE'

@_opcode(73, 'has_print_to')
class OpcodePrintItemTo(Opcode):
    name = 'PRINT_ITEM_TO'

@_opcode(74, 'has_print_to')
class OpcodePrintNewlineTo(Opcode):
    name = 'PRINT_NEWLINE_TO'

@_opcode(75, 'has_inplace')
class OpcodeInplaceLshift(Opcode):
    name = 'INPLACE_LSHIFT'

@_opcode(76, 'has_inplace')
class OpcodeInplaceRshift(Opcode):
    name = 'INPLACE_RSHIFT'

@_opcode(77, 'has_inplace')
class OpcodeInplaceAnd(Opcode):
    name = 'INPLACE_AND'

@_opcode(78, 'has_inplace')
class OpcodeInplaceXor(Opcode):
    name = 'INPLACE_XOR'

@_opcode(79, 'has_inplace')
class OpcodeInplaceOr(Opcode):
    name = 'INPLACE_OR'

@_opcode(80)
class OpcodeBreakLoop(Opcode):
    name = 'BREAK_LOOP'

@_opcode(81, '!has_new_raise')
class OpcodeRaiseException(Opcode):
    name = 'RAISE_EXCEPTION'

@_opcode(82)
class OpcodeLoadLocals(Opcode):
    name = 'LOAD_LOCALS'

@_opcode(83)
class OpcodeReturnValue(Opcode):
    name = 'RETURN_VALUE'

# TODO: LOAD_GLOBALS - appears unused...

@_opcode(84, 'has_import_star')
class OpcodeImportStar(Opcode):
    name = 'IMPORT_STAR'

@_opcode(85, 'has_exec')
class OpcodeExecStmt(Opcode):
    name = 'EXEC_STMT'

@_opcode(86, '!has_new_code')
class OpcodeBuildFunction(Opcode):
    name = 'BUILD_FUNCTION'

@_opcode(86, 'has_yield_stmt')
class OpcodeYieldValue(Opcode):
    name = 'YIELD_VALUE'

@_opcode(87)
class OpcodePopBlock(Opcode):
    name = 'POP_BLOCK'

@_opcode(88)
class OpcodeEndFinally(Opcode):
    name = 'END_FINALLY'

@_opcode(89)
class OpcodeBuildClass(Opcode):
    name = 'BUILD_CLASS'


# opcodes have an argument from here on

@_opcode(90)
class OpcodeStoreName(OpcodeParamName):
    name = "STORE_NAME"

@_opcode(91)
class OpcodeDeleteName(OpcodeParamName):
    name = "DELETE_NAME"

@_opcode(92, '!has_unpack_sequence')
class OpcodeUnpackTuple(OpcodeParamNum):
    name = "UNPACK_TUPLE"

@_opcode(92, 'has_unpack_sequence')
class OpcodeUnpackSequence(OpcodeParamNum):
    name = "UNPACK_SEQUENCE"

@_opcode(93, '!has_unpack_sequence')
class OpcodeUnpackList(OpcodeParamNum):
    name = "UNPACK_LIST"

@_opcode(93, 'has_iter')
class OpcodeForIter(OpcodeParamRel):
    name = 'FOR_ITER'

@_opcode(94, '!has_new_code')
class OpcodeUnpackArg(OpcodeParamNum):
    name = "UNPACK_ARG"

@_opcode(95)
class OpcodeStoreAttr(OpcodeParamName):
    name = "STORE_ATTR"

@_opcode(96)
class OpcodeDeleteAttr(OpcodeParamName):
    name = "DELETE_ATTR"

@_opcode(97)
class OpcodeStoreGlobal(OpcodeParamName):
    name = "STORE_GLOBAL"

@_opcode(98)
class OpcodeDeleteGlobal(OpcodeParamName):
    name = "DELETE_GLOBAL"

@_opcode(99, '!has_new_code')
class OpcodeUnpackVararg(OpcodeParamNum):
    name = "UNPACK_VARARG"

@_opcode(99, 'has_dup_topx')
class OpcodeDupTopX(OpcodeParamNum):
    name = "DUP_TOPX"


@_opcode(100)
class OpcodeLoadConst(Opcode):
    """$push(const)"""
    __slots__ = 'const', 'idx'
    name = 'LOAD_CONST'

    def read_params(self, bytecode):
        from .code import Code
        self.const, self.idx = bytecode.get_const((Expr, Code), self.ext)

    def print_params(self):
        from .code import Code
        if isinstance(self.const, Expr):
            return self.const.show(None)
        elif isinstance(self.const, Code):
            return "<code {}>".format(self.idx)
        else:
            raise TypeError("unknown const")


@_opcode(101)
class OpcodeLoadName(OpcodeParamName):
    name = "LOAD_NAME"

@_opcode(102)
class OpcodeBuildTuple(OpcodeParamNum):
    name = "BUILD_TUPLE"

@_opcode(103)
class OpcodeBuildList(OpcodeParamNum):
    name = "BUILD_LIST"

@_opcode(104)
class OpcodeBuildMap(OpcodeParamNum):
    name = "BUILD_MAP"

@_opcode(105)
class OpcodeLoadAttr(OpcodeParamName):
    name = "LOAD_ATTR"

@_opcode(106)
class OpcodeCompareOp(Opcode):
    __slots__ = 'mode',
    name = "COMPARE_OP"

    def read_params(self, bytecode):
        try:
            self.mode = CmpOp(bytecode.word(self.ext))
        except ValueError:
            raise PythonError("invalid cmp op")

    def print_params(self):
        return self.mode.name


@_opcode(107)
class OpcodeImportName(OpcodeParamName):
    name = "IMPORT_NAME"

@_opcode(108)
class OpcodeImportFrom(OpcodeParamName):
    name = "IMPORT_FROM"

@_opcode(109, 'has_access')
class OpcodeAccessMode(OpcodeParamName):
    name = "ACCESS_MODE"

@_opcode(110)
class OpcodeJumpForward(OpcodeParamRel):
    name = 'JUMP_FORWARD'

@_opcode(111)
class OpcodeJumpIfFalse(OpcodeParamRel):
    name = 'JUMP_IF_FALSE'

@_opcode(112)
class OpcodeJumpIfTrue(OpcodeParamRel):
    name = 'JUMP_IF_TRUE'

@_opcode(113)
class OpcodeJumpAbsolute(OpcodeParamAbs):
    name = 'JUMP_ABSOLUTE'

@_opcode(114, '!has_iter')
class OpcodeForLoop(OpcodeParamRel):
    name = 'FOR_LOOP'

# TODO: LOAD_LOCAL - appears unused...


@_opcode(116)
class OpcodeLoadGlobal(OpcodeParamName):
    name = "LOAD_GLOBAL"

@_opcode(117, ('has_def_args', '!has_new_code'))
class OpcodeSetFuncArgs(OpcodeParamNum):
    name = "SET_FUNC_ARGS"

@_opcode(119, 'has_new_continue')
class OpcodeContinueLoop(OpcodeParamAbs):
    name = 'CONTINUE_LOOP'


@_opcode(120)
class OpcodeSetupLoop(OpcodeParamRel):
    name = 'SETUP_LOOP'

@_opcode(121)
class OpcodeSetupExcept(OpcodeParamRel):
    name = 'SETUP_EXCEPT'

@_opcode(122)
class OpcodeSetupFinally(OpcodeParamRel):
    name = 'SETUP_FINALLY'


@_opcode(123, '!has_new_code')
class OpcodeReserveFast(Opcode):
    """Prepares fast slots. Arg is a const: dict or None."""
    __slots__ = 'names',
    name = 'RESERVE_FAST'

    def read_params(self, bytecode):
        # TODO
        if bytecode.version.consts_is_list:
            from .code import CodeDict
            const, _ = bytecode.get_const((CodeDict, ExprNone), self.ext)
            if isinstance(const, CodeDict):
                self.names = const.names
            elif isinstance(const, ExprNone):
                self.names = []
            else:
                assert False
        else:
            const, _ = bytecode.get_const((ExprTuple, ExprNone), self.ext)
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


@_opcode(124)
class OpcodeLoadFast(OpcodeParamFast):
    name = "LOAD_FAST"

@_opcode(125)
class OpcodeStoreFast(OpcodeParamFast):
    name = "STORE_FAST"

@_opcode(126)
class OpcodeDeleteFast(OpcodeParamFast):
    name = "DELETE_FAST"

@_opcode(127, 'has_set_lineno')
class OpcodeSetLineno(OpcodeParamNum):
    name = "SET_LINENO"

@_opcode(130, 'has_new_raise')
class OpcodeRaiseVarargs(OpcodeParamNum):
    name = "RAISE_VARARGS"


class OpcodeCallFunctionBase(Opcode):
    __slots__ = 'args', 'kwargs'

    def read_params(self, bytecode):
        param = bytecode.word(self.ext)
        self.args = param & 0xff
        self.kwargs = param >> 8 & 0xff

    def print_params(self):
        return "{}, {}".format(self.args, self.kwargs)


@_opcode(131, 'has_new_code')
class OpcodeCallFunction(OpcodeCallFunctionBase):
    name = "CALL_FUNCTION"

@_opcode(132, 'has_new_code')
class OpcodeMakeFunction(OpcodeParamNum):
    name = "MAKE_FUNCTION"

@_opcode(133, 'has_new_slice')
class OpcodeBuildSlice(OpcodeParamNum):
    name = "BUILD_SLICE"

@_opcode(134, 'has_closure')
class OpcodeMakeClosure(OpcodeParamNum):
    name = "MAKE_CLOSURE"

@_opcode(135, 'has_closure')
class OpcodeLoadClosure(OpcodeParamNum):
    name = "LOAD_CLOSURE"

@_opcode(136, 'has_closure')
class OpcodeLoadDeref(OpcodeParamNum):
    name = "LOAD_DEREF"

@_opcode(137, 'has_closure')
class OpcodeStoreDeref(OpcodeParamNum):
    name = "STORE_DEREF"

@_opcode(140, 'has_var_call')
class OpcodeCallFunctionVar(OpcodeCallFunctionBase):
    name = "CALL_FUNCTION_VAR"

@_opcode(141, 'has_var_call')
class OpcodeCallFunctionKw(OpcodeCallFunctionBase):
    name = "CALL_FUNCTION_KW"

@_opcode(142, 'has_var_call')
class OpcodeCallFunctionVarKw(OpcodeCallFunctionBase):
    name = "CALL_FUNCTION_VAR_KW"

@_opcode(143, 'has_extended_arg')
class ExtendedArg(OpcodeParamNum):
    name = "EXTENDED_ARG"


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
            op = self.get_op(pos, opc, 0)
            if isinstance(op, ExtendedArg):
                opc = self.byte()
                op = self.get_op(pos, opc, op.param)
                if isinstance(op, ExtendedArg):
                    raise PythonError("funny, two EXTENDED_ARG in a row")
            self.ops.append(op)
            self.opdict[pos] = op
        for op in self.ops:
            for out in op.outflow:
                if out not in self.opdict:
                    raise PythonError("invalid branch target")
                trg = self.opdict[out]
                trg.inflow.append(op.pos)

    def get_op(self, pos, opc, ext):
        for cls, flag in OPCODES.get(opc, []):
            if self.version.match(flag):
                return cls(self, pos, ext)
        raise PythonError("unknown opcode {}".format(opc))

    def bytes(self, num):
        new = self.pos + num
        if new > len(self.code):
            raise PythonError("bytecode ends in the middle of an opcode")
        res = self.code[self.pos:new]
        self.pos = new
        return res

    def byte(self):
        return self.bytes(1)[0]

    def word(self, ext):
        return int.from_bytes(self.bytes(2), 'little') | ext << 16

    def get_const(self, cls, ext):
        idx = self.word(ext)
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
