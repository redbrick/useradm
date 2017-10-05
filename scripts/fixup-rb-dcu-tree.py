#! /usr/bin/python

import re
import sys

re_dn = re.compile(r'^(dn: cn=.*?,).*(ou=.*?),o=DCU$')

for i in sys.stdin:
    i = i.rstrip()
    if i.startswith("dn:"):
        print(re.sub(re_dn, r'\1\2,ou=dcu,o=redbrick', i))
        print("objectClass: top")
        print("objectClass: dcuAccount")
    elif not i.startswith('objectClass:'):
        print(i)
