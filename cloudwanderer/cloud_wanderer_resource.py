"""Standardised dataclasses for returning resources from storage."""

import datetime
import logging
from typing import Any, Callable, Generator, List, Optional, Tuple, Union

from botocore import xform_name

from .models import Relationship  # type: ignore
from .urn import URN, PartialUrn

logger = logging.getLogger(__name__)


class ResourceMetadata:
    """Metadata for a :class:`CloudWandererResource`.

    Contains the original dictionaries of the resource and its attributes.

    Attributes:
        resource_data (dict):
            The raw dictionary representation of the Resource.
    """

    def __init__(self, resource_data: dict) -> None:
        """Initialise the data class.

        Arguments:
            resource_data (dict):
                The raw dictionary representation of the Resource.
        """
        self.resource_data = resource_data

    def __iter__(self) -> Generator[Tuple[str, Any], None, None]:
        """Allow this object to be converted to a dictionary."""
        yield from self.resource_data.items()


class CloudWandererResource:
    """A simple representation of a resource that prevents any storage metadata polluting the resource dictionary.

    This can be a resource, or a dependent resource.
    A dependent resource in CloudWanderer is a resource which does not have a unique identifier of its own and depends
    upon its parent for its identity.

    Attributes:
        urn: The URN of the resource.
        dependent_resource_urns: The URNs of this resource's dependent resources (e.g. role_policies for a role).
        relationships: The PartialURNs of resources that are related to this one.
        parent_urn: The URN of this resource's parent (only exists if this is a dependent resource).
        cloudwanderer_metadata (ResourceMetadata): The metadata of this resource (including attributes).
    """

    def __init__(
        self,
        urn: Union[URN, PartialUrn],
        resource_data: dict,
        relationships: List[Relationship] = None,
        loader: Optional[Callable] = None,
        dependent_resource_urns: List[URN] = None,
        parent_urn: URN = None,
        discovery_time: datetime.datetime = None,
    ) -> None:
        """Initialise the resource.

        Arguments:
            urn: The URN of the resource.
            resource_data: The dictionary containing the raw data about this resource.
            relationships: The relationships this resource has with other resources.
            loader: The method which can be used to fulfil the :meth:`CloudWandererResource.load`.
            dependent_resource_urns: The URNs of the dependent resources of this resource.
            parent_urn: The URN of the resource's parent resource.
            discovery_time: The time the resource was discovered.
        """
        self.urn = urn
        self.relationships = relationships or []
        self.dependent_resource_urns = dependent_resource_urns or []
        self.parent_urn = parent_urn
        self.cloudwanderer_metadata = ResourceMetadata(resource_data=resource_data or {})
        self.discovery_time = discovery_time or datetime.datetime.now()

        self._loader = loader
        self._set_resource_data_attrs()

    def load(self) -> None:
        """Inflate this resource with all data from the original storage connector it was spawned from.

        Raises:
            ValueError: Occurs if the storage connector loader isn't populated or the resource no longer exists
                in the StorageConnector's storage.
        """
        if self._loader is None:
            raise ValueError(f"Could not inflate {self}, storage connector loader not populated")
        updated_resource = self._loader(urn=self.urn)
        if updated_resource is None:
            raise ValueError(f"Could not inflate {self}, does not exist in storage")
            return
        self.cloudwanderer_metadata = updated_resource.cloudwanderer_metadata
        self._set_resource_data_attrs()

    @property
    def is_inflated(self) -> bool:
        """Return whether this resource has all the attributes from storage."""
        return bool([key for key in self.cloudwanderer_metadata.resource_data if not key.startswith("_")])

    @property
    def is_dependent_resource(self) -> bool:
        return bool(self.parent_urn)

    def _set_resource_data_attrs(self) -> None:
        for key, value in self.cloudwanderer_metadata.resource_data.items():
            if key.startswith("_"):
                continue
            setattr(self, xform_name(key), value)

    def __repr__(self) -> str:
        """Return a code representation of this resource."""
        return str(
            f"{self.__class__.__name__}("
            f"urn={repr(self.urn)}, "
            f"dependent_resource_urns={repr(self.dependent_resource_urns)}, "
            f"resource_data={self.cloudwanderer_metadata.resource_data})"
        )

    def __str__(self) -> str:
        """Return the string representation of this Resource."""
        return repr(self)

    def __eq__(self, other) -> bool:
        """Return the equality or not of the compared object.

        Arguments:
            other: The resource to compare our equality against.
        """
        return repr(self) == repr(other)

    def __iter__(self) -> Generator[Tuple[str, Any], None, None]:
        """Allow this object to be converted to a dictionary."""
        for attribute_name in vars(self):
            if attribute_name.startswith("_"):
                continue
            value = getattr(self, attribute_name)
            if isinstance(value, ResourceMetadata):
                value = dict(value)
            yield attribute_name, value
