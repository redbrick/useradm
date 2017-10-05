# --------------------------------------------------------------------------- #
# MODULE DESCRIPTION                                                          #
# --------------------------------------------------------------------------- #
"""RedBrick Options Module; contains RBOpt class."""

# --------------------------------------------------------------------------- #
# DATA                                                                        #
# --------------------------------------------------------------------------- #

__version__ = '$Revision: 1.5 $'
__author__ = 'Cillian Sharkey'

# --------------------------------------------------------------------------- #
# CLASSES                                                                     #
# --------------------------------------------------------------------------- #


class RBOpt:
    """Class for storing options to be shared by modules"""

    def __init__(self):
        """Create new RBOpt object."""

        # Used by all modules.
        self.override = None
        # Used by useradm, RBUserDB & RBAccount.
        self.test = None
        # Used by useradm & rrs.
        self.mode = None
        self.setpasswd = None
        # Used by useradm.
        self.args = []
        self.help = None
        self.uid = None
        self.dbonly = None
        self.aconly = None
        self.updatedby = None
        self.newbie = None
        self.mailuser = None
        self.usertype = None
        self.cn = None
        self.altmail = None
        self.id = None
        self.course = None
        self.year = None
        self.yearsPaid = None
        self.birthday = None
        self.loginShell = None
        self.quiet = None
        self.rrslog = None
        self.presync = None
        # Used by rrs.
        self.action = None
