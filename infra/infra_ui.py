from aws_cdk import (
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    BundlingOptions,
    CfnOutput,
    DockerImage,
    Duration,
    RemovalPolicy,
    Stack,    
)
from pathlib import Path

from .infra_utils import _read_env_file

def create_ui_infrastructure(self: Stack):

    bucket = s3.Bucket(self, "DynamicRagBucket",
        bucket_name="dynamic-rag-bucket",
        block_public_access=s3.BlockPublicAccess.BLOCK_ACLS_ONLY,
        enforce_ssl=True,
        removal_policy=RemovalPolicy.DESTROY,
        auto_delete_objects=True,
    )

    oac = cloudfront.CfnOriginAccessControl(self, "OAC",
        origin_access_control_config=cloudfront.CfnOriginAccessControl.OriginAccessControlConfigProperty(
            name="dynamic-rag-oac",
            origin_access_control_origin_type="s3",
            signing_behavior="always",
            signing_protocol="sigv4"
        )        
    )    

    distribution = cloudfront.Distribution(self, "DynamicRagDistribution",
        default_behavior=cloudfront.BehaviorOptions(
            origin=origins.S3BucketOrigin(bucket, 
                origin_access_control_id=oac.attr_id
            ),
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,                
        ),
        default_root_object="index.html",
        # optional: serve SPA routes by returning index.html for 403/404
        error_responses=[
            cloudfront.ErrorResponse(http_status=403, response_http_status=200, response_page_path="/index.html", ttl=Duration.seconds(0)),
            cloudfront.ErrorResponse(http_status=404, response_http_status=200, response_page_path="/index.html", ttl=Duration.seconds(0)),
        ],
    )

    vite_api_url = _read_env_file("VITE_API_URL")

    s3_deployment.BucketDeployment(self, "DeployWebsite",
        sources=[
            s3_deployment.Source.asset(
                str(Path.cwd() / "src" / "ui"),
                bundling=BundlingOptions(
                    image=DockerImage.from_build(path="infra"),
                    command=[
                        "bash", "-c",
                        "CI=true pnpm i --frozen-lockfile && pnpm build && cp -r dist/. /asset-output/"
                    ],
                    environment={
                        "VITE_API_URL": vite_api_url
                    }

                ),
            )
        ],
        destination_bucket=bucket,
        distribution=distribution
    )

    bucket.add_to_resource_policy(iam.PolicyStatement(
        sid="AllowCloudFrontReadAccess",
        effect=iam.Effect.ALLOW,
        principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
        actions=["s3:GetObject"],
        resources=[bucket.arn_for_objects("*")],
        conditions={
            "StringEquals": {
                "AWS:SourceArn": distribution.distribution_arn
            }
        }            
    ))

    # Output the CloudFront distribution domain name
    CfnOutput(self, "DistributionDomainName",
        value=distribution.domain_name,
        description="The domain name of the CloudFront distribution",
    )