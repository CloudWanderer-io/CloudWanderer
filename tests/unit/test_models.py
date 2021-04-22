import unittest

from cloudwanderer.models import AWSGetAndCleanUp, CleanupAction, GetAction, GetAndCleanUp


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


class TestAWSGetAndCleanup:
    def test_inflate(self):
        actions = AWSGetAndCleanUp(
            [GetAction("ec2", "ALL_REGIONS", "instance")], [CleanupAction("ec2", "ALL_REGIONS", "instance")]
        )

        result = actions.inflate_actions(["us-east-1", "eu-west-1", "ap-east-1"])

        assert result == GetAndCleanUp(
            get_actions=[
                GetAction(service_name="ec2", region="us-east-1", resource_type="instance"),
                GetAction(service_name="ec2", region="eu-west-1", resource_type="instance"),
                GetAction(service_name="ec2", region="ap-east-1", resource_type="instance"),
            ],
            cleanup_actions=[
                CleanupAction(service_name="ec2", region="us-east-1", resource_type="instance"),
                CleanupAction(service_name="ec2", region="eu-west-1", resource_type="instance"),
                CleanupAction(service_name="ec2", region="ap-east-1", resource_type="instance"),
            ],
        )
