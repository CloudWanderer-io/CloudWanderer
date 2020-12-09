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

   class_reference
   storage_connector_reference

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

   >>> wanderer.write_all_resources()

Get a list of lambda functions back.

.. doctest ::

   >>> lambda_functions = wanderer.read_resource_of_type(service='lambda', resource_type='function')
   >>> print([dict(wanderer.read_resource(x.urn)) for x in lambda_functions])
   [{'FunctionArn': 'arn:aws:lambda:eu-west-2:111111111111:function:awesomeproject-201904202316-HostedUICustomResource-1PLE213GNV66A', 'MemorySize': Decimal('128'), 'Description': '', 'TracingConfig': {'Mode': 'PassThrough'}, 'Timeout': Decimal('300'), 'Handler': 'index.handler', 'CodeSha256': 'fBLFD+AwFo/EQK5rdUweTW8jdBg6cw9LORbpVYqlXXQ=', 'RevisionId': '7fd173f0-0fc0-4df3-a4c3-5464431da769', 'Role': 'arn:aws:iam::111111111111:role/cognitod72684bb_userpoolclient_lambda_role-dev', 'LastModified': '2019-04-20T22:32:07.805+0000', 'FunctionName': 'awesomeproject-201904202316-HostedUICustomResource-1PLE213GNV66A', 'Runtime': 'nodejs8.10', 'CodeSize': Decimal('1742'), 'Version': '$LATEST', 'PackageType': 'Zip'}]
