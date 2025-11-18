from aws_cdk import (
    aws_apigateway as apigw,
    aws_lambda as _lambda,    
    aws_lambda_python_alpha as lambda_python,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    Duration,
    Stack
)

import json

def create_api_infrastructure(self: Stack):
    vpc = ec2.Vpc(self, "DynamicRagVPC",
        max_azs=2,
        cidr="10.5.0.0/16",
        nat_gateways=0,
        subnet_configuration=[
            ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.PUBLIC,
                name="Public",
                cidr_mask=26
            ),
            ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                name="DB",
                cidr_mask=26
            ),
        ],        
    )

    secretDb = secretsmanager.Secret(
        self,
        "DynamicRagDbSecret",
        secret_name="dynamic-rag/db_creds",
        generate_secret_string=secretsmanager.SecretStringGenerator(
            secret_string_template=json.dumps({"username": "dynamic_rag_user"}),
            exclude_punctuation=True,
            generate_string_key="password",
        ),
    )

    lambdaSecurityGroup = ec2.SecurityGroup(self, "DynamicRagLambdaSecurityGroup",
        vpc=vpc,
        security_group_name="security_group_lambda",
        allow_all_outbound=True,
    )        
    
    subnetGroup = rds.SubnetGroup(self, "DynamicRagSubnetGroup",
        vpc=vpc,
        vpc_subnets=ec2.SubnetSelection(
            subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
        ),
        subnet_group_name="postgres-subnet-group",
        description="Subnet group for postgres",
    )

    securityGroup = ec2.SecurityGroup(self, "DynamicRagDBSecurityGroup",
        vpc=vpc,
        security_group_name="security_group_db",
        allow_all_outbound=True,
    )

    securityGroup.add_ingress_rule(
        peer=lambdaSecurityGroup,
        connection=ec2.Port.tcp(5432),
    )

    parameterGroup = rds.ParameterGroup(self, "DynamicRagPostgresParameterGroup",
        engine=rds.DatabaseInstanceEngine.postgres(
            version=rds.PostgresEngineVersion.VER_17_6
        ),
        parameters={
            "max_standby_streaming_delay": "600000",  # milliseconds (5 minutes)
            "max_standby_archive_delay": "600000",  # milliseconds (5 minutes)
        },
    )    

    postgres = rds.DatabaseInstance(self, "DynamicRagPostgresDB",
        instance_identifier="dynamic-rag-postgres",
        engine=rds.DatabaseInstanceEngine.postgres(
            version=rds.PostgresEngineVersion.VER_17_6
        ),
        instance_type=ec2.InstanceType.of(
            ec2.InstanceClass.T4G, ec2.InstanceSize.MICRO
        ),
        parameter_group=parameterGroup,
        allocated_storage=20,
        max_allocated_storage=100,
        credentials=rds.Credentials.from_secret(secretDb),
        database_name="dynamic_rag_db",
        vpc=vpc,
        subnet_group=subnetGroup,      
        publicly_accessible=False,
        backup_retention=Duration.days(7),
        security_groups=[
            securityGroup,
        ],
    )

    addDocumentToIndexFn = lambda_python.PythonFunction(self, "AddDocumentToIndexApiHandler",
        entry="./src/api/lambdas",
        runtime=_lambda.Runtime.PYTHON_3_11,
        index="addDocumentToIndex.py",
        handler="handle",
        vpc=vpc,
        security_groups=[lambdaSecurityGroup],
        timeout=Duration.seconds(30),
        # layers=[baseLayer],
        environment={
            "DB_SECRET_ARN": secretDb.secret_arn,
            "DB_HOST": postgres.db_instance_endpoint_address,
            "DB_PORT": str(postgres.db_instance_endpoint_port),
            "DB_NAME": "dynamic_rag_db"
        }
    )    

    # VPC Endpoints for Secrets Manager and STS
    ec2.InterfaceVpcEndpoint(self, "SecretsManagerVpcEndpoint",
        vpc=vpc,
        service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
        subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
        security_groups=[lambdaSecurityGroup]
    )
    ec2.InterfaceVpcEndpoint(self, "StsVpcEndpoint",
        vpc=vpc,
        service=ec2.InterfaceVpcEndpointAwsService.STS,
        subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
        security_groups=[lambdaSecurityGroup]
    )

    secretDb.grant_read(addDocumentToIndexFn)

    apigw.LambdaRestApi(self, "ApiGwEndpoint",
        handler=addDocumentToIndexFn,
        rest_api_name="DynamicRagApi",
        description="API Gateway for Dynamic RAG Application",
    )