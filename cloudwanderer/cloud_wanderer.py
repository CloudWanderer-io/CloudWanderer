"""Main cloudwanderer module."""
from collections import namedtuple
import logging
from botocore import xform_name
import boto3
from .boto3_interface import CloudWandererBoto3Interface, CustomAttributesInterface
from .aws_urn import AwsUrn
from .global_service_mappings import GlobalServiceMappingCollection


class CloudWanderer():
    """CloudWanderer.

    Args:
        storage_connector: A CloudWanderer storage connector object.
        boto3_session (boto3.session.Session): A boto3 :class:`~boto3.session.Session` object.
    """

    def __init__(self, storage_connector, boto3_session=None):
        """Initialise CloudWanderer."""
        self.storage_connector = storage_connector
        self.boto3_session = boto3_session or boto3.session.Session()
        self.boto3_interface = CloudWandererBoto3Interface(boto3_session=self.boto3_session)
        self.custom_attributes_interface = CustomAttributesInterface(boto3_session=self.boto3_session)
        self.global_service_maps = GlobalServiceMappingCollection(boto3_session=self.boto3_session)
        self._account_id = None

    def write_all_resources(self, exclude_resources=None, region_name=None, service_args=None):
        """Write all AWS resources in this account region from all services to storage."""
        exclude_resources = exclude_resources or []

        service_args = service_args or {'region_name': region_name}

        for boto3_service in self.boto3_interface.get_all_resource_services():
            self.write_resources(
                service_name=boto3_service.meta.service_name,
                exclude_resources=exclude_resources,
                region_name=region_name,
                service_args=service_args
            )

    def write_resources(self, service_name, exclude_resources=None, region_name=None, service_args=None):
        """Write all AWS resources in this region in this service to storage.

        Arguments:
            service_name (str): The name of the service to write resources for (e.g. ``'ec2'``)
            exclude_resources (list): A list of resource names to exclude (e.g. ``['instance']``)
            region_name (str): The name of the region to get resources from
                (defaults to session default if not specified)
            service_args (dict): Arguments to pass into the boto3 service Resource object.
                See: :meth:`boto3.session.Session.resource`
        """
        service_args = {
            'region_name': region_name or self.boto3_session.region_name
        }
        logging.info("Writing all %s resources in %s", service_name, service_args['region_name'])
        exclude_resources = exclude_resources or []
        service_map = self.global_service_maps.get_global_service_map(service_name=service_name)
        if (
            not service_map.has_global_resources_in_region(service_args['region_name'])
            and not service_map.has_regional_resources
        ):
            logging.info("Skipping %s as it does not have resources in %s",
                         service_name, service_args['region_name'])
            return

        for resource_name in self.boto3_interface.get_service_resource_names(service_name=service_name):
            if resource_name in exclude_resources:
                logging.info('Skipping %s as per exclude_resources', resource_name)
                continue
            self.write_resources_of_type(
                service_name=service_name,
                resource_type=resource_name,
                service_args=service_args
            )

    def write_resources_of_type(self, service_name, resource_type=None, region_name=None, service_args=None):
        """Write all AWS resources in this region in this service to storage.

        Arguments:
            service_name (str): The name of the service to write resources for (e.g. ``'ec2'``)
            resource_type (str): The name of the type of the resource to write (e.g. ``'instance'``)
            region_name (str): The name of the region to get resources from
                (defaults to session default if not specified)
            service_args (dict): Arguments to pass into the boto3 service Resource object.
                See: :meth:`boto3.session.Session.resource`
        """
        service_args = service_args or {
            'region_name': region_name or self.boto3_session.region_name
        }
        logging.info('--> Fetching %s %s from %s', service_name, resource_type, service_args['region_name'])
        resources = self.boto3_interface.get_resources_of_type(service_name, resource_type, service_args)
        urns = []
        for boto3_resource in resources:
            urn = self._get_resource_urn(boto3_resource)
            if not self._should_write_resource_in_region(urn, service_args['region_name']):
                continue
            self.storage_connector.write_resource(urn, boto3_resource)
            urns.append(urn)
        self._clean_resources_in_region(
            service_name, resource_type, service_args['region_name'], urns)

    def _clean_resources_in_region(self, service_name, resource_type, region_name, current_urns):
        """Remove all resources of this type in this region which no longer exist."""
        self.storage_connector.delete_resource_of_type_in_account_region(
            service=service_name,
            resource_type=resource_type,
            account_id=self.account_id,
            region=region_name,
            urns_to_keep=current_urns
        )

    def _should_write_resource_in_region(self, urn, write_region):
        """Return True if this is a resource we should write in this region and log the result."""
        if urn.region != write_region:
            logging.debug(
                "Skipping %s %s in %s because it is not in %s",
                urn.resource_type,
                urn.resource_id,
                urn.region,
                write_region
            )
            return False
        return True

    def write_all_resource_attributes(self, exclude_resources=None, region_name=None, service_args=None):
        """Write all AWS resource attributes in this account in this region to storage.

        These custom resource attribute definitions allow us to fetch resource attributes that are not returned by the
        resource's default describe calls.
        Unlike :meth:`~CloudWanderer.write_resources` and :meth:`~CloudWanderer.write_resources_of_type` this method does not clean up stale resource attributes from storage.

        Arguments:
            service_name (str): The name of the service to write the attributes of (e.g. ``ec2``)
        """
        service_args = service_args or {'region_name': region_name}

        for boto3_service in self.custom_attributes_interface.get_all_resource_services():
            self.write_resource_attributes(
                service_name=boto3_service.meta.service_name,
                exclude_resources=exclude_resources,
                region_name=region_name,
                service_args=service_args
            )

        # services = self.custom_attributes_interface.get_resource_attributes_service_by_name(service_name)
        # for service_name in services:
        #     self.write_resource_attributes(service_name)

    def write_resource_attributes(self, service_name, exclude_resources=None, region_name=None, service_args=None):
        """Write all AWS resource attributes in this account in this service to storage.

        These custom resource attribute definitions allow us to fetch resource attributes that are not returned by the
        resource's default describe calls.
        Unlike :meth:`~CloudWanderer.write_resources` and :meth:`~CloudWanderer.write_resources_of_type` this method does not clean up stale resource attributes from storage.

        Arguments:
            service_name (str): The name of the service to write the attributes of (e.g. ``'ec2'``)
            exclude_attributes (list): A list of resources not to write attributes for (e.g. ``['vpc']``)
        """
        exclude_resources = exclude_resources or []
        service_args = service_args or {'region_name': region_name}
        for resource_name in self.custom_attributes_interface.get_service_resource_names(service_name):
            if resource_name in exclude_resources:
                logging.info('Skipping %s as per exclude_resources', resource_name)
                continue
            self.write_resource_attributes_of_type(service_name, resource_name)

    def write_resource_attributes_of_type(self, service_name, resource_type, service_args=None):
        """Write all AWS resource attributes in this account of this resource type to storage.

        These custom resource attribute definitions allow us to fetch resource attributes that are not returned by the
        resource's default describe calls.

        Arguments:
            service_name (str): The name of the service to write the attributes of (e.g. ``ec2``)
            resource_type (str): The type of resource to write the attributes of (e.g. ``instance``)
        """
        logging.info('--> Fetching %s %s', service_name, resource_type)
        resource_attributes = self.custom_attributes_interface.get_resources_of_type(service_name, resource_type, service_args)
        for resource_attribute in resource_attributes:
            urn = self._get_resource_urn(resource_attribute)
            self.storage_connector.write_resource_attribute(
                urn=urn,
                resource_attribute=resource_attribute,
                attribute_type=xform_name(resource_attribute.meta.resource_model.name)
            )

    def read_resource_of_type(self, service, resource_type):
        """Return all resources of type.

        Args:
            service (str): Service name (e.g. ec2)
            resource_type (str): Resource Type (e.g. instance)
        """
        return self.storage_connector.read_resource_of_type(service, resource_type)

    def read_resource(self, urn):
        """Return a specific resource by its urn from storage."""
        try:
            return next(self.storage_connector.read_resource(urn))
        except StopIteration:
            return None

    def read_all_resources_in_account(self, account_id):
        """Return all resources in the provided AWS Account from storage."""
        return self.storage_connector.read_all_resources_in_account(account_id)

    def read_resource_of_type_in_account(self, service, resource_type, account_id):
        """Return all resources of this type in the provided AWS Account from storage."""
        return self.storage_connector.read_resource_of_type_in_account(service, resource_type, account_id)

    @property
    def account_id(self):
        """Return the AWS Account ID our boto3 session is authenticated against."""
        if self._account_id is None:
            sts = self.boto3_session.client('sts')
            self._account_id = sts.get_caller_identity()['Account']
        return self._account_id

    def _get_resource_urn(self, resource):
        id_member_name = resource.meta.resource_model.identifiers[0].name
        resource_id = getattr(resource, id_member_name)
        if resource_id.startswith('arn:'):
            resource_id = ''.join(resource_id.split(':')[5:])
        global_service_map = self.global_service_maps.get_global_service_map(resource.meta.service_name)
        return AwsUrn(
            account_id=self.account_id,
            region=global_service_map.get_resource_region(resource),
            service=resource.meta.service_name,
            resource_type=xform_name(resource.meta.resource_model.shape),
            resource_id=resource_id
        )


class ResourceMetadata(namedtuple('ResourceMetadata', ['resource_data', 'resource_attributes'])):
    """Metadata for a :class:`CloudWandererResource`.

    Contains the original dictionaries of the resource and its attributes.

    Attributes:
        resource_data (dict): The raw dictionary representation of the Resource.
        resource_attributes (list): the list of raw dictionary representation of the Resource's attributes.
    """


class CloudWandererResource():
    """A simple representation of a resource that prevents any storage metadata polluting the resource dictionary.

    Use ``dict(my_resource_dict)`` to convert this object into a dictionary that
    contains *only* the resource's metadata.

    Attributes:
        urn (cloudwanderer.aws_urn.AwsUrn): The AWS URN of the resource.
        metadata (dict): The original storage representation of the resource as it was passed in.
    """

    def __init__(self, urn, resource_data, resource_attributes=None):
        """Initialise the resource."""
        self.urn = urn
        self.cloudwanderer_metadata = ResourceMetadata(
            resource_data=resource_data,
            resource_attributes=resource_attributes or []
        )
        self._set_attrs()

    @property
    def _clean_resource(self):
        return {
            key: value
            for key, value in self.metadata.items()
            if not key.startswith('_')
        }

    def _set_attrs(self):
        for key, value in self.cloudwanderer_metadata.resource_data.items():
            setattr(
                self,
                xform_name(key),
                value
            )

    def __repr__(self):
        """Return a code representation of this resource."""
        return str(
            f"{self.__class__.__name__}("
            f"urn={repr(self.urn)}, "
            f"resource_data={self.cloudwanderer_metadata.resource_data}, "
            f"resource_attributes={self.cloudwanderer_metadata.resource_attributes})"
        )

    def __str__(self):
        """Return the string representation of this Resource."""
        return repr(self)
