#-----------------------------------------------------------------------------#
# MODULE DESCRIPTION                                                          #
#-----------------------------------------------------------------------------#

"""RedBrick User Module; contains RBUser class."""

#-----------------------------------------------------------------------------#
# DATA                                                                        #
#-----------------------------------------------------------------------------#

__version__ = '$Revision: 1.4 $'
__author__ = 'Cillian Sharkey'

#-----------------------------------------------------------------------------#
# CLASSES                                                                     #
#-----------------------------------------------------------------------------#

class RBUser:
    """Class to represent a user."""

    # List of valid LDAP attributes for a user. The order of these is used
    # when displaying a user's information.
    #
    attr_list = (
        # Attributes associated with user.

        'uid',                  # Username
        'usertype',             # XXX NOT IN LDAP: contains primary
                                # usertype from objectClass list.
                                # Placed here so it's at start of
                                # output for user's information.
        'objectClass',          # List of classes.
        'newbie',               # New this year (boolean)
        'cn',                   # Full name
        'altmail',              # Alternate email
        'id',                   # DCU ID number (integer)
        'course',               # DCU course code
        'year',                 # DCU course year number/code
        'yearsPaid',            # Number of years paid (integer)
        'updatedby',            # Username
        'updated',              # Timestamp
        'createdby',            # Username
        'created',              # Timestamp
        'birthday',             # Date

        # Attributes associated with Unix account.

        'uidNumber',
        'gidNumber',
        'gecos',
        'loginShell',
        'homeDirectory',
        'userPassword',         # Crypted password.
        'host',                 # List of hosts.
        'shadowLastChange'      # Last time password was changed.
    )

    # List of additional user attributes that are NOT in LDAP.
    #
    attr_misc_list = (
        'passwd',               # Plaintext password
        'oldusertype',          # Used when converting usertype?
        'bday',                 # Birthday day
        'bmonth',               # Birthday month
        'byear',                # Birthday year
        'disuser_period',       # at(1) timespec
        #XXX remove usr.override
        #'override'             # Boolean
    )

    # Union of above lists.
    #
    attr_list_all = attr_list + attr_misc_list

    attr_list_info = (
        # Attributes associated with user to be used for the useradm info command

        'uid',                  # Username
        'usertype',             # XXX NOT IN LDAP: contains primary
                                # usertype from objectClass list.
                                # Placed here so it's at start of
                                # output for user's information.
        'newbie',               # New this year (boolean)
        'cn',                   # Full name
        'altmail',              # Alternate email
        'id',                   # DCU ID number (integer)
        'course',               # DCU course code
        'year',                 # DCU course year number/code
        'yearsPaid',            # Number of years paid (integer)
        'updatedby',            # Username
        'updated',              # Timestamp
        'createdby',            # Username
        'created',              # Timestamp
        'birthday',             # Date

        # Attributes associated with Unix account.

        'gecos',
        'loginShell',
        'homeDirectory',
    )

    # List of attributes that have multiple values (i.e. are lists).
    #
    attr_list_value = (
        'objectClass',
        'host'
    )

    def __init__(self, usr=None, **attrs):
        """Create new RBUser object.
        If the optional usr argument is an RBUser object, its
        attributes are copied to the new object. Only valid RBUser
        attributes (listed in RBUser.attr_list_all) are copied. If any
        keywords are given, the new object's attributes are set to
        their values accordingly. Keywords override data copied from a
        given RBUser object. Any remaining unset attributes are
        explicitly set to None or an empty list [] as appropriate, so
        that they exist within the object."""

        if isinstance(usr, RBUser):
            for i in self.attr_list_all:
                setattr(self, i, getattr(usr, i))

        for i in self.attr_list_all:
            if i in attrs:
                setattr(self, i, attrs[i])
            elif not hasattr(self, i):
                # XXX set list attributes to empty list [] or None ??
                #if i in self.attr_list_value:
                #       setattr(self, i, [])
                #else:
                setattr(self, i, None)

    def merge(self, usr, override=0):
        """Merge attributes from given RBUser object.

        For each valid attribute in the given usr object that has
        a value (is not None) set this object (self) to that value
        if it is currently None or if override is true.
        """

        for i in self.attr_list_all:
            if (hasattr(usr, i) and (getattr(self, i) is None or override) and
                    getattr(usr, i) != None):
                setattr(self, i, getattr(usr, i))
