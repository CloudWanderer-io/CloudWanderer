Writing a Subresource
==================================

In this guide we're going to write a CloudWanderer subresource definition for lambda layer versions.

A CloudWanderer subresource is a specific type of Boto3 resource.

* Boto3 subresources are any AWS resource which depends on another resource for its existence (e.g. subnets depend on VPCs and so subnets would be a subresource).
* CloudWanderer subresources are resources which depend on their parent for their identity. A resource is a subresource in CloudWanderer terms if you must supply the id of its parent in order to fetch it (e.g. IAM Role inline policies).

In our case lambda layer versions are subresources because you cannot fetch metadata about them from the AWS API without supplying the
name of the layer of which they are a version.

.. note::

    This guide assumes you have read the :doc:`example_resource` guide as a pre-requisite. As it has a lot more
    detail on some of the steps outlined here. Look to that page for further clarification if need be.

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

Subresources are always discovered alongside their parents, so our tests for lambda layer versions will fit nicely
alongside the tests for lambda layers.

.. code-block:: python
    :linenos:
    :emphasize-lines: 4-10, 17-18, 27-30, 36

    class TestLambdaLayers(NoMotoMock, unittest.TestCase):
        ...

        layer_version_payload = {
            "LayerVersionArn": "arn:aws:lambda:eu-west-1:123456789012:layer:test-layer:1",
            "Version": 1,
            "Description": "This is a test layer!",
            "CreatedDate": "2020-10-17T13:18:00.303+0000",
            "CompatibleRuntimes": ["nodejs10.x"],
        }

        mock = {
            "lambda": {
                "list_layers.return_value": {
                    "Layers": [layer_payload],
                },
                "list_layer_versions.return_value": {"LayerVersions": [layer_version_payload]},
                "get_layer_version.return_value": layer_version_payload,
            }
        }

        single_resource_scenarios = [
            SingleResourceScenario(
                urn=URN.from_string("urn:aws:123456789012:eu-west-1:lambda:layer:test-layer"),
                expected_results=UnsupportedResourceTypeError,
            ),
            SingleResourceScenario(
                urn=URN.from_string("urn:aws:123456789012:eu-west-1:lambda:layer_version:test-layer/1"),
                expected_results=[layer_version_payload],
            ),
        ]

        multiple_resource_scenarios = [
            MultipleResourceScenario(
                arguments=CloudWandererCalls(regions=["eu-west-1"], service_names=["lambda"], resource_types=["layer"]),
                expected_results=[layer_payload, layer_version_payload],
            )
        ]

We've added our test payload as a class variable, referenced it in the mock on line 17, as well as the mock on line 18, and expected it as a result in
lines 27-29 and 36. We have added it to ``single_resource_scenarios`` and ``get_layer_version.return_value`` because while lambda layers cannot be discovered individually, lambda layer **versions** can!

Populate the definition
---------------------------

Visit `Botocore's specification data on GitHub <https://github.com/boto/botocore/tree/develop/botocore/data>`_ and open the latest ``service-2.json`` for your service.

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

You'll notice we've added the collection specification inside the ``Layer`` resource instead of inside the ``service``
as we did in :doc:`example_resource`, this is what allows us to reference the ``LayerName`` of the parent resource
when we call ``ListLayerVersions`` in our collection API call.

Writing the Service Map
------------------------------

The service map is CloudWanderer's store for resource type metadata that does not fit into the Boto3 specification.
It broadly follows the structure of Boto3's to try and keep things simple and consistent.
For our new Layer resource we just need to ensure that the following exists in ``service_mappings/lambda.json``

.. code-block:: json
    :linenos:
    :emphasize-lines: 10-13

    {
        "service": {
            "globalService": false,
            "regionalResources": true
        },
        "resources": {
            "Layer": {
                "type": "baseResource"
            },
            "LayerVersion": {
                "type": "subresource",
                "parentResourceType": "Layer"
            }
        }
    }

We added the ``LayerVersion`` key to ``resources`` to indicate that we've added a subresource whose parent resource type is ``Layer``.
This allows CloudWanderer to determine the proper relationship between these resources and properly generate URNs.

.. include:: service_map_key.rst
.. include:: tests.rst
