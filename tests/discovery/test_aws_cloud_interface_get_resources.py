from unittest.mock import ANY, MagicMock
from cloudwanderer.aws_interface import CloudWandererAWSInterface
from cloudwanderer.cloud_wanderer_resource import CloudWandererResource
from pytest import fixture


@fixture
def aws_interface() -> CloudWandererAWSInterface:
    mock_cloudwanderer_boto3_session = MagicMock(
        **{
            "available_services": ["ec2"],
            "enabled_regions": ["us-east-1", "eu-west-1"],
            "resource.return_value": MagicMock(resource_types=["vpc"]),
            "account_id": "111111111111",
        }
    )
    return CloudWandererAWSInterface(cloudwanderer_boto3_session=mock_cloudwanderer_boto3_session)


def test_get_resources(aws_interface):
    result = list(aws_interface.get_resources(service_name="ec2", resource_type="vpc", region="eu-west-1"))
    assert isinstance(result[0], CloudWandererResource)
