"""AWS Interface specific model classes."""
import jmespath  # type: ignore
from typing import Any, Dict, Iterator, List, Optional

from ..cloud_wanderer_resource import CloudWandererResource
from ..models import ServiceResourceTypeFilter
import logging
from boto3.resources.base import ServiceResource

logger = logging.getLogger(__name__)


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
            logger.info("Returning all as no jmespath filter is set")
            yield from resources
        for resource in resources:
            for filter in self.jmespath_filters:
                if jmespath.search(filter, [resource.meta.data]):
                    yield resource

    def __repr__(self):
        return f"AWSResourceTypeFilter(service='{self.service}', resource_type='{self.resource_type}', botocore_filters={self.botocore_filters}, jmespath_filters={self.jmespath_filters})"
