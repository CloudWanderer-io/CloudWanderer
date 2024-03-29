"""Allows CloudWanderer to store resources in memory."""
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Iterator, Optional

from ..cloud_wanderer_resource import CloudWandererResource
from ..urn import URN
from ..utils import standardise_data_types
from .base_connector import BaseStorageConnector

logger = logging.getLogger(__name__)


class MemoryStorageConnector(BaseStorageConnector):
    """Storage connector to place data in memory.

    Useful for testing.

    Example:
        >>> import cloudwanderer
        >>> cloud_wanderer = cloudwanderer.CloudWanderer(
        ...     storage_connectors=[cloudwanderer.storage_connectors.MemoryStorageConnector()]
        ... )

    """

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}

    def init(self) -> None:
        """Do nothing. Dummy method to fulfil interface requirements."""

    def open(self) -> None:
        """Do nothing. Dummy method to fulfil interface requirements."""

    def close(self) -> None:
        """Do nothing. Dummy method to fulfil interface requirements."""

    def read_resource(self, urn: URN) -> Optional[CloudWandererResource]:
        try:
            return memory_item_to_resource(urn, self._data[str(urn)], loader=self.read_resource)
        except KeyError:
            return None

    def read_resources(
        self,
        cloud_name: str = None,
        account_id: str = None,
        region: str = None,
        service: str = None,
        resource_type: str = None,
        urn: URN = None,
    ) -> Iterator["CloudWandererResource"]:
        for urn_str, items in self._data.items():
            item_urn = URN.from_string(urn_str)
            if urn is not None:
                if item_urn == urn:
                    yield memory_item_to_resource(item_urn, items, loader=self.read_resource)
                continue
            if self._urn_matches_kwargs(
                item_urn,
                cloud_name=cloud_name,
                account_id=account_id,
                region=region,
                service=service,
                resource_type=resource_type,
            ):
                yield memory_item_to_resource(item_urn, items, loader=self.read_resource)

    def _urn_matches_kwargs(self, urn: URN, **kwargs) -> bool:
        filter_items = ("cloud_name", "account_id", "region", "service", "resource_type")
        for item in filter_items:
            if kwargs.get(item) is not None and getattr(urn, item) != kwargs[item]:
                return False
        return True

    def read_all(self) -> Iterator[dict]:
        """Return the raw dictionaries stored in memory."""
        for urn_str, items in self._data.items():
            for item_type, item in items.items():
                item_dict = item if isinstance(item, dict) else {"value": item}
                yield {
                    **{
                        "urn": urn_str,
                        "attr": item_type,
                    },
                    **item_dict,
                }

    def write_resource(self, resource: CloudWandererResource) -> None:
        self._data[str(resource.urn)] = self._data.get(str(resource.urn), {})
        self._data[str(resource.urn)]["BaseResource"] = standardise_data_types(
            resource.cloudwanderer_metadata.resource_data
        )
        self._data[str(resource.urn)]["ParentUrn"] = resource.parent_urn
        self._data[str(resource.urn)]["DependentResourceUrns"] = resource.dependent_resource_urns

    def delete_resource(self, urn: URN) -> None:
        try:
            del self._data[str(urn)]
        except KeyError:
            pass
        subresources_to_delete = set()
        for subresource_urn, resource_dict in self._data.items():
            if resource_dict.get("ParentUrn") == urn:
                subresources_to_delete.add(subresource_urn)
        for subresource_urn in subresources_to_delete:
            del self._data[subresource_urn]

    def delete_resource_of_type_in_account_region(
        self,
        cloud_name: str,
        service: str,
        resource_type: str,
        account_id: str,
        region: str,
        cutoff: Optional[datetime],
    ) -> None:
        urns_to_delete = []
        for urn_str, items in self._data.items():
            urn = URN.from_string(urn_str)
            if urn.cloud_name != cloud_name:
                continue
            if urn.service != service:
                continue
            if urn.account_id != account_id:
                continue
            if urn.resource_type != resource_type:
                continue
            if urn.region != region:
                continue
            resource = memory_item_to_resource(urn, items)
            if cutoff and resource.discovery_time >= cutoff:
                continue
            urns_to_delete.append(urn)
        for urn in urns_to_delete:
            del self._data[str(urn)]

    def __repr__(self) -> str:
        """Return an instantiable string representation of this object."""
        return f"{self.__class__.__name__}()"

    def __str__(self) -> str:
        """Return a string representation of this object."""
        return f"<{self.__class__.__name__}>"


def memory_item_to_resource(urn: URN, items: Dict[str, Any] = None, loader: Callable = None) -> CloudWandererResource:
    """Convert a resource and its attributes to a CloudWandererResource.

    Arguments:
        urn (URN): The URN of the resource.
        items (dict): The dictionary of items stored under this URN. (e.g. BaseResource)
        loader (Callable): The method which can be used to fulfil the :meth:`CloudWandererResource.load`

    """
    items = items or {}
    base_resource: Dict[str, Any] = next(
        iter(resource for item_type, resource in items.items() if item_type == "BaseResource"), {}
    )

    return CloudWandererResource(
        urn=urn,
        dependent_resource_urns=items.get("DependentResourceUrns"),
        resource_data=base_resource,
        parent_urn=items.get("ParentUrn"),
        loader=loader,
    )
