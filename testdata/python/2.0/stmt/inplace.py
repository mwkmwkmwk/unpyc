a += 1
b[c] -= 2
b[:] *= 3
b[1:] /= 4
b[:2] %= 5
b[3:4] **= 6
a.b <<= 7
a.b.c >>= 8

def f():
    global b
    a &= 9
    b ^= 10
    c |= 11
