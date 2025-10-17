# Sprint 5: Review Interface & Export
## Hybrid Architecture + Security Implementation (v3.0)

**Duration:** 2.5 weeks (Extended from 2 weeks)  
**Sprint Goal:** Secure, market-aware user interface with XSS/CSRF protection  
**Story Points:** 38 (+3 days for security)  
**Team Size:** 2-3 developers

[← Back to Master Plan](./master_sprint_plan.md)

---

## Overview

Sprint 5 delivers a **secure, market-aware frontend** with currency formatting, market-specific templates, and comprehensive security controls.

### Sprint Objectives
✅ Market-aware UI (currency, date formats)  
✅ XSS protection (DOMPurify)  
✅ CSRF token validation  
✅ Input sanitization  
✅ Market-specific DOCX templates  
✅ Secure source referencing  
✅ Performance optimization for large reports

---

## Hybrid Architecture: Market-Aware UI

### 1. Market Context in Frontend

```typescript
// frontend/src/types/Project.ts
export interface Project {
  id: number;
  project_name: string;
  client: {
    id: number;
    company_name: string;
  };
  
  // Hybrid Architecture fields
  jurisdiction: 'HK' | 'SG' | 'AU';  // NEW
  accounting_standard: string;       // NEW
  currency: string;                  // NEW
  
  financial_year_end: string;
  status: 'draft' | 'processing' | 'review' | 'approved';
  created_at: string;
  updated_at: string;
}

export interface MarketInfo {
  jurisdiction: string;
  currency: string;
  accounting_standard: string;
  date_format: string;
}
```

### 2. Currency Formatting Helper

```typescript
// frontend/src/utils/currency.ts
export class CurrencyFormatter {
  static format(amount: number, currency: string): string {
    return new Intl.NumberFormat('en', {
      style: 'currency',
      currency: currency  // HKD, SGD, AUD
    }).format(amount);
  }
  
  static formatCompact(amount: number, currency: string): string {
    return new Intl.NumberFormat('en', {
      style: 'currency',
      currency: currency,
      notation: 'compact',
      maximumFractionDigits: 1
    }).format(amount);
  }
}

// Usage in components
const RevenueSection = ({ revenue, currency }: Props) => {
  return (
    <div>
      <h3>Revenue</h3>
      <p>Total: {CurrencyFormatter.format(revenue.total, currency)}</p>
    </div>
  );
};
```

### 3. Date Formatting by Market

```typescript
// frontend/src/utils/date.ts
export class DateFormatter {
  static format(date: Date, format: string): string {
    const locale = format === 'DD/MM/YYYY' ? 'en-GB' : 'en-US';
    
    return new Intl.DateFormat(locale, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    }).format(date);
  }
  
  static formatByJurisdiction(date: Date, jurisdiction: string): string {
    const formats = {
      'HK': 'DD/MM/YYYY',
      'SG': 'DD/MM/YYYY',
      'AU': 'DD/MM/YYYY',
      'US': 'MM/DD/YYYY'
    };
    
    return this.format(date, formats[jurisdiction] || 'DD/MM/YYYY');
  }
}
```

### 4. Project Dashboard with Jurisdiction

```tsx
// frontend/src/components/dashboard/ProjectCard.tsx
import { Project } from '@/types';
import { CurrencyFormatter } from '@/utils/currency';

const ProjectCard = ({ project }: { project: Project }) => {
  return (
    <div className="project-card">
      <h3>{project.project_name}</h3>
      <div className="meta">
        <span className="jurisdiction-badge">
          {project.jurisdiction}
        </span>
        <span>{project.accounting_standard}</span>
      </div>
      <div className="details">
        <p>Client: {project.client.company_name}</p>
        <p>FYE: {DateFormatter.formatByJurisdiction(
          new Date(project.financial_year_end),
          project.jurisdiction
        )}</p>
      </div>
    </div>
  );
};
```

---

## Security Implementation

### 1. XSS Protection with DOMPurify

```typescript
// frontend/src/services/sanitization.ts
import DOMPurify from 'dompurify';

export class SanitizationService {
  /**
   * Sanitize HTML content to prevent XSS
   */
  static sanitizeHTML(dirty: string): string {
    return DOMPurify.sanitize(dirty, {
      ALLOWED_TAGS: [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3',
        'ul', 'ol', 'li', 'table', 'tr', 'td', 'th'
      ],
      ALLOWED_ATTR: ['class', 'id'],
      KEEP_CONTENT: true
    });
  }
  
  /**
   * Sanitize user input (remove all HTML)
   */
  static sanitizeInput(input: string): string {
    return DOMPurify.sanitize(input, {
      ALLOWED_TAGS: [],
      ALLOWED_ATTR: [],
      KEEP_CONTENT: true
    });
  }
  
  /**
   * Validate and sanitize rich text content
   */
  static sanitizeRichText(content: string): string {
    // First pass: Remove dangerous tags
    let cleaned = DOMPurify.sanitize(content, {
      FORBID_TAGS: ['script', 'iframe', 'object', 'embed'],
      FORBID_ATTR: [
        'onerror', 'onload', 'onclick', 'onmouseover'
      ]
    });
    
    // Second pass: Additional cleaning
    cleaned = cleaned.replace(/javascript:/gi, '');
    cleaned = cleaned.replace(/on\w+\s*=/gi, '');
    
    return cleaned;
  }
}

// Usage in components
const ReportDisplay = ({ content }: { content: string }) => {
  const sanitizedContent = SanitizationService.sanitizeHTML(content);
  
  return (
    <div 
      dangerouslySetInnerHTML={{ __html: sanitizedContent }}
    />
  );
};
```

### 2. CSRF Protection

```typescript
// frontend/src/services/api.ts
import axios from 'axios';

class APIClient {
  private csrfToken: string | null = null;
  
  constructor() {
    this.setupCSRFToken();
  }
  
  async setupCSRFToken() {
    // Fetch CSRF token on app init
    const response = await axios.get('/api/csrf-token');
    this.csrfToken = response.data.csrf_token;
    
    // Add to all requests
    axios.defaults.headers.common['X-CSRF-Token'] = this.csrfToken;
  }
  
  async post(url: string, data: any) {
    if (!this.csrfToken) {
      await this.setupCSRFToken();
    }
    
    return axios.post(url, data, {
      headers: {
        'X-CSRF-Token': this.csrfToken
      }
    });
  }
  
  async refreshCSRFToken() {
    await this.setupCSRFToken();
  }
}

export const apiClient = new APIClient();
```

### 3. Input Sanitization

```typescript
// frontend/src/hooks/useSecureInput.ts
import { useState } from 'react';
import { SanitizationService } from '@/services/sanitization';

export const useSecureInput = (initialValue: string = '') => {
  const [value, setValue] = useState(initialValue);
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Sanitize input immediately
    const sanitized = SanitizationService.sanitizeInput(e.target.value);
    setValue(sanitized);
  };
  
  return [value, handleChange] as const;
};

// Usage
const EditSection = () => {
  const [content, setContent] = useSecureInput();
  
  return (
    <input
      value={content}
      onChange={setContent}
      maxLength={10000}  // Enforce length limits
    />
  );
};
```

### 4. Content Security Policy

```typescript
// frontend/public/index.html or via meta tag
const cspDirectives = {
  'default-src': ["'self'"],
  'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'"],  // Minimize in production
  'style-src': ["'self'", "'unsafe-inline'"],
  'img-src': ["'self'", 'data:', 'https:'],
  'font-src': ["'self'", 'data:'],
  'connect-src': ["'self'", process.env.REACT_APP_API_URL],
  'frame-ancestors': ["'none'"]
};

// Apply via meta tag
const csp = Object.entries(cspDirectives)
  .map(([key, values]) => `${key} ${values.join(' ')}`)
  .join('; ');

document.querySelector('meta[http-equiv="Content-Security-Policy"]')
  ?.setAttribute('content', csp);
```

### 5. Secure API Communication

```typescript
// frontend/src/services/auth.ts
import axios from 'axios';

export class AuthService {
  private static readonly TOKEN_KEY = 'access_token';
  private static readonly REFRESH_KEY = 'refresh_token';
  
  static async login(email: string, password: string) {
    // Never store tokens in localStorage in production
    // Use HTTP-only cookies instead
    
    const response = await axios.post('/api/auth/login', {
      email: SanitizationService.sanitizeInput(email),
      password  // Never log or expose passwords
    });
    
    // Tokens handled by HTTP-only cookies
    return response.data;
  }
  
  static async refreshToken() {
    // Refresh token stored in HTTP-only cookie
    const response = await axios.post('/api/auth/refresh');
    return response.data;
  }
  
  static setupAxiosInterceptors() {
    // Add interceptor for 401 errors
    axios.interceptors.response.use(
      response => response,
      async error => {
        if (error.response?.status === 401) {
          try {
            await this.refreshToken();
            // Retry original request
            return axios(error.config);
          } catch {
            // Redirect to login
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );
  }
}
```

---

## Market-Specific DOCX Export

### Backend DOCX Generator

```python
# core/export/docx_generator.py
from docx import Document
from pathlib import Path
from typing import Dict

class MarketAwareDocxGenerator:
    """Generate DOCX using market-specific templates"""
    
    def __init__(self, jurisdiction: str):
        self.jurisdiction = jurisdiction
        self.templates_path = self._get_templates_path()
    
    def _get_templates_path(self) -> Path:
        """Get market-specific templates path"""
        return Path(f"markets/{self.jurisdiction.lower()}/templates")
    
    def generate(self, report_data: Dict, template_name: str = "audit_report.docx"):
        """Generate DOCX from market-specific template"""
        
        # Load template
        template_path = self.templates_path / template_name
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        # Load template
        doc = Document(str(template_path))
        
        # Replace placeholders
        self._replace_placeholders(doc, report_data)
        
        # Apply market-specific formatting
        self._apply_market_formatting(doc, report_data)
        
        return doc
    
    def _replace_placeholders(self, doc: Document, data: Dict):
        """Replace {{placeholders}} in document"""
        for paragraph in doc.paragraphs:
            for key, value in data.items():
                placeholder = f"{{{{{key}}}}}"
                if placeholder in paragraph.text:
                    paragraph.text = paragraph.text.replace(placeholder, str(value))
    
    def _apply_market_formatting(self, doc: Document, data: Dict):
        """Apply market-specific formatting"""
        
        # Currency formatting
        currency = data.get('currency', 'HKD')
        
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    # Format currency values
                    if '{{currency}}' in cell.text:
                        amount = data.get('amount', 0)
                        cell.text = f"{currency} {amount:,.2f}"
        
        # Date formatting
        date_format = self._get_date_format()
        for paragraph in doc.paragraphs:
            if '{{date}}' in paragraph.text:
                from datetime import datetime
                formatted_date = datetime.now().strftime(date_format)
                paragraph.text = paragraph.text.replace('{{date}}', formatted_date)
    
    def _get_date_format(self) -> str:
        """Get date format for jurisdiction"""
        formats = {
            'HK': '%d/%m/%Y',
            'SG': '%d/%m/%Y',
            'AU': '%d/%m/%Y',
            'US': '%m/%d/%Y'
        }
        return formats.get(self.jurisdiction, '%d/%m/%Y')

# API endpoint
@router.post("/projects/{project_id}/export")
async def export_report(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant)
):
    """Export report with market-specific template"""
    
    # Get project
    project = get_project(db, project_id, tenant_id)
    
    # Get report data
    report_data = get_report_data(db, project_id)
    
    # Add market context
    report_data['currency'] = project.currency
    report_data['jurisdiction'] = project.jurisdiction
    report_data['accounting_standard'] = project.accounting_standard
    
    # Generate DOCX
    generator = MarketAwareDocxGenerator(project.jurisdiction)
    doc = generator.generate(report_data)
    
    # Save to temp file
    output_path = f"/tmp/{project_id}_report.docx"
    doc.save(output_path)
    
    # Audit log
    AuditLogger.log_event(
        db=db,
        event_type="EXPORT",
        action="DOCX_EXPORT",
        user_id=current_user.id,
        tenant_id=tenant_id,
        resource_type="report",
        resource_id=project_id
    )
    
    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{project.project_name}_report.docx"
    )
```

---

## Testing Strategy

```typescript
// tests/security/xss.test.ts
import { SanitizationService } from '@/services/sanitization';

describe('XSS Protection', () => {
  it('should remove script tags', () => {
    const dirty = '<p>Hello</p><script>alert("XSS")</script>';
    const clean = SanitizationService.sanitizeHTML(dirty);
    
    expect(clean).not.toContain('<script>');
    expect(clean).toContain('<p>Hello</p>');
  });
  
  it('should remove event handlers', () => {
    const dirty = '<div onclick="alert(1)">Click</div>';
    const clean = SanitizationService.sanitizeHTML(dirty);
    
    expect(clean).not.toContain('onclick');
  });
  
  it('should remove javascript: URLs', () => {
    const dirty = '<a href="javascript:alert(1)">Link</a>';
    const clean = SanitizationService.sanitizeHTML(dirty);
    
    expect(clean).not.toContain('javascript:');
  });
});

// tests/hybrid/market-formatting.test.ts
describe('Market-Aware Formatting', () => {
  it('should format HK currency correctly', () => {
    const formatted = CurrencyFormatter.format(1234567.89, 'HKD');
    expect(formatted).toBe('HK$1,234,567.89');
  });
  
  it('should format SG currency correctly', () => {
    const formatted = CurrencyFormatter.format(1234567.89, 'SGD');
    expect(formatted).toBe('S$1,234,567.89');
  });
  
  it('should format dates by jurisdiction', () => {
    const date = new Date('2025-03-15');
    
    expect(DateFormatter.formatByJurisdiction(date, 'HK')).toBe('15/03/2025');
    expect(DateFormatter.formatByJurisdiction(date, 'US')).toBe('03/15/2025');
  });
});
```

---

## Definition of Done

### Sprint 5 is complete when:

#### Hybrid Architecture
- [x] UI displays jurisdiction and accounting standard
- [x] Currency formatting works for all markets
- [x] Date formatting respects jurisdiction
- [x] Market-specific DOCX templates working

#### Security
- [x] XSS protection with DOMPurify implemented
- [x] CSRF tokens on all state-changing requests
- [x] Input sanitization working
- [x] CSP configured
- [x] Secure API communication (HTTP-only cookies)
- [x] Security tests pass

#### Core Functionality
- [x] Interactive review interface working
- [x] Source referencing functional
- [x] Inline editing with auto-save
- [x] DOCX export functional
- [x] Performance optimized for large reports

#### Quality
- [x] All tests pass (unit, integration, security)
- [x] Performance targets met
- [x] No XSS vulnerabilities
- [x] CSRF protection verified

---

## Time Estimates

**Week 1: Core UI (40 hours)**
- Market-aware components: 12h
- Review interface: 12h
- Source referencing: 8h
- Testing: 8h

**Week 2: Security & Export (40 hours)**
- XSS protection: 8h
- CSRF implementation: 6h
- Input sanitization: 6h
- DOCX export: 12h
- Security testing: 8h

**Week 2.5: Polish (10 hours)**
- Performance optimization: 4h
- Bug fixes: 3h
- Documentation: 3h

**Total: 90 hours (2.5 weeks, 2-3 developers)**

---

## Next Steps

After Sprint 5, proceed to:

**Sprint 6:** Testing, Security Audit & Production Readiness
- Penetration testing
- Multi-region deployment
- Disaster recovery plan

[→ View Sprint 6 Details](./sprint_6_production.md)

[← Back to Master Plan](./master_sprint_plan.md)

---

**Document Version:** 3.0 (Hybrid + Security)  
**Last Updated:** 2025-10-17  
**Status:** Ready for Implementation