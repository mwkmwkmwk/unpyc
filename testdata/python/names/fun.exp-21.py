def g1():
	a$2 = 3
	b$1 = $global[c]
	b$1 = a$2
	del a$2
	del d$0
def g2():
	$global[a] = 3
	$global[b] = $global[c]
	$global[b] = $global[a]
	del $global[a]
	del $global[d]
def g3():
	exec z
	a$2 = 3
	b$1 = c
	b$1 = a$2
	del a$2
	del d$0
def g4():
	exec z in None
	a$2 = 3
	b$1 = c
	b$1 = a$2
	del a$2
	del d$0
def g5():
	from x import *
	a$2 = 3
	b$1 = c
	b$1 = a$2
	del a$2
	del d$0
