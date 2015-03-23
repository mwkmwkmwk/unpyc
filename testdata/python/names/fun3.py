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
