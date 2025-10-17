# Running Celery Workers - Operations Guide

**Date:** 2025-10-17
**Version:** 1.0
**Target Audience:** DevOps, Backend Developers

---

## Quick Start

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery Worker
./scripts/start_celery_worker.sh

# Terminal 3: Start FastAPI
uvicorn genreport.api.main:app --reload
```

---

## Prerequisites

### 1. Redis Installation

**macOS (Homebrew):**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**Docker:**
```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

### 2. Verify Redis is Running
```bash
redis-cli ping
# Expected output: PONG
```

### 3. Python Dependencies
```bash
# Ensure virtual environment is active
source .venv/bin/activate

# Dependencies already in requirements.txt:
# - celery[redis]>=5.3.0
# - redis>=4.5.0
```

---

## Celery Worker Operations

### Starting a Worker

**Development (with auto-reload):**
```bash
./scripts/start_celery_worker.sh
```

**Production:**
```bash
celery -A genreport.core.tasks.celery_app worker \
    --loglevel=info \
    --queues=parsing,default \
    --concurrency=4 \
    --max-tasks-per-child=100 \
    --time-limit=600 \
    --soft-time-limit=540 \
    --logfile=/var/log/celery/worker.log \
    --pidfile=/var/run/celery/worker.pid
```

### Worker Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| `--concurrency` | 2 (dev), 4+ (prod) | Number of worker processes |
| `--max-tasks-per-child` | 100 | Restart worker after N tasks (memory cleanup) |
| `--time-limit` | 600 | Hard timeout (10 minutes) |
| `--soft-time-limit` | 540 | Soft timeout (9 minutes) |
| `--queues` | `parsing,default` | Queues to consume from |
| `--loglevel` | `info` | Logging verbosity |

### Stopping a Worker

**Graceful Shutdown:**
```bash
# Send SIGTERM (allows tasks to complete)
pkill -TERM -f "celery.*worker"
```

**Force Shutdown:**
```bash
# Send SIGKILL (immediate termination)
pkill -KILL -f "celery.*worker"
```

---

## Monitoring & Debugging

### 1. Check Worker Status

**List Active Workers:**
```bash
celery -A genreport.core.tasks.celery_app inspect active
```

**Worker Statistics:**
```bash
celery -A genreport.core.tasks.celery_app inspect stats
```

**Registered Tasks:**
```bash
celery -A genreport.core.tasks.celery_app inspect registered
```

### 2. Monitor Task Queue

**View Pending Tasks:**
```bash
celery -A genreport.core.tasks.celery_app inspect reserved
```

**View Active Tasks:**
```bash
celery -A genreport.core.tasks.celery_app inspect active
```

**View Scheduled Tasks:**
```bash
celery -A genreport.core.tasks.celery_app inspect scheduled
```

### 3. Redis Queue Inspection

**Connect to Redis CLI:**
```bash
redis-cli
```

**Check Queue Lengths:**
```redis
# Default queue
LLEN celery

# Parsing queue
LLEN parsing

# All keys
KEYS *
```

**View Task Details:**
```redis
# List tasks in parsing queue
LRANGE parsing 0 -1

# Get task result
GET celery-task-meta-{task_id}
```

### 4. Flower Monitoring (Optional)

**Install Flower:**
```bash
pip install flower
```

**Start Flower Web UI:**
```bash
celery -A genreport.core.tasks.celery_app flower \
    --port=5555 \
    --broker=redis://localhost:6379/0
```

**Access:** http://localhost:5555

---

## Task Execution

### Manual Task Invocation

**Python:**
```python
from genreport.core.tasks.parsing_tasks import parse_excel_file_task

# Queue task
result = parse_excel_file_task.delay(
    file_id="123e4567-e89b-12d3-a456-426614174000",
    project_id=1,
    tenant_id="987fcdeb-51a2-3b4c-d567-890123456789",
    user_id=1,
)

# Get task ID
print(f"Task ID: {result.id}")

# Check status (non-blocking)
print(f"Status: {result.status}")

# Wait for result (blocking)
try:
    output = result.get(timeout=600)
    print(f"Result: {output}")
except Exception as e:
    print(f"Task failed: {e}")
```

**API:**
```bash
# Trigger parsing via API
curl -X POST http://localhost:8000/api/v1/parsing/projects/1/parse \
  -H "Authorization: Bearer $TOKEN"

# Check status
curl http://localhost:8000/api/v1/parsing/projects/1/status \
  -H "Authorization: Bearer $TOKEN"
```

---

## Task Management

### Revoking Tasks

**Revoke Task (soft):**
```bash
celery -A genreport.core.tasks.celery_app revoke {task_id}
```

**Revoke Task (terminate immediately):**
```bash
celery -A genreport.core.tasks.celery_app revoke {task_id} --terminate
```

### Purging Queue

**Purge All Tasks:**
```bash
celery -A genreport.core.tasks.celery_app purge
```

**Purge Specific Queue:**
```bash
celery -A genreport.core.tasks.celery_app purge -Q parsing
```

---

## Scaling & Performance

### Horizontal Scaling

**Multiple Workers:**
```bash
# Worker 1: Parsing queue only
celery -A genreport.core.tasks.celery_app worker \
    --hostname=worker1@%h \
    --queues=parsing \
    --concurrency=2

# Worker 2: Default queue only
celery -A genreport.core.tasks.celery_app worker \
    --hostname=worker2@%h \
    --queues=default \
    --concurrency=2
```

### Vertical Scaling

**Increase Concurrency:**
```bash
# Auto-scale between 4-16 worker processes
celery -A genreport.core.tasks.celery_app worker \
    --autoscale=16,4
```

### Performance Tuning

**Prefetch Multiplier:**
```python
# celery_app.conf.update()
worker_prefetch_multiplier = 1  # Default (recommended for long tasks)
worker_prefetch_multiplier = 4  # For short tasks
```

**Result Backend:**
```python
# Use Redis for faster result retrieval
result_backend = 'redis://localhost:6379/1'
result_expires = 3600  # Results expire after 1 hour
```

---

## Production Deployment

### Supervisor Configuration

**File:** `/etc/supervisor/conf.d/celery.conf`
```ini
[program:celery-worker]
command=/opt/genreport/.venv/bin/celery -A genreport.core.tasks.celery_app worker --loglevel=info --queues=parsing,default --concurrency=4
directory=/opt/genreport
user=celery
autostart=true
autorestart=true
stopwaitsecs=600
killasgroup=true
priority=998
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker_err.log
```

**Commands:**
```bash
# Reload configuration
sudo supervisorctl reread
sudo supervisorctl update

# Start worker
sudo supervisorctl start celery-worker

# Stop worker
sudo supervisorctl stop celery-worker

# Restart worker
sudo supervisorctl restart celery-worker

# View status
sudo supervisorctl status
```

### Systemd Configuration

**File:** `/etc/systemd/system/celery-worker.service`
```ini
[Unit]
Description=Celery Worker for GenReport
After=network.target redis.service postgresql.service

[Service]
Type=forking
User=celery
Group=celery
WorkingDirectory=/opt/genreport
Environment=PATH=/opt/genreport/.venv/bin:/usr/bin
ExecStart=/opt/genreport/.venv/bin/celery -A genreport.core.tasks.celery_app worker --loglevel=info --queues=parsing,default --concurrency=4 --detach
ExecStop=/bin/kill -TERM $MAINPID
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

**Commands:**
```bash
# Enable service
sudo systemctl enable celery-worker

# Start service
sudo systemctl start celery-worker

# Stop service
sudo systemctl stop celery-worker

# Restart service
sudo systemctl restart celery-worker

# View status
sudo systemctl status celery-worker

# View logs
sudo journalctl -u celery-worker -f
```

---

## Troubleshooting

### Problem: Worker Not Starting

**Symptoms:**
```
Error: Could not connect to broker
```

**Solution:**
```bash
# 1. Check Redis is running
redis-cli ping

# 2. Check Redis URL in environment
echo $REDIS_URL

# 3. Test Redis connection
redis-cli -u redis://localhost:6379/0 ping
```

### Problem: Tasks Stuck in Queue

**Symptoms:**
- Tasks remain in "PENDING" state
- Workers show 0 active tasks

**Solution:**
```bash
# 1. Check worker is consuming from correct queue
celery -A genreport.core.tasks.celery_app inspect active_queues

# 2. Check task routing
celery -A genreport.core.tasks.celery_app inspect registered

# 3. Restart worker
pkill -TERM -f "celery.*worker" && ./scripts/start_celery_worker.sh
```

### Problem: High Memory Usage

**Symptoms:**
- Worker process grows >2GB
- System becomes slow

**Solution:**
```bash
# 1. Reduce max-tasks-per-child
--max-tasks-per-child=50  # Default is 100

# 2. Reduce concurrency
--concurrency=2  # Default is 4

# 3. Enable worker restart
# Workers automatically restart after N tasks
```

### Problem: Task Timeout

**Symptoms:**
```
SoftTimeLimitExceeded: Task exceeded soft time limit (540s)
```

**Solution:**
```bash
# 1. Increase time limits
--soft-time-limit=900
--time-limit=1000

# 2. Optimize task code (see Sprint 7 performance guide)

# 3. Split large tasks into smaller subtasks
```

---

## Security Considerations

### 1. Redis Security

**Bind to Localhost Only:**
```bash
# redis.conf
bind 127.0.0.1 ::1
```

**Enable Authentication:**
```bash
# redis.conf
requirepass your_strong_password

# Update REDIS_URL
REDIS_URL=redis://:your_strong_password@localhost:6379/0
```

### 2. Worker Permissions

**Run as Dedicated User:**
```bash
# Create celery user
sudo useradd -r -s /bin/false celery

# Set file permissions
sudo chown -R celery:celery /opt/genreport
sudo chmod 750 /opt/genreport
```

### 3. Sensitive Data

**Environment Variables:**
- Never log REDIS_URL, DATABASE_URL
- Use secrets management (AWS Secrets Manager, Vault)
- Rotate credentials regularly

**Task Arguments:**
- Use IDs, not sensitive data
- Audit all task executions
- Encrypt results if needed

---

## Monitoring & Alerting

### Key Metrics to Monitor

| Metric | Threshold | Action |
|--------|-----------|--------|
| Queue Length | >100 | Scale workers |
| Task Failure Rate | >5% | Investigate errors |
| Worker Memory | >2GB | Restart worker |
| Task Duration | >300s | Optimize code |
| Redis Memory | >80% | Increase Redis memory |

### Log Aggregation

**Recommended Tools:**
- **ELK Stack**: Elasticsearch + Logstash + Kibana
- **Datadog**: Application monitoring
- **Sentry**: Error tracking
- **CloudWatch**: AWS logging

**Log Format:**
```json
{
  "timestamp": "2025-10-17T10:00:00Z",
  "level": "INFO",
  "task_id": "abc123",
  "task_name": "parse_excel_file_task",
  "status": "SUCCESS",
  "duration": 45.2,
  "tenant_id": "uuid",
  "project_id": 1
}
```

---

## Appendix

### Useful Commands Cheat Sheet

```bash
# Worker management
celery -A genreport.core.tasks.celery_app worker --help
celery -A genreport.core.tasks.celery_app inspect --help
celery -A genreport.core.tasks.celery_app control --help

# Queue management
celery -A genreport.core.tasks.celery_app purge
celery -A genreport.core.tasks.celery_app inspect reserved

# Monitoring
celery -A genreport.core.tasks.celery_app events
celery -A genreport.core.tasks.celery_app status

# Beat scheduler (future use)
celery -A genreport.core.tasks.celery_app beat
```

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@localhost/genreport
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=<generated>
JWT_SECRET_KEY=<generated>
ENCRYPTION_KEY=<generated>

# Optional
CELERY_BROKER_URL=$REDIS_URL  # Defaults to REDIS_URL
CELERY_RESULT_BACKEND=$REDIS_URL  # Defaults to REDIS_URL
CELERY_TASK_SERIALIZER=json
CELERY_RESULT_SERIALIZER=json
```

---

**Document Version:** 1.0
**Last Updated:** 2025-10-17
**Maintained By:** DevOps Team
**Next Review:** Sprint 4
