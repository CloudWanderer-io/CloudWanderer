Examples
==========================

Getting Started
------------------------------------------


Testing with a local DynamoDB
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

DynamoDB has a `Docker Image <https://hub.docker.com/r/amazon/dynamodb-local>` that allows you to run a local DynamoDB in memory.
This provides us with a cheap and easy way to start trying out CloudWanderer.

.. code-block ::

    $  docker run -p 8000:8000 -v $(pwd):/data amazon/dynamodb-local  -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -dbPath  /data/

This starts a DynamoDB docker image on your local machine and tells it to persist data into the current directory in
a shared database file ``shared-local-instance.db``. This allows the data to persist even if you stop the container.

.. doctest ::

    >>> from cloudwanderer.storage_connectors import DynamoDbConnector
    >>> local_storage_connector=DynamoDbConnector(
    ...     endpoint_url='http://localhost:8000'
    ... )

This creates an alternative storage connector that points at your local DynamoDB

.. doctest ::

    >>> wanderer = cloudwanderer.CloudWanderer(storage_connector=local_storage_connector)

This passes the storage connector that points at your local DynamoDB into a new wanderer
and now all subsequent CloudWanderer operations will occur against your local DynamoDB!

Testing With the Memory Connector
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you don't mind that your data is thrown away as soon as your ``python`` executable stops you can
test CloudWanderer using the Memory Storage Connector!

.. doctest ::

    >>> import cloudwanderer
    >>> wanderer = cloudwanderer.CloudWanderer(storage_connector=cloudwanderer.storage_connectors.MemoryStorageConnector())

It's wise to do this in an interactive environment otherwise you may spend an inordinate amount of time re-querying
your AWS environment!

Writing all Resources from all Regions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Writing all :doc:`supported_resources` in all regions is as simple as using the :meth:`~cloudwanderer.CloudWanderer.write_resources` method.

.. doctest ::

    >>> import cloudwanderer
    >>> storage_connector = cloudwanderer.storage_connectors.DynamoDbConnector()
    >>> storage_connector.init()
    >>> wanderer = cloudwanderer.CloudWanderer(storage_connector=storage_connector)
    >>> wanderer.write_resources()

In that block we are:

#. Creating a storage connector (in this case DynamoDB)
#. Initialising the storage connector (in this case creating a dynamodb table called ``cloud_wanderer``
#. Creating a wanderer and using :meth:`~cloudwanderer.CloudWanderer.write_resources` to get all resources in all regions.

**Important:** This will create DynamoDB table in your AWS account and write a potentially large number of records to it which may incur some cost.
See earlier examples for how to test against a local DynamoDB or memory.

Retrieving all VPCs from all Regions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. doctest ::

    >>> vpcs = wanderer.read_resource_of_type(service='ec2', resource_type='vpc')
    >>> for vpc in vpcs:
    ...     print('vpc_region:', vpc.urn.region)
    ...     vpc.load()
    ...     print('vpc_state:', vpc.state)
    ...     print('is_default:', vpc.is_default)
    vpc_region: eu-west-2
    vpc_state: available
    is_default: True
    vpc_region: us-east-1
    vpc_state: available
    is_default: True

You'll notice here we're calling a property ``urn`` in order to print the region.
:doc:`AwsUrns <reference/aws_urn>` are CloudWanderer's way of uniquely identifying a resource.

More expectedly you can see we're printing the vpc's ``state`` attribute and ``is_default`` attribute. However, it's very important to notice the
:meth:`~cloudwanderer.cloud_wanderer.CloudWandererResource.load` call beforehand which loads the resource's data.
Resources returned from any ``read_`` method of the ``DynamoDbConnector`` are lazily loaded *except* for ``read_resource``.
This is due to the sparsely populated global secondary indexes in the DynamoDB table schema.

Once you've called :meth:`~cloudwanderer.cloud_wanderer.CloudWandererResource.load` you can access any property of
the AWS resource that is returned by its describe method. E.g. for VPCs see :attr:`boto3:EC2.Client.describe_vpcs`.
These attributes are stored as snake_case instead of the APIs camelCase, so ``isDefault`` becomes ``is_default``.
