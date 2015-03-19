class A:
    pass

class A(B, C):
    z, w, y = 3

class X:
    def x():
        return super(a, b).c

class Y:
    def x():
        return super(b).c

class Z:
    def x():
        return super().c

class W:
    def x():
        return __class__

class V:
    class N:
        def z():
            return __class__

class T:
    def x():
        return super
