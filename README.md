# Text Correction (Bedrock + CDK)

CloudShell だけでデプロイできる “テキスト校正アプリ” のサンプルです。  
アップロードしたテキストを **Amazon Bedrock – Nova Micro** に渡して要約し、ダウンロード可能なテキストファイルを生成します。

## デプロイ手順（要: us-east-1 もしくは us-west-2）

```bash
# CloudShell
mkdir /tmp/project
cd /tmp/project

git clone https://github.com/nkknj/simplecorrect.git
cd simplecorrect

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

sudo npm install -g aws-cdk@latest
export AWS_REGION=us-east-1        # Nova Micro 対応リージョン
cd infra
cdk bootstrap aws://$(aws sts get-caller-identity --query Account --output text)/$AWS_REGION
cdk deploy --all

STACK=TextCorrectionStack
API_URL=$(aws cloudformation describe-stacks --stack-name $STACK --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text)
sed -i "s|__API_ENDPOINT__|${API_URL}|g" ../frontend/index.html
cdk deploy --all
