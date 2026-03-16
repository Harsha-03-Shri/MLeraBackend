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

# Enable Docker to start on boot
sudo systemctl enable docker

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

echo "=== Setup Complete ==="
echo ""
echo "IMPORTANT: You must logout and login again for Docker permissions to take effect!"
echo ""
echo "Run: exit"
echo "Then SSH back in: ssh -i your-key.pem ec2-user@YOUR_EC2_IP"
echo ""
echo "Next steps after re-login:"
echo "1. Verify Docker works: docker ps"
echo "2. Run 'aws configure' to set up AWS credentials (or use IAM role)"
echo "3. Create .env file in /home/ec2-user/app/"
echo "4. Ensure EC2 IAM role has ECR, RDS, ElastiCache, SNS, SQS, DynamoDB permissions"
echo ""
