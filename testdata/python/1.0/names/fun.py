def g1():
    a = 3
    b = c
    b = a
    del a
    del d

def g2():
    global a, b, c, d
    a = 3
    b = c
    b = a
    del a
    del d

def g3():
    exec z
    a = 3
    b = c
    b = a
    del a
    del d

def g4():
    exec z in None
    a = 3
    b = c
    b = a
    del a
    del d

def g5():
    from x import *
    a = 3
    b = c
    b = a
    del a
    del d

