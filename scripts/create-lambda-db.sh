#!/bin/bash

# Lambda Setup Script for DB Operations Consumer
# Creates Lambda function, IAM role, and SQS trigger

set -e

AWS_REGION="ap-south-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
LAMBDA_NAME="mlera-db-consumer"
DB_QUEUE_URL="${1:-}"
RDS_ENDPOINT="${2:-}"
DB_NAME="${3:-mlera}"
DB_USER="${4:-postgres}"
DB_PASSWORD="${5:-}"
VPC_SUBNET_IDS="${6:-}"
VPC_SECURITY_GROUP_IDS="${7:-}"

if [ -z "$DB_QUEUE_URL" ] || [ -z "$RDS_ENDPOINT" ] || [ -z "$DB_PASSWORD" ] || [ -z "$VPC_SUBNET_IDS" ] || [ -z "$VPC_SECURITY_GROUP_IDS" ]; then
    echo "Usage: ./create-lambda-db.sh <DB_QUEUE_URL> <RDS_ENDPOINT> <DB_NAME> <DB_USER> <DB_PASSWORD> <VPC_SUBNET_IDS> <VPC_SECURITY_GROUP_IDS>"
    echo "Example: ./create-lambda-db.sh https://sqs.ap-south-1.amazonaws.com/123/queue db.xxx.rds.amazonaws.com mlera postgres mypass subnet-xxx,subnet-yyy sg-xxx"
    exit 1
fi

DB_QUEUE_ARN=$(aws sqs get-queue-attributes \
    --queue-url $DB_QUEUE_URL \
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

aws iam attach-role-policy \
    --role-name ${LAMBDA_NAME}-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole

echo "Waiting for role to propagate..."
sleep 10

echo "Creating Lambda deployment package..."
cd ../ProdDBSystem/Consumer
mkdir -p package
pip install psycopg2-binary -t package/
cp lambdaFunction.py package/
cp Event.py package/
cp -r ../Resorces package/
cd package
zip -r ../lambda-deployment.zip .
cd ..
zip -g lambda-deployment.zip lambdaFunction.py Event.py
cd ../../

echo "Creating Lambda function..."
aws lambda create-function \
    --function-name $LAMBDA_NAME \
    --runtime python3.11 \
    --role $ROLE_ARN \
    --handler lambdaFunction.handler \
    --zip-file fileb://ProdDBSystem/Consumer/lambda-deployment.zip \
    --timeout 300 \
    --memory-size 512 \
    --region $AWS_REGION \
    --vpc-config SubnetIds=$VPC_SUBNET_IDS,SecurityGroupIds=$VPC_SECURITY_GROUP_IDS \
    --environment "Variables={DB_HOST=$RDS_ENDPOINT,DB_PORT=5432,DB_NAME=$DB_NAME,DB_USER=$DB_USER,DB_PASSWORD=$DB_PASSWORD}" \
    2>/dev/null || echo "Lambda function already exists, updating..."

if [ $? -ne 0 ]; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $LAMBDA_NAME \
        --zip-file fileb://ProdDBSystem/Consumer/lambda-deployment.zip \
        --region $AWS_REGION
    
    aws lambda update-function-configuration \
        --function-name $LAMBDA_NAME \
        --vpc-config SubnetIds=$VPC_SUBNET_IDS,SecurityGroupIds=$VPC_SECURITY_GROUP_IDS \
        --environment "Variables={DB_HOST=$RDS_ENDPOINT,DB_PORT=5432,DB_NAME=$DB_NAME,DB_USER=$DB_USER,DB_PASSWORD=$DB_PASSWORD}" \
        --region $AWS_REGION
fi

echo "Waiting for Lambda to become active..."
aws lambda wait function-active --function-name $LAMBDA_NAME --region $AWS_REGION

echo "Creating SQS trigger for Lambda..."
aws lambda create-event-source-mapping \
    --function-name $LAMBDA_NAME \
    --event-source-arn $DB_QUEUE_ARN \
    --batch-size 10 \
    --region $AWS_REGION \
    2>/dev/null || echo "Event source mapping already exists"

echo "Cleaning up deployment package..."
rm -rf ProdDBSystem/Consumer/package
rm -f ProdDBSystem/Consumer/lambda-deployment.zip

echo ""
echo "=========================================="
echo "Lambda DB Consumer Setup Complete!"
echo "=========================================="
echo ""
echo "Lambda Function: $LAMBDA_NAME"
echo "Region: $AWS_REGION"
echo "VPC: Enabled (Private Subnets)"
echo "Trigger: SQS Queue ($DB_QUEUE_ARN)"
echo ""
echo "To update Lambda code in future:"
echo "1. cd ProdDBSystem/Consumer"
echo "2. zip -r lambda-deployment.zip lambdaFunction.py Event.py Resorces/"
echo "3. aws lambda update-function-code --function-name $LAMBDA_NAME --zip-file fileb://lambda-deployment.zip --region $AWS_REGION"
echo ""
