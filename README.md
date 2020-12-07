# CloudWanderer

![cloudwanderer](https://user-images.githubusercontent.com/803607/101322139-7111b800-385e-11eb-9277-c6bf3a580987.png)

A Python package which wanders across your AWS account and records your resources in DynamoDB

# Running


Start a local dynamodb
```
$  docker run -p 8000:8000 amazon/dynamodb-local
```
Open up python and import and initialise `CloudWanderer`
```
$ python
>>> import logging
>>> from cloud_wanderer import CloudWanderer
>>> from cloud_wanderer.storage_connectors import DynamoDbConnector
>>> wanderer = CloudWanderer(storage_connector=DynamoDbConnector(
...     endpoint_url='http://localhost:8000'
... ))
>>> logging.basicConfig(level='INFO')
>>> wanderer.storage_connector.init()
```
Query all the resources from your current account region and save them to your local dynamodb.
```
>>> wanderer.write_all_resources()
INFO     root:cloud_wanderer.py:97 --> Fetching cloudformation stacks
INFO     root:cloud_wanderer.py:97 --> Fetching cloudwatch alarms
INFO     root:cloud_wanderer.py:97 --> Fetching cloudwatch metrics
INFO     root:cloud_wanderer.py:97 --> Fetching dynamodb tables
INFO     root:cloud_wanderer.py:97 --> Fetching ec2 classic_address
...
```
Get a list of lambda functions back.
```
>>> lambda_functions = wanderer.read_resource_of_type(service='lambda', resource_type='function')
>>> print([dict(wanderer.read_resource(x.urn)) for x in lambda_functions])

[{'FunctionArn': 'arn:aws:lambda:eu-west-2:111111111111:function:awesomeproject-201904202316-HostedUICustomResource-1PLE213GNV66A', 'MemorySize': Decimal('128'), 'Description': '', 'TracingConfig': {'Mode': 'PassThrough'}, 'Timeout': Decimal('300'), 'Handler': 'index.handler', 'CodeSha256': 'fBLFD+AwFo/EQK5rdUweTW8jdBg6cw9LORbpVYqlXXQ=', 'RevisionId': '7fd173f0-0fc0-4df3-a4c3-5464431da769', 'Role': 'arn:aws:iam::111111111111:role/cognitod72684bb_userpoolclient_lambda_role-dev', 'LastModified': '2019-04-20T22:32:07.805+0000', 'FunctionName': 'awesomeproject-201904202316-HostedUICustomResource-1PLE213GNV66A', 'Runtime': 'nodejs8.10', 'CodeSize': Decimal('1742'), 'Version': '$LATEST', 'PackageType': 'Zip'}, ...]
```

# Expanding Boto3: Adding custom service definitions

As CloudWanderer works off boto3's `Resource` classes, there is limited suppor for the wide range of AWS resources to query out of the box with boto3. Fortunately as boto3 is data defined, it's relatively trivial to add the json to support additional resources.

Look to the json files in [boto3](https://github.com/boto/boto3/tree/develop/boto3/data) for an example of what a _complete_ definition looks like.
However, you do not need to fill out the full service definition, look at [cloud_wanderer/service_definitions](cloudwanderer/service_definitions) for an example of what's required to fill out specific resources.

The only non-obvious thing in that is that the `shape` definition comes from the [botocore json](https://github.com/boto/botocore/tree/develop/botocore/data). Look at the `shapes` key in the `service-{n}.json` you're interested in, follow that to the request that returns the resource you want to record (e.g. `ListFunctions`) and see what the output shape name is (e.g. `ListFunctionsResponse`), then see what the members shape is (e.g. `FunctionList`) and finally look at the shape name for that member (i.e. the shape of the resource you actually want to return) (e.g. `FunctionConfiguration`)
