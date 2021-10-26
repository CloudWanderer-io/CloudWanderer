
Running the tests
-----------------------
Now you've put all the pieces together you need to run the tests.
You can see the specifications on GitHub:

 - `test specification <https://github.com/CloudWanderer-io/CloudWanderer/blob/main/tests/integration/custom_resources/lambda/layer_multiple_resources.json>`__.
 - `resource specification (alongside Lambda Function) <https://github.com/CloudWanderer-io/CloudWanderer/blob/main/cloudwanderer/aws_interface/resource_definitions/lambda/2015-03-31/resources-1.json>`__.
 - `service map specification <https://github.com/CloudWanderer-io/CloudWanderer/blob/main/cloudwanderer/aws_interface/resource_definitions/lambda/2015-03-31/resources-cw-1.json>`__.

To run the tests:

.. code-block :: shell

    # Install the pre-reqs
    $ pip install -r requirements-test.txt -r requirements.txt
    # Install the package in interactive mode
    $ pip install -e .
    # Run the tests
    $ pytest tests/integration/custom_resources/ -k layer_multiple_resources
    AssertionError: Dictionaries do not match 
    E           Second dict as json: {"urn": ...

You can then take the ``Second dict as json`` result and place it in your ``expectedResults`` list, validate it's what you expect, and re-run the test.

.. tip:: 
    
    Make sure to remove the key/value for ``discovery_time`` as this will change with every test execution!

Submit a PR!
-------------------

Congratulations! You have successfully created a new resource!
If you submit a Pull Request to https://github.com/CloudWanderer-io/CloudWanderer/ with your new resource we
will get it merged in and released for everyone to use as quickly as we possibly can!
If you find you're not getting the attention you deserve for whatever reason, contact us on `twitter <https://twitter.com/cloudwandererio>`_.
