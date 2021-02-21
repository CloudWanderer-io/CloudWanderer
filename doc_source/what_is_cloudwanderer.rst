What is CloudWanderer
=======================

CloudWanderer is a Python based tool built on top of AWS's `Boto3 SDK <https://boto3.amazonaws.com/v1/documentation/api/latest/index.html>`_ which allows you to discover AWS resources
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
    New AWS Services get introduced *constantly*. CloudWanderer makes it easy to keep up with
    the rate of change by leveraging Boto3's :ref:`boto3:guide_resources` and allowing the definition
    of additional ones using Boto3's own JSON syntax.

Why not use AWS Config Advanced Query?
----------------------------------------

`AWS Config Query <https://docs.aws.amazon.com/config/latest/developerguide/querying-AWS-resources.html>`_
(`released in March 2019 <https://aws.amazon.com/blogs/mt/query-your-resource-configuration-state-using-the-advanced-query-feature-of-aws-config/>`_)
is AWS's solution to centralised resource querying and represents a huge improvement in usability and performance
over querying AWS Config on a resource-by-resource basis as a cross-account aggregated repository.

If AWS Config works for you, you should use it, especially if you have AWS Config enabled already
as it does not entail any additional cost to use Advanced Query.

Here are a few reasons you might find AWS Config lacking for querying your resources.

1. Limited Resource Support
    While AWS Config boasts `an impressive list of supported resources <https://docs.aws.amazon.com/config/latest/developerguide/resource-config-reference.html>`_
    not all of these resources are `available to query via Advanced Query <https://github.com/awslabs/aws-config-resource-schema>`_.
    At the time of writing ``AWS::SecretsManager::Secret`` is a good example of this.
2. Limited Expandibility
    While you can expand the resources available in Advanced Query with `AWS Config Custom Resources, <https://docs.aws.amazon.com/config/latest/developerguide/customresources.html>`_
    at the time of writing, the following limitations apply:

    1. It is a simple API to post data to, you must write and trigger your own code to discover new/update existing resources
    2. It is not possible to retrieve any of the custom attributes you provide via Advanced Query, only the mandatory attributes are returned (e.g. Account, region).
    3. Not all regions are supported.

2. No Subresource Support
    Some resources do not have their own ARNs. Inline IAM Policies are a good example of this.
    It is currently not possible to lookup the policy document of an inline IAM policy via AWS Config.
3. No Secondary Attribute Support
    AWS Config works by storing the primary attributes of a resource, i.e. those attributes that are returned
    by the ``Describe`` method (e.g. ``DescribeImages``). However, there are secondary attributes that you sometimes
    need to lookup to understand your environment. For example you may need to know which AWS Accounts an AMI
    is shared with, in which case you would need to call ``DescribeImageAttribute`` with the ``Attribute=launchPermission``
    argument. This information is currently not available in AWS Config.
4. Indeterminate API Throttling.
    The AWS Config Advanced Query API does not have a documented query limit. As it was billed at launch
    as a way to `"[help] reduce the throttling encountered while making service-specific describe API calls."`
    it's reasonable to assume that the throttling threshold is high, but bear in mind there is no cost
    associated with this service.

If any of these are dealbreakers for you, and you don't mind putting in the time, effort, and cost to
query your own resources, CloudWanderer may be for you!
