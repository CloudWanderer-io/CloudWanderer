"""Standardised dataclasses for returning resources from storage."""
from typing import Callable, List
import logging
import jmespath
from botocore import xform_name
from .aws_urn import AwsUrn
logger = logging.getLogger(__name__)


class ResourceMetadata:
    """Metadata for a :class:`CloudWandererResource`.

    Contains the original dictionaries of the resource and its attributes.

    Attributes:
        resource_data (dict):
            The raw dictionary representation of the Resource.
        secondary_attributes (list):
            The list of the resource's :class:`SecondaryAttribute` objects.
    """

    def __init__(self, resource_data: dict, secondary_attributes: list) -> None:
        """Initialise the data class.

        Arguments:
            resource_data (dict):
                The raw dictionary representation of the Resource.
            secondary_attributes (list):
                The list of the resource's :class:`SecondaryAttribute` objects.
        """
        self.resource_data = resource_data
        self.secondary_attributes = secondary_attributes


class CloudWandererResource():
    """A simple representation of a resource that prevents any storage metadata polluting the resource dictionary.

    Attributes:
        urn (AwsUrn): The URN of the resource.
        cloudwanderer_metadata (ResourceMetadata): The metadata of this resource (including attributes).
    """

    def __init__(self, urn: AwsUrn, resource_data: dict,
                 secondary_attributes: List[dict] = None, loader: Callable = None) -> None:
        """Initialise the resource.

        Arguments:
            urn (AwsUrn): The AWS URN of the resource.
            resource_data (dict): The dictionary containing the raw data about this resource.
            secondary_attributes (List[dict]): A list of secondary attribute raw dictionaries.
            loader (Callable): The method which can be used to fulfil the :meth:`CloudWandererResource.load`.
        """
        self.urn = urn
        self.cloudwanderer_metadata = ResourceMetadata(
            resource_data=resource_data or {},
            secondary_attributes=secondary_attributes or []
        )
        self._loader = loader
        self._set_resource_data_attrs()

    def load(self) -> None:
        """Inflate this resource with all data from the original storage connector it was spawned from.

        Raises:
            ValueError: Occurs if the storage connector loader isn't populated or the resource no longer exists
                in the StorageConnector's storage.
        """
        if self._loader is None:
            raise ValueError(f'Could not inflate {self}, storage connector loader not populated')
        updated_resource = self._loader(urn=self.urn)
        if updated_resource is None:
            raise ValueError(f'Could not inflate {self}, does not exist in storage')
            return
        self.cloudwanderer_metadata = updated_resource.cloudwanderer_metadata
        self._set_resource_data_attrs()

    @property
    def is_inflated(self) -> bool:
        """Return whether this resource has all the attributes from storage."""
        return bool([
            key
            for key in self.cloudwanderer_metadata.resource_data
            if not key.startswith('_')
        ])

    def get_secondary_attribute(self, name: str = None, jmes_path: str = None) -> None:
        """Get an attribute not returned in the resource's standard ``describe`` method.

        Arguments:
            name (str): The name of the secondary attribute (e.g. ``'enable_dns_support``)
            jmes_path (str): A JMES path to the secondary attribute. e.g. ``[].EnableDnsSupport.Value``
        """
        if name is not None:
            return [
                secondary_attr
                for secondary_attr in self.cloudwanderer_metadata.secondary_attributes
                if secondary_attr.name == name
            ]
        return jmespath.search(jmes_path, self.cloudwanderer_metadata.secondary_attributes)

    def _set_resource_data_attrs(self) -> None:
        for key, value in self.cloudwanderer_metadata.resource_data.items():
            if key.startswith('_'):
                continue
            setattr(self, xform_name(key), value)

    def __repr__(self) -> str:
        """Return a code representation of this resource."""
        return str(
            f"{self.__class__.__name__}("
            f"urn={repr(self.urn)}, "
            f"resource_data={self.cloudwanderer_metadata.resource_data}, "
            f"secondary_attributes={self.cloudwanderer_metadata.secondary_attributes})"
        )

    def __str__(self) -> str:
        """Return the string representation of this Resource."""
        return repr(self)


class SecondaryAttribute(dict):
    """Partially formalised SecondaryAttribute for resources.

    Allows us to store unstructured data in a dict-like object while maintaining the
    attribute_name attribute.

    Attributes:
        attribute_name (str): The name of the attribute.
    """

    def __init__(self, name: str, **kwargs) -> None:
        """Initialise the Secondary Attribute.

        Arguments:
            name (str): The name of the attribute
            **kwargs: The attributes keys and values
        """
        super().__init__(**kwargs)
        self.name = name
