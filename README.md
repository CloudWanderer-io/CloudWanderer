# CloudWanderer

![cloudwanderer](https://user-images.githubusercontent.com/803607/101322139-7111b800-385e-11eb-9277-c6bf3a580987.png)

[![PyPI](https://img.shields.io/pypi/v/cloudwanderer?style=flat-square)](https://pypi.org/project/cloudwanderer/)


A Python package which wanders across your AWS account and records your resources in DynamoDB

# Documentation

See the full documentation at [CloudWanderer.io](https://www.cloudwanderer.io).

# Quick Start

## Installation

```
pip install cloudwanderer
```

## Usage

Start a local dynamodb

```
$  docker run -p 8000:8000 amazon/dynamodb-local
```

Open up python and import and initialise `CloudWanderer`

```
>>> import logging
>>> from cloudwanderer import CloudWanderer
>>> from cloudwanderer.storage_connectors import DynamoDbConnector
>>> wanderer = CloudWanderer(storage_connector=DynamoDbConnector(
...     endpoint_url='http://localhost:8000'
... ))
>>> logging.basicConfig(level='INFO')
>>> wanderer.storage_connector.init()
```

Query all the resources from your current account region and save them to your local dynamodb.

```
>>> wanderer.write_all_resources()
```

Get a list of lambda functions back.

```
>>> lambda_function_urns = wanderer.read_resource_of_type(service='lambda', resource_type='function')
>>> first_function = next(lambda_function_urns)
>>> first_function.urn
AwsUrn(account_id='111111111111', region='eu-west-2', service='lambda', resource_type='function', resource_id='awesomeproject-201904202316-HostedUICustomResource-1PLE213GNV66A')
```

Load the full details of the resource.

```
>>> function = wanderer.read_resource(urn=first_function.urn)
>>> function.function_name
'awesomeproject-201904202316-HostedUICustomResource-1PLE213GNV66A'
>>> function.role
'arn:aws:iam::111111111111:role/cognitod72684bb_userpoolclient_lambda_role-dev'
>>> function.runtime
'python3.8'
```
