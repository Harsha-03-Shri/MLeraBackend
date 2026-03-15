#!/bin/bash
# Script to create ElastiCache Redis cluster

set -e

# Configuration
CACHE_CLUSTER_ID="mlera-redis-cluster"
CACHE_NODE_TYPE="cache.t3.micro"
VPC_ID="vpc-05f426c085e90fc3e"
PRIVATE_SUBNET_1="subnet-0d9dc14695f0cdf9c"
PRIVATE_SUBNET_2="subnet-XXXXXXXX"  # Add your second private subnet

echo "Creating Cache Subnet Group..."
aws elasticache create-cache-subnet-group \
    --cache-subnet-group-name mlera-cache-subnet-group \
    --cache-subnet-group-description "Subnet group for MLera ElastiCache" \
    --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
    --region ap-south-1 || echo "Subnet group may already exist"

echo "Creating Security Group for ElastiCache..."
CACHE_SG_ID=$(aws ec2 create-security-group \
    --group-name mlera-elasticache-sg \
    --description "Security group for MLera ElastiCache" \
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

echo "Adding ingress rule to allow EC2 to connect to Redis..."
aws ec2 authorize-security-group-ingress \
    --group-id $CACHE_SG_ID \
    --protocol tcp \
    --port 6379 \
    --source-group $EC2_SG_ID \
    --region ap-south-1 || echo "Rule may already exist"

echo "Creating ElastiCache Redis cluster..."
aws elasticache create-cache-cluster \
    --cache-cluster-id $CACHE_CLUSTER_ID \
    --cache-node-type $CACHE_NODE_TYPE \
    --engine redis \
    --engine-version 7.0 \
    --num-cache-nodes 1 \
    --cache-subnet-group-name mlera-cache-subnet-group \
    --security-group-ids $CACHE_SG_ID \
    --region ap-south-1

echo "Waiting for ElastiCache cluster to be available..."
aws elasticache wait cache-cluster-available \
    --cache-cluster-id $CACHE_CLUSTER_ID \
    --region ap-south-1

echo "Getting ElastiCache endpoint..."
REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters \
    --cache-cluster-id $CACHE_CLUSTER_ID \
    --show-cache-node-info \
    --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
    --output text \
    --region ap-south-1)

echo "=== ElastiCache Creation Complete ==="
echo "Redis Endpoint: $REDIS_ENDPOINT"
echo ""
echo "Update your .env file with:"
echo "ELASTICACHE_ENDPOINT=$REDIS_ENDPOINT"
