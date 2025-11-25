from aws_cdk import (
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,    
)
from pathlib import Path

def create_ui_infrastructure(self: Stack):
    asset_dir = Path.cwd() / "src" / "ui" / "dist"
    if not asset_dir.is_dir():
        raise FileNotFoundError(f"Required asset directory not found: {asset_dir}. Build the UI (create ./src/dynamic-rag-ui/dist) before deploying.")

    bucket = s3.Bucket(self, "DynamicRagBucket",
        bucket_name="dynamic-rag-bucket",
        block_public_access=s3.BlockPublicAccess.BLOCK_ACLS_ONLY,
        enforce_ssl=True,
        removal_policy=RemovalPolicy.DESTROY,
        auto_delete_objects=True,
        # website_index_document="index.html",             
    )

    s3_deployment.BucketDeployment(self, "DeployWebsite",
        sources=[s3_deployment.Source.asset(asset_dir.as_posix())],
        destination_bucket=bucket,
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

    bucket.add_to_resource_policy(iam.PolicyStatement(
        sid="AllowCloudFrontReadAccess",
        effect=iam.Effect.ALLOW,
        principals=[iam.AnyPrincipal()],
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