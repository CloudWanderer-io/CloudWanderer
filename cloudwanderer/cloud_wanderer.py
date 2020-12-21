"""Main cloudwanderer module."""
from collections import namedtuple
import logging
from botocore import xform_name
import boto3
from .boto3_interface import CloudWandererBoto3Interface
from .aws_urn import AwsUrn
from .global_service_mappings import GlobalServiceMappingCollection


class CloudWanderer():
    """CloudWanderer.

    Args:
        storage_connector: A CloudWanderer storage connector object.
        boto3_session (boto3.session.Session): A boto3 Session object.
    """

    def __init__(self, storage_connector, boto3_session=None):
        """Initialise CloudWanderer."""
        self.storage_connector = storage_connector
        self.boto3_session = boto3_session or boto3.session.Session()
        self.boto3_interface = CloudWandererBoto3Interface(boto3_session=self.boto3_session)
        self.global_service_maps = GlobalServiceMappingCollection(boto3_session=self.boto3_session)
        self._account_id = None

    def write_all_resources(self, exclude_resources=None):
        """Write all AWS resources in this account from all services to storage."""
        exclude_resources = exclude_resources or []
        for boto3_service in self.boto3_interface.get_all_resource_services():
            self.write_resources(
                service_name=boto3_service.meta.service_name,
                exclude_resources=exclude_resources
            )

    def write_resources(self, service_name, exclude_resources=None):
        """Write all AWS resources in this account in this service to storage.

        Arguments:
            service_name (str): The name of the service to write resources for (e.g. ``'ec2'``)
            exclude_resources (list): A list of resources to exclude (e.g. `['instances']`)
        """
        logging.info("Writing all %s resources in %s", service_name, self.boto3_session.region_name)
        exclude_resources = exclude_resources or []
        service_map = self.global_service_maps.get_global_service_map(service_name=service_name)
        if (
            not service_map.has_global_resources_in_region(self.boto3_session.region_name)
            and not service_map.has_regional_resources
        ):
            logging.info("Skipping %s as it does not have resources in %s",
                         service_name, self.boto3_session.region_name)
            return
        for boto3_service in self.boto3_interface.get_resource_service_by_name(service_name):
            for boto3_resource_collection in self.boto3_interface.get_resource_collections(boto3_service):
                if boto3_resource_collection.name in exclude_resources:
                    logging.info('Skipping %s as per exclude_resources', boto3_resource_collection.name)
                    continue
                logging.info('--> Fetching %s %s', boto3_service.meta.service_name, boto3_resource_collection.name)
                resources = self.boto3_interface.get_resource_from_collection(boto3_service, boto3_resource_collection)
                urns = []
                for boto3_resource in resources:
                    urn = self._get_resource_urn(boto3_resource)
                    if urn.region != self.boto3_session.region_name:
                        logging.debug(
                            "Skipping %s %s in %s because it is not in %s",
                            urn.resource_type,
                            urn.resource_id,
                            urn.region,
                            self.boto3_session.region_name
                        )
                        continue
                    self.storage_connector.write_resource(urn, boto3_resource)
                    urns.append(urn)
                self.storage_connector.delete_resource_of_type_in_account_region(
                    service=boto3_service.meta.service_name,
                    resource_type=xform_name(boto3_resource_collection.resource.model.shape),
                    account_id=self.account_id,
                    region=self.boto3_session.region_name,
                    urns_to_keep=urns
                )

    def write_resource_attributes(self, service_name):
        """Write all AWS resource attributes in this account in this service to storage.

        These custom resource attribute definitions allow us to fetch resource attributes that are not returned by the
        resource's default describe calls.

        Arguments:
            service_name (str): The name of the service to write the attributes of (e.g. ``ec2``)
        """
        services = self.boto3_interface.get_resource_attributes_service_by_name(service_name)
        for boto3_resource_attribute_service in services:
            collections = self.boto3_interface.get_resource_collections(boto3_resource_attribute_service)
            for boto3_resource_attribute_collection in collections:
                logging.info(
                    '--> Fetching %s %s',
                    boto3_resource_attribute_service.meta.service_name,
                    boto3_resource_attribute_collection.name
                )
                resource_attributes = self.boto3_interface.get_resource_attribute_from_collection(
                    boto3_resource_attribute_service,
                    boto3_resource_attribute_collection
                )

                for boto3_resource_attribute in resource_attributes:
                    urn = self._get_resource_urn(boto3_resource_attribute)
                    self.storage_connector.write_resource_attribute(
                        urn=urn,
                        resource_attribute=boto3_resource_attribute,
                        attribute_type=boto3_resource_attribute_collection.name
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
        urn (cloudwanderer.AwsUrn): The AWS URN of the resource.
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
