from cloudwanderer.aws_interface.models import IdPartSpecification


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
