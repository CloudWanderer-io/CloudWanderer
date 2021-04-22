"""CloudWanderer's Exceptions."""


class BadUrnRegionError(Exception):
    """Raised when an URN is passed to get_resource with a region that is not possible."""


class BadUrnIdentifiersError(Exception):
    """Raised when an URN has the wrong number or type of identifier parts."""


class BadUrnAccountIdError(Exception):
    """Raised when an URN is passed to get_resource with an account other than the one the session is for."""


class BadUrnSubResourceError(Exception):
    """Raised when an URN for a subresource is passed to get resource."""


class GlobalServiceResourceMappingNotFoundError(Exception):
    """Global Service Resource Mapping not Found."""


class ResourceActionDoesNotExistError(Exception):
    """Resource does not exist on this service as supported by CloudWanderer."""


class ResourceNotFoundError(Exception):
    """Requested resource was not found."""


class BadRequestError(Exception):
    """The Cloud API returned a Bad Request Error.

    For some services for some clouds this is the same as a ResourceNotFoundError error.
    """


class UnsupportedResourceTypeError(Exception):
    """The resource type in question is not supported for this operation."""


class UnsupportedServiceError(Exception):
    """The service in question is not supported for this operation."""


class BadServiceMapError(Exception):
    """There was an insconsistency in the service map for this operation."""
