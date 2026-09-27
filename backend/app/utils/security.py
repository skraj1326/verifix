"""Security utilities - encryption, hashing, audit."""

import base64
import hashlib
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def generate_encryption_key() -> str:
    """Generate a secure random encryption key."""
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


def hash_sensitive(data: str, salt: str = "") -> str:
    """Hash sensitive data (e.g., IP identifiers) for storage."""
    to_hash = data + salt
    return hashlib.sha256(to_hash.encode()).hexdigest()


def mask_secrets(data: str) -> str:
    """Mask API keys and secrets in logs."""
    import re
    patterns = [
        (r'(api[_-]?key\s*[:=]\s*)(\S+)', r'\1***MASKED***'),
        (r'(sk-[a-zA-Z0-9]{8})\w+', r'\1***'),
        (r'(password\s*[:=]\s*)\S+', r'\1***'),
    ]
    masked = data
    for pattern, replacement in patterns:
        masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE)
    return masked


class AuditLogger:
    """Audit logging for security compliance."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def log(self, action: str, resource_type: str = "",
            resource_id: str = "", details: dict = None,
            user_id: str = "", ip_address: str = ""):
        """Record an audit event."""
        if not self.enabled:
            return

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "user_id": user_id,
            "ip_address": ip_address,
        }
        logger.info(f"AUDIT: {entry}")


def validate_rtl_content(content: str) -> bool:
    """Basic validation of RTL content before analysis."""
    # Must contain at least one module/interface/package
    import re
    if not content or len(content.strip()) < 10:
        return False

    has_module = bool(re.search(r'\b(?:module|interface|package)\s+\w+', content))
    if not has_module:
        return False

    # Reject binary content
    if "\x00" in content:
        return False

    return True


def validate_systemverilog_code(code: str) -> tuple[bool, list[str]]:
    """Validate generated SystemVerilog for obvious syntax issues."""
    issues = []
    balanced = True

    # Check balanced begin/end
    begins = code.count("begin")
    ends = code.count("end")
    if begins != ends and not (begins == ends + 1):  # module end at EOF allowed
        if begins > ends:
            # Allow for missing final end in module context
            if begins - ends > 1:
                issues.append(f"Unbalanced begin/end: {begins} begin vs {ends} end")

    # Check balanced parentheses
    depth = 0
    for ch in code:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth < 0:
            balanced = False
            break
    if depth != 0 or not balanced:
        issues.append(f"Unbalanced parentheses (depth={depth})")

    # Check module declaration exists
    import re
    if not re.search(r'\bmodule\s+\w+', code):
        issues.append("No module declaration found")

    # Check for empty statements
    if ";;" in code:
        issues.append("Empty statement (;;)")

    return len(issues) == 0, issues