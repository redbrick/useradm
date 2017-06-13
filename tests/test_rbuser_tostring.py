"""RedBrick Test Module; Tests the to_string method of the rbuser module."""

import unittest

from tests import data_rbuser_tostring as data
from useradm import rbuser


class RBUserTestCase(unittest.TestCase):
    """Test Case class for to_string method"""

    def test_member_one(self):
        """Test case A. Member One"""
        member_one = rbuser.RBUser()
        member_one.set_attr(**data.MEMBER_ONE_ATTR)
        to_string_output = member_one.__str__()
        assert to_string_output == data.MEMBER_ONE_OUTPUT, \
            'member1 attributes not as expected. ' + \
            'Diff at: ' + [i for i in range(len(data.MEMBER_ONE_OUTPUT))
                           if data.MEMBER_ONE_OUPUT[i] != to_string_output[i]]

    def test_associate_one(self):
        """Test case B. Associate One"""
        associate_one = rbuser.RBUser()
        associate_one.set_attr(**data.ASSOCIATE_ONE_ATTR)
        to_string_output = associate_one.__str__()
        assert associate_one.__str__() == data.ASSOCIATE_ONE_OUTPUT, \
            'associate one attributes not as expected' + \
            'Diff at: ' + [i for i in range(len(data.ASSOCIATE_ONE_OUTPUT))
                           if data.ASSOCIATE_ONE_OUTPUT[i] != to_string_output[i]]

if __name__ == "__main__":
    unittest.main()  # run all tests
