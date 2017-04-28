#! /usr/bin/env python3

import sys
from ..useradm.rbuserdb import RBUserDB
udb = RBUserDB()
udb.connect()
fd, n = udb.uidNumber_getnext()
for line in sys.stdin:
    if line == 'uidNumber: -1\n':
        print('uidNumber:', n)
        n += 1
    else:
        print(line, end=' ')

udb.uidNumber_savenext(fd, n)
udb.uidNumber_unlock(fd)
