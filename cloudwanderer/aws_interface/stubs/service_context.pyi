from botocore.model import ServiceModel
from botocore.waiter import WaiterModel

class ServiceContext:
    service_name: str
    service_model: ServiceModel
    service_waiter_model: WaiterModel
