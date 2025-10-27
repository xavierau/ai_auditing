# GenReport Implementation Guides

This directory contains step-by-step implementation guides, operational runbooks, and troubleshooting documentation.

**Last Updated:** 2025-10-24

---

## Quick Navigation

### 🚀 Getting Started

Start here if you're new to the project:
1. **LLM Configuration** - `2025-10-17-llm-configuration.md`
2. **Running Celery Workers** - `2025-10-17-running-celery-workers.md`

### 📚 By Category

#### AI/ML Implementation Guides

**Chunk Categorizer (Knowledge Base)**
- **File:** `2025-10-18-chunk-categorizer-implementation.md`
- **Purpose:** DSPy-based semi-automated content classification
- **Sprint:** Sprint 3 - Knowledge Base RAG System
- **When to Use:** Implementing or understanding chunk categorization logic
- **Key Topics:**
  - DSPy signature for content type classification
  - 7 content types (requirement, template, example, definition, disclosure, table, general)
  - Semi-automated with human review workflow
- **Related:** `genreport/core/retrieval/chunk_categorizer.py`

**Base Agent Infrastructure**
- **File:** `2025-10-18-implementing-base-agents.md`
- **Purpose:** Implementation guide for DSPy-based financial agents
- **Sprint:** Sprint 4 Phase 2
- **When to Use:** Creating new market-specific agents or understanding agent architecture
- **Key Topics:**
  - BaseFinancialAgent abstract class
  - Agent lifecycle (validation → retrieval → generation → verification)
  - Market config pattern
  - DSPy module composition
- **Related:** `genreport/core/orchestration/base_agent.py`

**Agentic RAG Integration**
- **File:** `2025-10-24-agentic-rag-integration.md`
- **Purpose:** Complete guide for autonomous ReAct agent implementation
- **Status:** ✅ Production Ready
- **When to Use:** Implementing or extending agentic RAG capabilities
- **Key Topics:**
  - DSPy ReAct pattern integration
  - Tool-based design (search_knowledge_base, search_by_section)
  - Query rewriting and iterative refinement
  - Agent factory updates
- **Related:**
  - Architecture: `docs/architecture/2025-10-23-agentic-rag-react-design.md`
  - Implementation: `genreport/core/orchestration/agentic_rag_agent.py`
  - Demo: `notebooks/04_agentic_rag_demo.py`

#### Knowledge Base & Retrieval

**Full Document Ingestion**
- **File:** `2025-10-22-full-document-ingestion.md`
- **Purpose:** Step-by-step guide for ingesting accounting standards
- **Status:** Ready to Execute
- **Estimated Time:** 10-15 minutes
- **When to Use:** Adding new documents to knowledge base or re-ingesting with new chunking strategy
- **Key Topics:**
  - Embedding generation (Google Gemini 1536-dim)
  - Chunk categorization workflow
  - Database schema and indexes
  - Verification steps
- **Related:** `notebooks/01_kb_ingestion.ipynb`

**SME-FRS Document Structure**
- **File:** `2025-10-23-smefrs-document-structure.md`
- **Purpose:** Comprehensive guide to SME-FRS structure for intelligent retrieval
- **When to Use:** Understanding document organization for structure-aware retrieval
- **Key Topics:**
  - Table of contents hierarchy
  - Section types (requirements, templates, examples)
  - Cross-references between sections
  - Document navigation patterns
- **Related:**
  - Architecture: `docs/architecture/2025-10-22-structure-aware-retrieval.md`
  - Data: `genreport/markets/hk/knowledge_base/smefrs_structure.py`

#### API & Integration

**Export API Usage**
- **File:** `2025-10-20-export-api-usage.md`
- **Purpose:** Guide for using DOCX export API endpoints
- **Sprint:** Sprint 5 - Backend DOCX Export
- **Status:** Production Ready
- **When to Use:** Integrating with report export functionality
- **Key Topics:**
  - Export API endpoints and request format
  - Market-aware template selection (HK/SG/AU)
  - DOCX generation with python-docx
  - Error handling and validation
- **Related:** `genreport/api/routers/export.py`

#### Operations & Production

**Production Deployment**
- **File:** `2025-10-21-production-deployment-guide.md`
- **Version:** 1.0
- **Target Environment:** Production (Hong Kong ap-east-1)
- **When to Use:** Deploying to production or setting up new environments
- **Key Topics:**
  - Ansible-based Infrastructure as Code
  - AWS resource provisioning (ECS, RDS, ElastiCache, S3)
  - Environment variable configuration
  - Database migrations
  - Zero-downtime deployment strategy
- **Prerequisites:**
  - AWS credentials with appropriate permissions
  - Ansible installed locally
  - Secrets configured in AWS Secrets Manager

**Disaster Recovery Runbook**
- **File:** `2025-10-21-disaster-recovery-runbook.md`
- **Version:** 1.0
- **Classification:** CONFIDENTIAL
- **When to Use:** Database corruption, data loss, or system failure scenarios
- **Key Topics:**
  - RTO/RPO targets (15 min / 1 hour)
  - Automated daily backups
  - Point-in-time recovery procedures
  - Database restore steps
  - Rollback procedures
- **Emergency Contacts:** See document for on-call rotation

**Production Launch Checklist**
- **File:** `2025-10-21-production-launch-checklist.md`
- **Version:** 1.0
- **Status:** Pre-Launch
- **When to Use:** Final pre-launch verification
- **Sections:**
  - Infrastructure readiness
  - Security validation
  - Performance benchmarks
  - Monitoring and alerting
  - Documentation completeness
  - Team readiness

**Celery Workers Operations**
- **File:** `2025-10-17-running-celery-workers.md`
- **Version:** 1.0
- **Target Audience:** DevOps, Backend Developers
- **When to Use:** Setting up or troubleshooting asynchronous task processing
- **Key Topics:**
  - Starting workers with proper configuration
  - Monitoring worker health
  - Scaling strategies
  - Troubleshooting common issues
- **Related:** `genreport/core/orchestration/` (Celery tasks)

#### Security & Compliance

**Secrets Management**
- **File:** `2025-10-21-secrets-management-guide.md`
- **Sprint:** 6 Phase 3
- **When to Use:** Managing credentials, API keys, and sensitive configuration
- **Key Topics:**
  - AWS Secrets Manager integration
  - Secret rotation procedures
  - Environment-specific secrets
  - Security best practices
- **Tools:**
  - `scripts/rotate_secrets.py`
  - AWS Secrets Manager console

**Security Scanning**
- **File:** `2025-10-21-security-scanning-guide.md`
- **Sprint:** 6 Phase 2
- **When to Use:** Running automated security audits
- **Key Topics:**
  - Bandit (Python security linter)
  - Safety (dependency vulnerability scanner)
  - OWASP dependency check
  - Automated scanning in CI/CD
- **Tools:**
  - `scripts/security-check.sh`
  - Pre-commit hooks

#### Troubleshooting

**Embedding Dimension Fix**
- **File:** `2025-10-17-embedding-dimension-fix.md`
- **Issue:** Google Gemini embeddings returning 768 dims instead of configured 1536
- **When to Use:** Reference for embedding configuration issues
- **Resolution:** Explicit embedding model specification in LangChain
- **Related:** `genreport/core/retrieval/embedding_service.py`

**LLM Configuration**
- **File:** `2025-10-17-llm-configuration.md`
- **Purpose:** Configuring LLM providers (Gemini & OpenAI)
- **When to Use:** Setting up new environments or switching LLM providers
- **Key Topics:**
  - Environment variable configuration
  - Model selection (Gemini 2.0 Flash, GPT-4o-mini)
  - Cost optimization
  - Fallback strategies
- **Related:** `genreport/core/llm/` (LLM service layer)

---

## Guide Organization

### By Development Phase

**Phase 1: Setup & Configuration**
1. LLM Configuration
2. Celery Workers
3. Secrets Management

**Phase 2: Knowledge Base**
1. Full Document Ingestion
2. SME-FRS Document Structure
3. Chunk Categorizer Implementation

**Phase 3: AI Agents**
1. Base Agent Infrastructure
2. Agentic RAG Integration

**Phase 4: Production**
1. Production Deployment Guide
2. Disaster Recovery Runbook
3. Security Scanning
4. Production Launch Checklist

### By User Role

**Backend Developers:**
- LLM Configuration
- Celery Workers
- Base Agent Infrastructure
- Chunk Categorizer Implementation
- Export API Usage
- Agentic RAG Integration

**DevOps Engineers:**
- Production Deployment Guide
- Disaster Recovery Runbook
- Celery Workers
- Secrets Management
- Security Scanning

**Data Scientists / AI Engineers:**
- Full Document Ingestion
- SME-FRS Document Structure
- Chunk Categorizer Implementation
- Base Agent Infrastructure
- Agentic RAG Integration
- Embedding Dimension Fix

**Security Team:**
- Security Scanning Guide
- Secrets Management Guide
- Disaster Recovery Runbook

---

## Related Documentation

**Architecture:**
- See `docs/architecture/README.md` for design documents and ADRs

**Implementation Reports:**
- See `docs/reports/README.md` for sprint completion and feature implementation reports

**Debugging:**
- See `debugging_journals/` for troubleshooting case studies

**Code Examples:**
- See `notebooks/` for interactive demonstrations and experiments

---

## Contributing

When adding new guides:

1. **Follow naming convention:** `YYYY-MM-DD-topic-description.md`
2. **Include metadata:**
   - Date, Sprint (if applicable), Status
   - Prerequisites and target audience
   - Estimated time for procedures
3. **Structure clearly:**
   - Purpose and when to use
   - Step-by-step instructions
   - Code examples with explanation
   - Troubleshooting section
   - Related files and documentation
4. **Update this README:** Add entry to appropriate category
5. **Cross-reference:** Link to related architecture docs and implementation reports

---

## Document Status

| Guide | Status | Last Updated | Related Code |
|-------|--------|--------------|--------------|
| LLM Configuration | ✅ Active | 2025-10-17 | `genreport/core/llm/` |
| Celery Workers | ✅ Active | 2025-10-17 | Celery tasks |
| Embedding Fix | 📚 Reference | 2025-10-17 | `embedding_service.py` |
| Chunk Categorizer | ✅ Active | 2025-10-18 | `chunk_categorizer.py` |
| Base Agents | ✅ Active | 2025-10-18 | `base_agent.py` |
| Export API | ✅ Active | 2025-10-20 | `routers/export.py` |
| Deployment | ✅ Active | 2025-10-21 | Ansible playbooks |
| Disaster Recovery | ✅ Active | 2025-10-21 | Backup scripts |
| Launch Checklist | 📋 Pre-Launch | 2025-10-21 | N/A |
| Secrets Management | ✅ Active | 2025-10-21 | `scripts/rotate_secrets.py` |
| Security Scanning | ✅ Active | 2025-10-21 | `scripts/security-check.sh` |
| Document Ingestion | ✅ Active | 2025-10-22 | `notebooks/01_kb_ingestion.ipynb` |
| SME-FRS Structure | ✅ Active | 2025-10-23 | `smefrs_structure.py` |
| Agentic RAG | ✅ Active | 2025-10-24 | `agentic_rag_agent.py` |

---

**Maintained by:** Engineering Team
**Last Review:** 2025-10-24
**Next Review:** As needed when new guides are added
