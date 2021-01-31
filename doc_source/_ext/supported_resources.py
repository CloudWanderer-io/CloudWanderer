import docutils
import os
import pathlib
from docutils import nodes
from docutils.frontend import OptionParser
import botocore
import sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.domains import Domain
from botocore import xform_name
import boto3
import cloudwanderer

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


class CloudWandererResourcesDirective(SphinxDirective):
    """A custom directive that lists CloudWanderers added resources."""

    has_content = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.boto3_session = boto3.Session(region_name='eu-west-2')
        self.boto3_interface = cloudwanderer.boto3_interface.CloudWandererBoto3Interface(
            boto3_session=self.boto3_session
        )
        self.boto3_services = list(self.get_boto3_default_services())

    def run(self) -> list:
        targetid = 'cloudwanderer-%d' % self.env.new_serialno('cloudwanderer')
        targetnode = nodes.target('', '', ids=[targetid])

        return [targetnode, self.get_cloudwanderer_resources()]

    def get_boto3_default_services(self) -> list:
        boto3_services = self.boto3_session.get_available_resources()
        for service_name in boto3_services:
            resource_collections = self.boto3_interface.get_resource_collections(
                self.boto3_session.resource(service_name)
            )
            for resource_collection in resource_collections:
                yield (service_name, resource_collection.name)

    def get_cloudwanderer_resources(self) -> list:
        service_list = nodes.bullet_list()
        cloudwanderer_services = self.boto3_interface.custom_resource_definitions.services
        for service_name, service in sorted(cloudwanderer_services.items()):
            client = self.boto3_session.client(service_name)
            service_model = client.meta.service_model
            service_name = service_model.metadata['serviceId']
            resource_list = nodes.bullet_list()
            resource_collections = self.boto3_interface.get_resource_collections(
                service
            )
            for resource_collection in resource_collections:
                shape = service_model.shape_for(resource_collection.resource.model.shape)
                if (service_name, resource_collection.name) not in self.boto3_services:
                    resource_list += nodes.list_item('', nodes.Text(shape.name))
            if resource_list.children:
                service_list += nodes.list_item('', nodes.Text(service_name), resource_list)
        return service_list


class CloudWandererSecondaryAttributesDirective(SphinxDirective):
    """A custom directive that lists CloudWanderers secondary attribute definitions."""

    has_content = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.boto3_interface = cloudwanderer.boto3_interface.CloudWandererBoto3Interface(
            boto3_session=boto3.Session(region_name='eu-west-2')
        )

    def run(self) -> list:
        targetid = 'cloudwanderer-%d' % self.env.new_serialno('cloudwanderer')
        targetnode = nodes.target('', '', ids=[targetid])

        return [targetnode, self.get_cloudwanderer_secondary_attributes()]

    def get_cloudwanderer_secondary_attributes(self) -> list:
        service_list = nodes.bullet_list()

        for boto3_service in self.boto3_interface.get_all_resource_services():
            for collection in self.boto3_interface.get_resource_collections(boto3_service):
                service_model = boto3_service.meta.client.meta.service_model
                service_name = service_model.metadata['serviceId']
                resource_list = nodes.bullet_list()
                secondary_attributes = self.boto3_interface.get_child_resource_definitions(
                    service_name=boto3_service.meta.service_name,
                    boto3_resource_model=collection.resource.model,
                    resource_type='secondaryAttribute')
                for secondary_attribute in secondary_attributes:
                    resource_list += nodes.list_item('', nodes.Text(secondary_attribute.name))
                if resource_list.children:
                    service_list += nodes.list_item(
                        '',
                        nodes.Text(service_name), resource_list)
        return service_list


class CloudWandererResourceDefinitionsDirective(SphinxDirective):
    """A custom directive that describes CloudWanderers respources."""

    has_content = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.cw = GetCwServices()
        self.relative_path = 'resource_properties'

    def run(self) -> list:
        services_section = nodes.section(ids=['cloudwanderer_resources'])
        services_section += nodes.title('', 'CloudWanderer Resources')
        rst_section = '.. toctree::\n'
        rst_section += '   :maxdepth: 2\n\n'
        for service_name, _ in self.cw.get_cloudwanderer_services():
            rst_section += f'   {os.path.join(self.relative_path, service_name)}.rst\n'
        services_section += self.parse_rst(rst_section).children
        targetid = 'cloudwanderer-%d' % self.env.new_serialno('cloudwanderer')
        targetnode = nodes.target('', '', ids=[targetid])
        return [targetnode, services_section]

    def parse_rst(self, text: str) -> docutils.nodes.document:
        parser = sphinx.parsers.RSTParser()
        parser.set_application(self.env.app)

        settings = OptionParser(
            defaults=self.env.settings,
            components=(sphinx.parsers.RSTParser,),
            read_config_files=True).get_default_values()
        document = docutils.utils.new_document('<rst-doc>', settings=settings)
        parser.parse(text, document)
        return document


class GetCwServices:

    def __init__(self) -> None:
        self.relative_path = 'resource_properties'
        self.base_path = os.path.join(pathlib.Path(__file__).parent.absolute(), '..')
        self.boto3_interface = cloudwanderer.boto3_interface.CloudWandererBoto3Interface(
            boto3_session=boto3.Session(region_name='eu-west-2')
        )

    def get_cloudwanderer_services(self) -> list:
        boto3_services = sorted(
            self.boto3_interface.get_all_resource_services(),
            key=lambda x: x.meta.resource_model.name)
        for boto3_service in boto3_services:
            service_model = boto3_service.meta.client.meta.service_model
            service_name = service_model.metadata['serviceId']
            yield service_name, boto3_service

    def write_cloudwanderer_services(self) -> list:
        for service_name, boto3_service in self.get_cloudwanderer_services():
            service_section = f"{service_name}\n{'-'*len(service_name)}\n\n"
            service_section += '\n\n'.join(self.get_collections(boto3_service))
            if not os.path.exists(os.path.join(self.base_path, self.relative_path)):
                os.makedirs(os.path.join(self.base_path, self.relative_path))

            with open(os.path.join(self.base_path, self.relative_path, f'{service_name}.rst'), 'w') as f:
                f.write(service_section)

    def parse_html(self, html: str) -> str:
        html_parser = botocore.docs.bcdoc.restdoc.ReSTDocument()
        html_parser.include_doc_string(html)
        return html_parser.getvalue().decode().replace('\n', '\n')

    def get_collections(self, boto3_service: boto3.resources.base.ServiceResource) -> list:

        result = []
        collections = sorted(
            self.boto3_interface.get_resource_collections(boto3_service),
            key=lambda x: x.resource.model.name)
        for collection in collections:
            result.append(self.generate_resource_section(boto3_service, collection, "{service_name}.{resource_name}"))
            result.append(self.get_subresources(boto3_service, collection.resource.model))
            result.append(self.get_secondary_attributes(boto3_service, collection.resource.model))
        return result

    def get_subresources(
            self,
            boto3_service: boto3.resources.base.ServiceResource,
            boto3_resource: boto3.resources.model.ResourceModel) -> str:
        result = ''
        service_name = boto3_service.meta.resource_model.name
        parent_resource_name = xform_name(boto3_resource.name)
        subresources = self.boto3_interface.get_child_resource_definitions(
            service_name, boto3_resource, 'resource')
        for collection in subresources:
            result += self.generate_resource_section(
                boto3_service, collection,
                f"{{service_name}}.{parent_resource_name}.{{resource_name}}",
                f"A subresource of :class:`{{service_name}}.{parent_resource_name}`.\n\n"
            )
        return result

    def get_secondary_attributes(
            self,
            boto3_service: boto3.resources.base.ServiceResource,
            boto3_resource: boto3.resources.model.ResourceModel) -> str:
        result = ''
        service_name = boto3_service.meta.resource_model.name
        parent_resource_name = xform_name(boto3_resource.name)
        secondaryAttributes = self.boto3_interface.get_child_resource_definitions(
            service_name, boto3_resource, 'secondaryAttribute')
        for collection in secondaryAttributes:
            resource_name = xform_name(collection.resource.model.name)
            result += SECONDARY_ATTR_TEMPLATE.format(
                service_name=service_name,
                parent_resource_name=parent_resource_name,
                resource_name=resource_name,
            )
        return result

    def generate_resource_section(
            self,
            boto3_service: boto3.resources.base.ServiceResource,
            boto3_collection: boto3.resources.model.Collection,
            name: str,
            description: str = '') -> str:
        service_name = boto3_service.meta.resource_model.name
        service_model = boto3_service.meta.client.meta.service_model
        shape = service_model.shape_for(boto3_collection.resource.model.shape)
        attributes = sorted(boto3_collection.resource.model.get_attributes(shape).items())
        resource_name = xform_name(boto3_collection.resource.model.name)

        resource_section = RESOURCE_TEMPLATE.format(
            class_name=name.format(service_name=service_name, resource_name=resource_name),
            service_name=service_name,
            resource_name=resource_name,
            description=description.format(service_name=service_name, resource_name=resource_name)
        )
        attributes_doc = ''
        for attribute_name, attribute in attributes:
            documentation = attribute[1].documentation
            documentation = self.parse_html(documentation).replace("\n", "")
            attributes_doc += ATTRIBUTES_TEMPLATE.format(
                attribute_name=attribute_name,
                documentation=documentation)
            resource_section += f"            print(resource.{attribute_name})\n"

        resource_section += '\n\n'
        resource_section += attributes_doc
        return resource_section


class SupportedResources(Domain):

    name = 'supported-resources'
    label = 'Cloudwanderer Supported Resources'
    directives = {
        'cloudwanderer-resources': CloudWandererResourcesDirective,
        'cloudwanderer-secondary-attributes': CloudWandererSecondaryAttributesDirective,
        'resource-definitions': CloudWandererResourceDefinitionsDirective,
    }


def main(*args) -> None:
    d = GetCwServices()
    d.write_cloudwanderer_services()


def setup(app: object) -> dict:
    app.add_domain(SupportedResources)
    app.connect('builder-inited', main)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
