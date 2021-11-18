import unittest
from unittest.mock import MagicMock

import boto3
from boto3.resources.model import ResourceModel

from cloudwanderer.aws_interface.models import (
    AWSResourceTypeFilter,
    IdPartSpecification,
    RelationshipSpecification,
    ResourceMap,
    ResourceRegionRequest,
)
from cloudwanderer.models import (
    RelationshipAccountIdSource,
    RelationshipDirection,
    RelationshipRegionSource,
    ResourceIdUniquenessScope,
)


class TestResourceMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ec2_service_model = boto3.session.Session()._loader.load_service_model("ec2", "resources-1", "2016-11-15")
        s3_service_model = boto3.session.Session()._loader.load_service_model("s3", "resources-1", "2006-03-01")
        iam_service_model = boto3.session.Session()._loader.load_service_model("iam", "resources-1", "2010-05-08")
        cls.vpc_resource_model = ResourceModel(
            name="Vpc",
            definition=ec2_service_model["resources"]["Vpc"],
            resource_defs=ec2_service_model["resources"],
        )
        cls.bucket_resource_model = ResourceModel(
            name="Bucket",
            definition=s3_service_model["resources"]["Bucket"],
            resource_defs=s3_service_model["resources"],
        )
        cls.role_resource_model = ResourceModel(
            name="Role",
            definition=iam_service_model["resources"]["Role"],
            resource_defs=iam_service_model["resources"],
        )

    def test_global_service_regional_resource_map(self):
        resource_map = ResourceMap.factory(
            name="Bucket",
            definition={
                "type": "resource",
                "regionalResource": False,
                "regionRequest": {
                    "operation": "get_bucket_location",
                    "params": [{"target": "Bucket", "source": "resourceAttribute", "name": "name"}],
                    "pathToRegion": "LocationConstraint",
                    "defaultValue": "us-east-1",
                },
                "requiresLoadForFullMetadata": True,
                "defaultFilters": {"Key": "Value"},
            },
            service_map=MagicMock(),
        )

        assert isinstance(resource_map.region_request, ResourceRegionRequest)

        assert not resource_map.regional_resource
        assert isinstance(resource_map.default_aws_resource_type_filter, AWSResourceTypeFilter)

    def test_dependent_resource_map(self):
        resource_map = ResourceMap.factory(
            name="RolePolicy",
            definition={"type": "resource", "parentResourceType": "role"},
            service_map=MagicMock(),
        )

        assert isinstance(resource_map.default_aws_resource_type_filter, AWSResourceTypeFilter)
        assert resource_map.name == "RolePolicy"

    def test_should_query_resources_in_region_global_service(self):
        resource_map = ResourceMap.factory(
            name="Role",
            definition={},
            service_map=MagicMock(is_global_service=True, global_service_region="us-east-1"),
        )

        assert resource_map.should_query_resources_in_region("us-east-1")
        assert not resource_map.should_query_resources_in_region("eu-west-1")

    def test_should_query_resources_in_region_regional_service(self):
        resource_map = ResourceMap.factory(
            definition={},
            name="Instance",
            service_map=MagicMock(is_global_service=False),
        )

        assert resource_map.should_query_resources_in_region("us-east-1")
        assert resource_map.should_query_resources_in_region("eu-west-1")

    def test_relationships(self):
        resource_map = ResourceMap.factory(
            name="Vpc",
            definition={
                "relationships": [
                    {
                        "basePath": "@",
                        "idParts": [{"path": "VpcId"}],
                        "service": "ec2",
                        "resourceType": "vpc",
                        "regionSource": "sameAsResource",
                        "accountIdSource": "unknown",
                        "direction": "inbound",
                    }
                ],
            },
            service_map=MagicMock(is_global_service=False),
        )

        assert resource_map.relationships == [
            RelationshipSpecification(
                base_path="@",
                direction=RelationshipDirection.INBOUND,
                id_parts=[IdPartSpecification(path="VpcId", regex_pattern="")],
                service="ec2",
                resource_type="vpc",
                region_source=RelationshipRegionSource.SAME_AS_RESOURCE,
                account_id_source=RelationshipAccountIdSource.UNKNOWN,
            )
        ]

    def test_uniqueness_scope(self):
        resource_map = ResourceMap.factory(
            name="Vpc",
            definition={"idUniquenessScope": {"requiresRegion": False, "requiresAccountId": False}},
            service_map=MagicMock(is_global_service=False),
        )

        assert resource_map.id_uniqueness_scope == ResourceIdUniquenessScope(
            requires_region=False, requires_account_id=False
        )
