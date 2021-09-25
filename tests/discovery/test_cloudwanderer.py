import datetime
from cloudwanderer.urn import URN, PartialUrn
from cloudwanderer.cloud_wanderer_resource import CloudWandererResource
from pytest import fixture
from unittest.mock import MagicMock
from cloudwanderer import CloudWanderer
from cloudwanderer.models import ActionSet


@fixture
def cloud_wanderer() -> CloudWanderer:
    mock_storage_connector = MagicMock(**{})
    mock_cloud_interface = MagicMock(
        **{
            "get_resource_discovery_actions.return_value": [
                ActionSet(
                    get_urns=[
                        PartialUrn(
                            account_id="111111111111",
                            region="eu-west-1",
                            service="ec2",
                            resource_type="vpc",
                            resource_id="ALL",
                        )
                    ],
                    delete_urns=[
                        PartialUrn(
                            account_id="111111111111",
                            region="eu-west-1",
                            service="ec2",
                            resource_type="vpc",
                            resource_id="ALL",
                        )
                    ],
                )
            ],
            "get_resources.return_value": [
                CloudWandererResource(
                    URN(
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


def test_get_resources(cloud_wanderer: CloudWanderer):
    cloud_wanderer.write_resources()

    cloud_wanderer.cloud_interface.get_resource_discovery_actions.assert_called()
    cloud_wanderer.cloud_interface.get_resources.assert_called_with(
        region="eu-west-1", service_name="ec2", resource_type="vpc"
    )
    cloud_wanderer.storage_connectors[0].write_resource.assert_called_with(
        CloudWandererResource(
            urn=URN(
                account_id="111111111111",
                region="eu-west-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=["vpc-11111111"],
            ),
            subresource_urns=[],
            resource_data={},
            secondary_attributes=[],
        )
    )
    cloud_wanderer.storage_connectors[0].delete_resource_of_type_in_account_region.assert_called_with(
        account_id="111111111111",
        region="eu-west-1",
        service="ec2",
        resource_type="vpc",
        cutoff=datetime.datetime(1986, 1, 1, 0, 0, tzinfo=datetime.timezone.utc),
    )
