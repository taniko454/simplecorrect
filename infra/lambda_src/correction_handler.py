import os, json, urllib.parse, boto3

BEDROCK_REGION = os.environ["BEDROCK_REGION"]
MODEL_ID = "amazon.nova-micro-v1:0"

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

def split_text_into_chunks(text, chunk_size=1500):
    # textを句点で分割し、空の要素は除去する
    sentences = [s for s in text.split('。') if s]

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        #現在の分に次の分を追加するとサイズを超えるかチェック
        if len(current_chunk) + len(sentence) + 1 > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip() + '。')
            current_chunk = sentence

        else:
            if current_chunk:
                current_chunk += '。' + sentence
            else:
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk.strip() + '。')

    return chunks

def handler(event, _):
    for rec in event["Records"]:
        bucket = rec["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(rec["s3"]["object"]["key"])
        if not key.startswith("uploads/"):
            continue  # ガード

        obj = s3.get_object(Bucket=bucket, Key=key)
        text = obj["Body"].read().decode()

        chunks = split_text_into_chunks(text, chunk_size=1500)

        corrected_parts = []

        for chunk in chunks:
            #チャンクごとにプロンプトを作成
            user_message = f"次に示す文章から、「あー」「えー」などのフィラーを削除したものを、【Start】【End】で括って出力してください。\n\n{chunk}"
            resp = bedrock.converse(
                modelId=MODEL_ID,
                messages=[{
                    "role": "user",
                    "content": [{"text": user_message}]
                }],
                inferenceConfig={"maxTokens": 2000},
            )
            correction = resp["output"]["message"]["content"][0]["text"]

            # 【Start】と【End】の間だけを抽出
            if '【Start】' in correction and '【End】' in correction:
                correction = correction.split('【Start】')[1].split('【End】')[0]
                corrected_parts.append(correction)
            
        final_correction = "".join(corrected_parts)

        out_key = "outputs/correction.txt"
        s3.put_object(Bucket=bucket, Key=out_key,
                      Body=final_correction.encode("utf-8"),
                      ContentType="text/plain")
