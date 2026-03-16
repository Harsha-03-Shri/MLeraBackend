#!/bin/bash

# Lambda Setup Script for Email Notification Consumer
# Creates Lambda function, IAM role, and SQS trigger

set -e

AWS_REGION="ap-south-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
LAMBDA_NAME="mlera-email-consumer"
EMAIL_QUEUE_URL="${1:-}"
GMAIL_FROM="${2:-}"
GMAIL_PASSWORD="${3:-}"

if [ -z "$EMAIL_QUEUE_URL" ] || [ -z "$GMAIL_FROM" ] || [ -z "$GMAIL_PASSWORD" ]; then
    echo "Usage: ./create-lambda-email.sh <EMAIL_QUEUE_URL> <GMAIL_FROM> <GMAIL_PASSWORD>"
    echo "Example: ./create-lambda-email.sh https://sqs.ap-south-1.amazonaws.com/123456789012/mlera-email-queue noreply@example.com app_password"
    exit 1
fi

EMAIL_QUEUE_ARN=$(aws sqs get-queue-attributes \
    --queue-url $EMAIL_QUEUE_URL \
    --attribute-names QueueArn \
    --region $AWS_REGION \
    --query 'Attributes.QueueArn' \
    --output text)

echo "Creating IAM role for Lambda..."
ROLE_ARN=$(aws iam create-role \
    --role-name ${LAMBDA_NAME}-role \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }' \
    --query 'Role.Arn' \
    --output text 2>/dev/null || aws iam get-role --role-name ${LAMBDA_NAME}-role --query 'Role.Arn' --output text)

echo "Role ARN: $ROLE_ARN"

echo "Attaching policies to role..."
aws iam attach-role-policy \
    --role-name ${LAMBDA_NAME}-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
    --role-name ${LAMBDA_NAME}-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole

echo "Waiting for role to propagate..."
sleep 10

echo "Creating Lambda deployment package..."
cd ../ProdNotification/Consumer/EmailConsumer
mkdir -p package
pip install -r ../Requirements.txt -t package/
cp lambdaFunction.py package/
cp smtpClient.py package/
cd package
zip -r ../lambda-deployment.zip .
cd ..
zip -g lambda-deployment.zip lambdaFunction.py smtpClient.py
cd ../../../

echo "Creating Lambda function..."
aws lambda create-function \
    --function-name $LAMBDA_NAME \
    --runtime python3.11 \
    --role $ROLE_ARN \
    --handler lambdaFunction.handler \
    --zip-file fileb://ProdNotification/Consumer/EmailConsumer/lambda-deployment.zip \
    --timeout 300 \
    --memory-size 256 \
    --region $AWS_REGION \
    --environment "Variables={GMAILFROM=$GMAIL_FROM,GMAILPASSWORD=$GMAIL_PASSWORD}" \
    2>/dev/null || echo "Lambda function already exists, updating..."

if [ $? -ne 0 ]; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $LAMBDA_NAME \
        --zip-file fileb://ProdNotification/Consumer/EmailConsumer/lambda-deployment.zip \
        --region $AWS_REGION
    
    aws lambda update-function-configuration \
        --function-name $LAMBDA_NAME \
        --environment "Variables={GMAILFROM=$GMAIL_FROM,GMAILPASSWORD=$GMAIL_PASSWORD}" \
        --region $AWS_REGION
fi

echo "Creating SQS trigger for Lambda..."
aws lambda create-event-source-mapping \
    --function-name $LAMBDA_NAME \
    --event-source-arn $EMAIL_QUEUE_ARN \
    --batch-size 10 \
    --region $AWS_REGION \
    2>/dev/null || echo "Event source mapping already exists"

echo "Cleaning up deployment package..."
rm -rf ProdNotification/Consumer/EmailConsumer/package
rm -f ProdNotification/Consumer/EmailConsumer/lambda-deployment.zip

echo ""
echo "=========================================="
echo "Lambda Email Consumer Setup Complete!"
echo "=========================================="
echo ""
echo "Lambda Function: $LAMBDA_NAME"
echo "Region: $AWS_REGION"
echo "Trigger: SQS Queue ($EMAIL_QUEUE_ARN)"
echo ""
echo "To update Lambda code in future:"
echo "1. cd ProdNotification/Consumer/EmailConsumer"
echo "2. zip -r lambda-deployment.zip lambdaFunction.py smtpClient.py"
echo "3. aws lambda update-function-code --function-name $LAMBDA_NAME --zip-file fileb://lambda-deployment.zip --region $AWS_REGION"
echo ""
