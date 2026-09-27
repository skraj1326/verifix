# Development Guide

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 16 (or use Docker)
- Redis 7 (or use Docker)
- Verilator & Icarus Verilog (in Docker)

## Quick Start

```bash
# Clone
git clone <repo>
cd verifix

# Start all services
docker compose -f docker/docker-compose.yml up --build

# Or develop locally:
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env with your settings
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Project Structure

```
verifix/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   ├── core/            # Config, DB, security
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   ├── engines/         # Verification engines
│   │   ├── ai/              # AI agents
│   │   └── utils/
│   ├── tests/
│   ├── alembic/             # Migrations
│   └── Dockerfile
├── frontend/
│   ├── app/                 # Next.js pages
│   ├── components/          # React components
│   ├── lib/                 # Utilities
│   └── Dockerfile
├── examples/                # Demo RTL
├── docker/                  # Docker Compose
└── docs/
```

## Running Tests

```bash
# Backend tests
cd backend
pytest app/tests/ -v --cov=app

# Specific test
pytest app/tests/e2e/test_fifo_demo.py -v

# Frontend tests
cd frontend
npm test
npm run lint
```

## Code Style

### Python
```bash
# Format
black backend/app

# Lint
ruff backend/app

# Type check
mypy backend/app
```

### TypeScript/React
```bash
# Format
npm run format

# Lint
npm run lint
```

## Adding a New Engine

1. Create engine directory:
```bash
mkdir -p backend/app/engines/my_engine
```

2. Create engine module:
```python
# backend/app/engines/my_engine/engine.py
class MyEngine:
    def process(self, input_data):
        # Implementation
        return result
```

3. Add `__init__.py`:
```python
from .engine import MyEngine
__all__ = ["MyEngine"]
```

4. Register in VerificationService:
```python
# backend/app/services/verification_service.py
from app.engines.my_engine import MyEngine

class VerificationService:
    def __init__(self):
        self.my_engine = MyEngine()
```

5. Add API endpoint if needed:
```python
# backend/app/api/v1/my_engine.py
from fastapi import APIRouter
router = APIRouter(prefix="/my-engine")

@router.post("/process")
async def process(...):
    return service.my_engine.process(...)
```

6. Register router in main.py:
```python
from app.api.v1 import my_engine
app.include_router(my_engine.router, prefix=API_PREFIX, tags=["My Engine"])
```

## Adding a New AI Agent

1. Create agent class:
```python
# backend/app/ai/agents/my_agent.py
from app.ai.agents.base import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__("my_agent")
    
    async def run(self, **kwargs) -> dict:
        # Use self.llm for LLM calls
        # Use self.tools for tool calls
        pass
```

2. Register tool if needed:
```python
# backend/app/ai/tools/registry.py
from app.ai.tools.registry import tool_registry

@tool_registry.register("my_tool", permissions=["read"])
async def my_tool(arg1: str) -> dict:
    return {"result": "..."}
```

3. Add to orchestrator:
```python
# backend/app/ai/orchestrator/orchestrator.py
from app.ai.agents.my_agent import MyAgent

class AgentOrchestrator:
    def __init__(self):
        self.agents = {
            "my_agent": MyAgent(),
            # ...
        }
```

## Database Migrations

```bash
# Create migration
cd backend
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Adding a New API Endpoint

1. Create schema:
```python
# backend/app/schemas/schemas.py
class MyRequest(BaseModel):
    field: str

class MyResponse(BaseModel):
    result: str
```

2. Create endpoint:
```python
# backend/app/api/v1/my_feature.py
from fastapi import APIRouter
from app.schemas.schemas import MyRequest, MyResponse

router = APIRouter(prefix="/my-feature")

@router.post("/action", response_model=MyResponse)
async def my_action(request: MyRequest):
    return MyResponse(result="done")
```

3. Register in main.py

## Frontend Development

### Adding a New Page

```bash
# Create page
mkdir -p frontend/app/my-page
# Create page.tsx
```

### Using the API Client

```typescript
// frontend/lib/api.ts
import { api } from "@/lib/api";

const response = await api.post("/verification/plan", {
  rtl_content: "...",
  specification: "..."
});
```

### Adding a Component

```tsx
// frontend/components/my-component/MyComponent.tsx
"use client";
import { cn } from "@/lib/utils";

export function MyComponent({ className, ...props }) {
  return <div className={cn("base-styles", className)} {...props} />;
}
```

## Debugging

### Backend
```bash
# With VS Code
# .vscode/launch.json
{
  "type": "python",
  "request": "launch",
  "name": "FastAPI",
  "module": "uvicorn",
  "args": ["app.main:app", "--reload"]
}
```

### Frontend
```bash
# Next.js dev tools
npm run dev
# Open http://localhost:3000
# Use React DevTools
```

### Simulation Debugging
```bash
# Run simulation manually
cd /tmp
verilator --trace --cc ../rtl/fifo.sv ../tb/tb_fifo.sv
make -C obj_dir -f Vtb_fifo.mk Vtb_fifo
./obj_dir/Vtb_fifo
gtkwave waveform.vcd
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Async PostgreSQL URL | `postgresql+asyncpg://verifix:verifix@localhost:5432/verifix` |
| `DATABASE_SYNC_URL` | Sync PostgreSQL URL | `postgresql://verifix:verifix@localhost:5432/verifix` |
| `REDIS_URL` | Redis URL | `redis://localhost:6379/0` |
| `LLM_PROVIDER` | openai/anthropic/local | `openai` |
| `LLM_API_KEY` | API key for LLM | `` |
| `LLM_MODEL` | Model name | `gpt-4o` |
| `VERILATOR_PATH` | Verilator executable | `verilator` |
| `SIMULATION_TIMEOUT` | Seconds | `300` |
| `DEBUG` | Debug mode | `false` |

## Troubleshooting

### Database Connection Failed
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check connection
psql postgresql://verifix:verifix@localhost:5432/verifix
```

### Verilator Not Found
```bash
# In Docker (already installed)
# Local Ubuntu:
apt-get install verilator
# macOS:
brew install verilator
```

### Frontend Build Fails
```bash
cd frontend
rm -rf node_modules .next
npm install
npm run build
```

### Tests Fail
```bash
# Check test database
cd backend
alembic upgrade head  # Ensure migrations applied
pytest app/tests/ -v -x  # Stop on first failure
```

## CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: cd backend && pip install -r requirements.txt
      - run: cd backend && pytest
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd frontend && npm ci
      - run: cd frontend && npm run lint && npm run build
```

## Performance Tips

1. **Use async/await** throughout backend
2. **Connection pooling** for database (configured in `database.py`)
3. **Redis caching** for frequent queries
4. **Celery workers** for long-running simulations
5. **Pagination** for list endpoints
6. **Streaming responses** for large outputs

## Monitoring

```python
# Structured logging
import structlog
logger = structlog.get_logger()

logger.info("simulation_started", project_id=pid, test_count=10)
logger.error("simulation_failed", project_id=pid, error=str(e))
```

## Contributing

1. Fork repository
2. Create feature branch
3. Write tests
4. Ensure CI passes
5. Submit PR with description