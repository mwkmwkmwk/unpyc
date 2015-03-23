def a():
    x = 1
    def b():
        return x
    return x

def a():
    x = 1
    def b():
        x = 2
        return x
    return x

def a():
    x = 1
    y = 2
    z = 3
    def b():
        def c():
            return y, z
        return c, x, y
    return b
