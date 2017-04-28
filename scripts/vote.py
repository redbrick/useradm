#!/usr/bin/python

import sys
import readline
import re
import os

from rbuser import *
from rbuserdb import *

voteregister= 'voted.txt'

#-----------------------------------------------------------------------------#
# MAIN                                                                        #
#-----------------------------------------------------------------------------#

def main():
	"""Program entry function."""

	voted = {}

	if os.path.exists(voteregister):
		fd = open(voteregister, 'r')
		for line in fd.readlines():
			voted[line.rstrip()] = 1
		fd.close()

	fd = open(voteregister, 'a')

	udb = RBUserDB()
	udb.connect()

	while 1:
		usr = RBUser()
		tmp = None
		while not tmp:
			tmp = input("Please enter Username/Student ID/Student Card: ")
		res = re.search(r'\D*\d{2}(\d{8})\d{3}\D*', tmp)
		if res:
			usr.id = int(res.group(1))
			print('CARD', usr.id)
		else:
			res = re.search(r'^(\d{8})$', tmp)
			if res:
				usr.id = int(tmp)
				print('ID', usr.id)
		try:
			if usr.id:
				udb.get_user_byid(usr)
				udb.show(usr)
			else:
				usr.uid = tmp
				udb.get_user_byname(usr)
				udb.show(usr)
		except RBError:

			print('[31;1mNO SUCH USER YOU FUCKING DICKHEAD[0m')
		else:
			if usr.uid in voted:
				print('\n[31;1mGO FUCK YOUSELF YOU TWO-VOTING PRICK[0m\n')
				continue

			if usr.usertype not in ('member', 'committe', 'staff'):
				print('\n[31;1mTELL THE COCKMUCH TO GET A REAL MEMBER ACCOUNT[0m\n')
			elif usr.yearsPaid <= 0:
				print('\n[31;1mTELL THE SCABBY BASTARD TO PISS OFF[0m\n')
			else:
				fd.write('%s\n' % usr.uid)
				fd.flush()
				voted[usr.uid] = 1
				print('\n[32;1mBIG VOTE GO NOW![0m\n')

	fd.close()
	sys.exit(0)

if __name__ == "__main__":
        main()

