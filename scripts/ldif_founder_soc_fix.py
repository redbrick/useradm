#!/usr/bin/python
import sys
for i in sys.stdin:
	i = i.rstrip()
	if i.startswith("yearsPaid:"):
		print "yearsPaid:", int(i.split()[1]) + 9
	elif i.startswith("newbie:"):
		print "newbie: FALSE"
	else:
		print i
