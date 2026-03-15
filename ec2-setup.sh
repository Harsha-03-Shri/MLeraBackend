#!/bin/bash
# Run this script on your EC2 instance for initial setup

set -e

echo "=== EC2 Initial Setup ==="

# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Create app directory
mkdir -p /home/ec2-user/app
cd /home/ec2-user/app

# Configure AWS CLI (you'll need to add credentials)
echo "Please configure AWS CLI with your credentials:"
echo "aws configure"

echo "=== Setup Complete ==="
echo "Next steps:"
echo "1. Run 'aws configure' to set up AWS credentials"
echo "2. Create .env file from .env.template"
echo "3. Ensure EC2 IAM role has ECR, RDS, ElastiCache, SNS, SQS, DynamoDB permissions"
