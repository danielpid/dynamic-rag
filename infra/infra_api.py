from aws_cdk import (
    aws_apigateway as apigw,
    aws_lambda as _lambda,    
    aws_lambda_python_alpha as lambda_python,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
    Duration,
    RemovalPolicy,
    Stack
)

import json

POSTGRES_VERSION = rds.PostgresEngineVersion.VER_17_6

def create_api_infrastructure(self: Stack):
    nat = ec2.NatProvider.gateway()

    vpc = ec2.Vpc(self, "DynamicRagVPC",
        max_azs=2,
        cidr="10.5.0.0/16",
        nat_gateway_provider=nat,
        nat_gateways=1,
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
            ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                name="Lambda",
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

    secretKeys = secretsmanager.Secret.from_secret_name_v2(self, "DynamicRagKeysSecret",
        "dynamic-rag/openai_api_key"
    )

    lambdaSecurityGroup = ec2.SecurityGroup(self, "DynamicRagLambdaSecurityGroup",
        vpc=vpc,
        security_group_name="security_group_lambda",
        allow_all_outbound=True,
    )        
    
    subnetGroupDb = rds.SubnetGroup(self, "DynamicRagSubnetGroup",
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
            version=POSTGRES_VERSION
        ),
        parameters={
            "max_standby_streaming_delay": "600000",  # milliseconds (5 minutes)
            "max_standby_archive_delay": "600000",  # milliseconds (5 minutes)
        },
    )    

    postgres = rds.DatabaseInstance(self, "DynamicRagPostgresDB",
        instance_identifier="dynamic-rag-postgres",
        engine=rds.DatabaseInstanceEngine.postgres(
            version=POSTGRES_VERSION
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
        subnet_group=subnetGroupDb,      
        publicly_accessible=False,
        backup_retention=Duration.days(7),
        security_groups=[
            securityGroup,
        ],
    )

    # addDocumentToIndexFn = lambda_python.PythonFunction(self, "AddDocumentToIndexApiHandler",
    #     entry="./src/api/lambdas",
    #     runtime=_lambda.Runtime.PYTHON_3_12,
    #     index="addDocumentToIndex.py",
    #     handler="handler",
    #     vpc=vpc,
    #     security_groups=[lambdaSecurityGroup],
    #     timeout=Duration.seconds(30),
    #     environment={
    #         "DB_SECRET_ARN": secretDb.secret_arn,
    #         "DB_HOST": postgres.db_instance_endpoint_address,
    #         "DB_PORT": str(postgres.db_instance_endpoint_port),
    #         "DB_NAME": "dynamic_rag_db"
    #     }
    # )    

    addDocumentToIndexFn = _lambda.DockerImageFunction(self, "AddDocumentToIndexApiHandler",
        # need a docker lambda container because of the size of the dependencies 
        code=_lambda.DockerImageCode.from_image_asset("./src/api/lambdas"),
        memory_size=1024,
        vpc=vpc,
        vpc_subnets=ec2.SubnetSelection(
            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
        ),
        security_groups=[lambdaSecurityGroup],
        timeout=Duration.seconds(30),
        environment={
            "DB_HOST": postgres.db_instance_endpoint_address,
            "DB_PORT": str(postgres.db_instance_endpoint_port),
            "DB_NAME": "dynamic_rag_db",
        }
    )

    s3DataBucket = s3.Bucket(self, "DynamicRagDataBucket", 
        bucket_name="dynamic-rag-data-bucket", 
        block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        removal_policy=RemovalPolicy.DESTROY,
        auto_delete_objects=True,
    )
    
    s3DataBucket.grant_read(addDocumentToIndexFn)

    ec2.GatewayVpcEndpoint(self, "S3GatewayEndpoint",
        vpc=vpc,
        service=ec2.GatewayVpcEndpointAwsService.S3,
        subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)]
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
    secretKeys.grant_read(addDocumentToIndexFn)

    apigw.LambdaRestApi(self, "ApiGwEndpoint",
        handler=addDocumentToIndexFn,
        rest_api_name="DynamicRagApi",
        description="API Gateway for Dynamic RAG Application",
        deploy_options=apigw.StageOptions(
            stage_name="prod",
            caching_enabled=False
        )
    )
