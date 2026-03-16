# Deployment Scripts

This directory contains all AWS infrastructure setup and deployment scripts for MLera Backend.

## Quick Start

Run the master setup script to create all infrastructure:

```bash
./setup-all.sh
```

This will guide you through creating all AWS resources in the correct order.

## Individual Scripts

### Infrastructure Setup Scripts

#### 1. create-ecr.sh
Creates three ECR repositories for Docker images.

**Usage:**
```bash
./create-ecr.sh
```

**Creates:**
- prod-main-api
- prod-db-system
- prod-notification

**Output:** ECR repository URIs

---

#### 2. create-rds.sh
Creates RDS PostgreSQL instance in private subnet.

**Prerequisites:** Edit script to set DB_PASSWORD and PRIVATE_SUBNET_2

**Usage:**
```bash
./create-rds.sh
```

**Creates:**
- RDS PostgreSQL instance (db.t3.micro)
- DB subnet group
- Security group

**Output:** RDS endpoint

---

#### 3. create-elasticache.sh
Creates ElastiCache Redis cluster in private subnet.

**Prerequisites:** Edit script to set PRIVATE_SUBNET_2

**Usage:**
```bash
./create-elasticache.sh
```

**Creates:**
- Redis cluster (cache.t3.micro)
- Cache subnet group
- Security group

**Output:** Redis endpoint

---

#### 4. create-sns-sqs.sh
Creates SNS topic and SQS queue for email notifications.

**Usage:**
```bash
./create-sns-sqs.sh
```

**Creates:**
- SNS topic (mlera-notifications)
- SQS queue (mlera-email-queue)
- SNS subscription with filter policy (Channel=email)
- Queue policy for SNS

**Output:** SNS_TOPIC_ARN, EMAIL_QUEUE_URL

---

#### 5. create-sqs-db.sh
Creates SQS queue for database operations.

**Usage:**
```bash
./create-sqs-db.sh
```

**Creates:**
- SQS queue (mlera-db-operations-queue)

**Output:** SQS_QUEUE_URL, Queue ARN

---

#### 6. create-dynamodb.sh
Creates DynamoDB tables for notification service.

**Usage:**
```bash
./create-dynamodb.sh
```

**Creates:**
- Users table (PK: userId, SK: channel)
  - Attributes: id (email/apn/fcm token), Name
- Templates table (PK: TemplateType, SK: Channel)
  - Attributes: TemplateId, Subject, Body, Version, CreatedAt

**Billing:** PAY_PER_REQUEST

---

#### 7. populate-templates.sh
Populates Templates table with default notification templates.

**Prerequisites:** DynamoDB tables must exist

**Usage:**
```bash
./populate-templates.sh
```

**Creates:**
- Registration email template
- ModuleCompletion email template
- CoursePurchase email template

**Template Variables:** {Name}, {Email}, {QuizPercentage}

---

#### 8. create-lambda-email.sh
Creates Lambda function for email notifications.

**Usage:**
```bash
./create-lambda-email.sh <EMAIL_QUEUE_URL> <GMAIL_FROM> <GMAIL_APP_PASSWORD>
```

**Example:**
```bash
./create-lambda-email.sh \
  https://sqs.ap-south-1.amazonaws.com/123456789012/mlera-email-queue \
  noreply@mlera.com \
  abcd1234efgh5678
```

**Creates:**
- Lambda function (mlera-email-consumer)
- IAM role with SQS and CloudWatch permissions
- SQS trigger (batch size: 10)

**Runtime:** Python 3.11
**Timeout:** 300 seconds
**Memory:** 256 MB

**Note:** Use Gmail App Password, not regular password

---

#### 9. create-lambda-db.sh
Creates Lambda function for database operations.

**Usage:**
```bash
./create-lambda-db.sh <DB_QUEUE_URL> <RDS_ENDPOINT> <DB_NAME> <DB_USER> <DB_PASSWORD> <SUBNET_IDS> <SECURITY_GROUP_IDS>
```

**Example:**
```bash
./create-lambda-db.sh \
  https://sqs.ap-south-1.amazonaws.com/123456789012/mlera-db-operations-queue \
  mlera-db.xxx.ap-south-1.rds.amazonaws.com \
  mlera \
  postgres \
  mypassword \
  subnet-xxx,subnet-yyy \
  sg-xxx
```

**Creates:**
- Lambda function (mlera-db-consumer)
- IAM role with SQS, CloudWatch, and VPC permissions
- SQS trigger (batch size: 10)
- VPC configuration

**Runtime:** Python 3.11
**Timeout:** 300 seconds
**Memory:** 512 MB

**Note:** Must use private subnets with RDS access

---

### Deployment Scripts

#### 10. ec2-setup.sh
Sets up EC2 instance with Docker and AWS CLI.

**Usage:**
```bash
# Copy to EC2
scp ec2-setup.sh ec2-user@YOUR_EC2_IP:/home/ec2-user/

# SSH and run
ssh ec2-user@YOUR_EC2_IP
chmod +x ec2-setup.sh
./ec2-setup.sh
```

**Installs:**
- Docker
- Docker Compose
- AWS CLI
- Git

**Creates:** /home/ec2-user/app directory

---

#### 11. deploy.sh
Deploys application to EC2 using Docker Compose.

**Usage:**
```bash
# On EC2
cd /home/ec2-user/app
./deploy.sh
```

**Actions:**
- Pulls latest images from ECR
- Stops existing containers
- Starts new containers with docker-compose
- Shows container status

---

#### 12. setup-all.sh
Master script that runs all setup scripts in order.

**Usage:**
```bash
./setup-all.sh
```

**Interactive:** Prompts for required values at each step

**Creates:** Complete infrastructure from scratch

---

## Execution Order

For manual setup, run scripts in this order:

1. `create-ecr.sh`
2. `create-rds.sh`
3. `create-elasticache.sh`
4. `create-sns-sqs.sh`
5. `create-sqs-db.sh`
6. `create-dynamodb.sh`
7. `populate-templates.sh`
8. `create-lambda-email.sh`
9. `create-lambda-db.sh`
10. `ec2-setup.sh` (on EC2 instance)
11. `deploy.sh` (on EC2 instance)

## Prerequisites

- AWS CLI installed and configured
- Appropriate IAM permissions
- VPC with public and private subnets
- Security groups configured
- Gmail account with app password (for email Lambda)

## Environment Variables

After running scripts, update `.env` file with:

```bash
DOCKER_REGISTRY=<account-id>.dkr.ecr.ap-south-1.amazonaws.com
RDS_ENDPOINT=<from create-rds.sh>
ELASTICACHE_ENDPOINT=<from create-elasticache.sh>
SNS_TOPIC_ARN=<from create-sns-sqs.sh>
SQS_QUEUE_URL=<from create-sqs-db.sh>
DYNAMODB_TABLE=Users
```

## GitHub Secrets

Configure these secrets in GitHub repository:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `EC2_SSH_PRIVATE_KEY`
- `EC2_HOST`
- `EC2_USER`

## Troubleshooting

### Script fails with permission error
```bash
chmod +x scripts/*.sh
```

### AWS CLI not found
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### Resource already exists
Scripts will skip or update existing resources. Check AWS console to verify.

### Lambda deployment package too large
Ensure you're only including necessary dependencies in the package.

### VPC/Subnet issues
Verify your VPC has:
- Public subnets for EC2
- Private subnets for RDS/ElastiCache/Lambda
- NAT Gateway for private subnet internet access
- Proper route tables

## Cleanup

To delete all resources:

```bash
# Delete Lambda functions
aws lambda delete-function --function-name mlera-email-consumer --region ap-south-1
aws lambda delete-function --function-name mlera-db-consumer --region ap-south-1

# Delete SQS queues
aws sqs delete-queue --queue-url <EMAIL_QUEUE_URL> --region ap-south-1
aws sqs delete-queue --queue-url <DB_QUEUE_URL> --region ap-south-1

# Delete SNS topic
aws sns delete-topic --topic-arn <SNS_TOPIC_ARN> --region ap-south-1

# Delete DynamoDB tables
aws dynamodb delete-table --table-name Users --region ap-south-1
aws dynamodb delete-table --table-name Templates --region ap-south-1

# Delete ElastiCache cluster
aws elasticache delete-cache-cluster --cache-cluster-id mlera-redis --region ap-south-1

# Delete RDS instance
aws rds delete-db-instance --db-instance-identifier mlera-postgres-db --skip-final-snapshot --region ap-south-1

# Delete ECR repositories
aws ecr delete-repository --repository-name prod-main-api --force --region ap-south-1
aws ecr delete-repository --repository-name prod-db-system --force --region ap-south-1
aws ecr delete-repository --repository-name prod-notification --force --region ap-south-1
```

## Support

For issues or questions, refer to:
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Complete deployment guide
- [LAMBDA_README.md](../LAMBDA_README.md) - Lambda functions documentation
- AWS documentation for specific services
