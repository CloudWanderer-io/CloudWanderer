# 0.17.0

## New Resources
 - Added ec2 vpc endpoints support
 - Added ec2 vpc endpoint services support
 - Added ec2 elastic IP support
 - Added elbv2 target group support
 - Added elbv2 load balancer support


# 0.16.1

- Fixed memory leak due where decorating with `lru_cache` caused old objects' caches not to be garbage collected.

# 0.16.0

- Allow subresources in `write_resource`
- Escaped URNs with forward slashes
- Provided way to explicitly specify base resources with multiple identifiers as a base resource.
- URNs are now made up of unlimited resource ids aka `resource_id_parts`.
- URNs now have a `resource_id_parts_parsed` which will attempt to convert non-string id parts into their appropriate type (fixing a bug preventing us from getting lambda layer versions from URN)
- Added Boto3 resource/service definitions as part of service maps as the first steps to making service maps wrap Boto3 definitions fully.
- Resources and subresources no longer have to have specific numbers of identifiers, fixing a bug that caused Cloudwatch Metrics to be misidentified as a subresource.
- Service and Resource maps now have a `boto3_definition` attribute which is the start of the work to have service maps properly superordinate to Boto3 definitions.
- `resource_summary` now includes more detailed information about subresources
- `CloudWandererResource` now generates `parent_urn` property from service mapping data using its news `boto3_definition` property.

## Resources

- Added AutoScalingGroup fixing [#123](https://github.com/CloudWanderer-io/CloudWanderer/issues/123)
- Added load operation for lambda layer versions


# 0.15.0

- Added `lambda` `layer` resource type.
- Added `lambda` `layer_version` subresource type.
- Added `py.typed` for PEP561 support.
- Added documentation on writing custom resource definitions.
- Fixed bug where resources could not build URNs if they had non-string ID components.

# 0.14.1

 - Implemented `mypy` type checking
 - Corrected a huge number of type hints
 - Reformalised arguments for `get_resources` on storage_connectors.
 - Fixed DynamoDB pagination

# 0.14.0

 - Added `parent_urn` and `subresource_urn` properties to the `CloudWanderResource` class.
 - Added new DynamoDB secondary index `parent_urn`
 - Fixed bug where subresources were not cleaned up when `write_resource` was called on `CloudWanderer`
 - Stripped out DynamoDB record specific attributes which were polluting Secondary Attributes dictionaries.
 - Changed `AWSInterface` `get_resources` to expect specific service, resource type, region arguments instead of reusing the arguments from CloudWanderer `write_resources`.
 - Added `get_actions` to `AWSInterface` which returns a list of `GetAndCleanUp` objects which pair `GetAction`s and `CleanUpAction`s.
 - CloudWanderer's `write_resources` now contains the logic for iterating over each `GetAction`, calling `get_resources` on `AWSInterface` and calling `delete_resource_of_type_in_account_region` on each StorageConnector in accordance with the `CleanUpAction`.
 - Added `get_and_cleanup_actions` property to `CloudWandererBoto3Resource` so the responsibility for defining `GetAndCleanUp` objects resides with the resource. This provides maximum flexibility for asymmetric region/resource discovery (like S3 buckets).
 - Added `get_empty_service` to `Boto3Services` to minimise the number of unnecessary (and expensive) Boto3 client creations when generating get and cleanup actions.

# 0.13.2

- Fixed bug causing subresources to inherit the secondary attributes of their parent resource erroneously.

# 0.13.1

- Fixed bug that prevented global services with regional resources being cleaned up properly.
- Fixed bug that prevented subresources from being cleaned up.
- Subresources are now written by `write_resource`.

# 0.13.0

- Added `get_resource` to `CloudWanderer` to allow the writing of a single resource based on its URN
- Added `get_resource` to `CloudWandererAWSInterface` to allow the getting of a single resource based on its URN
- Added `get_resource_by_urn` to `Boto3Getter` to support `CloudWandererAWSInterface`
- Normalised custom error exception names to have Error at the end as per PEP8
- Renamed `CloudWandererBoto3Interface` to `CloudWandererAWSInterface`
- Renamed `AwsUrn` to `URN`
- Added `storage_connector_generator` to `write_resources_concurrently` to handle non thread safe storage connectors (hopefully fixing #86)
- Refactored `Boto3Getter` into service and resource oriented wrappers for Boto3 objects to make it more domain drive and easier to understand.
- Added support for Boto3 subresources (where they match the CloudWanderer definition of a subresource)

# 0.12.0

- Changed the way `exclude_resources` works so you can differentiate between CloudFormation Stacks and OpsWorks Stacks #70
- Formalised the interface between the `CloudInterface` > `CloudWanderer` > `StorageConnector` by
    converting Boto3 resources to `CloudWandererResources`
    - Removed `write_secondary_attributes` from `BaseStorageConnector` as it's no longer required to be public.
- Added `name` argument to `get_secondary_attribute` allowing you to get secondary attributes by name.
- Ensured that all resource attributes that *can* exist *do* exist when `CloudWandererResource` returned from `CloudWandererBoto3Interface`, irrespective of whether they were returned in that particular API call.

## New Resources

- apigateway rest_api
- secretsmanager secret

# 0.11.0

- Collapsed all `write_secondary_attributes` methods into `write_resources` so secondary attributes are written automatically.
- Moved AWS specific methods to `CloudWandererBoto3Interface`
- Fixed bug that would have prevented global services with regional resources being cleaned properly.
    This was due to cleanup only happening in the global service region, and being limited to
    cleaning up resources in that region. E.g. it would write buckets from all regions from `us-east-1`
    and then _only_ cleanup `us-east-1` s3 buckets.
- Removed `client_args` as an explicit argument on cloudwanderer resources, any keywords args supplied to `write_` methods are now passed into the `get_` methods of the `cloud_interface`
- Subresources now build their compound id using a `/` separator rather than a `:` separator. This ensures that
    `:` remains the primary separator for URN parts.

# 0.10.2

 - Reuse service definition objects via `_get_resource_definitions` to save on time spent reinstantiating identical objects
 - Only instantiate the default `ServiceMapping` from `get_service_mapping` if it's required.
 - Reduced number of regions tested from _all_ to 3.

# 0.10.1

- S3 buckets and other regional resources of global services will now only be written in their service's globalRegion
- Fixed bug where AWSUrn did not parse subresources URNs correctly
- Improved cloudwanderer tests by leveraging `MemoryStorageConnector`

# 0.10.0

- Added `role_managed_policy_attachments` secondary attribute
- Added `role_inline_policy_attachments` secondary attribute
- Collapsed secondary attribute definitions into custom resource definitions
- Collapsed boto3 resources into custom resource definitions
- Abstracted GlobalServiceMaps to ServiceMaps as supporting metadata CloudWanderer needs to understand resources
- Resources with multple identifiers now include all identifiers as part of the AWSUrn
- Split out experimental concurrency into separate `write_resources_concurrently` method.

# 0.9.0

- Added `get_secondary_attribute` to `CloudWandererResource`
- Added `is_inflated` to `CloudWandererResource`
- Storage Standardisation improvements
    - Standardised storage connector write tests
    - Deleted duplicate read tests
    - Added `write_resource_attribute` to `BaseStorageConnector`
    - Added `write_resource_attribute` to `MemoryStorageConnector`
    - Renamed `resource_attributes` to `secondary_attributes`
- Fixed bug where `write_secondary_attributes` would enumerate services which did not have secondary attributes.

# 0.8.0

- Added support for multiple storage connectors
- Made Storage Connectors the primary interface for reading from storage
    - `read_resource` on DynamoDbStorageConnector returns a `CloudWandererResource` instead of an iterator.
    - `read_resource` on MemoryStorageConnector returns a `CloudWandererResource` instead of an iterator.
    - Added `read_resources` to DynamoDbStorageConnector
    - Added `read_resources` to MemoryStorageConnector
    - Removed `read_resource_of_type` from DynamoDBStorageConnector
    - Removed `read_resource_of_type_in_account` from DynamoDBStorageConnector
    - Removed `read_all_resources_in_account` from DynamoDBStorageConnector
    - Removed `read_resource_of_type` from BaseStorageConnector
    - Removed `read_resource_of_type_in_account` from BaseStorageConnector
    - Removed `read_all_resources_in_account` from BaseStorageConnector
    - Removed `read_resource_of_type` from MemoryStorageConnector
    - Removed `read_resource_of_type_in_account` from MemoryStorageConnector
    - Removed `read_all_resources_in_account` from MemoryStorageConnector
    - Removed `read_resource_of_type` from CloudWanderer
    - Removed `read_resource` from CloudWanderer
    - Removed `read_all_resources_in_account` from CloudWanderer
    - Removed `read_resource_of_type_in_account` from CloudWanderer
- Added  dynamodb filter expressions to increase flexibility of `get_resources`
- Added attribute projections for urn parts to DynamoDB Global Secondary Indexes

# 0.7.1

- Bugfix Memory Storage Connector to return None from `read_resource`

# 0.7.0

- Added MemoryStorageConnector (useful for testing)
- Added `load` method to `CloudWandererResource`
- Added `load` support to `MemoryStorageConnector`
- Added `load` support to `DynamoDbConnector`

# 0.6.0

- Fetch region information for semi-global resources like S3 buckets using `GlobalServiceMapping` objects.
- Identify global services and their primary region using `GlobalServiceMapping` objects.
- No longer queries services which do not exist in the region being queried
- No longer writes resources which do not exist in the region being queried
- Added type hints
- Added client_args
- Added `write_all_resource_attributes`
- Added `write_resource_attributes_of_type`
- Made `CustomResourceDefinitions` work more like a `ServiceResource` object with a `resource()` method
- Renamed `write_all_resources` to `write_resources_in_region`
- Renamed `write_resources` to `write_resources_of_service_in_region`
- Renamed `write_resources_of_type` to `write_resources_of_type_in_region`
- Renamed `write_all_resource_attributes` to `write_resource_attributes_in_region`
- Renamed `write_resource_attributes` to `write_resource_attributes_of_service_in_region`
- Renamed `write_resource_attributes_of_type` to `write_resource_attributes_of_type_in_region`
- Added `write_resources` which pulls resources from all regions.
- Added `write_resource_attributes` which pulls resource attributes from all regions.
- Handle `EndpointConnectionError`s which occur when a service is not supported in a region.
- Added experimental multithreading support
- Updated logger to log to filename logger rather than `root`

# 0.5.0

 - Add tests for storage connector
 - Fixed return of read_all on storage connector
 - Added delete_resource on storage connector
 - Added delete_resource_of_type_in_account_region on storage connector
 - write_resources in CloudWanderer now deletes resources which no longer exist.
 - Added param for number_of_shards for dynamodb connector rather than hardcoding it.

# 0.4.0

- Introduced more structured `CloudWandererResource` result object to ensure resource attribute keys don't clash with resource keys.
- Refactored `CloudWanderer` main class and abstracted much of it into `CloudWandererInterface`
- Added boto3 `Sesssion` support to allow passing of non-default credentials and configuration options.
