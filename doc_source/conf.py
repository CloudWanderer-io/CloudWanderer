import os
import sys

import sphinx_rtd_theme  # noqa

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
release = "0.13.2"

nitpicky = True
nitpick_ignore = [
    ("py:exc", "botocore.exceptions.ClientError"),
    ("py:class", "botocore.client.ClientCreator"),
    ("py:class", "botocore.model.Shape"),
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
from moto import ec2

ec2.models.RegionsAndZonesBackend.regions = [
    ec2.models.Region(region_name, "ec2.{region_name}.amazonaws.com", "opt-in-not-required")
    for region_name in ['eu-west-2', 'us-east-1']
]
ec2.models.random_vpc_id = MagicMock(return_value='vpc-11111111')
from tests.integration.helpers import get_default_mocker
from tests.integration.mocks import add_infra
get_default_mocker().start_general_mock(
    restrict_regions=['eu-west-2', 'us-east-1']
)
add_infra()

cloudwanderer.storage_connectors.DynamoDbConnector = MagicMock(
    return_value=cloudwanderer.storage_connectors.MemoryStorageConnector()
)
"""
