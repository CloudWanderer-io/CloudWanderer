import pytest
from cloudwanderer.urn import PartialUrn


def test_is_partial():
    partial_urn = PartialUrn(
        account_id="1", region="unknown", service="service", resource_type="resource_type", resource_id_parts=["id"]
    )

    assert partial_urn.is_partial


def test_is_not_partial():
    partial_urn = PartialUrn(
        account_id="1", region="region", service="service", resource_type="resource_type", resource_id_parts=["id"]
    )

    assert not partial_urn.is_partial
