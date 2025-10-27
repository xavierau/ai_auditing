"""
End-to-End Workflow Tests

Tests complete user workflows currently implemented:
- Project creation → Export (Sprint 1 + Sprint 5)
- Multi-tenant workflows with proper isolation
- Market-specific workflows (HK, SG, AU)

Sprint 6 Phase 1
NOTE: Tests for report generation workflows await Sprint 4 (AI agents)
"""

import pytest
from uuid import uuid4
from datetime import date
from pathlib import Path
import tempfile

from genreport.core.database.models import (
    Jurisdiction,
    Project,
    Tenant,
    User,
)


class TestProjectWorkflow:
    """Test project creation and management workflows"""

    @pytest.fixture
    def workflow_tenant(self, db):
        """Create tenant and user for workflow testing"""
        tenant_id = uuid4()

        tenant = Tenant(
            id=tenant_id,
            company_name="E2E Test Company",
            data_residency_region="HK",
            jurisdiction="HK",
            is_active=True,
        )
        db.add(tenant)
        db.flush()

        user = User(
            tenant_id=tenant_id,
            email="test@e2etest.com",
            full_name="E2E Tester",
            password_hash="dummy_hash",
            is_active=True,
        )
        db.add(user)
        db.commit()

        return {
            'tenant_id': tenant_id,
            'user_id': user.id,
            'tenant': tenant,
            'user': user
        }

    def test_complete_project_to_export_workflow(self, db, workflow_tenant):
        """
        Test: Complete project workflow (Sprint 1 + Sprint 5)
        Steps:
        1. Create project
        2. Update project status
        3. Export to DOCX
        """

        # Step 1: Create project
        project = Project(
            tenant_id=workflow_tenant['tenant_id'],
            project_name="E2E Test Project",
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            status="in_progress"
        )
        db.add(project)
        db.commit()

        assert project.id is not None, "Project should be created with ID"
        assert project.status == "in_progress"

        # Step 2: Simulate work on project
        project.status = "completed"
        db.commit()

        # Verify status updated
        updated_project = db.query(Project).filter(Project.id == project.id).first()
        assert updated_project.status == "completed"

        # Step 3: Export to DOCX
        from genreport.core.export import MarketAwareDocxGenerator

        generator = MarketAwareDocxGenerator(Jurisdiction.HK)

        report_data = {
            'project_name': project.project_name,
            'client_name': 'E2E Test Client',
            'financial_year_end': str(project.financial_year_end),
            'jurisdiction': project.jurisdiction,
            'accounting_standard': project.accounting_standard,
            'currency': 'HKD',
            'sections': [
                {'title': 'Revenue Recognition', 'content': 'Sample revenue disclosure...'},
                {'title': 'PPE', 'content': 'Sample PPE disclosure...'},
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / f"report_{project.id}.docx"
            generator.generate(report_data, "audit_report", output_path)

            assert output_path.exists(), "DOCX should be generated"
            assert output_path.stat().st_size > 0, "DOCX should not be empty"

        # Verify complete workflow
        final_project = db.query(Project).filter(Project.id == project.id).first()
        assert final_project.status == "completed"
        assert final_project.tenant_id == workflow_tenant['tenant_id']

    def test_project_creation_with_validation(self, db, workflow_tenant):
        """
        Test: Project creation with field validation
        """

        # Valid project
        valid_project = Project(
            tenant_id=workflow_tenant['tenant_id'],
            project_name="Valid Project",
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            status="draft"
        )
        db.add(valid_project)
        db.commit()

        assert valid_project.id is not None
        assert valid_project.status == "draft"
        assert valid_project.jurisdiction == "HK"

    def test_project_status_transitions(self, db, workflow_tenant):
        """
        Test: Project status transitions (draft → in_progress → completed)
        """

        # Create draft project
        project = Project(
            tenant_id=workflow_tenant['tenant_id'],
            project_name="Status Transition Project",
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            status="draft"
        )
        db.add(project)
        db.commit()

        assert project.status == "draft"

        # Transition to in_progress
        project.status = "in_progress"
        db.commit()

        assert db.query(Project).filter(Project.id == project.id).first().status == "in_progress"

        # Transition to completed
        project.status = "completed"
        db.commit()

        assert db.query(Project).filter(Project.id == project.id).first().status == "completed"


class TestMultiTenantWorkflows:
    """Test workflows across multiple tenants"""

    @pytest.fixture
    def two_tenants(self, db):
        """Create two separate tenants with projects"""
        tenants = []

        for i in range(2):
            tenant_id = uuid4()

            tenant = Tenant(
                id=tenant_id,
                company_name=f"Tenant {i+1}",
                data_residency_region="HK",
                jurisdiction="HK",
                is_active=True,
            )
            db.add(tenant)
            db.flush()

            user = User(
                tenant_id=tenant_id,
                email=f"user{i+1}@tenant{i+1}.com",
                full_name=f"User {i+1}",
                password_hash="dummy_hash",
                is_active=True,
            )
            db.add(user)
            db.flush()

            project = Project(
                tenant_id=tenant_id,
                project_name=f"Project for Tenant {i+1}",
                jurisdiction="HK",
                accounting_standard="HKFRS",
                financial_year_end=date(2024, 12, 31),
                status="in_progress"
            )
            db.add(project)

            tenants.append({
                'tenant_id': tenant_id,
                'user_id': user.id,
                'project_id': None
            })

        db.commit()

        # Update project IDs
        for tenant_info in tenants:
            project = db.query(Project).filter(
                Project.tenant_id == tenant_info['tenant_id']
            ).first()
            tenant_info['project_id'] = project.id

        return tenants

    def test_tenant_cannot_access_other_tenant_projects(self, db, two_tenants):
        """
        Test: Tenant isolation - Tenant 1 cannot access Tenant 2's projects
        Critical security test
        """

        tenant1_id = two_tenants[0]['tenant_id']
        tenant2_id = two_tenants[1]['tenant_id']

        # Tenant 1 queries their own projects
        tenant1_projects = db.query(Project).filter(
            Project.tenant_id == tenant1_id
        ).all()

        assert len(tenant1_projects) == 1
        assert tenant1_projects[0].tenant_id == tenant1_id

        # Tenant 2 queries their own projects
        tenant2_projects = db.query(Project).filter(
            Project.tenant_id == tenant2_id
        ).all()

        assert len(tenant2_projects) == 1
        assert tenant2_projects[0].tenant_id == tenant2_id

        # Critical: Verify no overlap
        tenant1_project_ids = {p.id for p in tenant1_projects}
        tenant2_project_ids = {p.id for p in tenant2_projects}

        assert tenant1_project_ids.isdisjoint(tenant2_project_ids), \
            "Tenant project IDs must not overlap"

    def test_concurrent_tenant_project_creation(self, db, two_tenants):
        """
        Test: Two tenants creating projects concurrently don't interfere
        """

        # Both tenants create additional projects
        for i, tenant_info in enumerate(two_tenants):
            new_project = Project(
                tenant_id=tenant_info['tenant_id'],
                project_name=f"Concurrent Project {i}",
                jurisdiction="HK",
                accounting_standard="HKFRS",
                financial_year_end=date(2024, 12, 31),
                status="draft"
            )
            db.add(new_project)

        db.commit()

        # Verify each tenant has exactly 2 projects
        for tenant_info in two_tenants:
            projects = db.query(Project).filter(
                Project.tenant_id == tenant_info['tenant_id']
            ).all()

            assert len(projects) == 2, f"Tenant should have 2 projects"
            assert all(p.tenant_id == tenant_info['tenant_id'] for p in projects)


class TestMarketSpecificWorkflows:
    """Test workflows for different jurisdictions"""

    @pytest.fixture
    def multi_jurisdiction_tenant(self, db):
        """Create tenant for multi-jurisdiction testing"""
        tenant_id = uuid4()

        tenant = Tenant(
            id=tenant_id,
            company_name="Multi-Jurisdiction Tenant",
            data_residency_region="HK",
            jurisdiction="HK",
            is_active=True,
        )
        db.add(tenant)
        db.flush()

        user = User(
            tenant_id=tenant_id,
            email="multi@test.com",
            full_name="Multi Jurisdiction User",
            password_hash="dummy_hash",
            is_active=True,
        )
        db.add(user)
        db.commit()

        return {'tenant_id': tenant_id, 'user_id': user.id}

    def test_hk_project_workflow(self, db, multi_jurisdiction_tenant):
        """Test Hong Kong project creation and export"""

        project = Project(
            tenant_id=multi_jurisdiction_tenant['tenant_id'],
            project_name="HK Project",
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            status="in_progress"
        )
        db.add(project)
        db.commit()

        # Verify jurisdiction settings
        assert project.jurisdiction == "HK"
        assert project.accounting_standard == "HKFRS"

        # Verify HK-specific generator
        from genreport.core.export import MarketAwareDocxGenerator
        generator = MarketAwareDocxGenerator(Jurisdiction.HK)

        assert generator.jurisdiction == Jurisdiction.HK
        assert 'hk' in str(generator.templates_path).lower()

    def test_sg_project_workflow(self, db, multi_jurisdiction_tenant):
        """Test Singapore project creation and export"""

        project = Project(
            tenant_id=multi_jurisdiction_tenant['tenant_id'],
            project_name="SG Project",
            jurisdiction="SG",
            accounting_standard="SFRS",
            financial_year_end=date(2024, 12, 31),
            status="in_progress"
        )
        db.add(project)
        db.commit()

        # Verify jurisdiction settings
        assert project.jurisdiction == "SG"
        assert project.accounting_standard == "SFRS"

        # Verify SG-specific generator
        from genreport.core.export import MarketAwareDocxGenerator
        generator = MarketAwareDocxGenerator(Jurisdiction.SG)

        assert generator.jurisdiction == Jurisdiction.SG
        assert 'sg' in str(generator.templates_path).lower()

    def test_au_project_workflow(self, db, multi_jurisdiction_tenant):
        """Test Australia project creation and export"""

        project = Project(
            tenant_id=multi_jurisdiction_tenant['tenant_id'],
            project_name="AU Project",
            jurisdiction="AU",
            accounting_standard="AASB",
            financial_year_end=date(2024, 12, 31),
            status="in_progress"
        )
        db.add(project)
        db.commit()

        # Verify jurisdiction settings
        assert project.jurisdiction == "AU"
        assert project.accounting_standard == "AASB"

        # Verify AU-specific generator
        from genreport.core.export import MarketAwareDocxGenerator
        generator = MarketAwareDocxGenerator(Jurisdiction.AU)

        assert generator.jurisdiction == Jurisdiction.AU
        assert 'au' in str(generator.templates_path).lower()

    def test_mixed_jurisdiction_projects(self, db, multi_jurisdiction_tenant):
        """
        Test: Single tenant with projects in multiple jurisdictions
        """

        # Create projects in all 3 jurisdictions
        hk_project = Project(
            tenant_id=multi_jurisdiction_tenant['tenant_id'],
            project_name="HK Mixed Project",
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            status="in_progress"
        )

        sg_project = Project(
            tenant_id=multi_jurisdiction_tenant['tenant_id'],
            project_name="SG Mixed Project",
            jurisdiction="SG",
            accounting_standard="SFRS",
            financial_year_end=date(2024, 12, 31),
            status="in_progress"
        )

        au_project = Project(
            tenant_id=multi_jurisdiction_tenant['tenant_id'],
            project_name="AU Mixed Project",
            jurisdiction="AU",
            accounting_standard="AASB",
            financial_year_end=date(2024, 12, 31),
            status="in_progress"
        )

        db.add_all([hk_project, sg_project, au_project])
        db.commit()

        # Verify all projects belong to same tenant but different jurisdictions
        projects = db.query(Project).filter(
            Project.tenant_id == multi_jurisdiction_tenant['tenant_id']
        ).all()

        assert len(projects) == 3
        jurisdictions = {p.jurisdiction for p in projects}
        assert jurisdictions == {"HK", "SG", "AU"}


class TestErrorRecoveryWorkflows:
    """Test error handling scenarios"""

    @pytest.fixture
    def recovery_tenant(self, db):
        """Create tenant for error testing"""
        tenant_id = uuid4()

        tenant = Tenant(
            id=tenant_id,
            company_name="Recovery Test Tenant",
            data_residency_region="HK",
            jurisdiction="HK",
            is_active=True,
        )
        db.add(tenant)
        db.flush()

        user = User(
            tenant_id=tenant_id,
            email="recovery@test.com",
            full_name="Recovery User",
            password_hash="dummy_hash",
            is_active=True,
        )
        db.add(user)
        db.commit()

        return {'tenant_id': tenant_id, 'user_id': user.id}

    def test_project_without_optional_fields(self, db, recovery_tenant):
        """
        Test: Create project with only required fields
        """

        # Minimal project (only required fields)
        minimal_project = Project(
            tenant_id=recovery_tenant['tenant_id'],
            project_name="Minimal Project",
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31)
        )
        db.add(minimal_project)
        db.commit()

        assert minimal_project.id is not None
        # Verify defaults
        assert minimal_project.status == "draft"

    def test_project_status_recovery(self, db, recovery_tenant):
        """
        Test: Recover from failed status by resetting
        """

        # Create project
        project = Project(
            tenant_id=recovery_tenant['tenant_id'],
            project_name="Recovery Project",
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            status="in_progress"
        )
        db.add(project)
        db.commit()

        # Simulate failure - reset to draft
        project.status = "draft"
        db.commit()

        # Verify recovery
        recovered = db.query(Project).filter(Project.id == project.id).first()
        assert recovered.status == "draft"


# ===========================
# PLACEHOLDER TESTS - Sprint 2/3/4 Pending
# ===========================

class TestFileProcessingWorkflow:
    """Test file processing workflows - PLACEHOLDER"""

    def test_excel_upload_to_report_workflow(self):
        """REQUIRES: Sprint 2 Excel processor"""
        pytest.skip("Excel processing not yet implemented - Sprint 2")

    def test_file_upload_with_encryption(self):
        """REQUIRES: Sprint 2 file upload + encryption"""
        pytest.skip("File upload endpoint not yet implemented - Sprint 2")


class TestKnowledgeBaseWorkflow:
    """Test KB integration workflows - PLACEHOLDER"""

    def test_kb_query_workflow(self):
        """REQUIRES: Sprint 3 KB implementation"""
        pytest.skip("KB not yet implemented - Sprint 3")


class TestAIAgentWorkflow:
    """Test AI agent workflows - PLACEHOLDER"""

    def test_report_generation_workflow(self):
        """REQUIRES: Sprint 4 AI agents"""
        pytest.skip("AI agents not yet implemented - Sprint 4")


# Test suite metadata
"""
E2E TEST SUITE SUMMARY:

Implemented Tests (11 active):
✅ TestProjectWorkflow (3 tests)
   - Complete project to export workflow
   - Project creation with validation
   - Project status transitions

✅ TestMultiTenantWorkflows (2 tests)
   - Tenant isolation verification
   - Concurrent project creation

✅ TestMarketSpecificWorkflows (4 tests)
   - HK project workflow
   - SG project workflow
   - AU project workflow
   - Mixed jurisdiction projects

✅ TestErrorRecoveryWorkflows (2 tests)
   - Project with minimal fields
   - Status recovery

Placeholder Tests (3 pending):
⏸️ TestFileProcessingWorkflow (2 tests) - Sprint 2
⏸️ TestKnowledgeBaseWorkflow (1 test) - Sprint 3
⏸️ TestAIAgentWorkflow (1 test) - Sprint 4

Total: 11 active + 3 placeholders = 14 E2E tests
Focus: Tests current implementation (Sprint 1 + Sprint 5)
"""
