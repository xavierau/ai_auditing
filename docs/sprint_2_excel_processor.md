# Sprint 2: Excel Processing Engine
## Hybrid Architecture + Security Implementation (v3.0)

**Duration:** 2.5 weeks (Extended from 2 weeks)  
**Sprint Goal:** Intelligent working paper analysis with security and market-awareness  
**Story Points:** 34 (+3 days for security)  
**Team Size:** 2-3 developers

[← Back to Master Plan](./master_sprint_plan.md)

---

## Overview

Sprint 2 builds the **intelligent Excel processing engine** using two-phase LLM parsing, while maintaining **tenant isolation** and adding **optional market-specific validation**. This sprint focuses on generic parsing logic in `core/` with market-specific extensions in `markets/`.

### Sprint Objectives
✅ Secure Excel file upload with encryption  
✅ Two-phase LLM parsing (coding discovery + contextual analysis)  
✅ Relationship map generation  
✅ Validation with fuzzy matching  
✅ DuckDB integration for querying  
✅ Input sanitization and file validation  
✅ Audit trail for file operations  
✅ Optional market-specific validators

---

## Hybrid Architecture Updates

### Optional Market-Specific Validators

```python
# core/parsing/validation_engine.py
from typing import List, Optional
from abc import ABC, abstractmethod

class Validator(ABC):
    """Base validator interface"""
    @abstractmethod
    def validate(self, data: dict) -> dict:
        """Validate data and return validation result"""
        pass

class ValidationEngine:
    """Generic validation engine with pluggable validators"""
    
    def __init__(self, validators: Optional[List[Validator]] = None):
        self.validators = validators or []
    
    def add_validator(self, validator: Validator):
        """Add a validator to the pipeline"""
        self.validators.append(validator)
    
    def validate(self, data: dict) -> dict:
        """Run all validators"""
        results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        for validator in self.validators:
            result = validator.validate(data)
            
            if not result.get("valid", True):
                results["valid"] = False
                results["errors"].extend(result.get("errors", []))
            
            results["warnings"].extend(result.get("warnings", []))
        
        return results

# markets/hk/validators/hkfrs_validator.py (optional, add later if needed)
from core.parsing.validation_engine import Validator

class HKFRSValidator(Validator):
    """Hong Kong specific validation rules"""
    
    def validate(self, trial_balance: dict) -> dict:
        """Validate HK-specific requirements"""
        errors = []
        warnings = []
        
        # Example: Check for required HK disclosures
        if "company_registration" not in trial_balance.get("metadata", {}):
            warnings.append("Missing Hong Kong company registration number")
        
        # Example: Validate SME-FRS formatting
        if self._is_sme(trial_balance):
            if not self._validate_sme_format(trial_balance):
                errors.append("Trial balance doesn't match SME-FRS format")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _is_sme(self, trial_balance: dict) -> bool:
        """Check if entity qualifies as SME"""
        # Implement SME criteria check
        return trial_balance.get("metadata", {}).get("entity_type") == "SME"
    
    def _validate_sme_format(self, trial_balance: dict) -> bool:
        """Validate SME-FRS specific format"""
        # Implement format validation
        return True
```

### Usage in Upload Endpoint

```python
# api/routers/projects.py
from fastapi import APIRouter, UploadFile, Depends
from core.parsing.validation_engine import ValidationEngine
from markets.hk.config import get_market_config

@router.post("/projects/{project_id}/upload")
async def upload_working_papers(
    project_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload and parse working papers"""
    # Get project to determine jurisdiction
    project = get_project(db, project_id, current_user.tenant_id)
    
    # Get market configuration
    market_config = get_market_config(project.jurisdiction)
    
    # Initialize validation engine
    validator = ValidationEngine()
    
    # Optionally add market-specific validators
    if project.jurisdiction == "HK":
        from markets.hk.validators.hkfrs_validator import HKFRSValidator
        validator.add_validator(HKFRSValidator())
    
    # Parse file (generic core logic)
    parsed_data = await parse_excel(file, validator)
    
    return {"status": "success", "data": parsed_data}
```

---

## Security Enhancements

### 1. Encrypted File Upload/Download

```python
# core/security/file_encryption.py
from cryptography.fernet import Fernet
import base64
import os

class FileEncryptionService:
    """Handles file encryption for uploaded documents"""
    
    def __init__(self, encryption_service):
        self.encryption_service = encryption_service
    
    def encrypt_file(self, file_content: bytes, tenant_id: str) -> bytes:
        """Encrypt file content"""
        cipher = self.encryption_service.get_cipher(tenant_id)
        return cipher.encrypt(file_content)
    
    def decrypt_file(self, encrypted_content: bytes, tenant_id: str) -> bytes:
        """Decrypt file content"""
        cipher = self.encryption_service.get_cipher(tenant_id)
        return cipher.decrypt(encrypted_content)

# api/routers/files.py
from fastapi import APIRouter, UploadFile, Depends, HTTPException
from uuid import uuid4
from core.security.file_encryption import FileEncryptionService
from core.security.tenant_context import get_current_tenant
from core.security.audit_logger import AuditLogger

router = APIRouter()

@router.post("/upload")
async def upload_file(
    file: UploadFile,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant)
):
    """Securely upload and encrypt file"""
    
    # Validate file type
    if not validate_file_type(file):
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # Read file content
    content = await file.read()
    
    # Check file size (50MB limit)
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")
    
    # Encrypt file
    file_encryption = FileEncryptionService(encryption_service)
    encrypted_content = file_encryption.encrypt_file(content, str(tenant_id))
    
    # Generate secure file path
    file_id = uuid4()
    storage_path = f"encrypted/{tenant_id}/{project_id}/{file_id}.enc"
    
    # Save encrypted file
    save_to_storage(storage_path, encrypted_content)
    
    # Store metadata in database
    file_record = FileMetadata(
        tenant_id=tenant_id,
        project_id=project_id,
        original_filename=file.filename,
        storage_path=storage_path,
        file_size=len(content),
        encrypted=True,
        uploaded_by=current_user.id
    )
    db.add(file_record)
    db.commit()
    
    # Audit log
    AuditLogger.log_event(
        db=db,
        event_type="FILE_UPLOAD",
        action="CREATE",
        user_id=current_user.id,
        tenant_id=tenant_id,
        resource_type="file",
        resource_id=file_record.id,
        ip_address=request.client.host,
        details={"filename": file.filename, "size": len(content)}
    )
    
    return {
        "file_id": file_id,
        "filename": file.filename,
        "size": len(content)
    }
```

### 2. Input Sanitization

```python
# core/parsing/excel_converter.py
import pandas as pd
import re
from typing import Any

class SecureExcelParser:
    """Secure Excel parser with sanitization"""
    
    @staticmethod
    def strip_formulas(df: pd.DataFrame) -> pd.DataFrame:
        """Remove Excel formulas to prevent code injection"""
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].apply(
                    lambda x: str(x).replace('=', '').replace('+', '') 
                    if isinstance(x, str) and x.startswith('=') 
                    else x
                )
        return df
    
    @staticmethod
    def sanitize_cell_value(value: Any) -> Any:
        """Sanitize individual cell values"""
        if not isinstance(value, str):
            return value
        
        # Remove potential script injections
        dangerous_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe.*?>',
        ]
        
        for pattern in dangerous_patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        return value
    
    def parse_excel_safe(self, file_path: str) -> dict:
        """Parse Excel file with security checks"""
        try:
            # Read Excel file
            xls = pd.ExcelFile(file_path)
            
            worksheets = {}
            for sheet_name in xls.sheet_names:
                # Read sheet
                df = pd.read_excel(xls, sheet_name=sheet_name)
                
                # Strip formulas
                df = self.strip_formulas(df)
                
                # Sanitize all cells
                for col in df.columns:
                    df[col] = df[col].apply(self.sanitize_cell_value)
                
                worksheets[sheet_name] = df
            
            return {
                "worksheets": worksheets,
                "sheet_names": xls.sheet_names,
                "total_sheets": len(xls.sheet_names)
            }
            
        except Exception as e:
            raise ValueError(f"Failed to parse Excel file: {str(e)}")
```

### 3. File Type Validation

```python
# core/security/file_validation.py
import magic
from fastapi import UploadFile, HTTPException

ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.csv'}
ALLOWED_MIME_TYPES = {
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'text/csv',
    'application/octet-stream'  # Sometimes Excel files report as this
}

def validate_file_type(file: UploadFile) -> bool:
    """Validate file type using both extension and magic bytes"""
    
    # Check extension
    if not any(file.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension. Allowed: {ALLOWED_EXTENSIONS}"
        )
    
    # Check actual content type (magic bytes)
    file.file.seek(0)
    content = file.file.read(1024)
    file.file.seek(0)
    
    mime = magic.from_buffer(content, mime=True)
    
    if mime not in ALLOWED_MIME_TYPES:
        # Additional check for ZIP-based formats (XLSX)
        if not (mime == 'application/zip' and file.filename.endswith('.xlsx')):
            raise HTTPException(
                status_code=400,
                detail=f"File content doesn't match extension. Detected: {mime}"
            )
    
    return True

def check_for_macros(file_path: str) -> bool:
    """Check if Excel file contains macros"""
    import zipfile
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # XLSX files with macros have vbaProject.bin
            if 'xl/vbaProject.bin' in zip_ref.namelist():
                return True
    except:
        pass
    
    return False
```

---

## Core Parsing Logic (Generic)

### Two-Phase LLM Parsing

All parsing logic stays in `core/` and works for any market:

```python
# core/parsing/preliminary_scanner.py
from typing import List, Dict
import dspy

class CodingSystemAnalyzer(dspy.Signature):
    """Analyze worksheet names to discover coding system"""
    worksheet_names: List[str] = dspy.InputField(desc="List of all worksheet names")
    coding_pattern: str = dspy.OutputField(desc="Identified coding pattern")
    code_families: List[Dict] = dspy.OutputField(desc="Grouped code families")
    confidence: float = dspy.OutputField(desc="Confidence score 0-1")

class PreliminaryScanner:
    """Phase 1: Discover coding system and analyze worksheets"""
    
    def __init__(self, model_manager):
        self.model = model_manager
        self.analyzer = dspy.ChainOfThought(CodingSystemAnalyzer)
    
    def analyze_workbook(self, excel_path: str) -> dict:
        """
        Phase 1a: Discover coding system
        Phase 1b: Analyze each worksheet with context
        """
        # Get worksheet names
        sheet_names = self._get_sheet_names(excel_path)
        
        # Phase 1a: Discover coding system (1 API call)
        coding_result = self.analyzer(worksheet_names=sheet_names)
        
        # Phase 1b: Analyze each worksheet with coding context (N API calls)
        worksheet_analyses = []
        for sheet_name in sheet_names:
            analysis = self._analyze_worksheet_with_context(
                sheet_name,
                coding_result.coding_pattern,
                coding_result.code_families
            )
            worksheet_analyses.append(analysis)
        
        return {
            "coding_system": coding_result.coding_pattern,
            "code_families": coding_result.code_families,
            "worksheet_analyses": worksheet_analyses,
            "recommended_sheets": self._select_important_sheets(worksheet_analyses)
        }
    
    def _analyze_worksheet_with_context(self, sheet_name: str, 
                                       coding_pattern: str,
                                       code_families: List[Dict]) -> dict:
        """Phase 1b: Analyze single worksheet with coding context"""
        
        class WorksheetAnalyzer(dspy.Signature):
            sheet_name: str = dspy.InputField()
            coding_pattern: str = dspy.InputField()
            code_families: List[Dict] = dspy.InputField()
            
            is_summary: bool = dspy.OutputField(desc="Is this a summary sheet?")
            is_supporting: bool = dspy.OutputField(desc="Is this a supporting detail?")
            referenced_codes: List[str] = dspy.OutputField(desc="Other codes referenced")
            importance_score: float = dspy.OutputField(desc="Importance 0-1")
        
        analyzer = dspy.ChainOfThought(WorksheetAnalyzer)
        return analyzer(
            sheet_name=sheet_name,
            coding_pattern=coding_pattern,
            code_families=code_families
        )
```

---

## Tenant Isolation in Parsing

```python
# api/routers/parsing.py
from fastapi import APIRouter, Depends, BackgroundTasks
from core.security.tenant_context import get_current_tenant
from core.parsing.preliminary_scanner import PreliminaryScanner

@router.post("/projects/{project_id}/parse")
async def parse_working_papers(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant)
):
    """Parse working papers with tenant isolation"""
    
    # Verify project belongs to tenant
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.tenant_id == tenant_id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get encrypted file
    file_record = get_latest_file(db, project_id, tenant_id)
    
    # Decrypt file
    decrypted_content = decrypt_file(file_record.storage_path, tenant_id)
    
    # Parse in background
    background_tasks.add_task(
        parse_and_store,
        decrypted_content,
        project_id,
        tenant_id
    )
    
    return {"status": "parsing_started", "project_id": project_id}

def parse_and_store(content: bytes, project_id: int, tenant_id: UUID):
    """Background task to parse and store results"""
    from core.security.tenant_context import current_tenant
    
    # Set tenant context for background task
    token = current_tenant.set(tenant_id)
    
    try:
        # Parse Excel
        scanner = PreliminaryScanner(model_manager)
        result = scanner.analyze_workbook(content)
        
        # Store relationship map (automatically includes tenant_id)
        store_relationship_map(project_id, result, tenant_id)
        
        # Audit log
        AuditLogger.log_event(
            db=db,
            event_type="PARSING",
            action="COMPLETE",
            tenant_id=tenant_id,
            resource_type="project",
            resource_id=project_id,
            status="SUCCESS"
        )
    finally:
        current_tenant.reset(token)
```

---

## Testing Strategy

```python
# tests/test_parsing_security.py
import pytest
from uuid import uuid4

def test_tenant_isolation_in_parsing():
    """Ensure parsing respects tenant boundaries"""
    tenant_a = uuid4()
    tenant_b = uuid4()
    
    # Upload file for tenant A
    file_a = upload_file(tenant_id=tenant_a, filename="workbook_a.xlsx")
    
    # Try to access from tenant B
    set_tenant_context(tenant_b)
    
    with pytest.raises(PermissionError):
        parse_file(file_a.id)

def test_file_encryption():
    """Ensure files are encrypted at rest"""
    tenant_id = uuid4()
    
    # Upload file
    file_record = upload_file(tenant_id=tenant_id, content=b"sensitive data")
    
    # Read raw file from storage
    raw_content = read_raw_file(file_record.storage_path)
    
    # Should NOT contain plaintext
    assert b"sensitive data" not in raw_content
    assert file_record.encrypted is True

def test_formula_stripping():
    """Ensure Excel formulas are stripped"""
    parser = SecureExcelParser()
    
    df = pd.DataFrame({
        'A': ['=SUM(B1:B10)', 'normal text', '=HYPERLINK("evil.com")']
    })
    
    sanitized = parser.strip_formulas(df)
    
    # Formulas should be removed
    assert not any(str(x).startswith('=') for x in sanitized['A'])

def test_file_type_validation():
    """Ensure only valid file types accepted"""
    # Valid file
    valid_file = create_upload_file("workbook.xlsx", b"PK...")  # ZIP magic bytes
    assert validate_file_type(valid_file) is True
    
    # Invalid extension
    with pytest.raises(HTTPException):
        invalid_file = create_upload_file("malicious.exe", b"MZ...")
        validate_file_type(invalid_file)
    
    # Mismatched content
    with pytest.raises(HTTPException):
        fake_file = create_upload_file("fake.xlsx", b"This is text")
        validate_file_type(fake_file)
```

---

## Definition of Done

### Sprint 2 is complete when:

#### Core Functionality
- [x] Secure file upload with encryption working
- [x] Two-phase LLM parsing functional
- [x] Relationship map generation complete
- [x] Validation engine with fuzzy matching
- [x] DuckDB integration functional

#### Security
- [x] File encryption at rest implemented
- [x] Input sanitization (formulas, XSS) working
- [x] File type validation (extension + magic bytes)
- [x] Macro detection implemented
- [x] File size limits enforced
- [x] Audit logging for file operations
- [x] Tenant isolation in file storage verified

#### Hybrid Architecture
- [x] Parsing logic in `core/` (generic)
- [x] Optional validators in `markets/hk/` (if needed)
- [x] No hardcoded HK references in core parsing

#### Quality
- [x] 80%+ test coverage
- [x] Security tests pass
- [x] Cost per workbook < $0.15
- [x] Average processing time < 45 seconds
- [x] All unit and integration tests pass

---

## Time Estimates

**Week 1: Core Parsing (40 hours)**
- Secure file upload: 8h
- Two-phase parsing: 12h
- Relationship mapping: 8h
- DuckDB integration: 6h
- Testing: 6h

**Week 2: Security + Validation (40 hours)**
- File encryption: 10h
- Input sanitization: 8h
- File validation: 6h
- Market-aware validation: 4h
- Security testing: 8h
- Documentation: 4h

**Week 2.5: Polish (10 hours)**
- Bug fixes: 4h
- Performance optimization: 3h
- Documentation: 3h

**Total: 90 hours (2.5 weeks, 2-3 developers)**

---

## Next Steps

After Sprint 2, proceed to:

**Sprint 3:** Knowledge Base & RAG System
- KB will be jurisdiction-aware
- Retrieval filtered by project jurisdiction
- Encrypted KB storage

[→ View Sprint 3 Details](./sprint_3_knowledge_base.md)

[← Back to Master Plan](./master_sprint_plan.md)

---

**Document Version:** 3.0 (Hybrid + Security)  
**Last Updated:** 2025-10-17  
**Status:** Ready for Implementation