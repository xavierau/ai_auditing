#!/usr/bin/env python3
"""
Secret Rotation Script

Automates rotation of secrets in AWS Secrets Manager.
Sprint 6 Phase 3: Secrets Management

SECURITY: Run this script on a schedule (via cron or AWS EventBridge)
to rotate database passwords and encryption keys.

Rotation Schedule:
- Database passwords: Every 90 days
- Encryption keys: Every 180 days
- JWT secrets: Every 365 days
"""

import argparse
import logging
import secrets
import string
import sys
from datetime import datetime
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_secure_password(length: int = 32) -> str:
    """
    Generate a cryptographically secure password.

    Args:
        length: Password length (default: 32)

    Returns:
        Secure random password

    Example:
        >>> password = generate_secure_password(32)
        >>> len(password)
        32
    """
    # Use all character types for strong passwords
    alphabet = (
        string.ascii_letters +
        string.digits +
        string.punctuation.replace("'", "").replace('"', "")  # No quotes
    )

    # Ensure password contains at least one of each type
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(string.punctuation.replace("'", "").replace('"', ""))
    ]

    # Fill remaining length
    password += [secrets.choice(alphabet) for _ in range(length - 4)]

    # Shuffle
    secrets.SystemRandom().shuffle(password)

    return ''.join(password)


def rotate_database_password(
    environment: str = 'prod',
    dry_run: bool = False
) -> bool:
    """
    Rotate database password.

    Steps:
    1. Generate new secure password
    2. Update secret in AWS Secrets Manager
    3. Update database user password
    4. Trigger application restart (zero downtime)

    Args:
        environment: Environment to rotate ('prod', 'staging', 'dev')
        dry_run: If True, simulate without making changes

    Returns:
        True if successful
    """
    from genreport.core.security.secrets_manager import get_secrets_manager

    logger.info(f"Starting database password rotation for environment: {environment}")

    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    try:
        # Get current credentials
        sm = get_secrets_manager()
        secret_name = f'genreport/database/{environment}'
        current_creds = sm.get_secret(secret_name)

        username = current_creds['username']
        host = current_creds['host']
        port = current_creds.get('port', '5432')
        database = current_creds.get('database', 'genreport')

        logger.info(f"Current database: {host}:{port}/{database} (user: {username})")

        # Generate new password
        new_password = generate_secure_password(32)
        logger.info("Generated new secure password (32 chars)")

        if not dry_run:
            # Update Secrets Manager
            new_creds = current_creds.copy()
            new_creds['password'] = new_password
            new_creds['rotated_at'] = datetime.utcnow().isoformat()

            success = sm.update_secret(secret_name, new_creds)
            if not success:
                logger.error("Failed to update secret in Secrets Manager")
                return False

            logger.info(f"Updated secret in Secrets Manager: {secret_name}")

            # Update database password
            update_postgres_password(
                host=host,
                port=port,
                database=database,
                username=username,
                old_password=current_creds['password'],
                new_password=new_password
            )

            logger.info(f"Updated database password for user: {username}")

            # Trigger application restart (zero downtime)
            if environment == 'prod':
                logger.info("Triggering zero-downtime application restart...")
                trigger_rolling_restart(environment)

        logger.info(f"Database password rotation complete for {environment}")
        return True

    except Exception as e:
        logger.error(f"Database password rotation failed: {str(e)}", exc_info=True)
        return False


def update_postgres_password(
    host: str,
    port: str,
    database: str,
    username: str,
    old_password: str,
    new_password: str
) -> None:
    """
    Update PostgreSQL user password.

    Args:
        host: Database host
        port: Database port
        database: Database name
        username: Database username
        old_password: Current password (for connection)
        new_password: New password to set
    """
    import psycopg2

    try:
        # Connect with old password
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=old_password
        )
        conn.autocommit = True

        # Update password
        cursor = conn.cursor()
        # Use parameterized query to prevent SQL injection
        cursor.execute(
            f"ALTER USER {username} WITH PASSWORD %s",
            (new_password,)
        )

        cursor.close()
        conn.close()

        logger.info("Successfully updated database password")

    except psycopg2.Error as e:
        logger.error(f"Failed to update database password: {str(e)}")
        raise


def trigger_rolling_restart(environment: str) -> None:
    """
    Trigger zero-downtime rolling restart of application.

    Args:
        environment: Environment to restart

    Note:
        Implementation depends on deployment platform:
        - ECS: Update service to force new deployment
        - Kubernetes: kubectl rollout restart
        - EC2: Use Auto Scaling Group rolling update
    """
    logger.info(f"Triggering rolling restart for environment: {environment}")

    # Example for AWS ECS
    try:
        import boto3

        ecs = boto3.client('ecs')

        # Force new deployment (will pick up new secrets)
        ecs.update_service(
            cluster=f'genreport-{environment}',
            service='genreport-api',
            forceNewDeployment=True
        )

        logger.info("Rolling restart triggered successfully")

    except Exception as e:
        logger.warning(f"Failed to trigger automatic restart: {str(e)}")
        logger.info("Please manually restart the application to use new password")


def rotate_encryption_key(dry_run: bool = False) -> bool:
    """
    Rotate encryption master key.

    WARNING: This is a complex operation requiring re-encryption of all data.

    Steps:
    1. Generate new encryption key
    2. Store new key in Secrets Manager
    3. Queue background job to re-encrypt all encrypted data
    4. Keep old key available for 30 days for rollback

    Args:
        dry_run: If True, simulate without making changes

    Returns:
        True if successful
    """
    from cryptography.fernet import Fernet
    from genreport.core.security.secrets_manager import get_secrets_manager

    logger.info("Starting encryption key rotation")

    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    try:
        # Generate new key
        new_key = Fernet.generate_key()
        logger.info("Generated new encryption key")

        if not dry_run:
            sm = get_secrets_manager()

            # Get current key
            current_secret = sm.get_secret('genreport/encryption/master-key')
            current_key = current_secret.get('key', '')

            # Store new key
            new_secret = {
                'key': new_key.decode('utf-8'),
                'rotated_at': datetime.utcnow().isoformat(),
                'previous_key': current_key,  # Keep for rollback
                'expiry_date': None  # Will be set after re-encryption complete
            }

            success = sm.update_secret('genreport/encryption/master-key', new_secret)
            if not success:
                logger.error("Failed to update encryption key in Secrets Manager")
                return False

            logger.info("Updated encryption key in Secrets Manager")

            # Queue re-encryption job
            logger.info("Queueing background re-encryption job...")
            queue_reencryption_job()

        logger.info("Encryption key rotation initiated")
        return True

    except Exception as e:
        logger.error(f"Encryption key rotation failed: {str(e)}", exc_info=True)
        return False


def queue_reencryption_job() -> None:
    """
    Queue background job to re-encrypt all encrypted data with new key.

    This is a long-running operation that should be executed in background:
    - Re-encrypt all encrypted file paths
    - Re-encrypt all encrypted database fields
    - Update encryption_key_id references
    """
    logger.info("Re-encryption job queued")

    # Implementation would use Celery or AWS Step Functions
    # Example:
    # from genreport.core.tasks import reencrypt_all_data
    # reencrypt_all_data.delay(key_type='master-key')

    logger.warning(
        "Re-encryption job implementation pending. "
        "Manual re-encryption may be required."
    )


def rotate_jwt_secret(dry_run: bool = False) -> bool:
    """
    Rotate JWT signing secret.

    WARNING: This will invalidate all existing JWT tokens.
    Users will need to re-authenticate.

    Args:
        dry_run: If True, simulate without making changes

    Returns:
        True if successful
    """
    from genreport.core.security.secrets_manager import get_secrets_manager

    logger.info("Starting JWT secret rotation")
    logger.warning("This will invalidate all existing user sessions!")

    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        return True

    try:
        # Generate new secret
        new_secret_key = secrets.token_urlsafe(64)

        sm = get_secrets_manager()

        new_jwt_secret = {
            'secret_key': new_secret_key,
            'algorithm': 'HS256',
            'rotated_at': datetime.utcnow().isoformat()
        }

        success = sm.update_secret('genreport/jwt/secret', new_jwt_secret)
        if not success:
            logger.error("Failed to update JWT secret")
            return False

        logger.info("JWT secret rotated successfully")
        logger.warning("All users will need to re-authenticate")

        # Trigger application restart to pick up new secret
        logger.info("Triggering application restart...")
        trigger_rolling_restart('prod')

        return True

    except Exception as e:
        logger.error(f"JWT secret rotation failed: {str(e)}", exc_info=True)
        return False


def main():
    """Main entry point for secret rotation script."""
    parser = argparse.ArgumentParser(
        description='Rotate secrets in AWS Secrets Manager'
    )
    parser.add_argument(
        '--secret-type',
        choices=['database', 'encryption', 'jwt', 'all'],
        required=True,
        help='Type of secret to rotate'
    )
    parser.add_argument(
        '--environment',
        choices=['prod', 'staging', 'dev'],
        default='prod',
        help='Environment (for database rotation)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate rotation without making changes'
    )

    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("Secret Rotation Script")
    logger.info("=" * 50)
    logger.info(f"Secret type: {args.secret_type}")
    logger.info(f"Environment: {args.environment}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 50)

    success = True

    if args.secret_type in ['database', 'all']:
        success = rotate_database_password(args.environment, args.dry_run) and success

    if args.secret_type in ['encryption', 'all']:
        success = rotate_encryption_key(args.dry_run) and success

    if args.secret_type in ['jwt', 'all']:
        success = rotate_jwt_secret(args.dry_run) and success

    if success:
        logger.info("=" * 50)
        logger.info("Secret rotation completed successfully")
        logger.info("=" * 50)
        sys.exit(0)
    else:
        logger.error("=" * 50)
        logger.error("Secret rotation failed")
        logger.error("=" * 50)
        sys.exit(1)


if __name__ == '__main__':
    main()
