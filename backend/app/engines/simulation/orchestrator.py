"""Simulation Orchestrator - Manages simulation execution across multiple simulators."""

import subprocess
import tempfile
import os
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class SimulationConfig:
    simulator: str = "verilator"
    top_module: str = ""
    clock_signal: str = "clk"
    reset_signal: str = "rst"
    timeout: int = 300
    extra_flags: list = None
    include_dirs: list = None

    def __post_init__(self):
        if self.extra_flags is None:
            self.extra_flags = []
        if self.include_dirs is None:
            self.include_dirs = []


@dataclass
class SimulationResult:
    success: bool = False
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    compilation_log: str = ""
    simulation_log: str = ""
    coverage_report: str = ""
    runtime_seconds: float = 0.0
    error_message: str = ""


class SimulationOrchestrator:
    """Manages simulation across Verilator, Icarus, and commercial simulators.

    Supports:
    - Verilator (primary, open-source)
    - Icarus Verilog (secondary, open-source)
    - Commercial simulator adapters (future)
    """

    def __init__(self):
        self.simulators = {
            "verilator": VerilatorAdapter(),
            "icarus": IcarusAdapter(),
        }

    def compile(self, rtl_files: list[str], config: SimulationConfig,
                testbench_file: str = "") -> SimulationResult:
        """Compile RTL and testbench."""
        adapter = self.simulators.get(config.simulator)
        if not adapter:
            return SimulationResult(
                error_message=f"Unknown simulator: {config.simulator}"
            )
        return adapter.compile(rtl_files, config, testbench_file)

    def simulate(self, compiled_dir: str, config: SimulationConfig,
                 test_name: str = "") -> SimulationResult:
        """Run simulation on compiled design."""
        adapter = self.simulators.get(config.simulator)
        if not adapter:
            return SimulationResult(
                error_message=f"Unknown simulator: {config.simulator}"
            )
        return adapter.simulate(compiled_dir, config, test_name)

    def run_test(self, rtl_files: list[str], test_code: str,
                 config: SimulationConfig) -> SimulationResult:
        """Complete flow: compile and run a single test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write testbench
            tb_path = os.path.join(tmpdir, "tb.sv")
            with open(tb_path, "w") as f:
                f.write(test_code)

            # Compile
            compile_result = self.compile(rtl_files, config, tb_path)
            if not compile_result.success:
                return compile_result

            # Simulate
            sim_result = self.simulate(tmpdir, config)
            sim_result.compilation_log = compile_result.stdout + compile_result.stderr
            return sim_result

    def run_regression(self, rtl_files: list[str], test_files: list[str],
                       config: SimulationConfig) -> dict:
        """Run a full regression suite."""
        results = {}
        for test_file in test_files:
            test_name = Path(test_file).stem
            with open(test_file, "r") as f:
                test_code = f.read()
            results[test_name] = self.run_test(rtl_files, test_code, config)
        return results


class VerilatorAdapter:
    """Adapter for Verilator simulator."""

    def compile(self, rtl_files: list[str], config: SimulationConfig,
                testbench_file: str = "") -> SimulationResult:
        """Compile with Verilator."""
        result = SimulationResult()
        start_time = time.time()

        cmd = [
            config.simulator or "verilator",
            "--binary",
            "--top-module", config.top_module,
            "-Wall",
            "--trace",
            "--cc",
        ]

        # Add include directories
        for inc_dir in config.include_dirs:
            cmd.extend(["-I", inc_dir])

        # Add extra flags
        cmd.extend(config.extra_flags)

        # Add RTL files
        cmd.extend(rtl_files)

        # Add testbench
        if testbench_file:
            cmd.append(testbench_file)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.timeout,
                cwd=os.path.dirname(rtl_files[0]) if rtl_files else ".",
            )
            result.exit_code = proc.returncode
            result.stdout = proc.stdout
            result.stderr = proc.stderr
            result.success = proc.returncode == 0
        except subprocess.TimeoutExpired:
            result.error_message = f"Compilation timed out after {config.timeout}s"
        except FileNotFoundError:
            result.error_message = f"Verilator not found at: {config.simulator}"
        except Exception as e:
            result.error_message = f"Compilation error: {str(e)}"

        result.runtime_seconds = time.time() - start_time
        return result

    def simulate(self, compiled_dir: str, config: SimulationConfig,
                 test_name: str = "") -> SimulationResult:
        """Run Verilator simulation."""
        result = SimulationResult()
        start_time = time.time()

        exe_path = os.path.join(compiled_dir, f"V{config.top_module}")
        if not os.path.exists(exe_path):
            exe_path = os.path.join(compiled_dir, "obj_dir",
                                    f"V{config.top_module}")

        try:
            proc = subprocess.run(
                [exe_path],
                capture_output=True,
                text=True,
                timeout=config.timeout,
            )
            result.exit_code = proc.returncode
            result.stdout = proc.stdout
            result.stderr = proc.stderr
            result.simulation_log = proc.stdout + proc.stderr
            result.success = proc.returncode == 0
        except subprocess.TimeoutExpired:
            result.error_message = f"Simulation timed out after {config.timeout}s"
        except FileNotFoundError:
            result.error_message = f"Compiled executable not found: {exe_path}"
        except Exception as e:
            result.error_message = f"Simulation error: {str(e)}"

        result.runtime_seconds = time.time() - start_time
        return result


class IcarusAdapter:
    """Adapter for Icarus Verilog simulator."""

    def compile(self, rtl_files: list[str], config: SimulationConfig,
                testbench_file: str = "") -> SimulationResult:
        """Compile with Icarus Verilog."""
        result = SimulationResult()
        start_time = time.time()

        cmd = [
            config.simulator or "iverilog",
            "-g2012",
            "-o", os.path.join(tempfile.gettempdir(), "sim.vvp"),
        ]

        for inc_dir in config.include_dirs:
            cmd.extend(["-I", inc_dir])

        cmd.extend(rtl_files)
        if testbench_file:
            cmd.append(testbench_file)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.timeout,
            )
            result.exit_code = proc.returncode
            result.stdout = proc.stdout
            result.stderr = proc.stderr
            result.success = proc.returncode == 0
        except subprocess.TimeoutExpired:
            result.error_message = f"Compilation timed out after {config.timeout}s"
        except FileNotFoundError:
            result.error_message = f"Icarus Verilog not found at: {config.simulator}"
        except Exception as e:
            result.error_message = f"Compilation error: {str(e)}"

        result.runtime_seconds = time.time() - start_time
        return result

    def simulate(self, compiled_dir: str, config: SimulationConfig,
                 test_name: str = "") -> SimulationResult:
        """Run Icarus simulation."""
        result = SimulationResult()
        start_time = time.time()

        vvp_path = os.path.join(tempfile.gettempdir(), "sim.vvp")

        try:
            proc = subprocess.run(
                ["vvp", vvp_path],
                capture_output=True,
                text=True,
                timeout=config.timeout,
            )
            result.exit_code = proc.returncode
            result.stdout = proc.stdout
            result.stderr = proc.stderr
            result.simulation_log = proc.stdout + proc.stderr
            result.success = proc.returncode == 0
        except subprocess.TimeoutExpired:
            result.error_message = f"Simulation timed out after {config.timeout}s"
        except FileNotFoundError:
            result.error_message = "VVP runtime not found"
        except Exception as e:
            result.error_message = f"Simulation error: {str(e)}"

        result.runtime_seconds = time.time() - start_time
        return result
