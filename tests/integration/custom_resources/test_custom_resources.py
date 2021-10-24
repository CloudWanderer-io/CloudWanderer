import json
import logging
import os
from pathlib import Path
from unittest.mock import MagicMock

import botocore
import pytest

from cloudwanderer.urn import URN

from ..pytest_helpers import compare_list_of_dicts_allow_any, prepare_for_comparison

logger = logging.getLogger(__name__)


def get_resources_to_test():
    results = []
    for root, dirs, files in os.walk(Path(__file__).parent):
        for file in files:
            if file.endswith(".json"):
                results.append(os.path.join(root, file))
    return results


@pytest.mark.parametrize("file_name", get_resources_to_test())
def test_all_custom_resources(file_name, aws_interface):
    with open(file_name) as f:
        test_spec = json.load(f)

    aws_interface.cloudwanderer_boto3_session.client = MagicMock(
        return_value=MagicMock(
            **{
                **{"meta": aws_interface.cloudwanderer_boto3_session.client(test_spec["service"]).meta},
                **test_spec["mockData"],
            }
        ),
    )

    if "getResource" in test_spec:
        urn = URN.from_string(test_spec["getResource"]["urn"])
        logger.info("Getting resource %s", urn)
        try:
            result = prepare_for_comparison(aws_interface.get_resource(urn=urn))
        except botocore.model.NoShapeFoundError as ex:
            raise ValueError(
                "Boto3 raised a NoShapeFoundError, this suggests your test has the wrong service name specified"
            ) from ex
    if "getResources" in test_spec:
        get_resources = test_spec["getResources"]
        logger.info("Getting resources %s", get_resources)
        try:
            result = prepare_for_comparison(
                aws_interface.get_resources(
                    service_name=get_resources["serviceName"],
                    resource_type=get_resources["resourceType"],
                    region=get_resources["region"],
                )
            )

        except NotImplementedError as ex:
            raise ValueError(
                "Boto3 raised a NotImplementedError, usually this means "
                "you forgot to wrap your paginate.return_results in a list or "
                "include the key at the top level (e.g. Instances)"
            ) from ex
        except botocore.model.NoShapeFoundError as ex:
            raise ValueError(
                "Boto3 raised a NoShapeFoundError, this suggests your test has the wrong service name specified"
            ) from ex

    compare_list_of_dicts_allow_any(
        test_spec["expectedResults"], [dict(x) for x in result], allow_partial_match_first=True
    )
