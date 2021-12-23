from unittest.mock import MagicMock

from cloudwanderer.aws_interface import CloudWandererAWSInterface


def test_get_resources_requires_load():
    mock_session = MagicMock(
        **{
            "available_services": ["test_service"],
            "enabled_regions": ["test-region"],
            "account_id": "111111111111",
        }
    )
    mock_service = mock_session.resource.return_value
    mock_resource = MagicMock()
    mock_resource.resource_map.requires_load = True
    mock_service.collection.return_value = [mock_resource]

    interface = CloudWandererAWSInterface(cloudwanderer_boto3_session=mock_session)

    list(interface.get_resources(service_name="test_service", resource_type="test_resource", region="test-region"))

    mock_resource.load.assert_called()
