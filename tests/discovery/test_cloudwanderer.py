import datetime
from unittest.mock import MagicMock

from pytest import fixture

from cloudwanderer import CloudWanderer
from cloudwanderer.aws_interface.interface import CloudWandererAWSInterface
from cloudwanderer.cloud_wanderer_resource import CloudWandererResource
from cloudwanderer.models import ActionSet, ServiceResourceType
from cloudwanderer.urn import URN, PartialUrn


@fixture
def cloud_wanderer() -> CloudWanderer:
    mock_storage_connector = MagicMock(**{})
    mock_cloud_interface = MagicMock(
        spec_set=CloudWandererAWSInterface,
        **{
            "get_resource_discovery_actions.return_value": [
                ActionSet(
                    get_urns=[
                        PartialUrn(
                            cloud_name="aws",
                            account_id="111111111111",
                            region="eu-west-1",
                            service="ec2",
                            resource_type="vpc",
                            resource_id_parts=["ALL"],
                        )
                    ],
                    delete_urns=[
                        PartialUrn(
                            cloud_name="aws",
                            account_id="111111111111",
                            region="eu-west-1",
                            service="ec2",
                            resource_type="vpc",
                            resource_id_parts=["ALL"],
                        )
                    ],
                )
            ],
            "get_resources.return_value": [
                CloudWandererResource(
                    URN(
                        cloud_name="aws",
                        account_id="111111111111",
                        region="eu-west-1",
                        service="ec2",
                        resource_type="vpc",
                        resource_id_parts=["vpc-11111111"],
                    ),
                    resource_data={},
                    discovery_time=datetime.datetime(1986, 1, 1, tzinfo=datetime.timezone.utc),
                )
            ],
        }
    )
    return CloudWanderer(storage_connectors=[mock_storage_connector], cloud_interface=mock_cloud_interface)


def test_write_resources(cloud_wanderer: CloudWanderer):
    cloud_wanderer.write_resources()

    cloud_wanderer.cloud_interface.get_resource_discovery_actions.assert_called()
    cloud_wanderer.cloud_interface.get_resources.assert_called_with(
        region="eu-west-1", service_name="ec2", resource_type="vpc", service_resource_type_filters=None
    )
    cloud_wanderer.storage_connectors[0].write_resource.assert_called_with(
        CloudWandererResource(
            urn=URN(
                cloud_name="aws",
                account_id="111111111111",
                region="eu-west-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=["vpc-11111111"],
            ),
            dependent_resource_urns=[],
            resource_data={},
        )
    )
    cloud_wanderer.storage_connectors[0].delete_resource_of_type_in_account_region.assert_called_with(
        cloud_name="aws",
        account_id="111111111111",
        region="eu-west-1",
        service="ec2",
        resource_type="vpc",
        cutoff=datetime.datetime(1986, 1, 1, 0, 0, tzinfo=datetime.timezone.utc),
    )


def test_get_resources_specific_resource(cloud_wanderer: CloudWanderer):
    cloud_wanderer.write_resources(service_resource_types=[ServiceResourceType(service="ec2", resource_type="vpc")])

    cloud_wanderer.cloud_interface.get_resource_discovery_actions.assert_called()
    cloud_wanderer.cloud_interface.get_resources.assert_called_with(
        region="eu-west-1", service_name="ec2", resource_type="vpc", service_resource_type_filters=None
    )
    cloud_wanderer.storage_connectors[0].write_resource.assert_called_with(
        CloudWandererResource(
            urn=URN(
                cloud_name="aws",
                account_id="111111111111",
                region="eu-west-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=["vpc-11111111"],
            ),
            dependent_resource_urns=[],
            resource_data={},
        )
    )
    cloud_wanderer.storage_connectors[0].delete_resource_of_type_in_account_region.assert_called_with(
        cloud_name="aws",
        account_id="111111111111",
        region="eu-west-1",
        service="ec2",
        resource_type="vpc",
        cutoff=datetime.datetime(1986, 1, 1, 0, 0, tzinfo=datetime.timezone.utc),
    )
