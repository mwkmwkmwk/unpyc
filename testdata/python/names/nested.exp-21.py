def a():
	x$1 = 1
	def b():
		return $global[x]
	return x$1
def a():
	x$1 = 1
	def b():
		x$0 = 2
		return x$0
	return x$1
def a():
	x$2 = 1
	y$3 = 2
	z$1 = 3
	def b():
		def c():
			return ($global[y], $global[z])
		return (c$0, $global[x], $global[y])
	return b$0
