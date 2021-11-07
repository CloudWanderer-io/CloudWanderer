Resource Filtering
=====================

I did consider doing resource filtering by adding filters to ActionSets but the major complexity ended up being how to handle
dependent resource filters as those currently are not represented in ``get_urns`` and that would have resulted in even more major a rewrite
than replacing ``get_urns`` with ``GetResourceTypeAction`` objects on ``ActionSet``s.
