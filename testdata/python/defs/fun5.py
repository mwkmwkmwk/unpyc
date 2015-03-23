def f1():
    pass

def f2():
    return None

def f3():
    return

def f4(a):
    pass

def f5(a, b):
    pass

def f6(a, *b):
    pass

def f7(a, *b): pass

def f8(a, b, *c): pass

def f(a, b=3, c=4):
    pass

def g(a=1, b=3):
    pass

def g(a, b=3, *c):
    pass

def f(a, b=3, c=4, **d):
    pass

def h(i, *j, **k):
    pass

x = lambda a, b=3, c=None, **d: d * c
