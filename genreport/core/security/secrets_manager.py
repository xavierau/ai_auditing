"""
AWS Secrets Manager Integration

Manages secrets using AWS Secrets Manager with caching and rotation support.
Sprint 6 Phase 3: Secrets Management

SECURITY: Never store secrets in code or environment variables.
All secrets are retrieved from AWS Secrets Manager at runtime.
"""

import json
import logging
from functools import lru_cache
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Manage secrets using AWS Secrets Manager.

    Features:
    - Secure secret retrieval with LRU caching
    - Secret rotation support
    - Audit logging for secret access
    - Graceful degradation for local development
    """

    def __init__(self, region_name: str = 'ap-east-1', use_local: bool = False):
        """
        Initialize Secrets Manager client.

        Args:
            region_name: AWS region (default: ap-east-1 for Hong Kong)
            use_local: If True, use local env vars instead of AWS (for development)
        """
        self.region_name = region_name
        self.use_local = use_local
        self._client = None

        if not use_local:
            try:
                import boto3
                self._client = boto3.client('secretsmanager', region_name=region_name)
                logger.info(f"AWS Secrets Manager initialized for region: {region_name}")
            except ImportError:
                logger.warning(
                    "boto3 not installed. Install with: pip install boto3"
                )
                self.use_local = True
            except Exception as e:
                logger.warning(
                    f"Failed to initialize AWS Secrets Manager: {str(e)}. "
                    "Falling back to local mode."
                )
                self.use_local = True

    @lru_cache(maxsize=128)
    def get_secret(self, secret_name: str) -> Dict[str, Any]:
        """
        Get secret from AWS Secrets Manager (with caching).

        Args:
            secret_name: Name of the secret (e.g., 'genreport/database/prod')

        Returns:
            Dict containing secret key-value pairs

        Raises:
            ValueError: If secret not found or cannot be retrieved

        Example:
            ```python
            sm = SecretsManager()
            db_creds = sm.get_secret('genreport/database/prod')
            # Returns: {'username': '...', 'password': '...', 'host': '...'}
            ```
        """
        if self.use_local:
            return self._get_secret_local(secret_name)

        try:
            response = self._client.get_secret_value(SecretId=secret_name)

            # Parse JSON secret string
            if 'SecretString' in response:
                secret = json.loads(response['SecretString'])
            else:
                # Binary secrets (less common)
                secret = response['SecretBinary']

            logger.info(f"Retrieved secret: {secret_name}")
            return secret

        except self._client.exceptions.ResourceNotFoundException:
            logger.error(f"Secret not found: {secret_name}")
            raise ValueError(f"Secret '{secret_name}' not found in AWS Secrets Manager")

        except self._client.exceptions.InvalidRequestException as e:
            logger.error(f"Invalid request for secret '{secret_name}': {str(e)}")
            raise ValueError(f"Invalid secret request: {str(e)}")

        except self._client.exceptions.InvalidParameterException as e:
            logger.error(f"Invalid parameter for secret '{secret_name}': {str(e)}")
            raise ValueError(f"Invalid secret parameter: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to retrieve secret '{secret_name}': {str(e)}")
            raise ValueError(f"Failed to retrieve secret: {str(e)}")

    def _get_secret_local(self, secret_name: str) -> Dict[str, Any]:
        """
        Get secret from local environment variables (development only).

        Args:
            secret_name: Secret name (converted to env var name)

        Returns:
            Dict with secret values from env vars

        Example:
            For secret 'genreport/database/prod':
            - Reads: GENREPORT_DATABASE_PROD_USERNAME, _PASSWORD, _HOST
        """
        import os

        # Convert secret name to env var prefix
        # 'genreport/database/prod' -> 'GENREPORT_DATABASE_PROD'
        env_prefix = secret_name.replace('/', '_').replace('-', '_').upper()

        logger.warning(
            f"Using local environment variables for secret: {secret_name} "
            f"(prefix: {env_prefix}_*)"
        )

        # Common secret patterns
        secret = {}

        # Database credentials
        if 'database' in secret_name.lower():
            secret['username'] = os.getenv(f"{env_prefix}_USERNAME", "postgres")
            secret['password'] = os.getenv(f"{env_prefix}_PASSWORD", "postgres")
            secret['host'] = os.getenv(f"{env_prefix}_HOST", "localhost")
            secret['port'] = os.getenv(f"{env_prefix}_PORT", "5432")
            secret['database'] = os.getenv(f"{env_prefix}_DATABASE", "genreport")

        # Encryption keys
        elif 'encryption' in secret_name.lower():
            secret['key'] = os.getenv(f"{env_prefix}_KEY", "")
            if not secret['key']:
                logger.warning(
                    f"No encryption key found in env var: {env_prefix}_KEY. "
                    "Using placeholder for development."
                )
                secret['key'] = "development-placeholder-key-DO-NOT-USE-IN-PRODUCTION"

        # JWT secrets
        elif 'jwt' in secret_name.lower():
            secret['secret_key'] = os.getenv(
                f"{env_prefix}_SECRET_KEY",
                "dev-secret-key-DO-NOT-USE-IN-PRODUCTION"
            )
            secret['algorithm'] = os.getenv(f"{env_prefix}_ALGORITHM", "HS256")

        # Generic secret (try to parse JSON)
        else:
            secret_json = os.getenv(secret_name.replace('/', '_').upper())
            if secret_json:
                try:
                    secret = json.loads(secret_json)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON from env var: {secret_name}")
                    secret = {'value': secret_json}

        return secret

    def create_secret(self, secret_name: str, secret_value: Dict[str, Any]) -> bool:
        """
        Create a new secret in AWS Secrets Manager.

        Args:
            secret_name: Name for the secret
            secret_value: Dict with secret data

        Returns:
            True if successful

        Example:
            ```python
            sm = SecretsManager()
            sm.create_secret('genreport/database/prod', {
                'username': 'genreport_user',
                'password': 'secure_generated_password',
                'host': 'genreport-db.xxx.rds.amazonaws.com'
            })
            ```
        """
        if self.use_local:
            logger.warning("Cannot create secrets in local mode")
            return False

        try:
            self._client.create_secret(
                Name=secret_name,
                SecretString=json.dumps(secret_value)
            )

            logger.info(f"Created secret: {secret_name}")
            return True

        except self._client.exceptions.ResourceExistsException:
            logger.warning(f"Secret already exists: {secret_name}")
            return False

        except Exception as e:
            logger.error(f"Failed to create secret '{secret_name}': {str(e)}")
            return False

    def update_secret(self, secret_name: str, new_value: Dict[str, Any]) -> bool:
        """
        Update (rotate) an existing secret.

        Args:
            secret_name: Name of the secret to update
            new_value: New secret value

        Returns:
            True if successful

        Example:
            ```python
            sm = SecretsManager()
            sm.update_secret('genreport/database/prod', {
                'username': 'genreport_user',
                'password': 'new_rotated_password',
                'host': 'genreport-db.xxx.rds.amazonaws.com'
            })
            ```
        """
        if self.use_local:
            logger.warning("Cannot update secrets in local mode")
            return False

        try:
            self._client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(new_value)
            )

            # Clear cache for this secret
            self.get_secret.cache_clear()

            logger.info(f"Updated secret: {secret_name}")
            return True

        except self._client.exceptions.ResourceNotFoundException:
            logger.error(f"Secret not found for update: {secret_name}")
            return False

        except Exception as e:
            logger.error(f"Failed to update secret '{secret_name}': {str(e)}")
            return False

    def delete_secret(
        self,
        secret_name: str,
        recovery_window_days: int = 30
    ) -> bool:
        """
        Delete a secret (with recovery window).

        Args:
            secret_name: Name of secret to delete
            recovery_window_days: Days before permanent deletion (7-30)

        Returns:
            True if successful

        Note:
            Secrets are not immediately deleted. They enter a recovery
            window period during which they can be restored.
        """
        if self.use_local:
            logger.warning("Cannot delete secrets in local mode")
            return False

        try:
            self._client.delete_secret(
                SecretId=secret_name,
                RecoveryWindowInDays=recovery_window_days
            )

            # Clear cache
            self.get_secret.cache_clear()

            logger.info(
                f"Scheduled secret deletion: {secret_name} "
                f"(recovery window: {recovery_window_days} days)"
            )
            return True

        except self._client.exceptions.ResourceNotFoundException:
            logger.error(f"Secret not found for deletion: {secret_name}")
            return False

        except Exception as e:
            logger.error(f"Failed to delete secret '{secret_name}': {str(e)}")
            return False

    def list_secrets(self, prefix: Optional[str] = None) -> list:
        """
        List all secrets (optionally filtered by prefix).

        Args:
            prefix: Optional prefix to filter secrets (e.g., 'genreport/')

        Returns:
            List of secret names

        Example:
            ```python
            sm = SecretsManager()
            secrets = sm.list_secrets(prefix='genreport/')
            # Returns: ['genreport/database/prod', 'genreport/jwt/secret', ...]
            ```
        """
        if self.use_local:
            logger.warning("Cannot list secrets in local mode")
            return []

        try:
            paginator = self._client.get_paginator('list_secrets')
            page_iterator = paginator.paginate()

            secrets = []
            for page in page_iterator:
                for secret in page['SecretList']:
                    name = secret['Name']
                    if prefix is None or name.startswith(prefix):
                        secrets.append(name)

            logger.info(f"Listed {len(secrets)} secrets (prefix: {prefix})")
            return secrets

        except Exception as e:
            logger.error(f"Failed to list secrets: {str(e)}")
            return []


# Singleton instance for application use
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager(
    region_name: str = 'ap-east-1',
    use_local: bool = False
) -> SecretsManager:
    """
    Get singleton Secrets Manager instance.

    Args:
        region_name: AWS region
        use_local: Use local env vars instead of AWS

    Returns:
        SecretsManager instance

    Example:
        ```python
        from genreport.core.security.secrets_manager import get_secrets_manager

        sm = get_secrets_manager()
        db_creds = sm.get_secret('genreport/database/prod')
        ```
    """
    global _secrets_manager

    if _secrets_manager is None:
        _secrets_manager = SecretsManager(
            region_name=region_name,
            use_local=use_local
        )

    return _secrets_manager


# Convenience functions for common secret types

def get_database_credentials(environment: str = 'prod') -> Dict[str, str]:
    """
    Get database credentials from Secrets Manager.

    Args:
        environment: Environment name ('prod', 'staging', 'dev')

    Returns:
        Dict with username, password, host, port, database

    Example:
        ```python
        from genreport.core.security.secrets_manager import get_database_credentials

        db_creds = get_database_credentials('prod')
        DATABASE_URL = (
            f"postgresql://{db_creds['username']}:{db_creds['password']}"
            f"@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
        )
        ```
    """
    sm = get_secrets_manager()
    return sm.get_secret(f'genreport/database/{environment}')


def get_encryption_key(key_type: str = 'master-key') -> str:
    """
    Get encryption key from Secrets Manager.

    Args:
        key_type: Type of key ('master-key', 'field-encryption', etc.)

    Returns:
        Encryption key string

    Example:
        ```python
        from genreport.core.security.secrets_manager import get_encryption_key

        key = get_encryption_key('master-key')
        ```
    """
    sm = get_secrets_manager()
    secret = sm.get_secret(f'genreport/encryption/{key_type}')
    return secret.get('key', '')


def get_jwt_secret() -> Dict[str, str]:
    """
    Get JWT secret from Secrets Manager.

    Returns:
        Dict with secret_key and algorithm

    Example:
        ```python
        from genreport.core.security.secrets_manager import get_jwt_secret

        jwt_config = get_jwt_secret()
        SECRET_KEY = jwt_config['secret_key']
        ALGORITHM = jwt_config['algorithm']
        ```
    """
    sm = get_secrets_manager()
    return sm.get_secret('genreport/jwt/secret')
