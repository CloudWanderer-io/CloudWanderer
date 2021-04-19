import unittest

from cloudwanderer.models import CleanupAction, GetAction, GetAndCleanUp


class TestGetAndCleanUp(unittest.TestCase):
    def test_addition(self):
        result = GetAndCleanUp([GetAction("ec2", "eu-west-1", "instance")], [])
        result += GetAndCleanUp([], [CleanupAction("ec2", "eu-west-1", "instance")])

        assert result == GetAndCleanUp(
            [GetAction("ec2", "eu-west-1", "instance")], [CleanupAction("ec2", "eu-west-1", "instance")]
        )

    def test_addition_bad_value(self):
        result = GetAndCleanUp([GetAction("ec2", "eu-west-1", "instance")], [])
        with self.assertRaisesRegex(TypeError, r"unsupported operand type\(s\) for \+: GetAndCleanUp and int"):
            result += 1
