import os
import re
import sys
from pathlib import Path

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
sys.path.insert(0, os.path.abspath(".."))
sys.path.append(os.path.abspath("./_ext"))


# -- Project information -----------------------------------------------------

project = "CloudWanderer"
copyright = "2020, Sam Martin"
author = "Sam Martin"

# The full version, including alpha/beta/rc tags
with open(Path(__file__).parent.parent / Path("setup.py")) as f:
    release = re.search(r"version=\"([^\"]+)\"", f.read()).groups()[0]


nitpicky = True
nitpick_ignore = [
    ("py:exc", "botocore.exceptions.ClientError"),
    ("py:class", "botocore.client.ClientCreator"),
    ("py:class", "botocore.model.Shape"),
    ("py:class", "gremlin_python.driver.driver_remote_connection.DriverRemoteConnection"),
    ("py:class", "type"),
    ("py:class", ("string", "boolean")),
]


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autodoc.typehints",
    "sphinx.ext.doctest",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx_rtd_theme",
    "supported_resources",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_favicon = "logo.png"

# -- intersphinx
intersphinx_mapping = {
    "boto3": ("https://boto3.amazonaws.com/v1/documentation/api/latest/", None),
    "botocore": ("https://botocore.amazonaws.com/v1/documentation/api/latest/", None),
    "python": ("https://docs.python.org/3", None),
}

# -- Napoleon
napoleon_include_init_with_doc = True

# -- Autodoc
add_module_names = False
autodoc_typehints = "description"


# -- Doctest
doctest_global_setup = """
import os
import json
import logging
from unittest.mock import MagicMock, patch
import boto3
import cloudwanderer
from moto import ec2, mock_ec2, mock_sts, mock_s3, mock_iam
from cloudwanderer.models import ActionSet
from cloudwanderer.urn import PartialUrn
from tests.pytest_helpers import create_iam_role

ec2.models.random_vpc_id = MagicMock(return_value='vpc-11111111')

for mock in [mock_ec2, mock_sts, mock_s3, mock_iam]:
    mock().start()

create_iam_role()

cloudwanderer.aws_interface.session.CloudWandererBoto3Session.get_available_regions = ['eu-west-1', 'us-east-1']
cloudwanderer.aws_interface.CloudWandererAWSInterface.get_resource_discovery_actions = MagicMock(return_value=[
        ActionSet(
            get_urns=[
                PartialUrn(
                    cloud_name="aws",
                    account_id="123456789012",
                    region="eu-west-2",
                    service="ec2",
                    resource_type="vpc",
                    resource_id_parts=["ALL"],
                ),
                PartialUrn(
                    cloud_name="aws",
                    account_id="123456789012",
                    region="us-east-1",
                    service="ec2",
                    resource_type="vpc",
                    resource_id_parts=["ALL"],
                ),
            ],
            delete_urns=[
                PartialUrn(
                    cloud_name="aws",
                    account_id="123456789012",
                    region="eu-west-2",
                    service="ec2",
                    resource_type="vpc",
                    resource_id_parts=["ALL"],
                ),
                PartialUrn(
                    cloud_name="aws",
                    account_id="123456789012",
                    region="us-east-1",
                    service="ec2",
                    resource_type="vpc",
                    resource_id_parts=["ALL"],
                ),
            ],
        ),
        # S3
        ActionSet(
            get_urns=[
                PartialUrn(
                    cloud_name="aws",
                    account_id="123456789012",
                    region="us-east-1",
                    service="s3",
                    resource_type="bucket",
                    resource_id_parts=["ALL"],
                ),
            ],
            delete_urns=[
                PartialUrn(
                    cloud_name="aws",
                    account_id="123456789012",
                    region="us-east-1",
                    service="s3",
                    resource_type="bucket",
                    resource_id_parts=["ALL"],
                ),
            ],
        ),
        # IAM
        ActionSet(
            get_urns=[
                PartialUrn(
                    cloud_name="aws",
                    account_id="123456789012",
                    region="us-east-1",
                    service="iam",
                    resource_type="role",
                    resource_id_parts=["ALL"],
                ),
            ],
            delete_urns=[
                PartialUrn(
                    cloud_name="aws",
                    account_id="123456789012",
                    region="us-east-1",
                    service="iam",
                    resource_type="role",
                    resource_id_parts=["ALL"],
                ),
            ],
        ),
    ]
)

cloudwanderer.storage_connectors.DynamoDbConnector = MagicMock(
    return_value=cloudwanderer.storage_connectors.MemoryStorageConnector()
)
cloudwanderer.storage_connectors.GremlinStorageConnector = MagicMock(
    return_value=cloudwanderer.storage_connectors.MemoryStorageConnector()
)
"""
