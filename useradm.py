#-----------------------------------------------------------------------------#
# MODULE DESCRIPTION                                                          #
#-----------------------------------------------------------------------------#

"""RedBrick command line user administration interface."""

# System modules

import atexit
import getopt
import getpass
import grp
import os
import pwd
import re
import readline
import sys

# 3rd party modules

#import

# RedBrick modules

import rbconfig
from rbaccount import *
from rberror import *
from rbopt import *
from rbuser import *
from rbuserdb import *

#-----------------------------------------------------------------------------#
# DATA                                                                        #
#-----------------------------------------------------------------------------#

__version__ = '$Revision: 1.1 $'
__author__  = 'Cillian Sharkey'

# Command name -> (command description, optional arguments)
#
cmds = {
	'add':			('Add new user', '[username]'),
	'renew':		('Renew user', '[username]'),
	'update':		('Update user', '[username]'),
	'delete':		('Delete user', '[username]'),
	'resetpw':		('Set new random password and mail it to user', '[username]'),
	'resetsh':		('Reset user\'s shell', '[username]'),
	'rename':		('Rename user', '[username]'),
	'convert':		('Change user to a different usertype', '[username]'),
	'disuser':		('Disuser a user', '[username [new username]]'),
	'reuser':		('Re-user a user', '[username]'),
	'show':			('Show user details', '[username]'),
	'freename':		('Check if a username is free', '[username]'),
	'search':		('Search user and dcu databases', '[username]'),
	'sync':			('Synchronise accounts with userdb (for RRS)', '[rrs-logfile]'),
	'sync_dcu_info':	('Interactive update of userdb using dcu database info', ''),
	'newbies_list':		('List all paid newbies', ''),
	'renewals_list':	('List all paid renewals (non-newbie)', ''),
	'freename_list':	('List all usernames that are taken', ''),
	'unpaid_list':		('List all non-renewed users', ''),
	'unpaid_list_normal':	('List all normal non-renewed users', ''),
	'unpaid_list_reset':	('List all normal non-renewed users with reset shells', ''),
	'unpaid_list_grace':	('List all grace non-renewed users', ''),
	'newyear':		('Prepare database for start of new academic year', ''),
	'unpaid_warn':		('Warn (mail) all non-renewed users', ''),
	'unpaid_disable':	('Disable all normal non-renewed users', ''),
	'unpaid_delete':	('Delete all grace non-renewed users', ''),
	'checkdb':		('Check database for inconsistencies', ''),
	'stats':		('Show database and account statistics', ''),
}

# Command groups
#
cmds_single_user = ('add', 'delete', 'renew', 'update', 'rename', 'convert')
cmds_single_account = ('resetpw', 'resetsh', 'disuser', 'reuser')
cmds_single_user_info = ('show', 'freename')
cmds_interactive_batch = ('search', 'sync', 'sync_dcu_info')
cmds_batch = ('newyear', 'unpaid_warn', 'unpaid_disable', 'unpaid_delete')
cmds_batch_info = ('newbies_list', 'renewals_list', 'freename_list', 'unpaid_list', 'unpaid_list_normal', 'unpaid_list_reset', 'unpaid_list_grace')
cmds_misc = ('checkdb', 'stats')

# Command group descriptions
#
cmds_group_desc = (
	(cmds_single_user,	'Single user commands'),
	(cmds_single_account,	'Single account commands'),
	(cmds_single_user_info,	'Single user information commands'),
	(cmds_interactive_batch,'Interactive batch commands'),
	(cmds_batch,		'Batch commands'),
	(cmds_batch_info,	'Batch information commands'),
	(cmds_misc,		'Miscellaneous commands')
)

# All commands
#
cmds_all = cmds.keys()

# Command option -> (optional argument, option description, commands that use option)
#
cmds_opts = (
	('h', '', 'Display this usage', cmds_all),
	('T', '', 'Test mode, show what would be done', cmds_all),
	('d', '', 'Perform database operations only', cmds_single_user),
	('a', '', 'Perform unix account operations only', cmds_single_user),
	('u', 'username', 'Unix username of who updated this user', cmds_single_user + ('disuser', 'reuser')),
	('f', '', 'Set newbie (fresher) to true', ('add', 'update')),
	('F', '', 'Opposite of -f', ('add', 'update')),
	('m', '', 'Send account details to user\'s alternate email address', ('add', 'renew', 'rename', 'resetpw')),
	('M', '', 'Opposite of -m', ('add', 'renew', 'rename', 'resetpw')),
	('o', '', 'Override warning errors', cmds_all),
	('p', '', 'Set new random password', ('add', 'renew')),
	('P', '', 'Opposite of -p', ('add', 'renew')),
	('t', 'usertype', 'Type of account', ('add', 'renew', 'update', 'convert')),
	('n', 'name', 'Real name or account description', ('add', 'renew', 'update', 'search')),
	('e', 'email', 'Alternative email address', ('add', 'renew', 'update')),
	('i', 'id', 'Student/Staff ID', ('add', 'renew', 'update', 'search')),
	('c', 'course', 'DCU course (abbreviation)', ('add', 'renew', 'update')),
	('y', 'year', 'DCU year', ('add', 'renew', 'update')),
	('s', 'years', 'paid Number of years paid (subscription)', ('add', 'renew', 'update')),
	('b', 'birthday', 'Birthday (format YYYY-MM-DD)', ('add', 'renew', 'update')),
	('q', '', 'Quiet mode', ('reuser',))
)

input_instructions = '\033[1mRETURN\033[0m: use [default] given  \033[1mTAB\033[0m: answer completion  \033[1mEOF\033[0m: give empty answer\n'

# Global variables.
#
opt = RBOpt()
udb = acc = None	 # Initialised later in main()

#-----------------------------------------------------------------------------#
# MAIN                                                                        #
#-----------------------------------------------------------------------------#

def main():
	"""Program entry function."""

	atexit.register(shutdown)

	if len(sys.argv) > 1 and sys.argv[1][0] != '-':
		opt.mode = sys.argv.pop(1)
		
	try:
		opts, args = getopt.getopt(sys.argv[1:], 'b:c:e:i:n:s:t:u:y:adfFhmMopPqT')
	except getopt.GetoptError, e:
		print e
		usage()
		sys.exit(1)
	
	for o, a in opts:
		if o == '-h':
			opt.help = 1
			usage()
			sys.exit(0)
		elif o == '-T':
			opt.test = 1
		elif o == '-d':
			opt.dbonly = 1
			opt.aconly = 0
		elif o == '-a':
			opt.aconly = 1
			opt.dbonly = 0
		elif o == '-u':
			opt.updatedby = a
		elif o == '-f':
			opt.newbie = 1
		elif o == '-F':
			opt.newbie = 0
		elif o == '-m':
			opt.mailuser = 1
		elif o == '-M':
			opt.mailuser = 0
		elif o == '-o':
			opt.override = 1
		elif o == '-p':
			opt.setpasswd = 1
		elif o == '-P':
			opt.setpasswd = 0
		elif o == '-t':
			opt.usertype = a
		elif o == '-n':
			opt.name = a
		elif o == '-e':
			opt.email = a
		elif o == '-i':
			opt.id = a
		elif o == '-c':
			opt.course = a
		elif o == '-y':
			opt.year = a
		elif o == '-s':
			opt.years_paid = a
		elif o == '-b':
			opt.birthday = a
		elif o == '-q':
			opt.quiet = 1

	if not cmds.has_key(opt.mode):
		usage()
		sys.exit(1)

	global udb, acc
	udb = RBUserDB()

	try:
		udb.connect()
	except ldap.LDAPError, e:
		error(e, 'Could not connect to user database')
		# not reached
	except KeyboardInterrupt:
		print
		sys.exit(1)
		# not reached

	acc = RBAccount()

	# Optional additional parameters after command line options.
	opt.args = args

	try:
		# Call function for specific mode.
		eval(opt.mode + "()")
	except KeyboardInterrupt:
		print
		sys.exit(1)
		# not reached
	except RBError, e:
		rberror(e)
		# not reached
	except ldap.LDAPError, e:
		error(e)
		# not reached

	sys.exit(0)

def shutdown():
	"""Cleanup function registered with atexit."""

	if udb:	udb.close()

def usage():
	"""Print command line usage and options."""

	if opt.mode and not cmds.has_key(opt.mode):
		print "Unknown command '%s'" % opt.mode
		opt.mode = None

	if not opt.mode:
		print "Usage: useradm command [options]"
		if opt.help:
			for grp in cmds_group_desc:
				print "[1m%s:[0m" % (grp[1])
				for cmd in grp[0]:
					print "  %-20s %s" % (cmd, cmds[cmd][0])
			print "'useradm command -h' for more info on a command's options & usage."
		else:
			print "'useradm -h' for more info on available commands"
	else:
		print cmds[opt.mode][0]
		print "Usage: useradm", opt.mode, "[options]", cmds[opt.mode][1]
		for i in cmds_opts:
			if opt.mode in i[3]:
				print " -%s %-15s%s" % (i[0], i[1], i[2])

#=============================================================================#
# MAIN FUNCTIONS                                                              #
#=============================================================================#

#-----------------------------------------------------------------------------#
# SINGLE USER COMMANDS                                                        #
#-----------------------------------------------------------------------------#

def add():
	"""Add a new user."""
	
	usr = RBUser()
	get_usertype(usr)
	# XXX
	#get_freeusername(usr, not usr.usertype in rbconfig.usertypes_system)
	get_freeusername(usr)

	while 1:
		try:
			get_id(usr)
			udb.get_userinfo_new(usr)
		except RBError, e:
			if not rberror(e, opt.id == None):
				break
			usr.id = None
		else:
			break
	
	udb.get_userdefaults_new(usr)
	get_createaccount(usr)
	get_setpasswd(usr)
	get_mailuser(usr)
	get_newbie(usr)
	get_name(usr)
	get_email(usr)
	get_course(usr)
	get_year(usr)
	get_years_paid(usr)
	get_birthday(usr)
	get_updatedby(usr)

	# End of user interaction, set options for override & test mode.
	#
	udb.setopt(opt)
	acc.setopt(opt)
	
	if opt.setpasswd:
		usr.passwd = acc.mkpasswd()

	if not opt.aconly:
		print "User added: %s %s (%s)" % (usr.usertype, usr.username, usr.name)
		udb.add(usr)

	if not opt.dbonly and usr.usertype != 'reserved':
		# If we're adding a "DCU" person and their email address is not
		# a redbrick one then use it to place in their .forward file.
		#
		email = None
		if usr.usertype in rbconfig.usertypes_dcu and not re.search(r'@.*redbrick\.dcu\.ie', usr.email):
			email = usr.email

		print "Account created: %s %s password: %s" % (usr.usertype, usr.username, usr.passwd)
		acc.add(usr.username, usr.usertype, usr.name, usr.passwd, email)
	else:
		# If not creating a Unix account but setting a new password is
		# required, do that now.
		#
		if opt.setpasswd:
			print "Account password set for %s password: %s" % (usr.username, usr.passwd)
			acc.setpasswd(usr.username, usr.passwd)

	if opt.mailuser:
		print "User mailed:", usr.email
		mailuser(usr)

def delete():
	"""Delete user."""

	usr = RBUser()
	get_username(usr)
	
	# End of user interaction, set options for override & test mode.
	udb.setopt(opt)
	acc.setopt(opt)

	if not opt.aconly:
		print 'User deleted:', usr.uid
		udb.delete(usr.uid)
	#if not opt.dbonly:
	#	print 'Account deleted:', usr.username
	#	acc.delete(usr.username)
	
def renew():
	"""Renew user."""

	usr = RBUser()
	curusr = RBUser()
	get_username(usr)
	newusr = RBUser(username = usr.username)

	try:
		udb.get_userinfo_renew(newusr, curusr)
	except RBError, e:
		if rberror(e, opt.username == None):
			return
	
	try:
		udb.check_unpaid(curusr)
	except RBError, e:
		if rberror(e, opt.username == None):
			return

	usr.usertype = newusr.usertype
	usr.id = newusr.id
	udb.get_userdefaults_renew(usr)
	
	get_setpasswd(usr)
	get_mailuser(usr)
	get_usertype(usr)

	while 1:
		get_id(usr)
	
		try:
			# If id was changed, need to get updated user info.
			#
			udb.get_userinfo_renew(usr)
		except RBError, e:
			if not rberror(e, opt.id == None):
				break
		else:
			break

	get_newbie(usr)
	get_name(usr, (curusr.name,))
	get_email(usr, (curusr.email,))
	get_course(usr, (curusr.course,))
	get_year(usr, (curusr.year,))
	get_years_paid(usr)
	get_birthday(usr)
	get_updatedby(usr)
	
	# End of user interaction, set options for override & test mode.
	udb.setopt(opt)
	acc.setopt(opt)

	if not opt.aconly:
		print 'User renewed:', usr.username
		udb.renew(usr)
	
	if opt.setpasswd:
		usr.passwd = acc.mkpasswd()
		print "Account password set for %s password: %s" % (usr.username, usr.passwd)
		acc.setpasswd(usr.username, usr.passwd)
	
	if not opt.dbonly:
		if usr.oldusertype != usr.usertype:
			print 'Account converted: %s -> %s' % (usr.username, usr.usertype)
			acc.convert(usr.username, usr.usertype)
	
		if not acc.valid_shell(acc.get_shell(usr.username)):
			print 'Account shell reset for', usr.username
			acc.reset_shell(usr.username)
	
	if opt.mailuser:
		print "User mailed:", usr.email
		mailuser(usr)
	
def update():
	"""Update user."""

	# Update mode only works on database.
	opt.dbonly = 1

	usr = RBUser()
	get_username(usr)
	udb.get_user_byname(usr)
	get_newbie(usr)
	defid = usr.id

	while 1:
		try:
			get_id(usr)
			newusr = RBUser(usertype = usr.usertype, id = usr.id)
			udb.get_dcu_byid(newusr)
		except RBError, e:
			if not rberror(e, opt.id == None):
				break
			usr.id = defid
		else:
			break

	get_name(usr, (newusr.name,))
	get_email(usr, (newusr.email,))
	get_course(usr, (newusr.course,))
	get_year(usr, (newusr.year,))
	get_years_paid(usr)
	get_birthday(usr)
	get_updatedby(usr)

	# End of user interaction, set options for override & test mode.
	udb.setopt(opt)
	acc.setopt(opt)
	
	print "User updated:", usr.username
	udb.update(usr)

def rename():
	"""Rename user."""

	usr = RBUser()
	newusr = RBUser()
	get_username(usr)
	get_freeusername(newusr)
	get_updatedby(usr)

	# End of user interaction, set options for override & test mode.
	udb.setopt(opt)
	acc.setopt(opt)
	
	print 'User renamed: %s -> %s' % (usr.uid, newusr.uid)
	udb.rename(usr, newusr)
	print 'Account renamed: %s -> %s' % (usr.uid, newusr.uid)
	acc.rename(usr, newusr)

def convert():
	"""Convert user."""

	usr = RBUser()
	get_username(usr)
	get_convert_usertype(usr)
	get_updatedby(usr)

	# End of user interaction, set options for override & test mode.
	udb.setopt(opt)
	acc.setopt(opt)

	if not opt.aconly:
		print 'User converted: %s -> %s' % (usr.username, usr.usertype)
		udb.convert(usr.username, usr.usertype, usr.updatedby)
	if not opt.dbonly:
		print 'Account converted: %s -> %s' % (usr.username, usr.usertype)
		acc.convert(usr.username, usr.usertype)

#-----------------------------------------------------------------------------#
# SINGLE ACCOUNT COMMANDS                                                     #
#-----------------------------------------------------------------------------#

def resetpw():
	"""Set new random password and mail it to user."""

	usr = RBUser()
	get_username(usr)
	udb.get_user_byname(usr)
	usr.passwd = rbconfig.gen_passwd()
	get_mailuser(usr)
	
	# End of user interaction, set options for override & test mode.
	udb.setopt(opt)
	acc.setopt(opt)

	print "Account password reset: %s password: %s" % (usr.uid, usr.passwd)
	udb.setpasswd(usr.uid, usr.passwd)

	if opt.mailuser:
		print "User mailed:", usr.email
		mailuser(usr)

def resetsh():
	"""Reset user's shell."""

	usr = RBUser()
	get_username(usr)
	
	# End of user interaction, set options for override & test mode.
	udb.setopt(opt)
	acc.setopt(opt)

	print 'Account shell reset for', usr.username
	acc.reset_shell(usr.username)

def disuser():
	"""Disuser a user."""

	usr = RBUser()
	get_username(usr)
	get_disuser_period(usr)
	get_disuser_message(usr)
	get_updatedby(usr)
	
	# End of user interaction, set options for override & test mode.
	udb.setopt(opt)
	acc.setopt(opt)

	acc.disuser(usr.username, usr.disuser_period)

def reuser():
	"""Re-user a user."""

	usr = RBUser()
	get_username(usr)
	get_updatedby(usr)
	
	# End of user interaction, set options for override & test mode.
	udb.setopt(opt)
	acc.setopt(opt)

#-----------------------------------------------------------------------------#
# SINGLE USER INFORMATION COMMANDS                                            #
#-----------------------------------------------------------------------------#

def show():
	"""Show user's database and account details."""

	usr = RBUser()
	get_username(usr)
	
	# End of user interaction, set options for override & test mode.
	udb.setopt(opt)

	udb.get_user_byname(usr)
	print header('User Information')
	udb.show(usr)
	print header('Account Information')
	acc.show(usr)

def freename():
	"""Check if a username is free."""

	usr = RBUser()
	if get_freeusername(usr):
		print "Username '%s' is free." % (usr.uid)

#-----------------------------------------------------------------------------#
# BATCH INTERACTIVE COMMANDS                                                  #
#-----------------------------------------------------------------------------#

def search():
	"""Search user and/or DCU databases."""

	pager = os.environ.get('PAGER', 'more')

	username = None
	if len(opt.args) > 0:
		username = opt.args.pop(0)
	if not username and not opt.id and not opt.name:
		username = ask('Enter username to search user database', optional = 1)
		if not username:
			opt.id = ask('Enter DCU Id number to search user and DCU databases', optional = 1)
			if not opt.id:
				opt.name = ask('Enter name to search user and DCU databases', optional = 1)
	
	if username:
		res = udb.search_users_byusername(username)
		fd = os.popen(pager, 'w')
		print >> fd, "User database search for username '%s' - %d match%s\n" % (username, len(res), len(res) != 1 and 'es' or '')
		show_search_results(res, fd)
		fd.close()
	elif opt.id or opt.name:
		fd = os.popen(pager, 'w')
		if opt.id:
			res = udb.search_users_byid(opt.id)
			print >> fd, "User database search for id '%s' - %d match%s\n" % (opt.id, len(res), len(res) != 1 and 'es' or '')
		else:
			res = udb.search_users_byname(opt.name)
			print >> fd, "User database search for name '%s' - %d match%s\n" % (opt.name, len(res), len(res) != 1 and 'es' or '')
		show_search_results(res, fd)
		print >> fd
		if opt.id:
			res = udb.search_dcu_byid(opt.id)
			print >> fd, "DCU database search for id '%s' - %d match%s\n" % (opt.id, len(res), len(res) != 1 and 'es' or '')
		else:
			res = udb.search_dcu_byname(opt.name)
			print >> fd, "DCU database search for name '%s' - %d match%s\n" % (opt.name, len(res), len(res) != 1 and 'es' or '')
		show_search_results(res, fd)
		fd.close()
	else:
		raise RBFatalError('No search term given!')

def show_search_results(res, fd):
	"""Actual routine to display search results on given output steam."""

	if res:
		print >> fd, '%-*s %-*s %-8s %-30s %-6s %-4s %s' % (rbconfig.maxlen_uname, 'username', rbconfig.maxlen_group, 'usertype', 'id', 'name', 'course', 'year', 'email')
		print >> fd, '%s %s %s %s %s %s %s' % ('-' * rbconfig.maxlen_uname, '-' * rbconfig.maxlen_group, '-' * 8, '-' * 30, '-' * 6, '-' * 4, '-' * 30)
		for username, usertype, id, name, course, year, email in res:
			print >> fd, "%-*s %-*s %-8s %-30.30s %-6.6s %-4.4s %s" % (rbconfig.maxlen_uname, username or '-', rbconfig.maxlen_group, usertype or '-', id != None and id or '-', name, course or '-', year or '-', email)

def sync():
	"""Synchronise accounts (i.e. no changes are made to userdb) after an
	offline update to user database with RRS. Needs rrs.log to process
	renames and password resets for existing accounts.
	
	Procedure:
	
	1. Process all renames, only applicable to existing accounts. Taken from
	rrs.log. Keep a mapping of username renewals. Note there may be
	multiple rename entries.
	  
	2. Process all conversions, only applicable to existing accounts.
	Detected by comparing Unix group and usertype in database.
	
	3. Process all deletions, only applicable to existing accounts.
	Detected by checking for unix accounts missing a database entry. All
	accounts should be renamed all ready so the only accounts left with
	missing database entries must have been deleted. Confirmation is
	required for each deletion, however.
	
	4. Process all adds, only applicable to new users. Detected by user
	database entry being a newbie, paid and having no unix account.
	Password is generated on-the-fly and mailed.
	
	5. Process all renewals, only applicable to existing users. Detected by
	user database entry being a non-newbie, paid and having an existing
	unix account. Reset account shell if needed. Password is reset
	on-the-fly and mailed if flagged in rrs.log. The flag in the logfile
	will be marked on the original username so the rename map is used to
	map this to the current username.
	
	"""

	user_rename_map = {}
	user_rename_reverse_map = {}
	reset_password = {}
	
	get_rrslog()
	
	# XXX: Set override by default ?
	# Set options for override & test mode.
	udb.setopt(opt)
	acc.setopt(opt)

	#-------------#
	# sync_rename #
	#-------------#
	
	print '===> start sync_rename'
	pause()

	fd = open(opt.rrslog, 'r')
	for line in fd.readlines():
		tlog = line.rstrip().split(':')
	
		# We ignore renames of new accounts as we just go by the final
		# entry in the database.
		#
		if tlog[4] != 'rename-existing':
			continue

		user_rename_map[tlog[5]] = tlog[6]
               
		try:
			pwd.getpwnam(tlog[5])
		except KeyError:
			# Old account doesn't exist, must be renamed already.
			if opt.test:
				print 'SKIPPED: account rename: %s -> %s' % (tlog[5], tlog[6])
		else:
			print 'Account renamed: %s -> %s' % (tlog[5], tlog[6])
			acc.rename(tlog[5], tlog[6])
	fd.close()
	
	#--------------#
	# sync_convert #
	#--------------#

	print '\n===> start sync_convert'
	pause()
	
	for username, usertype in udb.non_system_list():
		group = None
		try:
			pw = pwd.getpwnam(username)
		except KeyError:
			# This user must be a newbie and the account hasn't
			# been added yet. Conversions only apply to existing
			# accounts so do nothing!
			#
			if opt.test:
				print 'IGNORED non existant account:', username
		else:
			group = acc.get_groupname_byid(pw[3])
			if group != usertype:
				print 'Account converted: %s: %s -> %s' % (username, group, usertype)
				acc.convert(username, usertype)

	#-------------#
	# sync_delete #
	#-------------#

	print '\n===> start sync_delete'
	pause()

	for pw in pwd.getpwall():
		try:
			udb.check_user_byname(pw[0])
		except RBError:
			# User doesn't exist in database, ask to delete it.
			#
			if yesno("Delete account %s" % pw[0]):
				print 'Account deleted: %s' % pw[0]
				acc.delete(pw[0])
		else:
			# User exists in database, do nothing!
			pass
	
	#----------#
	# sync_add #
	#----------#

	print '\n===> start sync_add'
	pause()

	for username in udb.newbies_list():
		try:
			pwd.getpwnam(username)
		except KeyError:
			usr = RBUser(username = username)
			# Don't catch exception as user is known to exist.
			udb.get_user_byname(usr)
			usr.passwd = acc.mkpasswd()

			# If we're adding a "DCU" person and their email address is not
			# a redbrick one then use it to place in their .forward file.
			#
			email = None
			if usr.usertype in rbconfig.usertypes_dcu and not re.search(r'@.*redbrick\.dcu\.ie', usr.email):
				email = usr.email

			print "Account created: %s %s password: %s" % (usr.usertype, usr.username, usr.passwd)
			acc.add(usr.username, usr.usertype, usr.name, usr.passwd, email)
			print "User mailed:", usr.email
			mailuser(usr)
		else:
			# Account has already been added, do nothing!
			if opt.test:
				print 'SKIPPED: account create:', username

	#------------#
	# sync_renew #
	#------------#

	print '\n===> start sync_renew'
	pause()

	# First find out which users we have to reset passwords for.
	#
	fd = open(opt.rrslog, 'r')
	for line in fd.readlines():
		tlog = line.split(':')
		
		# tlog[7] denotes if a new password is needed
		#
		if tlog[4] == 'renew' and tlog[7] == '1':
			# Traverse user_rename_map like a linked list to find
			# the current username in case the original was
			# renamed. This map is setup during the sync_rename
			# step.
			#
			cur = tlog[5]
			while user_rename_map.has_key(cur):
				cur = user_rename_map[cur]

			# Have a reverse map so we can map from current
			# username back to the original..
			#
			if cur != tlog[5]:
				user_rename_reverse_map[cur] = tlog[5]

			# Flag this user for a new password.
			#
			reset_password[cur] = 1
	fd.close()

	# Now 'renew' each user.
	#
	for username in udb.renewals_list():
		try:
			pwd.getpwnam(username)
		except KeyError:
			# Accounts should have been renamed beforehand so we
			# should never get here!
			#
			print "SKIPPED: User '$username' missing account"
		else:
			usr = RBUser(username = username)
			# Don't catch exception as user is known to exist.
			udb.get_user_byname(usr)

			# Get original username if user was renamed.
			if user_rename_reverse_map.has_key(username):
				oldusername = user_rename_reverse_map[username]
			else:
				oldusername = username

			if not acc.valid_shell(acc.get_shell(username)):
				print 'Account shell reset for', username
				acc.reset_shell(username)
		
			# Set a new password if they need one.
			#
			if reset_password.has_key(username):
				usr.passwd = acc.mkpasswd()
				print 'Account password reset for %s password: %s' % (username, usr.passwd)
				acc.setpasswd(username, usr.passwd)
				print 'User mailed:', usr.email
				mailuser(usr)

	print '\nsync completed.'

def sync_dcu_info():
	"""Interactive update of user database using dcu database information."""

	print 'Comparing user and DCU databases. NOTE: please be patient'
	print 'this takes some time...\n'

	# Set options for override & test mode.
	udb.setopt(opt)
	acc.setopt(opt)

#-----------------------------------------------------------------------------#
# BATCH INFORMATION COMMANDS                                                  #
#-----------------------------------------------------------------------------#

def newbies_list():
	"""List all paid newbies."""

	for username in udb.newbies_list():
		print username
		
def renewals_list():
	"""List all paid renewals (non-newbie)."""

	for username in udb.renewals_list():
		print username

def freename_list():
	"""List all usernames that are taken."""

	for username in udb.freename_list():
		print username

def unpaid_list():
	"""Print list of all non-renewed users."""

	for username in udb.unpaid_list():
		print username

def unpaid_list_normal():
	"""Print list of all normal non-renewed users."""

	for username in udb.unpaid_list_normal():
		print username

def unpaid_list_reset():
	"""Print list of all normal non-renewed users with reset shells."""
	
	for username in udb.unpaid_list_normal():
		if acc.get_shell(username) != rbconfig.expired_shell:
			print username

def unpaid_list_grace():
	"""Print list of all grace non-renewed users."""

	for username in udb.unpaid_list_grace():
		print username

#-----------------------------------------------------------------------------#
# BATCH COMMANDS                                                              #
#-----------------------------------------------------------------------------#

def newyear():
	"""Prepare database for start of new academic year."""

	# Set options for override & test mode.
	udb.setopt(opt)
	acc.setopt(opt)

	print 'Prepared database for start of new academic year'
	udb.newyear()

def unpaid_warn():
	"""Mail a reminder/warning message to all non-renewed users."""
	
	# Set options for override & test mode.
	udb.setopt(opt)
	acc.setopt(opt)

	for username in udb.unpaid_list():
		usr = RBUser(username = username)
		udb.get_user_byname(usr)
		print "Warned user:", username
		mail_unpaid(usr)

def unpaid_disable():
	"""Disable all normal non-renewed users."""

	# Set options for override & test mode.
	udb.setopt(opt)
	acc.setopt(opt)

	for username in udb.unpaid_list_normal():
		if acc.get_shell(username) != rbconfig.expired_shell:
			print "Account disabled:", username
			acc.set_shell(username, rbconfig.expired_shell)
	
def unpaid_delete():
	"""Delete all grace non-renewed users."""

	# Set options for override & test mode.
	udb.setopt(opt)
	acc.setopt(opt)

	for username in udb.unpaid_list_grace():
		print 'User deleted:', username
		udb.delete(username)
		print 'Account deleted:', username
		acc.delete(username)

#-----------------------------------------------------------------------------#
# MISCELLANEOUS COMMANDS                                                      #
#-----------------------------------------------------------------------------#

def checkdb():
	"""Check database for inconsistencies."""

	# First make sure all Unix accounts are in the userdb. Also check
	# their group/usertype match (ignore differences for the system
	# usertype).
	#
	hdr = header('User database problems')
	pwusers = {}
	for pw in pwd.getpwall():
		pwusers[pw[0]] = 1
		group = acc.get_groupname_byid(pw[3])
		try:
			usertype = udb.get_usertype_byname(pw[0])
		except RBError:
			if hdr:
				print hdr
				hdr = None
			print "%-*s MISSING from userdb  (%-*s)" % (pw[0], rbconfig.maxlen_uname, group, rbconfig.maxlen_group),
			if not os.access('%s/%s' % (rbconfig.signaway_state_dir, pw[0]), os.F_OK):
				print '[never logged in]'
			else:
				print
		else:
			if group != usertype and usertype != 'system':
				if hdr:
					print hdr
					hdr = None
				print "%-8s GROUP/TYPE MISMATCH  (%-8s) (%-8s)" % (pw[0], group, usertype)

	# Check for entries in the userdb that are missing an account (ignoring
	# reserved entries). Also check email address.
	#
	for username in udb.user_list():
		usr = RBUser(username = username)
		udb.get_user_byname(usr)
		if usr.usertype != 'reserved' and not pwusers.has_key(username):
			if hdr:
				print hdr
				hdr = None
			print "%-8s MISSING unix account (%-8s)" % (username, usr.usertype)
		if usr.usertype in ('member', 'staff', 'committe') and not re.search(r'.+@.*dcu\.ie', usr.email, re.I):
			if hdr:
				print hdr
				hdr = None
			print "%-8s does not have dcu email address: %s" % (username, usr.email)

def stats():
	"""Show database and account statistics."""

	if not opt.aconly:
		print header('User database stats')
		udb.stats()
	if not opt.dbonly:
		print header('Account stats')
		acc.stats()

#-----------------------------------------------------------------------------#
# USER INPUT FUNCTIONS                                                        #
#-----------------------------------------------------------------------------#

def ask(prompt, default = None, optional = 0, hints = None):
	"""Ask a question using given prompt and return user's answer.

	A default answer maybe provided which is returned if no answer is given
	(i.e. user hits RETURN).
 
	If optional is false (the default) an answer is required. So if no
	default answer is given and the user presses RETURN, the question will
	be repeated.

	If optional is true, the first answer given is returned. If a default
	is provided an empty answer may be given by sending EOF (typically
	Control-D). If no default is provided an empty answer may be given by
	pressing RETURN.
	
	If there is more than one default answer these can be provided in the
	form of "hints" which the user can cycle through by hitting TAB. The
	default answer is also available by pressing TAB.

	"""
	
	def complete(text, state):
		"""Completion function used by readline module for ask().

		If no text typed in yet, offer all hints. Otherwise offer only
		hints that begin with the given text.

		"""

		if not text and len(hints) > state:
			return str(hints[state])
		else:
			tmp = [i for i in hints if i.startswith(text)]
			if len(tmp) > state:
				return str(tmp[state])
		return None

	global input_instructions
	if input_instructions:
		print input_instructions
		input_instructions = None
	
	if hints == None:
		hints = []

	if default == None:
		defans = 'no default'
	else:
		defans = default

	hints = [i for i in hints if i != None]
	num_hints = len(hints)

	if default != None:
		if default not in hints:
			hints.insert(0, default)
		else:
			num_hints -= 1

	prompt = '%s\n%s%s[%s] >> ' % (prompt, optional and '(optional) ' or '', num_hints and '(hints) ' or '', defans)

	readline.parse_and_bind('tab: menu-complete')
	readline.set_completer(complete)

	ans = None
	while ans == None or ans == '':
		try:
			ans = raw_input(prompt)
		except EOFError:
			print
			ans = None
		else:
			if not ans:
				ans = default
		print
		if optional:
			break
	return ans

def yesno(prompt, default = None):
	"""Prompt for confirmation to a question. Returns boolean."""

	global input_instructions
	if input_instructions:
		print input_instructions
		input_instructions = None
	
	if default == None:
		defans = 'no default'
	else:
		if default: defans = 'yes'
		else: defans = 'no'

	prompt = '%s\n[%s] (Y/N) ? ' % (prompt, defans)

	ans = None
	while 1:
		try:
			ans = raw_input(prompt)
		except EOFError:
			print
			ans = None
		else:
			print
			if not ans and not default == None:
				return default

		if ans:
			if re.search(r'^[yY]', ans):
				return 1
			elif re.search(r'^[nN]', ans):
				return 0

def pause():
	"""Prompt for user input to continue."""

	print 'Press RETURN to continue...'
	try:
		raw_input()
	except EOFError:
		pass

#-----------------------------------------------------------------------------#
# MISCELLANEOUS FUNCTIONS                                                     #
#-----------------------------------------------------------------------------#

def header(mesg):
	"""Return a simple header string for given message."""

	return '\n' + mesg + '\n' + '=' * len(mesg)

#-----------------------------------------------------------------------------#
# USER MAILING FUNCTIONS                                                      #
#-----------------------------------------------------------------------------#

def mailuser(usr):
	"""Mail user's account details to their alternate email address."""
	
	fd = sendmail_open()
	fd.write(
"""From: RedBrick Admin Team <admins@redbrick.dcu.ie>
Subject: Your RedBrick Account
To: %s
Reply-To: admin-request@redbrick.dcu.ie

Welcome to RedBrick, the DCU Networking Society!

Your RedBrick Account details are:

""" % usr.email)

	fd.write('%21s: %s\n' % ('username', usr.username))
	if usr.passwd:
		fd.write('%21s: %s\n\n' % ('password', usr.passwd))
	fd.write('%21s: %s\n' % ('account type', usr.usertype))
        fd.write('%21s: %s\n' % ('name', usr.name))
	if usr.id != None:
		fd.write('%21s: %s\n' % ('id number',  usr.id))
	if usr.course:
		fd.write('%21s: %s\n' % ('course', usr.course))
	if usr.year != None:
		fd.write('%21s: %s\n' % ('year', usr.year))

	fd.write(
"""
your RedBrick webpage: http://www.redbrick.dcu.ie/~%s
  your RedBrick email: %s@RedBrick.DCU.ie

Information on how to login is at:
  http://www.redbrick.dcu.ie/help/login

We recommend that you change your password as soon as you login!

Problems with your password or wish to change your username? Contact:
  admin-request@redbrick.dcu.ie

Problems using RedBrick in general or not sure what to do? Contact:
  helpdesk-request@redbrick.dcu.ie

Have fun!

  - RedBrick Admin Team <admins@redbrick.dcu.ie>
""" % (usr.username, usr.username))

	sendmail_close(fd)

def mail_unpaid(usr):
	"""Mail a warning to a non-renewed user."""

	fd = sendmail_open()
	fd.write(
"""From: RedBrick Admin Team <admins@redbrick.dcu.ie>
Subject: Time to renew your RedBrick account!
To: %s@redbrick.dcu.ie
"""  % usr.username)

	if usr.email.lower().find('%s@redbrick.dcu.ie' % usr.username) == -1:
		print >> fd, 'Cc:', usr.email

	fd.write(
"""Reply-To: accounts@redbrick.dcu.ie

Hey there,

It's that time again to renew your RedBrick account!

Members and Staff
-----------------
All you need to do is find one of the members on the committee and pay
the ¤2.50 fee. If you have left DCU, you should be applying for
associate membership instead (see below).

Associates and Guests
---------------------
If you've left DCU or are currently an associate/guest, you'll need to
pay the ¤6.50 fee in one of two ways: meet up with one of the members of
the committee or alternatively, pay the money directly into the RedBrick
bank account. Details are on the website here:

http://www.redbrick.dcu.ie/help/joining/

You may also be interested in our special 5 year membership offer for
associates - this is available at a discounted price of ¤26.

Please Note!
------------""")

	if usr.years_paid == 0:
		fd.write(
"""
If you do not renew within the following month, your account will be
disabled at the start of December. Your account will remain on the
system however for a grace period of one year - you just won't be able
to login. So don't worry, it won't be deleted any time soon! You can
renew at any time during the year.
""")
	else:
		fd.write(
"""
If you do not renew within the following month, your account WILL BE
DELETED at the start of Decemeber. This is because you were not recorded
as having paid for last year and as such are nearing the end of your one
year 'grace' period to renew. Please make sure to renew as soon as
possible otherwise please contact us at: committee@redbrick.dcu.ie.
""")
	fd.write(
"""
If in fact you have renewed and have received this email in error, it is
important you let us know. Just reply to this email and tell us how and
when you renewed and we'll sort it out.

For your information, your current RedBrick account details are:

             username: %s
         account type: %s
                 name: %s
    alternative email: %s
""" % (usr.username, usr.usertype, usr.name, usr.email))

	if usr.id != None:
		fd.write('%21s: %s\n' % ('id number',  usr.id))
	if usr.course:
		fd.write('%21s: %s\n' % ('course', usr.course))
	if usr.year != None:
		fd.write('%21s: %s\n' % ('year', usr.year))
	
	fd.write(
"""
If any of the above details are wrong, please correct them when you
renew!

  - RedBrick Admin Team <admins@redbrick.dcu.ie>
""")
	sendmail_close(fd)

def mail_committee(subject, body):
	"""Email committee with given subject and message body."""

	fd = sendmail_open()
	fd.write(
"""From: RedBrick Admin Team <admins@redbrick.dcu.ie>
Subject: %s
To: committee@redbrick.dcu.ie

%s
""" % (subject, body))
	sendmail_close(fd)
	
def sendmail_open():
	"""Return file descriptor to write email message to."""

	if opt.test:
		print >> sys.stderr, header('Email message that would be sent')
		return sys.stderr
	else:
		return os.popen('/usr/sbin/sendmail', 'w')

def sendmail_close(fd):
	"""Close sendmail file descriptor."""
	
	if not opt.test:
		fd.close()

#-----------------------------------------------------------------------------#
# GET USER DATA FUNCTIONS                                                     #
#-----------------------------------------------------------------------------#

def get_username(usr, check_user_exists = 1):
	"""Get an existing username."""

	if len(opt.args) > 0 and opt.args[0]:
		usr.uid = opt.username = opt.args.pop(0)
		interact = 0
	else:
		interact = 1
		
	while 1:
		if interact:
			usr.uid = ask('Enter username')
		try:
			udb.check_username(usr.uid)

			if check_user_exists:
				tmpusr = RBUser(uid = usr.uid)
				udb.get_user_byname(tmpusr)
				udb.check_user_byname(usr.uid)
				# XXX: disabling for Shrapnel FTTB
				#acc.check_account_byname(tmpusr)
		except RBError, e:
			if not rberror(e, interact):
				break
		else:
			break
		if not interact:
			break

def get_freeusername(usr, check_reserved = 1):
	"""Get a new (free) username."""

	if len(opt.args) > 0 and opt.args[0]:
		usr.uid = opt.args.pop(0)
		interact = 0
	else:
		interact = 1
	
	while 1:
		if interact:
			usr.uid = ask('Enter new username')
		try:
			udb.check_username(usr.uid)
			udb.check_userfree(usr.uid, check_reserved)
		except RBError, e:	
			if not rberror(e, interact):
				break
		else:
			break
		if not interact:
			return 0
	return 1

def get_usertype(usr):
	"""Get usertype."""

	usr.oldusertype = usr.usertype

	if opt.usertype:
		usr.usertype = opt.usertype
		interact = 0
	else:
		interact = 1
		print "Usertype must be specified. List of valid usertypes:\n"
		for i in rbconfig.usertypes_list:
			if opt.mode != 'renew' or i in rbconfig.usertypes_paying:
				print " %-12s %s" % (i, rbconfig.usertypes[i])
		print

	defans = usr.usertype or 'member'

	while 1:	
		if interact:
			usr.usertype = ask('Enter usertype', defans, hints = [i for i in rbconfig.usertypes_list if opt.mode != 'renew' or i in rbconfig.usertypes_paying])
		try:
			if opt.mode == 'renew':
				udb.check_renewal_usertype(usr.usertype)
			else:
				udb.check_usertype(usr.usertype)
		except RBError, e:
			if not rberror(e, interact):
				break
		else:
			break

def get_convert_usertype(usr):
	"""Get usertype to convert to."""

	if opt.usertype:
		usr.usertype = opt.usertype
		interact = 0
	else:
		interact = 1
		print "Conversion usertype must be specified. List of valid usertypes:\n"
		for i in rbconfig.usertypes_list:
			print " %-12s %s" % (i, rbconfig.usertypes[i])

		print "\nSpecial committee positions (usertype is 'committe'):\n"
		for i, j in rbconfig.convert_usertypes.items():
			print " %-12s %s" % (i, j)
		print

	while 1:	
		if interact:
			usr.usertype = ask('Enter conversion usertype', hints = list(rbconfig.usertypes_list) + rbconfig.convert_usertypes.keys())
		try:
			udb.check_convert_usertype(usr.usertype)
		except RBError, e:
			if not rberror(e, interact):
				break
		else:
			break

def get_id(usr):
	"""Get DCU ID."""

	if usr.usertype not in rbconfig.usertypes_dcu and opt.mode != 'update':
		return
		
	if opt.id != None:
		usr.id = opt.id
		interact = 0
	else:
		interact = 1
		
	defans = usr.id

	while 1:
		if interact:
			usr.id = ask('Enter student/staff id', defans, optional = opt.mode == 'update' or usr.usertype == 'committe')
		try:
			if usr.id:
				usr.id = int(usr.id)
				udb.check_id(usr)
		except (ValueError, RBError), e:
			if not rberror(e, interact):
				break
		else:
			break

def get_name(usr, hints = None):
	"""Get name (or account description)."""

	if opt.name:
		usr.name = opt.name
		interact = 0
	else:
		interact = 1
		
	defans = usr.name
	
	while 1:
		if interact:
			usr.name = ask("Enter name (or account description)", defans, hints = hints)
		try:
			udb.check_name(usr)
		except RBError, e:
			if not rberror(e, interact):
				break
		else:
			break

def get_mailuser(usr):
	"""Ask wheter to mail user their details."""

	if opt.mailuser != None:
		return
	
	if not usr.usertype == 'reserved':
		# By default mail them.
		opt.mailuser = 1

		# If only adding database entry, don't mail.
		if opt.mode == 'add' and opt.dbonly:
			opt.mailuser = 0

		opt.mailuser = yesno('Mail account details to user', opt.mailuser)
	else:
		opt.mailuser = 0

def get_createaccount(usr):
	"""Ask if account should be created."""

	if opt.dbonly != None and opt.aconly != None:
		return
	
	# XXX
	#if usr.usertype != 'reserved' and not yesno('Create account', not usr.usertype in rbconfig.usertypes_system):
	if not yesno('Create account', 1):
		opt.dbonly = 1
		opt.aconly = 0

def get_setpasswd(usr):
	"""Ask if new random password should be set."""

	if opt.setpasswd != None:
		return

	# XXX
	#if opt.dbonly != None:
	#	opt.setpasswd = not opt.dbonly
	#	return

	# XXX
	#if usr.usertype != 'reserved':
	if opt.mode == 'renew':
		opt.setpasswd = 0
	else:
		opt.setpasswd = 1
	opt.setpasswd = yesno('Set new random password', opt.setpasswd)
	#else:
	#	opt.setpasswd = 0

def get_newbie(usr):
	"""Get newbie boolean."""

	if opt.newbie != None:
		usr.newbie = opt.newbie
		return

	usr.newbie = yesno('Flag as a new user', usr.newbie)
	
def get_years_paid(usr):
	"""Get years paid."""

	if not usr.usertype in rbconfig.usertypes_paying and opt.mode != 'update':
		return
	
	if opt.years_paid != None:
		usr.years_paid = opt.years_paid
		interact = 0
	else:
		interact = 1

	if opt.mode == 'add' and usr.years_paid == None:
		usr.years_paid = 1
	defans = usr.years_paid

	while 1:
		if interact:
			usr.years_paid = ask('Enter number of years paid', defans, optional = opt.mode == 'update' or usr.usertype in ('committe', 'guest'))
		try:
			if usr.years_paid:
				usr.years_paid = int(usr.years_paid)
				udb.check_years_paid(usr)
		except (ValueError, RBError), e:
			if not rberror(e, interact):
				break
		else:
			break

def get_course(usr, hints = None):
	"""Get DCU course."""

	if usr.usertype not in ('member', 'committee') and opt.mode != 'update':
		return
	if opt.course:
		usr.course = opt.course
		return
	usr.course = ask('Enter course', usr.course, optional = opt.mode == 'update' or usr.usertype == 'committe', hints = hints)

def get_year(usr, hints = None):
	"""Get DCU year."""

	if usr.usertype not in ('member', 'committee') and opt.mode != 'update':
		return
	if opt.year != None:
		usr.year = opt.year
		return
	usr.year = ask('Enter year', usr.year, optional = opt.mode == 'update' or usr.usertype == 'committe', hints = hints)

def get_email(usr, hints = None):
	"""Get alternative email address."""

	if opt.email:
		usr.email = opt.email
		interact = 0
	else:
		interact = 1
	
	defans = usr.email

	while 1:
		if interact:
			usr.email = ask('Enter email', defans, hints = hints)
		try:
			udb.check_email(usr)
		except RBError, e:
			if not rberror(e, interact):
				break
		else:
			break

def get_updatedby(usr):
	"""Get username of who is performing the action.

	Uses LOGNAME environment variable by default unless it's 'root' in
	which case no default is provided. There is no actual restriction on
	using 'root', although its use (or any other generic username) is
	strongly not recommended.

	"""

	if opt.updatedby:
		usr.updatedby = opt.updatedby
		interact = 0
	else:
		interact = 1
		usr.updatedby = os.environ.get('LOGNAME') or os.environ.get('SU_FROM')

	defans = usr.updatedby

	while 1:
		if interact:
			usr.updatedby = ask('Enter who updated this user (give Unix username)', defans)
		try:
			udb.check_updatedby(usr.updatedby)
		except RBError, e:
			if not rberror(e, interact):
				break
		else:
			break

def get_birthday(usr):
	"""Get (optional) birthday."""

	if not usr.usertype in rbconfig.usertypes_paying:
		return
	
	if opt.birthday != None:
		usr.birthday = opt.birthday or None
		interact = 0
	else:
		interact = 1

	defans = usr.birthday

	while 1:
		if interact:
			usr.birthday = ask("Enter birthday as 'YYYY-MM-DD'", defans, optional = 1)
		try:
			udb.check_birthday(usr)
		except RBError, e:
			if not rberror(e, interact):
				break
		else:
			break

def get_disuser_period(usr):
	"""Get (optional) period of disuserment."""

	if len(opt.args) > 0:
		usr.disuser_period = opt.args[0]
		interact = 0
	else:
		interact = 1
	
	while 1:
		if interact:
			usr.disuser_period = ask("If the account is to be automatically re-enabled, enter a valid at(1) timespec,\ne.g: '5pm', '12am + 2 weeks', 'now + 1 month' (see at man page).", optional = 1)
		try:
			udb.check_disuser_period(usr)
		except RBError, e:
			if not rberror(e, interact):
				break
		else:
			break

def get_disuser_message(usr):
	"""Get message to display when disusered user tries to log in."""

	file = "%s/%s" % (rbconfig.daft_dir, usr.username)
	editor = os.environ.get('EDITOR', os.environ.get('VISUAL', 'vi'))
	
	while 1:
		if not os.path.isfile(file):
			fd = open(file, "w")
			fd.write("The contents of this file will be displayed when %s logs in.\nThe reason for disuserment should be placed here.\n" % (usr.username))
			fd.close()
		mtime = os.path.getmtime(file)
		os.system("%s %s" % (acc.shquote(editor), acc.shquote(file)))

		if not os.path.isfile(file) or not os.path.getsize(file) or mtime == os.path.getmtime(file):
			if not rberror(RBWarningError('Unchanged disuser message file detected'), 1):
				break
		else:
			break
	os.chmod(file, 0644)

def get_rrslog():
	"""Get name of RRS log file."""

	if len(opt.args) > 0 and opt.args[0]:
		opt.rrslog = opt.args.pop(0)
		interact = 0
	else:
		interact = 1
	
	while 1:
		if interact:
			opt.rrslog = ask('Enter name of RRS logfile')
		try:
			open(opt.rrslog, 'r').close()
		except IOError, e:
			if not rberror(e, interact):
				break
		else:
			break
	
#-----------------------------------------------------------------------------#
# ERROR HANDLING                                                              #
#-----------------------------------------------------------------------------#

def rberror(e, interactive = 0):
	"""rberror(e[, interactive]) -> status

	Handle (mostly) RBError exceptions.
	
	Interactive: If e is a RBWarningError, prompt to override this error.
	If overridden, return false. Otherwise and for all other errors,
	return true.

	Not interactive: If e is a RBWarningError and the override option was
	set on the command line, return false. Otherwise and for all other
	errors, exit the program.

	"""

	res = None
	if not isinstance(e, RBError):
		print "FATAL:",
	print e
	
	if not isinstance(e, RBWarningError):
		if interactive:
			print
			return 1
	else:
		if interactive:
			print
			if yesno('Ignore this error?'):
				opt.override = 1
				return 0
			else:
				return 1
		elif opt.override:
			print "[IGNORED]\n"
			return 0

	# If we reach here we're not in interactive mode and the override
	# option wasn't set, so all errors result in program exit.
	#
	print
	sys.exit(1)
	
def error(e, mesg = None):
	"""error(e[, mesg])
	
	Handle general exceptions: prints the 'FATAL:' prefix, optional
	message followed by the exception message. Exits program.
	
	"""
	
	print "FATAL: ",
	if mesg:
		print mesg
	print e
	print
	sys.exit(1)

#-----------------------------------------------------------------------------#
# If module is called as script, run main()                                   #
#-----------------------------------------------------------------------------#

if __name__ == "__main__":
	main()
