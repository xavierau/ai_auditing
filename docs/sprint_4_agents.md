# Sprint 4: Advanced AI Report Generation  
## Hybrid Architecture + Security Implementation (v3.0)

**Duration:** 3.5 weeks (Extended from 3 weeks)  
**Sprint Goal:** Production-ready DSPy agents with market-awareness and security  
**Story Points:** 34 (+4 days for security)  
**Team Size:** 2-3 developers

[← Back to Master Plan](./master_sprint_plan.md)

---

## Overview

Sprint 4 builds **market-aware AI agents** with complete tenant isolation and PII detection. Agents automatically use the correct accounting standards based on project jurisdiction.

### Sprint Objectives
✅ Base agent classes for multi-market support  
✅ Agent factory pattern for market-specific agents  
✅ Context validation (no cross-tenant data)  
✅ PII detection in generated content  
✅ Rate limiting per tenant  
✅ Comprehensive error handling  
✅ Source attribution with audit trail

---

## Hybrid Architecture: Base Agent Classes

### Generic Base Agent

```python
# core/orchestration/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any
import dspy

class BaseFinancialAgent(ABC):
    """Base agent that works for any market"""
    
    def __init__(self, market_config, retriever, tenant_id):
        self.market_config = market_config
        self.retriever = retriever
        self.tenant_id = tenant_id
    
    @abstractmethod
    async def analyze(self, context: dict) -> dict:
        """Analyze financial data and generate disclosure"""
        pass
    
    def get_relevant_standards(self, query: str):
        """Get standards filtered by jurisdiction"""
        return self.retriever.retrieve(
            query=query,
            top_k=5
        )
    
    def format_currency(self, amount: float) -> str:
        """Format currency based on market"""
        return f"{self.market_config.currency} {amount:,.2f}"
    
    def validate_context(self, context: dict):
        """Ensure no cross-tenant data contamination"""
        from core.security.context_validator import ContextValidator
        
        validator = ContextValidator(self.tenant_id)
        if not validator.validate(context):
            raise SecurityError("Cross-tenant data detected in context")
```

### HK-Specific Agent Implementation

```python
# markets/hk/agents/revenue_agent.py
from core.orchestration.base_agent import BaseFinancialAgent
import dspy

class HKRevenueAgent(BaseFinancialAgent):
    """Hong Kong Revenue Recognition Agent"""
    
    async def analyze(self, context: dict) -> dict:
        """
        Generate revenue note using HKFRS 15 or SME-FRS
        """
        # Validate context first
        self.validate_context(context)
        
        # Get relevant standards (automatically filtered to HK)
        standards = self.get_relevant_standards(
            "revenue recognition performance obligations"
        )
        
        # Determine if SME
        is_sme = self._is_sme_entity(context)
        standard = "SME-FRS" if is_sme else "HKFRS 15"
        
        # Define signature
        class GenerateRevenueNote(dspy.Signature):
            """Generate revenue recognition note"""
            revenue_data: dict = dspy.InputField()
            standards: list = dspy.InputField()
            accounting_standard: str = dspy.InputField()
            currency: str = dspy.InputField()
            
            disclosure: str = dspy.OutputField(desc="Revenue disclosure")
            completeness_score: float = dspy.OutputField()
            source_references: list = dspy.OutputField()
        
        # Generate
        generator = dspy.ChainOfThought(GenerateRevenueNote)
        result = generator(
            revenue_data=context['revenue'],
            standards=standards,
            accounting_standard=standard,
            currency=self.market_config.currency
        )
        
        # Scan for PII
        result.disclosure = self._remove_pii(result.disclosure)
        
        return {
            "section": "revenue_recognition",
            "content": result.disclosure,
            "standard_used": standard,
            "completeness": result.completeness_score,
            "sources": result.source_references
        }
    
    def _is_sme_entity(self, context: dict) -> bool:
        """Check if entity qualifies as SME under HK rules"""
        # Implement SME criteria (turnover, employees, etc.)
        return context.get('entity_type') == 'SME'
    
    def _remove_pii(self, content: str) -> str:
        """Remove PII from generated content"""
        from core.security.pii_detector import PIIDetector
        
        detector = PIIDetector()
        return detector.redact(content)
```

### Agent Factory Pattern

```python
# core/orchestration/agent_factory.py
from typing import Dict
from core.orchestration.base_agent import BaseFinancialAgent

class AgentFactory:
    """Factory to create market-specific agents"""
    
    @staticmethod
    def create_agents(
        jurisdiction: str,
        tenant_id: UUID,
        user_id: int
    ) -> Dict[str, BaseFinancialAgent]:
        """Create agents for specific jurisdiction"""
        
        # Get market config
        from markets.hk.config import get_market_config
        config = get_market_config(jurisdiction)
        
        # Get jurisdiction-aware retriever
        from core.retrieval.kb_retriever import SecureKBRetriever
        retriever = SecureKBRetriever(
            jurisdiction=jurisdiction,
            tenant_id=tenant_id,
            user_id=user_id
        )
        
        # Create market-specific agents
        if jurisdiction == "HK":
            from markets.hk.agents import (
                HKRevenueAgent,
                HKPPEAgent,
                HKLeaseAgent,
                HKInventoryAgent
            )
            
            return {
                "revenue": HKRevenueAgent(config, retriever, tenant_id),
                "ppe": HKPPEAgent(config, retriever, tenant_id),
                "lease": HKLeaseAgent(config, retriever, tenant_id),
                "inventory": HKInventoryAgent(config, retriever, tenant_id)
            }
        
        elif jurisdiction == "SG":
            # Future: Singapore agents
            from markets.sg.agents import SGRevenueAgent
            # ...
        
        else:
            raise ValueError(f"Unsupported jurisdiction: {jurisdiction}")
```

---

## Security Implementation

### 1. Context Validation (No Cross-Tenant Data)

```python
# core/security/context_validator.py
from uuid import UUID
from typing import Dict, Any

class ContextValidator:
    """Validates that context contains no cross-tenant data"""
    
    def __init__(self, expected_tenant_id: UUID):
        self.expected_tenant_id = expected_tenant_id
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """
        Recursively check all data for tenant_id fields
        Ensures no data leakage between tenants
        """
        violations = []
        
        for key, value in context.items():
            violations.extend(
                self._check_value(key, value, path=[key])
            )
        
        if violations:
            from core.security.audit_logger import AuditLogger
            
            # Log security violation
            AuditLogger.log_event(
                db=get_db(),
                event_type="SECURITY_VIOLATION",
                action="CROSS_TENANT_DATA_DETECTED",
                tenant_id=self.expected_tenant_id,
                details={"violations": violations},
                status="FAILURE"
            )
            
            return False
        
        return True
    
    def _check_value(self, key: str, value: Any, path: list) -> list:
        """Check individual value for tenant_id mismatches"""
        violations = []
        
        if isinstance(value, dict):
            # Check if dict has tenant_id
            if 'tenant_id' in value:
                if str(value['tenant_id']) != str(self.expected_tenant_id):
                    violations.append({
                        "path": " -> ".join(path),
                        "found_tenant_id": str(value['tenant_id']),
                        "expected_tenant_id": str(self.expected_tenant_id)
                    })
            
            # Recurse into dict
            for k, v in value.items():
                violations.extend(
                    self._check_value(k, v, path + [k])
                )
        
        elif isinstance(value, list):
            # Check each item in list
            for idx, item in enumerate(value):
                violations.extend(
                    self._check_value(f"{key}[{idx}]", item, path + [f"[{idx}]"])
                )
        
        return violations

# Usage in orchestrator
class SecureOrchestrator:
    def package_context(self, project_id: int, tenant_id: UUID) -> dict:
        """Package context with validation"""
        
        # Get data
        context = {
            "trial_balance": get_trial_balance(project_id, tenant_id),
            "general_ledger": get_general_ledger(project_id, tenant_id),
            "prior_year": get_prior_year_data(project_id, tenant_id),
            "relationship_map": get_relationship_map(project_id, tenant_id)
        }
        
        # Validate no cross-tenant data
        validator = ContextValidator(tenant_id)
        if not validator.validate(context):
            raise SecurityError(
                "Context validation failed: cross-tenant data detected"
            )
        
        return context
```

### 2. PII Detection and Redaction

```python
# core/security/pii_detector.py
import re
from typing import List, Dict

class PIIDetector:
    """Detects and redacts PII from generated content"""
    
    # Patterns for different types of PII
    PATTERNS = {
        'hkid': r'[A-Z]\d{6}\([0-9A]\)',
        'phone_hk': r'\+852\s?\d{4}\s?\d{4}',
        'phone_intl': r'\+\d{1,3}\s?\d{3,4}\s?\d{4,8}',
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'credit_card': r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}',
        'bank_account': r'\d{3}-\d{6}-\d{3}',
        'address': r'\d+[A-Za-z\s,]+(?:Street|Road|Avenue|Drive|Lane|Floor)',
    }
    
    def scan(self, text: str) -> Dict[str, List[str]]:
        """Scan text for PII"""
        findings = {}
        
        for pii_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                findings[pii_type] = matches
        
        return findings
    
    def redact(self, text: str) -> str:
        """Redact PII from text"""
        redacted = text
        
        for pii_type, pattern in self.PATTERNS.items():
            if pii_type == 'email':
                # Partial redaction for emails
                redacted = re.sub(
                    pattern,
                    lambda m: self._partial_redact_email(m.group()),
                    redacted
                )
            elif pii_type == 'phone_hk' or pii_type == 'phone_intl':
                # Keep last 4 digits
                redacted = re.sub(
                    pattern,
                    lambda m: f"***{m.group()[-4:]}",
                    redacted
                )
            else:
                # Full redaction
                redacted = re.sub(pattern, '[REDACTED]', redacted)
        
        return redacted
    
    def _partial_redact_email(self, email: str) -> str:
        """Partially redact email (keep first 2 chars and domain)"""
        try:
            local, domain = email.split('@')
            if len(local) > 2:
                return f"{local[:2]}***@{domain}"
            else:
                return f"***@{domain}"
        except:
            return '[REDACTED]'

# Usage in agents
class SecureAgent(BaseFinancialAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pii_detector = PIIDetector()
    
    async def analyze(self, context: dict) -> dict:
        # Generate content
        result = await self._generate_content(context)
        
        # Scan for PII
        pii_findings = self.pii_detector.scan(result['content'])
        
        if pii_findings:
            # Log PII detection
            logger.warning(f"PII detected in generated content: {pii_findings}")
            
            # Redact PII
            result['content'] = self.pii_detector.redact(result['content'])
            result['pii_detected'] = True
            result['pii_types'] = list(pii_findings.keys())
        
        return result
```

### 3. Rate Limiting Per Tenant

```python
# core/security/tenant_rate_limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from functools import wraps

def tenant_rate_limit(calls: int, period: str):
    """Rate limit decorator per tenant"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from core.security.tenant_context import get_current_tenant
            
            tenant_id = get_current_tenant()
            
            # Check rate limit for this tenant
            rate_limiter = TenantRateLimiter()
            if not rate_limiter.allow(tenant_id, calls, period):
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded: {calls} calls per {period}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator

# Usage
@router.post("/generate-report")
@tenant_rate_limit(calls=100, period="hour")
async def generate_report(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate report with per-tenant rate limiting"""
    pass
```

---

## Orchestration with Security

```python
# core/orchestration/secure_orchestrator.py
from typing import Dict
from uuid import UUID

class SecureOrchestrator:
    """Orchestrator with security built-in"""
    
    def __init__(self, project_id: int, tenant_id: UUID, user_id: int):
        self.project_id = project_id
        self.tenant_id = tenant_id
        self.user_id = user_id
        
        # Get project to determine jurisdiction
        self.project = self._get_project()
        
        # Create market-specific agents
        self.agents = AgentFactory.create_agents(
            jurisdiction=self.project.jurisdiction,
            tenant_id=tenant_id,
            user_id=user_id
        )
    
    async def generate_report(self) -> Dict:
        """Generate complete report with security"""
        
        # Package context with validation
        context = self.package_context()
        
        # Get relationship map to determine which agents to trigger
        rel_map = context['relationship_map']
        
        results = {}
        
        # Trigger relevant agents
        for section, agent_name in self._map_sections_to_agents(rel_map):
            agent = self.agents[agent_name]
            
            try:
                # Generate section
                result = await agent.analyze(context)
                results[section] = result
                
                # Audit log
                self._log_generation(section, result)
                
            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {str(e)}")
                results[section] = {
                    "error": str(e),
                    "status": "failed"
                }
        
        return results
    
    def package_context(self) -> Dict:
        """Package context with validation"""
        context = {
            "trial_balance": get_trial_balance(self.project_id, self.tenant_id),
            "general_ledger": get_general_ledger(self.project_id, self.tenant_id),
            "prior_year": get_prior_year_data(self.project_id, self.tenant_id),
            "relationship_map": get_relationship_map(self.project_id, self.tenant_id),
            "project_metadata": {
                "jurisdiction": self.project.jurisdiction,
                "accounting_standard": self.project.accounting_standard,
                "financial_year_end": self.project.financial_year_end
            }
        }
        
        # Validate no cross-tenant data
        validator = ContextValidator(self.tenant_id)
        if not validator.validate(context):
            raise SecurityError("Context validation failed")
        
        return context
    
    def _log_generation(self, section: str, result: Dict):
        """Audit log generation"""
        from core.security.audit_logger import AuditLogger
        
        AuditLogger.log_event(
            db=get_db(),
            event_type="REPORT_GENERATION",
            action="GENERATE_SECTION",
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            resource_type="report_section",
            details={
                "section": section,
                "project_id": self.project_id,
                "completeness": result.get('completeness'),
                "pii_detected": result.get('pii_detected', False)
            },
            status="SUCCESS"
        )
```

---

## Testing Strategy

```python
# tests/test_agent_security.py
import pytest
from uuid import uuid4

def test_context_validation_detects_cross_tenant():
    """Ensure context validator catches cross-tenant data"""
    tenant_a = uuid4()
    tenant_b = uuid4()
    
    # Context with mixed tenant data
    context = {
        "trial_balance": {"tenant_id": tenant_a, "data": []},
        "general_ledger": {"tenant_id": tenant_b, "data": []}  # Wrong tenant!
    }
    
    validator = ContextValidator(tenant_a)
    assert validator.validate(context) is False

def test_pii_detection():
    """Ensure PII is detected and redacted"""
    detector = PIIDetector()
    
    text = "Contact John at john@example.com or +852 1234 5678. HKID: A123456(7)"
    
    # Scan
    findings = detector.scan(text)
    assert 'email' in findings
    assert 'phone_hk' in findings
    assert 'hkid' in findings
    
    # Redact
    redacted = detector.redact(text)
    assert "john@example.com" not in redacted
    assert "A123456(7)" not in redacted

def test_agent_uses_correct_jurisdiction():
    """Ensure agents use jurisdiction-specific standards"""
    tenant_id = uuid4()
    
    # Create HK project
    project = create_project(jurisdiction="HK")
    
    # Create agent
    agents = AgentFactory.create_agents("HK", tenant_id, user_id=1)
    
    # Generate revenue note
    context = create_mock_context(project)
    result = await agents['revenue'].analyze(context)
    
    # Should reference HKFRS 15 or SME-FRS
    assert any(std in result['content'] for std in ['HKFRS 15', 'SME-FRS'])
    assert 'HKD' in result['content']  # HK currency

def test_rate_limiting_per_tenant():
    """Ensure rate limiting is enforced per tenant"""
    tenant_a = uuid4()
    tenant_b = uuid4()
    
    # Tenant A makes 100 requests (limit)
    for i in range(100):
        generate_report(project_id=1, tenant_id=tenant_a)
    
    # 101st should fail
    with pytest.raises(HTTPException) as exc:
        generate_report(project_id=1, tenant_id=tenant_a)
    assert exc.value.status_code == 429
    
    # But tenant B should still work
    generate_report(project_id=2, tenant_id=tenant_b)  # Should succeed
```

---

## Definition of Done

### Sprint 4 is complete when:

#### Hybrid Architecture
- [x] Base agent classes work for any market
- [x] Agent factory creates market-specific agents
- [x] HK agents implemented (Revenue, PPE, Lease, Inventory)
- [x] No hardcoded jurisdictions in core orchestration

#### Security
- [x] Context validation prevents cross-tenant data
- [x] PII detection and redaction working
- [x] Rate limiting per tenant enforced
- [x] Audit logging for all agent operations
- [x] Security tests pass

#### Core Functionality
- [x] DSPy agents generate quality disclosures
- [x] Context packaging with size limits
- [x] Error handling and retry logic
- [x] Source attribution working
- [x] End-to-end generation <3min
- [x] Cost per report <$0.50

#### Quality
- [x] Agent quality >90% completeness
- [x] Required disclosures >95% present
- [x] All tests pass (unit, integration, security)
- [x] Performance targets met

---

## Time Estimates

**Week 1-2: Agent Development (80 hours)**
- Base agent classes: 12h
- Agent factory: 8h
- HK agents (4 agents): 32h
- Context packaging: 12h
- Testing: 16h

**Week 3: Security (40 hours)**
- Context validation: 10h
- PII detection: 10h
- Rate limiting: 6h
- Audit logging: 6h
- Security testing: 8h

**Week 3.5: Integration (14 hours)**
- End-to-end testing: 6h
- Performance optimization: 4h
- Documentation: 4h

**Total: 134 hours (3.5 weeks, 2-3 developers)**

---

## Next Steps

After Sprint 4, proceed to:

**Sprint 5:** Review Interface & Export
- Market-aware UI (currency formatting)
- Market-specific DOCX templates
- XSS/CSRF protection

[→ View Sprint 5 Details](./sprint_5_frontend.md)

[← Back to Master Plan](./master_sprint_plan.md)

---

**Document Version:** 3.0 (Hybrid + Security)  
**Last Updated:** 2025-10-17  
**Status:** Ready for Implementation