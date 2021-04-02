Writing a Subresource
==================================

Getting the test data
---------------------------

.. code-block:: shell

    $ aws lambda list-layer-versions --layer-name test-layer
    {
        "LayerVersions": [
            {
                "LayerVersionArn": "arn:aws:lambda:eu-west-1:123456789012:layer:test-layer:1",
                "Version": 1,
                "Description": "This is a test layer!",
                "CreatedDate": "2020-10-17T13:18:00.303+0000",
                "CompatibleRuntimes": [
                    "nodejs10.x"
                ]
            }
        ]
    }

Create the tests
-----------------


Populate the definition
---------------------------

https://github.com/boto/botocore/blob/develop/botocore/data/lambda/2015-03-31/service-2.json

We're here following much the same process as in :doc:`example_resource`.
We're following our ``ListLayerVersions`` through its return of ``ListLayerVersionsResponse`` to its shape of ``LayerVersionsList``
to its member of ``LayerVersionsListItem``.
Along the way we've identified the

* Collection Request Operation (``ListLayerVersions``)
* Resource Shape (``LayerVersionsListItem``)
* Identifiers (``LayerName`` and ``Version``)

Subresource Identifiers
"""""""""""""""""""""""""""""

Subresources *always* have two identifiers, one is the identifier of their parent, and the other is their identifier.
In CloudWanderer's definition this is what makes them a subresource, that they do not have an independent identity without their parent.

.. code-block:: json

    [
        {
            "target": "LayerName",
            "source": "identifier",
            "name": "LayerName"
        },
        {
            "target": "Version",
            "source": "response",
            "path": "LayerVersions[].Version"
        }
    ]

Subresource Request Operation
"""""""""""""""""""""""""""""""""

Resource request operations were pretty simple as they had no arguments. Subresources on the other hand
need to supply the identity of their parent as an argument to whatever API method they're calling.

.. code-block:: json

    {
        "operation": "ListLayerVersions",
        "params": [
            {
                "target": "LayerName",
                "source": "identifier",
                "name": "LayerName"
            }
        ]
    }

This will take the ``LayerName`` from the parent resource, and submit it as a parameter called ``LayerName`` to the ``ListLayerVersions`` API method.

Bringing it all together
-------------------------------

In the ``resources`` definiton we've added the highlighted lines.

.. code-block ::
    :linenos:
    :emphasize-lines: 11-40, 42-54

    {
        "resources": {
            "Layer": {
                "identifiers": [
                    {
                        "name": "LayerName",
                        "memberName": "LayerName"
                    }
                ],
                "shape": "LayersListItem",
                "hasMany": {
                    "LayerVersions": {
                        "request": {
                            "operation": "ListLayerVersions",
                            "params": [
                                {
                                    "target": "LayerName",
                                    "source": "identifier",
                                    "name": "LayerName"
                                }
                            ]
                        },
                        "resource": {
                            "type": "LayerVersion",
                            "identifiers": [
                                {
                                    "target": "LayerName",
                                    "source": "identifier",
                                    "name": "LayerName"
                                },
                                {
                                    "target": "Version",
                                    "source": "response",
                                    "path": "LayerVersions[].Version"
                                }
                            ],
                            "path": "LayerVersions[]"
                        }
                    }
                }
            },
            "LayerVersion": {
                "identifiers": [
                    {
                        "name": "LayerName",
                        "memberName": "LayerName"
                    },
                    {
                        "name": "Version",
                        "memberName": "Version"
                    }
                ],
                "shape": "LayerVersionsListItem"
                }
            }
        }
    }
