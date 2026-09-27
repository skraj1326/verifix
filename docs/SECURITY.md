# Security Model

## Threat Model

### Assets to Protect
1. **RTL/IP Code** - Highly confidential semiconductor designs
2. **Verification Plans** - Proprietary verification strategies
3. **Simulation Results** - May reveal design behavior/bugs
4. **Coverage Data** - Reveals design structure and testing gaps
5. **User Credentials** - Authentication tokens

### Threat Actors
- External attackers
- Malicious insiders
- Compromised dependencies
- AI model providers (if using cloud LLMs)

### Attack Vectors
1. **Code Injection** - Malicious RTL/testbench causing RCE
2. **Data Exfiltration** - RTL uploaded to external AI APIs
3. **Privilege Escalation** - Container escape from simulation sandbox
4. **Supply Chain** - Compromised dependencies
5. **Side Channels** - Timing/power analysis

## Security Controls

### 1. Data Isolation

```python
# Project-scoped database access
async def get_user_projects(user_id: str):
    return await db.query(Project).filter(Project.owner_id == user_id).all()

# All queries include project_id filter
async def get_designs(project_id: str, user_id: str):
    project = await get_project(project_id)
    if project.owner_id != user_id:
        raise PermissionError("Access denied")
    return await db.query(Design).filter(Design.project_id == project_id).all()
```

### 2. Sandboxed Simulation

```yaml
# Docker security configuration
services:
  simulation-runner:
    image: verilator-sandbox:latest
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    cap_drop:
      - ALL
    network_mode: "none"
    mem_limit: 4g
    cpus: "2"
    pids_limit: 100
    ulimits:
      nproc: 64
      nofile:
        soft: 1024
        hard: 1024
```

### 3. AI Tool Permissions

```python
# Tool permission matrix
TOOL_PERMISSIONS = {
    "read_file": ["viewer", "engineer", "admin"],
    "write_file": ["engineer", "admin"],
    "execute_command": ["engineer", "admin"],
    "run_simulation": ["engineer", "admin"],
    "delete_file": ["admin"],
    "modify_rtl": ["admin"],  # Requires explicit approval
}

# Every tool call validated
async def execute_tool(tool_name: str, args: dict, user: User):
    if not has_permission(user, tool_name):
        raise PermissionError(f"User {user.id} lacks permission for {tool_name}")
    
    if tool_name in REQUIRES_APPROVAL:
        if not await get_approval(user, tool_name, args):
            raise PermissionError("Approval required")
    
    return await TOOLS[tool_name].execute(args)
```

### 4. LLM Data Protection

```python
# On-premise deployment option
LLM_PROVIDER = "local"  # Use local model
LLM_BASE_URL = "http://local-llm:8000/v1"
LLM_API_KEY = "not-needed"

# Cloud with data processing agreement
LLM_PROVIDER = "anthropic"
LLM_API_KEY = "encrypted-in-vault"
# Ensure contract prohibits training on customer data

# Offline mode (no external calls)
LLM_API_KEY = ""  # Empty = offline mode
```

### 5. Audit Logging

```python
# All significant actions logged
audit_log = AuditLog(
    timestamp=datetime.utcnow(),
    action="simulation_run",
    resource_type="project",
    resource_id=project_id,
    details={
        "user_id": user_id,
        "simulator": "verilator",
        "test_count": 15,
        "duration_seconds": 45
    },
    user_id=user_id,
    ip_address=request.client.host
)
db.add(audit_log)
```

### 6. Secrets Management

```bash
# Use environment variables or secret manager
# .env file (gitignored)
DATABASE_URL=postgresql://user:${DB_PASSWORD}@localhost/db
LLM_API_KEY=${OPENAI_API_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# Production: HashiCorp Vault / AWS Secrets Manager / Azure Key Vault
```

### 7. Container Security

```dockerfile
# Dockerfile security
FROM python:3.11-slim

# Non-root user
RUN groupadd -r verifix && useradd -r -g verifix verifix
USER verifix

# Read-only filesystem
# No package installation at runtime
# Minimal base image
```

### 8. Network Security

```python
# CORS configuration
CORS_ORIGINS = [
    "https://verifix.company.com",
    "http://localhost:3000"  # Dev only
]

# Rate limiting
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    # Implement rate limiting per IP/project
    pass
```

## Compliance

### SOC 2 Type II
- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- Access logging
- Incident response plan

### GDPR/CCPA
- Data minimization
- Right to deletion
- Data portability
- Privacy by design

### Export Control (ITAR/EAR)
- On-premise deployment option
- No data leaves customer network
- Audit trail for all access

## Incident Response

1. **Detection**: Audit log alerts, anomaly detection
2. **Containment**: Revoke tokens, isolate project
3. **Investigation**: Log analysis, forensic imaging
4. **Recovery**: Restore from backup, rotate secrets
5. **Lessons Learned**: Post-incident review

## Security Checklist

- [ ] All API endpoints require authentication
- [ ] Project-scoped data access enforced
- [ ] Simulations run in isolated containers
- [ ] AI tools require explicit permissions
- [ ] No hardcoded secrets in code
- [ ] Audit logging enabled for all actions
- [ ] Dependencies scanned for vulnerabilities
- [ ] Regular penetration testing
- [ ] Incident response plan documented
- [ ] Data processing agreements with AI providers