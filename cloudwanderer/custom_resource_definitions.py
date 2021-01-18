"""Classes for handling custom boto3 :class:`~boto3.resources.base.ServiceResource`.

Custom resources use the :class:`boto3.resources.base.ServiceResource` model to extend support to
AWS resources that boto3 does not support natively. We can do this quite easily because CloudWanderer only needs
a fraction of the functionality that native boto3 resources provide (i.e. the description of the resources).
"""
from typing import List
import os
import json
import pathlib
import botocore
import boto3
from botocore.exceptions import UnknownServiceError
from boto3.resources.model import ResourceModel
from boto3.resources.factory import ResourceFactory
from boto3.utils import ServiceContext


# Default resource definitions, loaded when needed
DEFAULT_RESOURCE_DEFINITIONS = None


class CustomResourceFactory():
    """Factory class for generating custom boto3 Resource objects.

    Arguments:
        boto3_session (boto3.session.Session): The :class:`boto3.session.Session` object to use for any queries.
    """

    def __init__(self, boto3_session: boto3.session.Session) -> None:
        """Initialise the ResourceFactory."""
        self.boto3_session = boto3_session or boto3.Session()
        self.emitter = self.boto3_session.events
        self.factory = ResourceFactory(self.emitter)

    def load(self, service_name: str, resource_definitions: dict = None,
             service_definition: dict = None) -> ResourceModel:
        """Load the specified resource definition dictionaries into a Resource object.

        Arguments:
            service_name (str):
                The name of the service to load (e.g. ``'ec2'``)
            resource_definitions (list):
                A list of dicts describing the resource definitions.
                This is the ``'resources'`` key in each ``resource_definition`` json.
            service_definition (dict):
                A dict describing the service definition.
                This is the ``'service'`` key in each ``resource_definition`` json.
        """
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

    def _get_service_model(self, service_name: str) -> boto3.resources.base.ServiceResource:
        client = self.boto3_session.client(service_name)
        return client.meta.service_model


class CustomResourceDefinitions():
    """Custom Resource Definitions.

    Allows us to specify :class:`~boto3.resources.base.ServiceResource` definitions
    where they are not supplied by boto3.
    """

    def __init__(self, boto3_session: boto3.session.Session = None,
                 definition_path: str = 'resource_definitions') -> None:
        """Initialise the CustomResourceDefinition.

        Arguments:
        boto3_session (boto3.session.Session): The :class:`boto3.session.Session` object to use for any queries.
        definition_path (str): The path to the ``*.json`` files containing the custom resource definitions.
        """
        self.service_definitions_path = os.path.join(
            pathlib.Path(__file__).parent.absolute(),
            definition_path
        )
        self.boto3_session = boto3_session or boto3.session.Session()
        self.factory = CustomResourceFactory(boto3_session=self.boto3_session)
        self._custom_resource_definitions = None
        self._custom_resources = None
        self._service_definitions = None
        self.botocore_session = botocore.session.get_session()
        self._setup_boto3_loader()
        self._populate_service_definitions()
        self._populate_resource_definitions()

    def _setup_boto3_loader(self) -> None:
        self._boto3_loader = self.botocore_session.get_component('data_loader')
        self._boto3_loader.search_paths.append(os.path.join(os.path.dirname(boto3.__file__), 'data'))

    def _populate_service_definitions(self) -> None:
        custom_definitions = [
            file_name.replace('.json', '')
            for file_name in os.listdir(self.service_definitions_path)
            if os.path.isfile(os.path.join(self.service_definitions_path, file_name))
        ]
        self._service_definitions = set(custom_definitions + self.boto3_session.get_available_resources())

    def _populate_resource_definitions(self) -> None:
        """Populate resource definitions."""
        self._custom_resource_definitions = {}
        for service_name in self._service_definitions:
            service_definition = self._load_service_definition(service_name)
            self._custom_resource_definitions[service_name] = service_definition

    def _load_service_definition(self, service_name: str) -> dict:
        boto3_definition = self._get_boto3_definition(service_name)
        try:
            with open(os.path.join(self.service_definitions_path, f"{service_name}.json")) as definition_path:
                cloudwanderer_definition = json.load(definition_path)
        except FileNotFoundError:
            cloudwanderer_definition = {'service': {}, 'resources': {}}
        return {
            'service': {
                **boto3_definition['service'],
                **cloudwanderer_definition['service']
            },
            'resources': {
                **boto3_definition['resources'],
                **cloudwanderer_definition['resources']
            }
        }

    def _get_boto3_definition(self, service_name: str) -> dict:
        """Get the boto3 definition for service_name so we can build on top of it."""
        try:
            return self._boto3_loader.load_service_model(service_name, 'resources-1', None)
        except UnknownServiceError:
            return {
                'service': {},
                'resources': {}
            }

    @property
    def definitions(self) -> List[ResourceModel]:
        """Return our custom resource definitions."""
        return self._custom_resource_definitions

    @property
    def services(self) -> List[ResourceModel]:
        """Return our custom service resources."""
        if self._custom_resources is None:
            self._custom_resources = {}
            for service_name, service_definition in self.definitions.items():
                self._custom_resources[service_name] = self.factory.load(
                    service_name=service_name,
                    service_definition=service_definition['service'],
                    resource_definitions=service_definition['resources'],
                )
        return self._custom_resources

    def resource(self, service_name: str, **kwargs) -> ResourceModel:
        """Instantiate and return the boto3 Resource object for our custom resource definition."""
        if service_name in self.services:
            return self.services[service_name](
                client=self.boto3_session.client(service_name, **kwargs))
        return None


def _get_resource_definitions() -> CustomResourceDefinitions:
    """Return a default set of resource definitions."""
    global DEFAULT_RESOURCE_DEFINITIONS

    if DEFAULT_RESOURCE_DEFINITIONS is None:
        DEFAULT_RESOURCE_DEFINITIONS = CustomResourceDefinitions()
    return DEFAULT_RESOURCE_DEFINITIONS
