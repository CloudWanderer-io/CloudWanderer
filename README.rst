.. image :: https://user-images.githubusercontent.com/803607/101322139-7111b800-385e-11eb-9277-c6bf3a580987.png

|version| |checks| |docs|

.. |version|
   image:: https://img.shields.io/pypi/v/cloudwanderer?style=flat-square
      :alt: PyPI
      :target: https://pypi.org/project/cloudwanderer/

.. |checks|
   image:: https://img.shields.io/github/workflow/status/cloudwanderer-io/cloudwanderer/Python%20package/main?style=flat-square
      :alt: GitHub Workflow Status (branch)
      :target: https://github.com/CloudWanderer-io/CloudWanderer/actions?query=branch%3Amain

.. |docs|
   image:: https://readthedocs.org/projects/cloudwanderer/badge/?version=latest&style=flat-square
      :target: https://www.cloudwanderer.io/en/latest/?badge=latest
      :alt: Documentation Status

A Python package which wanders across your AWS account and records your resources in DynamoDB


| **Documentation:** `CloudWanderer.io <https://www.cloudwanderer.io>`_
| **GitHub:** `https://github.com/CloudWanderer-io/CloudWanderer <https://github.com/CloudWanderer-io/CloudWanderer>`_

Installation
"""""""""""""""

.. code-block ::

   pip install cloudwanderer

Usage
""""""""""

Start a local dynamodb

.. code-block ::

   $  docker run -p 8000:8000 amazon/dynamodb-local


Open up python and import and initialise `CloudWanderer`

.. doctest ::

   >>> import logging
   >>> from cloudwanderer import CloudWanderer
   >>> from cloudwanderer.storage_connectors import DynamoDbConnector
   >>> storage_connector = DynamoDbConnector(
   ...     endpoint_url='http://localhost:8000'
   ... )
   >>> wanderer = CloudWanderer(storage_connectors=[storage_connector])
   >>> logging.basicConfig(level='INFO')
   >>> storage_connector.init()

Get all the resources from your AWS account and save them to your local dynamodb.

.. doctest ::

   >>> wanderer.write_resources()

Get a list of VPCs back.

.. doctest ::

   >>> vpcs = storage_connector.read_resources(service='ec2', resource_type='vpc')
   >>> first_vpc = next(vpcs)
   >>> first_vpc.urn
   URN(account_id='123456789012', region='us-east-1', service='ec2', resource_type='vpc', resource_id_parts=['vpc-11111111'])

Load the full details of the resource.

.. doctest ::

   >>> first_vpc.load()
   >>> first_vpc.cidr_block
   '172.31.0.0/16'
   >>> first_vpc.instance_tenancy
   'default'
   >>> first_vpc.is_default
   True
