import logging
import re
from collections import defaultdict
from functools import lru_cache

import pytest

from cloudwanderer.aws_interface import CloudWandererBoto3Session
from cloudwanderer.models import RelationshipAccountIdSource, RelationshipRegionSource

logger = logging.getLogger(__name__)


@lru_cache()
def session_cache():
    return CloudWandererBoto3Session()


@lru_cache()
def service_cache(service_name):
    session = session_cache()
    return session.resource(service_name)


@lru_cache(maxsize=999)
def resource_type_cache(service_name, resource_type):
    service = service_cache(service_name)
    return service.resource(resource_type, empty_resource=True)


def get_matching_groups(regex_pattern, starts_with=""):
    pattern = re.compile(regex_pattern)
    return [id_part for id_part in pattern.groupindex.keys()]


def get_urn_components_from_id_parts(id_parts):
    urn_parts = defaultdict(list)
    for part in id_parts:
        if part.regex_pattern:
            for matching_group in get_matching_groups(part.regex_pattern):
                if matching_group.startswith("id_"):
                    urn_parts["id_parts"].append(matching_group)
                    continue
                urn_parts[matching_group].append("regex")
            continue
        urn_parts["id_parts"].append(part.path)
    return dict(urn_parts)


def validate_identifiers(service_name, resource_type, id_parts):
    identifiers = get_urn_components_from_id_parts(id_parts).get("id_parts", [])
    resource = resource_type_cache(service_name, resource_type)
    assert len(resource.meta.resource_model.identifiers) == len(identifiers), (
        f"Expected {[x.name for x in resource.meta.resource_model.identifiers]} "
        f"got {identifiers}. The id names are not expected to match, but the number of ids must match."
    )


def validate_relationship_spec_fulfils_uniqueness_scope(relationship_spec, originating_resource_type):

    # regex_matching_groups = get_matching_groups()
    resource = resource_type_cache(relationship_spec.service, relationship_spec.resource_type)
    scope = resource.resource_map.id_uniqueness_scope
    urn_components = get_urn_components_from_id_parts(relationship_spec.id_parts)
    if scope.requires_region:
        assert relationship_spec.region_source != RelationshipRegionSource.UNKNOWN or "region" in urn_components, (
            f"{relationship_spec.service} {relationship_spec.resource_type} requires "
            "region to uniquely identify it, but "
            f"relationship from {originating_resource_type} does not specify it"
        )
    if scope.requires_account_id:
        assert (
            relationship_spec.account_id_source != RelationshipAccountIdSource.UNKNOWN or "account_id" in urn_components
        ), (
            f"{relationship_spec.service} {relationship_spec.resource_type} requires "
            "account id to uniquely identify it, but "
            f"relationship from {originating_resource_type} does not specify it"
        )


def get_resources_to_test():
    session = CloudWandererBoto3Session()
    for service_name in session.get_available_resources():
        service = service_cache(service_name)
        for resource_type in service.resource_types:
            resource = resource_type_cache(service_name, resource_type)
            yield f"{service.service_name}_{resource_type}", resource
            for dependent_resource_type in resource.dependent_resource_types:
                dependent_resource = service.resource(dependent_resource_type, empty_resource=True)
                yield f"{service.service_name}_{dependent_resource_type}", dependent_resource


@pytest.mark.parametrize("resource_type, resource", get_resources_to_test())
def test_identities(resource_type, resource):
    for relationship_spec in resource.resource_map.relationships:

        validate_identifiers(relationship_spec.service, relationship_spec.resource_type, relationship_spec.id_parts)
        validate_relationship_spec_fulfils_uniqueness_scope(relationship_spec, resource_type)
