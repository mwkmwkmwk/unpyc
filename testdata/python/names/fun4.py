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
