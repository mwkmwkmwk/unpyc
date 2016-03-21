# funny intermediate stuff to put on stack

class NoMatch(Exception):
    pass

from collections import namedtuple
from ..bytecode import *
from ..stmt import *

DupTop = namedtuple('DupTop', [])
DupTwo = namedtuple('DupTwo', [])
DupThree = namedtuple('DupThree', [])

RotTwo = namedtuple('RotTwo', [])
RotThree = namedtuple('RotThree', [])
RotFour = namedtuple('RotFour', [])

Iter = namedtuple('Iter', ['expr'])

Import = namedtuple('Import', ['name', 'items'])
Import2Simple = namedtuple('Import2Simple', ['level', 'name', 'attrs'])
Import2Star = namedtuple('Import2Star', ['level', 'name'])
Import2From = namedtuple('Import2From', ['level', 'fromlist', 'name', 'exprs'])

MultiAssign = namedtuple('MultiAssign', ['src', 'dsts'])
PrintTo = namedtuple('PrintTo', ['expr', 'vals'])

UnpackSlot = namedtuple('UnpackSlot', ['expr', 'idx'])
UnpackArgSlot = namedtuple('UnpackArgSlot', ['args', 'idx'])
UnpackVarargSlot = namedtuple('UnpackVarargSlot', ['args'])
UnpackBeforeSlot = namedtuple('UnpackBeforeSlot', ['expr', 'idx'])
UnpackAfterSlot = namedtuple('UnpackAfterSlot', ['expr', 'idx'])
UnpackStarSlot = namedtuple('UnpackStarSlot', ['expr'])

IfStart = namedtuple('IfStart', ['expr', 'flow', 'neg', 'pop'])
IfExprTrue = namedtuple('IfExprTrue', ['expr', 'flow'])
IfExprElse = namedtuple('IfExprElse', ['cond', 'true', 'flow'])
IfDead = namedtuple('IfDead', ['cond', 'true', 'flow'])

CompareStart = namedtuple('CompareStart', ['first', 'rest', 'flows'])
Compare = namedtuple('Compare', ['first', 'rest', 'flows'])
CompareLast = namedtuple('CompareLast', ['first', 'rest', 'flows'])
CompareNext = namedtuple('CompareNext', ['first', 'rest', 'flows'])

WantPop = namedtuple('WantPop', [])
WantRotPop = namedtuple('WantRotPop', [])
WantFlow = namedtuple('WantFlow', ['any', 'true', 'false'])
WantReturn = namedtuple('WantReturn', ['expr'])

SetupLoop = namedtuple('SetupLoop', ['flow'])
SetupFinally = namedtuple('SetupFinally', ['flow'])
SetupExcept = namedtuple('SetupExcept', ['flow'])

Loop = namedtuple('Loop', ['flow'])
While = namedtuple('While', ['expr', 'end', 'block'])
ForStart = namedtuple('ForStart', ['expr', 'flow'])
TopForStart = namedtuple('TopForStart', ['expr', 'flow'])
ForLoop = namedtuple('ForLoop', ['expr', 'dst', 'flow'])
TopForLoop = namedtuple('TopForLoop', ['expr', 'dst', 'flow'])

TryFinallyPending = namedtuple('TryFinallyPending', ['body', 'flow'])
TryFinally = namedtuple('TryFinally', ['body'])

TryExceptEndTry = namedtuple('TryExceptEndTry', ['flow', 'body'])
TryExceptMid = namedtuple('TryExceptMid', ['else_', 'body', 'items', 'any', 'flows'])
TryExceptMatchMid = namedtuple('TryExceptMatchMid', ['expr'])
TryExceptMatchOk = namedtuple('TryExceptMatchOk', ['expr', 'next'])
TryExceptMatch = namedtuple('TryExceptMatch', ['expr', 'dst', 'next'])
TryExceptAny = namedtuple('TryExceptAny', [])
PopExcept = namedtuple('PopExcept', [])

UnaryCall = namedtuple('UnaryCall', ['code'])
Locals = namedtuple('Locals', [])

DupAttr = namedtuple('DupAttr', ['expr', 'name'])
DupSubscr = namedtuple('DupSubscr', ['expr', 'index'])
DupSlice = namedtuple('DupSlice', ['expr', 'start', 'end'])

InplaceSimple = namedtuple('InplaceSimple', ['dst', 'src', 'stmt'])
InplaceAttr = namedtuple('InplaceAttr', ['expr', 'name', 'src', 'stmt'])
InplaceSubscr = namedtuple('InplaceSubscr', ['expr', 'index', 'src', 'stmt'])
InplaceSlice = namedtuple('InplaceSlice', ['expr', 'start', 'end', 'src', 'stmt'])

TmpVarAttrStart = namedtuple('TmpVarAttrStart', ['tmp', 'expr', 'name'])
TmpVarCleanup = namedtuple('TmpVarCleanup', ['tmp'])

Closure = namedtuple('Closure', ['var'])
ClosuresTuple = namedtuple('ClosuresTuple', ['vars'])

FinalElse = namedtuple('FinalElse', ['flow', 'maker'])
AssertJunk = namedtuple('AssertJunk', ['expr', 'msg'])

WithEnter = namedtuple('WithEnter', ['tmp', 'expr'])
WithResult = namedtuple('WithResult', ['tmp', 'expr'])
WithStart = namedtuple('WithStart', ['tmp', 'expr'])
WithStartTmp = namedtuple('WithStartTmp', ['tmp', 'expr', 'res'])
WithTmp = namedtuple('WithTmp', ['tmp', 'expr', 'res', 'flow'])
WithInnerResult = namedtuple('WithInnerResult', ['tmp', 'expr', 'flow'])
With = namedtuple('With', ['tmp', 'expr', 'dst', 'flow'])
WithEndPending = namedtuple('WithEndPending', ['tmp', 'flow', 'stmt'])
WithEnd = namedtuple('WithEnd', ['tmp', 'stmt'])
WithExit = namedtuple('WithExit', ['stmt'])
WithExitDone = namedtuple('WithExitDone', ['stmt'])

# final makers

class FinalJunk(namedtuple('FinalJunk', [])):
    def __call__(self, else_):
        return StmtJunk(else_)

class FinalIf(namedtuple('FinalIf', ['expr', 'body'])):
    def __call__(self, else_):
        return StmtIfRaw(self.expr, self.body, else_)

class FinalLoop(namedtuple('FinalLoop', ['body'])):
    def __call__(self, else_):
        return StmtLoop(self.body, else_)

class FinalExcept(namedtuple('FinalExcept', ['body', 'items', 'any'])):
    def __call__(self, else_):
        return StmtExcept(self.body, self.items, self.any, else_)

# regurgitables

class Regurgitable: __slots__ = ()

class Store(Regurgitable, namedtuple('Store', ['dst'])): pass
class Inplace(Regurgitable, namedtuple('Inplace', ['stmt'])): pass

# fake opcodes

class JumpIfTrue(OpcodeFlow): pass
class JumpIfFalse(OpcodeFlow): pass
class PopJumpIfTrue(OpcodeFlow): pass
class PopJumpIfFalse(OpcodeFlow): pass
class JumpUnconditional(OpcodeFlow): pass
class JumpContinue(OpcodeFlow): pass
class JumpSkipJunk(OpcodeFlow): pass

class FwdFlow(Regurgitable, namedtuple('FwdFlow', ['flow'])): pass
class RevFlow(Regurgitable, namedtuple('RevFlow', ['flow'])): pass

# for checks

Regurgitable = (Regurgitable, Stmt, Opcode)
