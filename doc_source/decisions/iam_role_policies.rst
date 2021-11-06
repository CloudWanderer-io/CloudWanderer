IAM Role Policies
===================

IAM Role policies come in two varieties:

1. Inline Policies
2. Managed Policies

The former is a dependent resource (because to list inline policies you must supply the ``RoleName`` to the ``ListRolePolicies`` function).
The latter is a top-level resource (i.e. it can be discovered without supplying any arguments to the ``ListPolicies`` function) but discovering the relationship
between the Role and the Managed Policies attached to it requires a call to the ``ListAttachedRolePolicies`` function.

This is why the ``resources-1.json`` and ``resources-cw-1.json`` seem so asymmetric by having:

1. ``RoleManagedPolicyAttachments`` (a secondary attribute)
2. ``RolePolicy`` (a dependent resource)
3. ``Policy`` (a base resource)

The order of operations when discovering roles and their policies is as follows:

1. List roles
2. Fetch each role's secondary attributes (``RoleManagedPolicyAttachments``)
3. Create a ``Relationship`` on the ``Role`` with each ``RoleManagedPolicyAttachment``
4. Fetch each role's dependent resources (``RolePolicy``)

Interestingly this involves actually _moving_ ``AttachedPolicies`` (and renaming to ``RoleManagedPolicyAttachments``) from ``hasMany`` to ``has``.
This is because we want to have ``RoleManagedPolicyAttachments`` as an secondary attribute rather than a dependent resource (as that would create a resource that was an _attachment_ which would make no sense.).
Once we have it as a secondary attribute on the role we can use it to create relationships to the indenpendently discovered managed policies. 
