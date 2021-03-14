import unittest
from unittest.mock import MagicMock, call

from cloudwanderer import CloudWandererAWSInterface
from cloudwanderer.exceptions import UnsupportedServiceError

from ..helpers import get_default_mocker


class TestAWSInterfaceCleanup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mocker = get_default_mocker()
        mocker.start_general_mock(restrict_regions=["us-east-1", "eu-west-2", "ap-east-1"])

    @classmethod
    def tearDownClass(cls):
        get_default_mocker().stop_general_mock()

    def setUp(self):
        self.aws_interface = CloudWandererAWSInterface()

    def test_cleanup_resources_single_region_single_resource(self):
        mock_storage_connector = MagicMock()
        self.aws_interface.cleanup_resources(
            regions=["eu-west-2"], resource_types=["instance"], storage_connector=mock_storage_connector
        )

        mock_storage_connector.delete_resource_of_type_in_account_region.assert_called_once_with(
            service="ec2", resource_type="instance", account_id="123456789012", region="eu-west-2", urns_to_keep=None
        )

    def test_cleanup_resources_single_region_single_resource_with_subresources(self):
        mock_storage_connector = MagicMock()
        self.aws_interface.cleanup_resources(
            regions=["us-east-1"], resource_types=["role"], storage_connector=mock_storage_connector
        )

        mock_storage_connector.delete_resource_of_type_in_account_region.assert_has_calls(
            [
                call(
                    service="iam",
                    resource_type="role",
                    account_id="123456789012",
                    region="us-east-1",
                    urns_to_keep=None,
                ),
                call(
                    service="iam",
                    resource_type="role_policy",
                    account_id="123456789012",
                    region="us-east-1",
                    urns_to_keep=None,
                ),
            ]
        )

    def test_cleanup_resources_global_api_regional_resource_api_region(self):
        mock_storage_connector = MagicMock()
        self.aws_interface.cleanup_resources(
            regions=["us-east-1"], resource_types=["bucket"], storage_connector=mock_storage_connector
        )

        mock_storage_connector.delete_resource_of_type_in_account_region.assert_has_calls(
            [
                call(
                    service="s3",
                    resource_type="bucket",
                    account_id="123456789012",
                    region="us-east-1",
                    urns_to_keep=None,
                ),
                call(
                    service="s3",
                    resource_type="bucket",
                    account_id="123456789012",
                    region="eu-west-2",
                    urns_to_keep=None,
                ),
                call(
                    service="s3",
                    resource_type="bucket",
                    account_id="123456789012",
                    region="ap-east-1",
                    urns_to_keep=None,
                ),
            ]
        )

    def test_cleanup_resources_global_api_regional_resource_wrong_region(self):
        mock_storage_connector = MagicMock()
        self.aws_interface.cleanup_resources(
            regions=["eu-west-2"], resource_types=["bucket"], storage_connector=mock_storage_connector
        )

        mock_storage_connector.delete_resource_of_type_in_account_region.assert_not_called()

    def test_cleanup_resources_global_api_global_resource_wrong_region(self):
        mock_storage_connector = MagicMock()
        self.aws_interface.cleanup_resources(
            regions=["eu-west-2"], resource_types=["bucket"], storage_connector=mock_storage_connector
        )

        mock_storage_connector.delete_resource_of_type_in_account_region.assert_not_called()

    def test_cleanup_resources_unsupported_service(self):
        mock_storage_connector = MagicMock()
        with self.assertRaises(UnsupportedServiceError):
            list(
                self.aws_interface.cleanup_resources(
                    service_names=["unicorn_stable"], storage_connector=mock_storage_connector
                )
            )

    def test_cleanup_resources_unsupported_resource_type(self):
        mock_storage_connector = MagicMock()

        self.aws_interface.cleanup_resources(resource_types="unicorn", storage_connector=mock_storage_connector)

        mock_storage_connector.delete_resources_of_type_in_account_region.assert_not_called()

    def test_cleanup_resources_exclude_resources(self):
        mock_storage_connector = MagicMock()

        self.aws_interface.cleanup_resources(
            service_names=["ec2"], exclude_resources=["ec2:instance"], storage_connector=mock_storage_connector
        )

        mock_storage_connector.delete_resources_of_type_in_account_region.assert_not_called()
