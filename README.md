# MLera Backend

Complete backend system with CI/CD pipeline for deploying to AWS EC2.

## Services

- **ProdMainAPI** - Main API Gateway (Port 8000)
- **ProdDBSystem** - Database Service API (Port 8080)
- **ProdNotification** - Notification Service (Port 8001)

## Quick Start

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete setup instructions.

## Structure

```
MLeraBackend/
├── ProdMainAPI/           # Main API service
├── ProdDBSystem/          # Database service
├── ProdNotification/      # Notification service
├── .github/workflows/     # CI/CD pipeline
├── scripts/               # Deployment scripts
│   ├── create-ecr.sh
│   ├── create-rds.sh
│   ├── create-elasticache.sh
│   ├── create-sns-sqs.sh
│   ├── create-sqs-db.sh
│   ├── create-dynamodb.sh
│   ├── populate-templates.sh
│   ├── create-lambda-email.sh
│   ├── create-lambda-db.sh
│   ├── ec2-setup.sh
│   ├── deploy.sh
│   └── setup-all.sh       # Master setup script
├── docker-compose.yml     # Container orchestration
├── nginx.conf            # Reverse proxy config
├── .env.template         # Environment variables template
├── DEPLOYMENT.md         # Complete deployment guide
└── LAMBDA_README.md      # Lambda functions documentation
```

## Deployment

### Quick Setup (Automated)
```bash
cd scripts
./setup-all.sh
```

### Manual Setup
1. Create AWS resources (ECR, RDS, ElastiCache, SNS, SQS, DynamoDB, Lambda)
2. Setup EC2 instance
3. Configure GitHub secrets
4. Push to main branch - automatic deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions.

## Architecture

```
GitHub → Actions → ECR → EC2 (Docker Compose)
                           ├── Nginx (port 80)
                           ├── Main API (port 8000)
                           ├── DB API (port 8080)
                           └── Notification API (port 8001)
                                 ↓
                    RDS + ElastiCache (private subnet)
```
