import os
import sys
import sphinx_rtd_theme # noqa

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
sys.path.insert(0, os.path.abspath('..'))
sys.path.append(os.path.abspath("./_ext"))


# -- Project information -----------------------------------------------------

project = 'CloudWanderer'
copyright = '2020, Sam Martin'
author = 'Sam Martin'

# The full version, including alpha/beta/rc tags
release = '0.8.0'

nitpicky = True


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autodoc.typehints',
    'sphinx.ext.doctest',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx_rtd_theme',
    'supported_resources'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# -- intersphinx
intersphinx_mapping = {
    'boto3': ('https://boto3.amazonaws.com/v1/documentation/api/latest/', None)
}

# -- Autodoc
add_module_names = False
autodoc_typehints = 'description'


# -- Doctest
doctest_global_setup = '''
import os
from unittest.mock import MagicMock, patch
import boto3
import cloudwanderer
from moto import ec2

ec2.models.RegionsAndZonesBackend.regions = [
    ec2.models.Region(region_name, "ec2.{region_name}.amazonaws.com", "opt-in-not-required")
    for region_name in ['eu-west-2', 'us-east-1']
]
ec2.models.random_vpc_id = MagicMock(return_value='vpc-11111111')
from moto import mock_ec2, mock_s3, mock_iam, mock_sts, mock_dynamodb2

os.environ['AWS_ACCESS_KEY_ID'] = '1111111'
os.environ['AWS_SECRET_ACCESS_KEY'] = '1111111'
os.environ['AWS_SESSION_TOKEN'] = '1111111'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-2'


def limit_collections_list():
    collections_to_mock = {
        'ec2': ('instance', 'instances'),
        'ec2': ('vpc', 'vpcs'),
        's3': ('bucket', 'buckets'),
        'iam': ('group', 'groups')
    }
    mock_collections = []
    for service, name_tuple in collections_to_mock.items():
        collection = MagicMock(**{
            'meta.service_name': service,
            'resource.model.shape': name_tuple[0]
        })
        collection.configure_mock(name=name_tuple[1])
        mock_collections.append(collection)
    cloudwanderer.cloud_wanderer.CloudWandererBoto3Interface.get_resource_collections = MagicMock(
        side_effect=lambda service_resource: [
            collection
            for collection in mock_collections
            if service_resource.meta.service_name == collection.meta.service_name
        ]
    )

def limit_services_list():
    cloudwanderer.cloud_wanderer.CloudWandererBoto3Interface.get_all_resource_services = MagicMock(
        return_value=[boto3.resource(service) for service in ['ec2', 's3', 'iam']])

def mock_services():
    for service in [mock_ec2, mock_iam, mock_sts, mock_s3, mock_dynamodb2]:
        mock = service()
        mock.start()

limit_services_list()
limit_collections_list()
mock_services()

cloudwanderer.storage_connectors.DynamoDbConnector = cloudwanderer.storage_connectors.MemoryStorageConnector
'''
