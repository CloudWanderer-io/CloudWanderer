import re
from functools import lru_cache

import pytest

from cloudwanderer.aws_interface import CloudWandererBoto3Session


@lru_cache
def session_cache():
    return CloudWandererBoto3Session()


@lru_cache
def service_cache(service_name):
    session = session_cache()
    return session.resource(service_name)


@lru_cache(maxsize=999)
def resource_type_cache(service_name, resource_type):
    service = service_cache(service_name)
    return service.resource(resource_type, empty_resource=True)


def validate_id_parts(service_name, resource_type, id_parts):
    resource = resource_type_cache(service_name, resource_type)
    id_part_list = []

    for part in id_parts:
        if part.regex_pattern:
            pattern = re.compile(part.regex_pattern)
            id_part_list.extend(id_part for id_part in pattern.groupindex.keys() if id_part.startswith("id_"))
            continue
        id_part_list.append(part.path)
    assert len(resource.meta.resource_model.identifiers) == len(id_part_list), (
        f"Expected {[x.name for x in resource.meta.resource_model.identifiers]} "
        f"got {id_part_list}. These are not expected to match names, but the number of ids must match."
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
    for relationship in resource.resource_map.relationships:
        validate_id_parts(relationship.service, relationship.resource_type, relationship.id_parts)
