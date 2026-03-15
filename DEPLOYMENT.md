# MLera Backend Deployment Guide

Complete CI/CD setup for deploying ProdMainAPI, ProdDBSystem, and ProdNotification to EC2.

## Architecture Overview

- **ProdMainAPI** (Port 8000): Main API Gateway
- **ProdDBSystem** (Port 8080): Database Service API
- **ProdNotification** (Port 8000): Notification Service
- **Nginx**: Reverse proxy routing traffic to services
- **RDS PostgreSQL**: Database in private subnet
- **ElastiCache Redis**: Cache in private subnet
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
chmod +x create-ecr.sh
./create-ecr.sh
```

### 2. Create RDS Instance

Edit `create-rds.sh` and update:
- `DB_PASSWORD`: Set a secure password
- `PRIVATE_SUBNET_2`: Add your second private subnet ID

```bash
chmod +x create-rds.sh
./create-rds.sh
```

This will output the RDS endpoint. Save it for later.

### 3. Create ElastiCache Redis

Edit `create-elasticache.sh` and update:
- `PRIVATE_SUBNET_2`: Add your second private subnet ID

```bash
chmod +x create-elasticache.sh
./create-elasticache.sh
```

This will output the Redis endpoint. Save it for later.

### 4. Configure EC2 Instance

SSH into your EC2 instance and run:

```bash
# Copy the setup script to EC2
scp ec2-setup.sh ec2-user@YOUR_EC2_IP:/home/ec2-user/

# SSH into EC2
ssh ec2-user@YOUR_EC2_IP

# Run setup
chmod +x ec2-setup.sh
./ec2-setup.sh

# Configure AWS credentials
aws configure
```

### 5. Create IAM Role for EC2

Your EC2 instance needs an IAM role with these permissions:
- AmazonEC2ContainerRegistryReadOnly
- AmazonRDSFullAccess (or specific RDS access)
- AmazonElastiCacheFullAccess (or specific ElastiCache access)
- AmazonSNSFullAccess
- AmazonSQSFullAccess
- AmazonDynamoDBFullAccess

Attach this role to your EC2 instance.

### 6. Configure Environment Variables on EC2

SSH into EC2 and create `.env` file:

```bash
cd /home/ec2-user/app
nano .env
```

Copy from `.env.template` and fill in actual values:
- RDS_ENDPOINT (from step 2)
- ELASTICACHE_ENDPOINT (from step 3)
- DB_PASSWORD
- SQS_QUEUE_URL
- SNS_TOPIC_ARN
- DYNAMODB_TABLE

### 7. Configure GitHub Secrets

In your GitHub repository, go to Settings > Secrets and add:

- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `EC2_SSH_PRIVATE_KEY`: Private key to SSH into EC2
- `EC2_HOST`: Your EC2 public IP or DNS
- `EC2_USER`: Usually `ec2-user`

### 8. Update Security Groups

Ensure your EC2 security group allows:
- Inbound: Port 80 from ALB security group
- Outbound: All traffic

Ensure RDS security group allows:
- Inbound: Port 5432 from EC2 security group

Ensure ElastiCache security group allows:
- Inbound: Port 6379 from EC2 security group

### 9. Deploy

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

### 10. Verify Deployment

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
./deploy.sh
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

## Next Steps

1. Set up CloudWatch alarms for monitoring
2. Configure auto-scaling for EC2 (optional)
3. Set up SSL/TLS certificate on ALB
4. Configure Route53 for custom domain
5. Set up CloudWatch Logs for centralized logging
