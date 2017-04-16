#! /usr/bin/env python

from rbuserdb import *
udb = RBUserDB()
udb.connect()
fd, n = udb.uidNumber_getnext()
for line in sys.stdin:
	if line == 'uidNumber: -1\n':
		print 'uidNumber:', n
		n += 1
	else:
		print line,

udb.uidNumber_savenext(fd, n)
udb.uidNumber_unlock(fd)
