Examples
==========================

Getting Started
------------------------------------------


Testing with a local DynamoDB
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`DynamoDB has a Docker Image <https://hub.docker.com/r/amazon/dynamodb-local>`_ that allows you to run a local, persistent DynamoDB.
This provides us with a cheap and easy way to start trying out CloudWanderer.

.. code-block ::

    $ docker run -p 8000:8000 -v $(pwd):/data amazon/dynamodb-local \
        -Djava.library.path=./DynamoDBLocal_lib \
        -jar DynamoDBLocal.jar \
        -sharedDb -dbPath /data/

This starts a DynamoDB docker image on your local machine and tells it to persist data into the current directory in
a shared database file ``shared-local-instance.db``. This allows the data to persist even if you stop the container.

.. doctest ::

    >>> from cloudwanderer.storage_connectors import DynamoDbConnector
    >>> local_storage_connector = DynamoDbConnector(
    ...     endpoint_url='http://localhost:8000'
    ... )

This creates an alternative storage connector that points at your local DynamoDB

.. doctest ::

    >>> wanderer = cloudwanderer.CloudWanderer(storage_connectors=[local_storage_connector])

This passes the storage connector that points at your local DynamoDB into a new wanderer
and now all subsequent CloudWanderer operations will occur against your local DynamoDB!

Testing With the Memory Connector
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you don't mind that your data is thrown away as soon as your ``python`` executable stops you can
test CloudWanderer using the Memory Storage Connector!

.. doctest ::

    >>> import cloudwanderer
    >>> wanderer = cloudwanderer.CloudWanderer(
    ...     storage_connectors=[cloudwanderer.storage_connectors.MemoryStorageConnector()]
    ... )

It's wise to do this in an interactive environment otherwise you may spend an inordinate amount of time re-querying
your AWS environment!

Writing Resources
--------------------

Writing all Resources from all Regions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Writing all :doc:`supported_resources` in all regions is as simple as using the :meth:`~cloudwanderer.cloud_wanderer.CloudWanderer.write_resources` method.

.. doctest ::

    >>> import cloudwanderer
    >>> storage_connector = cloudwanderer.storage_connectors.DynamoDbConnector()
    >>> storage_connector.init()
    >>> wanderer = cloudwanderer.CloudWanderer(storage_connectors=[storage_connector])
    >>> wanderer.write_resources()

In that block we are:

#. Creating a storage connector (in this case DynamoDB)
#. Initialising the storage connector (in this case creating a dynamodb table called ``cloud_wanderer``
#. Creating a wanderer and using :meth:`~cloudwanderer.cloud_wanderer.CloudWanderer.write_resources` to get all resources in all regions.

**Important:** This will create DynamoDB table in your AWS account and write a potentially large number of records to it which may incur some cost.
See earlier examples for how to test against a local DynamoDB or memory.

Writing VPCs from all Regions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Writing VPCs is as simple as passing the ``resource_types`` argument.

.. doctest ::

    >>> wanderer.write_resources(resource_types=['vpcs'])

Excluding Resource Types
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some resource types take a very long time to query (e.g. EC2 Images) and depending on what you're using your data for
may not be worth the time.

.. doctest ::

    >>> wanderer.write_resources(exclude_resources=['ec2:images'])

Writing Resource by URN
^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you're writing an event driven discovery mechanism it can be very useful to be able to update an individual resource
without discovering all of the other resources of that type as well.

.. doctest ::

    >>> from cloudwanderer import URN
    >>> urn = URN(
    ...     account_id="123456789012",
    ...     region="eu-west-2",
    ...     service="ec2",
    ...     resource_type="vpc",
    ...     resource_id="vpc-1111111111",
    ... )

    >>> wanderer.write_resource(urn=urn)

.. warning::

    If the resource is not found it will delete it from your storage connector.


Reading Resources
--------------------

Retrieving all VPCs from all Regions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. doctest ::

    >>> vpcs = storage_connector.read_resources(service='ec2', resource_type='vpc')
    >>> for vpc in vpcs:
    ...     print('vpc_region:', vpc.urn.region)
    ...     vpc.load()
    ...     print('vpc_state: ', vpc.state)
    ...     print('is_default:', vpc.is_default)
    vpc_region: us-east-1
    vpc_state:  available
    is_default: True
    vpc_region: eu-west-2
    vpc_state:  available
    is_default: True


You'll notice here we're calling a property ``urn`` in order to print the region.
:doc:`URNs <reference/urn>` are CloudWanderer's way of uniquely identifying a resource.

You can also see we're printing the vpc's ``state`` and ``is_default`` attributes. It's very important to notice the
:meth:`~cloudwanderer.cloud_wanderer_resource.CloudWandererResource.load` call beforehand which loads the resource's data.
Resources returned from any :meth:`~cloudwanderer.storage_connectors.DynamoDbConnector.read_resources`
call on :class:`~cloudwanderer.storage_connectors.DynamoDbConnector`
are lazily loaded *unless* you specify the ``urn=`` argument.
This is due to the sparsely populated global secondary indexes in the DynamoDB table schema.

Once you've called :meth:`~cloudwanderer.cloud_wanderer_resource.CloudWandererResource.load` you can access any property of
the AWS resource that is returned by its describe method. E.g. for VPCs see :attr:`boto3:EC2.Client.describe_vpcs`.
These attributes are stored as snake_case instead of the APIs camelCase, so ``isDefault`` becomes ``is_default``.

Retrieving Subresources
^^^^^^^^^^^^^^^^^^^^^^^^^

Let's say we want to get a list of role policies. We can start by getting the role

.. doctest ::

    >>> role = next(storage_connector.read_resources(service_name='iam', resource_type='role'))
    >>> role.load()

Next we need to find out what policies are attached, we can either do this with the secondary attributes.

.. doctest ::

    >>> role.get_secondary_attribute('role_inline_policy_attachments')
    [{'PolicyNames': ['test-role-policy'], 'IsTruncated': False}]
    >>> role.get_secondary_attribute(jmes_path='[].PolicyNames[0]')
    ['test-role-policy']

Or we can do it with the :attr:`~cloudwanderer.cloud_wanderer_resource.CloudWandererResource.subresource_urns` property.

.. doctest ::

    >>> role.subresource_urns
    [URN(account_id='123456789012', region='us-east-1', service='iam', resource_type='role_policy', resource_id='test-role/test-role-policy')]

Then we can lookup the inline policy

.. doctest ::

    >>> inline_policy_urn = role.subresource_urns[0]
    >>> inline_policy = storage_connector.read_resource(urn=inline_policy_urn)
    >>> inline_policy.policy_document
    {'Version': '2012-10-17', 'Statement': {'Effect': 'Allow', 'Action': 's3:ListBucket', 'Resource': 'arn:aws:s3:::example_bucket'}}

Reading Secondary Resource Attributes
---------------------------------------

Some resources require additional API calls beyond the initial
``list`` or ``describe`` call to retrieve all their metadata. These are known as Secondary Attributes.
These secondary attributes are written as part of :meth:`~cloudwanderer.cloud_wanderer.CloudWanderer.write_resources`
which we called earlier.

Let's say we want to get the value of ``enableDnsSupport`` for a VPC.
We can get this one of two ways, either by looping over the dictionaries in
:attr:`~cloudwanderer.cloud_wanderer_resource.ResourceMetadata.secondary_attributes` on
:attr:`~cloudwanderer.cloud_wanderer_resource.CloudWandererResource.cloudwanderer_metadata`, or by calling
:meth:`~cloudwanderer.cloud_wanderer_resource.CloudWandererResource.get_secondary_attribute`
with a `JMESPath <https://jmespath.org/>`_.

.. doctest ::

    >>> first_vpc = next(storage_connector.read_resources(service='ec2', resource_type='vpc'))
    >>> first_vpc.load()

    >>> first_vpc.cloudwanderer_metadata.secondary_attributes[0]['EnableDnsSupport']
    {'Value': True}

    >>> first_vpc.get_secondary_attribute(name='vpc_enable_dns_support')
    [{'VpcId': 'vpc-11111111', 'EnableDnsSupport': {'Value': True}}]

    >>> first_vpc.get_secondary_attribute(jmes_path='[].EnableDnsSupport.Value')
    [True]

This special way of accesssing secondary attributes ensures that secondary attributes do not conflict with primary attributes if they have the same name.

Deleting Stale Resources
-------------------------

CloudWanderer deletes resources which no longer exist automatically when you run:
:meth:`~cloudwanderer.cloud_wanderer.CloudWanderer.write_resources`.

This has some complexity with *regional* resources that only exist via global APIs.
For example S3 buckets are regional resources, but S3 is a global *service* so when you call
:meth:`~cloudwanderer.cloud_wanderer.CloudWanderer.write_resources` for S3 buckets
in ``us-east-1`` you will get buckets from **all** regions due to the nature of the API.

This also means that you will delete S3 buckets that no longer exist from **all** regions when you call
:meth:`~cloudwanderer.cloud_wanderer.CloudWanderer.write_resources` in ``us-east-1``.

Individual Resources
^^^^^^^^^^^^^^^^^^^^^

Deleting individual resources (if necessary), can be done by calling
:meth:`~cloudwanderer.storage_connectors.DynamoDbConnector.delete_resource` directly on the storage connector.

e.g.

.. doctest ::

    >>> vpc = next(storage_connector.read_resources(
    ...     service='ec2',
    ...     resource_type='vpc',
    ... ))
    >>> str(vpc.urn)
    'urn:aws:123456789012:us-east-1:ec2:vpc:vpc-11111111'
    >>> storage_connector.delete_resource(urn=vpc.urn)
    >>> vpc = storage_connector.read_resource(
    ...     urn=vpc.urn
    ... )
    >>> print(vpc)
    None
