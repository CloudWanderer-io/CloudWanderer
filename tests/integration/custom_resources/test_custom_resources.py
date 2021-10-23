import json
import logging
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cloudwanderer.urn import URN

from ..pytest_helpers import compare_list_of_dicts_allow_any

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
                # **{"meta": aws_interface.cloudwanderer_boto3_session.client(test_spec["service"]).meta},
                **test_spec["mockData"],
            }
        ),
    )

    if "getResource" in test_spec:
        urn = URN.from_string(test_spec["getResource"]["urn"])
        logger.info("Getting resource %s", urn)
        result = list(aws_interface.get_resource(urn=urn))
    if "getResources" in test_spec:
        get_resources = test_spec["getResources"]
        logger.info("Getting resources %s", get_resources)
        result = list(
            aws_interface.get_resources(
                service_name=get_resources["serviceName"],
                resource_type=get_resources["resourceType"],
                region=get_resources["region"],
            )
        )

    compare_list_of_dicts_allow_any(
        [dict(x) for x in result], test_spec["expectedResults"], allow_partial_match_second=True
    )
