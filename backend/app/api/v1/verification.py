"""Verification Planning & Generation API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.engines.rtl_parser.parser import RTLParser
from app.engines.verification_planner.planner import VerificationPlanGenerator
from app.engines.assertion_generator.generator import AssertionGenerator
from app.engines.test_generator.generator import TestGenerator
from app.engines.uvm_generator.generator import UVMGenerator

router = APIRouter(prefix="/verification")


class VerificationPlanRequest(BaseModel):
    rtl_content: str
    specification: Optional[str] = ""


class AssertionGenRequest(BaseModel):
    rtl_content: str


class TestGenRequest(BaseModel):
    rtl_content: str
    coverage_gaps: Optional[list[dict]] = None
    test_types: list[str] = ["directed", "constrained_random"]


class UVMGenRequest(BaseModel):
    rtl_content: str
    include_tests: bool = True


@router.post("/uvm")
async def generate_uvm(request: UVMGenRequest):
    """Generate complete UVM environment from RTL."""
    parser = RTLParser()
    modules = parser.parse(request.rtl_content)

    if not modules:
        raise HTTPException(status_code=400, detail="No modules found in RTL")

    generator = UVMGenerator()
    uvm_components = generator.generate(modules)

    component_types = {}
    for comp in uvm_components:
        ct = comp["component_type"]
        component_types[ct] = component_types.get(ct, 0) + 1

    return {
        "uvm_components": uvm_components,
        "total_components": len(uvm_components),
        "component_types": component_types,
        "modules_analyzed": [m.name for m in modules],
    }


@router.post("/plan")
async def generate_verification_plan(request: VerificationPlanRequest):
    """Generate a verification plan from RTL analysis."""
    parser = RTLParser()
    modules = parser.parse(request.rtl_content)

    if not modules:
        raise HTTPException(status_code=400, detail="No modules found in RTL")

    planner = VerificationPlanGenerator()
    plan = planner.generate(modules, request.specification)

    return {
        "plan": plan,
        "summary": plan["summary"],
        "traceability": plan["traceability"],
        "modules_analyzed": [m.name for m in modules],
    }


@router.post("/assertions")
async def generate_assertions(request: AssertionGenRequest):
    """Generate SystemVerilog assertions from RTL."""
    parser = RTLParser()
    modules = parser.parse(request.rtl_content)

    if not modules:
        raise HTTPException(status_code=400, detail="No modules found in RTL")

    generator = AssertionGenerator()
    assertions = generator.generate(modules)

    return {
        "assertions": assertions,
        "total_generated": len(assertions),
        "modules_analyzed": [m.name for m in modules],
        "assertion_types": list(set(a["name"].split("_")[-1] for a in assertions)),
    }


@router.post("/tests")
async def generate_tests(request: TestGenRequest):
    """Generate tests from RTL."""
    parser = RTLParser()
    modules = parser.parse(request.rtl_content)

    if not modules:
        raise HTTPException(status_code=400, detail="No modules found in RTL")

    generator = TestGenerator()
    tests = generator.generate(modules, request.coverage_gaps)

    # Filter by requested test types
    if request.test_types:
        tests = [t for t in tests if t["test_type"] in request.test_types]

    return {
        "tests": tests,
        "total_generated": len(tests),
        "test_types": {
            tt: len([t for t in tests if t["test_type"] == tt])
            for tt in set(t["test_type"] for t in tests)
        },
        "modules_analyzed": [m.name for m in modules],
    }


@router.post("/full-flow")
async def full_verification_flow(request: VerificationPlanRequest):
    """Run the complete verification flow: plan → assertions → tests."""
    parser = RTLParser()
    modules = parser.parse(request.rtl_content)

    if not modules:
        raise HTTPException(status_code=400, detail="No modules found in RTL")

    # Step 1: Verification Plan
    planner = VerificationPlanGenerator()
    plan = planner.generate(modules, request.specification)

    # Step 2: Assertions
    assertion_gen = AssertionGenerator()
    assertions = assertion_gen.generate(modules)

    # Step 3: Tests
    test_gen = TestGenerator()
    tests = test_gen.generate(modules)

    # Step 4: Summary
    summary = parser.get_design_summary()

    return {
        "summary": summary,
        "verification_plan": {
            "total_items": plan["summary"]["total_items"],
            "categories": plan["summary"]["categories"],
            "items": plan["items"][:20],  # Limit for response size
        },
        "assertions": {
            "total_generated": len(assertions),
            "assertions": assertions[:20],
        },
        "tests": {
            "total_generated": len(tests),
            "test_types": {
                tt: len([t for t in tests if t["test_type"] == tt])
                for tt in set(t["test_type"] for t in tests)
            },
            "tests": [
                {
                    "name": t["name"],
                    "type": t["test_type"],
                    "objective": t["verification_objective"],
                    "code_length": len(t["code"]),
                }
                for t in tests
            ],
        },
    }
