from aws_cdk import (   
    Stack,    
)
from constructs import Construct

from .infra_ui import create_ui_infrastructure
from .infra_api import create_api_infrastructure

class DynamicRagStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # Create UI Infrastructure
        create_ui_infrastructure(self)  
        # Create API Infrastructure
        create_api_infrastructure(self)

        
