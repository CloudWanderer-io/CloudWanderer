from typing import OrderedDict
from pytest import fixture
import pytest

from cloudwanderer.aws_interface.boto3_loaders import MergedServiceLoader
from cloudwanderer.exceptions import UnsupportedServiceError


@fixture
def merged_service_loader():
    return MergedServiceLoader()


def test_list_available_services(merged_service_loader):
    assert "lambda" in merged_service_loader.list_available_services()
    assert "sns" in merged_service_loader.list_available_services()


def test_load_service_model_cw(merged_service_loader):
    result = merged_service_loader.load_service_model(
        service_name="lambda", type_name="resources-1", api_version="2015-03-31"
    )
    assert result["resources"]
    assert "Function" in result["resources"]
    assert isinstance(result, OrderedDict)


def test_load_service_model_boto3(merged_service_loader):
    result = merged_service_loader.load_service_model(
        service_name="sns", type_name="resources-1", api_version="2010-03-31"
    )
    assert result["resources"]
    assert "Topic" in result["resources"]
    assert isinstance(result, OrderedDict)


def test_load_service_model_no_api_version(merged_service_loader):
    result = merged_service_loader.load_service_model(service_name="lambda", type_name="resources-1", api_version=None)
    assert result["resources"]
    assert "Function" in result["resources"]
    assert isinstance(result, OrderedDict)


def test_list_api_versions(merged_service_loader):
    result = merged_service_loader.list_api_versions(service_name="lambda", type_name="resources-1")
    assert result == ["2015-03-31"]


def test_list_api_versions_incorrect_type_name(merged_service_loader):

    with pytest.raises(UnsupportedServiceError) as excinfo:
        result = merged_service_loader.list_api_versions(service_name="lambda", type_name="resources-2")
    assert "lambda is not supported by either Boto3 or CloudWanderer's custom services" in str(excinfo.value)


def test_determine_latest_version(merged_service_loader):
    result = merged_service_loader.determine_latest_version(service_name="lambda", type_name="resources-1")
    assert result == "2015-03-31"
