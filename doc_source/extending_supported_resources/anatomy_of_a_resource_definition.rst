Anatomy of a Resource Definition
================================

Because they are loaded into Boto3, CloudWanderer resources use the same JSON definition as Boto3 resources.

.. code-block:: json
    :linenos:

    {
        "service": {
            "hasMany": {
                "Functions": {
                    "request": {
                        "operation": "ListFunctions"
                    },
                    "resource": {
                        "type": "Function",
                        "identifiers": [
                            {
                                "target": "FunctionName",
                                "source": "response",
                                "path": "Functions[].FunctionName"
                            }
                        ],
                        "path": "Functions[]"
                    }
                }
            }
        },
        "resources": {
            "Function": {
                "identifiers": [
                    {
                        "name": "FunctionName",
                        "memberName": "FunctionName"
                    }
                ],
                "shape": "FunctionConfiguration",
                "load": {
                    "request": {
                        "operation": "GetFunction",
                        "params": [
                            {
                                "target": "FunctionName",
                                "source": "identifier",
                                "name": "FunctionName"
                            }
                        ]
                    },
                    "path": "Configuration"
                }
            }
        }
    }

This is made up of the following two parts:

Collection definition (lines 3-20)
"""""""""""""""""""""""""""""""""""

A collection definition is the way CloudWanderer and Boto3 determine how they can list all resources of a specific type.

* Collection Name (line 4)
    The name of the collection (really only appears in documentation)
* Collection Request Operation Name (line 6)
    The name of the API method we need to call in order to list this type of resource
* Collection Resource Type (line 9)
    The type of the resource that this collection contains (this *must* match the name on line 23).
    This does **not** have to match any Boto3 or Botocore names and will be the name you supply when calling
    :class:`~cloudwanderer.cloud_wanderer.CloudWanderer.write_resources` with the ``service_names`` argument.
* Collection Resource Identifier (lines 11-15)
    A specification for the components of the API response which make up the unique identifiers for this resource type.
* Collection Resource Path (line 17)
    The `JMESPath <https://jmespath.org>`_ to the Resource metadata in the collection request response

Resource definition (lines 23-44)
""""""""""""""""""""""""""""""""""""
A resource definition is the way CloudWanderer and Boto3 understand a resource.
Boto3 uses resource definitions paired with Botocore API definitions to determine how to populate a resource,
and what relationships it has with other resources.

* Resource Type (line 23)
    Must match the one specified in the collection on line 9!
    This does **not** have to match any Boto3 or BotoCore names and will be the name you supply when calling
    :class:`~cloudwanderer.cloud_wanderer.CloudWanderer.write_resources` with the ``service_names`` argument.
* Resource Identifier(s) (lines 25-28)
    A specification for the unique identifiers for this resource, it can get values from either
    the load API response or (as in this case) the members passed from the collection.
    A base resource (e.g. an IAM Role) will only ever have one identifier.
    A subresource (e.g. an IAM Role's inline policy) will always have exactly two; the first being the identifier of its parent
    (e.g. the Role name) the second being its identifier within the parent (e.g. the inline policy name).
* Resource Shape (line 30)
    The Botocore shape name for this resource. This identifies the Botocore specification for the API responses that populate this resource.
    The Botocore shape specification tells Boto3 what attributes it can expect to populated with.
* Resource Load request (lines 32-42)
    A specification for how to load this resource without calling the collection first.
    If this is not populated then you will be unable to call
    :class:`~cloudwanderer.cloud_wanderer.CloudWanderer.write_resource` with this resource type and will only be
    able to populate it via :class:`~cloudwanderer.cloud_wanderer.CloudWanderer.write_resources`.
