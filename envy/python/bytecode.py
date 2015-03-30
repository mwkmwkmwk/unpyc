from collections import namedtuple

from .helpers import PythonError
from .expr import Expr, ExprNone, CmpOp, ExprTuple, ExprString

Flow = namedtuple('Flow', ['src', 'dst'])


# opcode classes

class Opcode:
    __slots__ = 'pos', 'nextpos'

    def __init__(self, pos, nextpos):
        self.pos = pos
        self.nextpos = nextpos

    def __str__(self):
        if hasattr(self, 'read_params'):
            return "{}\t{}".format(self.name, self.print_params())
        else:
            return self.name


class OpcodeParamNum(Opcode):
    __slots__ = 'param',

    def __init__(self, pos, nextpos, param):
        super().__init__(pos, nextpos)
        self.param = param

    def read_params(self, param, bytecode):
        self.param = param

    def print_params(self):
        return str(self.param)


class OpcodeFlow(Opcode):
    __slots__ = 'flow',

    def __init__(self, pos, nextpos, flow):
        super().__init__(pos, nextpos)
        self.flow = flow

    def print_params(self):
        return str(self.flow.dst)


class OpcodeParamAbs(OpcodeFlow):
    __slots__ = ()

    def read_params(self, param, bytecode):
        self.flow = Flow(self.pos, param)


class OpcodeParamRel(OpcodeFlow):
    __slots__ = ()

    def read_params(self, param, bytecode):
        # importantly, bytecode.pos is *end* of the insn
        target = bytecode.pos + param
        self.flow = Flow(self.pos, target)


class OpcodeParamName(Opcode):
    __slots__ = 'param',

    def __init__(self, pos, nextpos, param):
        super().__init__(pos, nextpos)
        self.param = param

    def read_params(self, param, bytecode):
        if param not in range(len(bytecode.names)):
            raise PythonError("name index out of range")
        self.param = bytecode.names[param]

    def print_params(self):
        return self.param


class OpcodeCallFunctionBase(Opcode):
    __slots__ = 'args', 'kwargs'

    def __init__(self, pos, nextpos, args, kwargs):
        super().__init__(pos, nextpos)
        self.args = args
        self.kwargs = kwargs

    def read_params(self, param, bytecode):
        self.args = param & 0xff
        self.kwargs = param >> 8 & 0xff
        if param & ~0xffff:
            raise PythonError("funny call function")

    def print_params(self):
        return "{}, {}".format(self.args, self.kwargs)


class OpcodeMakeFunctionNewBase(Opcode):
    __slots__ = 'args', 'kwargs', 'ann'

    def __init__(self, pos, nextpos, args, kwargs, ann):
        super().__init__(pos, nextpos)
        self.args = args
        self.kwargs = kwargs
        self.ann = ann

    def read_params(self, param, bytecode):
        self.args = param & 0xff
        self.kwargs = param >> 8 & 0xff
        self.ann = param >> 16 & 0x7fff
        if param & ~0x7fffffff:
            raise PythonError("funny make function")

    def print_params(self):
        return "{}, {}, {}".format(self.args, self.kwargs, self.ann)


class OpcodeUnpackExBase(Opcode):
    __slots__ = 'before', 'after'

    def __init__(self, pos, nextpos, before, after):
        super().__init__(pos, nextpos)
        self.before = before
        self.after = after

    def read_params(self, param, bytecode):
        self.before = param & 0xff
        self.after = param >> 8 & 0xff
        if param & ~0xffff:
            raise PythonError("funny unpack ex")

    def print_params(self):
        return "{}, {}".format(self.before, self.after)


class OpcodeLoadConstBase(Opcode):
    __slots__ = 'const', 'idx'

    def __init__(self, pos, nextpos, const, idx):
        super().__init__(pos, nextpos)
        self.const = const
        self.idx = idx

    def read_params(self, param, bytecode):
        from .code import Code
        self.const, self.idx = bytecode.get_const((Expr, Code), param)

    def print_params(self):
        from .code import Code
        if isinstance(self.const, Expr):
            return self.const.show(None)
        elif isinstance(self.const, Code):
            return "<code {}>".format(self.idx)
        else:
            raise TypeError("unknown const")


class OpcodeCompareOpBase(Opcode):
    __slots__ = 'param',

    def __init__(self, pos, nextpos, param):
        super().__init__(pos, nextpos)
        self.param = param

    def read_params(self, param, bytecode):
        try:
            self.param = CmpOp(param)
        except ValueError:
            raise PythonError("invalid cmp op")

    def print_params(self):
        return self.param.name


class OpcodeReserveFastBase(Opcode):
    """Prepares fast slots. Arg is a const: dict or None."""
    __slots__ = 'param',

    def __init__(self, pos, nextpos, param):
        super().__init__(pos, nextpos)
        self.param = param

    def read_params(self, param, bytecode):
        # TODO
        if bytecode.version.consts_is_list:
            from .code import CodeDict
            const, _ = bytecode.get_const((CodeDict, ExprNone), param)
            if isinstance(const, CodeDict):
                self.param = const.names
            elif isinstance(const, ExprNone):
                self.param = []
            else:
                assert False
        else:
            const, _ = bytecode.get_const((ExprTuple, ExprNone), param)
            if isinstance(const, ExprTuple):
                self.param = []
                for name in const.exprs:
                    if not isinstance(name, ExprString):
                        raise PythonError("funny var name")
                    self.param.append(name.val.decode('ascii'))
            else:
                self.param = None

    def print_params(self):
        if self.param is None:
            return 'None'
        return ', '.join(self.param)


# opcode registration functions

OPCODES = {}

def op_maker(base):
    def make_op_any(code, name, flag=None, multi=False):
        camelname = 'Opcode' + ''.join(x.capitalize() for x in name.split('_'))
        try:
            cls = globals()[camelname]
        except KeyError:
            namespace = {
                '__slots__': (),
                'name': name,
            }
            cls = type(camelname, (base,), namespace)
            globals()[camelname] = cls
        else:
            assert multi
        OPCODES.setdefault(code, []).append((cls, flag))
    return make_op_any

make_op = op_maker(Opcode)
make_op_name = op_maker(OpcodeParamName)
make_op_num = op_maker(OpcodeParamNum)
make_op_rel = op_maker(OpcodeParamRel)
make_op_abs = op_maker(OpcodeParamAbs)
make_op_call = op_maker(OpcodeCallFunctionBase)
make_op_fun = op_maker(OpcodeMakeFunctionNewBase)
make_op_uex = op_maker(OpcodeUnpackExBase)
make_op_const = op_maker(OpcodeLoadConstBase)
make_op_cmp = op_maker(OpcodeCompareOpBase)
make_op_res = op_maker(OpcodeReserveFastBase)


# opcodes start here

make_op(1, 'POP_TOP')
make_op(2, 'ROT_TWO')
make_op(3, 'ROT_THREE')
make_op(4, 'DUP_TOP')
make_op(5, 'ROT_FOUR', 'has_rot_four')
make_op(5, 'DUP_TWO', 'has_dup_two')

make_op(9, 'NOP', 'has_nop')
make_op(10, 'UNARY_POSITIVE')
make_op(11, 'UNARY_NEGATIVE')
make_op(12, 'UNARY_NOT')
make_op(13, 'UNARY_CONVERT', 'has_repr')
make_op(14, 'UNARY_CALL', '!has_kwargs')
make_op(15, 'UNARY_INVERT')

make_op(16, 'BINARY_MATRIX_MULTIPLY', 'has_matmul')
make_op(17, 'INPLACE_MATRIX_MULTIPLY', 'has_matmul')

make_op(17, 'SET_ADD', ('has_setdict_comp', '!has_new_comp'))
make_op(18, 'LIST_APPEND', ('has_list_append', '!has_new_comp'))

make_op(19, 'BINARY_POWER', 'has_power')
make_op(20, 'BINARY_MULTIPLY')
make_op(21, 'BINARY_DIVIDE', 'has_old_divide')
make_op(22, 'BINARY_MODULO')
make_op(23, 'BINARY_ADD')
make_op(24, 'BINARY_SUBTRACT')
make_op(25, 'BINARY_SUBSCR')
make_op(26, 'BINARY_CALL', '!has_kwargs')
make_op(26, 'BINARY_FLOOR_DIVIDE', 'has_new_divide')
make_op(27, 'BINARY_TRUE_DIVIDE', 'has_new_divide')
make_op(28, 'INPLACE_FLOOR_DIVIDE', 'has_new_divide')
make_op(29, 'INPLACE_TRUE_DIVIDE', 'has_new_divide')

make_op(30, 'SLICE_N_N', 'has_old_slice')
make_op(31, 'SLICE_E_N', 'has_old_slice')
make_op(32, 'SLICE_N_E', 'has_old_slice')
make_op(33, 'SLICE_E_E', 'has_old_slice')
make_op(40, 'STORE_SLICE_N_N', 'has_old_slice')
make_op(41, 'STORE_SLICE_E_N', 'has_old_slice')
make_op(42, 'STORE_SLICE_N_E', 'has_old_slice')
make_op(43, 'STORE_SLICE_E_E', 'has_old_slice')
make_op(50, 'DELETE_SLICE_N_N', 'has_old_slice')
make_op(51, 'DELETE_SLICE_E_N', 'has_old_slice')
make_op(52, 'DELETE_SLICE_N_E', 'has_old_slice')
make_op(53, 'DELETE_SLICE_E_E', 'has_old_slice')

make_op(54, 'STORE_MAP', 'has_store_map')

make_op(55, 'INPLACE_ADD', 'has_inplace')
make_op(56, 'INPLACE_SUBTRACT', 'has_inplace')
make_op(57, 'INPLACE_MULTIPLY', 'has_inplace')
make_op(58, 'INPLACE_DIVIDE', ('has_inplace', 'has_old_divide'))
make_op(59, 'INPLACE_MODULO', 'has_inplace')

make_op(60, 'STORE_SUBSCR')
make_op(61, 'DELETE_SUBSCR')

make_op(62, 'BINARY_LSHIFT')
make_op(63, 'BINARY_RSHIFT')
make_op(64, 'BINARY_AND')
make_op(65, 'BINARY_XOR')
make_op(66, 'BINARY_OR')

make_op(67, 'INPLACE_POWER', 'has_inplace')

make_op(68, 'GET_ITER', 'has_iter')
make_op(69, 'STORE_LOCALS', 'has_store_locals')
make_op(70, 'PRINT_EXPR')

make_op(71, 'PRINT_ITEM', 'has_print')
make_op(72, 'PRINT_NEWLINE', 'has_print')
make_op(73, 'PRINT_ITEM_TO', 'has_print_to')
make_op(74, 'PRINT_NEWLINE_TO', 'has_print_to')

make_op(71, 'LOAD_BUILD_CLASS', 'has_new_class')
make_op(72, 'YIELD_FROM', 'has_yield_from')

make_op(75, 'INPLACE_LSHIFT', 'has_inplace')
make_op(76, 'INPLACE_RSHIFT', 'has_inplace')
make_op(77, 'INPLACE_AND', 'has_inplace')
make_op(78, 'INPLACE_XOR', 'has_inplace')
make_op(79, 'INPLACE_OR', 'has_inplace')

make_op(80, 'BREAK_LOOP')
make_op(81, 'RAISE_EXCEPTION', '!has_new_raise')
make_op(81, 'WITH_CLEANUP', 'has_with')
make_op(82, 'LOAD_LOCALS', '!has_new_class')
make_op(83, 'RETURN_VALUE')
# TODO: LOAD_GLOBALS - appears unused...
make_op(84, 'IMPORT_STAR', 'has_import_star')
make_op(85, 'EXEC_STMT', 'has_exec')
make_op(86, 'BUILD_FUNCTION', '!has_kwargs')
make_op(86, 'YIELD_VALUE', 'has_yield_stmt')
make_op(87, 'POP_BLOCK')
make_op(88, 'END_FINALLY')
make_op(89, 'BUILD_CLASS', '!has_new_class')
make_op(89, 'POP_EXCEPT', 'has_pop_except')

# opcodes have an argument from here on

make_op_name(90, 'STORE_NAME')
make_op_name(91, 'DELETE_NAME')

make_op_num(92, 'UNPACK_SEQUENCE', 'has_unpack_sequence')
make_op_num(92, 'UNPACK_TUPLE', '!has_unpack_sequence')
make_op_num(93, 'UNPACK_LIST', '!has_unpack_sequence')
make_op_num(94, 'UNPACK_ARG', '!has_kwargs')

make_op_rel(93, 'FOR_ITER', 'has_iter')

make_op_num(94, 'LIST_APPEND_NEW', ('has_new_comp', '!has_unpack_ex'), True)

make_op_uex(94, 'UNPACK_EX', 'has_unpack_ex')

make_op_name(95, 'STORE_ATTR')
make_op_name(96, 'DELETE_ATTR')
make_op_name(97, 'STORE_GLOBAL')
make_op_name(98, 'DELETE_GLOBAL')

make_op_num(99, 'UNPACK_VARARG', '!has_kwargs')

make_op_num(99, 'DUP_TOP_X', 'has_dup_topx')

make_op_const(100, 'LOAD_CONST')
make_op_name(101, 'LOAD_NAME')

make_op_num(102, 'BUILD_TUPLE')
make_op_num(103, 'BUILD_LIST')
make_op_num(104, 'BUILD_MAP', '!has_setdict_comp', True)
make_op_name(105, 'LOAD_ATTR', '!has_setdict_comp', True)
make_op_cmp(106, 'COMPARE_OP', '!has_setdict_comp', True)
make_op_name(107, 'IMPORT_NAME', '!has_setdict_comp', True)
make_op_name(108, 'IMPORT_FROM', '!has_setdict_comp', True)
make_op_name(109, 'ACCESS_MODE', 'has_access')

make_op_num(104, 'BUILD_SET', 'has_setdict_comp')
make_op_num(105, 'BUILD_MAP', 'has_setdict_comp', True)
make_op_name(106, 'LOAD_ATTR', 'has_setdict_comp', True)
make_op_cmp(107, 'COMPARE_OP', 'has_setdict_comp', True)
make_op_name(108, 'IMPORT_NAME', 'has_setdict_comp', True)
make_op_name(109, 'IMPORT_FROM', 'has_setdict_comp', True)

make_op_rel(110, 'JUMP_FORWARD')

make_op_rel(111, 'JUMP_IF_FALSE', '!has_new_jump')
make_op_rel(112, 'JUMP_IF_TRUE', '!has_new_jump')

make_op_abs(111, 'JUMP_IF_FALSE_OR_POP', 'has_new_jump')
make_op_abs(112, 'JUMP_IF_TRUE_OR_POP', 'has_new_jump')

make_op_abs(113, 'JUMP_ABSOLUTE')

make_op_rel(114, 'FOR_LOOP', '!has_iter')

make_op_abs(114, 'POP_JUMP_IF_FALSE', 'has_new_jump')
make_op_abs(115, 'POP_JUMP_IF_TRUE', 'has_new_jump')

# TODO: LOAD_LOCAL - appears unused...
make_op_name(116, 'LOAD_GLOBAL')

make_op_num(117, 'SET_FUNC_ARGS', ('has_def_args', '!has_kwargs'))

make_op_abs(119, 'CONTINUE_LOOP', 'has_new_continue')

make_op_rel(120, 'SETUP_LOOP')
make_op_rel(121, 'SETUP_EXCEPT')
make_op_rel(122, 'SETUP_FINALLY')

make_op_res(123, 'RESERVE_FAST', '!has_kwargs')
make_op_num(124, 'LOAD_FAST')
make_op_num(125, 'STORE_FAST')
make_op_num(126, 'DELETE_FAST')

make_op_num(127, 'SET_LINENO', 'has_set_lineno')

make_op_num(130, 'RAISE_VARARGS', 'has_new_raise')

make_op_call(131, 'CALL_FUNCTION', 'has_kwargs')

make_op_num(132, 'MAKE_FUNCTION', ('has_kwargs', '!has_kwonlyargs'))
make_op_fun(132, 'MAKE_FUNCTION_NEW', 'has_kwonlyargs')

make_op_num(133, 'BUILD_SLICE', 'has_new_slice')

make_op_num(134, 'MAKE_CLOSURE', ('has_closure', '!has_kwonlyargs'))
make_op_fun(134, 'MAKE_CLOSURE_NEW', 'has_kwonlyargs')

make_op_num(135, 'LOAD_CLOSURE', 'has_closure')
make_op_num(136, 'LOAD_DEREF', 'has_closure')
make_op_num(137, 'STORE_DEREF', 'has_closure')
make_op_num(138, 'DELETE_DEREF', 'has_delete_deref')

make_op_call(140, 'CALL_FUNCTION_VAR', 'has_var_call')
make_op_call(141, 'CALL_FUNCTION_KW', 'has_var_call')
make_op_call(142, 'CALL_FUNCTION_VAR_KW', 'has_var_call')

make_op_rel(143, 'SETUP_WITH', 'has_setup_with')

# has special handling in the parser loop
make_op_num(143, 'EXTENDED_ARG', ('has_extended_arg', '!has_setup_with'), True)
make_op_num(144, 'EXTENDED_ARG', ('has_setup_with', 'has_unpack_ex'), True)
make_op_num(145, 'EXTENDED_ARG', ('has_setup_with', '!has_unpack_ex'), True)

make_op_num(145, 'LIST_APPEND_NEW', ('has_new_comp', 'has_unpack_ex'), True)
make_op_num(146, 'SET_ADD_NEW', 'has_new_comp')
make_op_num(147, 'MAP_ADD_NEW', 'has_new_comp')

make_op_num(148, 'LOAD_CLASS_DEREF', 'has_classderef')


# the reader

class _BytecodeCtx:
    def __init__(self, version, code):
        self.version = version
        self.code = code.rawcode
        self.consts = code.consts
        self.names = code.names
        self.pos = 0
        opdict = {}
        self.ops = []
        while self.pos != len(self.code):
            pos = self.pos
            op = self.get_op(pos, 0)
            if isinstance(op, OpcodeExtendedArg):
                op = self.get_op(pos, op.param)
                if isinstance(op, OpcodeExtendedArg):
                    raise PythonError("funny, two EXTENDED_ARG in a row")
            self.ops.append(op)
            opdict[pos] = op

    def get_op(self, pos, ext):
        opc = self.bytes(1)[0]
        for cls, flag in OPCODES.get(opc, []):
            if self.version.match(flag):
                op = cls.__new__(cls)
                op.pos = pos
                if hasattr(op, 'read_params'):
                    param = int.from_bytes(self.bytes(2), 'little') | ext << 16
                    op.read_params(param, self)
                op.nextpos = self.pos
                return op
        raise PythonError("unknown opcode {}".format(opc))

    def bytes(self, num):
        new = self.pos + num
        if new > len(self.code):
            raise PythonError("bytecode ends in the middle of an opcode")
        res = self.code[self.pos:new]
        self.pos = new
        return res

    def get_const(self, cls, idx):
        if idx < 0 or idx >= len(self.consts):
            raise PythonError("Const index out of range")
        res = self.consts[idx]
        if not isinstance(res, cls):
            raise PythonError("Const of type {} expected, got {}".format(cls, type(res)))
        return res, idx

def parse_bytecode(version, code):
    return _BytecodeCtx(version, code).ops


def process_flow(ops):
    inflow = {}
    for op in ops:
        inflow[op.pos] = []
    for op in ops:
        if hasattr(op, 'flow'):
            if op.flow.dst not in inflow:
                raise PythonError("funny flow target")
            inflow[op.flow.dst].append(op.flow)
    return inflow


# lineno handling

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
