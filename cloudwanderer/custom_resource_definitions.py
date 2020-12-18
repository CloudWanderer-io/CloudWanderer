"""Classes for handling custom boto3 Resources."""
import os
import json
import pathlib
from boto3.resources.factory import ResourceFactory
from boto3.utils import ServiceContext
import boto3


class CustomResourceFactory():
    """Factory class for generating custom boto3 Resource objects."""

    def __init__(self, boto3_session):
        """Initialise the ResourceFactory."""
        self.boto3_session = boto3_session or boto3.Session()
        self.emitter = self.boto3_session.events
        self.factory = ResourceFactory(self.emitter)

    def load(self, service_name, resource_definitions=None, service_definition=None):
        """Load the specified resource definition dictionaries into a Resource object."""
        service_context = ServiceContext(
            service_name=service_name,
            resource_json_definitions=resource_definitions,
            service_model=self._get_service_model(service_name),
            service_waiter_model=None
        )

        return self.factory.load_from_definition(
            resource_name=service_name,
            single_resource_json_definition=service_definition,
            service_context=service_context
        )

    def _get_shape(self, service, shape_name):
        service_model = self._get_service_model()
        return service_model.shape_for(shape_name)

    def _get_service_model(self, service):
        client = self.boto3_session.client(service)
        return client.meta.service_model


class CustomResourceDefinitions():
    """Custom Resource Definitions.

    Allows us to specify resource definitions where they are not supplied by boto3.
    """

    def __init__(self, boto3_session=None, definition_path='resource_definitions'):
        """Initialise the CustomResourceDefinition."""
        self.service_definitions_path = os.path.join(
            pathlib.Path(__file__).parent.absolute(),
            definition_path
        )
        self.boto3_session = boto3_session or boto3.session.Session()
        self.factory = CustomResourceFactory(boto3_session=self.boto3_session)

    def load_custom_resource_definitions(self):
        """Return our custom resource definitions."""
        services = {}
        for service_name in self._list_service_definitions():
            service_definition = self._load_service_definition(service_name)
            services[service_name] = self.factory.load(
                service_name=service_name,
                service_definition=service_definition['service'],
                resource_definitions=service_definition['resources'],
            )(client=self.boto3_session.client(service_name))
        return services

    def _load_service_definition(self, service_name):
        with open(os.path.join(self.service_definitions_path, f"{service_name}.json")) as definition_path:
            return json.load(definition_path)

    def _list_service_definitions(self):
        return [
            file_name.replace('.json', '')
            for file_name in os.listdir(self.service_definitions_path)
            if os.path.isfile(os.path.join(self.service_definitions_path, file_name))
        ]
