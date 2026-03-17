#!/bin/bash

# Deploy Email Lambda Function with Dependencies
# Run from project root: ./scripts/deploy-email-lambda.sh

set -e

echo "=== Deploying Email Lambda Function ==="
echo ""

LAMBDA_NAME="mlera-email-consumer"
REGION="ap-south-1"
LAMBDA_DIR="ProdNotification/Consumer/EmailConsumer"

# Navigate to Lambda directory
cd $LAMBDA_DIR

echo "1. Creating package directory..."
rm -rf package lambda-deployment.zip
mkdir -p package

echo "2. Installing dependencies..."
pip install aiosmtplib -t package/ --quiet

echo "3. Copying Lambda code..."
cp lambdaFunction.py package/
cp smtpClient.py package/

echo "4. Creating deployment package..."
cd package
zip -r ../lambda-deployment.zip . > /dev/null
cd ..

echo "5. Verifying package contents..."
unzip -l lambda-deployment.zip | grep -E "(lambdaFunction|smtpClient|aiosmtplib)"

echo ""
echo "6. Uploading to Lambda..."
aws lambda update-function-code \
    --function-name $LAMBDA_NAME \
    --zip-file fileb://lambda-deployment.zip \
    --region $REGION \
    --output json | jq '{FunctionName, LastModified, CodeSize, State}'

echo ""
echo "7. Waiting for Lambda to be ready..."
aws lambda wait function-updated \
    --function-name $LAMBDA_NAME \
    --region $REGION

echo ""
echo "8. Verifying Lambda configuration..."
aws lambda get-function-configuration \
    --function-name $LAMBDA_NAME \
    --region $REGION \
    --query '{Runtime, Handler, Environment: Environment.Variables}' \
    --output json | jq '.'

echo ""
echo "9. Cleaning up..."
rm -rf package lambda-deployment.zip

echo ""
echo "✅ Lambda deployed successfully!"
echo ""
echo "Test with:"
echo "  aws logs tail /aws/lambda/$LAMBDA_NAME --follow --region $REGION"
