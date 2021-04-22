#!/usr/bin/env python
"""Setup CloudWanderer package."""
import re
from os import path

from setuptools import find_packages, setup

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.rst"), encoding="utf-8") as f:
    long_description = re.sub(r"..\s+doctest\s+::", ".. code-block ::", f.read())

setup(
    version="0.18.0",
    python_requires=">=3.6.0",
    name="cloudwanderer",
    packages=find_packages(include=["cloudwanderer", "cloudwanderer.*"]),
    description="A Python package which wanders across your AWS account and records your resources in DynamoDB",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author="Sam Martin",
    author_email="samjackmartin+cloudwanderer@gmail.com",
    url="https://github.com/CloudWanderer-io/CloudWanderer",
    install_requires=["boto3", "jmespath", 'typing_extensions; python_version < "3.8.0"'],
    package_data={
        "": ["**/*.json", "py.typed"],
    },
)
