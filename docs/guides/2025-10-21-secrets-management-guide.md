# Secrets Management Guide
**Date:** 2025-10-21
**Sprint:** 6 Phase 3
**Purpose:** Guide for managing secrets using AWS Secrets Manager

---

## Overview

This guide covers the AWS Secrets Manager integration for GenReport, including secret storage, retrieval, rotation, and best practices.

**SECURITY PRINCIPLE:** Never store secrets in code, environment variables (in production), or version control.

---

## Architecture

### Secrets Storage

```
AWS Secrets Manager (ap-east-1)
├── genreport/database/prod          # Production database credentials
├── genreport/database/staging       # Staging database credentials
├── genreport/database/dev           # Development database credentials
├── genreport/encryption/master-key  # Master encryption key
├── genreport/encryption/field-encryption  # Field-level encryption keys
└── genreport/jwt/secret             # JWT signing secret
```

### Secret Structure

**Database Credentials:**
```json
{
  "username": "genreport_user",
  "password": "secure_generated_password_32_chars",
  "host": "genreport-db.xxx.rds.amazonaws.com",
  "port": "5432",
  "database": "genreport",
  "rotated_at": "2025-10-21T10:30:00Z"
}
```

**Encryption Keys:**
```json
{
  "key": "base64_encoded_encryption_key",
  "rotated_at": "2025-10-21T10:30:00Z",
  "previous_key": "base64_encoded_previous_key",
  "expiry_date": null
}
```

**JWT Secret:**
```json
{
  "secret_key": "url_safe_secret_64_chars",
  "algorithm": "HS256",
  "rotated_at": "2025-10-21T10:30:00Z"
}
```

---

## Usage

### Basic Secret Retrieval

```python
from genreport.core.security.secrets_manager import get_secrets_manager

# Initialize Secrets Manager
sm = get_secrets_manager(region_name='ap-east-1')

# Get database credentials
db_creds = sm.get_secret('genreport/database/prod')
print(db_creds['username'])  # genreport_user
print(db_creds['password'])  # secure_generated_password...
print(db_creds['host'])      # genreport-db.xxx.rds.amazonaws.com
```

### Convenience Functions

```python
from genreport.core.security.secrets_manager import (
    get_database_credentials,
    get_encryption_key,
    get_jwt_secret
)

# Get database credentials
db_creds = get_database_credentials('prod')
DATABASE_URL = (
    f"postgresql://{db_creds['username']}:{db_creds['password']}"
    f"@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
)

# Get encryption key
encryption_key = get_encryption_key('master-key')

# Get JWT secret
jwt_config = get_jwt_secret()
SECRET_KEY = jwt_config['secret_key']
ALGORITHM = jwt_config['algorithm']
```

### Application Integration

**FastAPI settings.py:**
```python
from pydantic_settings import BaseSettings
from genreport.core.security.secrets_manager import (
    get_database_credentials,
    get_jwt_secret
)

class Settings(BaseSettings):
    # Database
    @property
    def DATABASE_URL(self) -> str:
        """Get database URL from Secrets Manager"""
        db_creds = get_database_credentials('prod')
        return (
            f"postgresql://{db_creds['username']}:{db_creds['password']}"
            f"@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
        )

    # JWT
    @property
    def JWT_SECRET_KEY(self) -> str:
        """Get JWT secret from Secrets Manager"""
        jwt_config = get_jwt_secret()
        return jwt_config['secret_key']

    @property
    def JWT_ALGORITHM(self) -> str:
        """Get JWT algorithm from Secrets Manager"""
        jwt_config = get_jwt_secret()
        return jwt_config['algorithm']

settings = Settings()
```

---

## Local Development

For local development without AWS, the Secrets Manager automatically falls back to environment variables.

### Setup Local Environment

Create `.env` file:
```bash
# Database
GENREPORT_DATABASE_DEV_USERNAME=postgres
GENREPORT_DATABASE_DEV_PASSWORD=postgres
GENREPORT_DATABASE_DEV_HOST=localhost
GENREPORT_DATABASE_DEV_PORT=5432
GENREPORT_DATABASE_DEV_DATABASE=genreport_dev

# Encryption (development only - DO NOT use in production)
GENREPORT_ENCRYPTION_MASTER_KEY_KEY=dev-placeholder-key-32-chars-min

# JWT
GENREPORT_JWT_SECRET_SECRET_KEY=dev-jwt-secret-DO-NOT-USE-IN-PRODUCTION
GENREPORT_JWT_SECRET_ALGORITHM=HS256
```

### Force Local Mode

```python
from genreport.core.security.secrets_manager import get_secrets_manager

# Force local mode (reads from environment variables)
sm = get_secrets_manager(use_local=True)
db_creds = sm.get_secret('genreport/database/dev')
```

---

## Secret Creation

### Create Database Secret

```bash
# Using AWS CLI
aws secretsmanager create-secret \
  --name genreport/database/prod \
  --description "Production database credentials" \
  --secret-string '{
    "username": "genreport_user",
    "password": "$(openssl rand -base64 32)",
    "host": "genreport-db.xxx.rds.amazonaws.com",
    "port": "5432",
    "database": "genreport"
  }' \
  --region ap-east-1
```

### Create Encryption Key Secret

```python
from cryptography.fernet import Fernet
import json
import boto3

# Generate encryption key
key = Fernet.generate_key()

# Store in Secrets Manager
client = boto3.client('secretsmanager', region_name='ap-east-1')
client.create_secret(
    Name='genreport/encryption/master-key',
    Description='Master encryption key',
    SecretString=json.dumps({
        'key': key.decode('utf-8'),
        'rotated_at': datetime.utcnow().isoformat()
    })
)
```

### Create JWT Secret

```bash
# Generate secure random secret
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")

# Store in Secrets Manager
aws secretsmanager create-secret \
  --name genreport/jwt/secret \
  --description "JWT signing secret" \
  --secret-string "{
    \"secret_key\": \"$JWT_SECRET\",
    \"algorithm\": \"HS256\"
  }" \
  --region ap-east-1
```

---

## Secret Rotation

### Automatic Rotation Schedule

| Secret Type | Rotation Frequency | Impact |
|-------------|-------------------|--------|
| Database Password | Every 90 days | Application restart required |
| Encryption Key | Every 180 days | Re-encryption job required |
| JWT Secret | Every 365 days | All users must re-authenticate |

### Manual Rotation

#### Rotate Database Password

```bash
# Dry run (simulate without changes)
./scripts/rotate_secrets.py \
  --secret-type database \
  --environment prod \
  --dry-run

# Actual rotation
./scripts/rotate_secrets.py \
  --secret-type database \
  --environment prod
```

**Steps Performed:**
1. Generate new secure 32-character password
2. Update secret in AWS Secrets Manager
3. Update PostgreSQL user password
4. Trigger zero-downtime application restart

#### Rotate Encryption Key

```bash
./scripts/rotate_secrets.py \
  --secret-type encryption \
  --dry-run

./scripts/rotate_secrets.py \
  --secret-type encryption
```

**Steps Performed:**
1. Generate new Fernet encryption key
2. Store new key in Secrets Manager (keep old key for rollback)
3. Queue background re-encryption job
4. Old key expires after 30 days

**WARNING:** Encryption key rotation requires re-encrypting all encrypted data. This is a long-running background operation.

#### Rotate JWT Secret

```bash
./scripts/rotate_secrets.py \
  --secret-type jwt
```

**Steps Performed:**
1. Generate new JWT signing secret
2. Update secret in Secrets Manager
3. Trigger application restart

**WARNING:** All users will be logged out and must re-authenticate.

#### Rotate All Secrets

```bash
./scripts/rotate_secrets.py \
  --secret-type all \
  --environment prod \
  --dry-run
```

---

## Automated Rotation

### Cron Schedule

Add to crontab on secure admin server:

```bash
# Rotate database password every 90 days (1st of Jan, Apr, Jul, Oct at 2 AM)
0 2 1 1,4,7,10 * /path/to/rotate_secrets.py --secret-type database --environment prod

# Rotate encryption key every 180 days (1st of Jan and Jul at 3 AM)
0 3 1 1,7 * /path/to/rotate_secrets.py --secret-type encryption

# Rotate JWT secret every 365 days (1st of Jan at 4 AM)
0 4 1 1 * /path/to/rotate_secrets.py --secret-type jwt
```

### AWS EventBridge Schedule

**EventBridge Rule (Database Password):**
```json
{
  "ScheduleExpression": "rate(90 days)",
  "State": "ENABLED",
  "Target": {
    "Arn": "arn:aws:lambda:ap-east-1:xxx:function:rotate-db-password",
    "Input": "{\"secret_type\": \"database\", \"environment\": \"prod\"}"
  }
}
```

---

## Security Best Practices

### 1. Never Commit Secrets

**BAD:**
```python
DATABASE_PASSWORD = "my_secret_password"  # ❌ NEVER DO THIS
```

**GOOD:**
```python
from genreport.core.security.secrets_manager import get_database_credentials

db_creds = get_database_credentials('prod')  # ✅ Retrieve at runtime
DATABASE_PASSWORD = db_creds['password']
```

### 2. Use IAM Roles, Not Access Keys

**For EC2/ECS:**
- Attach IAM role with `secretsmanager:GetSecretValue` permission
- No AWS credentials in code or environment

**IAM Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:ap-east-1:*:secret:genreport/*"
    }
  ]
}
```

### 3. Enable Secret Versioning

Secrets Manager automatically versions secrets on rotation. Keep at least 2 versions:
- Current version (active)
- Previous version (for rollback)

### 4. Audit Secret Access

Enable CloudTrail logging for Secrets Manager API calls:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::SecretsManager::Secret \
  --start-time 2025-10-01 \
  --end-time 2025-10-21
```

### 5. Encrypt Secrets at Rest

Secrets Manager uses AWS KMS for encryption. Use customer-managed KMS keys:

```bash
aws secretsmanager create-secret \
  --name genreport/database/prod \
  --kms-key-id arn:aws:kms:ap-east-1:xxx:key/xxx \
  --secret-string '...'
```

### 6. Implement Secret Expiry

Set expiry dates for temporary secrets:

```python
import boto3
from datetime import datetime, timedelta

client = boto3.client('secretsmanager')

# Set expiry for temporary API key
client.update_secret(
    SecretId='genreport/temp/api-key',
    SecretString='...',
    Description=f'Expires: {(datetime.now() + timedelta(days=7)).isoformat()}'
)
```

---

## Troubleshooting

### Secret Not Found

**Error:** `Secret 'genreport/database/prod' not found`

**Solution:**
1. Verify secret exists:
   ```bash
   aws secretsmanager list-secrets --region ap-east-1 | grep genreport
   ```

2. Check IAM permissions:
   ```bash
   aws secretsmanager get-secret-value \
     --secret-id genreport/database/prod \
     --region ap-east-1
   ```

3. Verify region is correct (secrets are regional)

### Access Denied

**Error:** `User is not authorized to perform: secretsmanager:GetSecretValue`

**Solution:**
1. Attach IAM policy with `secretsmanager:GetSecretValue` permission
2. For EC2/ECS: Attach IAM role to instance/task
3. For local dev: Configure AWS credentials via `aws configure`

### Boto3 Not Installed

**Error:** `boto3 not installed`

**Solution:**
```bash
pip install boto3
```

Or add to `requirements.txt`:
```
boto3>=1.28.0
```

### Local Mode Fallback

If AWS Secrets Manager is unavailable, the system automatically falls back to environment variables.

**Warning in logs:**
```
WARNING - Failed to initialize AWS Secrets Manager: ... Falling back to local mode.
WARNING - Using local environment variables for secret: genreport/database/prod
```

**Solution:**
- For development: This is expected behavior
- For production: Fix AWS credentials or IAM role

---

## Monitoring and Alerting

### CloudWatch Metrics

Monitor secret access patterns:

```bash
# Get secret access count
aws cloudwatch get-metric-statistics \
  --namespace AWS/SecretsManager \
  --metric-name GetSecretValueCount \
  --dimensions Name=SecretId,Value=genreport/database/prod \
  --start-time 2025-10-01T00:00:00Z \
  --end-time 2025-10-21T23:59:59Z \
  --period 86400 \
  --statistics Sum
```

### CloudWatch Alarms

**Alert on Unusual Secret Access:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name genreport-secret-access-spike \
  --alarm-description "Alert on unusual secret access" \
  --metric-name GetSecretValueCount \
  --namespace AWS/SecretsManager \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold
```

### Audit Logging

Review secret access logs regularly:

```python
import boto3

# Get CloudTrail events for Secrets Manager
cloudtrail = boto3.client('cloudtrail')

response = cloudtrail.lookup_events(
    LookupAttributes=[
        {
            'AttributeKey': 'ResourceType',
            'AttributeValue': 'AWS::SecretsManager::Secret'
        }
    ],
    MaxResults=50
)

for event in response['Events']:
    print(f"{event['EventTime']}: {event['EventName']} by {event['Username']}")
```

---

## Cost Optimization

### Secrets Manager Pricing (ap-east-1)

- **Secret storage:** $0.40 per secret per month
- **API calls:** $0.05 per 10,000 API calls

### Minimize Costs

1. **Use caching:** LRU cache reduces API calls
   ```python
   @lru_cache(maxsize=128)  # Already implemented
   def get_secret(self, secret_name: str):
       ...
   ```

2. **Batch secret retrieval:** Get multiple secrets in one call (if possible)

3. **Delete unused secrets:**
   ```bash
   aws secretsmanager delete-secret \
     --secret-id genreport/old/secret \
     --recovery-window-in-days 30
   ```

4. **Use environment variables for non-sensitive config:**
   - Region, log level, feature flags → Environment variables
   - Passwords, keys, tokens → Secrets Manager

---

## Migration from Environment Variables

### Step 1: Identify Secrets

Audit environment variables for sensitive data:
```bash
printenv | grep -E "(PASSWORD|SECRET|KEY|TOKEN|CREDENTIAL)"
```

### Step 2: Create Secrets

For each secret:
```bash
aws secretsmanager create-secret \
  --name genreport/<category>/<secret_name> \
  --secret-string "$SECRET_VALUE" \
  --region ap-east-1
```

### Step 3: Update Code

**Before:**
```python
import os

DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
```

**After:**
```python
from genreport.core.security.secrets_manager import get_database_credentials

db_creds = get_database_credentials('prod')
DATABASE_PASSWORD = db_creds['password']
```

### Step 4: Remove Environment Variables

After verification, remove from:
- `.env` files
- Docker compose
- ECS task definitions
- EC2 user data

### Step 5: Verify

Test application startup and verify secrets are loaded correctly.

---

## Backup and Recovery

### Backup Secrets

```bash
# Export all secrets (for backup)
aws secretsmanager list-secrets --region ap-east-1 \
  | jq -r '.SecretList[].Name' \
  | while read secret; do
      echo "Backing up: $secret"
      aws secretsmanager get-secret-value \
        --secret-id "$secret" \
        --region ap-east-1 \
        | jq '{SecretString: .SecretString}' \
        > "backup-${secret//\//-}.json"
    done
```

**SECURITY:** Encrypt backups and store securely (S3 with KMS encryption).

### Restore Secret

```bash
# Restore from backup
SECRET_NAME="genreport/database/prod"
SECRET_VALUE=$(cat "backup-${SECRET_NAME//\//-}.json" | jq -r '.SecretString')

aws secretsmanager create-secret \
  --name "$SECRET_NAME" \
  --secret-string "$SECRET_VALUE" \
  --region ap-east-1
```

---

## Compliance

### ISO 27001

**A.10.1.1 Key Management:**
- ✅ Secrets stored in AWS Secrets Manager (encrypted at rest)
- ✅ Access controlled via IAM policies
- ✅ Audit logging enabled
- ✅ Regular rotation (90-365 days)

### SOC 2

**CC6.1 Logical and Physical Access:**
- ✅ Secrets access requires IAM authentication
- ✅ All access logged to CloudTrail
- ✅ Principle of least privilege enforced

### GDPR

**Article 32 - Security of Processing:**
- ✅ Secrets encrypted at rest (AWS KMS)
- ✅ Secrets encrypted in transit (TLS)
- ✅ Access controls and audit logs

---

## References

- [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
- [AWS Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [boto3 Secrets Manager Reference](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/secretsmanager.html)

---

**Document Version:** 1.0
**Last Updated:** 2025-10-21
**Maintained By:** Security Team
**Review Frequency:** Quarterly
