def f(a, b=3, c=4):
    pass

def g(a=1, b=3):
    pass

def g(a, b=3, *c):
    pass

def g(a, (b, c, (d, e))=z, (f, g)=w, *h):
    pass
def f(a, b=3, c=4, **d):
    pass

def h(i, *j, **k):
    pass

x = lambda a, b=3, c=None, **d: d * c
