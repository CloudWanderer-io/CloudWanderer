# 0.8.0

- `read_resource` on DynamoDbStorageConnector returns a `CloudWandererResource` instead of an iterator.
- `read_resource` on MemoryStorageConnector returns a `CloudWandererResource` instead of an iterator.
- added `read_resources` to DynamoDbStorageConnector
- added `read_resources` to MemoryStorageConnector
- Removed `read_resource_of_type` from DynamoDBStorageConnector
- Removed `read_resource_of_type_in_account` from DynamoDBStorageConnector
- Removed `read_all_resources_in_account` from DynamoDBStorageConnector
- Removed `read_resource_of_type` from BaseStorageConnector
- Removed `read_resource_of_type_in_account` from BaseStorageConnector
- Removed `read_all_resources_in_account` from BaseStorageConnector
- Removed `read_resource_of_type` from MemoryStorageConnector
- Removed `read_resource_of_type_in_account` from MemoryStorageConnector
- Removed `read_all_resources_in_account` from MemoryStorageConnector

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
