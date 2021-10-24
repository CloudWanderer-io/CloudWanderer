import logging
from typing import Any, List, NamedTuple

logger = logging.getLogger(__file__)

# TODO Clean up this legacy code in favour of the more modern pytest_helpers


def filter_collections(collections, service_resource):
    for collection in collections:
        if service_resource.meta.resource_model.name == collection.meta.service_name:
            yield collection


def has_matching_urn(iterable, **kwargs):
    matches = []
    for resource in iterable:
        attribute_results = []
        for key, value in kwargs.items():
            attribute_results.append(getattr(resource.urn, key) == value)
        if all(attribute_results):
            matches.append(resource.urn)
    return matches


def assert_has_matching_urns(iterable, urns):
    """Assert that iterable has URNs that match the list of dicts in urns

    Arguments:
        iterable (iterable):
            An iterable containing URN objects
        urns (list):
            List of dictionaries whose key match aws urn attributes that must
            exist in at least one urn in iterable.
    """
    iterable = list(iterable)
    for urn in urns:
        assert has_matching_urn(iterable, **urn), f"{urn} not in {iterable}"


def assert_does_not_have_matching_urns(iterable, urns):
    """Assert that iterable does not have URNs that match the list of dicts in urns

    Arguments:
        iterable (iterable):
            An iterable containing URN objects
        urns (list):
            List of dictionaries whose keys should not match aws urn attributes that must
            exist in at least one urn in iterable.
    """
    iterable = list(iterable)
    for urn in urns:
        assert not has_matching_urn(iterable, **urn), f"{urn} is in {iterable}"


class ItemResult(NamedTuple):
    result: bool
    expected_value: Any
    received_value: Any


class OverlapResult(NamedTuple):
    expected_item: Any
    received_item: Any
    results: List[ItemResult]

    def __repr__(self):
        return (
            f"\nExpected\n\t{self.expected_item}\n"
            f"got\n\t{self.received_item}\n"
            f"differing on:\n\t{[x for x in self.results if not x.result]}"
        )
