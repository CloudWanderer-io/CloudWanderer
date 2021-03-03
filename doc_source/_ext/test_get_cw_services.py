import unittest
from unittest.mock import patch

from supported_resources import GetCwServices


class TestGetCwServices(unittest.TestCase):
    def setUp(self) -> None:
        self.getter = GetCwServices()

    def test_get_secondary_attributes(self):
        service = self.getter.services.get_service("iam")
        resource = service._get_empty_resource("role")

        result = self.getter.get_secondary_attributes(service=service, resource=resource)

        assert (
            result
            == """
.. py:class:: iam.role.role_inline_policy_attachments

    A secondary attribute for the :class:`iam.role`
    resource type.

    **Example:**

    .. code-block ::

        resources = storage_connector.read_resources(
            service="iam",
            resource_type="role")
        for resource in resources:
            resource.get_secondary_attribute(name="role_inline_policy_attachments")


.. py:class:: iam.role.role_managed_policy_attachments

    A secondary attribute for the :class:`iam.role`
    resource type.

    **Example:**

    .. code-block ::

        resources = storage_connector.read_resources(
            service="iam",
            resource_type="role")
        for resource in resources:
            resource.get_secondary_attribute(name="role_managed_policy_attachments")

"""
        )

    def test_get_subresources(self):
        service = self.getter.services.get_service("iam")
        resource = service._get_empty_resource("role")

        result = self.getter.get_subresources(service, resource)
        assert (
            [x.rstrip() for x in result.split("\n")]
            == (
                """
.. py:class:: iam.role.role_policy

    A subresource of :class:`iam.role`.



    **Example:**

    .. code-block ::

        resources = storage_connector.read_resources(
            service="iam",
            resource_type="role_policy")
        for resource in resources:
            resource.load()
            print(resource.urn)
            print(resource.policy_document)
            print(resource.policy_name)



    .. py:attribute:: policy_document

         The policy document. IAM stores policies in JSON format. However, resources that were created using AWS CloudFormation templates can be formatted in YAML. AWS CloudFormation always converts a YAML policy to JSON format before submitting it to IAM.


    .. py:attribute:: policy_name

         The name of the policy.

"""
            ).split("\n")
        )

    def test_generate_resources_section(self):
        service = self.getter.services.get_service("iam")
        resource = service._get_empty_resource("role")
        result = self.getter.generate_resource_section(service, resource, "{service_name}.{resource_name}")

        assert (
            [x.rstrip() for x in result.split("\n")]
            == """
.. py:class:: iam.role



    **Example:**

    .. code-block ::

        resources = storage_connector.read_resources(
            service="iam",
            resource_type="role")
        for resource in resources:
            resource.load()
            print(resource.urn)
            print(resource.arn)
            print(resource.assume_role_policy_document)
            print(resource.create_date)
            print(resource.description)
            print(resource.max_session_duration)
            print(resource.path)
            print(resource.permissions_boundary)
            print(resource.role_id)
            print(resource.role_last_used)
            print(resource.role_name)
            print(resource.tags)



    .. py:attribute:: arn

         The Amazon Resource Name (ARN) specifying the role. For more information about ARNs and how to use them in policies, see `IAM Identifiers <https://docs.aws.amazon.com/IAM/latest/UserGuide/Using_Identifiers.html>`__ in the *IAM User Guide* guide.


    .. py:attribute:: assume_role_policy_document

         The policy that grants an entity permission to assume the role.


    .. py:attribute:: create_date

         The date and time, in `ISO 8601 date-time format <http://www.iso.org/iso/iso8601>`__ , when the role was created.


    .. py:attribute:: description

         A description of the role that you provide.


    .. py:attribute:: max_session_duration

         The maximum session duration (in seconds) for the specified role. Anyone who uses the AWS CLI, or API to assume the role can specify the duration using the optional ``DurationSeconds`` API parameter or ``duration-seconds`` CLI parameter.


    .. py:attribute:: path

         The path to the role. For more information about paths, see `IAM Identifiers <https://docs.aws.amazon.com/IAM/latest/UserGuide/Using_Identifiers.html>`__ in the *IAM User Guide* .


    .. py:attribute:: permissions_boundary

         The ARN of the policy used to set the permissions boundary for the role. For more information about permissions boundaries, see `Permissions Boundaries for IAM Identities <https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html>`__ in the *IAM User Guide* .


    .. py:attribute:: role_id

         The stable and unique string identifying the role. For more information about IDs, see `IAM Identifiers <https://docs.aws.amazon.com/IAM/latest/UserGuide/Using_Identifiers.html>`__ in the *IAM User Guide* .


    .. py:attribute:: role_last_used

         Contains information about the last time that an IAM role was used. This includes the date and time and the Region in which the role was last used. Activity is only reported for the trailing 400 days. This period can be shorter if your Region began supporting these features within the last year. The role might have been used more than 400 days ago. For more information, see `Regions Where Data Is Tracked <https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_access-advisor.html#access-advisor_tracking-period>`__ in the *IAM User Guide* .


    .. py:attribute:: role_name

         The friendly name that identifies the role.


    .. py:attribute:: tags

         A list of tags that are attached to the specified role. For more information about tagging, see `Tagging IAM Identities <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_tags.html>`__ in the *IAM User Guide* .

""".split(
                "\n"
            )
        )

    @patch("supported_resources.open")
    def test_write_cloudwanderer_services(self, mock_open):

        self.getter.write_cloudwanderer_services()

        mock_open.return_value.__enter__.return_value.write.assert_any_call(
            'sqs\n---\n\n\n.. py:class:: sqs.queue\n\n    \n\n    **Example:**\n\n    .. code-block ::\n\n        resources = storage_connector.read_resources(\n            service="sqs",\n            resource_type="queue")\n        for resource in resources:\n            resource.load()\n            print(resource.urn)\n            print(resource.attributes)\n\n\n\n    .. py:attribute:: attributes\n\n         A map of attributes to their respective values.\n\n\n\n\n\n'
        )

    def test_get_cloudwanderer_services(self):

        result = list(self.getter.get_cloudwanderer_services())

        assert {
            "cloudformation",
            "opsworks",
            "cloudwatch",
            "secretsmanager",
            "apigateway",
            "s3",
            "sqs",
            "lambda",
            "ec2",
            "glacier",
            "sns",
            "iam",
            "dynamodb",
        }.issubset(set(result))
