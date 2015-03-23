@a
def f(x):
    return x

@a
@b
@c
def f():
    return z


@a(4)
@b(2, 3, 4, c * d)
def f():
    pass

@a.b.c
@d.e.f(3)
def f():
    pass
