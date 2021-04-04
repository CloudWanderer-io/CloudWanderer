
Running the tests
-----------------------
Now you've put all the pieces together you need to run the tests.
You can `see the full test code on github <https://github.com/CloudWanderer-io/CloudWanderer/blob/master/tests/integration/custom_resources/lambda/test_layers.py>`_.
As well as the `full resource specification (alongside Lambda Function) <https://github.com/CloudWanderer-io/CloudWanderer/blob/master/cloudwanderer/resource_definitions/lambda.json>`_.

To run the tests:

.. code-block :: shell

    # Install the pre-reqs
    $ pip install -r requirements-test.txt -r requirements.txt
    # Install the package in interactive mode
    $ pip install -e .
    # Run the tests
    $ pytest tests/integration/custom_resources/lambda/test_layers.py
    === 2 passed in 2.28s ==


Submit a PR!
-------------------

Congratulations! You have successfully created a new resource!
If you submit a Pull Request to https://github.com/CloudWanderer-io/CloudWanderer/ with your new resource we
will get it merged in and released for everyone to use as quickly as we possibly can!
If you find you're not getting the attention you deserve for whatever reason, contact us on `twitter <https://twitter.com/cloudwandererio>`_.
