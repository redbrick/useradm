#-----------------------------------------------------------------------------#
# MODULE DESCRIPTION                                                          #
#-----------------------------------------------------------------------------#

"""RedBrick Error Module; contains RedBrick exception classes."""

#-----------------------------------------------------------------------------#
# DATA                                                                        #
#-----------------------------------------------------------------------------#

__version__ = '$Revision'
__author__  = 'Cillian Sharkey'

#-----------------------------------------------------------------------------#
# CLASSES                                                                     #
#-----------------------------------------------------------------------------#

class RBError(Exception):
	"""Base class for RedBrick exceptions"""

	def __init__(self, mesg):
		"""Create new RBError object with given error message."""

		self.mesg = mesg
	
	def __str__(self):
		"""Return exception error message."""

		return "ERROR: %s" % self.mesg

class RBFatalError(RBError):
	"""Class for fatal RedBrick exceptions"""

	def __str__(self):
		"""Return exception error message."""

		return "FATAL: %s" % self.mesg

class RBWarningError(RBError):
	"""Class for warning RedBrick exceptions. These can be overrided."""

	def __str__(self):
		"""Return exception error message."""

		return "WARNING: %s" % self.mesg
