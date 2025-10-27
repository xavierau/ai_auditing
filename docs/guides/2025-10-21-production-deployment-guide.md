# Production Deployment Guide
**Version:** 1.0
**Last Updated:** 2025-10-21
**Target Environment:** Production (Hong Kong ap-east-1)
**Deployment Method:** Ansible (Infrastructure as Code)

---

## Overview

This guide provides step-by-step instructions for deploying the GenReport audit platform to production. The deployment uses Ansible for automation with manual verification steps.

**Deployment Architecture:**
- **Region:** AWS ap-east-1 (Hong Kong)
- **Database:** RDS PostgreSQL 16 (Multi-AZ)
- **Application:** EC2 Auto Scaling Group (min 2, max 10)
- **Load Balancer:** Application Load Balancer (ALB)
- **Storage:** S3 with encryption
- **Cache:** Redis cluster
- **Queue:** Celery with Redis backend

---

## Prerequisites

### 1. AWS Account Setup

**Required:**
- AWS account with appropriate permissions
- AWS CLI installed and configured
- Access to ap-east-1 region enabled

```bash
# Verify AWS CLI configuration
aws sts get-caller-identity
aws ec2 describe-regions --region ap-east-1

# Expected output: Should show account ID and ap-east-1 region
```

### 2. Required Secrets

Create secrets in AWS Secrets Manager **before deployment**:

```bash
# Database credentials
aws secretsmanager create-secret \
  --name genreport/database/prod \
  --description "Production database credentials" \
  --secret-string '{
    "username": "genreport_prod",
    "password": "'$(openssl rand -base64 32)'",
    "host": "PLACEHOLDER",
    "port": "5432",
    "database": "genreport"
  }' \
  --region ap-east-1

# Encryption master key
python3 -c "
from cryptography.fernet import Fernet
import json
import boto3

key = Fernet.generate_key()
client = boto3.client('secretsmanager', region_name='ap-east-1')
client.create_secret(
    Name='genreport/encryption/master-key',
    Description='Master encryption key',
    SecretString=json.dumps({'key': key.decode('utf-8')})
)
print('Encryption key created')
"

# JWT secret
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
aws secretsmanager create-secret \
  --name genreport/jwt/secret \
  --description "JWT signing secret" \
  --secret-string "{\"secret_key\": \"$JWT_SECRET\", \"algorithm\": \"HS256\"}" \
  --region ap-east-1
```

### 3. SSL/TLS Certificate

**Option A: AWS Certificate Manager (Recommended)**

```bash
# Request certificate
aws acm request-certificate \
  --domain-name api.genreport.com \
  --subject-alternative-names '*.genreport.com' \
  --validation-method DNS \
  --region ap-east-1

# Note the CertificateArn from output
# Add DNS validation records to Route53 or your DNS provider
```

**Option B: Let's Encrypt (Alternative)**

```bash
# Install certbot
sudo apt-get install certbot

# Generate certificate
sudo certbot certonly --standalone -d api.genreport.com
```

### 4. Infrastructure Tools

```bash
# Install Ansible
pip install ansible boto3 botocore

# Verify installation
ansible --version
# Required: Ansible 2.14+

# Install required Ansible collections
ansible-galaxy collection install amazon.aws
ansible-galaxy collection install community.postgresql
```

---

## Deployment Steps

### Step 1: Infrastructure Provisioning (30-45 minutes)

**1.1 Create VPC and Networking**

```bash
cd /path/to/genreport-infra

# Run VPC provisioning playbook
ansible-playbook -i inventory/production playbooks/01-vpc.yml \
  --extra-vars "environment=production region=ap-east-1"

# Verify VPC creation
aws ec2 describe-vpcs \
  --filters "Name=tag:Project,Values=genreport" "Name=tag:Environment,Values=production" \
  --region ap-east-1
```

**Expected Resources:**
- VPC: 10.0.0.0/16
- Public subnets: 2 (across AZs)
- Private subnets: 2 (for database)
- Internet Gateway
- NAT Gateway (for private subnet egress)
- Route tables

**1.2 Create RDS Database**

```bash
# Run RDS provisioning playbook
ansible-playbook -i inventory/production playbooks/02-rds.yml \
  --extra-vars "environment=production"

# This creates:
# - RDS PostgreSQL 16 instance (Multi-AZ)
# - DB subnet group
# - Security group
# - Parameter group

# Wait for database to be available (10-15 minutes)
aws rds wait db-instance-available \
  --db-instance-identifier genreport-prod \
  --region ap-east-1

# Get database endpoint
DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier genreport-prod \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text \
  --region ap-east-1)

echo "Database endpoint: $DB_ENDPOINT"

# Update secret with actual endpoint
aws secretsmanager update-secret \
  --secret-id genreport/database/prod \
  --secret-string "{
    \"username\": \"genreport_prod\",
    \"password\": \"$(aws secretsmanager get-secret-value --secret-id genreport/database/prod --query SecretString --output text | jq -r .password)\",
    \"host\": \"$DB_ENDPOINT\",
    \"port\": \"5432\",
    \"database\": \"genreport\"
  }" \
  --region ap-east-1
```

**1.3 Create S3 Buckets**

```bash
# Run S3 provisioning playbook
ansible-playbook -i inventory/production playbooks/03-s3.yml \
  --extra-vars "environment=production"

# Creates:
# - genreport-prod-encrypted (application files)
# - genreport-backups (backups)
# - genreport-logs (application logs)

# Verify buckets
aws s3 ls | grep genreport
```

**1.4 Create Redis Cluster**

```bash
# Run Redis provisioning playbook
ansible-playbook -i inventory/production playbooks/04-redis.yml \
  --extra-vars "environment=production"

# Wait for cluster to be available
aws elasticache describe-cache-clusters \
  --cache-cluster-id genreport-prod-redis \
  --show-cache-node-info \
  --region ap-east-1
```

---

### Step 2: Database Migration (10-15 minutes)

**2.1 Initialize Database Schema**

```bash
# SSH to bastion host (or use local connection with VPN)
ssh -i ~/.ssh/genreport-prod.pem ec2-user@bastion.genreport.com

# Clone repository
git clone https://github.com/yourusername/genreport.git
cd genreport

# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure database connection
export DATABASE_URL="postgresql://genreport_prod:PASSWORD@$DB_ENDPOINT:5432/genreport"

# Run migrations
alembic upgrade head

# Verify migrations
psql $DATABASE_URL -c "\dt"
# Should show all tables: tenants, users, projects, uploads, reports, audit_logs, etc.
```

**2.2 Create Initial Admin User**

```bash
# Run admin user creation script
python scripts/create_admin_user.py \
  --email admin@genreport.com \
  --name "System Administrator" \
  --tenant "GenReport Internal"

# Save admin credentials securely
```

---

### Step 3: Application Deployment (20-30 minutes)

**3.1 Build Application Image (if using Docker)**

```bash
# Build Docker image
docker build -t genreport-api:v1.0.0 .

# Tag for ECR
docker tag genreport-api:v1.0.0 \
  123456789012.dkr.ecr.ap-east-1.amazonaws.com/genreport-api:v1.0.0

# Push to ECR
aws ecr get-login-password --region ap-east-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.ap-east-1.amazonaws.com

docker push 123456789012.dkr.ecr.ap-east-1.amazonaws.com/genreport-api:v1.0.0
```

**3.2 Deploy Application Servers**

```bash
# Run application deployment playbook
ansible-playbook -i inventory/production playbooks/05-app-servers.yml \
  --extra-vars "environment=production version=v1.0.0"

# This creates:
# - EC2 launch template
# - Auto Scaling Group (min 2, max 10)
# - Application Load Balancer
# - Target group with health checks
# - Security groups

# Wait for instances to be healthy
aws elbv2 describe-target-health \
  --target-group-arn <TARGET_GROUP_ARN> \
  --region ap-east-1

# Should show "healthy" for all targets
```

**3.3 Deploy Celery Workers**

```bash
# Run Celery worker deployment
ansible-playbook -i inventory/production playbooks/06-celery-workers.yml \
  --extra-vars "environment=production"

# Creates:
# - Celery worker instances (2 workers)
# - Celery beat scheduler (1 instance)
# - Systemd service files
# - Auto-restart configuration

# Verify workers are running
celery -A genreport inspect ping
# Should show worker responses
```

---

### Step 4: DNS and Load Balancer (10 minutes)

**4.1 Configure Route53**

```bash
# Get Load Balancer DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names genreport-prod-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text \
  --region ap-east-1)

echo "ALB DNS: $ALB_DNS"

# Create Route53 record
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch "{
    \"Changes\": [{
      \"Action\": \"UPSERT\",
      \"ResourceRecordSet\": {
        \"Name\": \"api.genreport.com\",
        \"Type\": \"A\",
        \"AliasTarget\": {
          \"HostedZoneId\": \"<ALB_HOSTED_ZONE_ID>\",
          \"DNSName\": \"$ALB_DNS\",
          \"EvaluateTargetHealth\": true
        }
      }
    }]
  }"

# Wait for DNS propagation (1-5 minutes)
dig api.genreport.com +short
# Should return ALB IPs
```

**4.2 Configure SSL on Load Balancer**

```bash
# Attach ACM certificate to HTTPS listener
aws elbv2 modify-listener \
  --listener-arn <HTTPS_LISTENER_ARN> \
  --certificates CertificateArn=<ACM_CERTIFICATE_ARN> \
  --region ap-east-1

# Verify HTTPS is working
curl -I https://api.genreport.com/health
# Should return 200 OK
```

---

### Step 5: Monitoring and Logging (15 minutes)

**5.1 Configure CloudWatch**

```bash
# Run monitoring setup playbook
ansible-playbook -i inventory/production playbooks/07-monitoring.yml \
  --extra-vars "environment=production"

# Creates:
# - CloudWatch log groups
# - CloudWatch metrics
# - CloudWatch alarms (CPU, memory, disk, errors)
# - SNS topic for alerts

# Verify log groups
aws logs describe-log-groups \
  --log-group-name-prefix /genreport/prod \
  --region ap-east-1
```

**5.2 Configure Alarms**

```bash
# Create critical alarms
aws cloudwatch put-metric-alarm \
  --alarm-name genreport-prod-high-error-rate \
  --alarm-description "Alert on high error rate" \
  --metric-name 5XXError \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:ap-east-1:123456789012:genreport-alerts \
  --region ap-east-1

# Create more alarms for:
# - Database CPU > 80%
# - Disk space < 20%
# - Memory usage > 90%
# - API latency > 2 seconds
```

---

### Step 6: Backup Configuration (10 minutes)

**6.1 Configure Automated Backups**

```bash
# Copy backup script to production
scp scripts/backup_automation.py ec2-user@backup-server:/opt/genreport/

# SSH to backup server
ssh ec2-user@backup-server

# Set up cron jobs
sudo crontab -e -u genreport

# Add these lines:
# Database backup - 02:00 UTC daily
0 2 * * * /opt/genreport/backup_automation.py --operation backup --type database >> /var/log/genreport/backup.log 2>&1

# File backup - 03:00 UTC daily
0 3 * * * /opt/genreport/backup_automation.py --operation backup --type files --source-path /data/encrypted >> /var/log/genreport/backup.log 2>&1

# Cleanup old backups - 04:00 UTC daily
0 4 * * * /opt/genreport/backup_automation.py --operation cleanup --retention-days 30 >> /var/log/genreport/backup.log 2>&1
```

**6.2 Test Backup**

```bash
# Run manual backup to test
/opt/genreport/backup_automation.py --operation backup --type all

# Verify backups created
/opt/genreport/backup_automation.py --operation list
```

---

### Step 7: Security Hardening (15 minutes)

**7.1 Security Group Review**

```bash
# Review all security groups
ansible-playbook -i inventory/production playbooks/08-security-hardening.yml \
  --extra-vars "environment=production"

# Verifies:
# - Database only accessible from app servers
# - App servers only accessible via load balancer
# - SSH only from bastion host
# - No public access to sensitive resources
```

**7.2 Enable Additional Security Features**

```bash
# Enable AWS GuardDuty
aws guardduty create-detector --enable --region ap-east-1

# Enable AWS Security Hub
aws securityhub enable-security-hub --region ap-east-1

# Enable VPC Flow Logs
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids <VPC_ID> \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpc/genreport-prod \
  --region ap-east-1

# Enable CloudTrail (if not already enabled)
aws cloudtrail create-trail \
  --name genreport-prod-trail \
  --s3-bucket-name genreport-cloudtrail-logs \
  --is-multi-region-trail \
  --region ap-east-1
```

---

### Step 8: Post-Deployment Verification (20 minutes)

**8.1 Health Checks**

```bash
# API health check
curl https://api.genreport.com/health
# Expected: {"status": "healthy", "database": "connected", "redis": "connected"}

# Database health
curl https://api.genreport.com/api/health/db
# Expected: {"status": "healthy", "latency_ms": 10}

# Redis health
curl https://api.genreport.com/api/health/redis
# Expected: {"status": "healthy", "latency_ms": 2}

# Celery health
curl https://api.genreport.com/api/health/celery
# Expected: {"status": "healthy", "workers": 2, "active_tasks": 0}
```

**8.2 Functional Testing**

```bash
# User registration
curl -X POST https://api.genreport.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "company_name": "Test Company"
  }'

# Login
TOKEN=$(curl -X POST https://api.genreport.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPassword123!"}' \
  | jq -r .access_token)

# Create project
curl -X POST https://api.genreport.com/api/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Audit 2024",
    "client_name": "Test Client Ltd",
    "jurisdiction": "HK",
    "accounting_standard": "HKFRS"
  }'
```

**8.3 Performance Testing**

```bash
# Run load test (using Apache Bench)
ab -n 1000 -c 10 https://api.genreport.com/health

# Expected results:
# - Requests per second: > 100
# - Mean response time: < 100ms
# - No failed requests

# Monitor during load test
watch -n 1 'aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=app/genreport-prod-alb/xxx \
  --statistics Average \
  --start-time $(date -u -d "5 minutes ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --region ap-east-1'
```

---

### Step 9: Rollback Plan (Documentation)

**9.1 Application Rollback**

```bash
# If deployment fails, rollback to previous version

# Option 1: Auto Scaling Group rollback
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name genreport-prod-asg \
  --preferences '{"MinHealthyPercentage": 90}' \
  --desired-configuration '{
    "LaunchTemplate": {
      "LaunchTemplateName": "genreport-prod",
      "Version": "$Previous"
    }
  }' \
  --region ap-east-1

# Option 2: Ansible rollback
ansible-playbook -i inventory/production playbooks/rollback.yml \
  --extra-vars "environment=production target_version=v0.9.0"
```

**9.2 Database Rollback**

```bash
# If migrations fail, rollback to previous migration

# SSH to bastion
ssh ec2-user@bastion.genreport.com

# Rollback one migration
alembic downgrade -1

# Or rollback to specific revision
alembic downgrade <revision_id>

# Verify database state
alembic current
psql $DATABASE_URL -c "\dt"
```

---

## Post-Deployment Checklist

### Immediate (Day 1)

- [ ] Verify all health checks passing
- [ ] Confirm DNS resolution working
- [ ] Test HTTPS certificate validity
- [ ] Verify backups created successfully
- [ ] Check CloudWatch logs for errors
- [ ] Test user registration and login
- [ ] Test file upload functionality
- [ ] Verify Celery workers processing jobs
- [ ] Confirm email notifications working

### First Week

- [ ] Monitor error rates and alerts
- [ ] Review CloudWatch metrics daily
- [ ] Test disaster recovery procedures
- [ ] Conduct backup restoration test
- [ ] Review security scan results
- [ ] Monitor API latency and throughput
- [ ] Check database performance metrics
- [ ] Review application logs for anomalies

### First Month

- [ ] Complete penetration testing
- [ ] Conduct load testing with realistic traffic
- [ ] Review and optimize database queries
- [ ] Implement additional monitoring
- [ ] Begin ISO 27001/SOC 2 observation period
- [ ] Conduct security audit
- [ ] Review and update documentation
- [ ] Train support team on operations

---

## Troubleshooting

### Database Connection Issues

```bash
# Check database status
aws rds describe-db-instances \
  --db-instance-identifier genreport-prod \
  --query 'DBInstances[0].DBInstanceStatus' \
  --region ap-east-1

# Check security group rules
aws ec2 describe-security-groups \
  --group-ids <DB_SECURITY_GROUP_ID> \
  --region ap-east-1

# Test connectivity from app server
psql -h $DB_ENDPOINT -U genreport_prod -d genreport -c "SELECT 1"
```

### Application Not Starting

```bash
# Check application logs
ssh ec2-user@<APP_SERVER_IP>
sudo journalctl -u genreport-api -n 100 --no-pager

# Check environment variables
sudo systemctl show genreport-api | grep Environment

# Check secrets access
aws secretsmanager get-secret-value \
  --secret-id genreport/database/prod \
  --region ap-east-1
```

### Load Balancer Health Check Failing

```bash
# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn <TARGET_GROUP_ARN> \
  --region ap-east-1

# Check application health endpoint
curl http://<INSTANCE_PRIVATE_IP>:8000/health

# Review ALB access logs
aws s3 cp s3://genreport-logs/alb-logs/latest.log - | grep "health"
```

---

## Monitoring and Alerts

### Key Metrics to Monitor

| Metric | Threshold | Action |
|--------|-----------|--------|
| API Error Rate (5XX) | > 1% | PagerDuty alert |
| API Latency (p95) | > 2 seconds | Email alert |
| Database CPU | > 80% | Scale up or optimize |
| Database Connections | > 90 of max | Scale up |
| Memory Usage | > 90% | Scale up ASG |
| Disk Usage | > 80% | Add storage |

### Alert Contacts

- **Critical (P0):** PagerDuty → On-call engineer
- **High (P1):** Email + Slack → DevOps team
- **Medium (P2):** Slack only → DevOps team
- **Low (P3):** Daily digest → Engineering team

---

## Maintenance Windows

### Scheduled Maintenance

- **Day:** Sunday
- **Time:** 02:00-06:00 UTC (off-peak)
- **Frequency:** Monthly (first Sunday)
- **Activities:**
  - Security patching
  - Database maintenance
  - Infrastructure updates

### Notification Process

1. Announce maintenance 7 days in advance
2. Send reminder 24 hours before
3. Update status page during maintenance
4. Send completion notification

---

## Conclusion

This deployment guide provides a comprehensive, step-by-step process for deploying GenReport to production. Follow each step carefully and verify completion before proceeding to the next step.

**Estimated Total Deployment Time:** 2-3 hours

**Post-Deployment Monitoring:** 24/7 for first week

**Next Steps:**
1. Complete production launch checklist
2. Begin user onboarding
3. Start compliance observation period
4. Monitor and optimize performance

---

**Document Version:** 1.0
**Last Updated:** 2025-10-21
**Maintained By:** DevOps Team
**Review Schedule:** Quarterly or after major changes
