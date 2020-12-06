import os
import json
import pathlib
from collections import defaultdict
import botocore
from boto3.resources.collection import (
    CollectionFactory,
    CollectionManager,
    ResourceCollection
)
from boto3.resources.factory import ResourceFactory
from boto3.utils import ServiceContext
from botocore.model import ServiceModel
import boto3


class BaseTestResourceFactory():
    def __init__(self):
        self.emitter = boto3.Session().events
        self.factory = ResourceFactory(self.emitter)
        self.botocore_session = botocore.session.get_session()

    def load(self, service_name, resource_definition=None,
             service_resource_definitions=None):
        service_context = ServiceContext(
            service_name=service_name,
            resource_json_definitions=service_resource_definitions,
            service_model=self._get_service_model(service_name),
            service_waiter_model=None
        )

        return self.factory.load_from_definition(
            resource_name=service_name,
            single_resource_json_definition=resource_definition,
            service_context=service_context
        )

    def _get_shape(self, service, shape_name):
        service_model = self._get_service_model()
        return service_model.shape_for(shape_name)

    def _get_service_model(self, service):
        client = self.botocore_session.create_client(service)
        return client.meta.service_model


class CustomResourceDefinitions():

    def __init__(self):
        self.service_definitions_path = os.path.join(
            pathlib.Path(__file__).parent.absolute(),
            'service_definitions'
        )
        self.factory = BaseTestResourceFactory()

    def load_custom_resource_definitions(self):
        services = {}
        for service_name in self._list_service_definitions():
            service_definition = self._load_service_definition(service_name)
            # for resource_name, resource_definition in service_definition['resources'].items():
            services[service_name] = self.factory.load(
                service_name=service_name,
                resource_definition=service_definition['service'],
                service_resource_definitions=service_definition['resources'],
            )()
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
