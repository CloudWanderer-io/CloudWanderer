"""A dataclass for building and querying AWS URNs.

AWS URNs are a standardised string format (name borrowed from Pulumi) which provide all the information required to
find a resource in AWS, whereas AWS ARNs do not always provide this information.

.. code-block ::

    # Format
    'urn:aws:<account_id>:<region>:<service>:<resource_type>:<resource_id>'
    # e.g.
    'urn:aws:111111111111:eu-west-2:iam:vpc:vpc-11111111'

Example:
    >>> from cloudwanderer import URN
    >>> URN.from_string('urn:aws:111111111111:eu-west-2:iam:vpc:vpc-11111111')
    URN(account_id='111111111111', region='eu-west-2', service='iam', \
resource_type='vpc', resource_id='vpc-11111111')

"""
import re
from typing import Any, Optional


class URN:
    """A dataclass for building and querying AWS URNs."""

    def __init__(
        self,
        account_id: str,
        region: str,
        service: str,
        resource_type: str,
        resource_id: str,
        parent_resource_id: Optional[str] = None,
        cloud_name: str = None,
    ) -> None:
        """Initialise an AWS Urn.

        Arguments:
            account_id (str): AWS Account ID (e.g. ``111111111111``).
            region (str): AWS region (e.g. `us-east-1``).
            service (str): AWS Service (e.g. ``iam``).
            resource_type (str): AWS Resource Type (e.g. ``role_policy``)
            resource_id (str): AWS Resource Id (e.g. ``test-role-policy``)
            parent_resource_id: Parent Resource Id (e.g. ``test-role``)
            cloud_name (str): The name of the cloud this resource exists in (defaults to ``'aws'``)

        Attributes:
            account_id: AWS Account ID (e.g. ``111111111111``).
            region: AWS region (e.g. `us-east-1``).
            service: AWS Service (e.g. ``iam``).
            resource_type: AWS Resource Type (e.g. ``role_policy``)
            resource_id: AWS Resource Id (e.g. ``test-role-policy``)
            parent_resource_id: Parent Resource Id (e.g. ``test-role``)
            cloud_name: The name of the cloud this resource exists in (defaults to ``'aws'``)
        """
        self.cloud_name = cloud_name or "aws"
        self.account_id = account_id
        self.region = region
        self.service = service
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.parent_resource_id = parent_resource_id or ""

    @classmethod
    def from_string(cls, urn_string: str) -> "URN":
        """Create an URN Object from an URN string.

        Arguments:
            urn_string (str): The string version of an AWSUrn to convert into an object.

        Returns:
            URN: The instantiated AWS URN.
        """
        parts = urn_string.split(":")
        resource_ids = re.split(r"(?<!\\)/", parts[6])
        if len(resource_ids) == 1:
            resource_id = cls.unescape_id(resource_ids[0])
            parent_resource_id = None
        else:
            resource_id = resource_ids[1]
            parent_resource_id = resource_ids[0]
        return cls(
            account_id=parts[2],
            region=parts[3],
            service=parts[4],
            resource_type=parts[5],
            resource_id=cls.unescape_id(resource_id),
            parent_resource_id=cls.unescape_id(parent_resource_id),
        )

    @staticmethod
    def unescape_id(escaped_id: Optional[str]) -> str:
        """Return an unescaped ID with the forward slashes unescaped.

        Arguments:
            escaped_id: The id to unescape.
        """
        if escaped_id is None:
            return None
        return escaped_id.replace(r"\/", r"/")

    @staticmethod
    def escape_id(unescaped_id: Optional[str]) -> str:
        """Return an escaped ID with the forward slashes escaped.

        Arguments:
            unescaped_id: The id to escape.
        """
        if unescaped_id is None:
            return None
        escape_translation = str.maketrans({"/": r"\/"})
        return unescaped_id.translate(escape_translation)

    @property
    def is_subresource(self) -> bool:
        """Return whether or not this urn pertains to a subresource.

        A subresource is a resource which does not have its own cloud provider identity and is only  accessible
        by referring to a parent resource.
        """
        return bool(self.parent_resource_id)

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
            f"resource_id='{self.resource_id}', "
            f"parent_resource_id='{self.parent_resource_id}')"
        )

    def __str__(self) -> str:
        """Return a string representation of the URN."""
        base = ":".join(["urn", self.cloud_name, self.account_id, self.region, self.service, self.resource_type])
        if self.parent_resource_id:
            return f"{base}:{self.escape_id(self.parent_resource_id)}/{self.escape_id(self.resource_id)}"
        return f"{base}:{self.escape_id(self.resource_id)}"
