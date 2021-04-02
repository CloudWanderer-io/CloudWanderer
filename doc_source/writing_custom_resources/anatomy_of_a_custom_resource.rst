Anatomy of a Custom Resource
================================

Because they are loaded into Boto3, CloudWanderer custom resources use the same JSON definition as do Boto3 resources.

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

This is made up of the following main components:

Collection definition
"""""""""""""""""""""""""

A collection definition is the way CloudWanderer and Boto3 determine how they can list all resources of a specific type.

* Collection Name (line 4)
    The name of the collection (really only appears in documentation)
* Collection Request Operation Name (line 6)
    The name of the API method we need to call in order to list this type of resource
* Collection Resource Type (line 9)
    The type of the resource that this collection contains (this *must* match the name on line 23).
* Collection Resource Identifier (lines 11-15)
    A specification for the components of the API response which make up the unique identifiers for this resource type.
* Collection Resource Path (line 17)

Resource definition
""""""""""""""""""""""
A resource definition is the way CloudWanderer and Boto3 determine how to understand a resource.

* Resource Type (line 23)
    Must match the one specified in the collection on line 9!
* Resource Identifier(s) (lines 25-28)
    A specification for the unique identifiers for this resource, can get values from either the load API response or (as in this case) the members passed from the collection.
* Resource Shape (line 30)
    The Botocore shape name for this resource.
* Resource Load request (lines 32-42)
    A specification for how to load this resource without calling the collection first.
