from aws_cdk import (
    aws_apigateway as apigw,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_s3 as s3,   
    aws_secretsmanager as secretsmanager,
    Duration,
    RemovalPolicy,
    Stack
)

import json

from .infra_utils import create_lambda_image, create_lambda_function

POSTGRES_VERSION = rds.PostgresEngineVersion.VER_17_6

def create_api_infrastructure(self: Stack):

    vpc = ec2.Vpc(self, "DynamicRagVPC",
        max_azs=2,
        cidr="10.5.0.0/16",
        nat_gateway_provider=ec2.NatProvider.gateway(),
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

    secrets_db = secretsmanager.Secret(
        self,
        "DynamicRagDbSecret",
        secret_name="dynamic-rag/db_creds",
        generate_secret_string=secretsmanager.SecretStringGenerator(
            secret_string_template=json.dumps({"username": "dynamic_rag_user"}),
            exclude_punctuation=True,
            generate_string_key="password",
        ),
    )

    secret_keys = secretsmanager.Secret.from_secret_name_v2(self, "DynamicRagKeysSecret",
        "dynamic-rag/openai_api_key"
    )

    lambda_security_group = ec2.SecurityGroup(self, "DynamicRagLambdaSecurityGroup",
        vpc=vpc,
        security_group_name="security_group_lambda",
        allow_all_outbound=True,
    )        
    
    subnet_group_db = rds.SubnetGroup(self, "DynamicRagSubnetGroup",
        vpc=vpc,
        vpc_subnets=ec2.SubnetSelection(
            subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
        ),
        subnet_group_name="postgres-subnet-group",
        description="Subnet group for postgres",
    )

    db_security_group = ec2.SecurityGroup(self, "DynamicRagDBSecurityGroup",
        vpc=vpc,
        security_group_name="security_group_db",
        allow_all_outbound=True,
    )

    db_security_group.add_ingress_rule(
        peer=lambda_security_group,
        connection=ec2.Port.tcp(5432),
    )

    parameter_group = rds.ParameterGroup(self, "DynamicRagPostgresParameterGroup",
        engine=rds.DatabaseInstanceEngine.postgres(
            version=POSTGRES_VERSION
        ),
        parameters={
            "max_standby_streaming_delay": "600000",  # milliseconds (5 minutes)
            "max_standby_archive_delay": "600000",  # milliseconds (5 minutes)
        },
    )    

    postgres_db = rds.DatabaseInstance(self, "DynamicRagPostgresDB",
        instance_identifier="dynamic-rag-postgres",
        engine=rds.DatabaseInstanceEngine.postgres(
            version=POSTGRES_VERSION
        ),
        instance_type=ec2.InstanceType.of(
            ec2.InstanceClass.T4G, ec2.InstanceSize.MICRO
        ),
        parameter_group=parameter_group,
        allocated_storage=20,
        max_allocated_storage=100,
        credentials=rds.Credentials.from_secret(secrets_db),
        database_name="dynamic_rag_db",
        vpc=vpc,
        subnet_group=subnet_group_db,      
        publicly_accessible=False,
        backup_retention=Duration.days(7),
        security_groups=[
            db_security_group,
        ],
    )

    health_check_fn = create_lambda_function(
        self,
        id="HealthCheckFunction",
        handler_path="health_check.handle_health_check"
    )

    s3_data_bucket = s3.Bucket(self, "DynamicRagDataBucket", 
        bucket_name="dynamic-rag-data-bucket", 
        block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        removal_policy=RemovalPolicy.DESTROY,
        auto_delete_objects=True,
    )

    env = {
        "DB_HOST": postgres_db.db_instance_endpoint_address,
        "DB_PORT": str(postgres_db.db_instance_endpoint_port),
        "DB_NAME": "dynamic_rag_db",
        "DATA_BUCKET_NAME": s3_data_bucket.bucket_name,
    }

    ingest_documents_fn = create_lambda_image(
        self,
        id="IngestDocumentsFunction",
        directory="ingest_documents",
        env=env,
        vpc=vpc,
        sg=lambda_security_group,        
    )

    query_index_fn = create_lambda_image(
        self,
        id="QueryIndexFunction",
        directory="query_index",
        vpc=vpc,
        sg=lambda_security_group,
        env=env
    )    
    
    s3_data_bucket.grant_read(ingest_documents_fn)

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
        security_groups=[lambda_security_group]
    )
    ec2.InterfaceVpcEndpoint(self, "StsVpcEndpoint",
        vpc=vpc,
        service=ec2.InterfaceVpcEndpointAwsService.STS,
        subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
        security_groups=[lambda_security_group]
    )

    secrets_db.grant_read(ingest_documents_fn)
    secrets_db.grant_read(query_index_fn)
    secret_keys.grant_read(ingest_documents_fn)
    secret_keys.grant_read(query_index_fn)

    api = apigw.LambdaRestApi(self, "ApiGwEndpoint",
        handler=health_check_fn,
        rest_api_name="DynamicRagApi",
        description="API Gateway for Dynamic RAG Application",
        deploy_options=apigw.StageOptions(
            stage_name="prod",
            caching_enabled=False
        ),
        default_cors_preflight_options=apigw.CorsOptions(
            allow_origins=apigw.Cors.ALL_ORIGINS,
            allow_methods=apigw.Cors.ALL_METHODS,
        )       
    )

    # This lambda won't be accessible
    # api.root.add_resource("ingest").add_method("POST", apigw.LambdaIntegration(ingest_documents_fn))
    
    api.root.add_resource("query").add_method("POST", apigw.LambdaIntegration(query_index_fn))

    api.add_usage_plan("UsagePlan", 
        name="Default",
        throttle=apigw.ThrottleSettings(
            rate_limit=2,
            burst_limit=1
        )    
    )


