from typing import Optional
from pathlib import Path

from aws_cdk import (
    aws_lambda as _lambda,    
    aws_ec2 as ec2,   
    Duration,
)

def create_lambda_image(
    self,
    id: str,
    directory: str,
    env: dict,
    vpc: ec2.Vpc,
    sg: ec2.SecurityGroup,    
) -> _lambda.Function:
    """Create a Lambda function using a Docker image. Needed because of the size of the dependencies."""
    return _lambda.DockerImageFunction(
        self,
        id,
        code=_lambda.DockerImageCode.from_image_asset('./src/api/lambdas',
            build_args={
                "DIRECTORY": directory
            },
            cmd=[f"{directory}.handler.handler"]
        ),
        memory_size=1024,
        vpc=vpc,
        vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        security_groups=[sg],
        timeout=Duration.seconds(30),
        environment=env,
    )

def create_lambda_function(
    self,
    id: str,
    handler_path: str,
    env: Optional[dict] = None,
    vpc: Optional[ec2.Vpc] = None,
    sg: Optional[ec2.SecurityGroup] = None,   
) -> _lambda.Function:
    kwargs = {
        "runtime": _lambda.Runtime.PYTHON_3_12,
        "handler": handler_path,
        "code": _lambda.Code.from_asset("./src/api/lambdas"),
        "memory_size": 1024,        
        "timeout": Duration.seconds(30),
    }
    if vpc and sg:
        kwargs.update({
            "vpc": vpc,
            "vpc_subnets": ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            "security_groups": [sg],
        })
    if env:
        kwargs["environment"] = env
    return _lambda.Function(self, id, **kwargs)
 
def _read_env_file(key: str) -> str:
    """Read a specific key from .env.local file"""
    env_path = Path.cwd() / "src" / "ui" / ".env.local"
    if not env_path.exists():
        raise FileNotFoundError(f".env.local file not found at {env_path}")
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                if k.strip() == key:
                    return v.strip().strip('\'"')
    raise ValueError(f"Environment variable '{key}' not found in .env.local")