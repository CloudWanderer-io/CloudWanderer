from cloudwanderer.aws_interface.models import IdPartSpecification, RelationshipSpecification
from cloudwanderer.models import RelationshipAccountIdSource, RelationshipDirection, RelationshipRegionSource


def test_get_specified_urn_parts():
    subject = IdPartSpecification.factory(
        definition={
            "path": "IamInstanceProfile.Arn",
            "regexPattern": "[^:]+:[^:]+:[^:]+:[^:]*:(?P<account_id>[^:]+):[^:]+/(?P<id_part_0>[^:]+)",
        }
    )

    assert subject.specified_urn_parts == {"account_id": ["account_id"], "resource_id_parts": ["id_part_0"]}


def testget_urn_parts_regex():
    data = {"IamInstanceProfile": {"Arn": "arn:aws:iam::0123456789012:instance-profile/testProfile"}}
    subject = IdPartSpecification.factory(
        definition={
            "path": "IamInstanceProfile.Arn",
            "regexPattern": "[^:]+:[^:]+:[^:]+:[^:]*:(?P<account_id>[^:]+):[^:]+/(?P<id_part_0>[^:]+)",
        }
    )

    assert subject.get_urn_parts(data) == {"account_id": "0123456789012", "resource_id_parts": ["testProfile"]}


def test_get_urn_parts_no_regex():
    data = {"SubnetId": "subnet-111111111"}
    subject = IdPartSpecification.factory(
        definition={
            "path": "SubnetId",
        }
    )

    assert subject.get_urn_parts(data) == {"resource_id_parts": ["subnet-111111111"]}


def test_relationship_specification_factory():
    subject = RelationshipSpecification.factory(
        definition={
            "basePath": "Id",
            "idParts": "",
            "direction": "outbound",
            "service": "test_service",
            "resourceType": "test_resource_type",
            "regionSource": "sameAsResource",
            "accountIdSource": "sameAsResource",
        }
    )

    assert subject == RelationshipSpecification(
        base_path="Id",
        id_parts=[],
        cloud_name="aws",
        service="test_service",
        resource_type="test_resource_type",
        region_source=RelationshipRegionSource.SAME_AS_RESOURCE,
        account_id_source=RelationshipAccountIdSource.SAME_AS_RESOURCE,
        direction=RelationshipDirection.OUTBOUND,
    )
