"""Waveform Viewer API endpoints for VCD/FST waveform analysis."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/waveform", tags=["Waveform Viewer"])


class WaveformUploadResponse(BaseModel):
    waveform_id: str
    filename: str
    format: str
    signals_count: int
    time_range: Dict[str, float]
    timescale: str
    date: str


class SignalTransition(BaseModel):
    time: float
    value: str
    signal_name: str = ""


class SignalData(BaseModel):
    name: str
    transitions: List[SignalTransition]
    width: int = 1
    type: str = "logic"  # logic, bit, reg, wire, bus
    min_value: str = ""
    max_value: str = ""
    toggle_count: int = 0
    x_count: int = 0
    z_count: int = 0


class WaveformAnalysisResponse(BaseModel):
    waveform_id: str
    filename: str
    format: str
    timescale: str
    time_range: Dict[str, float]
    total_signals: int
    signals: List[SignalData]
    metadata: Dict[str, Any]


class SignalContextRequest(BaseModel):
    waveform_id: str
    failure_time: float
    window: float = 100.0


class SignalContextResponse(BaseModel):
    failure_time: float
    window: float
    signals: Dict[str, Dict[str, Any]]


class CompareWaveformsRequest(BaseModel):
    waveform_id_1: str
    waveform_id_2: str
    tolerance: float = 0.0


class WaveformComparisonResponse(BaseModel):
    matching_signals: List[str]
    different_signals: List[Dict[str, Any]]
    only_in_1: List[str]
    only_in_2: List[str]


# In-memory storage for demo (use database in production)
waveform_store: Dict[str, Dict[str, Any]] = {}


@router.post("/upload", response_model=WaveformUploadResponse)
async def upload_waveform(file: UploadFile = File(...)):
    """Upload and parse a VCD/FST waveform file."""
    content_bytes = await file.read()
    
    # Detect format and parse
    filename = file.filename or "unknown"
    if filename.lower().endswith(".fst"):
        # FST is binary, parse from bytes
        parsed = parse_fst_from_bytes(content_bytes)
    else:
        # VCD is text
        content_str = content_bytes.decode("utf-8", errors="ignore")
        parsed = parse_waveform(content_str, filename)
    
    waveform_id = f"wave_{len(waveform_store) + 1}_{int(datetime.now().timestamp())}"
    waveform_store[waveform_id] = {
        "id": waveform_id,
        "filename": filename,
        "format": parsed["format"],
        "parsed": parsed,
        "uploaded_at": datetime.now().isoformat(),
    }
    
    return WaveformUploadResponse(
        waveform_id=waveform_id,
        filename=filename,
        format=parsed["format"],
        signals_count=len(parsed["signals"]),
        time_range=parsed["time_range"],
        timescale=parsed["timescale"],
        date=datetime.now().isoformat(),
    )


@router.get("/{waveform_id}", response_model=WaveformAnalysisResponse)
async def get_waveform(waveform_id: str):
    """Get parsed waveform data."""
    if waveform_id not in waveform_store:
        raise HTTPException(status_code=404, detail="Waveform not found")
    
    data = waveform_store[waveform_id]["parsed"]
    return WaveformAnalysisResponse(
        waveform_id=waveform_id,
        filename=waveform_store[waveform_id]["filename"],
        format=data["format"],
        timescale=data["timescale"],
        time_range=data["time_range"],
        total_signals=len(data["signals"]),
        signals=data["signals"],
        metadata=data.get("metadata", {}),
    )


@router.get("/{waveform_id}/signals", response_model=List[SignalData])
async def list_signals(waveform_id: str, pattern: str = ""):
    """List signals in waveform, optionally filtered by pattern."""
    if waveform_id not in waveform_store:
        raise HTTPException(status_code=404, detail="Waveform not found")
    
    signals = waveform_store[waveform_id]["parsed"]["signals"]
    
    if pattern:
        import re
        regex = re.compile(pattern.replace("*", ".*"))
        signals = [s for s in signals if regex.search(s["name"])]
    
    return signals


@router.get("/{waveform_id}/signal/{signal_name}", response_model=SignalData)
async def get_signal(waveform_id: str, signal_name: str):
    """Get detailed data for a specific signal."""
    if waveform_id not in waveform_store:
        raise HTTPException(status_code=404, detail="Waveform not found")
    
    signals = waveform_store[waveform_id]["parsed"]["signals"]
    signal = next((s for s in signals if s["name"] == signal_name), None)
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    return signal


@router.post("/{waveform_id}/signal-context", response_model=SignalContextResponse)
async def get_signal_context(waveform_id: str, request: SignalContextRequest):
    """Get signal values around a specific time (failure analysis)."""
    if waveform_id not in waveform_store:
        raise HTTPException(status_code=404, detail="Waveform not found")
    
    signals = waveform_store[waveform_id]["parsed"]["signals"]
    window_start = request.failure_time - request.window
    window_end = request.failure_time + request.window
    
    context = {}
    for signal in signals:
        relevant_transitions = [
            t for t in signal["transitions"]
            if window_start <= t["time"] <= window_end
        ]
        
        # Find value at failure time
        value_at_failure = "unknown"
        for t in reversed(signal["transitions"]):
            if t["time"] <= request.failure_time:
                value_at_failure = t["value"]
                break
        
        context[signal["name"]] = {
            "value_at_failure": value_at_failure,
            "transitions_near_failure": [
                {"time": t["time"], "value": t["value"]}
                for t in relevant_transitions
            ],
            "total_transitions_in_window": len(relevant_transitions),
        }
    
    return SignalContextResponse(
        failure_time=request.failure_time,
        window=request.window,
        signals=context,
    )


@router.post("/compare", response_model=WaveformComparisonResponse)
async def compare_waveforms(request: CompareWaveformsRequest):
    """Compare two waveforms to find differences."""
    if request.waveform_id_1 not in waveform_store:
        raise HTTPException(status_code=404, detail="First waveform not found")
    if request.waveform_id_2 not in waveform_store:
        raise HTTPException(status_code=404, detail="Second waveform not found")
    
    signals_1 = {s["name"]: s for s in waveform_store[request.waveform_id_1]["parsed"]["signals"]}
    signals_2 = {s["name"]: s for s in waveform_store[request.waveform_id_2]["parsed"]["signals"]}
    
    all_names = set(signals_1.keys()) | set(signals_2.keys())
    
    matching = []
    different = []
    only_in_1 = []
    only_in_2 = []
    
    for name in all_names:
        if name in signals_1 and name in signals_2:
            # Compare transitions
            trans_1 = signals_1[name]["transitions"]
            trans_2 = signals_2[name]["transitions"]
            
            if _transitions_equal(trans_1, trans_2, request.tolerance):
                matching.append(name)
            else:
                different.append({
                    "signal": name,
                    "differences": _find_transition_differences(trans_1, trans_2, request.tolerance),
                })
        elif name in signals_1:
            only_in_1.append(name)
        else:
            only_in_2.append(name)
    
    return WaveformComparisonResponse(
        matching_signals=matching,
        different_signals=different,
        only_in_1=only_in_1,
        only_in_2=only_in_2,
    )


def _transitions_equal(t1: List[Dict], t2: List[Dict], tolerance: float) -> bool:
    """Compare two transition lists."""
    if len(t1) != len(t2):
        return False
    for a, b in zip(t1, t2):
        if a["value"] != b["value"]:
            return False
        if abs(a["time"] - b["time"]) > tolerance:
            return False
    return True


def _find_transition_differences(t1: List[Dict], t2: List[Dict], tolerance: float) -> List[Dict]:
    """Find differences between two transition lists."""
    differences = []
    max_len = max(len(t1), len(t2))
    
    for i in range(max_len):
        a = t1[i] if i < len(t1) else None
        b = t2[i] if i < len(t2) else None
        
        if a is None:
            differences.append({"type": "missing_in_1", "index": i, "time": b["time"], "value": b["value"]})
        elif b is None:
            differences.append({"type": "missing_in_2", "index": i, "time": a["time"], "value": a["value"]})
        elif a["value"] != b["value"] or abs(a["time"] - b["time"]) > tolerance:
            differences.append({
                "type": "value_or_time_mismatch",
                "index": i,
                "time_1": a["time"],
                "value_1": a["value"],
                "time_2": b["time"],
                "value_2": b["value"],
            })
    
    return differences


def parse_waveform(content: str, filename: str) -> Dict[str, Any]:
    """Parse VCD or FST waveform content."""
    # Detect format
    is_fst = filename.lower().endswith(".fst") or "$fst" in content.lower()
    
    if is_fst:
        return parse_fst(content)
    else:
        return parse_vcd(content)


def _value_to_int(value: str) -> int:
    """Interpret a VCD value-change string as an integer.

    Scalar values ('0', '1') convert directly. Vector values are binary digits
    ('b1010' with the marker, or a bare '1010' without it), so they must be read
    as base 2 rather than base 10.
    """
    text = value[1:] if value[:1] in ("b", "B") else value
    if not text:
        raise ValueError("empty value")
    if any(ch in "xzXZ" for ch in text):
        raise ValueError("unknown/high-impedance value")
    return int(text, 2)


def parse_vcd(content: str) -> Dict[str, Any]:
    """Parse VCD (Value Change Dump) format."""
    lines = content.split("\n")
    
    signals = []
    signal_map = {}  # id -> signal info
    timescale = "1ns"
    time_range = {"min": 0, "max": 0}
    current_time = 0.0
    
    parsing_vars = False
    parsing_values = False
    
    for line in lines:
        line = line.strip()
        
        if line.startswith("$timescale"):
            # Extract timescale
            parts = line.split()
            if len(parts) >= 3:
                timescale = f"{parts[1]}{parts[2]}"
        
        elif line.startswith("$var"):
            # $var wire 1 ! clk $end
            parts = line.split()
            if len(parts) >= 5:
                var_type = parts[1]
                width = int(parts[2])
                var_id = parts[3]
                name = parts[4]
                
                signal = {
                    "name": name,
                    "id": var_id,
                    "type": var_type,
                    "width": width,
                    "transitions": [],
                }
                signals.append(signal)
                signal_map[var_id] = signal
        
        elif line.startswith("$upscope") or line.startswith("$enddefinitions"):
            pass
        
        elif line.startswith("#"):
            # Time change
            try:
                current_time = float(line[1:])
                time_range["max"] = max(time_range["max"], current_time)
            except ValueError:
                pass
        
        elif line and line[0] in "01xzXZ" and len(line) >= 2:
            # Single-bit value change: 0! or 1"
            value = line[0]
            var_id = line[1:]
            if var_id in signal_map:
                signal_map[var_id]["transitions"].append({
                    "time": current_time,
                    "value": value,
                })
        
        elif line.startswith("b"):
            # Multi-bit value change: b1010 !
            parts = line.split()
            if len(parts) >= 2:
                value = parts[0][1:]  # Remove 'b'
                var_id = parts[1]
                if var_id in signal_map:
                    signal_map[var_id]["transitions"].append({
                        "time": current_time,
                        "value": value,
                    })
    
    # Compute statistics for each signal
    for signal in signals:
        trans = signal["transitions"]
        signal["toggle_count"] = sum(1 for i in range(1, len(trans)) if trans[i]["value"] != trans[i-1]["value"])
        signal["x_count"] = sum(1 for t in trans if "x" in t["value"].lower())
        signal["z_count"] = sum(1 for t in trans if "z" in t["value"].lower())
        
        values = [t["value"] for t in trans]
        # Find min/max for numeric values.
        # Value changes are stored without their 'b' prefix, so multi-bit
        # vectors must be interpreted as binary, not decimal.
        numeric_values = []
        for v in values:
            try:
                numeric_values.append(_value_to_int(v))
            except ValueError:
                pass
        if numeric_values:
            signal["min_value"] = str(min(numeric_values))
            signal["max_value"] = str(max(numeric_values))
    
    return {
        "format": "VCD",
        "timescale": timescale,
        "time_range": time_range,
        "signals": signals,
        "metadata": {"total_signals": len(signals)},
    }


def parse_fst(content: str) -> Dict[str, Any]:
    """Parse FST (Fast Signal Trace) format.
    
    FST is a binary format. This function attempts to use gtkwave to convert
    FST to VCD, then parses the VCD. If gtkwave is not available, raises
    an informative error.
    """
    import subprocess
    import tempfile
    import os
    
    # Try to find gtkwave
    gtkwave_cmd = "gtkwave"
    
    # Write FST content to a temporary file (it's binary, so we need to handle it)
    # Note: The content passed here may already be decoded as text, which won't work
    # for binary FST. In practice, the upload endpoint reads raw bytes.
    # This function is kept for compatibility but the real parsing happens
    # in upload_waveform which has access to raw bytes.
    return {
        "format": "FST",
        "timescale": "1ps",
        "time_range": {"min": 0, "max": 0},
        "signals": [],
        "metadata": {
            "note": "FST parsing requires gtkwave binary. Use VCD format or install gtkwave.",
            "install_hint": "On Ubuntu/Debian: apt-get install gtkwave. On macOS: brew install gtkwave."
        },
    }


def parse_fst_from_bytes(fst_bytes: bytes) -> Dict[str, Any]:
    """Parse FST from raw bytes using gtkwave subprocess."""
    import subprocess
    import tempfile
    import os
    
    # Write FST to temp file
    with tempfile.NamedTemporaryFile(suffix=".fst", delete=False) as fst_file:
        fst_file.write(fst_bytes)
        fst_path = fst_file.name
    
    vcd_path = fst_path + ".vcd"
    
    try:
        # Use gtkwave to convert FST to VCD
        # gtkwave -F fst -O vcd input.fst output.vcd
        result = subprocess.run(
            ["gtkwave", "-F", "fst", "-O", "vcd", fst_path, vcd_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            return {
                "format": "FST",
                "timescale": "1ps",
                "time_range": {"min": 0, "max": 0},
                "signals": [],
                "metadata": {
                    "error": f"gtkwave conversion failed: {result.stderr}",
                    "install_hint": "Install gtkwave: apt-get install gtkwave (Linux) or brew install gtkwave (macOS)"
                },
            }
        
        # Read the converted VCD
        with open(vcd_path, "r") as f:
            vcd_content = f.read()
        
        # Parse as VCD
        parsed = parse_vcd(vcd_content)
        parsed["format"] = "FST (converted)"
        return parsed
        
    except FileNotFoundError:
        return {
            "format": "FST",
            "timescale": "1ps",
            "time_range": {"min": 0, "max": 0},
            "signals": [],
            "metadata": {
                "error": "gtkwave not found in PATH",
                "install_hint": "Install gtkwave: apt-get install gtkwave (Linux) or brew install gtkwave (macOS)"
            },
        }
    except subprocess.TimeoutExpired:
        return {
            "format": "FST",
            "timescale": "1ps",
            "time_range": {"min": 0, "max": 0},
            "signals": [],
            "metadata": {"error": "gtkwave conversion timed out"},
        }
    except Exception as e:
        return {
            "format": "FST",
            "timescale": "1ps",
            "time_range": {"min": 0, "max": 0},
            "signals": [],
            "metadata": {"error": f"FST parsing failed: {str(e)}"},
        }
    finally:
        # Cleanup temp files
        for path in [fst_path, vcd_path]:
            try:
                os.unlink(path)
            except:
                pass


# ============================================================
# FRONTEND: Waveform Viewer Component
# ============================================================
# File: frontend/components/waveform/WaveformViewer.tsx