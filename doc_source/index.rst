.. CloudWanderer documentation master file, created by
   sphinx-quickstart on Mon Dec  7 18:14:51 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

CloudWanderer
=========================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:


.. doctest ::

   >>> import logging
   >>> from cloudwanderer import CloudWanderer
   >>> from cloudwanderer.storage_connectors import DynamoDbConnector
   >>> wanderer = CloudWanderer(storage_connector=DynamoDbConnector(
   ...     endpoint_url='http://localhost:8000'
   ... ))
   >>> logging.basicConfig(level='INFO')
   >>> wanderer.storage_connector.init()

.. doctest ::

   >>> wanderer.write_all_resources()

.. doctest ::

   >>> lambda_functions = wanderer.read_resource_of_type(service='lambda', resource_type='function')
   >>> print([dict(wanderer.read_resource(x.urn)) for x in lambda_functions])
   [{'FunctionArn': 'arn:aws:lambda:eu-west-2:111111111111:function:awesomeproject-201904202316-HostedUICustomResource-1PLE213GNV66A', 'MemorySize': Decimal('128'), 'Description': '', 'TracingConfig': {'Mode': 'PassThrough'}, 'Timeout': Decimal('300'), 'Handler': 'index.handler', 'CodeSha256': 'fBLFD+AwFo/EQK5rdUweTW8jdBg6cw9LORbpVYqlXXQ=', 'RevisionId': '7fd173f0-0fc0-4df3-a4c3-5464431da769', 'Role': 'arn:aws:iam::111111111111:role/cognitod72684bb_userpoolclient_lambda_role-dev', 'LastModified': '2019-04-20T22:32:07.805+0000', 'FunctionName': 'awesomeproject-201904202316-HostedUICustomResource-1PLE213GNV66A', 'Runtime': 'nodejs8.10', 'CodeSize': Decimal('1742'), 'Version': '$LATEST', 'PackageType': 'Zip'}]
