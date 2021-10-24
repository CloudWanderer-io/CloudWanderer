Getting action templates (i.e. uninflated get/cleanup actions)
=================================================================
I originally went down the path of making the responsibility for resolving a list of actions belong to the service ServiceResource object
But then the ServiceResource object ends up iterating through teh service map and resource maps of all its resources and their subresources.
This is decidedly suboptimal because it should be the responsible of each resource ServiceResource object to tell us about its own actions and no-one elses.
e.g. iam roles should tell you about how to discover iam role and inline policies, but the iam service shouldn't know anything about it directly.
The downside to doing this is that it pushes the logic for discovering actions for each service and each resource into the AWSinterface object which would make it very hard to
test.
You could make it easier to test by splitting out the iteration layers into separate functions inside the AWSInterface object.
Maybe this warrants an object of its own, but then we have to call its intro method from the AWSInterface anyway as we don't want the cloudwanderer object to have to know about a
CloudInterface object AND a CloudActionGenerator object...
The other problem with that is that then any documentation that depends on this will need to call the AWSinterface object for this information when really it feels like it's information
about the resources. You could get the documentation generator to do the same iteration over services and resource as... well, it would need to anyway if it's going to document them
isn't it?

Hell I originally pushes it through teh Session object.. that made no sense whatsoever, what has it got to do with teh session?
