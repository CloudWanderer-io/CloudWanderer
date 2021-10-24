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
    URN(cloud_name='aws', account_id='111111111111', region='eu-west-2', \
service='iam', resource_type='vpc', resource_id_parts=['vpc-11111111'])

"""
import re
from typing import Any, Generator, List, Optional, Tuple


class PartialUrn:
    """A partially specified URN.

    Useful for matching unknown or multiple URNs.
    """

    cloud_name: Optional[str]
    account_id: Optional[str]
    region: Optional[str]
    service: Optional[str]
    resource_type: Optional[str]
    resource_id_parts: List[str]

    def __init__(
        self,
        cloud_name: Optional[str] = None,
        account_id: Optional[str] = None,
        region: Optional[str] = None,
        service: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id_parts: Optional[List[str]] = None,
    ) -> None:
        self.cloud_name = cloud_name
        self.account_id = account_id
        self.region = region
        self.service = service
        self.resource_type = resource_type
        self.resource_id_parts: List[str] = resource_id_parts or []
        self.resource_id = "/".join(self.escape_id(id_part) or "" for id_part in self.resource_id_parts)

    def copy(
        self,
        cloud_name: Optional[str] = None,
        account_id: Optional[str] = None,
        region: Optional[str] = None,
        service: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id_parts: Optional[List[str]] = None,
    ) -> "PartialUrn":
        return PartialUrn(
            cloud_name=cloud_name or self.cloud_name,
            account_id=account_id or self.account_id,
            region=region or self.region,
            service=service or self.service,
            resource_type=resource_type or self.resource_type,
            resource_id_parts=resource_id_parts or self.resource_id_parts,
        )

    @property
    def is_partial(self) -> bool:
        for value in self.__dict__.values():
            if value == "unknown":
                return True
        return False

    @property
    def is_dependent_resource(self) -> bool:
        if not self.resource_id_parts:
            raise ValueError(
                "Cannot determine whether this PartialURN is dependent because it has no resource id parts"
            )
        return len(self.resource_id_parts) > 1

    @property
    def cloud_service_resource_label(self) -> str:
        """Return the cloud service resource label (e.g. ``aws_iam_role``).

        Raises:
            ValueError: If we do not have sufficient information to generate a label
        """
        if (
            not isinstance(self.cloud_name, str)
            or not isinstance(self.service, str)
            or not isinstance(self.resource_type, str)
        ):
            raise ValueError(
                "Cannot determine this PartialURN's "
                "cloud_service_resource as it is missing one of the required attributes"
            )
        return "_".join([self.cloud_name, self.service, self.resource_type]).lower()

    @staticmethod
    def unescape_id(escaped_id: Optional[str]) -> Optional[str]:
        """Return an unescaped ID with the forward slashes unescaped.

        Arguments:
            escaped_id: The id to unescape.
        """
        if escaped_id is None:
            return None
        return re.sub(r"\\(/|:)", r"\1", escaped_id)

    @staticmethod
    def escape_id(unescaped_id: Optional[str]) -> Optional[str]:
        """Return an escaped ID with the forward slashes escaped.

        Arguments:
            unescaped_id: The id to escape.
        """
        if unescaped_id is None:
            return None
        if not isinstance(unescaped_id, str):
            unescaped_id = str(unescaped_id)
        return re.sub(r"(?<!\\)(/|:)", r"\\\1", unescaped_id)

    def __str__(self) -> str:
        """Return a string representation of the URN."""
        base = ":".join(
            [
                str(part or "unknown")
                for part in ["urn", self.cloud_name, self.account_id, self.region, self.service, self.resource_type]
            ]
        )
        return f"{base}:{self.resource_id}"

    def __repr__(self) -> str:
        """Return a class representation of the URN."""
        return str(
            f"{self.__class__.__name__}("
            f"cloud_name='{ self.cloud_name}', "
            f"account_id='{self.account_id}', "
            f"region='{self.region}', "
            f"service='{self.service}', "
            f"resource_type='{self.resource_type}', "
            f"resource_id_parts={self.resource_id_parts})"
        )

    def __eq__(self, other: Any) -> bool:
        """Allow comparison of one URN to another.

        Arguments:
            other (Any): The other object to compare this one with.
        """
        return str(self) == str(other)

    def __iter__(self) -> Generator[Tuple[str, str], None, None]:
        """Allow the URN to be turned into a dict."""
        for attribute_name in vars(self):
            if attribute_name.startswith("_"):
                continue
            yield attribute_name, getattr(self, attribute_name)


class URN(PartialUrn):
    """A dataclass for building and querying AWS URNs."""

    account_id: str
    region: str
    service: str
    resource_type: str
    resource_id: str

    def __init__(
        self,
        account_id: str,
        region: str,
        service: str,
        resource_type: str,
        resource_id_parts: Optional[list] = None,
        cloud_name: str = None,
    ) -> None:
        """Initialise an AWS Urn.

        Arguments:
            account_id: AWS Account ID (e.g. ``111111111111``).
            region: AWS region (e.g. `us-east-1``).
            service: AWS Service (e.g. ``iam``).
            resource_type: AWS Resource Type (e.g. ``role_policy``)
            resource_id_parts: AWS Resource Id (e.g. ``test-role-policy``)
            cloud_name: The name of the cloud this resource exists in (defaults to ``'aws'``)

        Attributes:
            account_id: AWS Account ID (e.g. ``111111111111``).
            region: AWS region (e.g. `us-east-1``).
            service: AWS Service (e.g. ``iam``).
            resource_type: AWS Resource Type (e.g. ``role_policy``)
            resource_id: AWS Resource Id (e.g. ``test-role-policy``)
            resource_id_parts: AWS Resource ID parts (e.g. ``['test-role', 'test-role-policy']``)
            cloud_name: The name of the cloud this resource exists in (defaults to ``'aws'``)

        Raises:
            ValueError: If incorrect values are supplied.
        """
        if not resource_id_parts or not all(resource_id_parts):
            raise ValueError("resource_id or id_parts must be supplied with non empty values")

        super().__init__(
            cloud_name=cloud_name or "aws",
            account_id=account_id,
            region=region,
            service=service,
            resource_type=resource_type,
            resource_id_parts=resource_id_parts,
        )

    @classmethod
    def from_string(cls, urn_string: str) -> "URN":
        """Create an URN Object from an URN string.

        Arguments:
            urn_string (str): The string version of an AWSUrn to convert into an object.

        Returns:
            URN: The instantiated AWS URN.

        Raises:
            ValueError: When no valid resource id found
        """
        parts = re.split(r"(?<!\\):", urn_string)
        try:
            resource_id_parts = re.split(r"(?<!\\)/", parts[6])
        except IndexError:
            raise ValueError("Resource ID must be supplied as the 7th element in a colon separated string")
        return cls(
            account_id=parts[2],
            region=parts[3],
            service=parts[4],
            resource_type=parts[5],
            resource_id_parts=[cls.unescape_id(id_part) for id_part in resource_id_parts],
        )
