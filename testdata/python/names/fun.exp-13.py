def g1():
	a$0 = 3
	b$1 = $global[c]
	b$1 = a$0
	del a$0
	del d$2
def g2():
	$global[a] = 3
	$global[b] = $global[c]
	$global[b] = $global[a]
	del $global[a]
	del $global[d]
def g3():
	exec z
	a$0 = 3
	b$1 = c
	b$1 = a$0
	del a$0
	del d$2
def g4():
	exec z in None
	a$0 = 3
	b$1 = c
	b$1 = a$0
	del a$0
	del d$2
def g5():
	from -1 x import *
	a$1 = 3
	b$2 = c
	b$2 = a$1
	del a$1
	del d$3
