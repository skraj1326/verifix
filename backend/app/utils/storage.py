"""File storage and management utilities."""

import os
import re
import uuid
import shutil
from pathlib import Path
from typing import Optional


class StorageManager:
    """Manages file storage for RTL, tests, logs, and coverage."""

    ALLOWED_EXTENSIONS = {".sv", ".v", ".vh", ".svh", ".vhd", ".log", ".vcd", ".json"}

    def __init__(self, base_dir: str = "./storage"):
        self.base_dir = Path(base_dir)
        self._ensure_directories()

    def _ensure_directories(self):
        """Create storage directory structure."""
        dirs = ["rtl", "tests", "logs", "coverage", "waveforms", "projects"]
        for d in dirs:
            (self.base_dir / d).mkdir(parents=True, exist_ok=True)

    def _validate_filename(self, filename: str) -> bool:
        """Validate filename for security."""
        # Reject path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            return False
        ext = Path(filename).suffix.lower()
        return ext in self.ALLOWED_EXTENSIONS

    def store_rtl(self, content: str, filename: str,
                  project_id: str = "") -> str:
        """Store RTL content and return the file path."""
        if self._validate_filename(filename):
            safe_name = filename
        else:
            ext = Path(filename).suffix or ".sv"
            safe_name = f"design_{uuid.uuid4().hex[:8]}{ext}"

        project_dir = self.base_dir / "projects" / (project_id or "default") / "rtl"
        project_dir.mkdir(parents=True, exist_ok=True)

        filepath = project_dir / safe_name
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def store_test(self, content: str, test_name: str,
                   project_id: str = "") -> str:
        """Store a generated test file."""
        safe_name = re.sub(r'[^\w\-.]', '_', test_name)
        if not safe_name.endswith(".sv"):
            safe_name += ".sv"

        project_dir = self.base_dir / "projects" / (project_id or "default") / "tests"
        project_dir.mkdir(parents=True, exist_ok=True)

        filepath = project_dir / safe_name
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def store_log(self, content: str, log_name: str = "") -> str:
        """Store a simulation log."""
        safe_name = log_name or f"sim_{uuid.uuid4().hex[:8]}.log"

        log_dir = self.base_dir / "logs"
        filepath = log_dir / safe_name
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def store_coverage(self, content: str, report_name: str = "") -> str:
        """Store a coverage report."""
        safe_name = report_name or f"cov_{uuid.uuid4().hex[:8]}.json"

        cov_dir = self.base_dir / "coverage"
        filepath = cov_dir / safe_name
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def read_file(self, path: str) -> str:
        """Read a file safely."""
        full_path = self.base_dir / path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return full_path.read_text(encoding="utf-8")

    def list_project_files(self, project_id: str,
                           category: str = "rtl") -> list[str]:
        """List files in a project directory."""
        project_dir = self.base_dir / "projects" / project_id / category
        if not project_dir.exists():
            return []
        return [str(p.relative_to(self.base_dir)) for p in project_dir.iterdir()]

    def delete_project(self, project_id: str) -> bool:
        """Delete all files for a project."""
        project_dir = self.base_dir / "projects" / project_id
        if project_dir.exists():
            shutil.rmtree(project_dir)
            return True
        return False

    def get_project_size(self, project_id: str) -> int:
        """Get total size of project files in bytes."""
        project_dir = self.base_dir / "projects" / project_id
        if not project_dir.exists():
            return 0
        return sum(p.stat().st_size for p in project_dir.rglob("*") if p.is_file())


def get_storage() -> StorageManager:
    """Get the StorageManager singleton."""
    from app.core.config import settings
    return StorageManager(str(settings.STORAGE_ROOT))