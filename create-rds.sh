#!/bin/bash
# Script to create RDS PostgreSQL instance

set -e

# Configuration
DB_INSTANCE_ID="mlera-postgres-db"
DB_NAME="mlera_db"
DB_USERNAME="admin"
DB_PASSWORD="YourSecurePassword123!"  # Change this!
DB_INSTANCE_CLASS="db.t3.micro"
ALLOCATED_STORAGE=20
VPC_ID="vpc-05f426c085e90fc3e"
PRIVATE_SUBNET_1="subnet-0d9dc14695f0cdf9c"
PRIVATE_SUBNET_2="subnet-XXXXXXXX"  # Add your second private subnet

echo "Creating DB Subnet Group..."
aws rds create-db-subnet-group \
    --db-subnet-group-name mlera-db-subnet-group \
    --db-subnet-group-description "Subnet group for MLera RDS" \
    --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
    --region ap-south-1 || echo "Subnet group may already exist"

echo "Creating Security Group for RDS..."
SG_ID=$(aws ec2 create-security-group \
    --group-name mlera-rds-sg \
    --description "Security group for MLera RDS" \
    --vpc-id $VPC_ID \
    --region ap-south-1 \
    --query 'GroupId' \
    --output text) || echo "Security group may already exist"

# Get EC2 security group ID
EC2_SG_ID=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=YourEC2Name" \
    --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
    --output text \
    --region ap-south-1)

echo "Adding ingress rule to allow EC2 to connect to RDS..."
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 5432 \
    --source-group $EC2_SG_ID \
    --region ap-south-1 || echo "Rule may already exist"

echo "Creating RDS instance..."
aws rds create-db-instance \
    --db-instance-identifier $DB_INSTANCE_ID \
    --db-instance-class $DB_INSTANCE_CLASS \
    --engine postgres \
    --engine-version 15.4 \
    --master-username $DB_USERNAME \
    --master-user-password $DB_PASSWORD \
    --allocated-storage $ALLOCATED_STORAGE \
    --db-subnet-group-name mlera-db-subnet-group \
    --vpc-security-group-ids $SG_ID \
    --db-name $DB_NAME \
    --backup-retention-period 7 \
    --no-publicly-accessible \
    --region ap-south-1

echo "Waiting for RDS instance to be available..."
aws rds wait db-instance-available \
    --db-instance-identifier $DB_INSTANCE_ID \
    --region ap-south-1

echo "Getting RDS endpoint..."
RDS_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier $DB_INSTANCE_ID \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text \
    --region ap-south-1)

echo "=== RDS Creation Complete ==="
echo "RDS Endpoint: $RDS_ENDPOINT"
echo "Database Name: $DB_NAME"
echo "Username: $DB_USERNAME"
echo "Password: $DB_PASSWORD"
echo ""
echo "Update your .env file with:"
echo "RDS_ENDPOINT=$RDS_ENDPOINT"
