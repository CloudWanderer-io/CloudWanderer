import os
import pathlib
from collections import defaultdict
from functools import lru_cache

import boto3
import botocore
import docutils
import sphinx
from docutils import nodes
from docutils.frontend import OptionParser
from sphinx.domains import Domain
from sphinx.util.docutils import SphinxDirective

import cloudwanderer
from cloudwanderer.boto3_loaders import MergedServiceLoader
from cloudwanderer.boto3_services import CloudWandererBoto3Resource, CloudWandererBoto3Service

SECONDARY_ATTR_TEMPLATE = """
.. py:class:: {service_name}.{parent_resource_name}.{resource_name}

    A secondary attribute for the :class:`{service_name}.{parent_resource_name}`
    resource type.

    **Example:**

    .. code-block ::

        resources = storage_connector.read_resources(
            service="{service_name}",
            resource_type="{parent_resource_name}")
        for resource in resources:
            resource.get_secondary_attribute(name="{resource_name}")

"""

RESOURCE_TEMPLATE = """
.. py:class:: {class_name}

    {description}

    **Example:**

    .. code-block ::

        resources = storage_connector.read_resources(
            service="{service_name}",
            resource_type="{resource_name}")
        for resource in resources:
            resource.load()
            print(resource.urn)
"""

ATTRIBUTES_TEMPLATE = """
    .. py:attribute:: {attribute_name}

         {documentation}

"""


def _generate_mock_session(region: str = "eu-west-2") -> boto3.session.Session:
    return boto3.session.Session(region_name=region, aws_access_key_id="1111", aws_secret_access_key="1111")


class SummarisedResources:
    def __init__(self) -> None:
        self.merged_loader = MergedServiceLoader()
        self.services = cloudwanderer.boto3_services.Boto3Services(
            boto3_session=_generate_mock_session(), account_id="111111111111"
        )
        cloudwanderer.boto3_services.Boto3Services = ["us-east-1"]

    @property
    @lru_cache()
    def cloudwanderer_resources(self) -> list:
        service_summary = defaultdict(list)

        for service_name in sorted(self.merged_loader.cloudwanderer_available_services):
            service = self.services.get_service(service_name)
            service_model = service.boto3_service.meta.client.meta.service_model
            service_id = service_model.metadata["serviceId"]
            service_definition = self.merged_loader._get_custom_service_definition(service_name)
            resource_list = nodes.bullet_list()
            for collection_name in service_definition["service"].get("hasMany", {}):
                resource_name = collection_name
                if collection_name not in self.boto3_resources.get(service_name, []):
                    resource_list += nodes.Text(resource_name)
            if resource_list.children:
                service_summary[service_id] = resource_list
        return service_summary

    @property
    @lru_cache()
    def boto3_resources(self) -> list:
        services_summary = defaultdict(list)
        for service_name in self.merged_loader.boto3_available_services:
            service = self.services.get_service(service_name)
            service_model = service.boto3_service.meta.client.meta.service_model
            service_id = service_model.metadata["serviceId"]
            service_definition = self.merged_loader._get_boto3_definition(service_name)
            for collection_name in service_definition["service"]["hasMany"]:
                services_summary[service_id].append(collection_name)
        return services_summary


class CloudWandererResourcesDirective(SphinxDirective):
    """A custom directive that lists CloudWanderers added resources."""

    has_content = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.summarised_resources = SummarisedResources()

    def run(self) -> list:
        targetid = "cloudwanderer-%d" % self.env.new_serialno("cloudwanderer")
        targetnode = nodes.target("", "", ids=[targetid])

        return [targetnode, self.get_cloudwanderer_resources()]

    def get_cloudwanderer_resources(self) -> list:
        service_list = nodes.bullet_list()

        for service_name, resource_types in sorted(self.summarised_resources.cloudwanderer_resources.items()):
            resource_list = nodes.bullet_list()
            for resource_type in resource_types:
                resource_list += nodes.list_item("", nodes.Text(resource_type))
            if resource_list.children:
                service_list += nodes.list_item("", nodes.Text(service_name), resource_list)
        return service_list


class Boto3ResourcesDirective(SphinxDirective):
    """A custom directive that lists Boot3 default resources."""

    has_content = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.summarised_resources = SummarisedResources()

    def run(self) -> list:
        targetid = "cloudwanderer-%d" % self.env.new_serialno("cloudwanderer")
        targetnode = nodes.target("", "", ids=[targetid])

        return [targetnode, self.get_boto3_resources()]

    def get_boto3_resources(self) -> list:
        service_list = nodes.bullet_list()

        for service_name, resource_types in sorted(self.summarised_resources.boto3_resources.items()):
            resource_list = nodes.bullet_list()
            for resource_type in resource_types:
                resource_list += nodes.list_item("", nodes.Text(resource_type))
            if resource_list.children:
                service_list += nodes.list_item("", nodes.Text(service_name), resource_list)
        return service_list


class CloudWandererSecondaryAttributesDirective(SphinxDirective):
    """A custom directive that lists CloudWanderers secondary attribute definitions."""

    has_content = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.services = cloudwanderer.boto3_services.Boto3Services(
            boto3_session=_generate_mock_session(), account_id="111111111111"
        )

    def run(self) -> list:
        targetid = "cloudwanderer-%d" % self.env.new_serialno("cloudwanderer")
        targetnode = nodes.target("", "", ids=[targetid])

        return [targetnode, self.get_cloudwanderer_secondary_attributes()]

    def get_cloudwanderer_secondary_attributes(self) -> list:
        service_list = nodes.bullet_list()

        for service_name in sorted(self.services.available_services):
            service = self.services.get_service(service_name)
            resources = sorted(service.resource_summary)
            resource_list = nodes.bullet_list()
            for resource in resources:
                for secondary_attribute in resource.secondary_attribute_names:
                    resource_list += nodes.list_item("", nodes.Text(secondary_attribute))

            if resource_list.children:
                service_list += nodes.list_item("", nodes.Text(service_name), resource_list)
        return service_list


class CloudWandererResourceDefinitionsDirective(SphinxDirective):
    """A custom directive that describes CloudWanderers respources."""

    has_content = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.cw = GetCwServices()
        self.relative_path = "resource_properties"

    def run(self) -> list:
        services_section = nodes.section(ids=["cloudwanderer_resources"])
        services_section += nodes.title("", "Available Services")
        rst_section = ".. toctree::\n"
        rst_section += "   :maxdepth: 2\n\n"
        for service_name in sorted(self.cw.get_cloudwanderer_services()):
            rst_section += f"   {os.path.join(self.relative_path, service_name)}.rst\n"
        services_section += self.parse_rst(rst_section).children
        targetid = "cloudwanderer-%d" % self.env.new_serialno("cloudwanderer")
        targetnode = nodes.target("", "", ids=[targetid])
        return [targetnode, services_section]

    def parse_rst(self, text: str) -> docutils.nodes.document:
        parser = sphinx.parsers.RSTParser()
        parser.set_application(self.env.app)

        settings = OptionParser(
            defaults=self.env.settings, components=(sphinx.parsers.RSTParser,), read_config_files=True
        ).get_default_values()
        document = docutils.utils.new_document("<rst-doc>", settings=settings)
        parser.parse(text, document)
        return document


class GetCwServices:
    def __init__(self) -> None:
        self.relative_path = "resource_properties"
        self.base_path = os.path.join(pathlib.Path(__file__).parent.absolute(), "..")
        self.services = cloudwanderer.boto3_services.Boto3Services(
            boto3_session=_generate_mock_session(), account_id="111111111111"
        )
        cloudwanderer.boto3_services.Boto3Services.enabled_regions = ["us-east-1"]
        self.loader = cloudwanderer.boto3_loaders.MergedServiceLoader()

    def get_cloudwanderer_services(self) -> list:
        yield from self.services.available_services

    def write_cloudwanderer_services(self) -> list:
        for service_name in self.services.available_services:
            service = self.services.get_service(service_name)
            service_model = service.boto3_service.meta.client.meta.service_model
            service_id = service_model.metadata["serviceId"]
            service_section = f"{service_id}\n{'-'*len(service_id)}\n\n"
            service_section += "\n\n".join(self.get_collections(service))
            if not os.path.exists(os.path.join(self.base_path, self.relative_path)):
                os.makedirs(os.path.join(self.base_path, self.relative_path))

            with open(os.path.join(self.base_path, self.relative_path, f"{service_name}.rst"), "w") as f:
                f.write(service_section)

    def parse_html(self, html: str) -> str:
        html_parser = botocore.docs.bcdoc.restdoc.ReSTDocument()
        html_parser.include_doc_string(html)
        return html_parser.getvalue().decode().replace("\n", "\n")

    def get_collections(self, service: cloudwanderer.boto3_services.CloudWandererBoto3Resource) -> list:

        result = []

        for resource_type in sorted(service.resource_types):
            resource = service._get_empty_resource(resource_type)
            result.append(self.generate_resource_section(service, resource, "{service_name}.{resource_name}"))
            result.append(self.get_subresources(service, resource))
            result.append(self.get_secondary_attributes(service, resource))
        return result

    def get_subresources(self, service: CloudWandererBoto3Service, resource: CloudWandererBoto3Resource) -> str:
        result = ""
        parent_resource_name = resource.resource_type

        for subresource_model in resource.subresource_models:
            subresource_type = botocore.xform_name(subresource_model.resource.model.name)
            subresource = service._get_empty_resource(subresource_type)
            result += self.generate_resource_section(
                service,
                subresource,
                f"{{service_name}}.{parent_resource_name}.{{resource_name}}",
                f"A subresource of :class:`{{service_name}}.{parent_resource_name}`.\n\n",
            )
        return result

    def get_secondary_attributes(self, service: CloudWandererBoto3Service, resource: CloudWandererBoto3Resource) -> str:
        result = ""
        service_name = service.name
        parent_resource_name = resource.resource_type
        for collection in resource.secondary_attribute_models:
            result += SECONDARY_ATTR_TEMPLATE.format(
                service_name=service_name,
                parent_resource_name=parent_resource_name,
                resource_name=botocore.xform_name(collection.name),
            )
        return result

    def generate_resource_section(
        self,
        service: CloudWandererBoto3Service,
        resource: CloudWandererBoto3Resource,
        name: str,
        description: str = "",
    ) -> str:
        service_model = service.boto3_service.meta.client.meta.service_model
        shape = service_model.shape_for(resource.boto3_resource.meta.resource_model.shape)
        attributes = sorted(resource.boto3_resource.meta.resource_model.get_attributes(shape).items())
        resource_section = RESOURCE_TEMPLATE.format(
            class_name=name.format(service_name=service.name, resource_name=resource.resource_type),
            service_name=service.name,
            resource_name=resource.resource_type,
            description=description.format(service_name=service.name, resource_name=resource.resource_type),
        )

        attributes_doc = ""
        for attribute_name, attribute in attributes:
            documentation = attribute[1].documentation
            documentation = self.parse_html(documentation).replace("\n", "")
            attributes_doc += ATTRIBUTES_TEMPLATE.format(attribute_name=attribute_name, documentation=documentation)
            resource_section += f"            print(resource.{attribute_name})\n"

        resource_section += "\n\n"
        resource_section += attributes_doc
        return resource_section


class SupportedResources(Domain):

    name = "supported-resources"
    label = "Cloudwanderer Supported Resources"
    directives = {
        "cloudwanderer-resources": CloudWandererResourcesDirective,
        "boto3-resources": Boto3ResourcesDirective,
        "cloudwanderer-secondary-attributes": CloudWandererSecondaryAttributesDirective,
        "resource-definitions": CloudWandererResourceDefinitionsDirective,
    }


def main(*args) -> None:
    d = GetCwServices()
    d.write_cloudwanderer_services()


def setup(app: object) -> dict:
    app.add_domain(SupportedResources)
    app.connect("builder-inited", main)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
