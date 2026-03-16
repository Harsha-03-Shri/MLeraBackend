# MLera Backend Deployment Guide

Complete CI/CD setup for deploying ProdMainAPI, ProdDBSystem, and ProdNotification to EC2.

## Architecture Overview

- **ProdMainAPI** (Port 8000): Main API Gateway
- **ProdDBSystem** (Port 8080): Database Service API
- **ProdNotification** (Port 8001): Notification Service
- **Nginx**: Reverse proxy routing traffic to services
- **RDS PostgreSQL**: Database in private subnet
- **ElastiCache Redis**: Cache in private subnet
- **SNS + SQS**: Message queuing for notifications and DB operations
- **Lambda Functions**: Async consumers for email and DB operations
- **DynamoDB**: User and template storage for notifications
- **ALB**: Routes traffic to EC2 on port 80

## Prerequisites

1. AWS Account with access to:
   - EC2, ECR, RDS, ElastiCache
   - VPC, Subnets, Security Groups
   - IAM for permissions

2. GitHub repository with the code

## Setup Steps

### 1. Create ECR Repositories

```bash
cd scripts
chmod +x create-ecr.sh
./create-ecr.sh
```

This creates three ECR repositories for the Docker images.

### 2. Create RDS Instance

Edit `scripts/create-rds.sh` and update:
- `DB_PASSWORD`: Set a secure password
- `PRIVATE_SUBNET_2`: Add your second private subnet ID

```bash
cd scripts
chmod +x create-rds.sh
./create-rds.sh
```

This will output the RDS endpoint. Save it for later.

### 3. Create ElastiCache Redis

Edit `scripts/create-elasticache.sh` and update:
- `PRIVATE_SUBNET_2`: Add your second private subnet ID

```bash
cd scripts
chmod +x create-elasticache.sh
./create-elasticache.sh
```

This will output the Redis endpoint. Save it for later.

### 4. Create SNS Topic and SQS Queues

```bash
cd scripts
chmod +x create-sns-sqs.sh
./create-sns-sqs.sh
```

This creates:
- SNS topic for notifications
- SQS queue for email notifications with SNS subscription

Save the output values (SNS_TOPIC_ARN, EMAIL_QUEUE_URL).

### 5. Create SQS Queue for DB Operations

```bash
cd scripts
chmod +x create-sqs-db.sh
./create-sqs-db.sh
```

Save the SQS_QUEUE_URL for DB operations.

### 6. Create DynamoDB Tables

```bash
cd scripts
chmod +x create-dynamodb.sh
./create-dynamodb.sh
```

This creates:
- Users table (userId, channel)
- Templates table (TemplateType, Channel)

### 7. Populate DynamoDB Templates

```bash
cd scripts
chmod +x populate-templates.sh
./populate-templates.sh
```

This adds default email templates for Registration, ModuleCompletion, and CoursePurchase.

### 8. Deploy Lambda Function for Email Notifications

```bash
cd scripts
chmod +x create-lambda-email.sh
./create-lambda-email.sh <EMAIL_QUEUE_URL> <GMAIL_FROM> <GMAIL_APP_PASSWORD>
```

Example:
```bash
./create-lambda-email.sh \
  https://sqs.ap-south-1.amazonaws.com/123456789012/mlera-email-queue \
  noreply@mlera.com \
  your_gmail_app_password
```

**Note**: Use Gmail App Password, not your regular password. Generate one at: https://myaccount.google.com/apppasswords

### 9. Deploy Lambda Function for DB Operations

```bash
cd scripts
chmod +x create-lambda-db.sh
./create-lambda-db.sh <DB_QUEUE_URL> <RDS_ENDPOINT> <DB_NAME> <DB_USER> <DB_PASSWORD> <SUBNET_IDS> <SECURITY_GROUP_IDS>
```

Example:
```bash
./create-lambda-db.sh \
  https://sqs.ap-south-1.amazonaws.com/123456789012/mlera-db-operations-queue \
  mlera-db.xxx.ap-south-1.rds.amazonaws.com \
  mlera \
  postgres \
  your_db_password \
  subnet-xxx,subnet-yyy \
  sg-xxx
```

**Important**: Use the same private subnets and security group that can access RDS.

### 10. Create and Configure EC2 Instance

**Create EC2 Instance:**

```bash
# Option 1: Via AWS Console
# - Launch EC2 instance (t3.micro or larger)
# - Choose Amazon Linux 2023 or Ubuntu
# - Select public subnet (for direct SSH access)
# - Enable auto-assign public IP
# - Create/select security group allowing SSH (port 22) and HTTP (port 80)
# - Create/select key pair for SSH access
# - Launch instance

# Option 2: Via AWS CLI
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.micro \
  --key-name your-key-pair \
  --subnet-id subnet-PUBLIC \
  --security-group-ids sg-YOUR_SG \
  --associate-public-ip-address \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=mlera-app-server}]' \
  --region ap-south-1
```

**Note the EC2 Public IP address for SSH access.**

**Setup EC2 Instance:**

SSH into your EC2 instance and run:

```bash
# Copy the setup script to EC2
scp scripts/ec2-setup.sh ec2-user@YOUR_EC2_IP:/home/ec2-user/

# SSH into EC2
ssh ec2-user@YOUR_EC2_IP

# Run setup
chmod +x ec2-setup.sh
./ec2-setup.sh

# Configure AWS credentials
aws configure
```

### 11. Create IAM Role for EC2

Your EC2 instance needs an IAM role with these permissions:
- AmazonEC2ContainerRegistryReadOnly
- AmazonRDSFullAccess (or specific RDS access)
- AmazonElastiCacheFullAccess (or specific ElastiCache access)
- AmazonSNSFullAccess
- AmazonSQSFullAccess
- AmazonDynamoDBFullAccess

Attach this role to your EC2 instance.

### 12. Configure Environment Variables on EC2

SSH into EC2 and create `.env` file:

```bash
cd /home/ec2-user/app
nano .env
```

Copy from `.env.template` and fill in actual values:
- RDS_ENDPOINT (from step 2)
- ELASTICACHE_ENDPOINT (from step 3)
- DB_PASSWORD
- SQS_QUEUE_URL (from step 5)
- SNS_TOPIC_ARN (from step 4)
- DYNAMODB_TABLE=Users

### 13. Configure GitHub Secrets

In your GitHub repository, go to Settings > Secrets and add:

- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `EC2_SSH_PRIVATE_KEY`: Private key to SSH into EC2
- `EC2_HOST`: Your EC2 public IP or DNS
- `EC2_USER`: Usually `ec2-user`

### 14. Update Security Groups

Ensure your EC2 security group allows:
- Inbound: Port 80 from ALB security group
- Outbound: All traffic

Ensure RDS security group allows:
- Inbound: Port 5432 from EC2 security group
- Inbound: Port 5432 from Lambda security group

Ensure ElastiCache security group allows:
- Inbound: Port 6379 from EC2 security group

### 15. Deploy

Push code to GitHub main/master branch:

```bash
git add .
git commit -m "Setup CI/CD pipeline"
git push origin main
```

GitHub Actions will automatically:
1. Build Docker images for all three services
2. Push images to ECR
3. Deploy to EC2
4. Start all services with docker-compose

### 16. Verify Deployment

Check ALB health:
```bash
curl http://YOUR_ALB_DNS/health
```

Check individual services:
```bash
curl http://YOUR_ALB_DNS/api/main/health
curl http://YOUR_ALB_DNS/api/db/health
curl http://YOUR_ALB_DNS/api/notification/health
```

## Manual Deployment

If you need to deploy manually:

```bash
ssh ec2-user@YOUR_EC2_IP
cd /home/ec2-user/app
./scripts/deploy.sh
```

## Lambda Function Updates

### Update Email Lambda

```bash
cd ProdNotification/Consumer/EmailConsumer
mkdir -p package
pip install -r ../Requirements.txt -t package/
cp lambdaFunction.py smtpClient.py package/
cd package
zip -r ../lambda-deployment.zip .
cd ..
zip -g lambda-deployment.zip lambdaFunction.py smtpClient.py
aws lambda update-function-code \
  --function-name mlera-email-consumer \
  --zip-file fileb://lambda-deployment.zip \
  --region ap-south-1
```

### Update DB Lambda

```bash
cd ProdDBSystem/Consumer
mkdir -p package
pip install psycopg2-binary -t package/
cp lambdaFunction.py Event.py package/
cp -r ../Resorces package/
cd package
zip -r ../lambda-deployment.zip .
cd ..
zip -g lambda-deployment.zip lambdaFunction.py Event.py
aws lambda update-function-code \
  --function-name mlera-db-consumer \
  --zip-file fileb://lambda-deployment.zip \
  --region ap-south-1
```

## Monitoring

Check running containers:
```bash
docker-compose ps
```

View logs:
```bash
docker-compose logs -f
docker-compose logs -f main-api
docker-compose logs -f db-api
docker-compose logs -f notification-api
```

## Troubleshooting

### Services not starting
```bash
docker-compose logs
```

### Can't pull images from ECR
```bash
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 812661756903.dkr.ecr.ap-south-1.amazonaws.com
```

### Database connection issues
- Verify RDS endpoint in .env
- Check security group rules
- Verify EC2 can reach private subnet

### Redis connection issues
- Verify ElastiCache endpoint in .env
- Check security group rules

### Lambda not processing messages
```bash
# Check Lambda logs
aws logs tail /aws/lambda/mlera-email-consumer --follow --region ap-south-1
aws logs tail /aws/lambda/mlera-db-consumer --follow --region ap-south-1

# Check SQS queue for messages
aws sqs get-queue-attributes \
  --queue-url <QUEUE_URL> \
  --attribute-names ApproximateNumberOfMessages \
  --region ap-south-1
```

### Email not sending
- Verify Gmail app password is correct
- Check Lambda environment variables
- Check CloudWatch logs for SMTP errors
- Ensure Gmail account has "Less secure app access" enabled or use App Password

### DynamoDB errors
- Verify table names are correct (Users, Templates)
- Check IAM permissions for Lambda and ECS tasks
- Verify templates are populated using populate-templates.sh

## Rollback

To rollback to a previous version:

```bash
# On EC2
cd /home/ec2-user/app
export IMAGE_TAG=<previous-git-sha>
docker-compose pull
docker-compose up -d
```

## Cost Optimization

- Use t3.micro for RDS and ElastiCache in dev/test
- Stop EC2 instance when not in use
- Use reserved instances for production
- Enable RDS automated backups with appropriate retention

## Architecture Flow

### Notification Flow
1. Main API → Notification API (HTTP)
2. Notification API → SNS Topic (publish)
3. SNS → SQS Email Queue (filtered by Channel=email)
4. SQS → Lambda Email Consumer (trigger)
5. Lambda → Gmail SMTP (send email)

### DB Operations Flow
1. DB API → SQS DB Queue (async operations)
2. SQS → Lambda DB Consumer (trigger)
3. Lambda → RDS (database operations)

## Next Steps

1. Set up CloudWatch alarms for monitoring
2. Configure auto-scaling for EC2 (optional)
3. Set up SSL/TLS certificate on ALB
4. Configure Route53 for custom domain
5. Set up CloudWatch Logs for centralized logging
6. Add more notification channels (SMS, Push) with additional SQS queues
7. Implement dead-letter queues for failed messages
