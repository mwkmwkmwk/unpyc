def f():
	return ($global[a] < $global[b] < $global[c])
	return ($global[a] < $global[b] < $global[c] < $global[d])
	return ($global[x] or ($global[a] < $global[b] < $global[c] < $global[d]))
	return ($global[x] and ($global[a] < $global[b] < $global[c] < $global[d]))
	return ($global[x] and ($global[y] and ($global[a] < $global[b] < $global[c] < $global[d])))
	return ($global[x] or ($global[y] or ($global[a] < $global[b] < $global[c] < $global[d])))
	return (($global[x] and $global[y]) or ($global[a] < $global[b] < $global[c] < $global[d]))
	return ($global[x] or ($global[y] and ($global[a] < $global[b] < $global[c] < $global[d])))
