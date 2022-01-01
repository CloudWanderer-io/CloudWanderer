import pytest

from cloudwanderer.urn import PartialUrn


@pytest.fixture
def partial_urn():
    return PartialUrn(
        account_id="111111111111",
        region="unknown",
        service="service",
        resource_type="resource_type",
        resource_id_parts=["id"],
    )


def test_is_partial(partial_urn):

    assert partial_urn.is_partial


def test_is_not_partial():
    complete_urn = PartialUrn(
        account_id="1", region="region", service="service", resource_type="resource_type", resource_id_parts=["id"]
    )

    assert not complete_urn.is_partial


def test_str_conversion(partial_urn):
    assert str(partial_urn) == "urn:unknown:111111111111:unknown:service:resource_type:id"


def test_non_string_id_parts():
    with pytest.raises(ValueError):
        PartialUrn(
            account_id="1", region="region", service="service", resource_type="resource_type", resource_id_parts=[1]
        )
