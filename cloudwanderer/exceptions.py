"""CloudWanderer's Exceptions."""


class BadUrnRegion(Exception):
    """Raised when an URN is passed to get_resource with a region that is not possible."""


class BadUrnAccountId(Exception):
    """Raised when an URN is passed to get_resource with an account other than the one the session is for."""


class BadUrnSubResource(Exception):
    """Raised when an URN for a subresource is passed to get resource."""


class GlobalServiceResourceMappingNotFound(Exception):
    """Global Service Resource Mapping not Found."""
