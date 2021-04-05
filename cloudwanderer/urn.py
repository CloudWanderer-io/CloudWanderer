"""A dataclass for building and querying AWS URNs.

AWS URNs are a standardised string format (name borrowed from Pulumi) which provide all the information required to
find a resource in AWS, whereas AWS ARNs do not always provide this information.

.. code-block ::

    # Format
    'urn:aws:<account_id>:<region>:<service>:<resource_type>:<resource_id>'
    # e.g.
    'urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111'

Example:
    >>> from cloudwanderer import URN
    >>> URN.from_string('urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111')
    URN(account_id='111111111111', region='eu-west-2', service='ec2', \
resource_type='vpc', resource_id='vpc-11111111')

"""
from typing import Any


class URN:
    """A dataclass for building and querying AWS URNs."""

    def __init__(
        self,
        account_id: str,
        region: str,
        service: str,
        resource_type: str,
        resource_id: str,
        cloud_name: str = None,
    ) -> None:
        """Initialise an AWS Urn.

        Arguments:
            account_id (str): AWS Account ID (e.g. ``111111111111``).
            region (str): AWS region (e.g. ``eu-west-1``).
            service (str): AWS Service (e.g. ``ec2``).
            resource_type (str): AWS Resource Type (e.g. ``instance``)
            resource_id (str): AWS Resource Id (e.g. ``i-11111111``)
            cloud_name (str): The name of the cloud this resource exists in (defaults to ``'aws'``)

        Attributes:
            account_id (str): AWS Account ID (e.g. ``111111111111``).
            region (str): AWS region (e.g. ``eu-west-1``).
            service (str): AWS Service (e.g. ``ec2``).
            resource_type (str): AWS Resource Type (e.g. ``instance``)
            resource_id (str): AWS Resource Id (e.g. ``i-11111111``)
            cloud_name (str): The name of the cloud this resource exists in (defaults to ``'aws'``)
        """
        self.cloud_name = cloud_name or "aws"
        self.account_id = account_id
        self.region = region
        self.service = service
        self.resource_type = resource_type
        self.resource_id = resource_id

    @classmethod
    def from_string(cls, urn_string: str) -> "URN":
        """Create an URN Object from an URN string.

        Arguments:
            urn_string (str): The string version of an AWSUrn to convert into an object.

        Returns:
            URN: The instantiated AWS URN.
        """
        parts = urn_string.split(":")
        return cls(account_id=parts[2], region=parts[3], service=parts[4], resource_type=parts[5], resource_id=parts[6])

    @property
    def is_subresource(self) -> bool:
        """Return whether or not this urn pertains to a subresource.

        A subresource is a resource which does not have its own cloud provider identity and is only  accessible
        by referring to a parent resource.
        """
        return "/" in self.resource_id

    @property
    def parent_resource_id(self) -> str:
        """Return the id of the parent resource if there is one."""
        if not self.is_subresource:
            return ""
        return self.resource_id.split("/")[0]

    @property
    def subresource_id(self) -> str:
        """Return the ID of the child resource if there is one."""
        if not self.is_subresource:
            return ""
        return self.resource_id.split("/")[1]

    def __eq__(self, other: Any) -> bool:
        """Allow comparison of one URN to another.

        Arguments:
            other (Any): The other object to compare this one with.
        """
        return str(self) == str(other)

    def __repr__(self) -> str:
        """Return a class representation of the URN."""
        return str(
            f"{self.__class__.__name__}("
            f"account_id='{self.account_id}', "
            f"region='{self.region}', "
            f"service='{self.service}', "
            f"resource_type='{self.resource_type}', "
            f"resource_id='{self.resource_id}')"
        )

    def __str__(self) -> str:
        """Return a string representation of the URN."""
        return ":".join(
            [
                "urn",
                self.cloud_name,
                self.account_id,
                self.region,
                self.service,
                self.resource_type,
                self.resource_id,
            ]
        )
