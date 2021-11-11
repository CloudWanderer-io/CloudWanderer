"""AWS Interface specific model classes."""
from typing import Any, Dict, Iterator, List, Optional

import jmespath  # type: ignore
from boto3.resources.base import ServiceResource

from ..models import ServiceResourceTypeFilter


class AWSResourceTypeFilter(ServiceResourceTypeFilter):
    """AWS Specific resource type filter.

    Allows specification of either botocore filters or jmespath filters.
    """

    service: str
    resource_type: str
    botocore_filters: Dict[str, Any]
    jmespath_filters: List[str]

    def __init__(
        self,
        service: str,
        resource_type: str,
        botocore_filters: Optional[Dict[str, Any]] = None,
        jmespath_filters: Optional[List[str]] = None,
    ) -> None:
        self.service = service
        self.resource_type = resource_type
        self.botocore_filters = botocore_filters or {}
        self.jmespath_filters = jmespath_filters or []

    def filter_jmespath(self, resources: List[ServiceResource]) -> Iterator[ServiceResource]:
        if not self.jmespath_filters:
            yield from resources
        for resource in resources:
            for filter in self.jmespath_filters:
                if jmespath.search(filter, [resource.meta.data]):
                    yield resource

    def __repr__(self) -> str:
        """Return an instantiable representation of this object."""
        return (
            "AWSResourceTypeFilter("
            f"service='{self.service}', "
            f"resource_type='{self.resource_type}', "
            f"botocore_filters={self.botocore_filters}, "
            f"jmespath_filters={self.jmespath_filters})"
        )
