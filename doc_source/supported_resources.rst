Supported Resources
========================

Resources
---------------

CloudWanderer finds resources from AWS based on :ref:`boto3 resources <boto3:guide_resources>`.
However, boto3 does not have definitions for all resources that exist in AWS
(though it does of course have :ref:`clients <boto3:guide_clients>` for all services).
To increase resource coverage, CloudWanderer implements its own resource definitions
(that provide only the subset of functionality required by a full boto3 resource).

You can find a full list of supported resources below.

Resources Provided by CloudWanderer
""""""""""""""""""""""""""""""""""""""""""""""""

.. supported-resources:cloudwanderer-resources ::

Resources Provided by boto3
""""""""""""""""""""""""""""""""""""""""""""

.. supported-resources:boto3-default-resources ::


Additional Resource Attributes
---------------------------------

Some resources required additional API calls above and beyond the initial
``list`` or ``describe`` call to retrieve all their metadata.
To allow us to retrieve that additional information and return it in our :class:`~cloudwanderer.cloud_wanderer.CloudWandererResource`
when queried, we leverage our own custom Resource Attribute definitions.

You can find the full list of supported Resource Attributes below.

.. supported-resources:cloudwanderer-resource-attributes ::
