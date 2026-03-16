#!/bin/bash

# SNS and SQS Setup Script for MLera Backend
# Creates SNS topic, SQS queues, and subscriptions with filtering

set -e

AWS_REGION="ap-south-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Creating SNS Topic..."
SNS_TOPIC_ARN=$(aws sns create-topic \
    --name mlera-notifications \
    --region $AWS_REGION \
    --query 'TopicArn' \
    --output text)

echo "SNS Topic created: $SNS_TOPIC_ARN"

echo "Creating SQS Queue for Email notifications..."
EMAIL_QUEUE_URL=$(aws sqs create-queue \
    --queue-name mlera-email-queue \
    --region $AWS_REGION \
    --attributes '{
        "VisibilityTimeout": "300",
        "MessageRetentionPeriod": "1209600",
        "ReceiveMessageWaitTimeSeconds": "20"
    }' \
    --query 'QueueUrl' \
    --output text)

echo "Email Queue created: $EMAIL_QUEUE_URL"

EMAIL_QUEUE_ARN=$(aws sqs get-queue-attributes \
    --queue-url $EMAIL_QUEUE_URL \
    --attribute-names QueueArn \
    --region $AWS_REGION \
    --query 'Attributes.QueueArn' \
    --output text)

echo "Setting SQS Queue Policy for SNS..."
aws sqs set-queue-attributes \
    --queue-url $EMAIL_QUEUE_URL \
    --region $AWS_REGION \
    --attributes '{
        "Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"sns.amazonaws.com\"},\"Action\":\"sqs:SendMessage\",\"Resource\":\"'$EMAIL_QUEUE_ARN'\",\"Condition\":{\"ArnEquals\":{\"aws:SourceArn\":\"'$SNS_TOPIC_ARN'\"}}}]}"
    }'

echo "Subscribing Email Queue to SNS Topic with filter..."
EMAIL_SUBSCRIPTION_ARN=$(aws sns subscribe \
    --topic-arn $SNS_TOPIC_ARN \
    --protocol sqs \
    --notification-endpoint $EMAIL_QUEUE_ARN \
    --region $AWS_REGION \
    --attributes '{
        "FilterPolicy": "{\"Channel\":[\"email\"]}"
    }' \
    --query 'SubscriptionArn' \
    --output text)

echo "Email subscription created: $EMAIL_SUBSCRIPTION_ARN"

echo ""
echo "=========================================="
echo "SNS and SQS Setup Complete!"
echo "=========================================="
echo ""
echo "Add these to your .env file:"
echo ""
echo "SNS_TOPIC_ARN=$SNS_TOPIC_ARN"
echo "EMAIL_QUEUE_URL=$EMAIL_QUEUE_URL"
echo ""
echo "Add to GitHub Secrets:"
echo "SNS_TOPIC_ARN=$SNS_TOPIC_ARN"
echo ""
