def g1():
	import a as a$0
	from z import b as b$1
	def c():
		pass
	class d:
		pass
def g2():
	import a as $global[a]
	from z import b as $global[b]
	def c():
		pass
	class d:
		pass
def g3():
	exec z
	import a as a$0
	from z import b as b$1
	def c():
		pass
	class d:
		pass
def g4():
	exec z in None
	import a as a$0
	from z import b as b$1
	def c():
		pass
	class d:
		pass
def g5():
	from x import *
	import a as a$0
	from z import b as b$1
	def c():
		pass
	class d:
		pass
