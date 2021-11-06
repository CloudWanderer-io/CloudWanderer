"""Exceptions pertaining to the AWS Interface."""


class SecondaryAttributesNotFetchedError(Exception):
    """Secondary attributes have not yet been fetched for this resource. Call fetch_secondary_attributes first."""
