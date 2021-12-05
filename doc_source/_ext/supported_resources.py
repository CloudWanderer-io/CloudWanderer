import os
import pathlib
from collections import defaultdict
from functools import lru_cache
from typing import TYPE_CHECKING

import boto3
import botocore
import docutils
import sphinx
from docutils import nodes
from docutils.frontend import OptionParser
from graph_visualisation import GraphManager
from jinja2 import Template
from sphinx.domains import Domain
from sphinx.util.docutils import SphinxDirective

from cloudwanderer.aws_interface.boto3_loaders import MergedServiceLoader
from cloudwanderer.aws_interface.session import CloudWandererBoto3Session
from cloudwanderer.utils import snake_to_pascal

if TYPE_CHECKING:
    from cloudwanderer.aws_interface.stubs.resource import CloudWandererServiceResource


RESOURCE_TEMPLATE = Template(
    """

{{class_name}}
'''''''''''''''''''''''''''''''''''''''''

.. py:class:: {{class_name}}

    {{description}}

    {{image}}

    {{default_filters}}

    **Discovery Example:**

    .. doctest ::

        >>> from cloudwanderer import CloudWanderer, ServiceResourceType
        >>> from cloudwanderer.storage_connectors import GremlinStorageConnector
        >>> cloud_wanderer = CloudWanderer(storage_connectors=[
        ...        GremlinStorageConnector(
        ...          endpoint_url="ws://localhost:8182",
        ...        )
        ...    ])
        >>> cloud_wanderer.write_resources(
        ...     service_resource_types=[ServiceResourceType("{{service_name}}","{{resource_name}}")]
        ... )

    **OpenCypher Example:**

    How to query resources of this type using OpenCypher in Neptune.

    .. code-block::

        MATCH ({{resource_name}}:aws_{{service_name}}_{{resource_name}})
        RETURN *

    **Gremlin Example:**

    How to query resources of this type using Gremlin in Neptune/local Gremlin.

    .. code-block::

        g.V().hasLabel('aws_{{service_name}}_{{resource_name}}').out().path().by(valueMap(true))

"""
)

ATTRIBUTES_TEMPLATE = """
    .. py:attribute:: {attribute_name}

         {documentation}

"""


def _generate_mock_session(region: str = "eu-west-2") -> boto3.session.Session:
    return boto3.session.Session(region_name=region, aws_access_key_id="1111", aws_secret_access_key="1111")


class SummarisedResources:
    def __init__(self) -> None:
        self.merged_loader = MergedServiceLoader()
        self.botocore_loader = self.merged_loader.botocore_loader
        self.session = CloudWandererBoto3Session()

    @property
    @lru_cache()
    def cloudwanderer_resources(self) -> list:
        service_summary = defaultdict(list)

        for service_name in sorted(self.merged_loader.cloudwanderer_available_services):
            service = self.session.resource(service_name)
            service_model = service.meta.client.meta.service_model
            service_id = service_model.metadata["serviceId"]
            service_definition = self.merged_loader._get_custom_service_definition(
                service_name, type_name="resources-1", api_version=None
            )
            resource_list = []
            for collection_name, collection in service_definition.get("service", {}).get("hasMany", {}).items():
                resource_name = collection["resource"]["type"]
                if collection_name in self.boto3_resources.get(service_name, []):
                    continue
                try:
                    resource = service.resource(botocore.xform_name(resource_name), empty_resource=True)
                except StopIteration:
                    continue
                subresource_summary = []
                for dependent_resource_type in resource.dependent_resource_types:
                    friendly_name = dependent_resource_type.replace("_", " ").title().replace(" ", "")
                    subresource_summary.append((friendly_name, friendly_name))
                resource_list.append((service_name, collection_name, resource_name, subresource_summary))

            if resource_list:
                service_summary[service_id] = resource_list
        return service_summary

    @property
    @lru_cache()
    def boto3_resources(self) -> list:
        services_summary = defaultdict(list)
        for service_name in self.merged_loader.boto3_available_services:
            service = self.session.resource(service_name)
            service_model = service.meta.client.meta.service_model
            service_id = service_model.metadata["serviceId"]
            service_definition = self.botocore_loader.load_service_model(service_name, type_name="resources-1")
            for collection_name, collection in service_definition["service"].get("hasMany", {}).items():

                resource_name = collection["resource"]["type"]
                try:
                    resource = service.resource(botocore.xform_name(resource_name), empty_resource=True)
                except StopIteration:
                    print(f"Could not find resource: {resource_name}")
                    continue
                subresource_summary = []
                for dependent_resource_type in resource.dependent_resource_types:
                    friendly_name = dependent_resource_type.replace("_", " ").title().replace(" ", "")
                    subresource_summary.append((friendly_name, friendly_name))
                services_summary[service_id].append((service_name, collection_name, resource_name, subresource_summary))

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
        services_section = nodes.section(ids=["cloudwanderer_resources"])
        services_section += nodes.title("", "CloudWanderer Provided Resources")
        services_section += self.parse_rst(self.get_cloudwanderer_resources()).children
        return [targetnode, services_section]

    def get_cloudwanderer_resources(self) -> list:
        service_list = ""

        for service_name, resource_type_tuple in sorted(self.summarised_resources.cloudwanderer_resources.items()):
            resource_list = ""
            for service_name_snake, collection_name, resource_type, subresource_summary in resource_type_tuple:
                resource_type_snake = botocore.xform_name(resource_type.replace(" ", ""))
                reference = f"{service_name_snake}.{resource_type_snake}"
                resource_list += f"    * :class:`{collection_name}<{reference}>`\n"
                for subresource_collection, subresource_type in subresource_summary:
                    subresource_type_snake = botocore.xform_name(subresource_type)
                    reference = f"{service_name_snake}.{resource_type_snake}.{subresource_type_snake}"
                    resource_list += f"         * :class:`{subresource_collection}<{reference}>`\n"
            if resource_list:
                service_list += f"* :doc:`{service_name} <resource_properties/{service_name_snake}>`\n" + resource_list
        return service_list

    def parse_rst(self, text: str) -> docutils.nodes.document:
        parser = sphinx.parsers.RSTParser()
        parser.set_application(self.env.app)

        settings = OptionParser(
            defaults=self.env.settings, components=(sphinx.parsers.RSTParser,), read_config_files=True
        ).get_default_values()
        document = docutils.utils.new_document("<rst-doc>", settings=settings)
        parser.parse(text, document)
        return document


class Boto3ResourcesDirective(SphinxDirective):
    """A custom directive that lists Boot3 default resources."""

    has_content = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.summarised_resources = SummarisedResources()

    def run(self) -> list:
        targetid = "cloudwanderer-%d" % self.env.new_serialno("cloudwanderer")
        targetnode = nodes.target("", "", ids=[targetid])
        services_section = nodes.section(ids=["boto3_resources"])
        services_section += nodes.title("", "Boto3 Provided Resouces")
        services_section += self.parse_rst(self.get_boto3_resources()).children

        return [targetnode, services_section]

    def get_boto3_resources(self) -> list:
        service_list = ""

        for service_name, resource_type_tuple in sorted(self.summarised_resources.boto3_resources.items()):
            resource_list = ""
            for service_name_snake, collection_name, resource_type, subresource_summary in resource_type_tuple:
                resource_type_snake = botocore.xform_name(resource_type.replace(" ", ""))
                reference = f"{service_name_snake}.{resource_type_snake}"
                resource_list += f"    * :class:`{collection_name}<{reference}>`\n"
                for subresource_collection, subresource_type in subresource_summary:
                    subresource_type_snake = botocore.xform_name(subresource_type)
                    reference = f"{service_name_snake}.{resource_type_snake}.{subresource_type_snake}"
                    resource_list += f"         * :class:`{subresource_collection}<{reference}>`\n"
            if resource_list:
                service_list += f"* :doc:`{service_name} <resource_properties/{service_name_snake}>`\n" + resource_list
        return service_list

    def parse_rst(self, text: str) -> docutils.nodes.document:
        parser = sphinx.parsers.RSTParser()
        parser.set_application(self.env.app)

        settings = OptionParser(
            defaults=self.env.settings, components=(sphinx.parsers.RSTParser,), read_config_files=True
        ).get_default_values()
        document = docutils.utils.new_document("<rst-doc>", settings=settings)
        parser.parse(text, document)
        return document


class CloudWandererSecondaryAttributesDirective(SphinxDirective):
    """A custom directive that lists CloudWanderers secondary attribute definitions."""

    has_content = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.session = CloudWandererBoto3Session()

    def run(self) -> list:
        targetid = "cloudwanderer-%d" % self.env.new_serialno("cloudwanderer")
        targetnode = nodes.target("", "", ids=[targetid])
        services_section = nodes.section(ids=["cloudwanderer_secondary_attributes"])
        services_section += nodes.title("", "Secondary Attributes")
        services_section += self.parse_rst(self.get_cloudwanderer_secondary_attributes()).children

        return [targetnode, services_section]

    def get_cloudwanderer_secondary_attributes(self) -> list:
        service_list = ""

        for service_name in sorted(self.session.get_available_resources()):
            service_friendly_name = service_name
            service = self.session.resource(service_name)

            resource_list = ""
            for resource_type in service.resource_types:
                resource = service.resource(resource_type, empty_resource=True)
                secondary_attributes_list = ""
                service_friendly_name = resource.meta.resource_model.name
                resource_type_pascal = snake_to_pascal(resource_type)
                for secondary_attribute in resource.secondary_attribute_names:
                    qualified_name = f"{service_name}.{resource_type}.{secondary_attribute}"
                    secondary_attributes_list += f"         * :class:`~{qualified_name}`\n"
                if secondary_attributes_list:
                    resource_link = f":class:`{resource_type_pascal}" f"<{service_name}.{resource_type}>`"
                    resource_list += f"    * {resource_link}\n{secondary_attributes_list}"
            if resource_list:
                service_list += (
                    f"* :doc:`{service_friendly_name} <resource_properties/{service_name}>`\n{resource_list}"
                )
        return service_list

    def parse_rst(self, text: str) -> docutils.nodes.document:
        parser = sphinx.parsers.RSTParser()
        parser.set_application(self.env.app)

        settings = OptionParser(
            defaults=self.env.settings, components=(sphinx.parsers.RSTParser,), read_config_files=True
        ).get_default_values()
        document = docutils.utils.new_document("<rst-doc>", settings=settings)
        parser.parse(text, document)
        return document


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
        self.session = CloudWandererBoto3Session()
        self.loader = MergedServiceLoader()
        self.gm = GraphManager(pathlib.Path(__file__).parent.parent / pathlib.Path("images"))

    def write_graphs(self) -> None:
        self.gm.generate_graphs()
        self.gm.render_all()

    def get_cloudwanderer_services(self) -> list:
        yield from self.session.get_available_resources()

    def write_cloudwanderer_services(self) -> list:
        for service_name in self.session.get_available_resources():
            service = self.session.resource(service_name)
            service_model = service.meta.client.meta.service_model
            service_id = service_model.metadata["serviceId"]
            service_section = f"{service_id}\n{'-'*len(service_id)}\n\n"
            service_section += ".. contents:: \n"
            service_section += "\t:backlinks: none\n"
            service_section += "\t:local:\n"
            service_section += "\t:depth: 3\n\n"
            service_section += "\n\n".join(self.get_collections(service))
            if not os.path.exists(os.path.join(self.base_path, self.relative_path)):
                os.makedirs(os.path.join(self.base_path, self.relative_path))

            with open(os.path.join(self.base_path, self.relative_path, f"{service_name}.rst"), "w") as f:
                f.write(service_section)

    def parse_html(self, html: str) -> str:
        html_parser = botocore.docs.bcdoc.restdoc.ReSTDocument()
        html_parser.include_doc_string(html)
        return html_parser.getvalue().decode().replace("\n", "\n")

    def get_collections(self, service: "CloudWandererServiceResource") -> list:

        result = []

        for resource_type in sorted(service.resource_types):
            resource = service.resource(resource_type, empty_resource=True)
            result.append(self.generate_resource_section(service, resource, "{service_name}.{resource_name}"))
            result.append(self.get_subresources(service, resource))
        return result

    def get_subresources(
        self, service: "CloudWandererServiceResource", resource: "CloudWandererServiceResource"
    ) -> str:
        result = ""
        parent_resource_name = resource.resource_type

        for dependent_resource_type in resource.dependent_resource_types:

            dependent_resource = service.resource(dependent_resource_type, empty_resource=True)
            result += self.generate_resource_section(
                service,
                dependent_resource,
                f"{{service_name}}.{parent_resource_name}.{{resource_name}}",
                f"A subresource of :class:`{{service_name}}.{parent_resource_name}`.\n\n",
            )
        return result

    def generate_resource_section(
        self,
        service: "CloudWandererServiceResource",
        resource: "CloudWandererServiceResource",
        name: str,
        description: str = "",
    ) -> str:
        image = ""
        filters = ""
        service_model = service.meta.client.meta.service_model
        shape = service_model.shape_for(resource.meta.resource_model.shape)
        attributes = sorted(
            [(name, value[1]) for name, value in resource.meta.resource_model.get_attributes(shape).items()]
        )
        for attribute_name in resource.secondary_attribute_names:
            attribute_resource = service.resource(attribute_name, empty_resource=True)
            attribute_resource_shape = service_model.shape_for(attribute_resource.meta.resource_model.shape)
            attributes.append((attribute_name, attribute_resource_shape))

        if f"{service.service_name}_{resource.resource_type}" in self.gm.graph_dict:
            image = f".. image:: ../images/{service.service_name}_{resource.resource_type}.gv.png"
        if resource.resource_map.default_aws_resource_type_filter.botocore_filters:
            filters += (
                "**Default Botocore Filters:** "
                f"``{resource.resource_map.default_aws_resource_type_filter.botocore_filters}``\n\n"
            )
        if resource.resource_map.default_aws_resource_type_filter.jmespath_filters:
            filters += (
                "**Default JMESPath Filters:** "
                f"``{resource.resource_map.default_aws_resource_type_filter.jmespath_filters}``\n"
            )
        resource_section = RESOURCE_TEMPLATE.render(
            class_name=name.format(service_name=service.service_name, resource_name=resource.resource_type),
            service_name=service.service_name,
            resource_name=resource.resource_type,
            description=description.format(service_name=service.service_name, resource_name=resource.resource_type),
            default_filters=filters,
            image=image,
        )

        attributes_doc = ""
        for attribute_name, attribute in attributes:
            documentation = attribute.documentation
            documentation = self.parse_html(documentation).replace("\n", "")
            attributes_doc += ATTRIBUTES_TEMPLATE.format(attribute_name=attribute_name, documentation=documentation)
            # resource_section += f"            print(resource.{attribute_name})\n"

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
    d.write_graphs()
    d.write_cloudwanderer_services()


def setup(app: object) -> dict:
    app.add_domain(SupportedResources)
    app.connect("builder-inited", main)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
