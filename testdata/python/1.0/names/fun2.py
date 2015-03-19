def g1():
    import a
    from z import b
    def c():
        pass
    class d:
        pass

def g2():
    global a, b, c, d
    import a
    from z import b
    def c():
        pass
    class d:
        pass

def g3():
    exec z
    import a
    from z import b
    def c():
        pass
    class d:
        pass

def g4():
    exec z in None
    import a
    from z import b
    def c():
        pass
    class d:
        pass

def g5():
    from x import *
    import a
    from z import b
    def c():
        pass
    class d:
        pass
