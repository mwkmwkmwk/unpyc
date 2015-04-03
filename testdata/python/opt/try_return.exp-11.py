def f():
	try:
		$global[a]
	except $global[b]:
		$global[c]
		return $global[d]
	try:
		$global[a]
	except $global[b]:
		return $global[c]
	except:
		return $global[d]
