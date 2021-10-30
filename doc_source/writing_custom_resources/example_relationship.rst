Writing a Resource Relationship Definition
============================================


Relationship definitions define how to discover the relationship one resource has with another.  
These are used by :class:`~cloudwanderer.storage_connectors.base_connector.BaseStorageConnector` s which have strong relationship definitions like 
:class:`~cloudwanderer.storage_connectors.GremlinStorageConnector` but not by ones which do not, like :class:`~cloudwanderer.storage_connectors.DynamoDbConnector`.

When to Write a Resource Definition
-------------------------------------------------

You need to write a relationship definition when you want to represent the fact that two resources reference 
each other. For example an :class:`ec2.vpc` has an :class:`ec2.subnet`. This relationship is inherent in the 
AWS resource structure and can be discovered by looking at the :attr:`~boto3:EC2.Client.describe_subnets` payload.

You do not need to write a relationship definition if a resource is a :doc:`dependent resource <example_dependent_resource>` 
as this is already created automatically by CloudWanderer.

Writing the Definition
---------------------------

Let's look at the relationship between an :class:`ec2.vpc` and an :class:`ec2.subnet`.
The :attr:`~boto3:EC2.Client.describe_vpcs` response payload doesn't specify what subnets the vpc has, but the 
:attr:`~boto3:EC2.Client.describe_subnets` payload does.

Specifically we need this bit:

.. code:: json

    {
        "Subnets": [
            {
                "VpcId": "vpc-11111111"
            }
        ]
    }
                

This means we need to go to the subnet resource definition
in ```aws_interface/resource_definitions/ec2/2016-11-15/resources-cw-1.json`` which looks like:

.. code:: json

    "Subnet": {
        "type": "resource"
    }

and add the ``relationships`` key to it.

.. code:: json

   {
        "Subnet": {
            "type": "resource",
            "relationships": [
                {
                    "basePath": "@",
                    "idParts": [
                        {
                            "path": "VpcId"
                        }
                    ],
                    "service": "ec2",
                    "resourceType": "vpc",
                    "regionSource": "sameAsResource",
                    "accountIdSource": "unknown",
                    "direction": "inbound"
                }
            ]
        }
    }

There are a number of keys in the relationship definition, let's go through them one by one.

- ``basePath`` 
    Defines where the relationship starts in the payload. 
    In our case it starts at the very top hence the ``@``, but if it was a one-to-many relationship like an AMI to 
    snapshot mapping (``BlockDeviceMappings[].Ebs``) then it would descend into a key, then iterate over a list, and 
    then descend into another key.
- ``idParts`` 
    Defines the path to the id parts (in our case only the one) relative to the base path.
- ``service`` 
    Statically defines the service name of the resource we are creating a relationship with.
- ``resourceType`` 
    Statically defines the resource type of the resource we are creating a relationship with.
- ``regionSource`` 
    Can be either ``sameAsResource`` or ``unknown`` as it is cast to :class:`~cloudwanderer.models.RelationshipRegionSource`.
    If it is ``sameAsResource`` then whatever region the resource acting as the origin of the relationship (in our case `ec2.subnet`) is in will 
    be what's specified as the region for the resource acting as the partner in their relationship.
    If it is ``unknown`` then it is down to the storage connector to search for the resource based on the remaining information (resource type, id, etc.).
- ``accountIdSource`` 
    Can be either ``sameAsResource`` or ``unknown`` as it is cast to :class:`~cloudwanderer.models.RelationshipAccountIdSource`.
    If it is ``sameAsResource`` then whatever account id the resource acting as the origin of the relationship (in our case :class:`ec2.subnet`) is in will 
    be what's specified as the accoutn id for the resource acting as the partner in their relationship.
    If it is ``unknown`` then it is down to the storage connector to search for the resource based on the remaining information (resource type, id, etc.).
- ``direction`` 
    Can be either ``inbound`` or ``outbound`` as it is cast to :class:`~cloudwanderer.models.RelationshipDirection`
    If the resource acting as the origin of our relationship (:class:`ec2.subnet`) **has** the resource acting as the partner in our relationship (:class:`ec2.vpc`).
    then the resource is considered ``outbound``. In our case it's the other way around, a :class:`ec2.vpc` has a :class:`ec2.subnet` therefore it should be ``inbound``.
 
 Complex ID Parts
 -------------------

 In some cases our job won't be quite so easy. 
 If you have a relationship like the one between :class:`iam.instance_profile` and its :class:`iam.role`, you'll find that the 
 role is not specified in the :attr:`~boto3:IAM.Client.list_instance_profiles` payload as a role name (which is what the id part is for an `iam.role` resource).
 Instead if is an entire ARN, which means you have to split out the ARN into its component parts.

 This is done using the ``regexPattern`` key inside the ``idParts`` definition.

 .. code-block:: json
    :linenos:
    :emphasize-lines: 6


    {
        "basePath": "Roles[]",
        "idParts": [
            {
                "path": "Arn",
                "regexPattern": "[^:]+:[^:]+:[^:]+::(?P<account_id>[^:]+):role.*/(?P<id_part_0>[^:]+)"
            }
        ],
        "service": "iam",
        "resourceType": "role",
        "regionSource": "sameAsResource",
        "accountIdSource": "unknown",
        "direction": "outbound"
    }

This pattern works on the concept of matching groups, which you use to capture the important components of an id from another string.

The supported matching groups are:

 - ``cloud_name``
 - ``account_id``
 - ``region``
 - ``service``
 - ``resource_type``
 - ``id_part_<n>``

You can try this out for yourself by going to `regex101 <https://regex101.com>`__ and putting the pattern in the Regular Expression field 
and an example arn like ``arn:aws:iam::123456789012:role/test-role`` (don't forget to select the flavor of 'Python' from the options on the left).

Testing
-------------

Provided your :doc:`custom resource <example_resource>` already has tests, you should just be able to run the tests with
``pytest tests/integration/custom_resources/`` and your previous ``expectedResult`` should now fail due to a new relationship being added.

If this is not the case, check that the ``idPart`` ``path`` your relationship specification is using actually exists in your test data.
