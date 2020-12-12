#!/usr/bin/env python
from os import path
from setuptools import setup, find_packages

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    version='0.3.2',
    python_requires='>=3.6.0',
    name='cloudwanderer',
    packages=find_packages(include=['cloudwanderer', 'cloudwanderer.*']),
    description='A Python package which wanders across your AWS account and records your resources in DynamoDB',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Sam Martin',
    author_email='samjackmartin+cloudwanderer@gmail.com',
    url='https://github.com/CloudWanderer-io/CloudWanderer',
    install_requires=['boto3'],
    package_data={
        "": [
            "**/*.json"
        ],
    }

)
