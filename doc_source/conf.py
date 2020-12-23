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
release = '0.6.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autodoc.typehints',
    'sphinx.ext.doctest',
    'sphinxarg.ext',
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
import sys
from decimal import Decimal
from unittest.mock import MagicMock
import logging
import cloudwanderer

# Mocking
mock_collection = MagicMock(**{
    'meta.service_name': 'ec2',
})
mock_collection.configure_mock(name='instances')
cloudwanderer.cloud_wanderer.boto3 = MagicMock(**{
    'Session.return_value.get_available_resources.return_value': ['ec2'],
    'resource.return_value.meta.resource_model.collections': [mock_collection],
    'resource.return_value.meta.service_name': 'ec2'

})

cloudwanderer.storage_connectors.DynamoDbConnector = MagicMock(**{
    'return_value.init.return_value': None,
    'return_value.read_resource_of_type.return_value': iter([
        cloudwanderer.cloud_wanderer.CloudWandererResource(
            urn=cloudwanderer.AwsUrn(
                account_id='111111111111',
                region='eu-west-2',
                service='lambda',
                resource_type='function',
                resource_id='awesomeproject-201904202316-HostedUICustomResource-1PLE213GNV66A'
            ),
            resource_data={}, resource_attributes=[]
        )
    ]),
    'return_value.read_resource.return_value': iter([
        cloudwanderer.cloud_wanderer.CloudWandererResource(
            urn=cloudwanderer.AwsUrn(
                account_id='111111111111',
                region='eu-west-2',
                service='lambda',
                resource_type='function',
                resource_id='awesomeproject-201904202316-HostedUICustomResource-1PLE213GNV66A'
            ),
            resource_data={
                'FunctionArn': str('arn:aws:lambda:eu-west-2:111111111111:function'
                ':awesomeproject-201904202316-HostedUICustomResource-1PLE213GNV66A'),
                'MemorySize': Decimal('128'),
                'Description': '',
                'TracingConfig': {'Mode': 'PassThrough'},
                'Timeout': Decimal('300'),
                'Handler': 'index.handler',
                'CodeSha256': 'fBLFD+AwFo/EQK5rdUweTW8jdBg6cw9LORbpVYqlXXQ=',
                'RevisionId': '7fd173f0-0fc0-4df3-a4c3-5464431da769',
                'Role': 'arn:aws:iam::111111111111:role/cognitod72684bb_userpoolclient_lambda_role-dev',
                'LastModified': '2019-04-20T22:32:07.805+0000',
                'FunctionName': 'awesomeproject-201904202316-HostedUICustomResource-1PLE213GNV66A',
                'Runtime': 'python3.8',
                'CodeSize': Decimal('1742'),
                'Version': '$LATEST',
                'PackageType': 'Zip'
            }
        )
    ])
})
'''
