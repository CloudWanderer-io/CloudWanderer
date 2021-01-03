What is CloudWanderer
=======================

CloudWanderer is a Python based tool which allows you to discover AWS resources
and store them for later retrieval.

Use Cases
----------

CloudWanderer makes it easy to answer questions like:

* Is S3 bucket name one in my organisation?
* Which roles have the ``AdministratorAccess`` policy attached?


Objectives
-------------

#. Be storage agnostic.
    The current primary storage connector is DynamoDB but can easily be replaced
    with other storage providers.
#. Allow complete discovery.
    Many AWS resource discovery solutions do not support secondary attributes like
    ``EnableDnsSupport`` from :meth:`~boto3:EC2.Client.describe_vpc_attribute`.
#. Be easily extensible.
    New AWS Services get introduced _constantly_. CloudWanderer makes it easy to keep up with
    the rate of change by leveraging Boto3's :ref:`boto3:guide_resources` and allowing the definition
    of additional ones using Boto3's own JSON syntax.
