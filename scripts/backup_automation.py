#!/usr/bin/env python3
"""
Backup Automation Script

Automates database and file backups to AWS S3 and RDS snapshots.
Sprint 6 Phase 4: Disaster Recovery

OPERATIONS: Run this script on a schedule (cron or AWS EventBridge)
to create automated backups following the 3-2-1 backup strategy.

Backup Strategy:
- Database: RDS snapshots (daily, 30-day retention)
- Files: S3 archive with encryption (daily, 30-day retention)
- Cleanup: Automated deletion of old backups
"""

import argparse
import logging
import tarfile
import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackupManager:
    """
    Automated backup management for GenReport system.

    Features:
    - RDS database snapshots
    - S3 encrypted file backups
    - Automated cleanup of old backups
    - Backup verification
    - Cost tracking
    """

    def __init__(
        self,
        backup_bucket: str = 'genreport-backups',
        region_name: str = 'ap-east-1',
        db_instance_id: str = 'genreport-prod',
        retention_days: int = 30,
        dry_run: bool = False
    ):
        """
        Initialize Backup Manager.

        Args:
            backup_bucket: S3 bucket for file backups
            region_name: AWS region
            db_instance_id: RDS instance identifier
            retention_days: Days to retain backups
            dry_run: If True, simulate without making changes
        """
        self.backup_bucket = backup_bucket
        self.region_name = region_name
        self.db_instance_id = db_instance_id
        self.retention_days = retention_days
        self.dry_run = dry_run

        self._s3_client = None
        self._rds_client = None

        if not dry_run:
            try:
                import boto3
                self._s3_client = boto3.client('s3', region_name=region_name)
                self._rds_client = boto3.client('rds', region_name=region_name)
                logger.info(f"AWS clients initialized for region: {region_name}")
            except ImportError:
                logger.error("boto3 not installed. Install with: pip install boto3")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize AWS clients: {str(e)}")
                raise

    def create_database_backup(self) -> Optional[str]:
        """
        Create automated RDS snapshot.

        Returns:
            Snapshot identifier if successful, None otherwise

        Example:
            >>> manager = BackupManager()
            >>> snapshot_id = manager.create_database_backup()
            >>> # Returns: 'genreport-backup-20251021-143000'
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
        snapshot_id = f"genreport-backup-{timestamp}"

        logger.info(f"Creating database snapshot: {snapshot_id}")

        if self.dry_run:
            logger.info(f"DRY RUN: Would create snapshot {snapshot_id}")
            return snapshot_id

        try:
            response = self._rds_client.create_db_snapshot(
                DBSnapshotIdentifier=snapshot_id,
                DBInstanceIdentifier=self.db_instance_id,
                Tags=[
                    {'Key': 'Environment', 'Value': 'production'},
                    {'Key': 'BackupType', 'Value': 'automated'},
                    {'Key': 'Timestamp', 'Value': timestamp},
                    {'Key': 'RetentionDays', 'Value': str(self.retention_days)}
                ]
            )

            logger.info(
                f"Database snapshot created: {snapshot_id} "
                f"(Status: {response['DBSnapshot']['Status']})"
            )

            # Log metadata
            self._log_backup_metadata('database', snapshot_id, {
                'type': 'rds_snapshot',
                'instance': self.db_instance_id,
                'timestamp': timestamp,
                'status': response['DBSnapshot']['Status']
            })

            return snapshot_id

        except self._rds_client.exceptions.DBSnapshotAlreadyExistsFault:
            logger.warning(f"Snapshot already exists: {snapshot_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to create database snapshot: {str(e)}", exc_info=True)
            return None

    def backup_encrypted_files(
        self,
        source_path: str = '/data/encrypted',
        archive_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Backup encrypted file storage to S3.

        Args:
            source_path: Path to encrypted files directory
            archive_name: Custom archive name (default: auto-generated)

        Returns:
            S3 key of uploaded archive if successful

        Example:
            >>> manager = BackupManager()
            >>> s3_key = manager.backup_encrypted_files()
            >>> # Returns: 'files/20251021-143000.tar.gz'
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')

        if archive_name is None:
            archive_name = f"files-backup-{timestamp}.tar.gz"

        archive_path = f"/tmp/{archive_name}"
        s3_key = f"files/{timestamp}.tar.gz"

        logger.info(f"Creating encrypted file backup: {archive_name}")

        if self.dry_run:
            logger.info(f"DRY RUN: Would backup {source_path} to s3://{self.backup_bucket}/{s3_key}")
            return s3_key

        try:
            # Check if source path exists
            if not os.path.exists(source_path):
                logger.warning(f"Source path does not exist: {source_path}")
                return None

            # Create compressed archive
            logger.info(f"Creating tar.gz archive from {source_path}")

            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(source_path, arcname="encrypted")

            # Get archive size
            archive_size = os.path.getsize(archive_path)
            logger.info(f"Archive created: {archive_size / (1024**2):.2f} MB")

            # Upload to S3 with encryption
            logger.info(f"Uploading to S3: s3://{self.backup_bucket}/{s3_key}")

            self._s3_client.upload_file(
                archive_path,
                self.backup_bucket,
                s3_key,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256',
                    'Metadata': {
                        'timestamp': timestamp,
                        'source_path': source_path,
                        'retention_days': str(self.retention_days)
                    }
                }
            )

            logger.info(f"Files backed up to S3: {s3_key}")

            # Clean up local archive
            os.remove(archive_path)
            logger.info(f"Cleaned up temporary archive: {archive_path}")

            # Log metadata
            self._log_backup_metadata('files', s3_key, {
                'type': 's3_archive',
                'bucket': self.backup_bucket,
                'key': s3_key,
                'size_mb': archive_size / (1024**2),
                'timestamp': timestamp
            })

            return s3_key

        except Exception as e:
            logger.error(f"Failed to backup files: {str(e)}", exc_info=True)

            # Clean up failed archive
            if os.path.exists(archive_path):
                os.remove(archive_path)

            return None

    def cleanup_old_backups(self, retention_days: Optional[int] = None) -> Dict[str, int]:
        """
        Delete backups older than retention period.

        Args:
            retention_days: Days to retain (default: use instance setting)

        Returns:
            Dict with counts of deleted backups by type

        Example:
            >>> manager = BackupManager(retention_days=30)
            >>> deleted = manager.cleanup_old_backups()
            >>> # Returns: {'rds_snapshots': 5, 's3_archives': 3}
        """
        if retention_days is None:
            retention_days = self.retention_days

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        logger.info(f"Cleaning up backups older than {retention_days} days (before {cutoff.isoformat()})")

        deleted_counts = {
            'rds_snapshots': 0,
            's3_archives': 0
        }

        if self.dry_run:
            logger.info(f"DRY RUN: Would delete backups before {cutoff.isoformat()}")
            return deleted_counts

        # Clean up RDS snapshots
        try:
            deleted_counts['rds_snapshots'] = self._cleanup_rds_snapshots(cutoff)
        except Exception as e:
            logger.error(f"Failed to cleanup RDS snapshots: {str(e)}", exc_info=True)

        # Clean up S3 archives
        try:
            deleted_counts['s3_archives'] = self._cleanup_s3_archives(cutoff)
        except Exception as e:
            logger.error(f"Failed to cleanup S3 archives: {str(e)}", exc_info=True)

        logger.info(
            f"Cleanup complete: "
            f"{deleted_counts['rds_snapshots']} RDS snapshots, "
            f"{deleted_counts['s3_archives']} S3 archives deleted"
        )

        return deleted_counts

    def _cleanup_rds_snapshots(self, cutoff: datetime) -> int:
        """Delete RDS snapshots older than cutoff date."""
        deleted_count = 0

        try:
            # List all manual snapshots for this instance
            snapshots = self._rds_client.describe_db_snapshots(
                DBInstanceIdentifier=self.db_instance_id,
                SnapshotType='manual'  # Only delete manual snapshots
            )['DBSnapshots']

            for snapshot in snapshots:
                snapshot_id = snapshot['DBSnapshotIdentifier']
                snapshot_time = snapshot['SnapshotCreateTime']

                # Ensure timezone-aware comparison
                if snapshot_time.tzinfo is None:
                    snapshot_time = snapshot_time.replace(tzinfo=timezone.utc)

                # Only delete automated backups (created by this script)
                if snapshot_time < cutoff and 'genreport-backup-' in snapshot_id:
                    logger.info(f"Deleting old RDS snapshot: {snapshot_id} (created {snapshot_time.isoformat()})")

                    self._rds_client.delete_db_snapshot(
                        DBSnapshotIdentifier=snapshot_id
                    )

                    deleted_count += 1
                    logger.info(f"Deleted RDS snapshot: {snapshot_id}")

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up RDS snapshots: {str(e)}")
            raise

    def _cleanup_s3_archives(self, cutoff: datetime) -> int:
        """Delete S3 archives older than cutoff date."""
        deleted_count = 0

        try:
            # List all objects in backup bucket with 'files/' prefix
            response = self._s3_client.list_objects_v2(
                Bucket=self.backup_bucket,
                Prefix='files/'
            )

            for obj in response.get('Contents', []):
                obj_key = obj['Key']
                obj_time = obj['LastModified']

                # Ensure timezone-aware comparison
                if obj_time.tzinfo is None:
                    obj_time = obj_time.replace(tzinfo=timezone.utc)

                if obj_time < cutoff:
                    logger.info(f"Deleting old S3 archive: {obj_key} (created {obj_time.isoformat()})")

                    self._s3_client.delete_object(
                        Bucket=self.backup_bucket,
                        Key=obj_key
                    )

                    deleted_count += 1
                    logger.info(f"Deleted S3 archive: {obj_key}")

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up S3 archives: {str(e)}")
            raise

    def verify_backup(self, backup_type: str, backup_id: str) -> bool:
        """
        Verify backup integrity and availability.

        Args:
            backup_type: 'database' or 'files'
            backup_id: Snapshot ID or S3 key

        Returns:
            True if backup is valid and accessible
        """
        logger.info(f"Verifying {backup_type} backup: {backup_id}")

        if self.dry_run:
            logger.info(f"DRY RUN: Would verify {backup_type} backup {backup_id}")
            return True

        try:
            if backup_type == 'database':
                response = self._rds_client.describe_db_snapshots(
                    DBSnapshotIdentifier=backup_id
                )

                snapshot = response['DBSnapshots'][0]
                status = snapshot['Status']

                logger.info(f"RDS snapshot status: {status}")
                return status == 'available'

            elif backup_type == 'files':
                response = self._s3_client.head_object(
                    Bucket=self.backup_bucket,
                    Key=backup_id
                )

                size_mb = response['ContentLength'] / (1024**2)
                logger.info(f"S3 archive size: {size_mb:.2f} MB")

                return response['ContentLength'] > 0

            else:
                logger.error(f"Unknown backup type: {backup_type}")
                return False

        except Exception as e:
            logger.error(f"Backup verification failed: {str(e)}", exc_info=True)
            return False

    def list_backups(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        List all available backups.

        Returns:
            Dict with 'database' and 'files' backup lists
        """
        backups = {
            'database': [],
            'files': []
        }

        if self.dry_run:
            logger.info("DRY RUN: Would list all backups")
            return backups

        # List RDS snapshots
        try:
            snapshots = self._rds_client.describe_db_snapshots(
                DBInstanceIdentifier=self.db_instance_id,
                SnapshotType='manual'
            )['DBSnapshots']

            for snapshot in snapshots:
                if 'genreport-backup-' in snapshot['DBSnapshotIdentifier']:
                    backups['database'].append({
                        'id': snapshot['DBSnapshotIdentifier'],
                        'created_at': snapshot['SnapshotCreateTime'].isoformat(),
                        'status': snapshot['Status'],
                        'size_gb': snapshot.get('AllocatedStorage', 0)
                    })
        except Exception as e:
            logger.error(f"Failed to list RDS snapshots: {str(e)}")

        # List S3 archives
        try:
            response = self._s3_client.list_objects_v2(
                Bucket=self.backup_bucket,
                Prefix='files/'
            )

            for obj in response.get('Contents', []):
                backups['files'].append({
                    'key': obj['Key'],
                    'created_at': obj['LastModified'].isoformat(),
                    'size_mb': obj['Size'] / (1024**2)
                })
        except Exception as e:
            logger.error(f"Failed to list S3 archives: {str(e)}")

        logger.info(
            f"Found {len(backups['database'])} database backups, "
            f"{len(backups['files'])} file backups"
        )

        return backups

    def _log_backup_metadata(self, backup_type: str, backup_id: str, metadata: dict):
        """Log backup metadata for audit trail."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': backup_type,
            'id': backup_id,
            'metadata': metadata
        }

        logger.info(f"Backup metadata: {json.dumps(log_entry)}")


def main():
    """Main entry point for backup automation script."""
    parser = argparse.ArgumentParser(
        description='Automated backup management for GenReport'
    )
    parser.add_argument(
        '--operation',
        choices=['backup', 'cleanup', 'verify', 'list'],
        required=True,
        help='Backup operation to perform'
    )
    parser.add_argument(
        '--type',
        choices=['database', 'files', 'all'],
        default='all',
        help='Type of backup (for backup/verify operations)'
    )
    parser.add_argument(
        '--backup-id',
        help='Backup ID to verify (snapshot ID or S3 key)'
    )
    parser.add_argument(
        '--retention-days',
        type=int,
        default=30,
        help='Backup retention period in days'
    )
    parser.add_argument(
        '--source-path',
        default='/data/encrypted',
        help='Source path for file backups'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate operations without making changes'
    )

    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("GenReport Backup Automation")
    logger.info("=" * 50)
    logger.info(f"Operation: {args.operation}")
    logger.info(f"Type: {args.type}")
    logger.info(f"Retention: {args.retention_days} days")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 50)

    # Initialize backup manager
    manager = BackupManager(
        retention_days=args.retention_days,
        dry_run=args.dry_run
    )

    success = True

    # Execute operation
    if args.operation == 'backup':
        if args.type in ['database', 'all']:
            snapshot_id = manager.create_database_backup()
            if snapshot_id is None:
                success = False

        if args.type in ['files', 'all']:
            s3_key = manager.backup_encrypted_files(source_path=args.source_path)
            if s3_key is None:
                success = False

    elif args.operation == 'cleanup':
        deleted = manager.cleanup_old_backups()
        logger.info(f"Cleanup results: {deleted}")

    elif args.operation == 'verify':
        if not args.backup_id:
            logger.error("--backup-id required for verify operation")
            success = False
        else:
            valid = manager.verify_backup(args.type, args.backup_id)
            if not valid:
                success = False

    elif args.operation == 'list':
        backups = manager.list_backups()

        print("\n=== Database Backups ===")
        for backup in backups['database']:
            print(f"  {backup['id']}: {backup['created_at']} ({backup['size_gb']} GB) - {backup['status']}")

        print("\n=== File Backups ===")
        for backup in backups['files']:
            print(f"  {backup['key']}: {backup['created_at']} ({backup['size_mb']:.2f} MB)")

    # Exit with appropriate code
    if success:
        logger.info("=" * 50)
        logger.info("Backup operation completed successfully")
        logger.info("=" * 50)
        exit(0)
    else:
        logger.error("=" * 50)
        logger.error("Backup operation failed")
        logger.error("=" * 50)
        exit(1)


if __name__ == '__main__':
    main()
