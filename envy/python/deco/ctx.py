from ..helpers import PythonError

from . import TRACE

from ..stmt import *
from ..expr import *
from ..bytecode import *

from .visitor import VISITORS
from .stack import *

class DecoCtx:
    def __init__(self, code):
        self.version = code.version
        self.stack = [Block([])]
        self.code = code
        self.lineno = None
        if self.version.has_kwargs:
            self.varnames = code.varnames
        else:
            self.varnames = None
        if TRACE:
            print("START {} {}".format(code.name, code.firstlineno))
        ops, inflow = self.preproc(code.ops)
        for op in ops:
            if hasattr(op, 'pos'):
                rev = []
                for flow in reversed(inflow[op.pos]):
                    if flow.dst > flow.src:
                        flow = FwdFlow(flow)
                        self.process(flow)
                    else:
                        rev.append(flow)
                if rev:
                    self.process(RevFlow(rev))
            self.process(op)
        if len(self.stack) != 1:
            raise PythonError("stack non-empty at the end: {}".format(
                ', '.join(type(x).__name__ for x in self.stack)
            ))
        if not isinstance(self.stack[0], Block):
            raise PythonError("weirdness on stack at the end")
        self.res = DecoCode(self.stack[0], code, self.varnames or [])

    def preproc(self, ops):
        # first pass: undo jump over true const
        if self.version.has_jump_true_const:
            newops = []
            fakejumps = {}
            for idx, op in enumerate(ops):
                op = ops[idx]
                more = len(ops) - idx - 1
                if (more >= 2
                    and isinstance(op, OpcodeJumpForward)
                    and isinstance(ops[idx+1], OpcodeJumpIfFalse)
                    and isinstance(ops[idx+2], OpcodePopTop)
                    and op.flow.dst == ops[idx+2].nextpos
                ):
                    fakejumps[op.flow.dst] = op.pos
                    newops.append(OpcodeLoadConst(op.pos, op.nextpos, ExprAnyTrue(), None))
                elif isinstance(op, (OpcodeJumpAbsolute, OpcodeContinueLoop)) and op.flow.dst in fakejumps:
                    newops.append(type(op)(op.pos, op.nextpos, Flow(op.flow.src, fakejumps[op.flow.dst])))
                else:
                    newops.append(op)
            ops = newops
        # alt first pass: undo conditional jump folding for jumps with opposite polarisation
        if self.version.has_jump_cond_fold:
            after_jif = {}
            after_jit = {}
            for op in ops:
                if isinstance(op, (OpcodeJumpIfFalse, OpcodeJumpIfFalseOrPop, OpcodePopJumpIfFalse)):
                    after_jif[op.nextpos] = op.pos
                elif isinstance(op, (OpcodeJumpIfTrue, OpcodeJumpIfTrueOrPop, OpcodePopJumpIfTrue)):
                    after_jit[op.nextpos] = op.pos
            newops = []
            for op in ops:
                if isinstance(op, OpcodeJumpIfFalse) and op.flow.dst in after_jit:
                    newops.append(OpcodeJumpIfFalse(op.pos, op.nextpos, Flow(op.pos, after_jit[op.flow.dst])))
                elif isinstance(op, OpcodePopJumpIfFalse) and op.flow.dst in after_jit:
                    newops.append(OpcodeJumpIfFalseOrPop(op.pos, op.nextpos, Flow(op.pos, after_jit[op.flow.dst])))
                elif isinstance(op, OpcodeJumpIfTrue) and op.flow.dst in after_jif:
                    newops.append(OpcodeJumpIfTrue(op.pos, op.nextpos, Flow(op.pos, after_jif[op.flow.dst])))
                elif isinstance(op, OpcodePopJumpIfTrue) and op.flow.dst in after_jif:
                    newops.append(OpcodeJumpIfTrueOrPop(op.pos, op.nextpos, Flow(op.pos, after_jif[op.flow.dst])))
                else:
                    newops.append(op)
            ops = newops
        # second pass: figure out the kinds of absolute jumps
        condflow = {op.nextpos: [] for op in ops}
        for op in ops:
            if isinstance(op, (OpcodePopJumpIfTrue, OpcodePopJumpIfFalse, OpcodeJumpIfTrueOrPop, OpcodeJumpIfFalseOrPop, OpcodeJumpIfTrue, OpcodeJumpIfFalse, OpcodeForLoop, OpcodeForIter, OpcodeSetupExcept)):
                condflow[op.flow.dst].append(op.flow)
        inflow = process_flow(ops)
        newops = []
        for idx, op in enumerate(ops):
            next_unreachable = not condflow[op.nextpos]
            next_end_finally = idx+1 < len(ops) and isinstance(ops[idx+1], OpcodeEndFinally)
            next_pop_top = idx+1 < len(ops) and isinstance(ops[idx+1], OpcodePopTop)
            if isinstance(op, OpcodeJumpAbsolute):
                insert_end = False
                is_final = op.flow == max(inflow[op.flow.dst])
                is_backwards = op.flow.dst <= op.pos
                if not is_backwards:
                    if next_unreachable and not next_end_finally:
                        op = JumpSkipJunk(op.pos, op.nextpos, [op.flow])
                    else:
                        op = JumpUnconditional(op.pos, op.nextpos, [op.flow])
                elif is_final:
                    op = JumpContinue(op.pos, op.nextpos, [op.flow])
                    insert_end = True
                elif next_unreachable and not next_end_finally:
                    if next_pop_top:
                        op = JumpSkipJunk(op.pos, op.nextpos, [op.flow])
                    else:
                        op = JumpContinue(op.pos, op.nextpos, [op.flow])
                else:
                    op = JumpContinue(op.pos, op.nextpos, [op.flow])
                newops.append(op)
            elif isinstance(op, OpcodeJumpForward):
                if next_unreachable and not next_end_finally:
                    op = JumpSkipJunk(op.pos, op.nextpos, [op.flow])
                else:
                    op = JumpUnconditional(op.pos, op.nextpos, [op.flow])
                newops.append(op)
            else:
                newops.append(op)
        ops = newops
        return ops, inflow

    def process(self, op):
        for t in type(op).mro():
            for visitor in VISITORS.get(t, []):
                try:
                    res = visitor.visit(op, self)
                except NoMatch:
                    pass
                else:
                    for item in res:
                        if item is None:
                            pass
                        elif isinstance(item, Regurgitable):
                            self.process(item)
                        else:
                            self.stack.append(item)
                    return
        if TRACE:
            for x in self.stack:
                print(x)
            print(op)
        raise PythonError("no visitors matched: {}, [{}]".format(
            type(op).__name__,
            ', '.join(type(x).__name__ for x in self.stack)
        ))

    def fast(self, idx):
        if self.varnames is None:
            raise PythonError("no fast variables")
        if idx not in range(len(self.varnames)):
            raise PythonError("fast var out of range")
        return ExprFast(idx, self.varnames[idx])

    def deref(self, idx):
        if idx in range(len(self.code.cellvars)):
            return ExprDeref(idx, self.code.cellvars[idx])
        fidx = idx - len(self.code.cellvars)
        if fidx in range(len(self.code.freevars)):
            return ExprDeref(idx, self.code.freevars[fidx])
        raise PythonError("deref var out of range")

    def string(self, expr):
        if self.version.py3k:
            if not isinstance(expr, ExprUnicode):
                raise PythonError("wanted a string, got {}".format(expr))
            return expr.val
        else:
            if not isinstance(expr, ExprString):
                raise PythonError("wanted a string")
            return expr.val.decode('ascii')

    def make_ann(self, ann):
        if not ann:
            return {}
        *vals, keys = ann
        if not isinstance(keys, ExprTuple):
            raise PythonError("no ann tuple")
        if len(vals) != len(keys.exprs):
            raise PythonError("ann len mismatch")
        return {self.string(k): v for k, v in zip(keys.exprs, vals)}

    def _ensure_dead_end(self, block):
        if not block.stmts:
            raise PythonError("empty dead block")
        final = block.stmts[-1]
        if isinstance(final, StmtFinalContinue):
            pass
        elif isinstance(final, StmtReturn) and self.version.has_dead_return:
            pass
        elif isinstance(final, StmtIf):
            for item in final.items:
                self._ensure_dead_end(item[1])
            self._ensure_dead_end(final.else_)
        else:
            raise PythonError("invalid dead block {}".format(final))

    def process_dead_end(self, block):
        if not block.stmts:
            raise PythonError("empty dead block")
        final = block.stmts[-1]
        if isinstance(final, StmtContinue):
            block.stmts[-1] = StmtFinalContinue()
        elif isinstance(final, StmtFinalContinue):
            pass
        elif isinstance(final, StmtReturn) and self.version.has_dead_return:
            pass
        elif isinstance(final, StmtIfDead):
            pass
        elif isinstance(final, StmtIfRaw):
            # XXX eh
            final.else_ = self.process_dead_end(final.else_)
        elif isinstance(final, StmtExcept):
            # XXX eh
            final.else_ = self.process_dead_end(final.else_)
        elif isinstance(final, StmtLoop):
            final.else_ = self.process_dead_end(final.else_)
        else:
            raise PythonError("invalid dead block {}".format(final))
        return block
