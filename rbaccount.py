#-----------------------------------------------------------------------------#
# MODULE DESCRIPTION                                                          #
#-----------------------------------------------------------------------------#

"""RedBrick Account Module; contains RBAccount class."""

# System modules

import grp
import os
import pwd
import random
import re
import shutil
import sys

# RedBrick modules

import rbconfig
from rberror import *
from rbopt import *
from rbuser import *

#-----------------------------------------------------------------------------#
# DATA                                                                        #
#-----------------------------------------------------------------------------#

__version__ = '$Revision: 1.3 $'
__author__  = 'Cillian Sharkey'

#-----------------------------------------------------------------------------#
# CLASSES                                                                     #
#-----------------------------------------------------------------------------#

class RBAccount:
	"""Class to interface with Unix accounts."""

	def __init__(self):
		"""Create new RBAccount object."""

		self.opt = RBOpt()
	
	def setopt(self, opt):
		"""Use given RBOpt object to retrieve options."""

		self.opt = opt
		
	#---------------------------------------------------------------------#
	# SINGLE ACCOUNT METHODS                                              #
	#---------------------------------------------------------------------#
	
	def add(self, usr):
		"""Add account."""
		
		# Create home and webtree directory and populate.
		#
		webtree = rbconfig.gen_webtree(usr.uid)
		self.wrapper(os.mkdir, webtree, 0711)
		self.wrapper(os.chown, webtree, usr.uidNumber, usr.gidNumber)
		self.cmd('%s -Rp %s %s' % (rbconfig.command_cp, rbconfig.dir_skel, usr.homeDirectory))
		self.wrapper(os.chmod, usr.homeDirectory, 0711)
		self.wrapper(os.symlink, webtree, '%s/public_html' % usr.homeDirectory)

		# Add a .forward file in their home directory to point to their
		# alternate email address, but only if they're a dcu person and
		# have an alternate email that's not a redbrick address.
		#
		if usr.usertype in rbconfig.usertypes_dcu and usr.altmail and not re.search(r'@.*redbrick\.dcu\.ie', usr.altmail):
			forward_file = '%s/.forward' % usr.homeDirectory
			fd = self.my_open(forward_file)
			fd.write('%s\n' % usr.altmail)
			self.my_close(fd)
			self.wrapper(os.chmod, forward_file, 0600)

		# Change user & group ownership recursively on home directory.
		#
		self.cmd('%s -Rh %s:%s %s' % (rbconfig.command_chown, usr.uidNumber, usr.usertype, self.shquote(usr.homeDirectory)))

		# Set quotas for each filesystem.
		#
		for fs, (bqs, bqh, iqs, iqh) in rbconfig.gen_quotas(usr.usertype).items():
			self.quota_set(usr.uidNumber, fs, bqs, bqh, iqs, iqh)

		# Add to redbrick announcement mailing lists.
		#
		self.list_add('announce-redbrick', '%s@redbrick.dcu.ie' % usr.uid)
		self.list_add('redbrick-newsletter', '%s@redbrick.dcu.ie' % usr.uid)
	
	def delete(self, usr):
		"""Delete a local Unix account."""

		# Zero out quotas.
		#
		for fs in rbconfig.gen_quotas().keys():
			self.quota_delete(usr.uidNumber, fs)
		
		# Remove home directory and webtree. Don't bomb out if the
		# directories don't exist (i.e. ignore OSError).
		#
		try:
			self.wrapper(shutil.rmtree, usr.homeDirectory)
		except OSError:
			pass
		try:
			self.wrapper(shutil.rmtree, rbconfig.gen_webtree(usr.uid))
		except OSError:
			pass

		# Remove from announce mailing lists.
		#
		self.list_delete('announce-redbrick', '%s@redbrick.dcu.ie' % usr.uid);
		self.list_delete('redbrick-newsletter', '%s@redbrick.dcu.ie' % usr.uid);

		for file in rbconfig.gen_extra_user_files(usr.uid):
			try:
				self.wrapper(os.unlink, file)
			except OSError:
				pass

	def rename(self, oldusr, newusr):
		"""Rename an account.
		
		Requires: oldusr.uid, oldusr.homeDirectory, newusr.uid,
		newusr.homeDirectory.
		
		"""

		# XXX Should check this before we rename user in ldap, have a
		# rbaccount.check_userfree? There should never be a file or
		# directory in /home or /webtree that doesn't belong to an
		# existing user.

		if os.path.exists(newusr.homeDirectory):
			if not os.path.isdir(newusr.homeDirectory):
				try:
					self.wrapper(os.unlink, newusr.homeDirectory)
				except OSError:
					raise RBFatalError("New home directory '%s' already exists, could not unlink existing file." % newusr.homeDirectory)
			else:
				raise RBFatalError("New home directory '%s' already exists." % newusr.homeDirectory)

		oldwebtree = rbconfig.gen_webtree(oldusr.uid)
		newwebtree = rbconfig.gen_webtree(newusr.uid)
		
		try:
			self.wrapper(os.rename, oldusr.homeDirectory, newusr.homeDirectory)
		except OSError, e:
			raise RBFatalError("Could not rename home directory [%s]" % e)

		try:
			self.wrapper(os.rename, oldwebtree, newwebtree)
		except OSError, e:
			raise RBFatalError("Could not rename webtree directory [%s]" % e)

		# Remove and then attempt to rename webtree symlink.
		#
		webtreelink = '%s/public_html' % newusr.homeDirectory
		try:
			self.wrapper(os.unlink, webtreelink)
		except OSError:
			pass
		if not os.path.exists(webtreelink):
			self.wrapper(os.symlink, newwebtree, webtreelink)

		# Rename any extra files that may belong to a user.
		#
		oldfiles = rbconfig.gen_extra_user_files(oldusr.uid)
		newfiles = rbconfig.gen_extra_user_files(newusr.uid)

		for i in range(len(oldfiles)):
			oldf = oldfiles[i]
			newf = newfiles[i]

			try:
				if os.path.isfile(oldf):
					self.wrapper(os.rename, oldf, newf)
			except OSError,e :
				raise RBFatalError("Could not rename '%s' to '%s' [%s]" % (oldf, newf, e))

		# XXX
		# Rename their subscription to announce lists in case an email
		# alias isn't put in for them or is later removed.
		#
		self.list_delete('announce-redbrick', "%s@redbrick.dcu.ie" % oldusr.uid);
		self.list_delete('redbrick-newsletter', "%s@redbrick.dcu.ie" % oldusr.uid);
		self.list_add('announce-redbrick', "%s@redbrick.dcu.ie" % newusr.uid);
		self.list_add('redbrick-newsletter', "%s@redbrick.dcu.ie" % newusr.uid);
		
	def convert(self, oldusr, newusr):
		"""Convert account to a new usertype (Unix group)."""

		if oldusr.usertype == newusr.usertype:
			return
		
		# Do supplementary group shit in rbuserdb.
		#
		#if rbconfig.convert_primary_groups.has_key(usertype):
		#	group = rbconfig.convert_primary_groups[usertype]
		#else:
		#	group = usertype
		
		#if rbconfig.convert_extra_groups.has_key(usertype):
		#	groups = '-G ' + rbconfig.convert_extra_groups[usertype]
		#else:
		#	groups = ''
		
		if newusr.usertype == 'committe' and oldusr.usertype not in ('member', 'staff', 'committe'):
			raise RBFatalError("Non-members cannot be converted to committee group")
		
		if os.path.exists(newusr.homeDirectory):
			if not os.path.isdir(newusr.homeDirectory):
				try:
					self.wrapper(os.unlink, newusr.homeDirectory)
				except OSError:
					raise RBFatalError("New home directory '%s' already exists, could not unlink existing file." % newusr.homeDirectory)
			else:
				raise RBFatalError("New home directory '%s' already exists." % newusr.homeDirectory)

		# Rename home directory.
		#
		try:
			self.wrapper(os.rename, oldusr.homeDirectory, newusr.homeDirectory)
		except:
			raise RBFatalError("Could not rename home directory")
		
		# Change the home directory and webtree ownership to the new
		# group. -h on Solaris chgrp makes sure to change the symbolic
		# links themselves not the files they point to - very
		# important!!
		#
		self.cmd("%s -Rh %s %s %s" % (rbconfig.command_chgrp, newusr.gidNumber, self.shquote(newusr.homeDirectory), self.shquote(rbconfig.gen_webtree(oldusr.uid))))
		
		# Change crontab group ownership to the new group.
		#
		if os.path.isfile("/var/spool/cron/crontabs/%s" % oldusr.uid):
			self.wrapper(os.chown, "/var/spool/cron/crontabs/%s " % oldusr.uid, newusr.uidNumber, newusr.gidNumber)
		
		# Add/remove from committee mailing list as appropriate.
		#
		if newusr.usertype == 'committe':
			self.list_add('committee', "%s@redbrick.dcu.ie" % oldusr.uid)
		elif oldusr.usertype == 'committe':
			self.list_delete('committee', "%s@redbrick.dcu.ie" % oldusr.uid)
		
		# Add to admin list. Most admins stay in the root group for a while
		# after leaving committee, so removal can be done manually later.
		# 
		if newusr.usertype == 'admin':
			self.list_add('rb-admins', "%s@redbrick.dcu.ie" % oldusr.uid)
		
	def disuser(self, username, disuser_period = None):
		"""Disable an account with optional automatic re-enabling after
		given period."""

		#TODO
	
	def reuser(self, username):
		"""Re-enable an account."""

		#TODO
		
	def quota_set(self, username, fs, bqs, bqh, iqs, iqh):
		"""Set given quota for given username on given filesystem.
		Format for quota values is the same as that used for quotas
		function in rbconfig module."""

		self.cmd("%s -b %d -B %d -i %d -I %d %s %s" % (rbconfig.command_setquota, bqs, bqh, iqs, iqh, fs, self.shquote(str(username))))

	def quota_delete(self, username, fs):
		"""Delete quota for given username on given filesystem."""

		self.cmd('%s -d %s %s' % (rbconfig.command_setquota, fs, self.shquote(str(username))))

	#---------------------------------------------------------------------#
	# SINGLE ACCOUNT INFORMATION METHODS                                  #
	#---------------------------------------------------------------------#
	
	def show(self, usr):
		"""Show account details on standard output."""

		print "%13s:" % 'homedir mode',
		if os.path.isdir(usr.homeDirectory):
			print '%04o' % (os.stat(usr.homeDirectory)[0] & 07777)
		else:
			print 'Home directory does not exist'
		print "%13s: %s" % ('logged in', os.path.exists('%s/%s' % (rbconfig.dir_signaway_state, usr.uid)) and 'true' or 'false')

	#---------------------------------------------------------------------#
	# MISCELLANEOUS METHODS                                               #
	#---------------------------------------------------------------------#
	
	def stats(self):
		"""Print account statistics on standard output."""

		print "%20s %5d (signed agreement)" % ('Logged in', len(os.listdir(rbconfig.dir_signaway_state)))
		
	#---------------------------------------------------------------------#
	# USER CHECKING AND INFORMATION RETRIEVAL METHODS                     #
	#---------------------------------------------------------------------#
	
	def check_accountfree(self, usr):
		"""Raise RBFatalError if given account name is not free i.e.
		has a home directory."""

		if os.path.exists(usr.homeDirectory):
			raise RBFatalError("Account '%s' already exists (has a home directory)" % usr.uid)

	def check_account_byname(self, usr):
		"""Raise RBFatalError if given account does not exist."""

		if not os.path.exists(usr.homeDirectory):
			raise RBFatalError("Account '%s' does not exist (no home directory)" % usr.uid)
		
	#---------------------------------------------------------------------#
	# OTHER METHODS                                                       #
	#---------------------------------------------------------------------#
	
	def list_add(self, list, email):
		"""Add email address to mailing list."""

		fd = self.my_popen('%s/bin/add_members -r - %s' % (rbconfig.dir_mailman, self.shquote(list)))
		fd.write('%s\n' % email)
		self.my_close(fd)
	
	def list_delete(self, list, email):
		"""Delete email address from a mailing list."""

		self.runcmd('%s/bin/remove_members %s %s' % (rbconfig.dir_mailman, self.shquote(list), self.shquote(email)))
	
        #--------------------------------------------------------------------#
	# INTERNAL METHODS                                                   #
	#--------------------------------------------------------------------#
	
	def shquote(self, string):
		"""Return a quoted string suitable to use with shell safely."""

		return "'" + string.replace("'", r"'\''") + "'"

	def runcmd(self, cmd):
		"""runcmd(command) -> output, status
		
		Run given command and return command output (stdout & stderr combined)
		and exit status.
	
		"""
	
		if self.opt.test:
			print >> sys.stderr, "TEST: runcmd:", cmd
			return None, None
		else:
			fd = os.popen(cmd + ' 2>&1')
			return fd.read(), fd.close()

	def cmd(self, cmd):
		"""Run given command and raise a RBError exception returning
		the command output if command exit status is non zero."""

		output, status = self.runcmd(cmd)
		if status:
			raise RBFatalError("Command '%s' failed.\n%s" % (cmd, output))
	
	def wrapper(self, function, *keywords, **arguments):
		"""Wrapper method for executing other functions.
		
		If test mode is set, print function name and arguments.
		Otherwise call function with arguments.
		
		"""

		if self.opt.test:
			sys.stderr.write("TEST: %s(" % function.__name__)
			for i in keywords:
				sys.stderr.write("%s, " % (i,))
			for k, v in arguments.items():
				sys.stderr.write("%s = %s, " % (k, v))
			sys.stderr.write(")\n")
		else:
			return function(*keywords, **arguments)

	def my_open(self, file):
		"""Return file descriptor to given file for writing."""
		
		if self.opt.test:
			print >> sys.stderr, 'TEST: open:', file
			return sys.stderr
		else:
			return open(file, 'w')

	def my_popen(self, cmd):
		"""Return file descriptor to given command pipe for writing."""
		
		if self.opt.test:
			print >> sys.stderr, 'TEST: popen:', cmd
			return sys.stderr
		else:
			return os.popen(cmd, 'w')
	
	def my_close(self, fd):
		"""Close given pipe returned by _[p]open."""
		
		if not self.opt.test:
			fd.close()
	
	#--------------------------------------------------------------------#
	# ERROR HANDLING                                                     #
	#--------------------------------------------------------------------#

	def rberror(self, e):
		"""Handle errors."""
		
		if self.opt.override and isinstance(e, RBWarningError):
			return

		# If we reach here it's either a FATAL error or there was no
		# override for a WARNING error, so raise it again to let the
		# caller handle it.
		#
		raise e
