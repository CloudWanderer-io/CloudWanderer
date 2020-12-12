"""A dataclass for building and querying AWS URNs."""


class AwsUrn():
    """A dataclass for building and querying AWS URNs.

    Args:
        account_id (str): AWS Account ID (e.g. ``111111111111``).
        region (str): AWS region (e.g. ``eu-west-1``).
        service (str): AWS Service (e.g. ``ec2``).
        resource_type (str): AWS Resource Type (e.g. ``instance``)
        resource_id (str): AWS Resource Id (e.g. ``i-11111111``)
    """

    def __init__(self, account_id, region, service, resource_type, resource_id):
        """Initialise an AWS Urn."""
        self.account_id = account_id
        self.region = region
        self.service = service
        self.resource_type = resource_type
        self.resource_id = resource_id

    @classmethod
    def from_string(cls, urn_string):
        """Create an AwsUrn Object from an AwsUrn string."""
        parts = urn_string.split(':')
        return cls(
            account_id=parts[2],
            region=parts[3],
            service=parts[4],
            resource_type=parts[5],
            resource_id=parts[6]
        )

    def __eq__(self, other):
        """Allow comparison of one AwsUrn to another."""
        return str(self) == str(other)

    def __repr__(self):
        """Return a class representation of the AwsUrn."""
        return str(
            f"{self.__class__.__name__}("
            f"account_id='{self.account_id}', "
            f"region='{self.region}', "
            f"service='{self.service}', "
            f"resource_type='{self.resource_type}', "
            f"resource_id='{self.resource_id}')"
        )

    def __str__(self):
        """Return a string representation of the AwsUrn."""
        return str(
            f"urn:aws:{self.account_id}:{self.region}:{self.service}:{self.resource_type}:{self.resource_id}"
        )
