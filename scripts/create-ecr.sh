#!/bin/bash
# Script to create ECR repositories for all three services

set -e

REGION="ap-south-1"

echo "Creating ECR repositories..."

# Create repository for Main API
aws ecr create-repository \
    --repository-name prod-main-api \
    --region $REGION \
    --image-scanning-configuration scanOnPush=true || echo "prod-main-api repository may already exist"

# Create repository for DB System
aws ecr create-repository \
    --repository-name prod-db-system \
    --region $REGION \
    --image-scanning-configuration scanOnPush=true || echo "prod-db-system repository may already exist"

# Create repository for Notification
aws ecr create-repository \
    --repository-name prod-notification \
    --region $REGION \
    --image-scanning-configuration scanOnPush=true || echo "prod-notification repository may already exist"

echo "=== ECR Repositories Created ==="
echo ""
echo "Repository URIs:"
echo "Main API: 812661756903.dkr.ecr.ap-south-1.amazonaws.com/prod-main-api"
echo "DB System: 812661756903.dkr.ecr.ap-south-1.amazonaws.com/prod-db-system"
echo "Notification: 812661756903.dkr.ecr.ap-south-1.amazonaws.com/prod-notification"
