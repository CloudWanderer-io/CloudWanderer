.. image :: https://user-images.githubusercontent.com/803607/101322139-7111b800-385e-11eb-9277-c6bf3a580987.png

|version| |checks| |docs|

.. |version|
   image:: https://img.shields.io/pypi/v/cloudwanderer?style=flat-square
      :alt: PyPI
      :target: https://pypi.org/project/cloudwanderer/

.. |checks|
   image:: https://img.shields.io/github/workflow/status/cloudwanderer-io/cloudwanderer/Python%20package/main?style=flat-square
      :alt: GitHub Workflow Status (branch)
      :target: https://github.com/CloudWanderer-io/CloudWanderer/actions?query=branch%3Amain

.. |docs|
   image:: https://readthedocs.org/projects/cloudwanderer/badge/?version=latest&style=flat-square
      :target: https://www.cloudwanderer.io/en/latest/?badge=latest
      :alt: Documentation Status

| **Documentation:** `CloudWanderer.io <https://www.cloudwanderer.io>`_
| **GitHub:** `https://github.com/CloudWanderer-io/CloudWanderer <https://github.com/CloudWanderer-io/CloudWanderer>`_

A Python package which allows you to enumerate and store your AWS Resources in AWS Neptune (or Gremlin for local execution) in order to be able to ask questions like:

1. `What EC2 instances do I have that are in Public Subnets that have roles and are accessible from the internet? <https://www.youtube.com/watch?v=GARTSsyYkk8>`__
2. How old are my IAM users access keys?
3. What lambda functions do I have that are connected to VPCs that have access to the internet via a NAT gateway?
4. How many untagged VPCs do I have across all regions?

What does it do?
""""""""""""""""""

.. image:: https://raw.githubusercontent.com/CloudWanderer-io/CloudWanderer/969a5692982f81ae2448a3447cb271adb2b333fa/doc_source/images/discovering-ec2-instances-video.png
   :target: https://www.youtube.com/watch?v=GARTSsyYkk8
   :alt: YouTube video demonstrating how to query public ec2 instances with CloudWander and OpenCypher.

What the above `YouTube video <https://www.youtube.com/watch?v=GARTSsyYkk8>`__ to see an example of what you can do with CloudWanderer.


Installation
"""""""""""""""

.. code-block ::

   pip install cloudwanderer

Local Quickstart
""""""""""""""""""

Spin up a local `Gremlin Graph Database server <http://tinkerpop.apache.org/docs/current/reference/#gremlin-server>`__ and a Jupyter Notebook.

.. code-block ::

   $ git clone https://github.com/CloudWanderer-io/docker-graph-notebook.git
   $ cd docker-graph-notebook
   $ docker-compose up

Look in the output for something that looks like:

.. code-block::

   jupyter-notebook_1  |     Or copy and paste one of these URLs:
   jupyter-notebook_1  |         http://localhost:8888/?token=88dc054886e3ea73480de91066937a33c9bc8bd484eb395c

Open the URL in question in a tab in your browser.


Open up Python **in your preferred IDE** and import and initialise `CloudWanderer`

.. doctest ::

   >>> import logging
   >>> from cloudwanderer import CloudWanderer
   >>> from cloudwanderer.storage_connectors import GremlinStorageConnector
   >>> storage_connector = GremlinStorageConnector(
   ...     endpoint_url="ws://localhost:8182"
   ... )
   >>> wanderer = CloudWanderer(storage_connectors=[storage_connector])
   >>> logging.basicConfig(level='INFO')

Get all the resources from your AWS account and save them to your local Gremlin graph database.

.. doctest ::

   >>> wanderer.write_resources()

Go to the Jupyter Notebook link you opened earlier and, **create a new notebook by hitting 'new'** on the top right, and type the following into a new cell to get a list of VPCs.

.. code-block:: 

   %%gremlin
   g.V().hasLabel('aws_ec2_vpc').out().path().by(valueMap(true))

Voila!

.. image:: https://user-images.githubusercontent.com/803607/144116568-ef8e6d38-11f6-477e-8c30-0882fbe29c94.png
   :alt: Example Query and graph output

You can learn more Gremlin (the language that's supported by the local setup here) by reading `Kevin Lawrence's amazing book on Gremlin <https://kelvinlawrence.net/book/Gremlin-Graph-Guide.html>`__ 
OR you can get stuck in to the much more straightforward OpenCypher language by following the `Neptune Quickstart guide <https://www.cloudwanderer.io/en/latest/neptune_quickstart.html>`__.
