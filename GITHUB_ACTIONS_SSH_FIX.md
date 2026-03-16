# Fixing GitHub Actions SSH Connection Timeout

## Problem
```
ssh: connect to host *** port 22: Connection timed out
```

This means GitHub Actions cannot reach your EC2 instance on port 22.

## Root Causes

1. **Security Group blocking SSH** - Most common
2. **EC2 in private subnet** - No public IP
3. **Network ACLs blocking traffic**
4. **EC2 instance stopped/terminated**

## Solutions

### Solution 1: Fix Security Group (Quickest)

**Check your EC2 Security Group allows SSH from anywhere:**

```bash
# Get your EC2 security group ID
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=mlera-app-server" \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
  --output text

# Add SSH rule allowing all IPs (GitHub Actions uses dynamic IPs)
aws ec2 authorize-security-group-ingress \
  --group-id sg-YOUR_SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0 \
  --region ap-south-1
```

**Security Note:** This opens SSH to the internet. For production:
- Use key-based authentication only (no passwords)
- Consider using SSM instead (Solution 3)
- Monitor SSH access logs
- Use fail2ban or similar tools

### Solution 2: Verify EC2 Configuration

```bash
# Check if EC2 has public IP
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=mlera-app-server" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text

# Check if EC2 is running
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=mlera-app-server" \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text
```

If no public IP, your EC2 is in a private subnet. Use Solution 3.

### Solution 3: Use AWS Systems Manager (SSM) - Recommended

**No SSH needed! No security group changes!**

#### Update GitHub Actions Workflow

Replace the deploy job with SSM-based deployment:

```yaml
deploy:
  needs: build-and-push
  runs-on: ubuntu-latest
  
  steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ap-south-1

    - name: Upload deployment files to S3
      run: |
        aws s3 cp docker-compose.yml s3://mlera-deployment/docker-compose.yml
        aws s3 cp nginx.conf s3://mlera-deployment/nginx.conf
        aws s3 cp scripts/deploy.sh s3://mlera-deployment/deploy.sh

    - name: Deploy via SSM
      run: |
        INSTANCE_ID=${{ secrets.EC2_INSTANCE_ID }}
        
        COMMAND_ID=$(aws ssm send-command \
          --instance-ids "$INSTANCE_ID" \
          --document-name "AWS-RunShellScript" \
          --parameters 'commands=[
            "cd /home/ec2-user/app",
            "aws s3 cp s3://mlera-deployment/docker-compose.yml .",
            "aws s3 cp s3://mlera-deployment/nginx.conf .",
            "aws s3 cp s3://mlera-deployment/deploy.sh .",
            "chmod +x deploy.sh",
            "./deploy.sh"
          ]' \
          --region ap-south-1 \
          --query 'Command.CommandId' \
          --output text)
        
        echo "Waiting for command to complete..."
        aws ssm wait command-executed \
          --command-id "$COMMAND_ID" \
          --instance-id "$INSTANCE_ID" \
          --region ap-south-1
        
        echo "Deployment complete!"
```

#### Prerequisites for SSM:

1. **Create S3 bucket:**
```bash
aws s3 mb s3://mlera-deployment --region ap-south-1
```

2. **Ensure EC2 has IAM role with these policies:**
   - `AmazonSSMManagedInstanceCore`
   - `AmazonS3ReadOnlyAccess`

3. **Add GitHub Secret:**
   - `EC2_INSTANCE_ID`: Your EC2 instance ID (e.g., i-1234567890abcdef0)

4. **Verify SSM agent is running on EC2:**
```bash
# SSH into EC2 (one time setup)
sudo systemctl status amazon-ssm-agent
```

### Solution 4: Use Self-Hosted Runner

Deploy a GitHub Actions runner inside your VPC:

```bash
# On a bastion or instance with VPC access
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz
./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token YOUR_TOKEN
./run.sh
```

Update workflow:
```yaml
jobs:
  deploy:
    runs-on: self-hosted  # Use your runner
```

## Quick Fix for Testing

**Temporarily allow SSH from your current IP only:**

```bash
# Get your current IP
MY_IP=$(curl -s ifconfig.me)

# Allow SSH from your IP
aws ec2 authorize-security-group-ingress \
  --group-id sg-YOUR_SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr $MY_IP/32 \
  --region ap-south-1
```

Then test SSH manually:
```bash
ssh -i your-key.pem ec2-user@YOUR_EC2_IP
```

If this works, the issue is the security group. Use Solution 1 or 3.

## Recommended Approach

**For Production: Use SSM (Solution 3)**
- ✅ No SSH port exposure
- ✅ Works with private subnets
- ✅ No bastion host needed
- ✅ Audit trail in CloudWatch
- ✅ No key management

**For Development: Fix Security Group (Solution 1)**
- ✅ Quick and simple
- ✅ Works with existing workflow
- ⚠️ Exposes SSH to internet (use strong keys)

## Debugging Steps

1. **Test SSH from your local machine:**
```bash
ssh -i your-key.pem -v ec2-user@YOUR_EC2_IP
```

2. **Check security group rules:**
```bash
aws ec2 describe-security-groups \
  --group-ids sg-YOUR_SG_ID \
  --region ap-south-1
```

3. **Check EC2 status:**
```bash
aws ec2 describe-instances \
  --instance-ids i-YOUR_INSTANCE_ID \
  --region ap-south-1
```

4. **Test from GitHub Actions (add debug step):**
```yaml
- name: Debug connection
  run: |
    echo "Testing connection to ${{ secrets.EC2_HOST }}"
    nc -zv ${{ secrets.EC2_HOST }} 22 || echo "Port 22 not reachable"
```

## chmod 600 vs 400

**Use 400 for SSH keys (more secure):**

```yaml
- name: Deploy to EC2
  run: |
    echo "$PRIVATE_KEY" > private_key.pem
    chmod 400 private_key.pem  # Read-only (better than 600)
```

**Permissions explained:**
- `400` = `-r--------` = Owner can read only
- `600` = `-rw-------` = Owner can read and write
- SSH only needs read access, so 400 is more restrictive and secure
