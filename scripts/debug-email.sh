#!/bin/bash

# Debug Email Notification Flow
# Run this on your local machine (not EC2)

echo "=== MLera Email Notification Debug ==="
echo ""

# Configuration
REGION="ap-south-1"
LAMBDA_FUNCTION="mlera-email-consumer"
SQS_QUEUE_URL="https://sqs.ap-south-1.amazonaws.com/812661756903/mlera-email-queue"
SNS_TOPIC_ARN="arn:aws:sns:ap-south-1:812661756903:mlera-notifications"

echo "1. Checking Lambda function..."
aws lambda get-function --function-name $LAMBDA_FUNCTION --region $REGION > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Lambda function exists"
else
    echo "   ❌ Lambda function NOT found"
    exit 1
fi

echo ""
echo "2. Checking Lambda configuration..."
aws lambda get-function-configuration --function-name $LAMBDA_FUNCTION --region $REGION --query 'Environment.Variables' --output json

echo ""
echo "3. Checking SQS queue attributes..."
aws sqs get-queue-attributes \
    --queue-url $SQS_QUEUE_URL \
    --attribute-names ApproximateNumberOfMessages,ApproximateNumberOfMessagesNotVisible \
    --region $REGION \
    --output table

echo ""
echo "4. Checking Lambda event source mapping..."
aws lambda list-event-source-mappings \
    --function-name $LAMBDA_FUNCTION \
    --region $REGION \
    --output table

echo ""
echo "5. Checking SNS subscriptions..."
aws sns list-subscriptions-by-topic \
    --topic-arn $SNS_TOPIC_ARN \
    --region $REGION \
    --output table

echo ""
echo "6. Checking recent Lambda logs (last 5 minutes)..."
aws logs tail /aws/lambda/$LAMBDA_FUNCTION --since 5m --region $REGION

echo ""
echo "7. Checking for messages in SQS queue..."
MESSAGES=$(aws sqs receive-message \
    --queue-url $SQS_QUEUE_URL \
    --max-number-of-messages 1 \
    --region $REGION \
    --output json)

if [ "$MESSAGES" != "" ] && [ "$MESSAGES" != "{}" ]; then
    echo "   ⚠️  Messages found in queue (Lambda not processing):"
    echo "$MESSAGES" | jq '.Messages[0].Body' -r
else
    echo "   ✅ No messages in queue (either processed or not sent)"
fi

echo ""
echo "=== Debug Complete ==="
echo ""
echo "Common Issues:"
echo "  - If messages stuck in queue: Lambda trigger not working"
echo "  - If no messages in queue: SNS filter policy issue"
echo "  - If Lambda errors in logs: SMTP credentials issue"
echo ""
echo "Next Steps:"
echo "  1. Check Lambda logs above for errors"
echo "  2. Verify SMTP credentials are correct"
echo "  3. Ensure Gmail App Password is used (not regular password)"
echo "  4. Check SNS subscription has filter policy: {\"Channel\":[\"email\"]}"
