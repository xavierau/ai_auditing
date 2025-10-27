"""Re-parse Excel file to populate worksheet summary field.

This script deletes existing worksheet analyses and re-runs the preliminary scanner
to populate the new summary field.
"""

import asyncio
import tempfile
import os
import dspy
from uuid import UUID
from genreport.core.database.base import SessionLocal
from genreport.core.database.models import FileMetadata, WorksheetAnalysis, RelationshipMap
from genreport.core.security.file_encryption import FileEncryptionService
from genreport.core.security.encryption import encryption_service
from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

# Get API key from environment
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print('GOOGLE_API_KEY not set!')
    exit(1)

# Configure DSPy
lm = dspy.LM(
    'gemini/gemini-2.5-flash',
    api_key=api_key,
    temperature=0.0,
)
dspy.configure(lm=lm)
print('✅ DSPy configured')

db = SessionLocal()

# Get the file metadata
file_id = UUID('674edfce-1ed3-49b8-b5cf-2f9c350a3196')
file_record = db.query(FileMetadata).filter(FileMetadata.id == file_id).first()

if not file_record:
    print('File not found')
    exit(1)

print(f'Processing file: {file_record.original_filename}')
print(f'Current status: {file_record.parsing_status}')

# Delete existing worksheet analyses and relationship maps
print('Deleting existing worksheet analyses...')
db.query(WorksheetAnalysis).filter(WorksheetAnalysis.file_id == file_id).delete()
db.query(RelationshipMap).filter(RelationshipMap.file_id == file_id).delete()
db.commit()
print('✅ Existing data deleted')

# Decrypt the file
file_encryption = FileEncryptionService(encryption_service)
with open(file_record.storage_path, 'rb') as f:
    encrypted_content = f.read()

decrypted_content = file_encryption.decrypt_file(encrypted_content, str(file_record.tenant_id))

# Save to temporary file
with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
    tmp_file.write(decrypted_content)
    tmp_path = tmp_file.name

try:
    print(f'Running preliminary scanner with async parallelization...')

    # Run preliminary scanner (async with parallelization)
    scanner = PreliminaryScanner()
    result = asyncio.run(scanner.analyze_workbook(tmp_path))

    print(f'✅ Analysis complete!')
    print(f'Total sheets: {result.total_sheets}')
    print(f'Coding pattern: {result.coding_system.coding_pattern}')
    print(f'Recommended sheets: {len(result.recommended_sheets)} - {result.recommended_sheets[:5]}')
    print(f'Worksheet analyses: {len(result.worksheet_analyses)}')

    # Save worksheet analyses to database with summary field
    for analysis in result.worksheet_analyses:
        ws_analysis = WorksheetAnalysis(
            tenant_id=file_record.tenant_id,
            project_id=file_record.project_id,
            file_id=file_record.id,
            worksheet_name=analysis.sheet_name,
            is_summary=analysis.is_summary,
            is_supporting=analysis.is_supporting,
            referenced_codes=analysis.referenced_codes,
            importance_score=analysis.importance_score,
            summary=analysis.summary,  # NOW SAVING THE SUMMARY!
            analysis_metadata=analysis.analysis_metadata,
        )
        db.add(ws_analysis)
        print(f'  - {analysis.sheet_name}: {analysis.summary[:100] if analysis.summary else "No summary"}...')

    # Save relationship map
    relationship_map = RelationshipMap(
        tenant_id=file_record.tenant_id,
        project_id=file_record.project_id,
        file_id=file_record.id,
        coding_system=result.coding_system.coding_pattern,
        code_families=[cf.model_dump() for cf in result.coding_system.code_families],
        relationships={'recommended_sheets': result.recommended_sheets},
        recommended_sheets=result.recommended_sheets,
        confidence_score=result.coding_system.confidence,
    )
    db.add(relationship_map)

    # Update file status
    file_record.parsing_status = 'completed'

    db.commit()
    print('✅ Parsing results saved to database with summary field!')

finally:
    # Clean up temporary file
    os.unlink(tmp_path)
    db.close()
