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
import sys

# RedBrick modules

import rbconfig
from rberror import *
from rbopt import *
from rbuser import *

#-----------------------------------------------------------------------------#
# DATA                                                                        #
#-----------------------------------------------------------------------------#

__version__ = '$Revision: 1.1 $'
__author__  = 'Cillian Sharkey'

valid_shells = None
backup_shells = None

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
	
	def add(self, username, usertype, name, passwd = None, email = None):
		"""Add a local Unix account."""
		
		if usertype == 'reserved':
			return

		sh_username = self.shquote(username)
		sh_usertype = self.shquote(usertype)
		sh_name = self.shquote(name)
		home = self.homedir(username, usertype)

		# Add the account.
		#
		self.cmd("%s -c %s -g %s -d %s -m -k %s -s %s %s" % (rbconfig.useradd_command, sh_name, sh_usertype, self.shquote(home), rbconfig.skel_dir, rbconfig.default_shell, sh_username))

		# Set home directory mode.
		#
		self.my_chmod(home, 0711)

		# Set quotas for each filesystem.
		#
		for fs, (bqs, bqh, iqs, iqh) in rbconfig.quotas(usertype).items():
			self.quota_set(username, fs, bqs, bqh, iqs, iqh)
		
		# Set password.
		#
		self.setpasswd(username, passwd)

		# Add a .forward file in their home directory to point to their
		# alternate email address if given.
		#
		if email:
			forward_file = '%s/.forward' % home
			fd = self.my_open(forward_file)
			fd.write('%s\n' % email)
			self.my_close(fd)
			# Now make sure they own the file.
			try:
				self.my_chown(forward_file, pwd.getpwnam(username)[2], grp.getgrnam(usertype)[2])
			except KeyError:
				# We only reach here when in test mode as the
				# new account wasn't created so the get*nam
				# calls fail above.
				#
				pass

		self.list_add('announce-redbrick', '%s@redbrick.dcu.ie' % username)
		self.list_add('redbrick-newsletter', '%s@redbrick.dcu.ie' % username)
	
	def delete(self, username):
		"""Delete a local Unix account."""

		sh_username = self.shquote(username)

		# Zero out quotas.
		#
		for fs in rbconfig.quotas().keys():
			self.quota_delete(username, fs)
		
		# Remove account and home directory.
		#
		self.cmd('%s -r %s' % (rbconfig.userdel_command, sh_username))

		# Remove from announce mailing lists.
		#
		self.list_delete('announce-redbrick', '%s@redbrick.dcu.ie' % username);
		self.list_delete('redbrick-newsletter', '%s@redbrick.dcu.ie' % username);

		remove_files = (
			'%s/%s' % (rbconfig.signaway_state_dir, username),
			'/var/mail/%s' % username,
			'/var/spool/cron/crontabs/%s' % username
		)

		for file in remove_files:
			try:
				self.my_unlink(file)
			except OSError:
				pass

	def rename(self, username, newusername):
		"""Rename an account."""

		pw = self.get_account_byname(username)
		usertype = self.get_group_byid(pw[3])[0]
		newhome = self.homedir(newusername, usertype)
		oldhome = pw[5]

		if os.access(newhome, os.F_OK):
			raise RBFatalError("New home directory '%s' already exists" % newhome)
		
		self.cmd("%s -d %s -l %s %s" % (rbconfig.usermod_command, self.shquote(newhome), self.shquote(newusername), self.shquote(username)))

		try:
			self.my_rename(oldhome, newhome)
		except:
			raise RBFatalError("Could not rename home directory")

		renames = (
			("%s/%s" % (rbconfig.signaway_state_dir, username), "%s/%s" % (rbconfig.signaway_state_dir, newusername)),
			("/var/mail/%s" % username, "/var/mail/%s" % newusername),
			("/var/spool/cron/crontabs/%s" % username, "/var/spool/cron/crontabs/%s" % newusername)
		)
			
		for old, new in renames:
			try:
				if os.access(old, os.F_OK):
					self.my_rename(old, new)
			except OSError:
				raise RBFatalError("Rename of '%s' to '%s'" % (old, new))

		# Rename their subscription to announce lists in case an email
		# alias isn't put in for them or is later removed.
		#
		self.list_delete('announce-redbrick', "%s@redbrick.dcu.ie" % username);
		self.list_delete('redbrick-newsletter', "%s@redbrick.dcu.ie" % username);
		self.list_add('announce-redbrick', "%s@redbrick.dcu.ie" % newusername);
		self.list_add('redbrick-newsletter', "%s@redbrick.dcu.ie" % newusername);
		
	def convert(self, username, usertype):
		"""Convert account to a new usertype (Unix group)."""

		if usertype == 'reserved':
			return

		pw = self.get_account_byname(username)
		
		if rbconfig.convert_primary_groups.has_key(usertype):
			group = rbconfig.convert_primary_groups[usertype]
		else:
			group = usertype
		
		if rbconfig.convert_extra_groups.has_key(usertype):
			groups = '-G ' + rbconfig.convert_extra_groups[usertype]
		else:
			groups = ''
		
		gr = self.get_group_byname(group)
		
		oldhome = pw[5]
		oldgroup = self.get_group_byid(pw[3])[0]
		newhome = self.homedir(username, group)
		
		if group == 'committe' and oldgroup not in ('member', 'staff', 'committe'):
			raise RBFatalError("Non-members cannot be converted to committee group")
		
		if os.path.islink(newhome):
			try:
				self.my_unlink(newhome)
			except OSError:
				raise RBFatalError("New home directory '%s' is a symlink and could not be removed" % newhome)
		
		if os.path.exists(newhome):
			raise RBFatalError("New home directory '%s' already exists" % newhome)
		
		# Change user's primary group, supplementary groups (if set)
		# and home directory (if it's changed location). usermod can
		# move the home directory itself with the "-m" switch, but it
		# copies the files instead of doing a simple rename which won't
		# work if the user is near quota and is incredibly inefficient
		# anyway. All home directories are on the one filesystem, so
		# there should be no worries about renaming home directories
		# across filesystems.
		#
		if newhome != oldhome:
			home = '-d %s' % self.shquote(newhome)
		else:
			home = ''

		self.cmd("%s -g %s %s %s %s " % (rbconfig.usermod_command, self.shquote(group), groups, home, self.shquote(username)))
		
		# Move the home directory to the new location.
		#
		try:
			self.my_rename(oldhome, newhome)
		except:
			raise RBFatalError("Could not rename home directory")
		
		# Change the home directory ownership to the new group. -h
		# makes sure to change the symbolic links themselves not the
		# files they point to - very important!!
		#
		self.cmd("/usr/bin/chgrp -Rh %s %s" % (self.shquote(group), self.shquote(newhome)))
		
		# Change crontab group ownership to the new group.
		#
		if os.path.isfile("/var/spool/cron/crontabs/%s" % username):
			self.my_chown("/var/spool/cron/crontabs/%s " % username, pw[2], gr[1])
		
		# Add/remove from committee mailing list as appropriate.
		#
		if group == 'committe':
			self.list_add('committee', "%s@redbrick.dcu.ie" % username)
		elif oldgroup == 'committe':
			self.list_delete('committee', "%s@redbrick.dcu.ie" % username)
		
		# Add to admin list. Most admins stay in the root group for a while
		# after leaving committee, so removal can be done manually later.
		# 
		if usertype == 'admin':
			self.list_add('rb-admins', "%s@redbrick.dcu.ie" % username)
		
	def disuser(self, username, disuser_period = None):
		"""Disable an account with optional automatic re-enabling after
		given period."""

		#TODO
	
	def reuser(self, username):
		"""Re-enable an account."""

		#TODO
		
	def set_shell(self, username, shell):
		"""Set shell for account."""

		self.cmd("%s %s %s" % (rbconfig.setshell_command, self.shquote(shell), self.shquote(username)))

	def reset_shell(self, username):
		"""Reset shell for account from backup of password file."""

		if self.valid_shell(self.get_shell(username)):
			return

		self.set_shell(username, self.get_backup_shell(username) or rbconfig.default_shell)	

	def quota_set(self, username, fs, bqs, bqh, iqs, iqh):
		"""Set given quota for given username on given filesystem.
		Format for quota values is the same as that used for quotas
		function in rbconfig module."""

		self.cmd("%s -b %d -B %d -i %d -I %d %s %s" % (rbconfig.setquota_command, bqs, bqh, iqs, iqh, fs, self.shquote(username)))

	def quota_delete(self, username, fs):
		"""Delete quota for given username on given filesystem."""

		self.cmd('%s -d %s %s' % (rbconfig.setquota_command, fs, self.shquote(username)))

	#---------------------------------------------------------------------#
	# SINGLE ACCOUNT INFORMATION METHODS                                  #
	#---------------------------------------------------------------------#
	
	def show(self, username):
		"""Show account details on standard output."""

		pw = self.get_account_byname(username)
		group = self.get_groupname_byid(pw[3])

		print "%12s: %d [%s]" % ('user id', pw[2], username)
		print "%12s: %d [%s]" % ('group id', pw[2], group)
		print "%12s: %s" % ('gecos', pw[4])
		print "%12s: %s" % ('homedir', pw[5])
		print "%12s: %s" % ('shell', pw[6])

	#---------------------------------------------------------------------#
	# MISCELLANEOUS METHODS                                               #
	#---------------------------------------------------------------------#
	
	def stats(self):
		"""Print account statistics on standard output."""

		print "%20s %5d (signed agreement)" % ('Logged in', len(os.listdir(rbconfig.signaway_state_dir)))
		
	#---------------------------------------------------------------------#
	# USER CHECKING AND INFORMATION RETRIEVAL METHODS                     #
	#---------------------------------------------------------------------#
	
	def check_accountfree(self, username):
		"""Raise RBFatalError if given account name is not free."""

		try:
			pw = self.check_account_byname(username)
		except RBError:
			pass
		else:
			raise RBFatalError("Account '%s' is already taken by %s account (%s)" % (pw[0], self.get_groupname_byid(pw[3]), pw[5]))

	def check_account_byname(self, username):
		"""Raise RBFatalError if given account does not exist."""

		self.get_account_byname(username)

	def check_group_byname(self, group):
		"""Raise RBFatalError if group with given name does not
		exist."""
		
		self.get_group_byname(group)

	def check_group_byid(self, gid):
		"""Raise RBFatalError if group with given ID does not exist."""
		
		self.get_group_byname(gid)

	def get_account_byname(self, username):
		"""Get Unix account information."""

		try:
			return pwd.getpwnam(username)
		except KeyError:
			raise RBFatalError("Account '%s' does not exist" % username)
	
	def get_group_byname(self, group):
		"""Get Unix group information."""

		try:
			return grp.getgrnam(group)
		except KeyError:
			raise RBFatalError("Group/Usertype '%s' does not exist" % group)

	def get_group_byid(self, gid):
		"""Get Unix group information."""

		try:
			return grp.getgrgid(gid)
		except KeyError:
			raise RBFatalError("Group ID '%s' does not exist" % gid)

	def get_groupname_byid(self, gid):
		"""Get Unix groupname for given group ID. If no group exists,
		return the group id as a string with a '#' prefix."""

		try:
			gr = grp.getgrgid(gid)
		except KeyError:
			return '#%s' % gid
		else:
			return gr[0]
	
	def get_shell(self, username):
		"""Return shell for given account or None if account does not exist."""

		try:
			return pwd.getpwnam(username)[6]
		except KeyError:
			return None
	
	def get_backup_shell(self, username):
		"""Return shell for given account from backup of password file."""

		if self.backup_shells == None:
			self.backup_shells = {}
			fd = open(rbconfig.backup_passwd_file, 'r')
			for line in fd.readlines():
				pw = line.split(':')
				self.backup_shells[pw[0]] = pw[6].rstrip()
			fd.close()

		if self.backup_shells.has_key(username):
			return self.backup_shells[username]
		else:
			return None
		
	def valid_shell(self, shell):
		"""Check if given shell is valid by checking against /etc/shells."""

		if not shell:
			return 0
		
		if self.valid_shells == None:
			self.valid_shells = {}
			re_shell = re.compile(r'^([^\s#]+)')
			fd = open(rbconfig.shells_file, 'r')
			for line in fd.readlines():
				res = re_shell.search(line)
				if res:
					self.valid_shells[res.group(1)] = 1
			fd.close()
			
		return self.valid_shells.has_key(shell)
		
	#---------------------------------------------------------------------#
	# OTHER METHODS                                                       #
	#---------------------------------------------------------------------#
	
	def list_add(self, list, email):
		"""Add email address to mailing list."""

		fd = self.my_popen('%s/bin/add_members -r - %s' % (rbconfig.mailman_dir, self.shquote(list)))
		fd.write('%s\n' % email)
		self.my_close(fd)
	
	def list_delete(self, list, email):
		"""Delete email address from a mailing list."""

		self.runcmd('%s/bin/remove_members %s %s' % (rbconfig.mailman_dir, self.shquote(list), self.shquote(email)))
	
	def setpasswd(self, username, passwd):
		"""Set password for local Unix account."""
		
		if passwd:
			fd = self.my_popen('%s %s' % (rbconfig.passwd_command, self.shquote(username)))
			fd.write('%s\n%s\n' % (passwd, passwd))
			self.my_close(fd)
		else: 
			# No password given. For new accounts this results in
			# the account remaining disabled.
			pass
		
	def homedir(self, username, usertype):
		"""Construct a user's home directory path given username and usertype."""
		
		if usertype in ('member', 'associat'):
			hash = username[0] + '/'
		else:
			hash = ''

		return '/home/%s/%s%s' % (usertype, hash, username)

	def mkpasswd(self):
		"""Generate a random plaintext password."""

		passchars = 'a b c d e f g h i j k m n p q r s t u v w x y z A B C D E F G H J K L M N P Q R S T U V W X Y Z 2 3 4 5 6 7 8 9'.split()
		password = ''
		for c in range(8):
			password += passchars[random.randrange(len(passchars))]

		return password

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
	
	def my_rename(self, old, new):
		"""Wrapper for os.rename()."""

		if self.opt.test:
			print >> sys.stderr, 'TEST: rename:', old, new
		else:
			os.rename(old, new)
			
	def my_unlink(self, file):
		"""Wrapper for os.unlink()."""

		if self.opt.test:
			print >> sys.stderr, 'TEST: unlink:', file
		else:
			os.unlink(file)
			
	def my_chown(self, file, uid, gid):
		"""Wrapper for os.chown()."""

		if self.opt.test:
			print >> sys.stderr, 'TEST: chown:', file, uid, gid
		else:
			os.chown(file, uid, gid)
			
	def my_chmod(self, file, mode):
		"""Wrapper for os.chmod()."""

		if self.opt.test:
			print >> sys.stderr, 'TEST: chmod: %s %o' % (file, mode)
		else:
			os.chmod(file, mode)
			
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
