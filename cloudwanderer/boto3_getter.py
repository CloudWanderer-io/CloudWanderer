"""Boto3 Getter provides easy abstraction from boto3's internals to make boto3_interface easier to work with."""

import boto3
from boto3.resources.model import ResourceModel
from botocore import xform_name

from .aws_urn import AwsUrn
from .boto3_helpers import (
    Boto3CommonAttributesMixin,
    _clean_boto3_metadata,
    get_resource_from_collection,
    normalise_resource_id,
)
from .cloud_wanderer_resource import SecondaryAttribute
from .custom_resource_definitions import CustomResourceDefinitions, get_resource_collections
from .service_mappings import GlobalServiceResourceMappingNotFound, ServiceMappingCollection


class Boto3Getter(Boto3CommonAttributesMixin):
    """Gets Boto3 resources, subresources, and secondary attributes."""

    def __init__(self, boto3_session: boto3.session.Session, service_maps: ServiceMappingCollection) -> None:
        self.boto3_session = boto3_session
        self.service_maps = service_maps
        self.custom_resource_definitions = CustomResourceDefinitions(boto3_session=boto3_session)

    def get_subresources(
        self, boto3_resource: boto3.resources.base.ServiceResource
    ) -> boto3.resources.base.ServiceResource:
        """Return all subresources for this resource.

        Subresources and collections on custom service resources may be subresources we want to collect if
        they are specified in our service mapping.

        Arguments:
            boto3_resource (boto3.resources.base.ServiceResource): The :class:`boto3.resources.base.ServiceResource`
                to get secondary attributes from
        """
        yield from self.get_child_resources(boto3_resource=boto3_resource, resource_type="resource")

    def get_secondary_attributes(self, boto3_resource: boto3.resources.base.ServiceResource) -> SecondaryAttribute:
        """Return all secondary attributes resources for this resource.

        Subresources and collections on custom service resources may be secondary attribute definitions if
        specified in our service mapping.

        Arguments:
            boto3_resource (boto3.resources.base.ServiceResource): The :class:`boto3.resources.base.ServiceResource`
                to get secondary attributes from
        """
        secondary_attributes = self.get_child_resources(
            boto3_resource=boto3_resource, resource_type="secondaryAttribute"
        )
        for secondary_attribute in secondary_attributes:
            yield SecondaryAttribute(
                name=xform_name(secondary_attribute.meta.resource_model.name),
                **_clean_boto3_metadata(secondary_attribute.meta.data)
            )

    def get_child_resources(
        self, boto3_resource: boto3.resources.base.ServiceResource, resource_type: str
    ) -> boto3.resources.base.ServiceResource:
        """Return all child resources of resource_type for this resource.

        This method contextualises the ``has`` and ``hasMany`` relationships that Boto3 uses to specify subresources.
        If they are found in the service map, then they are subresources or secondary attributes that CloudWanderer
        needs to record into storage. Anything that is not in the service map will have been provided as a definition
        by Boto3 itself and probably represents a relationship between base resources (i.e. resources that have ARNs)
        and therefore does not qualify as a subresource in the CloudWanderer sense of the word. CloudWanderer is only
        interested in capturing subresources which depend on their parents for existence (i.e. do not have their own
        ARN). Secondary attributes are not resources at all but merely resource-like representations of additional
        metadata about a resource which requires a secondary API call to fetch (e.g. AMI launchPermission).

        Arguments:
            boto3_resource (boto3.resources.base.ServiceResource):
                The :class:`boto3.resources.base.ServiceResource`
                to get secondary attributes from
            resource_type (str):
                The resource types to return (either 'secondaryAttribute' or 'resource')
        """
        service_mapping = self.service_maps.get_service_mapping(boto3_resource.meta.service_name)

        for subresource in boto3_resource.meta.resource_model.subresources:
            try:
                resource_mapping = service_mapping.get_resource_mapping(subresource.name)
            except GlobalServiceResourceMappingNotFound:
                continue

            if resource_mapping.resource_type != resource_type:
                continue
            subresource = getattr(boto3_resource, subresource.name)()
            subresource.load()
            yield subresource

        for child_resource_collection in get_resource_collections(boto3_resource):
            try:
                resource_mapping = service_mapping.get_resource_mapping(child_resource_collection.resource.model.name)
            except GlobalServiceResourceMappingNotFound:
                continue
            if resource_mapping.resource_type != resource_type:
                continue
            child_resources = get_resource_from_collection(
                boto3_service=boto3_resource, boto3_resource_collection=child_resource_collection
            )
            for resource in child_resources:
                resource.load()
                yield resource

    def get_child_resource_definitions(
        self, service_name: str, boto3_resource_model: boto3.resources.model.ResourceModel, resource_type: str
    ) -> boto3.resources.model.ResourceModel:
        """Return all child resource models for this resource.

        This method mirrors get_child_resources but instead of returning the CloudWandererResource object it
        returns the resource definition. This method is used to generate documentation in the Sphinx extension.

        Arguments:
            service_name (str):
                The name of the service this model resides in (e.g. ``'ec2'``)
            boto3_resource_model (boto3.resources.model.ResourceModel):
                The :class:`boto3.resources.model.ResourceModel` to get secondary attributes models from
            resource_type (str):
                The resource types to return (either 'secondaryAttribute' or 'resource')
        """
        service_mapping = self.service_maps.get_service_mapping(service_name)

        for subresource in boto3_resource_model.subresources:
            try:
                resource_mapping = service_mapping.get_resource_mapping(subresource.name)
            except GlobalServiceResourceMappingNotFound:
                continue
            if resource_mapping.resource_type != resource_type:
                continue
            yield subresource

        for secondary_attribute_collection in boto3_resource_model.collections:
            try:
                resource_mapping = service_mapping.get_resource_mapping(
                    secondary_attribute_collection.resource.model.name
                )
            except GlobalServiceResourceMappingNotFound:
                continue
            if resource_mapping.resource_type != resource_type:
                continue
            yield secondary_attribute_collection

    def get_resource_urn(self, resource: ResourceModel, region_name: str) -> "AwsUrn":
        """Return an AwsUrn from a Boto3 Resource.

        Arguments:
            resource (ResourceModel):
                The Boto3 resource for which to generate an URN.
            region_name (str):
                The region of the API the resource was discovered in. This may or may not reflect the region
                the resource exists in in some cases (e.g. S3 Buckets).
        """
        service_map = self.service_maps.get_service_mapping(resource.meta.service_name)
        return AwsUrn(
            account_id=self.account_id,
            region=service_map.get_resource_region(resource, region_name),
            service=resource.meta.service_name,
            resource_type=xform_name(resource.meta.resource_model.name),
            resource_id=normalise_resource_id(resource=resource),
        )
