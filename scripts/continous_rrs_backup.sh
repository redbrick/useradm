#! /bin/sh
#
# Simple way of dumping live ldap database and rrs.log file and copying them
# somewhere else.
#
while [ 1 ]; do
	# Can't use slapcat safely as the ldap database is read-write and in use.
	ldapsearch -x -w "LDAP-SECRET" -D cn=root,ou=ldap,o=redbrick -h localhost > shrapnel.ldif.bak
	# We're paranoid.
	sync; sync; sync
	# Again with the paranoia.
	cp rrs.log rrs.log.bak
	# Assumes SSH agent is running.
	scp shrapnel.ldif.bak rrs.log.bak carbon:
	# More healthy paranoia.
	ssh carbon 'cp shrapnel.ldif.bak shrapnel.ldif; cp rrs.log.bak rrs.log'
	# Wait 5 minutes.
	sleep 300
done
