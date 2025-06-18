from pathlib import Path
from aws_cdk import (
    Duration, RemovalPolicy, CfnOutput,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_s3_notifications as s3n,
    aws_iam as iam,
    aws_apigateway as apigw,
    aws_cloudfront as cf,
    aws_cloudfront_origins as origins,
)
import aws_cdk as cdk

PROJECT_ROOT = Path(__file__).parent


class TextCorrectionStack(cdk.Stack):

    def __init__(self, scope, construct_id, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ---------- S3 バケット ----------
        bucket = s3.Bucket(
            self, "FilesBucket",
            cors=[s3.CorsRule(
                allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET],
                allowed_origins=["*"],
                allowed_headers=["*"],
            )],
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=False,
        )

        # ---------- Lambda: 要約処理 ----------
        correction_fn = _lambda.Function(
            self, "CorrectionFn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="correction_handler.handler",
            code=_lambda.Code.from_asset(str(PROJECT_ROOT / "lambda_src")),
            memory_size=1024,
            timeout=Duration.minutes(2),
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "BEDROCK_REGION": self.region,
            },
        )
        bucket.grant_read_write(correction_fn)
        correction_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"],
        ))

        # S3 イベントで起動
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(correction_fn),
            s3.NotificationKeyFilter(prefix="uploads/"),
        )

        # ---------- Lambda: Presign ----------
        presign_fn = _lambda.Function(
            self, "PresignFn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="presign_handler.handler",
            code=_lambda.Code.from_asset(str(PROJECT_ROOT / "lambda_src")),
            timeout=Duration.seconds(30),
            environment={
                "BUCKET_NAME": bucket.bucket_name,
            },
        )
        bucket.grant_read_write(presign_fn)

        # ---------- API Gateway ----------
        api = apigw.RestApi(
            self, "PresignApi",
            rest_api_name="TextCorrectionPresignApi",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
            ),
        )
        presign = api.root.add_resource("presign")

        upload = presign.add_resource("upload")
        download = presign.add_resource("download")

        upload.add_method(
            "GET",
            apigw.LambdaIntegration(presign_fn, proxy=True),
        )
        download.add_method(
            "GET",
            apigw.LambdaIntegration(presign_fn, proxy=True),
        )

        # ---------- CloudFront (静的サイト) ----------
        distribution = cf.Distribution(
            self, "FrontendDist",
            default_root_object="index.html",
            default_behavior=cf.BehaviorOptions(
                origin=origins.S3Origin(bucket),
                cache_policy=cf.CachePolicy.CACHING_DISABLED,
                viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
        )

        # ---------- CDK Outputs ----------
        CfnOutput(self, "FrontendURL", value=f"https://{distribution.domain_name}")
        CfnOutput(self, "ApiEndpoint", value=api.url)
        CfnOutput(self, "BucketName", value=bucket.bucket_name)
