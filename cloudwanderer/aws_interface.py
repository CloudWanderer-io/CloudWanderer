"""Code which abstracts away the majority of boto3 interrogation.

Provides simpler methods for :class:`~.cloud_wanderer.CloudWanderer` to call.
"""

import logging
from typing import Iterator, List

import boto3
from boto3.resources.model import ResourceModel

from .boto3_getter import Boto3Getter
from .boto3_helpers import (
    Boto3CommonAttributesMixin,
    _prepare_boto3_resource_data,
    get_resource_collection_by_resource_type,
    get_resource_from_collection,
)
from .cloud_wanderer_resource import CloudWandererResource
from .exceptions import BadRequestError, ResourceNotFoundError
from .service_mappings import ServiceMappingCollection
from .storage_connectors.base_connector import BaseStorageConnector
from .urn import URN

logger = logging.getLogger(__name__)


class CloudWandererAWSInterface(Boto3CommonAttributesMixin):
    """Simplifies lookup of boto3 services and resources."""

    def __init__(self, boto3_session: boto3.session.Session = None) -> None:
        """Simplifies lookup of boto3 services and resources.

        Arguments:
            boto3_session (boto3.session.Session):
                A boto3 session, if not provided the default will be used.
        """
        self.boto3_session = boto3_session or boto3.Session()
        self.service_maps = ServiceMappingCollection(boto3_session=self.boto3_session)
        self.boto3_getter = Boto3Getter(boto3_session=self.boto3_session, service_maps=self.service_maps)

    def get_resource(self, urn: URN) -> CloudWandererResource:
        """Return CloudWandererResource picked out by this urn.

        Arguments:
            urn (URN): The urn of the resource to get.
        """
        try:
            resource = self.boto3_getter.get_resource_from_urn(urn=urn)
        except ResourceNotFoundError:
            return None
        except BadRequestError:
            logger.debug(
                f"Got BadRequestError while getting {urn}, as AWS services commonly return 4xx errors other than 404 "
                "for resource non-existence we are interpreting this as the resource does not exist."
            )
            return None

        return CloudWandererResource(
            urn=urn,
            resource_data=_prepare_boto3_resource_data(resource),
            secondary_attributes=list(self.boto3_getter.get_secondary_attributes(resource)),
        )

    def get_resources(
        self,
        regions: List[str] = None,
        service_names: List[str] = None,
        resource_types: List[str] = None,
        exclude_resources: List[str] = None,
        **kwargs,
    ) -> Iterator[CloudWandererResource]:
        """Get resources matching the arguments.

        All arguments are optional.

        Arguments:
            regions(list):
                The name of the region to get resources from (defaults to session default if not specified)
            service_names (str):
                The names of the services to write resources for (e.g. ``['ec2']``)
            resource_types (list):
                A list of resource types to include (e.g. ``['instance']``)
            exclude_resources (list):
                A list of service:resources to exclude (e.g. ``['ec2:instance']``)
            kwargs:
                All additional keyword arguments will be passed down to the Boto3 client calls.
        """
        regions = regions or self.enabled_regions
        for region_name in regions:
            yield from self._get_resources_in_region(
                service_names=service_names,
                resource_types=resource_types,
                exclude_resources=exclude_resources,
                region_name=region_name,
                **kwargs,
            )

    def _get_resources_in_region(
        self,
        service_names: List[str],
        resource_types: List[str] = None,
        exclude_resources: List[str] = None,
        region_name: str = None,
        **kwargs,
    ) -> None:
        """Get resources in region matching the resource types.

        Any additional args will be passed into the Boto3 client methods.

        Arguments:
            service_names (str):
                The names of the services to write resources for (e.g. ``['ec2']``)
            resource_types (list):
                A list of resource types to include (e.g. ``['instance']``)
            exclude_resources (list):
                exclude_resources (list): A list of service:resources to exclude (e.g. ``['ec2:instance']``)
            region_name (str):
                The name of the region to get resources from (defaults to session default if not specified)
            **kwargs: Additional keyword arguments will be passed down to the cloud interface methods.
        """
        exclude_resources = exclude_resources or []
        boto3_services = self.boto3_getter.get_resource_services_from_names(service_names, **kwargs)
        for boto3_service in boto3_services:
            yield from self._get_resources_of_service_in_region(
                service_name=boto3_service.meta.service_name,
                resource_types=resource_types,
                exclude_resources=exclude_resources,
                region_name=region_name,
                **kwargs,
            )

    def _get_resources_of_service_in_region(
        self,
        service_name: str,
        exclude_resources: List[str] = None,
        resource_types: List[str] = None,
        region_name: str = None,
        **kwargs,
    ) -> None:
        """Write all AWS resources in this region in this service to storage.

        Any additional args will be passed into the Boto3 client methods.

        Arguments:
            service_name (str):
                The name of the service to write resources for (e.g. ``'ec2'``)
            exclude_resources (list):
                A list of service:resources to exclude (e.g. ``['ec2:instance']``)
            resource_types (list):
                A list of resource types to include (e.g. ``['instance']``)
            region_name (str):
                The name of the region to get resources from
                (defaults to session default if not specified)
            **kwargs: Additional keyword arguments will be passed down to the cloud interface methods.
        """
        region_name = region_name or self.region_name

        logger.info("Writing all %s resources in %s", service_name, region_name)
        exclude_resources = exclude_resources or []
        resource_types = self.boto3_getter.custom_resource_definitions.get_valid_resource_types(
            service_name=service_name, resource_types=resource_types
        )
        for resource_type in resource_types:
            if f"{service_name}:{resource_type}" in exclude_resources:
                logger.info(
                    "Skipping %s as per exclude_resources",
                    f"{service_name}:{resource_type}",
                )
                continue
            yield from self._get_resources_of_type_in_region(
                service_name=service_name,
                resource_type=resource_type,
                region_name=region_name,
                **kwargs,
            )

    def _get_resources_of_type_in_region(
        self,
        service_name: str,
        resource_type: str = None,
        region_name: str = None,
        **kwargs,
    ) -> None:
        """Write all AWS resources in this region in this service to storage.

        Any additional args will be passed into the Boto3 client methods.

        Arguments:
            service_name (str):
                The name of the service to write resources for (e.g. ``'ec2'``)
            resource_type (str):
                The name of the type of the resource to write (e.g. ``'instance'``)
            region_name (str):
                The name of the region to get resources from
                (defaults to session default if not specified)
            **kwargs: Additional keyword arguments will be passed down to the cloud interface methods.
        """
        region_name = region_name or self.cloud_interface.region_name
        logger.info("Fetching %s %s from %s", service_name, resource_type, region_name)
        yield from self._get_resources_of_type(
            service_name=service_name,
            resource_type=resource_type,
            region_name=region_name,
            **kwargs,
        )

    def _get_resources_of_type(
        self, service_name: str, resource_type: str, region_name: str = None, **kwargs
    ) -> Iterator[ResourceModel]:
        """Return all resources of resource_type from Boto3.

        Arguments:
            service_name (str): The name of the service to get resource for (e.g. ``'ec2'``)
            resource_type (str): The type of resource to get resources of (e.g. ``'instance'``)
            region_name (str): The region to get resources of (e.g. ``'eu-west-1'``)
            **kwargs: Additional keyword arguments will be passed down to the Boto3 client.
        """
        service_map = self.service_maps.get_service_mapping(service_name=service_name)
        region_name = region_name or self.region_name
        if service_map.is_global_service and service_map.global_service_region != region_name:
            logger.info(
                "Skipping %s as it does not have resources in %s",
                service_name,
                region_name,
            )
            return
        boto3_service = self.boto3_getter.custom_resource_definitions.resource(service_name, **kwargs)
        boto3_resource_collection = get_resource_collection_by_resource_type(boto3_service, resource_type)

        resources = get_resource_from_collection(
            boto3_service=boto3_service,
            boto3_resource_collection=boto3_resource_collection,
        )

        for resource in resources:
            urn = self.boto3_getter.get_resource_urn(resource, region_name)
            logger.debug("Found %s", urn)
            yield CloudWandererResource(
                urn=urn,
                resource_data=_prepare_boto3_resource_data(resource),
                secondary_attributes=list(self.boto3_getter.get_secondary_attributes(resource)),
            )
            for subresource in self.boto3_getter.get_subresources(resource):
                yield CloudWandererResource(
                    urn=self.boto3_getter.get_resource_urn(subresource, region_name),
                    resource_data=_prepare_boto3_resource_data(subresource),
                    secondary_attributes=list(self.boto3_getter.get_secondary_attributes(subresource)),
                )

    def cleanup_resources(
        self,
        storage_connector: BaseStorageConnector,
        urns_to_keep: List[URN] = None,
        regions: List[str] = None,
        service_names: List[str] = None,
        resource_types: List[str] = None,
        **kwargs,
    ) -> None:
        """Delete records as appropriate from a storage connector based on the supplied arguments.

        All arguments except ``storage_connector`` are optional.

        Arguments:
            storage_connector (BaseStorageConnector):
                The storage connector to delete the records from.
            urns_to_keep (List[URN]):
                A list of URNs which should not be removed from the storage_connector
            regions(list):
                The name of the region to get resources from (defaults to session default if not specified)
            service_names (str):
                The names of the services to write resources for (e.g. ``['ec2']``)
            resource_types (list):
                A list of resource types to include (e.g. ``['instance']``)
            **kwargs:
                All additional keyword arguments will be passed down to the Boto3 client calls.
        """
        regions = regions or self.enabled_regions
        boto3_services = self.boto3_getter.get_resource_services_from_names(service_names, **kwargs)
        for region_name in regions:
            for boto3_service in boto3_services:
                resource_types = self.boto3_getter.custom_resource_definitions.get_valid_resource_types(
                    service_name=boto3_service.meta.service_name,
                    resource_types=resource_types,
                )
                for resource_type in resource_types:
                    self._clean_resources_in_region(
                        storage_connector=storage_connector,
                        service_name=boto3_service.meta.service_name,
                        resource_type=resource_type,
                        region_name=region_name,
                        current_urns=urns_to_keep,
                    )

    def _clean_resources_in_region(
        self,
        storage_connector: BaseStorageConnector,
        service_name: str,
        resource_type: str,
        region_name: str,
        current_urns: List[URN],
    ) -> None:
        """Remove all resources of this type in this region which no longer exist.

        Arguments:
            storage_connector (BaseStorageConnector):
                The storage connector that resources will be deleted from.
            service_name (str):
                The name of the service to write resources for (e.g. ``'ec2'``)
            resource_type (str):
                The name of the type of the resource to write (e.g. ``'instance'``)
            region_name (str):
                The name of the region to get resources from
                (defaults to session default if not specified)
            current_urns (List[URN]):
                A list of URNs which are still current and should not be deleted.
        """
        regions_returned = self.service_maps.resource_regions_returned_from_api_region(
            service_name=service_name, region_name=region_name, enabled_regions=self.enabled_regions
        )
        for region_name in regions_returned:
            logger.info("---> Deleting %s %s from %s", service_name, resource_type, region_name)
            storage_connector.delete_resource_of_type_in_account_region(
                service=service_name,
                resource_type=resource_type,
                account_id=self.account_id,
                region=region_name,
                urns_to_keep=current_urns,
            )