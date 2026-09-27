"""Simulation API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.engines.simulation.orchestrator import SimulationOrchestrator, SimulationConfig
from app.engines.log_analyzer.analyzer import LogAnalyzer

router = APIRouter(prefix="/simulation")


class CompileRequest(BaseModel):
    rtl_files: list[str]
    testbench: str
    top_module: str
    simulator: str = "verilator"
    timeout: int = 300


class SimulateRequest(BaseModel):
    rtl_content: str
    test_code: str
    top_module: str
    simulator: str = "verilator"
    timeout: int = 300


class LogAnalysisRequest(BaseModel):
    log_content: str
    log_type: str = "simulation"  # simulation, compilation, uvm


@router.post("/compile")
async def compile_rtl(request: CompileRequest):
    """Compile RTL with a simulator."""
    orchestrator = SimulationOrchestrator()
    config = SimulationConfig(
        simulator=request.simulator,
        top_module=request.top_module,
        timeout=request.timeout,
    )

    result = orchestrator.compile(request.rtl_files, config)

    return {
        "success": result.success,
        "exit_code": result.exit_code,
        "compilation_log": result.stdout + result.stderr,
        "error_message": result.error_message,
        "runtime_seconds": result.runtime_seconds,
    }


@router.post("/run")
async def run_simulation(request: SimulateRequest):
    """Run a complete simulation (compile + execute)."""
    orchestrator = SimulationOrchestrator()
    config = SimulationConfig(
        simulator=request.simulator,
        top_module=request.top_module,
        timeout=request.timeout,
    )

    # For MVP, we'll analyze the test code and report
    # Full simulation requires actual RTL files on disk
    analyzer = LogAnalyzer()

    result = {
        "status": "simulated",
        "test_name": "generated_test",
        "test_code": request.test_code,
        "top_module": request.top_module,
        "simulator": request.simulator,
        "note": "Full simulation requires file system access. Use /api/v1/simulation/compile for real compilation.",
    }

    return result


@router.post("/analyze-log")
async def analyze_simulation_log(request: LogAnalysisRequest):
    """Analyze a simulation log file."""
    analyzer = LogAnalyzer()

    if request.log_type == "compilation":
        errors = analyzer.parse_compilation_errors(request.log_content)
        return {
            "log_type": "compilation",
            "errors": errors,
            "total_errors": len(errors),
        }
    elif request.log_type == "uvm":
        uvm_info = analyzer.parse_uvm_log(request.log_content)
        return {
            "log_type": "uvm",
            **uvm_info,
        }
    else:
        analysis = analyzer.parse_log(request.log_content)
        return {
            "log_type": "simulation",
            **analysis,
        }
