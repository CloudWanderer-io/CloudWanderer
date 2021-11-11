from unittest.mock import MagicMock

from cloudwanderer.aws_interface import AWSResourceTypeFilter


def test_str():
    subject = AWSResourceTypeFilter(
        service="ec2", resource_type="image", botocore_filters={"Scope": "local"}, jmespath_filters=[""]
    )

    assert (
        str(subject) == "AWSResourceTypeFilter(service='ec2', "
        "resource_type='image', "
        "botocore_filters={'Scope': 'local'}, "
        "jmespath_filters=[''])"
    )


def test_filter_jmespath_true():
    subject = AWSResourceTypeFilter(
        service="iam",
        resource_type="policy_version",
        botocore_filters={},
        jmespath_filters=["[?IsDefaultVersion==`true`]"],
    )

    assert list(subject.filter_jmespath([MagicMock(**{"meta.data": {"IsDefaultVersion": True}})]))


def test_filter_jmespath_false():
    subject = AWSResourceTypeFilter(
        service="iam",
        resource_type="policy_version",
        botocore_filters={},
        jmespath_filters=["[?IsDefaultVersion==`true`]"],
    )

    assert not list(subject.filter_jmespath([MagicMock(**{"meta.data": {"IsDefaultVersion": False}})]))
