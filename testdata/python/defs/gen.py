from __future__ import generators
def f():
    yield a
    yield b
    yield c

def g():
    if 0:
        yield a

def h():
    if 1:
        f()
    else:
        yield a

def i():
    while 0:
        yield a
