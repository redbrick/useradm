#-----------------------------------------------------------------------------#
# MODULE DESCRIPTION                                                          #
#-----------------------------------------------------------------------------#

"""RedBrick Configuration Module; contains local configuration information."""

#---------------------------------------------------------------------#
# DATA                                                                #
#---------------------------------------------------------------------#

__version__ = '$Revision: 1.1 $'
__author__  = 'Cillian Sharkey'

# Directory pathnames.

signaway_state_dir = '/local/share/agreement/statedir'
daft_dir = '/local/share/daft'
skel_dir = '/etc/skel'
mailman_dir = '/local/mailman'

# Filenames.

shells_file = '/etc/shells'
backup_passwd_file = '/var/backups/passwd.pre-expired'
default_shell = '/usr/local/bin/zsh'
expired_shell = '/local/bin/shells/expired'

# Commands.

setquota_command = '/usr/local/sbin/setquota'
useradd_command = '/usr/sbin/useradd'
usermod_command = '/usr/sbin/usermod'
userdel_command = '/usr/sbin/userdel'

# Set account password with npasswd reading from stdin.
#
#passwd_command = '/usr/local/npasswd/npasswd -XI'

# Set account password with hacked version of NetBSD passwd(1).
#
passwd_command = '/local/admin/hacked-passwd'

# Set shell using modified version of Solaris usermod that does not check if
# user is logged in before performing account operation(s).
#
#setshell_command = '/local/admin/bin/usermod -s'

setshell_command = '/usr/sbin/usermod -s'

# Supplementary groups when converting an account to given usertype.
#
# Format: 'usertype': 'a string of comma seperated groups with no spaces'
#
convert_extra_groups = {
	'admin':	'root,log',
	'webmaster':	'root,log,webgroup',
	'helpdesk':	'helpdesk'
}

# Actual primary group to use when converting an account to given usertype
# (typically a 'pseudo-usertype').
#
# Format: 'usertype': 'actual unix group name'
#
convert_primary_groups = {
	'admin':	'committe',
	'webmaster':	'committe',
	'helpdesk':	'committe'
}

#---------------------------------------------------------------------#
# MODULE FUNCTIONS                                                    #
#---------------------------------------------------------------------#

def quotas(usertype = None):
	"""Returns a dictionary of quota limits for filesystems (possibly
	depending on the given usertype, if any).

	The format of the quota dictionary is as follows:

	'filesystem': (block quota soft, block quota hard,
	               inode quota soft, inode quota hard),
	 ...

	Block quota is in kilobytes, inode quota is number of inodes.
	
	"""

	quotas = {}
	default_home_quota = (75000, 80000, 10000, 10500)

	# Clubs & Socs get a 100MB quota.
	#
	if usertype in ('club', 'society'):
		quotas['/home'] = (100000, 105000) + default_home_quota[2:]
	else:
		quotas['/home'] = default_home_quota

	return quotas
