#!/usr/bin/env python3
import os
import aws_cdk as cdk
from text_correction_stack import TextCorrectionStack

app = cdk.App()

TextCorrectionStack(
    app, "TextCorrectionStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("AWS_REGION", "us-east-1"),
    ),
)

app.synth()
