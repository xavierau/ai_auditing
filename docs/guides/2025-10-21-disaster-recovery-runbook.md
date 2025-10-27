# Disaster Recovery Runbook
**Version:** 1.0
**Last Updated:** 2025-10-21
**Prepared By:** GenReport Operations Team
**Classification:** CONFIDENTIAL

---

## Executive Summary

This runbook provides step-by-step procedures for recovering the GenReport audit platform from various disaster scenarios. The system is designed for:

- **RTO (Recovery Time Objective):** 2-4 hours depending on scenario
- **RPO (Recovery Point Objective):** 1 hour (based on backup frequency)
- **Multi-region capability:** Primary (Hong Kong ap-east-1), Future (Singapore, Australia)

---

## Table of Contents

1. [Emergency Contact Information](#emergency-contact-information)
2. [Backup Infrastructure](#backup-infrastructure)
3. [Recovery Scenarios](#recovery-scenarios)
   - [Scenario 1: Database Corruption](#scenario-1-database-corruption)
   - [Scenario 2: Complete Server Failure](#scenario-2-complete-server-failure)
   - [Scenario 3: Security Breach](#scenario-3-security-breach)
4. [Recovery Procedures](#recovery-procedures)
5. [Verification Checklist](#verification-checklist)
6. [Testing Schedule](#testing-schedule)
7. [Post-Recovery Actions](#post-recovery-actions)

---

## Emergency Contact Information

### On-Call Rotation

| Role | Primary | Backup | Escalation |
|------|---------|--------|------------|
| Technical Lead | [Name] +852-XXXX-XXXX | [Name] +852-XXXX-XXXX | CTO |
| DevOps Engineer | [Name] +852-XXXX-XXXX | [Name] +852-XXXX-XXXX | Technical Lead |
| Database Admin | [Name] +852-XXXX-XXXX | [Name] +852-XXXX-XXXX | DevOps |
| Security Officer | [Name] +852-XXXX-XXXX | [Name] +852-XXXX-XXXX | CISO |

### External Contacts

- **AWS Support:** Premium Support (24/7)
- **Security Incident Response:** [Third-party SOC provider]
- **Legal/Compliance:** [Law firm contact]
- **Communication Team:** [PR contact for user notifications]

---

## Backup Infrastructure

### Backup Schedule

| Component | Frequency | Retention | Location |
|-----------|-----------|-----------|----------|
| Database (RDS) | Daily 02:00 UTC | 30 days | RDS Snapshots (ap-east-1) |
| Encrypted Files | Daily 03:00 UTC | 30 days | S3 (s3://genreport-backups) |
| Configuration | Daily 04:00 UTC | 90 days | S3 + Git repository |
| Secrets | On rotation | Versioned | AWS Secrets Manager |

### Backup Validation

**Daily Automated Checks:**
- Snapshot creation success
- Archive integrity (checksum)
- Backup size within expected range
- S3 encryption verification

**Monthly Manual Verification:**
- Test database restore to staging
- Test file restore to temporary directory
- Verify backup restoration time (RTO compliance)

---

## Recovery Scenarios

### Scenario 1: Database Corruption

**Symptoms:**
- Database queries failing with integrity errors
- Application errors related to data inconsistency
- Replication lag or failures
- Audit log corruption detected

**Impact:** HIGH
**RTO:** 2 hours
**RPO:** 1 hour
**Probability:** Low (Monthly)

#### Detection

```bash
# Check database health
aws rds describe-db-instances \
  --db-instance-identifier genreport-prod \
  --query 'DBInstances[0].[DBInstanceStatus,StorageEncrypted]'

# Check recent errors
aws rds describe-events \
  --source-identifier genreport-prod \
  --duration 60
```

#### Recovery Steps

**Step 1: Stop Application (5 minutes)**

```bash
# SSH to application server
ssh ec2-user@genreport-api-prod.example.com

# Stop API service
sudo systemctl stop genreport-api

# Verify service stopped
sudo systemctl status genreport-api

# Stop Celery workers
sudo systemctl stop genreport-celery-worker
sudo systemctl stop genreport-celery-beat
```

**Step 2: Identify Most Recent Clean Backup (10 minutes)**

```bash
# List all available snapshots sorted by creation time
aws rds describe-db-snapshots \
  --db-instance-identifier genreport-prod \
  --snapshot-type manual \
  --query 'sort_by(DBSnapshots, &SnapshotCreateTime)[-5:].[DBSnapshotIdentifier,SnapshotCreateTime,Status]' \
  --output table

# Verify snapshot integrity
SNAPSHOT_ID="genreport-backup-20251021-020000"

aws rds describe-db-snapshots \
  --db-snapshot-identifier $SNAPSHOT_ID \
  --query 'DBSnapshots[0].[Status,PercentProgress,Encrypted]'
```

**Step 3: Restore from Snapshot (60-90 minutes)**

```bash
# Rename current (corrupted) instance for rollback safety
aws rds modify-db-instance \
  --db-instance-identifier genreport-prod \
  --new-db-instance-identifier genreport-prod-corrupted \
  --apply-immediately

# Wait for rename to complete (5-10 minutes)
aws rds wait db-instance-available \
  --db-instance-identifier genreport-prod-corrupted

# Restore from snapshot with same identifier
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier genreport-prod \
  --db-snapshot-identifier $SNAPSHOT_ID \
  --db-subnet-group-name genreport-db-subnet-group \
  --vpc-security-group-ids sg-XXXXXXXXX \
  --publicly-accessible false \
  --multi-az true \
  --storage-encrypted true \
  --kms-key-id arn:aws:kms:ap-east-1:XXXX:key/YYYY

# Wait for restoration to complete (30-60 minutes)
aws rds wait db-instance-available \
  --db-instance-identifier genreport-prod

# Get new endpoint
NEW_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier genreport-prod \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

echo "New database endpoint: $NEW_ENDPOINT"
```

**Step 4: Update Connection Strings (5 minutes)**

```bash
# Update database credentials in Secrets Manager (if endpoint changed)
aws secretsmanager update-secret \
  --secret-id genreport/database/prod \
  --secret-string "{
    \"username\": \"genreport_prod\",
    \"password\": \"$(aws secretsmanager get-secret-value --secret-id genreport/database/prod --query SecretString --output text | jq -r .password)\",
    \"host\": \"$NEW_ENDPOINT\",
    \"port\": \"5432\",
    \"database\": \"genreport\"
  }"

# Verify secret updated
aws secretsmanager get-secret-value \
  --secret-id genreport/database/prod \
  --query SecretString \
  --output text | jq .
```

**Step 5: Verify Data Integrity (10 minutes)**

```bash
# Connect to restored database
psql -h $NEW_ENDPOINT -U genreport_prod -d genreport

-- Check table counts
SELECT 'tenants' AS table_name, COUNT(*) FROM tenants
UNION ALL
SELECT 'projects', COUNT(*) FROM projects
UNION ALL
SELECT 'uploads', COUNT(*) FROM uploads
UNION ALL
SELECT 'reports', COUNT(*) FROM reports;

-- Verify most recent data
SELECT MAX(created_at) FROM projects;
SELECT MAX(created_at) FROM reports;

-- Check for corruption
SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Exit
\q
```

**Step 6: Restart Application (10 minutes)**

```bash
# Restart API service
sudo systemctl start genreport-api

# Verify service started
sudo systemctl status genreport-api

# Check application logs
sudo journalctl -u genreport-api -n 100 --no-pager

# Restart Celery workers
sudo systemctl start genreport-celery-worker
sudo systemctl start genreport-celery-beat

# Verify worker health
celery -A genreport inspect ping
celery -A genreport inspect active
```

**Step 7: Verify Application Functionality (10 minutes)**

```bash
# Health check
curl -f https://api.genreport.com/health || echo "Health check failed"

# Test authentication
curl -X POST https://api.genreport.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test_password"}'

# Test project retrieval
TOKEN="<access_token>"
curl -H "Authorization: Bearer $TOKEN" \
  https://api.genreport.com/api/projects

# Monitor error logs
tail -f /var/log/genreport/api.log
```

**Total Time:** ~2 hours
**Data Loss:** Up to 1 hour (since last backup)

---

### Scenario 2: Complete Server Failure

**Symptoms:**
- Server unresponsive (no SSH, no HTTP)
- AWS console shows instance failure
- Hardware degradation detected
- Availability zone outage

**Impact:** CRITICAL
**RTO:** 4 hours
**RPO:** 1 hour
**Probability:** Very Low (Annually)

#### Recovery Steps

**Step 1: Assess Failure Scope (15 minutes)**

```bash
# Check instance status
aws ec2 describe-instance-status \
  --instance-ids i-XXXXXXXXX \
  --query 'InstanceStatuses[0].[InstanceStatus.Status,SystemStatus.Status]'

# Check availability zone health
aws health describe-events \
  --filter eventTypeCategories=issue \
  --query 'events[?region==`ap-east-1`]'

# Check auto-scaling group status
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names genreport-api-asg \
  --query 'AutoScalingGroups[0].[DesiredCapacity,MinSize,MaxSize,Instances[].HealthStatus]'
```

**Step 2: Provision New Server (Manual or IaC) (30 minutes)**

**Option A: Using Auto Scaling (Automatic)**

```bash
# Terminate failed instance (ASG will replace)
aws ec2 terminate-instances --instance-ids i-XXXXXXXXX

# Wait for new instance (ASG automatically launches replacement)
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names genreport-api-asg \
  --query 'AutoScalingGroups[0].Instances[?LifecycleState==`InService`]'
```

**Option B: Using Ansible (Manual deployment)**

```bash
# Provision new EC2 instance
cd /deploy/genreport-infra

ansible-playbook -i inventory/production provision.yml \
  --extra-vars "environment=production" \
  --tags "ec2"

# Wait for instance to be ready
# Note the new instance ID from output
```

**Step 3: Restore Database (see Scenario 1, Steps 2-4) (90 minutes)**

Follow database restoration steps from Scenario 1 if database is also affected.

**Step 4: Restore Encrypted Files from S3 (20 minutes)**

```bash
# SSH to new server
NEW_SERVER_IP=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=genreport-api-prod" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

ssh ec2-user@$NEW_SERVER_IP

# Create encrypted files directory
sudo mkdir -p /data/encrypted
sudo chown genreport:genreport /data/encrypted

# Download and extract latest backup
LATEST_BACKUP=$(aws s3 ls s3://genreport-backups/files/ \
  | sort | tail -n 1 | awk '{print $4}')

echo "Restoring from: $LATEST_BACKUP"

aws s3 cp "s3://genreport-backups/files/$LATEST_BACKUP" /tmp/backup.tar.gz

# Extract archive
sudo tar -xzf /tmp/backup.tar.gz -C /data/
sudo chown -R genreport:genreport /data/encrypted

# Verify extraction
sudo du -sh /data/encrypted
ls -la /data/encrypted/ | head -20

# Clean up
rm /tmp/backup.tar.gz
```

**Step 5: Deploy Application (30 minutes)**

```bash
# Deploy application code
cd /deploy/genreport-infra

ansible-playbook -i inventory/production deploy.yml \
  --extra-vars "environment=production version=v1.0.0" \
  --tags "application"

# Verify deployment
ssh ec2-user@$NEW_SERVER_IP "systemctl status genreport-api"
ssh ec2-user@$NEW_SERVER_IP "docker ps" # if using Docker
```

**Step 6: Update DNS (if IP changed) (30 minutes)**

```bash
# Get new Elastic IP or ALB DNS
NEW_ENDPOINT=$(aws ec2 describe-addresses \
  --filters "Name=tag:Name,Values=genreport-api-prod-eip" \
  --query 'Addresses[0].PublicIp' \
  --output text)

# Update Route53 DNS record
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch "{
    \"Changes\": [{
      \"Action\": \"UPSERT\",
      \"ResourceRecordSet\": {
        \"Name\": \"api.genreport.com\",
        \"Type\": \"A\",
        \"TTL\": 300,
        \"ResourceRecords\": [{\"Value\": \"$NEW_ENDPOINT\"}]
      }
    }]
  }"

# Wait for DNS propagation (check TTL)
dig api.genreport.com +short

# Test from multiple locations
curl -I https://api.genreport.com/health
```

**Step 7: Verify All Services (20 minutes)**

```bash
# Check all services
ssh ec2-user@$NEW_SERVER_IP << 'EOF'
  sudo systemctl status genreport-api
  sudo systemctl status genreport-celery-worker
  sudo systemctl status genreport-celery-beat
  sudo systemctl status nginx
  sudo systemctl status redis
EOF

# Verify application health
curl -f https://api.genreport.com/health
curl -f https://api.genreport.com/api/health/db
curl -f https://api.genreport.com/api/health/redis
curl -f https://api.genreport.com/api/health/celery

# Check logs for errors
ssh ec2-user@$NEW_SERVER_IP "sudo tail -100 /var/log/genreport/api.log"
```

**Step 8: Notify Users (15 minutes)**

```bash
# Send status page update
curl -X POST https://status.genreport.com/api/incidents \
  -H "Authorization: Bearer <status_page_token>" \
  -d '{
    "name": "Service Restored",
    "status": "resolved",
    "message": "All services have been restored and are operating normally."
  }'

# Send email notification to affected users
# (Use SendGrid, SES, or internal notification system)
```

**Total Time:** ~4 hours
**Data Loss:** Up to 1 hour (since last backup)

---

### Scenario 3: Security Breach

**Symptoms:**
- Unauthorized access detected in audit logs
- Suspicious database queries
- Unusual file access patterns
- Security alerts from WAF/IDS
- User reports of unauthorized access

**Impact:** CRITICAL
**RTO:** Immediate isolation, 2-4 hours recovery
**RPO:** N/A (security incident)
**Probability:** Low (Quarterly attempts, rare successful breaches)

#### Recovery Steps

**Step 1: Immediate Isolation (5 minutes)**

```bash
# CRITICAL: Isolate affected systems IMMEDIATELY

# Block all incoming traffic via security group
aws ec2 modify-security-group-rules \
  --group-id sg-XXXXXXXXX \
  --security-group-rules "SecurityGroupRuleId=sgr-YYYYYYY,SecurityGroupRule={IpProtocol=-1,CidrIpv4=127.0.0.1/32}"

# Or disable network interface
aws ec2 modify-network-interface-attribute \
  --network-interface-id eni-XXXXXXXXX \
  --no-source-dest-check

# Take snapshot of compromised instance (for forensics)
INSTANCE_ID="i-XXXXXXXXX"
aws ec2 create-snapshot \
  --volume-id $(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId' --output text) \
  --description "Security breach forensic snapshot $(date +%Y%m%d-%H%M%S)" \
  --tag-specifications 'ResourceType=snapshot,Tags=[{Key=Incident,Value=security-breach},{Key=Date,Value='$(date +%Y%m%d)'}]'
```

**Step 2: Activate Incident Response Team (10 minutes)**

```bash
# Send PagerDuty alert
curl -X POST https://api.pagerduty.com/incidents \
  -H 'Authorization: Token token=<PAGERDUTY_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{
    "incident": {
      "type": "incident",
      "title": "SECURITY BREACH DETECTED - GenReport Production",
      "service": {
        "id": "<SERVICE_ID>",
        "type": "service_reference"
      },
      "urgency": "high",
      "body": {
        "type": "incident_body",
        "details": "Security breach detected. System isolated. IR team activated."
      }
    }
  }'

# Notify security officer
# Notify legal team
# Notify compliance officer
```

**Step 3: Rotate All Credentials (30 minutes)**

```bash
# Rotate database password
./scripts/rotate_secrets.py --secret-type database --environment prod

# Rotate encryption keys
./scripts/rotate_secrets.py --secret-type encryption

# Rotate JWT secret (invalidates all sessions)
./scripts/rotate_secrets.py --secret-type jwt

# Rotate AWS access keys
aws iam list-access-keys --user-name genreport-prod
aws iam create-access-key --user-name genreport-prod
# Update application configuration with new keys
aws iam delete-access-key --user-name genreport-prod --access-key-id <OLD_KEY>

# Force password reset for all users
psql -h <DB_HOST> -U genreport_prod -d genreport << 'SQL'
UPDATE users SET password_reset_required = true, session_token = NULL;
SQL
```

**Step 4: Review Audit Logs (60 minutes)**

```bash
# Export audit logs for analysis
aws logs filter-log-events \
  --log-group-name /genreport/api \
  --start-time $(date -d '7 days ago' +%s)000 \
  --filter-pattern '[timestamp, request_id, level=ERROR, ...]' \
  > /tmp/audit-logs-$(date +%Y%m%d).json

# Analyze database audit logs
psql -h <DB_HOST> -U genreport_prod -d genreport << 'SQL'
-- Suspicious queries in last 7 days
SELECT event_type, action, user_id, tenant_id, resource_type, created_at, ip_address
FROM audit_logs
WHERE created_at > NOW() - INTERVAL '7 days'
  AND (
    event_type = 'UNAUTHORIZED_ACCESS'
    OR event_type = 'CROSS_TENANT_ATTEMPT'
    OR event_type = 'SECURITY_VIOLATION'
  )
ORDER BY created_at DESC
LIMIT 1000;

-- Unusual data access patterns
SELECT user_id, tenant_id, COUNT(*) as access_count
FROM audit_logs
WHERE created_at > NOW() - INTERVAL '7 days'
  AND event_type = 'DATA_ACCESS'
GROUP BY user_id, tenant_id
HAVING COUNT(*) > 1000
ORDER BY access_count DESC;
SQL

# Check file access logs
grep -r "SECURITY_VIOLATION\|UNAUTHORIZED" /var/log/genreport/ > /tmp/security-violations.log
```

**Step 5: Identify Vulnerability and Patch (90 minutes)**

```bash
# Run comprehensive security scan
./scripts/security-check.sh > /tmp/security-scan-$(date +%Y%m%d).txt

# Check for unpatched vulnerabilities
pip-audit --requirement requirements.txt --format json > /tmp/vuln-report.json

# Review recent code changes
git log --since="7 days ago" --oneline --all > /tmp/recent-commits.txt

# Apply security patches
pip install --upgrade <vulnerable_package>

# If application vulnerability:
# 1. Review code change that introduced vulnerability
# 2. Develop and test patch
# 3. Deploy emergency patch (bypass normal release process if critical)

# Deploy patch
ansible-playbook -i inventory/production deploy.yml \
  --extra-vars "environment=production version=v1.0.1-security-patch" \
  --tags "application,security"
```

**Step 6: Restore from Known-Good Backup (if data compromised) (120 minutes)**

```bash
# If data integrity compromised, restore from pre-breach backup

# Identify last known-good backup (before breach)
BREACH_TIME="2025-10-21T14:30:00Z"  # Adjust based on investigation

# Find backup before breach
aws rds describe-db-snapshots \
  --db-instance-identifier genreport-prod \
  --query "DBSnapshots[?SnapshotCreateTime<'$BREACH_TIME'] | sort_by(@, &SnapshotCreateTime)[-1].[DBSnapshotIdentifier,SnapshotCreateTime]"

# Restore from pre-breach snapshot
# (Follow Scenario 1 database restoration steps)

# Restore files from pre-breach backup
# (Follow Scenario 2 file restoration steps)
```

**Step 7: Notify Affected Parties (Compliance Requirement) (60 minutes)**

```bash
# Identify affected tenants/users
psql -h <DB_HOST> -U genreport_prod -d genreport << 'SQL'
-- Tenants with potential data exposure
SELECT DISTINCT t.id, t.company_name, t.contact_email
FROM tenants t
JOIN audit_logs al ON al.tenant_id = t.id
WHERE al.event_type = 'UNAUTHORIZED_ACCESS'
  AND al.created_at > NOW() - INTERVAL '7 days';
SQL

# GDPR Article 33 - Notify data protection authority within 72 hours
# PDPA (HK) - Notify Privacy Commissioner for data breaches

# Draft breach notification
cat > /tmp/breach-notification.txt << 'EOF'
Subject: Security Incident Notification - GenReport

Dear [Customer],

We are writing to inform you of a security incident that may have affected your data...

[Details of breach]
[Data potentially affected]
[Actions taken]
[Recommendations for customers]
[Contact information]

Sincerely,
GenReport Security Team
EOF

# Send notifications (automated via email service)
# python scripts/send_breach_notifications.py --template /tmp/breach-notification.txt
```

**Step 8: Create Incident Report (120 minutes)**

```markdown
# Security Incident Report

## Incident Summary
- **Date/Time:** 2025-10-21 14:30 UTC
- **Severity:** Critical
- **Status:** Contained and Resolved
- **Impact:** [X] tenants, [Y] users potentially affected

## Timeline
- 14:30 - Breach detected via WAF alert
- 14:35 - System isolated
- 14:45 - IR team activated
- 15:00 - Credentials rotated
- 16:30 - Vulnerability identified and patched
- 18:00 - System restored with patch
- 19:00 - Notifications sent

## Root Cause
[Detailed analysis of how breach occurred]

## Affected Systems
- Application servers: [list]
- Databases: [list]
- Data affected: [description]

## Actions Taken
1. Immediate isolation
2. Credential rotation
3. Audit log analysis
4. Vulnerability patching
5. System restoration
6. User notification

## Lessons Learned
[What went well, what could be improved]

## Prevention Measures
1. [Action item 1]
2. [Action item 2]
...

## Follow-up Actions
- [ ] Complete forensic analysis
- [ ] Update security policies
- [ ] Additional security training
- [ ] Third-party security audit
- [ ] Review access controls
```

**Total Time:** 4-8 hours (investigation continues)
**Data Loss:** Depends on breach scope
**Compliance:** GDPR/PDPA notification within 72 hours

---

## Verification Checklist

After any recovery, verify the following:

### System Health
- [ ] All application services running
- [ ] Database queries responding normally
- [ ] Redis cache operational
- [ ] Celery workers processing jobs
- [ ] Nginx serving requests

### Data Integrity
- [ ] Table row counts match expectations
- [ ] Most recent data timestamp within expected range
- [ ] No database corruption errors
- [ ] Audit logs continuous (no gaps)

### Security
- [ ] All secrets rotated (if security incident)
- [ ] SSL/TLS certificates valid
- [ ] Security groups configured correctly
- [ ] WAF rules active
- [ ] Audit logging enabled

### Functionality
- [ ] User authentication working
- [ ] File upload working
- [ ] Report generation working
- [ ] Email notifications sending
- [ ] API endpoints responding

### Monitoring
- [ ] CloudWatch metrics reporting
- [ ] Log aggregation working
- [ ] Alerts configured and firing correctly
- [ ] Status page updated

### Compliance
- [ ] Data residency requirements met (HK data in ap-east-1)
- [ ] Encryption at rest enabled
- [ ] Audit logging comprehensive
- [ ] Backup verification complete

---

## Testing Schedule

### Monthly Backup Restoration Test
**First Sunday of each month, 01:00-04:00 UTC**

```bash
# Test database restore to staging
LATEST_SNAPSHOT=$(aws rds describe-db-snapshots \
  --db-instance-identifier genreport-prod \
  --query 'sort_by(DBSnapshots, &SnapshotCreateTime)[-1].DBSnapshotIdentifier' \
  --output text)

aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier genreport-staging-restore-test \
  --db-snapshot-identifier $LATEST_SNAPSHOT

# Verify restoration time
# Delete test instance after verification
```

### Quarterly Full DR Drill
**Last Saturday of quarter, 08:00-16:00 UTC**

**Drill Objectives:**
1. Test complete server failure recovery
2. Verify team response time
3. Practice communication procedures
4. Identify gaps in runbook

**Drill Procedure:**
1. Simulate server failure (terminate staging instance)
2. Execute Scenario 2 recovery steps on staging
3. Time each step
4. Document issues encountered
5. Update runbook based on findings

### Annual Tabletop Exercise
**December, full team participation**

**Exercise Format:**
1. Present realistic disaster scenario
2. Team walks through response procedures
3. Discuss decisions and alternatives
4. Review incident command structure
5. Update contact information and procedures

---

## Post-Recovery Actions

### Immediate (Within 24 hours)
1. **Update status page:** Mark incident as resolved
2. **Notify users:** Send all-clear notification
3. **Document incident:** Create incident report
4. **Review costs:** Calculate recovery costs (AWS, team time)

### Short-term (Within 1 week)
1. **Post-mortem meeting:** Full team review
2. **Update runbook:** Incorporate lessons learned
3. **Fix root cause:** Permanent fix if temporary patch applied
4. **Improve monitoring:** Add alerts to detect similar issues earlier

### Long-term (Within 1 month)
1. **Security audit:** If security-related, engage third-party auditor
2. **Process improvements:** Update DR procedures
3. **Training:** Conduct DR training for team
4. **Compliance reporting:** Update compliance documentation

---

## Appendix A: Key AWS Resources

### Production Infrastructure (ap-east-1)

| Resource Type | Identifier | Purpose |
|---------------|------------|---------|
| RDS Instance | genreport-prod | Primary database |
| S3 Bucket | genreport-backups | Backup storage |
| EC2 Instance | i-XXXXXXXXX | Application server |
| ELB | genreport-prod-alb | Load balancer |
| Route53 Zone | Z1234567890ABC | DNS |
| Security Group | sg-XXXXXXXXX | Network security |
| KMS Key | arn:aws:kms:ap-east-1:XXXX:key/YYYY | Encryption |

---

## Appendix B: Emergency Access Procedures

### Break-Glass Access

If primary authentication is unavailable:

```bash
# Use emergency IAM user (stored in secure physical safe)
aws configure --profile emergency
# Access key: [Retrieved from safe]
# Secret key: [Retrieved from safe]

# Or use AWS Console with root account (MFA required)
# Root credentials stored in: [Secure location]
```

### Database Emergency Access

```bash
# Direct RDS connection (bypassing application)
psql -h genreport-prod.xxx.rds.amazonaws.com \
  -U genreport_admin \  # Emergency admin user
  -d genreport

# Password: Retrieved from AWS Secrets Manager using emergency IAM
```

---

## Appendix C: Runbook Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-21 | Claude Code | Initial version |

---

**END OF RUNBOOK**

**This document is confidential and should be stored securely with access restricted to authorized personnel only.**
