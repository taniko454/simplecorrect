import os, json, urllib.parse, boto3

BEDROCK_REGION = os.environ["BEDROCK_REGION"]
MODEL_ID = "amazon.nova-micro-v1:0"

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

def handler(event, _):
    for rec in event["Records"]:
        bucket = rec["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(rec["s3"]["object"]["key"])
        if not key.startswith("uploads/"):
            continue  # ガード

        obj = s3.get_object(Bucket=bucket, Key=key)
        text = obj["Body"].read().decode()

        user_message = f"次に示す文章から、「あー」「えー」などのフィラーを削除したものを、【Start】【End】で括って出力してください。\n\n{text}"
        resp = bedrock.converse(
                modelId=MODEL_ID,
                messages=[{
                    "role": "user",
                    "content": [{"text": user_message}]
                }],
                inferenceConfig={"maxTokens": 800},
        )
        correction = resp["output"]["message"]["content"][0]["text"]

        out_key = "outputs/correction.txt"
        s3.put_object(Bucket=bucket, Key=out_key,
                      Body=correction.encode("utf-8"),
                      ContentType="text/plain")
