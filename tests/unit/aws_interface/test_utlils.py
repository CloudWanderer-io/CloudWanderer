from cloudwanderer.aws_interface.utils import _get_urn_components_from_string


def test__get_urn_components_from_string():
    string = "arn:aws:iam::0123456789012:instance-profile/testProfile"
    pattern = "[^:]+:[^:]+:[^:]+:[^:]*:(?P<account_id>[^:]+):[^:]+/(?P<id_part_0>[^:]+)"

    result = _get_urn_components_from_string(pattern, string)

    assert result == {"account_id": "0123456789012", "resource_id_parts": ["testProfile"]}
