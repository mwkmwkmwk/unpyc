def f(a, b=3, c=4, **d):
    pass

def h(i, *j, **k):
    pass

x = lambda a, b=3, c, **d: d * c
