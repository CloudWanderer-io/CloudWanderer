from docutils import nodes
from sphinx.util.docutils import SphinxDirective
from sphinx.domains import Domain
from botocore import xform_name
import boto3
import cloudwanderer


def capitalize_snake_case(snake: str) -> str:
    return str(snake).replace('_', ' ').title()


class Boto3ResourcesDirective(SphinxDirective):
    """A custom directive that lists boto3's default resources."""

    has_content = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.boto3_session = boto3.Session(region_name='eu-west-2')
        self.boto3_interface = cloudwanderer.boto3_interface.CloudWandererBoto3Interface(
            boto3_session=self.boto3_session
        )

    def run(self) -> list:
        targetid = 'cloudwanderer-%d' % self.env.new_serialno('cloudwanderer')
        targetnode = nodes.target('', '', ids=[targetid])

        return [targetnode, self.get_boto3_default_resources()]

    def get_boto3_default_resources(self) -> list:
        service_list = nodes.bullet_list()
        boto3_services = self.boto3_session.get_available_resources()
        for service_name in boto3_services:
            resource_list = nodes.bullet_list()
            resource_collections = self.boto3_interface.get_resource_collections(
                self.boto3_session.resource(service_name)
            )
            for resource_collection in resource_collections:
                resource_list += nodes.list_item('', nodes.Text(capitalize_snake_case(resource_collection.name)))
            service_list += nodes.list_item('', nodes.Text(capitalize_snake_case(service_name)), resource_list)
        return service_list


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
        for service_name, service in cloudwanderer_services.items():

            resource_list = nodes.bullet_list()
            resource_collections = self.boto3_interface.get_resource_collections(
                service
            )
            for resource_collection in resource_collections:
                if (service_name, resource_collection.name) not in self.boto3_services:
                    resource_list += nodes.list_item('', nodes.Text(capitalize_snake_case(resource_collection.name)))
            if resource_list.children:
                service_list += nodes.list_item('', nodes.Text(capitalize_snake_case(service_name)), resource_list)
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
                        nodes.Text(capitalize_snake_case(collection.name)), resource_list)
        return service_list


class CloudWandererResourceDefinitionsDirective(SphinxDirective):
    """A custom directive that describes CloudWanderers respources."""

    has_content = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.boto3_interface = cloudwanderer.boto3_interface.CloudWandererBoto3Interface(
            boto3_session=boto3.Session(region_name='eu-west-2')
        )

    def run(self) -> list:
        services_section = nodes.section(ids=['cloudwanderer_resources'])
        services_section += nodes.title('', 'CloudWanderer Resources')
        services_section.extend(self.get_cloudwanderer_services())
        return [services_section]

    def get_cloudwanderer_services(self) -> list:
        sections = []
        boto3_services = sorted(
            self.boto3_interface.get_all_resource_services(),
            key=lambda x: x.meta.resource_model.name)
        for boto3_service in boto3_services:
            service_name = boto3_service.meta.resource_model.name
            service_id = f"cloudwanderer_resources_{service_name}"
            service_section = nodes.section(ids=[service_id])
            service_section += nodes.title('', service_name)

            service_section.extend(self.get_collections(boto3_service, service_id))
            sections.append(service_section)
        return sections

    def get_collections(self, boto3_service: boto3.resources.base.ServiceResource, service_id: str) -> list:

        result = []
        collections = sorted(
            self.boto3_interface.get_resource_collections(boto3_service),
            key=lambda x: x.resource.model.name)
        for collection in collections:
            resource_name = xform_name(collection.resource.model.name)
            resource_section = nodes.section(ids=[f"{service_id}_{resource_name}"])
            resource_section += nodes.title('', resource_name)
            resource_section += nodes.paragraph('', f"{resource_name} has the following attributes:")
            attributes_list = nodes.bullet_list()
            service_model = boto3_service.meta.client.meta.service_model
            shape = service_model.shape_for(collection.resource.model.shape)
            attributes = collection.resource.model.get_attributes(shape)
            for attribute in sorted(attributes.keys()):
                attributes_list += nodes.list_item('', nodes.Text(attribute))
            resource_section += attributes_list

            result.append(resource_section)
        return result


class SupportedResources(Domain):

    name = 'supported-resources'
    label = 'Cloudwanderer Supported Resources'
    directives = {
        'boto3-default-resources': Boto3ResourcesDirective,
        'cloudwanderer-resources': CloudWandererResourcesDirective,
        'cloudwanderer-secondary-attributes': CloudWandererSecondaryAttributesDirective,
        'resource-definitions': CloudWandererResourceDefinitionsDirective,
    }


def setup(app: object) -> dict:
    app.add_domain(SupportedResources)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
