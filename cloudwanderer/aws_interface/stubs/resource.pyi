from typing import Any, Collection, Dict, List, Optional

from boto3.resources.base import ResourceMeta

from ...models import Relationship, TemplateActionSet
from ...urn import URN
from ..boto3_loaders import ServiceMap

class CloudWandererServiceResource:
    service_name: str
    resource_type: str
    resource_types: List[str]
    dependent_resource_types: List[str]
    service_map: ServiceMap
    meta: ResourceMeta
    normalized_raw_data: Dict[str, Any]
    relationships: List[Relationship]
    def resource(
        self, resource_type: str, identifiers: List[str] = None, empty_resource=False
    ) -> "CloudWandererServiceResource": ...
    def get_discovery_action_templates(self, discovery_regions: List[str]) -> List[TemplateActionSet]: ...
    def get_dependent_resource(
        self, resource_type: str, args: List[str] = None, empty_resource=False
    ) -> "CloudWandererServiceResource": ...
    def get_urn(self) -> URN: ...
    def get_region(self) -> str: ...
    def collection(self, resource_type: str, filters: Optional[Dict[str, str]] = None) -> Collection: ...
    def load(self) -> None: ...
    def fetch_secondary_attributes(self) -> None: ...
