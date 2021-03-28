import unittest

from cloudwanderer.cloud_wanderer_resource import SecondaryAttribute


class TestSecondaryAttribute(unittest.TestCase):
    def test_vpc_secondary_attribute(self):
        secondary_attribute = SecondaryAttribute(name="EnableDnsSupport", **{"EnableDnsSupport": {"Value": True}})

        assert secondary_attribute.name == "EnableDnsSupport"
        assert dict(secondary_attribute) == {"EnableDnsSupport": {"Value": True}}

    def test_empty(self):
        secondary_attribute = SecondaryAttribute(name=None)

        assert secondary_attribute.name is None
        assert dict(secondary_attribute) == {}
