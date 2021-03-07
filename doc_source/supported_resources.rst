Supported Resources
========================

Resources
---------------

CloudWanderer finds resources from AWS based on :ref:`Boto3 resources <boto3:guide_resources>`.
However, Boto3 does not have definitions for all resources that exist in AWS
(though it does of course have :ref:`clients <boto3:guide_clients>` for all services).
To increase resource coverage, CloudWanderer implements additional definitions.
These definitions are very fast to write and test as they provide only the functionality
required to query the resource rather than the much more featureful Boto3 resources which expose additional actions.

CloudWanderer Provided Resources
"""""""""""""""""""""""""""""""""""""

.. supported-resources:cloudwanderer-resources ::

Boto3 Provided Resources
"""""""""""""""""""""""""""""""

.. supported-resources:boto3-resources ::

Additional Resource Attributes
---------------------------------

Some resources require additional API calls beyond the initial
``list`` or ``describe`` call to retrieve all their metadata.
To allow us to retrieve that additional information and return it in our
:class:`~cloudwanderer.cloud_wanderer_resource.CloudWandererResource`, we implement our own
custom Resource Attribute definitions.

You can find the full list of supported Resource Attributes below.

.. supported-resources:cloudwanderer-secondary-attributes ::
