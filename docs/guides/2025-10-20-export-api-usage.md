# Export API Usage Guide
**Created:** 2025-10-20
**Sprint:** Sprint 5 - Backend DOCX Export
**Status:** Production Ready

---

## Overview

The Export API provides secure, market-aware DOCX report generation with jurisdiction-specific formatting. Reports are generated on-demand with proper tenant isolation and audit logging.

---

## Endpoint

### Export Project Report as DOCX

**Method:** `POST`
**Path:** `/api/v1/export/projects/{project_id}/docx`
**Authentication:** Required (JWT Bearer Token)
**Tenant Isolation:** Enforced

---

## Request

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | integer | Yes | ID of the project to export |

### Headers

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Example Request

```bash
curl -X POST \
  'https://api.genreport.com/api/v1/export/projects/123/docx' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \
  -H 'Content-Type: application/json' \
  --output report.docx
```

**Using JavaScript/TypeScript:**

```typescript
const exportReport = async (projectId: number): Promise<Blob> => {
  const response = await fetch(
    `/api/v1/export/projects/${projectId}/docx`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getAccessToken()}`,
        'Content-Type': 'application/json'
      }
    }
  );

  if (!response.ok) {
    throw new Error(`Export failed: ${response.statusText}`);
  }

  return await response.blob();
};

// Usage
const blob = await exportReport(123);
const url = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = 'report.docx';
a.click();
```

**Using Python:**

```python
import requests

def export_report(project_id: int, access_token: str) -> bytes:
    """Export project report as DOCX"""

    response = requests.post(
        f'https://api.genreport.com/api/v1/export/projects/{project_id}/docx',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    response.raise_for_status()
    return response.content

# Usage
report_bytes = export_report(123, 'your_access_token')

with open('report.docx', 'wb') as f:
    f.write(report_bytes)
```

---

## Response

### Success Response

**Status Code:** `200 OK`

**Content-Type:** `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

**Headers:**
```http
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="ABC_Holdings_Limited_20251020_143025.docx"
Content-Length: 45678
```

**Body:** Binary DOCX file

**Filename Format:**
```
{project_name}_{timestamp}.docx

Examples:
- ABC_Holdings_Limited_20251020_143025.docx
- Singapore_Tech_Pte_Ltd_20251020_150132.docx
```

---

## Error Responses

### 401 Unauthorized

**Status Code:** `401`

**Body:**
```json
{
  "detail": "Not authenticated"
}
```

**Cause:** Missing or invalid JWT token

**Resolution:** Ensure valid access token is included in Authorization header

---

### 404 Not Found

**Status Code:** `404`

**Body:**
```json
{
  "detail": "Project not found"
}
```

**Causes:**
- Project ID doesn't exist
- Project belongs to different tenant (tenant isolation)
- Project was deleted

**Resolution:** Verify project ID and tenant access

---

### 400 Bad Request

**Status Code:** `400`

**Body:**
```json
{
  "detail": "Invalid jurisdiction: XX"
}
```

**Cause:** Project has invalid or unsupported jurisdiction

**Resolution:** Ensure project jurisdiction is one of: HK, SG, AU

---

### 500 Internal Server Error

**Status Code:** `500`

**Body:**
```json
{
  "detail": "Failed to generate report: <error_message>"
}
```

**Causes:**
- Document generation failure
- File system errors
- Missing template files
- Insufficient disk space

**Resolution:** Contact support with project ID and timestamp

---

## Market-Specific Formatting

### Currency Formatting

The export API automatically formats currency based on the project's jurisdiction:

| Jurisdiction | Currency | Format Example |
|--------------|----------|----------------|
| Hong Kong (HK) | HKD | HK$15,000,000.00 |
| Singapore (SG) | SGD | S$8,500,000.00 |
| Australia (AU) | AUD | A$12,000,000.00 |

**Features:**
- Thousand separators (`,`)
- Two decimal places
- Market-appropriate currency symbol

---

### Date Formatting

All dates are formatted according to jurisdiction:

| Jurisdiction | Format | Example |
|--------------|--------|---------|
| Hong Kong (HK) | DD/MM/YYYY | 31/12/2024 |
| Singapore (SG) | DD/MM/YYYY | 15/03/2025 |
| Australia (AU) | DD/MM/YYYY | 20/10/2025 |

---

### Template Selection

Templates are automatically selected based on jurisdiction:

```
genreport/markets/
├── hk/templates/audit_report.docx
├── sg/templates/audit_report.docx
└── au/templates/audit_report.docx
```

**Fallback Behavior:**
- If jurisdiction-specific template not found, generates document programmatically
- Maintains same formatting and structure
- Logs warning for missing template

---

## Report Content

### Data Included

Generated DOCX reports include:

**Project Information:**
- Project name
- Client company name
- Financial year end
- Jurisdiction
- Accounting standard
- Currency

**Financial Data:**
- Revenue (if available)
- Other financial metrics from trial balance

**Report Sections:**
- Revenue Recognition
- Property, Plant & Equipment (future)
- Intangible Assets (future)
- Other disclosure sections (future)

**Metadata:**
- Generation timestamp
- Report status
- Source references (future)

---

## Security Features

### 1. Tenant Isolation ✅

Export API enforces strict tenant isolation:

```python
# Backend implementation
project = db.query(Project).filter(
    Project.id == project_id,
    Project.tenant_id == tenant_id  # From JWT token
).first()
```

**Result:** Users can only export projects from their own tenant.

---

### 2. Audit Logging ✅

All export operations are logged:

**Logged Information:**
- Event type: "EXPORT"
- Action: "DOCX_EXPORT" or "DOCX_EXPORT_FAILED"
- User ID
- Tenant ID
- Project ID
- Jurisdiction
- Filename
- Timestamp
- IP address
- User agent

**Query Audit Logs:**
```python
from genreport.core.database.models import AuditLog

# Find all exports for a project
exports = db.query(AuditLog).filter(
    AuditLog.event_type == "EXPORT",
    AuditLog.resource_type == "project",
    AuditLog.resource_id == project_id
).all()
```

---

### 3. Authentication Required ✅

All requests must include valid JWT token:

```http
Authorization: Bearer <access_token>
```

**Token Requirements:**
- Must be valid and not expired
- Must not be blacklisted
- Must contain tenant_id claim

---

### 4. Authorization Checks ✅

**Verified:**
- User belongs to tenant
- Project belongs to same tenant as user
- User has permission to export reports

---

## Performance Characteristics

### Response Times

**Typical Performance:**
- Small reports (< 5 pages): < 1 second
- Medium reports (5-15 pages): 1-2 seconds
- Large reports (15+ pages): 2-5 seconds

**Factors Affecting Performance:**
- Number of report sections
- Template complexity
- Server load
- Network latency

---

### Rate Limiting

**Current Limits:**
- 100 requests per minute per user
- 1000 requests per hour per tenant

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1634567890
```

---

## Best Practices

### 1. Error Handling

Always handle errors gracefully:

```typescript
try {
  const blob = await exportReport(projectId);
  downloadFile(blob, 'report.docx');
} catch (error) {
  if (error.response?.status === 404) {
    showError('Project not found');
  } else if (error.response?.status === 401) {
    redirectToLogin();
  } else {
    showError('Export failed. Please try again.');
  }
}
```

---

### 2. Progress Indication

Show progress to users during export:

```typescript
const exportWithProgress = async (projectId: number) => {
  showProgressBar('Generating report...');

  try {
    const blob = await exportReport(projectId);
    updateProgress('Download complete');
    return blob;
  } finally {
    hideProgressBar();
  }
};
```

---

### 3. File Naming

Use descriptive filenames:

```typescript
const getFileName = (project: Project): string => {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  return `${project.project_name}_${timestamp}.docx`;
};
```

---

### 4. Caching Strategy

Consider caching for frequently accessed reports:

```typescript
const exportCache = new Map<number, { blob: Blob, timestamp: number }>();

const exportReportCached = async (projectId: number): Promise<Blob> => {
  const cached = exportCache.get(projectId);

  // Cache for 5 minutes
  if (cached && Date.now() - cached.timestamp < 5 * 60 * 1000) {
    return cached.blob;
  }

  const blob = await exportReport(projectId);
  exportCache.set(projectId, { blob, timestamp: Date.now() });

  return blob;
};
```

---

## Troubleshooting

### Issue: 404 Project Not Found (but project exists)

**Possible Causes:**
1. Tenant mismatch (different tenant than user)
2. Project deleted
3. Database replication lag

**Resolution:**
```bash
# Verify project exists and tenant matches
SELECT p.id, p.project_name, p.tenant_id, t.company_name
FROM projects p
JOIN tenants t ON p.tenant_id = t.id
WHERE p.id = 123;

# Check audit logs for deletion
SELECT * FROM audit_logs
WHERE resource_type = 'project'
  AND resource_id = 123
  AND action = 'DELETE'
ORDER BY created_at DESC;
```

---

### Issue: Export Fails with 500 Error

**Possible Causes:**
1. Missing template file
2. Disk space full
3. Corrupted project data

**Resolution:**
```bash
# Check logs
tail -f /var/log/genreport/api.log | grep "EXPORT"

# Verify template exists
ls -la genreport/markets/hk/templates/

# Check disk space
df -h /tmp
```

---

### Issue: Incorrect Currency Formatting

**Possible Causes:**
1. Project currency field null or invalid
2. Wrong jurisdiction set

**Resolution:**
```sql
-- Check project settings
SELECT id, project_name, jurisdiction, currency
FROM projects
WHERE id = 123;

-- Update if needed
UPDATE projects
SET currency = 'HKD', jurisdiction = 'HK'
WHERE id = 123;
```

---

## Examples

### React Component

```typescript
// components/ExportButton.tsx
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';

interface ExportButtonProps {
  projectId: number;
  projectName: string;
}

export const ExportButton: React.FC<ExportButtonProps> = ({
  projectId,
  projectName
}) => {
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    setIsExporting(true);

    try {
      const response = await fetch(
        `/api/v1/export/projects/${projectId}/docx`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${getAccessToken()}`
          }
        }
      );

      if (!response.ok) {
        throw new Error('Export failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${projectName}_${Date.now()}.docx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export report. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <Button
      onClick={handleExport}
      disabled={isExporting}
      variant="outline"
    >
      {isExporting ? (
        <>Exporting...</>
      ) : (
        <>
          <Download className="mr-2 h-4 w-4" />
          Export DOCX
        </>
      )}
    </Button>
  );
};
```

---

### Python Batch Export

```python
# scripts/batch_export.py
import requests
from pathlib import Path
from typing import List

def batch_export_projects(
    project_ids: List[int],
    access_token: str,
    output_dir: Path
):
    """Export multiple projects in batch"""

    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for project_id in project_ids:
        try:
            response = requests.post(
                f'https://api.genreport.com/api/v1/export/projects/{project_id}/docx',
                headers={'Authorization': f'Bearer {access_token}'}
            )

            response.raise_for_status()

            # Extract filename from Content-Disposition
            content_disposition = response.headers.get('Content-Disposition', '')
            filename = content_disposition.split('filename=')[-1].strip('"')

            # Save file
            output_path = output_dir / filename
            output_path.write_bytes(response.content)

            results.append({
                'project_id': project_id,
                'status': 'success',
                'file': str(output_path)
            })

            print(f"✓ Exported project {project_id} to {filename}")

        except Exception as e:
            results.append({
                'project_id': project_id,
                'status': 'failed',
                'error': str(e)
            })

            print(f"✗ Failed to export project {project_id}: {e}")

    return results

# Usage
if __name__ == '__main__':
    project_ids = [123, 456, 789]
    access_token = 'your_access_token'
    output_dir = Path('./exports')

    results = batch_export_projects(project_ids, access_token, output_dir)

    success_count = sum(1 for r in results if r['status'] == 'success')
    print(f"\nCompleted: {success_count}/{len(project_ids)} exports")
```

---

## Related Documentation

- [Sprint 5 Completion Report](../reports/2025-10-20-sprint5-completion-report.md)
- [DOCX Generator Implementation](../architecture/2025-10-20-docx-generator-design.md)
- [API Authentication Guide](../guides/api-authentication.md)
- [Tenant Isolation Guide](../guides/tenant-isolation.md)

---

**Document Version:** 1.0
**Last Updated:** 2025-10-20
**Maintained By:** Backend Team
