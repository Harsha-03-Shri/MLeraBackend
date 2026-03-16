#!/bin/bash

# SQS Setup Script for MLera DB Service
# Creates SQS queue for database operations

set -e

AWS_REGION="ap-south-1"

echo "Creating SQS Queue for DB operations..."
DB_QUEUE_URL=$(aws sqs create-queue \
    --queue-name mlera-db-operations-queue \
    --region $AWS_REGION \
    --attributes '{
        "VisibilityTimeout": "300",
        "MessageRetentionPeriod": "1209600",
        "ReceiveMessageWaitTimeSeconds": "20"
    }' \
    --query 'QueueUrl' \
    --output text)

echo "DB Operations Queue created: $DB_QUEUE_URL"

DB_QUEUE_ARN=$(aws sqs get-queue-attributes \
    --queue-url $DB_QUEUE_URL \
    --attribute-names QueueArn \
    --region $AWS_REGION \
    --query 'Attributes.QueueArn' \
    --output text)

echo ""
echo "=========================================="
echo "SQS Setup Complete!"
echo "=========================================="
echo ""
echo "Add these to your .env file:"
echo ""
echo "SQS_QUEUE_URL=$DB_QUEUE_URL"
echo ""
echo "Add to GitHub Secrets:"
echo "SQS_QUEUE_URL=$DB_QUEUE_URL"
echo ""
echo "Queue ARN (for Lambda trigger): $DB_QUEUE_ARN"
echo ""
