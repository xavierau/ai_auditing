# Security Scanning Guide
**Date:** 2025-10-21
**Sprint:** 6 Phase 2
**Purpose:** Guide for running automated security scans

---

## Overview

This guide covers the automated security scanning tools integrated into the GenReport project to continuously monitor for vulnerabilities in dependencies and code.

---

## Security Scanning Tools

### 1. pip-audit (Python Dependency Vulnerabilities)

**Purpose:** Scans Python dependencies for known security vulnerabilities

**Installation:**
```bash
source .venv/bin/activate
pip install pip-audit
```

**Usage:**
```bash
# Scan current environment
pip-audit

# Scan requirements.txt
pip-audit --requirement requirements.txt

# Output JSON report
pip-audit --requirement requirements.txt --format json --output pip-audit-report.json

# Fix vulnerabilities automatically (caution!)
pip-audit --fix
```

**Example Output:**
```
Found 2 known vulnerabilities in 1 package
Name    Version ID             Fix Versions
------- ------- -------------- ------------
cryptography 39.0.0  GHSA-xxx  40.0.0
```

**Severity Levels:**
- 🔴 **Critical:** Immediate action required
- 🟠 **High:** Address within 7 days
- 🟡 **Medium:** Address within 30 days
- 🟢 **Low:** Address when convenient

**Action:**
- Review each vulnerability
- Update dependencies: `uv pip install --upgrade <package>`
- Test after updates: `pytest`

---

### 2. Bandit (Python Code Security Linter)

**Purpose:** Analyzes Python code for common security issues

**Installation:**
```bash
source .venv/bin/activate
pip install bandit[toml]
```

**Usage:**
```bash
# Scan entire project
bandit -r genreport/

# Medium and high severity only
bandit -r genreport/ -ll

# Output JSON report
bandit -r genreport/ -f json -o bandit-report.json

# Exclude test files
bandit -r genreport/ --exclude genreport/tests/
```

**Common Issues Detected:**
- B105: Hardcoded password strings
- B201: Flask debug mode enabled
- B301: Pickle usage (unsafe deserialization)
- B303: Use of insecure MD5/SHA1 hashing
- B501: Certificate validation disabled
- B608: SQL injection via raw SQL

**Example Output:**
```
Issue: [B105:hardcoded_password_string] Possible hardcoded password: 'secret123'
Severity: High   Confidence: Medium
Location: genreport/core/auth.py:42
```

**Action:**
- Review each HIGH severity finding
- Fix issues or add `# nosec` comment with justification
- Re-run Bandit after fixes

**Configuration:**
Create `.bandit` file to customize:
```yaml
exclude_dirs:
  - /tests/
  - /venv/

skips:
  - B101  # Skip assert_used (OK in tests)
```

---

### 3. Safety (Alternative Dependency Scanner)

**Purpose:** Checks Python dependencies against Safety DB

**Installation:**
```bash
source .venv/bin/activate
pip install safety
```

**Usage:**
```bash
# Scan current environment
safety check

# Scan requirements.txt
safety check --file requirements.txt

# Output JSON report
safety check --json --output safety-report.json

# Ignore specific vulnerabilities
safety check --ignore 12345
```

**Example Output:**
```
+==============================================================================+
|                                                                              |
|                               /$$$$$$            /$$                         |
|                              /$$__  $$          | $$                         |
|           /$$$$$$$  /$$$$$$ | $$  \__//$$$$$$  /$$$$$$   /$$   /$$           |
|          /$$_____/ |____  $$| $$$$   /$$__  $$|_  $$_/  | $$  | $$           |
|         |  $$$$$$   /$$$$$$$| $$_/  | $$$$$$$$  | $$    | $$  | $$           |
|          \____  $$ /$$__  $$| $$    | $$_____/  | $$ /$$| $$  | $$           |
|          /$$$$$$$/|  $$$$$$$| $$    |  $$$$$$$  |  $$$$/|  $$$$$$$           |
|         |_______/  \_______/|__/     \_______/   \___/   \____  $$           |
|                                                           /$$  | $$           |
|                                                          |  $$$$$$/           |
|  by pyup.io                                              \______/            |
|                                                                              |
+==============================================================================+
| REPORT                                                                       |
+==============================================================================+
| Safety v2.0 is scanning 42 packages for known security vulnerabilities.     |
+==============================================================================+
| -> requests (2.27.0) - CVE-2023-32681 (HIGH)                                |
|    Affects versions: < 2.31.0                                               |
|    Fix: Upgrade to 2.31.0 or later                                          |
+==============================================================================+
```

---

### 4. npm audit (Frontend Dependency Vulnerabilities)

**Purpose:** Scans npm/yarn dependencies for vulnerabilities

**Usage:**
```bash
cd frontend

# Scan dependencies
npm audit

# Moderate severity and above
npm audit --audit-level=moderate

# Fix vulnerabilities automatically
npm audit fix

# Fix with breaking changes (caution!)
npm audit fix --force

# Output JSON report
npm audit --json > npm-audit-report.json
```

**Example Output:**
```
found 3 vulnerabilities (2 moderate, 1 high)
  run `npm audit fix` to fix 2 of them
  1 vulnerability requires manual review

High: Prototype Pollution
Package: lodash
Dependency of: react-scripts
Path: react-scripts > lodash
More info: https://npmjs.com/advisories/1523
```

**Action:**
- Run `npm audit fix` for automatic fixes
- Review manual fixes required
- Test thoroughly after updates

---

### 5. Trivy (Docker/Container Security)

**Purpose:** Scans Docker images and filesystems for vulnerabilities

**Installation:**
```bash
# macOS
brew install aquasecurity/trivy/trivy

# Linux
wget https://github.com/aquasecurity/trivy/releases/download/v0.45.0/trivy_0.45.0_Linux-64bit.deb
sudo dpkg -i trivy_0.45.0_Linux-64bit.deb
```

**Usage:**
```bash
# Scan filesystem
trivy fs .

# Scan Docker image
trivy image genreport:latest

# Critical and high only
trivy fs . --severity CRITICAL,HIGH

# Output JSON report
trivy fs . --format json --output trivy-report.json
```

**Example Output:**
```
Total: 5 (CRITICAL: 2, HIGH: 3)

┌───────────────┬────────────────┬──────────┬────────┬───────────────────┬───────────────┐
│   Library     │ Vulnerability  │ Severity │ Status │ Installed Version │ Fixed Version │
├───────────────┼────────────────┼──────────┼────────┼───────────────────┼───────────────┤
│ openssl       │ CVE-2023-12345 │ CRITICAL │  fixed │ 1.1.1             │ 1.1.1w        │
│ zlib          │ CVE-2023-67890 │ HIGH     │  fixed │ 1.2.11            │ 1.2.13        │
└───────────────┴────────────────┴──────────┴────────┴───────────────────┴───────────────┘
```

---

## CI/CD Integration

### GitHub Actions Workflow

The security scanning workflow runs automatically:

**Triggers:**
- ✅ Push to `main`, `develop`, or `feature/**` branches
- ✅ Pull requests to `main` or `develop`
- ✅ Weekly schedule (Sundays at midnight UTC)
- ✅ Manual trigger via GitHub UI

**Jobs:**
1. **python-security** - pip-audit, Bandit, Safety
2. **frontend-security** - npm audit (if frontend exists)
3. **docker-security** - Trivy scan (if Dockerfile exists)
4. **security-test-suite** - OWASP Top 10 tests
5. **security-summary** - Consolidated report

**Viewing Results:**
1. Go to GitHub → Actions tab
2. Click on "Security Scan" workflow
3. View job results and download artifacts

**Artifacts Generated:**
- `python-security-reports/pip-audit-report.json`
- `python-security-reports/bandit-report.json`
- `python-security-reports/safety-report.json`
- `frontend-security-reports/npm-audit-report.json`
- `trivy-security-report/trivy-results.sarif`

---

## Manual Security Scans

### Quick Security Check

Run all scans locally before committing:

```bash
#!/bin/bash
# scripts/security-check.sh

echo "Running security scans..."

# Python dependency scan
echo "1/4 - pip-audit..."
source .venv/bin/activate
pip-audit --requirement requirements.txt || true

# Python code scan
echo "2/4 - Bandit..."
bandit -r genreport/ -ll || true

# Frontend scan (if exists)
if [ -d "frontend" ]; then
  echo "3/4 - npm audit..."
  cd frontend && npm audit --audit-level=moderate || true
  cd ..
fi

# Security tests
echo "4/4 - OWASP tests..."
pytest tests/security/test_owasp_top10.py -v

echo "Security scans complete!"
```

**Usage:**
```bash
chmod +x scripts/security-check.sh
./scripts/security-check.sh
```

---

## Security Scan Schedule

### Recommended Schedule

| Scan Type | Frequency | Trigger |
|-----------|-----------|---------|
| pip-audit | Weekly | Automated (CI/CD) |
| Bandit | On every PR | Automated (CI/CD) |
| Safety | Weekly | Automated (CI/CD) |
| npm audit | Weekly | Automated (CI/CD) |
| Trivy | Weekly | Automated (CI/CD) |
| OWASP Tests | On every PR | Automated (CI/CD) |
| Manual Review | Monthly | Security team |
| Penetration Test | Quarterly | External firm |

---

## Handling Security Findings

### Response Workflow

1. **Triage (Within 24 hours)**
   - Review severity and exploitability
   - Determine if it affects production
   - Assign owner

2. **Remediation Timeline**
   - Critical: 24-48 hours
   - High: 7 days
   - Medium: 30 days
   - Low: 90 days or next release

3. **Fix Process**
   - Update dependency or patch code
   - Run tests: `pytest`
   - Re-run security scan to verify fix
   - Document in changelog

4. **Verification**
   - Run security scans again
   - Verify vulnerability is resolved
   - Update ticket/issue

### Example: Fixing Critical Vulnerability

```bash
# 1. Identify vulnerability
pip-audit --requirement requirements.txt

# Output: cryptography 39.0.0 has CVE-2023-12345 (CRITICAL)

# 2. Update dependency
uv pip install --upgrade cryptography

# 3. Verify fix
pip-audit --requirement requirements.txt

# 4. Test application
pytest

# 5. Update requirements
pip freeze > requirements.txt

# 6. Commit and deploy
git add requirements.txt
git commit -m "security: Update cryptography to fix CVE-2023-12345"
git push
```

---

## Suppressing False Positives

### Bandit False Positives

Use `# nosec` comment with justification:

```python
# SAFE: Using hardcoded test credentials only in test environment
test_password = "test123"  # nosec B105
```

### pip-audit Ignore

Create `.pip-audit-ignore.toml`:

```toml
[[tool.pip-audit.ignores]]
vulnerability-id = "GHSA-xxxx-yyyy-zzzz"
reason = "Not exploitable in our use case - we don't use affected feature"
expires = "2025-12-31"
```

### npm audit Ignore

```bash
# Temporarily ignore specific advisory
npm audit --audit-level=moderate --omit=dev
```

---

## Security Reporting

### Monthly Security Report Template

```markdown
# Monthly Security Report - [Month] 2025

## Scan Summary
- pip-audit: X vulnerabilities found (Y critical, Z high)
- Bandit: X issues found (Y high severity)
- npm audit: X vulnerabilities found
- Trivy: X CVEs found

## Actions Taken
1. Updated dependency X from v1.0 to v2.0 (fixed CVE-2023-12345)
2. Patched code in file.py to address Bandit issue B501
3. Deferred fix for low-severity finding (documented reason)

## Outstanding Issues
| Severity | Count | Status |
|----------|-------|--------|
| Critical | 0     | ✅     |
| High     | 1     | 🔄 In Progress |
| Medium   | 3     | 📋 Planned |
| Low      | 5     | ⏰ Backlog |

## Recommendations
1. Schedule penetration test for Q2
2. Review rate limiting implementation
3. Update SSL/TLS configuration

## Next Actions
- [ ] Fix remaining HIGH severity finding by [date]
- [ ] Update Python to 3.13.3 when released
- [ ] Review AWS Security Hub findings
```

---

## Best Practices

### 1. Keep Dependencies Updated
```bash
# Weekly: Check for updates
pip list --outdated

# Update strategically (not blindly)
uv pip install --upgrade <package>

# Test after updates
pytest
```

### 2. Review Before Merging
- All PRs must pass security scans
- Review security warnings in CI/CD logs
- Don't ignore security failures

### 3. Monitor Continuously
- Enable GitHub Dependabot alerts
- Subscribe to security mailing lists
- Follow CVE databases for used libraries

### 4. Document Decisions
- Document why vulnerabilities are suppressed
- Track remediation status in tickets
- Maintain security changelog

### 5. Secure by Default
- Use latest stable versions
- Enable security features by default
- Follow principle of least privilege

---

## Troubleshooting

### pip-audit: No vulnerabilities database

**Error:** `Unable to load vulnerability database`

**Fix:**
```bash
# Update pip-audit
pip install --upgrade pip-audit

# Clear cache
pip cache purge

# Re-run
pip-audit
```

### Bandit: Too many false positives

**Solution:** Configure `.bandit` to skip specific checks:
```yaml
skips:
  - B101  # assert_used
  - B601  # paramiko_calls
```

### npm audit: Unfixable vulnerabilities

**Solution:**
```bash
# Check if devDependency (lower risk)
npm audit --production

# Override resolution (package.json)
{
  "overrides": {
    "vulnerable-package": "^2.0.0"
  }
}
```

---

## Resources

### Documentation
- [pip-audit docs](https://github.com/pypa/pip-audit)
- [Bandit docs](https://bandit.readthedocs.io/)
- [Safety docs](https://docs.pyup.io/docs/safety-20-introduction)
- [npm audit docs](https://docs.npmjs.com/cli/v8/commands/npm-audit)
- [Trivy docs](https://aquasecurity.github.io/trivy/)

### Vulnerability Databases
- [National Vulnerability Database (NVD)](https://nvd.nist.gov/)
- [GitHub Advisory Database](https://github.com/advisories)
- [PyPI Advisory Database](https://github.com/pypa/advisory-database)
- [npm Security Advisories](https://www.npmjs.com/advisories)

### Tools
- [OWASP Dependency-Check](https://owasp.org/www-project-dependency-check/)
- [Snyk](https://snyk.io/)
- [WhiteSource](https://www.whitesourcesoftware.com/)

---

## Appendix: Security Scan Checklist

### Pre-Deployment Checklist

- [ ] Run all security scans locally
- [ ] All CRITICAL and HIGH findings addressed
- [ ] Security test suite passing (22/22 tests)
- [ ] Dependencies up to date
- [ ] Secrets not in code (use env vars)
- [ ] Debug mode disabled in production
- [ ] Error messages don't leak info
- [ ] Rate limiting configured
- [ ] Audit logging enabled
- [ ] Backup and recovery tested

---

**Document Version:** 1.0
**Last Updated:** 2025-10-21
**Maintained By:** Security Team
**Review Frequency:** Quarterly
