#-----------------------------------------------------------------------------#
# MODULE DESCRIPTION                                                          #
#-----------------------------------------------------------------------------#

"""RedBrick User Module; contains RBUser class."""

#-----------------------------------------------------------------------------#
# DATA                                                                        #
#-----------------------------------------------------------------------------#

__version__ = '$Revision'
__author__  = 'Cillian Sharkey'

#-----------------------------------------------------------------------------#
# CLASSES                                                                     #
#-----------------------------------------------------------------------------#

class RBUser:
	"""Class to represent a user."""
	
	attr_list = (
		# Following attributes are in the user table.
		'username', 'usertype', 'name',	'newbie', 'email', 'id',
		'course', 'year', 'years_paid',	'updated_by', 'updated_at',
		'created_by', 'created_at', 'birthday',
		# Following attributes are NOT in the user table.
		'newusername', 'oldusertype', 'bday', 'bmonth', 'byear', 'disuser_period',
		'passwd', 'override'
	)

	def __init__(self, usr = None, **attrs):
		"""Create new RBUser object.

		If the optional usr argument is an RBUser object, its
		attributes are copied to the new object. If any keywords are
		given, the new object's attributes are set to their values
		accordingly. Keywords override data copied from a given RBUser
		object.

		"""

		if isinstance(usr, RBUser):
			for i in self.attr_list:
				setattr(self, i, getattr(usr, i))
			
		for i in self.attr_list:
			if attrs.has_key(i):
				setattr(self, i, attrs[i])
			elif not hasattr(self, i):
				setattr(self, i, None)
	
	def merge(self, usr):
		"""Merge all attributes from given RBUser object if they have
		no value (None) in this object."""

		for i in self.attr_list:
			if hasattr(usr, i) and getattr(self, i) == None and getattr(usr, i) != None:
				setattr(self, i, getattr(usr, i))
