# Deploy schema.sql to RDS PostgreSQL

## Prerequisites
- EC2 instance running and accessible
- RDS PostgreSQL instance created
- Security group allows EC2 → RDS connection on port 5432
- PostgreSQL client installed on EC2

---

## Step 1: Copy schema.sql to EC2

### Option A: Using SCP (if you have SSH key)
```bash
# From your local machine
scp -i /path/to/your-key.pem \
    /home/shriharsha/Code/MLeraBackend/schema.sql \
    ec2-user@<EC2_PUBLIC_IP>:/home/ec2-user/schema.sql
```

### Option B: Using AWS Systems Manager Session Manager (no SSH key needed)
```bash
# From your local machine
# First, start a session
aws ssm start-session --target <EC2_INSTANCE_ID> --region ap-south-1

# Then on EC2, create the file
cat > /home/ec2-user/schema.sql << 'EOF'
# Paste the entire schema.sql content here
EOF
```

### Option C: Using GitHub (recommended for CI/CD)
```bash
# SSH into EC2 first
ssh -i /path/to/your-key.pem ec2-user@<EC2_PUBLIC_IP>

# Then on EC2
cd /home/ec2-user
git clone https://github.com/<your-username>/MLeraBackend.git
# Or if already cloned
cd MLeraBackend
git pull origin main
```

---

## Step 2: Install PostgreSQL Client on EC2 (if not installed)

### For Amazon Linux 2023
```bash
# SSH into EC2
ssh -i /path/to/your-key.pem ec2-user@<EC2_PUBLIC_IP>

# Install PostgreSQL client
sudo dnf install -y postgresql15

# Verify installation
psql --version
```

### For Amazon Linux 2
```bash
# SSH into EC2
ssh -i /path/to/your-key.pem ec2-user@<EC2_PUBLIC_IP>

# Install PostgreSQL client
sudo amazon-linux-extras install postgresql14 -y
# OR
sudo yum install -y postgresql

# Verify installation
psql --version
```

---

## Step 3: Test RDS Connection

```bash
# Test connection to RDS
psql -h mlera-postgres-db.cxesw4ko2d5b.ap-south-1.rds.amazonaws.com \
     -U mlera_admin \
     -d postgres \
     -p 5432

# You'll be prompted for password: postgres
# If connection successful, you'll see: postgres=>
# Type \q to exit
```

---

## Step 4: Apply schema.sql to RDS

### Method 1: Direct execution
```bash
# Execute schema.sql on RDS
psql -h mlera-postgres-db.cxesw4ko2d5b.ap-south-1.rds.amazonaws.com \
     -U mlera_admin \
     -d mlera_db \
     -p 5432 \
     -f /home/ec2-user/MLeraBackend/schema.sql

# Enter password when prompted: postgres
```

### Method 2: Interactive execution (for verification)
```bash
# Connect to RDS
psql -h mlera-postgres-db.cxesw4ko2d5b.ap-south-1.rds.amazonaws.com \
     -U mlera_admin \
     -d mlera_db \
     -p 5432

# Once connected, run the schema file
\i /home/ec2-user/MLeraBackend/schema.sql

# Or if using relative path
\i schema.sql
```

---

## Step 5: Verify Schema Creation

```bash
# Connect to RDS
psql -h mlera-postgres-db.cxesw4ko2d5b.ap-south-1.rds.amazonaws.com \
     -U mlera_admin \
     -d mlera_db \
     -p 5432

# List all tables
\dt

# Expected output:
#              List of relations
#  Schema |       Name           | Type  |    Owner
# --------+----------------------+-------+-------------
#  public | Auth                 | table | mlera_admin
#  public | Course               | table | mlera_admin
#  public | Module               | table | mlera_admin
#  public | PracticeQuiz         | table | mlera_admin
#  public | Quiz                 | table | mlera_admin
#  public | User                 | table | mlera_admin
#  public | UserCourse           | table | mlera_admin
#  public | UserModuleProgress   | table | mlera_admin

# Check specific table structure
\d "User"

# Check if UUID extension is enabled
\dx

# Exit
\q
```

---

## Step 6: Insert Sample Course Data (Optional)

```bash
# Connect to RDS
psql -h mlera-postgres-db.cxesw4ko2d5b.ap-south-1.rds.amazonaws.com \
     -U mlera_admin \
     -d mlera_db \
     -p 5432

# Insert sample courses
INSERT INTO "Course" ("CourseName", "Type") VALUES 
    ('Python Fundamentals', 'Programming'),
    ('Data Structures', 'Programming'),
    ('Machine Learning Basics', 'AI/ML');

# Insert sample modules
INSERT INTO "Module" ("CourseId", "ModuleName") 
SELECT "CourseId", 'Introduction' FROM "Course" WHERE "CourseName" = 'Python Fundamentals';

INSERT INTO "Module" ("CourseId", "ModuleName") 
SELECT "CourseId", 'Variables and Data Types' FROM "Course" WHERE "CourseName" = 'Python Fundamentals';

# Verify
SELECT * FROM "Course";
SELECT * FROM "Module";

# Exit
\q
```

---

## Complete Command Sequence (Copy-Paste Ready)

```bash
# ============================================
# STEP 1: SCP schema.sql to EC2
# ============================================
# Run from your LOCAL machine
scp -i ~/.ssh/your-key.pem \
    /home/shriharsha/Code/MLeraBackend/schema.sql \
    ec2-user@<EC2_PUBLIC_IP>:/home/ec2-user/schema.sql


# ============================================
# STEP 2: SSH into EC2
# ============================================
ssh -i ~/.ssh/your-key.pem ec2-user@<EC2_PUBLIC_IP>


# ============================================
# STEP 3: Install PostgreSQL client (on EC2)
# ============================================
# For Amazon Linux 2023
sudo dnf install -y postgresql15

# OR for Amazon Linux 2
sudo amazon-linux-extras install postgresql14 -y
# OR
sudo yum install -y postgresql


# ============================================
# STEP 4: Apply schema to RDS (on EC2)
# ============================================
export PGPASSWORD='postgres'
psql -h mlera-postgres-db.cxesw4ko2d5b.ap-south-1.rds.amazonaws.com \
     -U mlera_admin \
     -d mlera_db \
     -p 5432 \
     -f schema.sql


# ============================================
# STEP 5: Verify tables created (on EC2)
# ============================================
psql -h mlera-postgres-db.cxesw4ko2d5b.ap-south-1.rds.amazonaws.com \
     -U mlera_admin \
     -d mlera_db \
     -p 5432 \
     -c "\dt"


# ============================================
# STEP 6: Check UUID extension (on EC2)
# ============================================
psql -h mlera-postgres-db.cxesw4ko2d5b.ap-south-1.rds.amazonaws.com \
     -U mlera_admin \
     -d mlera_db \
     -p 5432 \
     -c "\dx"
```

---

## Troubleshooting

### Issue: Connection timeout
```bash
# Check security group allows EC2 → RDS on port 5432
# RDS Security Group Inbound Rules should have:
# Type: PostgreSQL, Port: 5432, Source: EC2 Security Group ID
```

### Issue: Password authentication failed
```bash
# Verify credentials in .env.template
# Default password: postgres
# Default user: mlera_admin
```

### Issue: Database does not exist
```bash
# Create database first
psql -h mlera-postgres-db.cxesw4ko2d5b.ap-south-1.rds.amazonaws.com \
     -U mlera_admin \
     -d postgres \
     -p 5432 \
     -c "CREATE DATABASE mlera_db;"
```

### Issue: Permission denied
```bash
# Ensure mlera_admin has proper permissions
psql -h mlera-postgres-db.cxesw4ko2d5b.ap-south-1.rds.amazonaws.com \
     -U mlera_admin \
     -d mlera_db \
     -p 5432 \
     -c "GRANT ALL PRIVILEGES ON DATABASE mlera_db TO mlera_admin;"
```

---

## Alternative: Using Docker Container on EC2

```bash
# If PostgreSQL client not installed, use Docker
docker run -it --rm \
    -v /home/ec2-user/schema.sql:/schema.sql \
    postgres:15 \
    psql -h mlera-postgres-db.cxesw4ko2d5b.ap-south-1.rds.amazonaws.com \
         -U mlera_admin \
         -d mlera_db \
         -p 5432 \
         -f /schema.sql
```

---

## Security Best Practices

1. **Don't use PGPASSWORD in production scripts**
   ```bash
   # Instead, use .pgpass file
   echo "mlera-postgres-db.cxesw4ko2d5b.ap-south-1.rds.amazonaws.com:5432:mlera_db:mlera_admin:postgres" > ~/.pgpass
   chmod 600 ~/.pgpass
   
   # Now you can connect without password prompt
   psql -h mlera-postgres-db.cxesw4ko2d5b.ap-south-1.rds.amazonaws.com \
        -U mlera_admin \
        -d mlera_db
   ```

2. **Use IAM authentication for RDS** (recommended for production)
   ```bash
   # Generate auth token
   aws rds generate-db-auth-token \
       --hostname mlera-postgres-db.cxesw4ko2d5b.ap-south-1.rds.amazonaws.com \
       --port 5432 \
       --username mlera_admin \
       --region ap-south-1
   ```

---

## Next Steps After Schema Deployment

1. ✅ Populate DynamoDB Templates table
   ```bash
   cd /home/ec2-user/MLeraBackend/scripts
   ./populate-templates.sh
   ```

2. ✅ Deploy Docker containers
   ```bash
   cd /home/ec2-user/MLeraBackend
   docker-compose up -d
   ```

3. ✅ Verify all services
   ```bash
   docker-compose ps
   curl http://localhost/health
   ```
