"""CloudWanderer's Exceptions."""


class BadUrnRegion(Exception):
    """Raised when an URN is passed to get_resource with a region that is not possible."""


class BadUrnAccountId(Exception):
    """Raised when an URN is passed to get_resource with an account other than the one the session is for."""


class BadUrnSubResource(Exception):
    """Raised when an URN for a subresource is passed to get resource."""


class GlobalServiceResourceMappingNotFound(Exception):
    """Global Service Resource Mapping not Found."""


class ResourceActionDoesNotExist(Exception):
    """Resource does not exist on this service as supported by CloudWanderer."""


class ResourceNotFound(Exception):
    """Requested resource was not found."""


class BadRequest(Exception):
    """The Cloud API returned a Bad Request Error.

    For some services for some clouds this is the same as a ResourceNotFound error.
    """
