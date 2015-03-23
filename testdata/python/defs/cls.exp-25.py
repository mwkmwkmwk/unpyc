class A:
	__module__ = __name__
class A(B, C):
	__module__ = __name__
	(z, w, y) = 3
class X:
	__module__ = __name__
	def x():
		return ($global[super]($global[a], $global[b])).c
class Y:
	__module__ = __name__
	def x():
		return ($global[super]($global[b])).c
class Z:
	__module__ = __name__
	def x():
		return ($global[super]()).c
class W:
	__module__ = __name__
	def x():
		return $global[__class__]
class V:
	__module__ = __name__
	class N:
		__module__ = __name__
		def z():
			return $global[__class__]
class T:
	__module__ = __name__
	def x():
		return $global[super]
