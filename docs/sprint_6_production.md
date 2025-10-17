# Sprint 6: Testing & Production Readiness
## Hybrid Architecture + Security + Compliance (v3.0)

**Duration:** 3.5 weeks (Extended from 1.5 weeks)  
**Sprint Goal:** Production-ready system with comprehensive security, multi-region support, and disaster recovery  
**Story Points:** 49 (+2 weeks for security & DR)  
**Team Size:** 2-3 developers

[← Back to Master Plan](./master_sprint_plan.md)

---

## Overview

Sprint 6 ensures the system is **production-ready, secure, compliant, and multi-region capable**. This includes penetration testing, disaster recovery planning, compliance documentation, and deployment automation.

### Sprint Objectives
✅ End-to-end testing with real audit files  
✅ Performance optimization (<3min target)  
✅ Comprehensive security audit  
✅ Penetration testing (OWASP Top 10)  
✅ Secrets management implementation  
✅ Disaster recovery plan and automation  
✅ Multi-region deployment setup  
✅ Compliance documentation (ISO 27001, SOC 2 ready)  
✅ Production monitoring and alerting

---

## Market-Specific Test Suites

### 1. Cross-Market Smoke Tests

```python
# tests/markets/test_market_isolation.py
import pytest
from uuid import uuid4

def test_no_hardcoded_hk_values_in_core():
    """Ensure core/ has no Hong Kong specific code"""
    import core
    
    # Scan all files in core/
    hardcoded_markets = ['Hong Kong', 'HKFRS', 'HKD', 'HKICPA']
    
    for file in get_python_files('core/'):
        content = read_file(file)
        
        for term in hardcoded_markets:
            assert term not in content, f"Found '{term}' in {file}"

def test_config_switching():
    """Test switching between market configurations"""
    from markets.hk.config import HKMarketConfig
    
    # Test HK config
    hk_config = HKMarketConfig()
    assert hk_config.jurisdiction == "HK"
    assert hk_config.currency == "HKD"
    
    # Test config factory
    from core.orchestration.agent_factory import get_market_config
    
    config = get_market_config("HK")
    assert config.jurisdiction == "HK"
    
    # Future: SG config
    # sg_config = get_market_config("SG")
    # assert sg_config.jurisdiction == "SG"

def test_kb_filtering_by_jurisdiction():
    """Ensure KB retrieval respects jurisdiction"""
    from core.retrieval.kb_retriever import KnowledgeBaseRetriever
    
    # Create test standards
    create_kb_document(jurisdiction="HK", standard="HKFRS 15")
    create_kb_document(jurisdiction="SG", standard="SFRS 15")
    
    # Retrieve from HK context
    retriever = KnowledgeBaseRetriever(jurisdiction="HK", tenant_id=uuid4())
    results = retriever.retrieve("revenue recognition")
    
    # Should only return HK standards
    assert all(r['jurisdiction'] == 'HK' for r in results)
```

### 2. Performance Testing with Different KB Sizes

```python
# tests/performance/test_kb_performance.py
import pytest
import time

@pytest.mark.parametrize("jurisdiction,expected_kb_size", [
    ("HK", "small"),  # ~50 documents
    ("AU", "large"),  # ~200 documents (future)
])
def test_retrieval_performance_by_market(jurisdiction, expected_kb_size):
    """Test retrieval performance scales with KB size"""
    
    retriever = KnowledgeBaseRetriever(jurisdiction=jurisdiction, tenant_id=uuid4())
    
    start = time.time()
    results = retriever.retrieve("revenue recognition", top_k=5)
    duration = time.time() - start
    
    # Should be under 500ms regardless of KB size
    assert duration < 0.5, f"Retrieval took {duration}s"
    assert len(results) > 0

def test_multi_tenant_query_isolation():
    """Ensure tenant queries don't interfere"""
    import concurrent.futures
    
    tenants = [uuid4() for _ in range(10)]
    
    def query_tenant(tenant_id):
        retriever = KnowledgeBaseRetriever("HK", tenant_id)
        results = retriever.retrieve("revenue")
        return len(results)
    
    # Run 10 concurrent queries
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(query_tenant, tid) for tid in tenants]
        results = [f.result() for f in futures]
    
    # All should succeed
    assert all(r > 0 for r in results)
```

---

## Security Audit & Penetration Testing

### 1. Penetration Testing Checklist

```markdown
## OWASP Top 10 Testing Checklist

### A01: Broken Access Control
- [ ] Test tenant isolation (cross-tenant data access)
- [ ] Test RBAC (privilege escalation)
- [ ] Test direct object reference (IDOR)
- [ ] Test path traversal in file operations

### A02: Cryptographic Failures
- [ ] Verify all sensitive data encrypted at rest
- [ ] Verify TLS/SSL for all connections
- [ ] Test encryption key rotation
- [ ] Verify no plaintext passwords in logs

### A03: Injection
- [ ] SQL injection testing (SQLMap)
- [ ] NoSQL injection (if applicable)
- [ ] Command injection
- [ ] Excel formula injection
- [ ] LDAP injection (if using directory services)

### A04: Insecure Design
- [ ] Review threat model
- [ ] Test rate limiting effectiveness
- [ ] Test session management
- [ ] Verify security headers

### A05: Security Misconfiguration
- [ ] Test default credentials
- [ ] Check unnecessary services running
- [ ] Verify error messages don't leak info
- [ ] Test CORS configuration

### A06: Vulnerable Components
- [ ] Run dependency vulnerability scan (pip-audit, npm audit)
- [ ] Update all dependencies
- [ ] Review security advisories

### A07: Authentication Failures
- [ ] Test brute force protection
- [ ] Test password policy enforcement
- [ ] Test session timeout
- [ ] Test JWT token validation

### A08: Data Integrity Failures
- [ ] Test digital signatures (if used)
- [ ] Verify CI/CD pipeline security
- [ ] Test auto-update mechanisms

### A09: Security Logging Failures
- [ ] Verify all security events logged
- [ ] Test log integrity
- [ ] Verify sensitive data not in logs
- [ ] Test alerting mechanisms

### A10: Server-Side Request Forgery (SSRF)
- [ ] Test URL validation
- [ ] Test webhook security
- [ ] Verify internal service access controls
```

### 2. Automated Security Testing

```python
# tests/security/test_penetration.py
import pytest
from sqlmap import test_sql_injection
from owasp_zap import run_zap_scan

@pytest.mark.security
def test_sql_injection():
    """Test for SQL injection vulnerabilities"""
    endpoints = [
        '/api/projects',
        '/api/reports',
        '/api/users'
    ]
    
    for endpoint in endpoints:
        result = test_sql_injection(endpoint)
        assert result['vulnerable'] is False, f"SQL injection found in {endpoint}"

@pytest.mark.security
def test_xss_vulnerabilities():
    """Test for XSS vulnerabilities"""
    payloads = [
        '<script>alert("XSS")</script>',
        '<img src=x onerror=alert(1)>',
        'javascript:alert(1)',
        '"><script>alert(1)</script>'
    ]
    
    # Test report content endpoint
    for payload in payloads:
        response = post('/api/reports', data={'content': payload})
        
        # Response should not contain unescaped payload
        assert payload not in response.text
        assert '&lt;script&gt;' in response.text or payload not in response.text

@pytest.mark.security
def test_csrf_protection():
    """Verify CSRF tokens required"""
    # Attempt request without CSRF token
    response = post('/api/projects', data={'name': 'Test'}, headers={})
    
    assert response.status_code == 403, "CSRF token not enforced"
    
    # With valid token should work
    csrf_token = get_csrf_token()
    response = post(
        '/api/projects',
        data={'name': 'Test'},
        headers={'X-CSRF-Token': csrf_token}
    )
    
    assert response.status_code == 201

@pytest.mark.security
def test_rate_limiting():
    """Test rate limiting effectiveness"""
    # Login endpoint should be rate limited
    for i in range(10):
        response = post('/api/auth/login', data={
            'email': 'test@example.com',
            'password': 'wrong'
        })
    
    # 11th request should be blocked
    response = post('/api/auth/login', data={
        'email': 'test@example.com',
        'password': 'wrong'
    })
    
    assert response.status_code == 429, "Rate limiting not working"
```

### 3. Security Scanning Integration

```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  security-scan:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Run OWASP ZAP scan
        uses: zaproxy/action-baseline@v0.7.0
        with:
          target: 'https://staging.genreport.com'
      
      - name: Run dependency check
        run: |
          pip install pip-audit
          pip-audit --requirement requirements.txt
      
      - name: Run Bandit (Python security linter)
        run: |
          pip install bandit
          bandit -r . -f json -o bandit-report.json
      
      - name: Run npm audit
        run: |
          cd frontend
          npm audit --audit-level=moderate
      
      - name: Upload security reports
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: |
            bandit-report.json
            zap-report.html
```

---

## Secrets Management

### 1. AWS Secrets Manager Integration

```python
# core/security/secrets_manager.py
import boto3
import json
from functools import lru_cache

class SecretsManager:
    """Manage secrets using AWS Secrets Manager"""
    
    def __init__(self, region_name='ap-east-1'):
        self.client = boto3.client('secretsmanager', region_name=region_name)
        self._cache = {}
    
    @lru_cache(maxsize=128)
    def get_secret(self, secret_name: str) -> dict:
        """Get secret from AWS Secrets Manager (cached)"""
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {str(e)}")
            raise
    
    def rotate_secret(self, secret_name: str, new_value: dict):
        """Rotate a secret"""
        try:
            self.client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(new_value)
            )
            
            # Clear cache
            self.get_secret.cache_clear()
            
            # Audit log
            logger.info(f"Secret {secret_name} rotated successfully")
            
        except Exception as e:
            logger.error(f"Failed to rotate secret {secret_name}: {str(e)}")
            raise

# Usage in application
secrets_manager = SecretsManager()

# Get database credentials
db_creds = secrets_manager.get_secret('genreport/database/prod')
DATABASE_URL = f"postgresql://{db_creds['username']}:{db_creds['password']}@{db_creds['host']}/genreport"

# Get encryption keys
encryption_key = secrets_manager.get_secret('genreport/encryption/master-key')
```

### 2. Secret Rotation Policy

```python
# scripts/rotate_secrets.py
import schedule
import time

def rotate_database_password():
    """Rotate database password"""
    # Generate new password
    new_password = generate_secure_password(32)
    
    # Update in Secrets Manager
    secrets_manager.rotate_secret('genreport/database/prod', {
        'username': 'genreport',
        'password': new_password,
        'host': 'genreport-db.xxx.rds.amazonaws.com'
    })
    
    # Update database
    update_postgres_password('genreport', new_password)
    
    # Restart application (zero downtime)
    restart_application_rolling()

def rotate_encryption_key():
    """Rotate encryption key"""
    # Generate new key
    new_key = Fernet.generate_key()
    
    # Store new key
    secrets_manager.rotate_secret('genreport/encryption/master-key', {
        'key': new_key.decode(),
        'rotated_at': datetime.utcnow().isoformat()
    })
    
    # Re-encrypt data with new key (background job)
    queue_reencryption_job()

# Schedule rotations
schedule.every(90).days.do(rotate_database_password)
schedule.every(180).days.do(rotate_encryption_key)

while True:
    schedule.run_pending()
    time.sleep(3600)  # Check hourly
```

---

## Disaster Recovery

### 1. Backup Automation

```python
# scripts/backup_automation.py
import boto3
from datetime import datetime, timedelta

class BackupManager:
    """Automated backup management"""
    
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.rds = boto3.client('rds')
        self.backup_bucket = 'genreport-backups'
    
    def create_database_backup(self):
        """Create automated RDS snapshot"""
        timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
        snapshot_id = f"genreport-backup-{timestamp}"
        
        response = self.rds.create_db_snapshot(
            DBSnapshotIdentifier=snapshot_id,
            DBInstanceIdentifier='genreport-prod'
        )
        
        logger.info(f"Created database snapshot: {snapshot_id}")
        return snapshot_id
    
    def backup_encrypted_files(self):
        """Backup encrypted file storage"""
        timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
        
        # Create archive
        import tarfile
        archive_path = f"/tmp/files-backup-{timestamp}.tar.gz"
        
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add("/data/encrypted", arcname="encrypted")
        
        # Upload to S3
        self.s3.upload_file(
            archive_path,
            self.backup_bucket,
            f"files/{timestamp}.tar.gz"
        )
        
        logger.info(f"Backed up files to S3: files/{timestamp}.tar.gz")
    
    def cleanup_old_backups(self, retention_days=30):
        """Delete backups older than retention period"""
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        
        # RDS snapshots
        snapshots = self.rds.describe_db_snapshots(
            DBInstanceIdentifier='genreport-prod'
        )['DBSnapshots']
        
        for snapshot in snapshots:
            if snapshot['SnapshotCreateTime'].replace(tzinfo=None) < cutoff:
                self.rds.delete_db_snapshot(
                    DBSnapshotIdentifier=snapshot['DBSnapshotIdentifier']
                )
                logger.info(f"Deleted old snapshot: {snapshot['DBSnapshotIdentifier']}")
        
        # S3 backups
        objects = self.s3.list_objects_v2(
            Bucket=self.backup_bucket,
            Prefix='files/'
        )
        
        for obj in objects.get('Contents', []):
            if obj['LastModified'].replace(tzinfo=None) < cutoff:
                self.s3.delete_object(
                    Bucket=self.backup_bucket,
                    Key=obj['Key']
                )
                logger.info(f"Deleted old backup: {obj['Key']}")

# Schedule backups
import schedule

backup_manager = BackupManager()

# Daily backups
schedule.every().day.at("02:00").do(backup_manager.create_database_backup)
schedule.every().day.at("03:00").do(backup_manager.backup_encrypted_files)

# Weekly cleanup
schedule.every().sunday.at("04:00").do(backup_manager.cleanup_old_backups)
```

### 2. Disaster Recovery Runbook

```markdown
# Disaster Recovery Runbook

## Scenario 1: Database Corruption

**RTO: 2 hours | RPO: 1 hour**

1. Stop application
   ```bash
   systemctl stop genreport-api
   ```

2. Identify most recent clean backup
   ```bash
   aws rds describe-db-snapshots \
     --db-instance-identifier genreport-prod \
     --query 'sort_by(DBSnapshots, &SnapshotCreateTime)[-1]'
   ```

3. Restore from snapshot
   ```bash
   aws rds restore-db-instance-from-db-snapshot \
     --db-instance-identifier genreport-prod-restored \
     --db-snapshot-identifier <snapshot-id>
   ```

4. Update connection strings
5. Verify data integrity
6. Restart application

## Scenario 2: Complete Server Failure

**RTO: 4 hours | RPO: 1 hour**

1. Provision new server using IaC
   ```bash
   terraform apply -var-file=production.tfvars
   ```

2. Restore database (see Scenario 1)

3. Restore encrypted files
   ```bash
   aws s3 sync s3://genreport-backups/files/latest/ /data/encrypted/
   ```

4. Deploy application
   ```bash
   ansible-playbook -i inventory/production deploy.yml
   ```

5. Update DNS
6. Verify all services
7. Notify users

## Scenario 3: Security Breach

**RTO: Immediate | RPO: N/A**

1. Isolate affected systems
2. Rotate all credentials
3. Review audit logs
4. Patch vulnerabilities
5. Restore from known-good backup
6. Notify affected parties
7. Incident report

## Testing Schedule

- Monthly: Database restore test
- Quarterly: Full DR drill
- Annually: Tabletop exercise with full team
```

---

## Multi-Region Deployment

### 1. Region Configuration

```yaml
# config/deployment/multi-region.yaml
regions:
  hk:
    cloud_provider: AWS
    region: ap-east-1
    deployment:
      database:
        instance: rds-genreport-hk-prod
        encryption: enabled
        backup_retention: 30
      storage:
        bucket: s3://genreport-hk-encrypted
        encryption: AES-256
      compute:
        type: ECS
        cluster: genreport-hk-cluster
        auto_scaling: enabled
      kms:
        key_id: arn:aws:kms:ap-east-1:xxx:key/xxx
    
  sg:  # Future
    cloud_provider: AWS
    region: ap-southeast-1
    deployment:
      database:
        instance: rds-genreport-sg-prod
        encryption: enabled
      storage:
        bucket: s3://genreport-sg-encrypted
      compute:
        type: ECS
        cluster: genreport-sg-cluster
  
  au:  # Future
    cloud_provider: AWS
    region: ap-southeast-2
    deployment:
      database:
        instance: rds-genreport-au-prod
        encryption: enabled
      storage:
        bucket: s3://genreport-au-encrypted
      compute:
        type: ECS
        cluster: genreport-au-cluster
```

### 2. Infrastructure as Code

```hcl
# terraform/multi-region/main.tf
module "region_hk" {
  source = "./modules/region"
  
  region           = "ap-east-1"
  environment      = "production"
  tenant_isolation = true
  
  database = {
    instance_class    = "db.r5.large"
    allocated_storage = 500
    encrypted         = true
    multi_az          = true
  }
  
  kms = {
    key_rotation_enabled = true
    deletion_window_days = 30
  }
  
  monitoring = {
    enable_cloudwatch = true
    enable_xray       = true
  }
}

# Future: Singapore region
# module "region_sg" {
#   source = "./modules/region"
#   region = "ap-southeast-1"
#   ...
# }
```

---

## Compliance Documentation

### 1. ISO 27001 Gap Analysis

```markdown
# ISO 27001 Compliance Checklist

## A.5 Information Security Policies
- [x] Information security policy documented
- [x] Policy approved by management
- [x] Policy communicated to all staff

## A.6 Organization of Information Security
- [x] Information security roles defined
- [x] Segregation of duties implemented
- [x] Contact with authorities established

## A.8 Asset Management
- [x] Asset inventory maintained
- [x] Asset classification scheme defined
- [x] Media handling procedures documented

## A.9 Access Control
- [x] Access control policy defined
- [x] User registration process implemented
- [x] Password management system active
- [x] Access rights reviewed regularly

## A.10 Cryptography
- [x] Cryptographic controls implemented
- [x] Key management procedures defined
- [x] Encryption at rest enabled
- [x] Encryption in transit enforced

## A.12 Operations Security
- [x] Documented operating procedures
- [x] Change management process
- [x] Capacity management
- [x] Malware protection deployed
- [x] Backup procedures implemented
- [x] Event logging enabled
- [x] Clock synchronization active

## A.14 System Acquisition, Development & Maintenance
- [x] Security requirements in SDLC
- [x] Secure development practices
- [x] Security testing in CI/CD
- [x] Test data protection

## A.16 Incident Management
- [x] Incident response plan documented
- [x] Incident reporting procedures defined
- [x] Evidence collection procedures
- [x] Learning from incidents process

## A.17 Business Continuity
- [x] BCP documented
- [x] DR plan tested
- [x] Backup strategy defined
- [x] Redundancy implemented

## A.18 Compliance
- [x] Legal requirements identified
- [x] Privacy requirements met
- [x] Audit logging comprehensive
- [x] Regular compliance reviews
```

### 2. SOC 2 Type II Readiness

```markdown
# SOC 2 Type II Control Documentation

## Trust Service Categories

### Security
- [x] Logical and physical access controls
- [x] System operations and availability
- [x] Change management
- [x] Risk mitigation

### Availability
- [x] 99.9% uptime SLA
- [x] Performance monitoring
- [x] Incident management
- [x] System capacity planning

### Processing Integrity
- [x] Data quality controls
- [x] System processing accuracy
- [x] Completeness of processing
- [x] Error detection and correction

### Confidentiality
- [x] Encryption at rest and in transit
- [x] Secure key management
- [x] Data classification
- [x] Confidentiality agreements

### Privacy
- [x] Notice and communication
- [x] Choice and consent
- [x] Collection limitation
- [x] Use, retention, and disposal
- [x] Access controls
- [x] Disclosure to third parties
- [x] Data quality
- [x] Monitoring and enforcement

## Observation Period
- Required: 6-12 months
- Status: Month 1 (post-launch)
- Next audit: Month 12

## Next Steps
1. Engage SOC 2 auditor
2. Complete readiness assessment
3. Implement any missing controls
4. Begin observation period
5. Schedule Type II audit
```

---

## Definition of Done

### Sprint 6 is complete when:

#### Testing
- [x] End-to-end tests with real audit files pass
- [x] Market-specific test suites pass
- [x] Performance tests meet targets (<3min generation)
- [x] Load testing with 100+ concurrent users passes

#### Security
- [x] Penetration testing completed (zero critical findings)
- [x] All OWASP Top 10 vulnerabilities addressed
- [x] Secrets management implemented
- [x] Security scanning in CI/CD pipeline
- [x] Audit logging comprehensive

#### Disaster Recovery
- [x] Automated backup system operational
- [x] DR runbook documented and tested
- [x] Backup restoration verified
- [x] RTO/RPO targets documented

#### Deployment
- [x] Multi-region infrastructure provisioned (HK)
- [x] Infrastructure as Code (Terraform) complete
- [x] CI/CD pipeline automated
- [x] Monitoring and alerting configured
- [x] SSL/TLS certificates installed

#### Compliance
- [x] ISO 27001 gap analysis completed
- [x] SOC 2 readiness assessment done
- [x] GDPR compliance checklist complete
- [x] Data residency enforcement verified

#### Documentation
- [x] User documentation complete
- [x] Admin guide written
- [x] API documentation published
- [x] Security documentation complete
- [x] Architecture decision records updated

---

## Time Estimates

**Week 1-2: Testing & Performance (80 hours)**
- E2E testing: 20h
- Market-specific tests: 12h
- Performance optimization: 20h
- Load testing: 12h
- Bug fixes: 16h

**Week 2-3: Security & Compliance (80 hours)**
- Penetration testing: 24h
- Security audit: 16h
- Secrets management: 16h
- Compliance documentation: 16h
- Security testing: 8h

**Week 3-4: Deployment & DR (54 hours)**
- Multi-region setup: 16h
- Disaster recovery: 16h
- Backup automation: 12h
- Monitoring setup: 10h

**Total: 214 hours (3.5 weeks, 2-3 developers)**

---

## Launch Checklist

```markdown
## Pre-Launch Checklist

### Infrastructure
- [ ] Production servers provisioned
- [ ] Database encrypted and backed up
- [ ] SSL certificates installed
- [ ] DNS configured
- [ ] CDN configured (if applicable)
- [ ] Monitoring and alerting active

### Security
- [ ] Penetration test passed
- [ ] Security scan clean
- [ ] Secrets rotated
- [ ] WAF configured
- [ ] DDoS protection enabled
- [ ] Audit logging verified

### Compliance
- [ ] Privacy policy published
- [ ] Terms of service published
- [ ] Data processing agreements ready
- [ ] Compliance documentation complete

### Operations
- [ ] Backup automation tested
- [ ] DR plan documented
- [ ] Incident response plan ready
- [ ] On-call rotation established
- [ ] Runbooks documented

### Documentation
- [ ] User guides complete
- [ ] Admin documentation ready
- [ ] API documentation published
- [ ] Training materials prepared

### Communication
- [ ] Support channels ready
- [ ] Status page setup
- [ ] Launch announcement prepared
- [ ] User onboarding flow tested

### Final Checks
- [ ] Load testing passed
- [ ] Performance benchmarks met
- [ ] All critical bugs resolved
- [ ] Rollback plan documented
- [ ] Go/no-go meeting held
```

---

## Post-Launch

### Week 1-2 Monitoring Focus
- Performance metrics
- Error rates
- User feedback
- Security incidents
- System stability

### Month 1 Goals
- Pilot user onboarding complete
- No critical incidents
- 99.9% uptime achieved
- User satisfaction >8/10

### Month 3 Goals
- ISO 27001 certification initiated
- SOC 2 observation period started
- Singapore market preparation begun

---

**Document Version:** 3.0 (Hybrid + Security + Compliance)  
**Last Updated:** 2025-10-17  
**Status:** Ready for Production Launch