"""Utils for the CloudWanderer AWS Interface."""
import logging
import re
from collections import defaultdict
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _get_urn_components_from_string(regex_pattern, string) -> Dict[str, Any]:
    result = re.match(regex_pattern, string)
    if not result:
        return {}
    urn_components = defaultdict(list)
    for component_name, component_value in result.groupdict().items():
        if component_name in ["cloud_name", "account_id", "region", "service", "resource_type"]:
            logger.debug("Found %s:%s from %s", component_name, component_value, regex_pattern)
            urn_components[component_name] = component_value
            continue
        if component_name.startswith("id_part_"):
            urn_components["resource_id_parts"].append(component_value)
    return urn_components
