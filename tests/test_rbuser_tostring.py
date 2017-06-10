"""RedBrick Test Module; Tests the to_string method of the rbuser module."""

import unittest
from useradm import rbuser


class RBUserTestCase(unittest.TestCase):
    """Test Case class for to_string method"""

    def setUp(self):
        """Call before every test case."""
        self.member_one_attr = {'cn': 'Member One',
                                'id': 15358462,
                                'uid': 'memberOne',
                                'bday': 12,
                                'host': 'carbon',
                                'year': 3,
                                'gecos': 'new member',
                                'byear': 2017,
                                'bmonth': 2,
                                'passwd': 'e1NTSEF9WlBURGtJdmZJSld0WUlrak9zdGxscXYySTRRVEhBYj=',
                                'newbie': True,
                                'course': 'CASE',
                                'created': '2009-10-06 11:20:13',
                                'altmail': 'memberOne@example.dcu.ie',
                                'updated': '2015-09-28 01:42:21',
                                'birthday': '12 02 2017',
                                'usertype': 'member',
                                'updatedby': 'admin',
                                'uidNumber': 102007,
                                'createdby': 'admin',
                                'gidNumber': 1017,
                                'yearsPaid': 1,
                                'loginShell': '/usr/local/shells/zsh',
                                'objectClass': ['redbrick', 'posixAccount', 'top', 'shadowAccount'],
                                'oldusertype': 'newb',
                                'userPassword': 'e1NTSEF9WlBURGtJdmZJSld0WUlrak9zdGxscXYySTRRVEhj=',
                                'homeDirectory': '/home/redbrick/memberOne',
                                'disuser_period': 0,
                                'shadowLastChange': 17073, }
        self.member_one_output = \
            'cn                :  Member One\n' + \
            'id                :  15358462\n' + \
            'uid               :  memberOne\n' + \
            'bday              :  12\n' + \
            'host              :  carbon\n' + \
            'year              :  3\n' + \
            'byear             :  2017\n' + \
            'gecos             :  new member\n' + \
            'bmonth            :  2\n' + \
            'course            :  CASE\n' + \
            'newbie            :  True\n' + \
            'passwd            :  e1NTSEF9WlBURGtJdmZJSld0WUlrak9zdGxscXYySTRRVEhBYj=\n' + \
            'altmail           :  memberOne@example.dcu.ie\n' + \
            'created           :  2009-10-06 11:20:13\n' + \
            'updated           :  2015-09-28 01:42:21\n' + \
            'birthday          :  12 02 2017\n' + \
            'usertype          :  member\n' + \
            'createdby         :  admin\n' + \
            'gidNumber         :  1017\n' + \
            'uidNumber         :  102007\n' + \
            'updatedby         :  admin\n' + \
            'yearsPaid         :  1\n' + \
            'loginShell        :  /usr/local/shells/zsh\n' + \
            'objectClass       :  [\'redbrick\', \'posixAccount\', \'top\', ' + \
            '\'shadowAccount\']\n' + \
            'oldusertype       :  newb\n' + \
            'userPassword      :  e1NTSEF9WlBURGtJdmZJSld0WUlrak9zdGxscXYySTRRVEhj=\n' + \
            'homeDirectory     :  /home/redbrick/memberOne\n' + \
            'disuser_period    :  0\n' + \
            'shadowLastChange  :  17073\n'

    def test_to_string(self):
        """Test case A. note that all test method names must begin with 'test.'"""
        member_one = rbuser.RBUser()
        member_one.set_attr(**self.member_one_attr)
        assert member_one.__str__() == self.member_one_output, 'member1 attributes not as expected'

if __name__ == "__main__":
    unittest.main()  # run all tests
