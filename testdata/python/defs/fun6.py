def f(a, b: 3, c=2, *d, e: x = 4, f, **g) -> y:
    pass

def f(a, b: 3, c=2, *d : w, e: x = 4, f, **g : v) -> y:
    pass

# with closure

def o(x, i):
    def f(a, b: 3, c=2, *d : w, e: x = 4, f, **g : v) -> y:
        return i
