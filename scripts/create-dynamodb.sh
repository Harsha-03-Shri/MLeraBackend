#!/bin/bash

set -e
AWS_REGION="ap-south-1"

echo "Checking if Users table exists..."

if aws dynamodb describe-table --table-name Users --region $AWS_REGION >/dev/null 2>&1; then
    echo "Users table already exists. Skipping creation."
else
    echo "Creating Users DynamoDB Table..."
    aws dynamodb create-table \
        --table-name Users \
        --attribute-definitions \
            AttributeName=userId,AttributeType=S \
            AttributeName=channel,AttributeType=S \
        --key-schema \
            AttributeName=userId,KeyType=HASH \
            AttributeName=channel,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST \
        --region $AWS_REGION
fi

echo "Checking if Templates table exists..."

if aws dynamodb describe-table --table-name Templates --region $AWS_REGION >/dev/null 2>&1; then
    echo "Templates table already exists. Skipping creation."
else
    echo "Creating Templates DynamoDB Table..."
    aws dynamodb create-table \
        --table-name Templates \
        --attribute-definitions \
            AttributeName=TemplateType,AttributeType=S \
            AttributeName=Channel,AttributeType=S \
        --key-schema \
            AttributeName=TemplateType,KeyType=HASH \
            AttributeName=Channel,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST \
        --region $AWS_REGION
fi

echo "Waiting for tables..."
aws dynamodb wait table-exists --table-name Users --region $AWS_REGION
aws dynamodb wait table-exists --table-name Templates --region $AWS_REGION

echo "DynamoDB setup complete"