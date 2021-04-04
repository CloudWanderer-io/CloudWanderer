# Project Advanced Query Coverage Parity

This folder contains files used to track the ongoing task of coverage parity with AWS Config Advanced Query.

The `.delta` file contains a list of GitHub CLI commands that have been used to create tickets for each
AWS Config Advanced Query supported resource.

As time goes on we should continue running the shell script which generates this file `advanced-query-parity-generator.sh` against the latest version of the [AWS Config Resource Schema](https://github.com/awslabs/aws-config-resource-schema) repo which powers AWS Config Advanced Query and run any new GitHub CI commands that are generated.
