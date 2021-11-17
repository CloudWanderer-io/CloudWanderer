import logging
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


def validate_identifiers(service_name, resource_type, id_parts):
    urn_parts = {k: v for id_part in id_parts for k, v in id_part.specified_urn_parts.items()}
    resource = resource_type_cache(service_name, resource_type)
    assert len(resource.meta.resource_model.identifiers) == len(urn_parts["resource_id_parts"]), (
        f"Expected {[x.name for x in resource.meta.resource_model.identifiers]} "
        f"got {urn_parts['resource_id_parts']}. The id names are "
        "not expected to match, but the number of ids must match."
    )


def validate_relationship_spec_fulfils_uniqueness_scope(relationship_spec, originating_resource_type):

    resource = resource_type_cache(relationship_spec.service, relationship_spec.resource_type)
    scope = resource.resource_map.id_uniqueness_scope
    urn_components = {k: v for id_part in relationship_spec.id_parts for k, v in id_part.specified_urn_parts.items()}
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
