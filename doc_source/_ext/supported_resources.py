from docutils import nodes
from sphinx.util.docutils import SphinxDirective
from sphinx.domains import Domain
import boto3
import cloudwanderer


def capitalize_snake_case(snake: str) -> str:
    return str(snake).replace('_', ' ').title()


class Boto3ResourcesDirective(SphinxDirective):
    """A custom directive that describes boto3's default resources."""

    has_content = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.boto3_interface = cloudwanderer.boto3_interface.CloudWandererBoto3Interface(
            boto3_session=boto3.Session(region_name='eu-west-2')
        )

    def run(self) -> list:
        targetid = 'cloudwanderer-%d' % self.env.new_serialno('cloudwanderer')
        targetnode = nodes.target('', '', ids=[targetid])

        return [targetnode, self.get_boto3_default_resources()]

    def get_boto3_default_resources(self) -> list:
        service_list = nodes.bullet_list()
        boto3_services = self.boto3_interface._get_available_services()
        for service_name in boto3_services:

            resource_list = nodes.bullet_list()
            resource_collections = self.boto3_interface.get_resource_collections(
                self.boto3_interface.get_boto3_resource_service(service_name)
            )
            for resource_collection in resource_collections:
                resource_list += nodes.list_item('', nodes.Text(capitalize_snake_case(resource_collection.name)))
            service_list += nodes.list_item('', nodes.Text(capitalize_snake_case(service_name)), resource_list)
        return service_list


class CloudWandererResourcesDirective(SphinxDirective):
    """A custom directive that describes CloudWanderers added resources."""

    has_content = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.boto3_interface = cloudwanderer.boto3_interface.CloudWandererBoto3Interface(
            boto3_session=boto3.Session(region_name='eu-west-2')
        )

    def run(self) -> list:
        targetid = 'cloudwanderer-%d' % self.env.new_serialno('cloudwanderer')
        targetnode = nodes.target('', '', ids=[targetid])

        return [targetnode, self.get_cloudwanderer_resources()]

    def get_cloudwanderer_resources(self) -> list:
        service_list = nodes.bullet_list()
        cloudwanderer_services = self.boto3_interface.custom_resource_definitions.definitions
        for service_name, service in cloudwanderer_services.items():

            resource_list = nodes.bullet_list()
            resource_collections = self.boto3_interface.get_resource_collections(
                service
            )
            for resource_collection in resource_collections:
                resource_list += nodes.list_item('', nodes.Text(capitalize_snake_case(resource_collection.name)))
            service_list += nodes.list_item('', nodes.Text(capitalize_snake_case(service_name)), resource_list)
        return service_list


class CloudWandererResourceAttributesDirective(SphinxDirective):
    """A custom directive that describes CloudWanderers additional resource attribute definitions."""

    has_content = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.secondary_attributes_interface = cloudwanderer.boto3_interface.SecondaryAttributesInterface(
            boto3.Session(region_name='eu-west-1'))

    def run(self) -> list:
        targetid = 'cloudwanderer-%d' % self.env.new_serialno('cloudwanderer')
        targetnode = nodes.target('', '', ids=[targetid])

        return [targetnode, self.get_cloudwanderer_secondary_attributes()]

    def get_cloudwanderer_secondary_attributes(self) -> list:
        service_list = nodes.bullet_list()
        services = self.secondary_attributes_interface.custom_secondary_attribute_definitions.definitions
        for service_name, service in services.items():

            resource_list = nodes.bullet_list()
            resource_collections = self.secondary_attributes_interface.get_resource_collections(
                service
            )
            for resource_collection in resource_collections:
                resource_list += nodes.list_item('', nodes.Text(resource_collection.name))
            service_list += nodes.list_item('', nodes.Text(capitalize_snake_case(service_name)), resource_list)
        return service_list


class SupportedResources(Domain):

    name = 'supported-resources'
    label = 'Cloudwanderer Supported Resources'
    directives = {
        'boto3-default-resources': Boto3ResourcesDirective,
        'cloudwanderer-resources': CloudWandererResourcesDirective,
        'cloudwanderer-resource-attributes': CloudWandererResourceAttributesDirective
    }


def setup(app: object) -> dict:
    app.add_domain(SupportedResources)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
