"""Boto3 Loaders.

Loaders and data classes to load custom CloudWanderer Boto3 service definitions and merge them with the boto3
provided ones. This allows cloudwanderer to extend Boto3 to support AWS resources that it does not support natively.
We can do this quite easily because CloudWanderer only needs a fraction of the functionality that native
Boto3 resources provide (i.e. the description of the resources).
"""

import json
import logging
import os
import pathlib
from collections import OrderedDict
from pathlib import Path
from typing import List, Optional

import boto3
import botocore
import jmespath  # type: ignore
from botocore.exceptions import DataNotFoundError, UnknownServiceError  # type: ignore
from botocore.loaders import Loader

from ..cache_helpers import memoized_method
from ..exceptions import MalformedFileError, UnsupportedServiceError

logger = logging.getLogger(__name__)


class CustomServiceLoader:
    """A class to load custom services."""

    def __init__(self, definition_path: str = "resource_definitions") -> None:
        self.service_definitions_path = os.path.join(pathlib.Path(__file__).parent.absolute(), definition_path)

    @memoized_method()
    def get_service_definition(self, service_name: str, type_name: str, api_version: str) -> dict:
        path = Path(service_name) / Path(api_version) / Path(f"{type_name}.json")
        full_path = self.service_definitions_path / path
        logger.debug("CustomServiceLoader get_service_definition loaded path %s", full_path)
        try:
            with open(full_path, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            raise UnsupportedServiceError(f"{service_name} does not exist as a custom CloudWanderer service.")
        except json.decoder.JSONDecodeError as ex:
            raise MalformedFileError(f"{service_name} has an invalid file at {full_path}.") from ex

    def list_api_versions(self, service_name: str, type_name: str) -> List[str]:
        path = self.service_definitions_path / Path(service_name)
        try:
            api_versions = [
                d
                for d in os.listdir(path)
                if os.path.isdir(os.path.join(path, d)) and os.path.isfile(os.path.join(path, d, f"{type_name}.json"))
            ]
        except FileNotFoundError:
            raise UnsupportedServiceError(f"{service_name} does not exist as a custom CloudWanderer service.")

        return sorted(api_versions)

    @property
    def available_services(self) -> List[str]:
        """Return a list of available snake_case service names."""
        possible_services = [
            d
            for d in os.listdir(self.service_definitions_path)
            if os.path.isdir(os.path.join(self.service_definitions_path, d))
        ]
        return sorted(possible_services)


class MergedServiceLoader(Loader):
    """A class to merge the services from a custom service loader with those of Boto3."""

    def __init__(self) -> None:
        self.custom_service_loader = CustomServiceLoader()
        botocore_session = botocore.session.get_session()
        self.botocore_loader = botocore_session.get_component("data_loader")
        boto3_data_path = os.path.join(os.path.dirname(boto3.__file__), "data")
        self.botocore_loader.search_paths.append(boto3_data_path)

    def list_available_services(self, type_name: str = "resources-1") -> List[str]:
        _ = type_name
        """Return a list of service names that can be loaded."""
        return list(set(self.cloudwanderer_available_services + self.boto3_available_services))

    def determine_latest_version(self, service_name: str, type_name: str) -> str:
        return max(self.list_api_versions(service_name, type_name))

    @property
    def cloudwanderer_available_services(self) -> List[str]:
        """Return a list of services defined by CloudWanderer."""
        return self.custom_service_loader.available_services

    @property
    def boto3_available_services(self) -> List[str]:
        """Return a list of services defined by Boto3."""
        return self.botocore_loader.list_available_services(type_name="resources-1")

    def list_api_versions(self, service_name: str, type_name: str) -> List[str]:
        logger.debug("list_api_version, service_name: %s, type_name: %s", service_name, type_name)
        try:
            boto3_api_versions = self.botocore_loader.list_api_versions(service_name=service_name, type_name=type_name)
        except DataNotFoundError:
            boto3_api_versions = []
        try:
            custom_api_versions = self.custom_service_loader.list_api_versions(
                service_name=service_name, type_name=type_name
            )
        except UnsupportedServiceError:
            custom_api_versions = []

        if not boto3_api_versions and not custom_api_versions:
            raise UnsupportedServiceError(
                f"{service_name} is not supported by either Boto3 or CloudWanderer's "
                f"custom services for {type_name}.json"
            )

        if custom_api_versions:
            return custom_api_versions

        return boto3_api_versions

    @memoized_method()
    def load_service_model(self, service_name: str, type_name: str, api_version: Optional[str] = None) -> OrderedDict:
        logger.debug(
            "botocore_loaders load_service_model service_name %s, type_name %s, api_version %s",
            service_name,
            type_name,
            api_version,
        )
        if not api_version:
            api_version = self.determine_latest_version(service_name=service_name, type_name=type_name)
        try:
            boto3_definition = self.botocore_loader.load_service_model(
                service_name, type_name=type_name, api_version=api_version
            )
        except UnknownServiceError:
            boto3_definition = OrderedDict()

        custom_service_definition = self._get_custom_service_definition(
            service_name, type_name=type_name, api_version=api_version
        )

        if not boto3_definition and not custom_service_definition:
            raise UnsupportedServiceError(
                f"{service_name} is not supported by either Boto3 or CloudWanderer's custom "
                f"services for api_version {api_version}, type {type_name}"
            )
        merged_dict = OrderedDict(
            {
                "service": OrderedDict(
                    {
                        **custom_service_definition.get("service", {}),
                        **{
                            "hasMany": OrderedDict(
                                {
                                    **(jmespath.search("service.hasMany", boto3_definition) or OrderedDict({})),
                                    **(
                                        jmespath.search("service.hasMany", custom_service_definition) or OrderedDict({})
                                    ),
                                }
                            )
                        },
                    }
                ),
                "resources": OrderedDict(
                    {
                        **boto3_definition.get("resources", OrderedDict({})),
                        **custom_service_definition.get("resources", OrderedDict({})),
                    }
                ),
            }
        )
        return merged_dict

    def _get_custom_service_definition(self, service_name: str, type_name: str, api_version: str) -> dict:
        """Get the custom CloudWanderer definition for service_name so we can merge it with Boto3's.

        Arguments:
            service_name: The PascalCase name of the service to get the definition of.
            api_version: The version of the api to get the definition of.
            type_name: The type of definition to get.
        """
        if not api_version:
            api_version = self.determine_latest_version(service_name=service_name, type_name=type_name)
        try:
            return self.custom_service_loader.get_service_definition(
                service_name=service_name, type_name=type_name, api_version=api_version
            )
        except UnsupportedServiceError:
            return {}
