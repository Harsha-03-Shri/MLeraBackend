# MLera Backend

Complete backend system with CI/CD pipeline for deploying to AWS EC2.

## Services

- **ProdMainAPI** - Main API Gateway (Port 8000)
- **ProdDBSystem** - Database Service API (Port 8080)
- **ProdNotification** - Notification Service (Port 8000)

## Quick Start

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete setup instructions.

## Structure

```
MLeraBackend/
├── ProdMainAPI/           # Main API service
├── ProdDBSystem/          # Database service
├── ProdNotification/      # Notification service
├── .github/workflows/     # CI/CD pipeline
├── docker-compose.yml     # Container orchestration
├── nginx.conf            # Reverse proxy config
├── deploy.sh             # Deployment script
├── create-ecr.sh         # ECR setup
├── create-rds.sh         # RDS setup
├── create-elasticache.sh # Redis setup
├── ec2-setup.sh          # EC2 initial setup
├── .env.template         # Environment variables template
└── DEPLOYMENT.md         # Complete deployment guide
```

## Deployment

1. Create AWS resources (ECR, RDS, ElastiCache)
2. Setup EC2 instance
3. Configure GitHub secrets
4. Push to main branch - automatic deployment

## Architecture

```
GitHub → Actions → ECR → EC2 (Docker Compose)
                           ├── Nginx (port 80)
                           ├── Main API
                           ├── DB API
                           └── Notification API
                                 ↓
                    RDS + ElastiCache (private subnet)
```
