from .boto3_loaders import ServiceMappingLoader
from .resource_factory import CloudWandererResourceFactory
from ..models import ActionSet
from typing import List, Optional, Tuple
import boto3
import logging

logger = logging.getLogger(__name__)


class CloudWandererBoto3Session(boto3.session.Session):
    def __init__(
        self,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None,
        region_name=None,
        botocore_session=None,
        profile_name=None,
        resource_factory=None,
        service_mapping_loader=None,
    ) -> None:
        super().__init__(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=region_name,
            botocore_session=botocore_session,
            profile_name=profile_name,
        )
        self.service_mapping_loader = service_mapping_loader or ServiceMappingLoader()
        self.resource_factory = resource_factory or CloudWandererResourceFactory(
            self._session.get_component("event_emitter"), service_mapping_loader=self.service_mapping_loader
        )

    def get_resource_discovery_actions(
        self, services_resource_tuples: List[Tuple[str]], regions: List[str]
    ) -> List[ActionSet]:
        service_names = [service for service, _ in services_resource_tuples]
        action_sets = []
        service_names = service_names or self.available_services
        for service_name in service_names:
            logger.debug("Getting resource_types for %s", service_name)
            service = self.resource(service_name=service_name)
            resource_types = [resource_type for _, resource_type in services_resource_tuples]
            action_sets.extend(service.get_resource_discovery_actions(resource_types=resource_types, regions=regions))

        return action_sets
