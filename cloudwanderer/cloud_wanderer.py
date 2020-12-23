"""Main cloudwanderer module."""
from typing import List
from collections import namedtuple
import logging
from typing import TYPE_CHECKING
import concurrent.futures
from botocore import xform_name
import boto3
from .utils import exception_logging_wrapper
from .boto3_interface import CloudWandererBoto3Interface, CustomAttributesInterface
from .aws_urn import AwsUrn
from .global_service_mappings import GlobalServiceMappingCollection
from boto3.resources.model import ResourceModel

logger = logging.getLogger('cloudwanderer')

if TYPE_CHECKING:
    from .storage_connectors import BaseStorageConnector  # noqa


class CloudWanderer():
    """CloudWanderer.

    Args:
        storage_connector: A CloudWanderer storage connector object.
        boto3_session (boto3.session.Session): A boto3 :class:`~boto3.session.Session` object.
    """

    def __init__(
            self, storage_connector: 'BaseStorageConnector',
            boto3_session: boto3.session.Session = None) -> None:
        """Initialise CloudWanderer."""
        self.storage_connector = storage_connector
        self.boto3_session = boto3_session or boto3.session.Session()
        self.boto3_interface = CloudWandererBoto3Interface(boto3_session=self.boto3_session)
        self.custom_attributes_interface = CustomAttributesInterface(boto3_session=self.boto3_session)
        self.global_service_maps = GlobalServiceMappingCollection(boto3_session=self.boto3_session)
        self._account_id = None
        self._enabled_regions = None

    def write_resources(
            self, exclude_resources: List[str] = None, client_args: dict = None, concurrency: int = 1) -> None:
        """Write all AWS resources in this account from all regions and all services to storage.

        Arguments:
            exclude_resources (list): A list of resource names to exclude (e.g. ``['instance']``)
            client_args (dict): Arguments to pass into the boto3 client.
                See: :meth:`boto3.session.Session.client`
            concurrency (int): Number of query threads to invoke concurrently.
                If the number of threads exceeds the number of regions by at least two times
                multiple services to be queried concurrently in each region.
                **WARNING:** Experimental. Complete data capture depends heavily on the thread safeness of the
                storage connector and has not been thoroughly tested!
        """
        logger.info('Writing resources in all regions')
        if concurrency > 1:
            logger.warning('Using concurrency of: %s - CONCURRENCY IS EXPERIMENTAL', concurrency)
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            for region_name in self.enabled_regions:
                executor.submit(
                    exception_logging_wrapper,
                    method=self.write_resources_in_region,
                    exclude_resources=exclude_resources,
                    region_name=region_name,
                    client_args=client_args
                )

    def write_resources_in_region(
            self, exclude_resources: List[str] = None, region_name: str = None,
            client_args: dict = None) -> None:
        """Write all AWS resources in this account region from all services to storage.

        Arguments:
            exclude_resources (list): A list of resource names to exclude (e.g. ``['instance']``)
            region_name (str): The name of the region to get resources from
                (defaults to session default if not specified)
            client_args (dict): Arguments to pass into the boto3 client.
                See: :meth:`boto3.session.Session.client`
        """
        exclude_resources = exclude_resources or []
        for boto3_service in self.boto3_interface.get_all_resource_services():
            self.write_resources_of_service_in_region(
                service_name=boto3_service.meta.service_name,
                exclude_resources=exclude_resources,
                region_name=region_name,
                client_args=client_args
            )

    def write_resources_of_service_in_region(
            self, service_name: str, exclude_resources: List[str] = None,
            region_name: str = None, client_args: dict = None) -> None:
        """Write all AWS resources in this region in this service to storage.

        Cleans up any resources in the StorageConnector that no longer exist.

        Arguments:
            service_name (str): The name of the service to write resources for (e.g. ``'ec2'``)
            exclude_resources (list): A list of resource names to exclude (e.g. ``['instance']``)
            region_name (str): The name of the region to get resources from
                (defaults to session default if not specified)
            client_args (dict): Arguments to pass into the boto3 client.
                See: :meth:`boto3.session.Session.client`
        """
        client_args = client_args.copy() if client_args else {}
        if region_name:
            client_args['region_name'] = region_name
        if 'region_name' not in client_args:
            client_args['region_name'] = self.boto3_session.region_name

        logger.info("Writing all %s resources in %s", service_name, client_args['region_name'])
        exclude_resources = exclude_resources or []
        service_map = self.global_service_maps.get_global_service_map(service_name=service_name)
        has_global_resources_in_this_region = service_map.has_global_resources_in_region(client_args['region_name'])
        if not has_global_resources_in_this_region and not service_map.has_regional_resources:
            logger.info("Skipping %s as it does not have resources in %s",
                        service_name, client_args['region_name'])
            return

        for resource_type in self.boto3_interface.get_service_resource_types(service_name=service_name):
            if resource_type in exclude_resources:
                logger.info('Skipping %s as per exclude_resources', resource_type)
                continue
            self.write_resources_of_type_in_region(
                service_name=service_name,
                resource_type=resource_type,
                client_args=client_args
            )

    def write_resources_of_type_in_region(
            self, service_name: str, resource_type: str = None,
            region_name: str = None, client_args: dict = None) -> None:
        """Write all AWS resources in this region in this service to storage.

        Cleans up any resources in the StorageConnector that no longer exist.

        Arguments:
            service_name (str): The name of the service to write resources for (e.g. ``'ec2'``)
            resource_type (str): The name of the type of the resource to write (e.g. ``'instance'``)
            region_name (str): The name of the region to get resources from
                (defaults to session default if not specified)
            client_args (dict): Arguments to pass into the boto3 client.
                See: :meth:`boto3.session.Session.client`
        """
        client_args = client_args or {
            'region_name': region_name or self.boto3_session.region_name
        }
        logger.info('--> Fetching %s %s from %s', service_name, resource_type, client_args['region_name'])
        resources = self.boto3_interface.get_resources_of_type(service_name, resource_type, client_args)
        urns = []
        for boto3_resource in resources:
            urn = self._get_resource_urn(boto3_resource, client_args['region_name'])
            if not self._should_write_resource_in_region(urn, client_args['region_name']):
                continue
            self.storage_connector.write_resource(urn, boto3_resource)
            urns.append(urn)
        self._clean_resources_in_region(
            service_name, resource_type, client_args['region_name'], urns)

    def _clean_resources_in_region(
            self, service_name: str, resource_type: str, region_name: str, current_urns: List[AwsUrn]) -> None:
        """Remove all resources of this type in this region which no longer exist."""
        self.storage_connector.delete_resource_of_type_in_account_region(
            service=service_name,
            resource_type=resource_type,
            account_id=self.account_id,
            region=region_name,
            urns_to_keep=current_urns
        )

    def _should_write_resource_in_region(self, urn: AwsUrn, write_region: str) -> bool:
        """Return True if this is a resource we should write in this region and log the result."""
        if urn.region != write_region:
            logger.debug(
                "Skipping %s %s in %s because it is not in %s",
                urn.resource_type,
                urn.resource_id,
                urn.region,
                write_region
            )
            return False
        return True

    def write_resource_attributes(
            self, exclude_resources: List[str] = None, client_args: dict = None) -> None:
        """Write all AWS resource attributes in this account from all regions and all services to storage.

        Arguments:
            exclude_resources (list): A list of resource names to exclude (e.g. ``['instance']``)
            client_args (dict): Arguments to pass into the boto3 client.
                See: :meth:`boto3.session.Session.client`
        """
        logger.info('Writing resource attributes in all regions')
        for region_name in self.enabled_regions:
            self.write_resource_attributes_in_region(
                region_name=region_name,
                exclude_resources=exclude_resources,
                client_args=client_args
            )

    def write_resource_attributes_in_region(
            self, exclude_resources: List[str] = None, region_name: str = None, client_args: dict = None) -> None:
        """Write all AWS resource attributes in this account in this region to storage.

        These custom resource attribute definitions allow us to fetch resource attributes that are not returned by the
        resource's default describe calls.
        Unlike :meth:`~CloudWanderer.write_resources` and :meth:`~CloudWanderer.write_resources_of_type`
        this method does not clean up stale resource attributes from storage.

        Arguments:
            exclude_resources (list): A list of resources not to write attributes for (e.g. ``['vpc']``)
            region_name (str): The name of the region to get resources from
                (defaults to session default if not specified)
            client_args (dict): Arguments to pass into the boto3 client.
                See: :meth:`boto3.session.Session.client`
        """
        for boto3_service in self.custom_attributes_interface.get_all_resource_services():
            self.write_resource_attributes_of_service_in_region(
                service_name=boto3_service.meta.service_name,
                exclude_resources=exclude_resources,
                client_args=client_args,
                region_name=region_name,
            )

    def write_resource_attributes_of_service_in_region(
            self, service_name: str, exclude_resources: List[str] = None,
            region_name: str = None, client_args: dict = None) -> None:
        """Write all AWS resource attributes in this account in this service to storage.

        These custom resource attribute definitions allow us to fetch resource attributes that are not returned by the
        resource's default describe calls.
        Unlike :meth:`~CloudWanderer.write_resources` and :meth:`~CloudWanderer.write_resources_of_type`
        this method does not clean up stale resource attributes from storage.

        Arguments:
            service_name (str): The name of the service to write the attributes of (e.g. ``'ec2'``)
            exclude_resources (list): A list of resources not to write attributes for (e.g. ``['vpc']``)
            region_name (str): The name of the region to get resources from
                (defaults to session default if not specified)
            client_args (dict): Arguments to pass into the boto3 client.
                See: :meth:`boto3.session.Session.client`
        """
        client_args = client_args or {
            'region_name': region_name or self.boto3_session.region_name
        }
        logger.info("Writing all %s resource attributes in %s", service_name, client_args['region_name'])
        exclude_resources = exclude_resources or []
        service_map = self.global_service_maps.get_global_service_map(service_name=service_name)
        has_gobal_resources_in_this_region = service_map.has_global_resources_in_region(client_args['region_name'])
        if not has_gobal_resources_in_this_region and not service_map.has_regional_resources:
            logger.info("Skipping %s as it does not have resources in %s",
                        service_name, client_args['region_name'])
            return
        exclude_resources = exclude_resources or []
        for resource_type in self.custom_attributes_interface.get_service_resource_types(service_name):
            if resource_type in exclude_resources:
                logger.info('Skipping %s as per exclude_resources', resource_type)
                continue
            self.write_resource_attributes_of_type_in_region(
                service_name=service_name,
                resource_type=resource_type,
                client_args=client_args
            )

    def write_resource_attributes_of_type_in_region(
            self, service_name: str, resource_type: str, region_name: str = None, client_args: dict = None) -> None:
        """Write all AWS resource attributes in this account of this resource type to storage.

        These custom resource attribute definitions allow us to fetch resource attributes that are not returned by the
        resource's default describe calls.

        Arguments:
            service_name (str): The name of the service to write the attributes of (e.g. ``ec2``)
            resource_type (str): The type of resource to write the attributes of (e.g. ``instance``)
            region_name (str): The name of the region to get resources from
                (defaults to session default if not specified)
            client_args (dict): Arguments to pass into the boto3 client.
                See: :meth:`boto3.session.Session.client`
        """
        client_args = client_args or {
            'region_name': region_name or self.boto3_session.region_name
        }
        logger.info('--> Fetching %s %s in %s', service_name, resource_type, client_args['region_name'])
        resource_attributes = self.custom_attributes_interface.get_resources_of_type(
            service_name=service_name,
            resource_type=resource_type,
            client_args=client_args
        )
        for resource_attribute in resource_attributes:
            urn = self._get_resource_urn(resource_attribute, client_args['region_name'])
            self.storage_connector.write_resource_attribute(
                urn=urn,
                resource_attribute=resource_attribute,
                attribute_type=xform_name(resource_attribute.meta.resource_model.name)
            )

    def read_resource_of_type(self, service: str, resource_type: str) -> List['CloudWandererResource']:
        """Return all resources of type.

        Arguments:
            service (str): Service name (e.g. ``'ec2'``)
            resource_type (str): Resource Type (e.g. ``'instance'``)
        """
        return self.storage_connector.read_resource_of_type(service, resource_type)

    def read_resource(self, urn: AwsUrn) -> List['CloudWandererResource']:
        """Return a specific resource by its urn from storage.

        Either use this to manually inflate the :class:`~.CloudWandererResource` passsed back by other read methods
        or build your own :class:`~.aws_urn.AwsUrn` to query a resource you already know exists.

        Args:
            urn (cloudwanderer.aws_urn.AwsUrn): The :class:`~cloudwanderer.aws_urn.AwsUrn` of the resource to retrieve.
        """
        try:
            return next(self.storage_connector.read_resource(urn))
        except StopIteration:
            return None

    def read_all_resources_in_account(self, account_id: str) -> List['CloudWandererResource']:
        """Return all resources in the provided AWS Account from storage.

        Arguments:
            account_id (str): The account id in which to look for resources.
        """
        return self.storage_connector.read_all_resources_in_account(account_id)

    def read_resource_of_type_in_account(
            self, service: str, resource_type: str, account_id: str) -> List['CloudWandererResource']:
        """Return all resources of this type in the provided AWS Account from storage.

        Arguments:
            service (str): Service name (e.g. ``'ec2'``)
            resource_type (str): Resource Type (e.g. ``'instance'``)
            account_id (str): The account id in which to look for resources.
        """
        return self.storage_connector.read_resource_of_type_in_account(service, resource_type, account_id)

    @property
    def account_id(self) -> str:
        """Return the AWS Account ID our boto3 session is authenticated against."""
        if self._account_id is None:
            sts = self.boto3_session.client('sts')
            self._account_id = sts.get_caller_identity()['Account']
        return self._account_id

    @property
    def enabled_regions(self) -> List[str]:
        """Return a list of enabled regions in this account."""
        if not self._enabled_regions:
            regions = self.boto3_session.client('ec2').describe_regions()['Regions']
            self._enabled_regions = [
                region['RegionName']
                for region in regions
                if region['OptInStatus'] != 'not-opted-in'
            ]
        return self._enabled_regions

    def _get_resource_urn(self, resource: ResourceModel, region_name: str) -> 'AwsUrn':
        id_member_name = resource.meta.resource_model.identifiers[0].name
        resource_id = getattr(resource, id_member_name)
        if resource_id.startswith('arn:'):
            resource_id = ''.join(resource_id.split(':')[5:])
        global_service_map = self.global_service_maps.get_global_service_map(resource.meta.service_name)
        return AwsUrn(
            account_id=self.account_id,
            region=global_service_map.get_resource_region(resource, region_name),
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

    def __init__(self, urn: AwsUrn, resource_data: dict, resource_attributes: List[dict] = None) -> None:
        """Initialise the resource."""
        self.urn = urn
        self.cloudwanderer_metadata = ResourceMetadata(
            resource_data=resource_data,
            resource_attributes=resource_attributes or []
        )
        self._set_attrs()

    @property
    def _clean_resource(self) -> dict:
        return {
            key: value
            for key, value in self.metadata.items()
            if not key.startswith('_')
        }

    def _set_attrs(self) -> None:
        for key, value in self.cloudwanderer_metadata.resource_data.items():
            setattr(
                self,
                xform_name(key),
                value
            )

    def __repr__(self) -> str:
        """Return a code representation of this resource."""
        return str(
            f"{self.__class__.__name__}("
            f"urn={repr(self.urn)}, "
            f"resource_data={self.cloudwanderer_metadata.resource_data}, "
            f"resource_attributes={self.cloudwanderer_metadata.resource_attributes})"
        )

    def __str__(self) -> str:
        """Return the string representation of this Resource."""
        return repr(self)
