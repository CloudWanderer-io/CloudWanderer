from typing import List

from ..models import TemplateActionSet

class CloudWandererServiceResource:
    service_name: str
    resource_type: str
    resource_types: List[str]
    dependent_resource_types: List[str]
    def resource(
        self, resource_type: str, identifiers: List[str] = None, empty_resource=False
    ) -> "CloudWandererServiceResource": ...
    def get_discovery_action_templates(self, discovery_regions: List[str]) -> List[TemplateActionSet]: ...
    def get_dependent_resource(
        self, resource_type: str, args: List[str] = None, empty_resource=False
    ) -> "CloudWandererServiceResource": ...
