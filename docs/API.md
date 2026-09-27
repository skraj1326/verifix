# API Reference

Base URL: `http://localhost:8000/api/v1`

## Authentication

Currently, the API uses project-scoped access. JWT authentication will be added in a future release.

## Projects

### Create Project
```http
POST /projects/
Content-Type: application/json

{
  "name": "My Verification Project",
  "description": "Verification of FIFO design"
}
```

Response:
```json
{
  "id": "uuid",
  "name": "My Verification Project",
  "description": "Verification of FIFO design",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### List Projects
```http
GET /projects/
```

### Get Project
```http
GET /projects/{project_id}
```

### Get Project Summary
```http
GET /projects/{project_id}/summary
```

### Delete Project
```http
DELETE /projects/{project_id}
```

## RTL Analysis

### Analyze RTL
```http
POST /rtl/analyze
Content-Type: application/json

{
  "content": "module fifo...",
  "filename": "fifo.sv"
}
```

Response includes:
- Parsed modules with ports, signals, FSMs
- Design summary
- Knowledge graph
- Verification recommendations

### Upload RTL File
```http
POST /rtl/upload
Content-Type: multipart/form-data

file: [binary]
```

## Specification Analysis

### Analyze Specification
```http
POST /spec/analyze
Content-Type: application/json

{
  "content": "# FIFO Specification\n\n## Requirements\n\nREQ-001: The FIFO shall not allow write when full...",
  "filename": "fifo_spec.md",
  "doc_type": "markdown"
}
```

### Upload Specification File
```http
POST /spec/upload
Content-Type: multipart/form-data

file: [binary]
```

## Verification

### Generate Verification Plan
```http
POST /verification/plan
Content-Type: application/json

{
  "rtl_content": "module fifo...",
  "specification": "FIFO specification text..."
}
```

### Generate Assertions
```http
POST /verification/assertions
Content-Type: application/json

{
  "rtl_content": "module fifo..."
}
```

### Generate Tests
```http
POST /verification/tests
Content-Type: application/json

{
  "rtl_content": "module fifo...",
  "coverage_gaps": [...],
  "test_types": ["directed", "constrained_random"]
}
```

### Full Verification Flow
```http
POST /verification/full-flow
Content-Type: application/json

{
  "rtl_content": "module fifo...",
  "specification": "FIFO specification..."
}
```

## Simulation

### Compile RTL
```http
POST /simulation/compile
Content-Type: application/json

{
  "rtl_files": ["rtl/fifo.sv"],
  "testbench": "module tb...",
  "top_module": "tb",
  "simulator": "verilator",
  "timeout": 300
}
```

### Run Simulation
```http
POST /simulation/run
Content-Type: application/json

{
  "rtl_content": "module fifo...",
  "test_code": "module tb...",
  "top_module": "tb",
  "simulator": "verilator"
}
```

### Analyze Simulation Log
```http
POST /simulation/analyze-log
Content-Type: application/json

{
  "log_content": "simulation log text...",
  "log_type": "simulation"
}
```

## Coverage

### Analyze Coverage
```http
POST /coverage/analyze
Content-Type: application/json

{
  "coverage_report": "Verilator XML or text output...",
  "rtl_content": "module fifo...",
  "module_name": "fifo_sync"
}
```

### Identify Gaps
```http
POST /coverage/gaps
Content-Type: application/json

{
  "coverage_report": "Verilator XML...",
  "rtl_content": "module fifo...",
  "module_name": "fifo_sync"
}
```

### Generate Targeted Tests
```http
POST /coverage/generate-targeted-tests
Content-Type: application/json

{
  "coverage_report": "Verilator XML...",
  "rtl_content": "module fifo...",
  "module_name": "fifo_sync"
}
```

### Compare Coverage
```http
POST /coverage/compare
Content-Type: application/json

{
  "coverage_before": {"line": {"overall": 80, "covered": 80, "total": 100}},
  "coverage_after": {"line": {"overall": 90, "covered": 90, "total": 100}}
}
```

## Analysis

### Failure Analysis
```http
POST /failure-analysis
Content-Type: application/json

{
  "failure_info": {"type": "assertion", "message": "..."},
  "rtl_content": "module fifo...",
  "log_analysis": {...},
  "use_ai": true
}
```

### Regression Analysis
```http
POST /regression/analyze
Content-Type: application/json

{
  "results": [
    {"name": "test1", "status": "passed", "runtime_seconds": 10},
    {"name": "test2", "status": "failed", "runtime_seconds": 5}
  ],
  "changed_modules": ["fifo_sync"],
  "budget_minutes": 60
}
```

### Waveform Analysis
```http
POST /waveform/analyze
Content-Type: application/json

{
  "vcd_content": "$date...$end..."
}
```

### Signal Context Around Failure
```http
POST /waveform/signal-context
Content-Type: application/json

{
  "vcd_content": "...",
  "failure_time": 12500,
  "window": 100
}
```

## AI Agents

### AI Status
```http
GET /ai/status
```

### Analyze Design
```http
POST /ai/analyze-design
Content-Type: application/json

{
  "rtl_content": "module fifo...",
  "parsed_modules": [...]
}
```

### Improve Test
```http
POST /ai/improve-test
Content-Type: application/json

{
  "test_code": "module tb...",
  "failure_info": "Assertion failed...",
  "rtl_content": "module fifo..."
}
```

### Analyze Coverage Gap
```http
POST /ai/analyze-gap
Content-Type: application/json

{
  "gap_info": {"gap_type": "reachable_untested", "description": "..."},
  "rtl_content": "module fifo..."
}
```

### Assess Reachability
```http
POST /ai/assess-reachability
Content-Type: application/json

{
  "gap_info": {"gap_type": "potentially_unreachable", "description": "..."},
  "rtl_content": "module fifo..."
}
```

## WebSocket

Connect to `/ws` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log(msg.type, msg.data);
};

// Event types:
// - progress: { phase, current, total }
// - log: { level, message }
// - simulation_complete: { simulation_id, status }
// - coverage_update: { coverage: {...} }
// - failure_detected: { failure: {...} }
// - gap_found: { gap: {...} }
```

## Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error description",
  "status_code": 400
}
```

Common status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Internal Server Error