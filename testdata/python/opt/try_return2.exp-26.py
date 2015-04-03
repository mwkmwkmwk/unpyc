def f():
	try:
		$global[a]
	except $global[b]:
		$global[c]
		return $global[d]
	$global[e]
	$global[f]
	try:
		$global[a]
	except $global[b]:
		return $global[c]
	except:
		return $global[d]
	$global[e]
	$global[f]
