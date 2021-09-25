from .boto3_loaders import ServiceMappingLoader
from boto3.resources.base import ResourceMeta, ServiceResource
from boto3.resources.factory import ResourceFactory
import logging
from ..exceptions import UnsupportedResourceTypeError

from boto3.resources.model import ResourceModel
from boto3.utils import ServiceContext
from botocore import xform_name

logger = logging.getLogger(__name__)


class CloudWandererResourceFactory(ResourceFactory):
    def __init__(self, emitter, service_mapping_loader: ServiceMappingLoader):
        super().__init__(emitter=emitter)
        self.service_mapping_loader = service_mapping_loader

    def load_from_definition(self, resource_name, single_resource_json_definition, service_context):

        logger.debug("Loading %s:%s", service_context.service_name, resource_name)

        # Using the loaded JSON create a ResourceModel object.
        resource_model = ResourceModel(
            resource_name, single_resource_json_definition, service_context.resource_json_definitions
        )

        # Do some renaming of the shape if there was a naming collision
        # that needed to be accounted for.
        shape = None
        if resource_model.shape:
            shape = service_context.service_model.shape_for(resource_model.shape)
        resource_model.load_rename_map(shape)

        # Set some basic info
        meta = ResourceMeta(service_context.service_name, resource_model=resource_model)
        attrs = {
            "meta": meta,
        }

        # Create and load all of attributes of the resource class based
        # on the models.

        # Identifiers
        self._load_identifiers(attrs=attrs, meta=meta, resource_name=resource_name, resource_model=resource_model)

        # Load/Reload actions
        self._load_actions(
            attrs=attrs, resource_name=resource_name, resource_model=resource_model, service_context=service_context
        )

        # Attributes that get auto-loaded
        self._load_attributes(
            attrs=attrs,
            meta=meta,
            resource_name=resource_name,
            resource_model=resource_model,
            service_context=service_context,
        )

        # Collections and their corresponding methods
        self._load_collections(attrs=attrs, resource_model=resource_model, service_context=service_context)

        # References and Subresources
        self._load_has_relations(
            attrs=attrs, resource_name=resource_name, resource_model=resource_model, service_context=service_context
        )

        # Waiter resource actions
        self._load_waiters(
            attrs=attrs, resource_name=resource_name, resource_model=resource_model, service_context=service_context
        )

        # CloudWanderer resource methods
        self._load_cloudwanderer_methods(
            attrs=attrs, resource_name=resource_name, resource_model=resource_model, service_context=service_context
        )

        # CloudWanderer resource properties
        self._load_cloudwanderer_properties(
            attrs=attrs, resource_name=resource_name, resource_model=resource_model, service_context=service_context
        )

        # Create the name based on the requested service and resource
        cls_name = resource_name
        if service_context.service_name == resource_name:
            cls_name = "ServiceResource"
        cls_name = service_context.service_name + "." + cls_name

        base_classes = [ServiceResource]
        if self._emitter is not None:
            self._emitter.emit(
                "creating-resource-class.%s" % cls_name,
                class_attributes=attrs,
                base_classes=base_classes,
                service_context=service_context,
            )
        return type(str(cls_name), tuple(base_classes), attrs)

    def _load_cloudwanderer_methods(self, attrs, resource_name, resource_model, service_context) -> None:
        if service_context.service_name == xform_name(resource_name):
            # This should only exist on Services, not on Resources
            attrs["get_resource_discovery_actions"] = self._create_get_resource_discovery_actions()

    def _create_get_resource_discovery_actions(self):
        def get_resource_discovery_actions(self, resource_types, regions):
            logger.debug("getting resource types for %s", self.service_name)
            action_sets = []
            if resource_types:
                logger.debug("Validating if %s are valid resource types in %s", resource_types, self.resource_types)
                service_resource_types = list(set(resource_types) & set(self.resource_types))
            else:
                service_resource_types = self.resource_types

            for resource_type in service_resource_types:
                for region_name in regions:
                    service_resource = f"{self.service_name}:{resource_type}"
                    logger.debug("Getting actions for %s %s in %s", service_resource, resource_type, region_name)
                    resource_map = self.service_map.get_resource_map(resource_type)
                    if not resource_map:
                        raise UnsupportedResourceTypeError("No %s resource type found", service_resource)
                        continue
                    actions = resource_map.get_and_cleanup_actions(region_name)
                    if not actions:
                        continue
                    resource_actions = actions.inflate_actions(regions)
                    for subresource_type in resource_map.subresource_types:
                        subresource_map = self.service_map.get_resource_map(subresource_type)
                        actions = subresource_map.get_and_cleanup_actions(region_name)
                        resource_actions += actions.inflate_actions(regions)
                    action_sets.append(resource_actions)
            return action_sets

        return get_resource_discovery_actions

    def _load_cloudwanderer_properties(
        self, attrs, resource_name, resource_model, service_context: ServiceContext
    ) -> None:
        attrs["service_name"] = service_context.service_name
        attrs["service_map"] = self.service_mapping_loader.get_service_mapping(
            service_name=service_context.service_name
        )
        if resource_name == service_context.service_name:

            @property
            def resource_types(self):
                resource_types = [
                    xform_name(collection.resource.type) for collection in self.meta.resource_model.collections
                ]

                return resource_types

            attrs["resource_types"] = resource_types
        else:
            attrs["resource_type"] = xform_name(resource_name)
