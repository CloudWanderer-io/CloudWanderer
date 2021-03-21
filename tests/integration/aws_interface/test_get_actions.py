import unittest

from cloudwanderer.aws_interface import CloudWandererAWSInterface
from cloudwanderer.models import CleanupAction, GetAction, GetAndCleanUp


class TestGetActions(unittest.TestCase):
    def setUp(self):
        self.aws_interface = CloudWandererAWSInterface()

    def test_no_arguments_has_global_service_regional_resources_cleanup(self):
        result = self.aws_interface.get_actions()

        assert (
            GetAndCleanUp(
                get_actions=[GetAction(service_name="s3", region="us-east-1", resource_type="bucket")],
                cleanup_actions=[
                    CleanupAction(service_name="s3", region=region, resource_type="bucket")
                    for region in self.aws_interface.boto3_services.enabled_regions
                ],
            )
            in result
        )

    def test_single_resource_regional(self):
        result = self.aws_interface.get_actions(resource_types=["instance"])
        expected_result = [
            GetAndCleanUp(
                get_actions=[GetAction(service_name="ec2", region=region, resource_type="instance")],
                cleanup_actions=[CleanupAction(service_name="ec2", region=region, resource_type="instance")],
            )
            for region in self.aws_interface.boto3_services.enabled_regions
        ]

        assert result == expected_result

    def test_single_resource_global_service_all_regions(self):
        assert self.aws_interface.get_actions(resource_types=["role"]) == [
            GetAndCleanUp(
                get_actions=[GetAction(service_name="iam", region="us-east-1", resource_type="role")],
                cleanup_actions=[
                    CleanupAction(service_name="iam", region="us-east-1", resource_type="role"),
                    CleanupAction(service_name="iam", region="us-east-1", resource_type="role_policy"),
                ],
            )
        ]

    def test_single_resource_global_service_regional_resource(self):
        assert self.aws_interface.get_actions(resource_types=["bucket"]) == [
            GetAndCleanUp(
                get_actions=[GetAction(service_name="s3", region="us-east-1", resource_type="bucket")],
                cleanup_actions=[
                    CleanupAction(service_name="s3", region=region, resource_type="bucket")
                    for region in self.aws_interface.boto3_services.enabled_regions
                ],
            )
        ]

    def test_single_resource_global_service_api_region(self):
        assert self.aws_interface.get_actions(resource_types=["role"], regions=["us-east-1"]) == [
            GetAndCleanUp(
                get_actions=[GetAction(service_name="iam", region="us-east-1", resource_type="role")],
                cleanup_actions=[
                    CleanupAction(service_name="iam", region="us-east-1", resource_type="role"),
                    CleanupAction(service_name="iam", region="us-east-1", resource_type="role_policy"),
                ],
            )
        ]

    def test_single_resource_global_service_non_api_region(self):
        assert self.aws_interface.get_actions(resource_types=["role"], regions=["eu-west-2"]) == []

    def test_single_resource_global_service_regional_resource_api_region(self):
        assert self.aws_interface.get_actions(resource_types=["bucket"], regions=["us-east-1"]) == [
            GetAndCleanUp(
                get_actions=[GetAction(service_name="s3", region="us-east-1", resource_type="bucket")],
                cleanup_actions=[
                    CleanupAction(service_name="s3", region=region, resource_type="bucket")
                    for region in self.aws_interface.boto3_services.enabled_regions
                ],
            )
        ]

    def test_single_resource_global_service_regional_resource_non_api_region(self):
        assert self.aws_interface.get_actions(resource_types=["bucket"], regions=["eu-west-2"]) == []

    def test_exclude_resources(self):
        result = self.aws_interface.get_actions(service_names=["ec2"], exclude_resources=["ec2:instance"])
        get_action_resource_types = set(
            get_action.resource_type for actions in result for get_action in actions.get_actions
        )
        cleanup_action_resource_types = set(
            cleanup_action.resource_type for actions in result for cleanup_action in actions.cleanup_actions
        )

        assert "instance" not in get_action_resource_types
        assert "instance" not in cleanup_action_resource_types
