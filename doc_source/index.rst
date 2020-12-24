.. CloudWanderer documentation master file, created by
   sphinx-quickstart on Mon Dec  7 18:14:51 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

CloudWanderer
=========================================

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Contents:

   examples
   supported_resources
   reference

.. image :: https://user-images.githubusercontent.com/803607/101322139-7111b800-385e-11eb-9277-c6bf3a580987.png

A Python package which wanders across your AWS account and records your resources in DynamoDB

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
   >>> wanderer = CloudWanderer(storage_connector=DynamoDbConnector(
   ...     endpoint_url='http://localhost:8000'
   ... ))
   >>> logging.basicConfig(level='INFO')
   >>> wanderer.storage_connector.init()

Query all the resources from your current account region and save them to your local dynamodb.

.. doctest ::

   >>> wanderer.write_resources_in_region()

Get a list of VPCs back.

.. doctest ::

   >>> vpc_urns = wanderer.read_resource_of_type(service='ec2', resource_type='vpc')
   >>> first_vpc = next(vpc_urns)
   >>> first_vpc.urn
   AwsUrn(account_id='123456789012', region='eu-west-2', service='ec2', resource_type='vpc', resource_id='vpc-11111111')

Load the full details of the resource.

.. doctest ::

   >>> vpc = wanderer.read_resource(urn=first_vpc.urn)
   >>> vpc.cidr_block
   '172.31.0.0/16'
   >>> vpc.instance_tenancy
   'default'
   >>> vpc.is_default
   True
