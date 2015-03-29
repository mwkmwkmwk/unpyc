from __future__ import nested_scopes

def a():
    x = 1
    def b(i=1):
        return x
    return x

def a():
    x = 1
    def b(j=2):
        x = 2
        return x
    return x

def a():
    x = 1
    y = 2
    z = 3
    def b(k=4, l=5):
        def c(m=6, n=7):
            return y, z
        return c, x, y
    return b
