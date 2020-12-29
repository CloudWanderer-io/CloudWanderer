"""Standardised dataclasses for returning resources from storage."""
from typing import Callable, List
from collections import namedtuple
import logging
import jmespath
from botocore import xform_name
from .aws_urn import AwsUrn
logger = logging.getLogger(__name__)


class ResourceMetadata(namedtuple('ResourceMetadata', ['resource_data', 'secondary_attributes'])):
    """Metadata for a :class:`CloudWandererResource`.

    Contains the original dictionaries of the resource and its attributes.

    Attributes:
        resource_data (dict): The raw dictionary representation of the Resource.
        secondary_attributes (list): the list of raw dictionary representation of the Resource's secondary attributes.
    """


class CloudWandererResource():
    """A simple representation of a resource that prevents any storage metadata polluting the resource dictionary.

    Use ``dict(my_resource_dict)`` to convert this object into a dictionary that
    contains *only* the resource's metadata.

    Attributes:
        urn (cloudwanderer.aws_urn.AwsUrn): The AWS URN of the resource.
        metadata (dict): The original storage representation of the resource as it was passed in.
    """

    def __init__(self, urn: AwsUrn, resource_data: dict,
                 secondary_attributes: List[dict] = None, loader: Callable = None) -> None:
        """Initialise the resource."""
        self.urn = urn
        self.cloudwanderer_metadata = ResourceMetadata(
            resource_data=resource_data,
            secondary_attributes=secondary_attributes or []
        )
        self._loader = loader
        self._set_resource_data_attrs()
        self._set_secondary_attribute_attrs()

    def load(self) -> None:
        """Inflate this resource with all data from the original storage connector it was spawned from.."""
        if self._loader is None:
            logger.error('Could not inflate %s, storage connector loader not populated', self)
            return
        updated_resource = self._loader(urn=self.urn)
        if updated_resource is None:
            logger.error('Could not inflate %s, does not exist in storage', self)
            return
        self.cloudwanderer_metadata = updated_resource.cloudwanderer_metadata
        self._set_resource_data_attrs()
        self._set_secondary_attribute_attrs()

    def get_secondary_attribute(self, jmes_path: str) -> None:
        """Get an attribute not returned in the resource's standard ``describe`` method.

        Arguments:
            jmes_path (str): A JMES path to the secondary attribute. e.g. ``[].EnableDnsSupport.Value``
        """
        return jmespath.search(jmes_path, self.cloudwanderer_metadata.secondary_attributes)

    @property
    def _clean_resource(self) -> dict:
        return {
            key: value
            for key, value in self.metadata.items()
            if not key.startswith('_')
        }

    def _set_resource_data_attrs(self) -> None:
        for key, value in self.cloudwanderer_metadata.resource_data.items():
            if key.startswith('_'):
                continue
            setattr(self, xform_name(key), value)

    def _set_secondary_attribute_attrs(self) -> None:
        for attribute in self.cloudwanderer_metadata.secondary_attributes:
            for key, value in attribute.items():
                if key.startswith('_'):
                    continue
                if xform_name(key) in dir(self):
                    logger.warning(
                        str(
                            '%s is already an attribute on %s, '
                            '%s will only be accessible via get_secondary_attributes'
                        ),
                        key, self.__class__.__name__, key
                    )
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
