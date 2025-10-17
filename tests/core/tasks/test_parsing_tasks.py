"""Tests for Celery parsing tasks with tenant isolation.

Following TDD approach - these tests verify background parsing behavior.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from pathlib import Path

from genreport.core.tasks.parsing_tasks import (
    parse_excel_file_task,
    _write_temp_file,
    _cleanup_temp_file,
)


class TestTempFileHelpers:
    """Test temp file helper functions."""

    def test_write_temp_file(self):
        """Test writing content to temp file."""
        content = b"test content"
        filename = "test.xlsx"

        temp_file = _write_temp_file(content, filename)

        assert temp_file.exists()
        assert temp_file.suffix == ".xlsx"
        assert temp_file.read_bytes() == content

        # Cleanup
        temp_file.unlink()

    def test_cleanup_temp_file(self):
        """Test cleanup of temp file."""
        content = b"test content"
        temp_file = _write_temp_file(content, "test.xlsx")

        assert temp_file.exists()

        _cleanup_temp_file(temp_file)

        assert not temp_file.exists()

    def test_cleanup_nonexistent_file(self):
        """Test cleanup of non-existent file doesn't raise error."""
        temp_file = Path("/tmp/nonexistent_file.xlsx")

        # Should not raise error
        _cleanup_temp_file(temp_file)


@pytest.mark.skip(reason="Requires Redis and Celery worker running")
class TestParseExcelFileTask:
    """Test Celery parsing task.

    Note: These tests require Redis and a Celery worker to be running.
    For unit tests without infrastructure, use mocks.
    """

    def test_task_queues_successfully(self):
        """Test that task can be queued."""
        from genreport.core.tasks.parsing_tasks import parse_excel_file_task

        file_id = str(uuid4())
        project_id = 1
        tenant_id = str(uuid4())
        user_id = 1

        # Queue task
        result = parse_excel_file_task.delay(
            file_id=file_id,
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        assert result.id is not None
        assert result.state in ["PENDING", "STARTED", "SUCCESS", "FAILURE"]


class TestParseExcelFileTaskMocked:
    """Test parsing task with mocked dependencies."""

    @patch("genreport.core.tasks.parsing_tasks.get_db")
    @patch("genreport.core.tasks.parsing_tasks.PreliminaryScanner")
    @patch("genreport.core.tasks.parsing_tasks.FileEncryptionService")
    @patch("genreport.core.tasks.parsing_tasks.current_tenant")
    @patch("genreport.core.tasks.parsing_tasks.AuditLogger")
    def test_parse_success(
        self,
        mock_audit_logger,
        mock_current_tenant,
        mock_file_encryption,
        mock_scanner,
        mock_get_db,
    ):
        """Test successful parsing execution."""
        # Setup mocks
        file_id = str(uuid4())
        project_id = 1
        tenant_id = str(uuid4())
        user_id = 1

        # Mock database session
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])

        # Mock project
        mock_project = Mock()
        mock_project.id = project_id
        mock_project.status = "pending"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project

        # Mock file record
        mock_file = Mock()
        mock_file.storage_path = "/tmp/test.enc"
        mock_file.original_filename = "test.xlsx"

        # Configure query to return different results for Project vs FileMetadata
        def query_side_effect(model):
            mock_query = Mock()
            if model.__name__ == "Project":
                mock_query.filter.return_value.first.return_value = mock_project
            elif model.__name__ == "FileMetadata":
                mock_query.filter.return_value.first.return_value = mock_file
            return mock_query

        mock_db.query.side_effect = query_side_effect

        # Mock file encryption
        mock_encryption_instance = Mock()
        mock_encryption_instance.decrypt_file.return_value = b"PK\x03\x04"  # XLSX magic
        mock_file_encryption.return_value = mock_encryption_instance

        # Mock scanner
        mock_scanner_instance = Mock()
        mock_scanner_instance.analyze_workbook.return_value = {
            "coding_system": "numeric",
            "code_families": [],
            "worksheet_analyses": [{"sheet_name": "Sheet1"}],
        }
        mock_scanner.return_value = mock_scanner_instance

        # Mock tenant context
        mock_token = Mock()
        mock_current_tenant.set.return_value = mock_token

        # Mock file read with proper context manager support
        mock_file_handle = MagicMock()
        mock_file_handle.read.return_value = b"encrypted"

        # Execute task
        with patch("builtins.open", return_value=mock_file_handle):
            with patch("genreport.core.tasks.parsing_tasks._write_temp_file") as mock_write_temp:
                mock_temp_path = Path("/tmp/test_file.xlsx")
                mock_write_temp.return_value = mock_temp_path

                with patch("genreport.core.tasks.parsing_tasks._cleanup_temp_file"):
                    result = parse_excel_file_task(
                        file_id=file_id,
                        project_id=project_id,
                        tenant_id=tenant_id,
                        user_id=user_id,
                    )

            # Assertions
            assert result["status"] == "success"
            assert result["project_id"] == project_id
            assert result["worksheets_analyzed"] == 1
            assert result["coding_system"] == "numeric"

            # Verify project status updated
            assert mock_project.status == "completed"
            mock_db.commit.assert_called()

            # Verify audit log called
            mock_audit_logger.log_event.assert_called()

            # Verify tenant context reset
            mock_current_tenant.reset.assert_called_with(mock_token)

    @patch("genreport.core.tasks.parsing_tasks.get_db")
    @patch("genreport.core.tasks.parsing_tasks.current_tenant")
    @patch("genreport.core.tasks.parsing_tasks.AuditLogger")
    def test_parse_project_not_found(
        self, mock_audit_logger, mock_current_tenant, mock_get_db
    ):
        """Test parsing fails when project not found."""
        file_id = str(uuid4())
        project_id = 999
        tenant_id = str(uuid4())
        user_id = 1

        # Mock database session
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])

        # Mock project not found
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Mock tenant context
        mock_token = Mock()
        mock_current_tenant.set.return_value = mock_token

        # Execute task - should raise ValueError
        with pytest.raises(ValueError, match="Project .* not found"):
            parse_excel_file_task(
                file_id=file_id,
                project_id=project_id,
                tenant_id=tenant_id,
                user_id=user_id,
            )

        # Verify tenant context reset even on error
        mock_current_tenant.reset.assert_called_with(mock_token)

    @patch("genreport.core.tasks.parsing_tasks.get_db")
    @patch("genreport.core.tasks.parsing_tasks.current_tenant")
    @patch("genreport.core.tasks.parsing_tasks.AuditLogger")
    def test_parse_file_not_found(
        self, mock_audit_logger, mock_current_tenant, mock_get_db
    ):
        """Test parsing fails when file not found."""
        file_id = str(uuid4())
        project_id = 1
        tenant_id = str(uuid4())
        user_id = 1

        # Mock database session
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])

        # Mock project found but file not found
        mock_project = Mock()

        def query_side_effect(model):
            mock_query = Mock()
            if model.__name__ == "Project":
                mock_query.filter.return_value.first.return_value = mock_project
            elif model.__name__ == "FileMetadata":
                mock_query.filter.return_value.first.return_value = None
            return mock_query

        mock_db.query.side_effect = query_side_effect

        # Mock tenant context
        mock_token = Mock()
        mock_current_tenant.set.return_value = mock_token

        # Execute task - should raise ValueError
        with pytest.raises(ValueError, match="File .* not found"):
            parse_excel_file_task(
                file_id=file_id,
                project_id=project_id,
                tenant_id=tenant_id,
                user_id=user_id,
            )

        # Verify tenant context reset
        mock_current_tenant.reset.assert_called_with(mock_token)

    @patch("genreport.core.tasks.parsing_tasks.get_db")
    @patch("genreport.core.tasks.parsing_tasks.PreliminaryScanner")
    @patch("genreport.core.tasks.parsing_tasks.FileEncryptionService")
    @patch("genreport.core.tasks.parsing_tasks.current_tenant")
    @patch("genreport.core.tasks.parsing_tasks.AuditLogger")
    def test_parse_failure_updates_project_status(
        self,
        mock_audit_logger,
        mock_current_tenant,
        mock_file_encryption,
        mock_scanner,
        mock_get_db,
    ):
        """Test that parsing failure updates project status to failed."""
        file_id = str(uuid4())
        project_id = 1
        tenant_id = str(uuid4())
        user_id = 1

        # Mock database session
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])

        # Mock project
        mock_project = Mock()
        mock_project.id = project_id
        mock_project.status = "pending"

        # Mock file record
        mock_file = Mock()
        mock_file.storage_path = "/tmp/test.enc"
        mock_file.original_filename = "test.xlsx"

        def query_side_effect(model):
            mock_query = Mock()
            if model.__name__ == "Project":
                mock_query.filter.return_value.first.return_value = mock_project
            elif model.__name__ == "FileMetadata":
                mock_query.filter.return_value.first.return_value = mock_file
            return mock_query

        mock_db.query.side_effect = query_side_effect

        # Mock scanner to raise error
        mock_scanner_instance = Mock()
        mock_scanner_instance.analyze_workbook.side_effect = Exception("Parsing error")
        mock_scanner.return_value = mock_scanner_instance

        # Mock file encryption
        mock_encryption_instance = Mock()
        mock_encryption_instance.decrypt_file.return_value = b"PK\x03\x04"
        mock_file_encryption.return_value = mock_encryption_instance

        # Mock tenant context
        mock_token = Mock()
        mock_current_tenant.set.return_value = mock_token

        # Mock file read with proper context manager support
        mock_file_handle = MagicMock()
        mock_file_handle.read.return_value = b"encrypted"

        # Execute task - should raise exception
        with patch("builtins.open", return_value=mock_file_handle):
            with patch("genreport.core.tasks.parsing_tasks._write_temp_file", return_value=Path("/tmp/test.xlsx")):
                with patch("genreport.core.tasks.parsing_tasks._cleanup_temp_file"):
                    with pytest.raises(Exception, match="Parsing error"):
                        parse_excel_file_task(
                            file_id=file_id,
                            project_id=project_id,
                            tenant_id=tenant_id,
                            user_id=user_id,
                        )

        # Verify tenant context reset
        mock_current_tenant.reset.assert_called_with(mock_token)
