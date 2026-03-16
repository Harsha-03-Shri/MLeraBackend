#!/bin/bash

# Master Setup Script for MLera Backend Infrastructure

# Idempotent version (safe to run multiple times)

set -e

echo "=========================================="
echo "MLera Backend Infrastructure Setup"
echo "=========================================="
echo ""

# Color codes

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
echo -e "${RED}✗ $1${NC}"
}

print_info() {
echo -e "${YELLOW}→ $1${NC}"
}

# Safe execution wrapper

run_safe() {
if "$@"; then
return 0
else
print_info "Resource may already exist. Continuing..."
return 0
fi
}

# Check AWS CLI

if ! command -v aws &> /dev/null; then
print_error "AWS CLI not installed"
exit 1
fi
print_success "AWS CLI found"

# Check AWS credentials

if ! aws sts get-caller-identity &> /dev/null; then
print_error "AWS credentials not configured"
exit 1
fi
print_success "AWS credentials configured"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_info "AWS Account ID: $ACCOUNT_ID"

echo ""
echo "Resources that will be created if missing:"
echo "1. ECR Repositories"
echo "2. RDS PostgreSQL"
echo "3. ElastiCache Redis"
echo "4. SNS Topic + SQS Email Queue"
echo "5. SQS Queue for DB Operations"
echo "6. DynamoDB Tables"
echo "7. Lambda Email Consumer"
echo "8. Lambda DB Consumer"
echo ""

read -p "Continue setup? (y/n): " -n 1 -r
echo
[[ ! $REPLY =~ ^[Yy]$ ]] && exit 0

print_info "Starting setup..."
echo ""

############################################

# Step 1 - ECR

############################################

print_info "Step 1/8: Creating ECR repositories"

if run_safe ./create-ecr.sh; then
print_success "ECR step completed"
fi

read -p "Press Enter to continue..."

############################################

# Step 2 - RDS

############################################

print_info "Step 2/8: Creating RDS PostgreSQL"

if run_safe ./create-rds.sh; then
print_success "RDS step completed"
fi

echo ""
read -p "Enter RDS Endpoint: " RDS_ENDPOINT
read -p "Enter DB Name: " DB_NAME
read -p "Enter DB User: " DB_USER
read -sp "Enter DB Password: " DB_PASSWORD
echo ""

############################################

# Step 3 - ElastiCache

############################################

print_info "Step 3/8: Creating Redis"

if run_safe ./create-elasticache.sh; then
print_success "ElastiCache step completed"
fi

read -p "Press Enter to continue..."

############################################

# Step 4 - SNS + SQS

############################################

print_info "Step 4/8: Creating SNS and Email Queue"

if run_safe ./create-sns-sqs.sh; then
print_success "SNS/SQS step completed"
fi

read -p "Enter Email Queue URL: " EMAIL_QUEUE_URL
read -p "Enter SNS Topic ARN: " SNS_TOPIC_ARN

############################################

# Step 5 - DB Queue

############################################

print_info "Step 5/8: Creating DB Queue"

if run_safe ./create-sqs-db.sh; then
print_success "DB Queue step completed"
fi

read -p "Enter DB Queue URL: " DB_QUEUE_URL

############################################

# Step 6 - DynamoDB

############################################

print_info "Step 6/8: Creating DynamoDB Tables"

if run_safe ./create-dynamodb.sh; then
print_success "DynamoDB tables step completed"
fi

read -p "Press Enter to populate templates..."

print_info "Populating templates"

run_safe ./populate-templates.sh

print_success "Templates populated"

############################################

# Step 7 - Email Lambda

############################################

print_info "Step 7/8: Creating Email Lambda"

read -p "Enter Gmail From Address: " GMAIL_FROM
read -sp "Enter Gmail App Password: " GMAIL_PASSWORD
echo ""

if run_safe ./create-lambda-email.sh "$EMAIL_QUEUE_URL" "$GMAIL_FROM" "$GMAIL_PASSWORD"; then
print_success "Email Lambda created"
fi

read -p "Press Enter to continue..."

############################################

# Step 8 - DB Lambda

############################################

print_info "Step 8/8: Creating DB Lambda"

read -p "Enter VPC Subnet IDs (comma separated): " SUBNET_IDS
read -p "Enter Security Group IDs (comma separated): " SECURITY_GROUP_IDS

if run_safe ./create-lambda-db.sh "$DB_QUEUE_URL" "$RDS_ENDPOINT" "$DB_NAME" "$DB_USER" "$DB_PASSWORD" "$SUBNET_IDS" "$SECURITY_GROUP_IDS"; then
print_success "DB Lambda created"
fi

############################################

# Complete

############################################

echo ""
echo "=========================================="
print_success "Infrastructure Setup Complete"
echo "=========================================="
echo ""

echo "Resources Summary"
echo "-----------------"
echo "RDS Endpoint: $RDS_ENDPOINT"
echo "SNS Topic: $SNS_TOPIC_ARN"
echo "Email Queue: $EMAIL_QUEUE_URL"
echo "DB Queue: $DB_QUEUE_URL"
echo "DynamoDB Tables: Users, Templates"
echo "Lambda Functions: mlera-email-consumer, mlera-db-consumer"

echo ""
echo "Next steps:"
echo "1. Update .env with above values"
echo "2. Configure CI/CD secrets"
echo "3. Run EC2 setup"
echo "4. Deploy application"

print_info "Save this information for your environment configuration."
