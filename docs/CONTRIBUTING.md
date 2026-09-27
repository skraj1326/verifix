# Contributing to VerifiX AI

Thank you for your interest in contributing to VerifiX AI! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- No harassment or discrimination

## How to Contribute

### Reporting Issues

1. Check existing issues first
2. Use the issue template
3. Provide:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment (OS, Python/Node versions)
   - Relevant logs/RTL snippets

### Suggesting Features

1. Open a feature request issue
2. Describe the use case
3. Explain the benefit
4. Consider implementation complexity

### Code Contributions

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes with tests
4. Ensure CI passes
5. Submit PR with description

## Development Setup

```bash
# Fork and clone
git clone https://github.com/your-username/verifix.git
cd verifix

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If exists
pre-commit install

# Frontend
cd ../frontend
npm install

# Run tests
cd ../backend
pytest app/tests/ -v
cd ../frontend
npm test
```

## Coding Standards

### Python (Backend)

```python
# Type hints required
def process_data(input: str) -> dict:
    """Process input data.
    
    Args:
        input: Raw input string
        
    Returns:
        Processed result dictionary
    """
    # Implementation
    return {"result": "processed"}

# Use dataclasses for data structures
from dataclasses import dataclass

@dataclass
class VerificationResult:
    passed: bool
    coverage: float
    details: dict = field(default_factory=dict)
```

**Tools:**
- `black` for formatting
- `ruff` for linting
- `mypy` for type checking
- `pytest` for testing

### TypeScript/React (Frontend)

```tsx
// Functional components with hooks
interface Props {
  title: string;
  onAction: (value: string) => void;
}

export function MyComponent({ title, onAction }: Props) {
  const [state, setState] = useState<string>("");
  
  return (
    <div className="p-4 bg-gray-800 rounded-lg">
      <h3 className="text-lg font-semibold">{title}</h3>
    </div>
  );
}

// Use cn() for conditional classes
import { cn } from "@/lib/utils";

<div className={cn("base", condition && "conditional")} />
```

**Tools:**
- `eslint` for linting
- `prettier` for formatting
- TypeScript strict mode

## Testing Requirements

### Backend Tests

```python
# Unit test example
@pytest.mark.asyncio
async def test_verification_plan_generation():
    parser = RTLParser()
    modules = parser.parse(FIFO_RTL)
    
    planner = VerificationPlanGenerator()
    plan = planner.generate(modules, "")
    
    assert plan["summary"]["total_items"] > 0
    assert "fifo" in plan["traceability"]["module_to_items"]

# Integration test example
@pytest.mark.asyncio
async def test_full_verification_flow():
    service = VerificationService()
    result = await service.full_verification_flow(FIFO_RTL, FIFO_SPEC)
    
    assert "analysis" in result
    assert "plan" in result
    assert "assertions" in result
    assert "tests" in result
```

### Frontend Tests

```tsx
// Component test
import { render, screen } from "@testing-library/react";
import { MonacoEditor } from "@/components/editor/MonacoEditor";

test("renders editor with content", () => {
  render(<MonacoEditor value="module test;" onChange={jest.fn()} />);
  expect(screen.getByText("module test;")).toBeInTheDocument();
});
```

## Pull Request Process

1. **Title**: Clear, descriptive (e.g., "Add Verilator XML coverage parsing")
2. **Description**: 
   - What changed
   - Why
   - Testing done
   - Screenshots (if UI)
3. **Linked Issues**: Reference related issues
4. **Review**: 
   - At least 1 approval required
   - All CI checks pass
   - No merge conflicts

## Commit Messages

Follow conventional commits:
```
feat(parser): add Verilator XML coverage parsing
fix(simulation): handle timeout correctly
docs(api): update verification endpoints
test(engine): add FIFO demo e2e test
refactor(ai): simplify agent orchestration
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `perf`

## Architecture Decisions

Document significant decisions in `docs/adr/` (Architecture Decision Records):

```markdown
# ADR-001: Use FastAPI for Backend

## Status: Accepted

## Context
Need async, high-performance API with OpenAPI support.

## Decision
Use FastAPI with Pydantic v2.

## Consequences
- Better performance than Flask
- Automatic OpenAPI generation
- Type-safe request/response validation
```

## Release Process

1. Update version in `pyproject.toml` / `package.json`
2. Update CHANGELOG.md
3. Create release tag: `git tag v0.2.0`
4. GitHub Actions builds and publishes
5. Update documentation

## Getting Help

- **Discord**: #verifix-dev
- **GitHub Discussions**: For questions
- **Email**: dev@verifix.ai

## License

By contributing, you agree that your contributions will be licensed under the project's license (Proprietary - All rights reserved).