from -1 __future__ import generators as generators
def f():
	(yield $global[a])
	(yield $global[b])
	(yield $global[c])
def g():
	pass
def h():
	$global[f]()
	if $true:
		pass
	else:
		(yield $global[a])
def i():
	while 0:
		(yield $global[a])
