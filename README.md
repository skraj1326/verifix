# VerifiX AI (AstrixCore)

> An autonomous, evidence-driven AI verification engineer for digital semiconductor design.

## Overview

VerifiX AI is an AI-native semiconductor verification platform that acts as an autonomous verification engineer. It understands RTL designs, creates verification strategies, generates verification infrastructure, executes simulations, analyzes coverage, finds gaps, and iterates toward verification closure—all under human supervision.

## Key Features

- **RTL Intelligence**: Parse SystemVerilog/Verilog, extract modules, ports, signals, FSMs, protocols, build Design Knowledge Graph
- **Specification Analysis**: Parse Markdown/PDF/Word specs → structured requirements with unique IDs
- **Verification Planning**: Auto-generate verification plans traceable to RTL behavior or specification
- **SVA Generation**: Generate SystemVerilog Assertions with evidence, confidence levels, false-positive warnings
- **Test Generation**: Directed, constrained-random, UVM tests with stated verification objectives
- **Coverage Intelligence**: Analyze coverage, identify gaps, classify reachability, generate targeted tests
- **Closed-Loop AI**: Coverage gaps → targeted tests → simulate → measure → repeat until closure
- **Failure Analysis**: Root cause analysis, waveform debugging, regression triage
- **Traceability**: Requirement → Plan → Assertion → Test → Coverage → Evidence → Result

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      VERIFIX AI PLATFORM                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  FRONTEND   │  │   BACKEND   │  │   SIMULATION        │  │
│  │  (Next.js)  │  │  (FastAPI)  │  │   (Verilator/Icarus)│  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │                │                     │             │
│         └────────────────┼─────────────────────┘             │
│                          ▼                                    │
│         ┌─────────────────────────────────────────────────┐   │
│         │           AI AGENT ORCHESTRATOR                 │   │
│         │  PM │ Spec │ RTL │ Plan │ Assert │ Test │ Cov  │   │
│         │  Agent│Analyst│Analyst│Gen  │ Gen   │ Gen  │Intel│   │
│         └─────────────────────────────────────────────────┘   │
│                          │                                    │
│                          ▼                                    │
│         ┌─────────────────────────────────────────────────┐   │
│         │  POSTGRESQL + REDIS + FILE STORAGE              │   │
│         │  Projects │ Designs │ Plans │ Tests │ Sims     │   │
│         └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 20+ (for frontend development)
- Verilator & Icarus Verilog (installed in Docker)

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd verifix

# Copy environment template
cp .env.example .env

# Start all services
docker compose -f docker/docker-compose.yml up --build
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Local Development

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Set up database
cp ../.env.example .env
# Edit .env with your database settings

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## FIFO Demo

The FIFO demonstration showcases the complete verification flow:

1. Navigate to **RTL Explorer** (/rtl)
2. Click **"Analyze FIFO Demo"** button on the dashboard
3. Or manually:
   - Paste `examples/fifo/fifo.sv` into the editor
   - Click **"Analyze"** → **"Full Flow"**

This will automatically:
1. Parse the RTL and build knowledge graph
2. Generate verification plan (18 items)
3. Generate SVA assertions (15+)
4. Generate directed tests (12+), random tests, UVM components
5. Run simulation via Verilator
6. Analyze coverage and identify gaps
7. Generate targeted tests for gaps
8. Produce final verification report

## Project Structure

```
verifix/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── api/v1/         # REST API endpoints
│   │   ├── core/           # Config, DB, Security
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   ├── engines/        # Verification engines (core IP)
│   │   │   ├── rtl_parser/
│   │   │   ├── knowledge_graph/
│   │   │   ├── verification_planner/
│   │   │   ├── assertion_generator/
│   │   │   ├── test_generator/
│   │   │   ├── coverage_engine/
│   │   │   ├── log_analyzer/
│   │   │   ├── root_cause_engine/
│   │   │   ├── regression_engine/
│   │   │   ├── waveform_analyzer/
│   │   │   ├── simulation/
│   │   │   └── spec_parser/
│   │   ├── ai/             # AI Agent System
│   │   │   ├── agents/
│   │   │   ├── orchestrator/
│   │   │   ├── memory/
│   │   │   ├── tools/
│   │   │   └── prompts/
│   │   └── utils/
│   ├── tests/
│   ├── alembic/            # DB migrations
│   └── Dockerfile
│
├── frontend/               # Next.js Frontend
│   ├── app/                # App Router pages
│   ├── components/         # React components
│   ├── lib/                # Utilities
│   └── Dockerfile
│
├── examples/               # Demo RTL designs
│   └── fifo/
│
├── docker/                 # Docker Compose files
│
└── docs/                   # Documentation
```

## API Endpoints

### Projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects` - List projects
- `GET /api/v1/projects/{id}` - Get project
- `GET /api/v1/projects/{id}/summary` - Project dashboard

### RTL Analysis
- `POST /api/v1/rtl/analyze` - Analyze RTL code
- `POST /api/v1/rtl/upload` - Upload RTL file

### Specification
- `POST /api/v1/spec/analyze` - Analyze specification
- `POST /api/v1/spec/upload` - Upload spec file

### Verification
- `POST /api/v1/verification/plan` - Generate verification plan
- `POST /api/v1/verification/assertions` - Generate SVA assertions
- `POST /api/v1/verification/tests` - Generate tests
- `POST /api/v1/verification/full-flow` - Complete flow

### Simulation
- `POST /api/v1/simulation/compile` - Compile RTL
- `POST /api/v1/simulation/run` - Run simulation
- `POST /api/v1/simulation/analyze-log` - Analyze simulation log

### Coverage
- `POST /api/v1/coverage/analyze` - Analyze coverage
- `POST /api/v1/coverage/gaps` - Identify gaps
- `POST /api/v1/coverage/generate-targeted-tests` - Generate gap-targeted tests

### Analysis
- `POST /api/v1/failure-analysis` - Root cause analysis
- `POST /api/v1/regression/analyze` - Regression analysis
- `POST /api/v1/waveform/analyze` - Waveform analysis

### AI Agents
- `GET /api/v1/ai/status` - AI configuration status
- `POST /api/v1/ai/analyze-design` - AI design analysis
- `POST /api/v1/ai/improve-test` - AI test improvement
- `POST /api/v1/ai/analyze-gap` - AI gap analysis

## Security

- **Authentication**: JWT-based (to be implemented)
- **Authorization**: Project-level RBAC
- **Sandboxing**: Simulations run in isolated containers
- **Audit Logging**: All AI actions recorded
- **Data Isolation**: Project-scoped data access

## Testing

```bash
# Backend tests
cd backend
pytest app/tests/ -v

# Run FIFO demo end-to-end test
pytest app/tests/e2e/test_fifo_demo.py -v

# Frontend tests
cd frontend
npm test
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [AI Agents](docs/AI_AGENTS.md)
- [Simulation](docs/SIMULATION.md)
- [Verification Engine](docs/VERIFICATION_ENGINE.md)
- [Security](docs/SECURITY.md)
- [Development](docs/DEVELOPMENT.md)
- [Limitations](docs/LIMITATIONS.md)

## Roadmap

### V1 (Current MVP)
- RTL understanding, SVA, tests, simulation, coverage, basic UVM

### V2
- Formal verification, waveform intelligence, regression intelligence, requirement traceability

### V3
- Advanced UVM, multi-agent optimization, mutation testing, flaky-test intelligence

### V4
- Enterprise deployment, on-premise AI, team collaboration, EDA integrations

## License

Proprietary - All rights reserved.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.