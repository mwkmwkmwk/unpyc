def g1():
	import -1 a as a$0
	from -1 z import b as b$2
	def c():
		pass
	class d:
		__module__ = $global[__name__]
def g2():
	import -1 a as $global[a]
	from -1 z import b as $global[b]
	def c():
		pass
	class d:
		__module__ = $global[__name__]
def g3():
	exec z
	import -1 a as a$0
	from -1 z import b as b$2
	def c():
		pass
	class d:
		__module__ = $global[__name__]
def g4():
	exec z in None
	import -1 a as a$0
	from -1 z import b as b$1
	def c():
		pass
	class d:
		__module__ = $global[__name__]
def g5():
	from -1 x import *
	import -1 a as a$0
	from -1 z import b as b$2
	def c():
		pass
	class d:
		__module__ = $global[__name__]
