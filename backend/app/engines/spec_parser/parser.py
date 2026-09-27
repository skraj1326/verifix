"""Specification Parser Engine - Extracts structured requirements from documents."""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class RequirementCategory(str, Enum):
    FUNCTIONAL = "functional"
    TIMING = "timing"
    PROTOCOL = "protocol"
    RESET = "reset"
    ERROR_HANDLING = "error_handling"
    PERFORMANCE = "performance"
    POWER = "power"
    SECURITY = "security"
    CORNER_CASE = "corner_case"


class RequirementSource(str, Enum):
    SPECIFICATION = "specification"
    ARCHITECTURE = "architecture"
    DESIGN_DOC = "design_doc"
    INFORMAL = "informal"


@dataclass
class Requirement:
    id: str
    category: RequirementCategory
    title: str
    description: str
    source: RequirementSource = RequirementSource.SPECIFICATION
    source_location: str = ""
    priority: int = 5  # 1=highest, 10=lowest
    tags: list[str] = field(default_factory=list)
    related_signals: list[str] = field(default_factory=list)
    verification_method: str = "simulation"  # simulation, formal, emulation
    acceptance_criteria: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class Specification:
    filename: str
    content: str
    requirements: list[Requirement] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class SpecParser:
    """Parses specification documents (Markdown, PDF, Word) into structured requirements."""

    def __init__(self):
        self.requirement_counter = 0
        self._requirement_id_prefix = "REQ"

    def parse(self, content: str, filename: str = "spec.md",
              doc_type: str = "markdown") -> Specification:
        """Parse specification content into structured requirements."""
        spec = Specification(filename=filename, content=content)

        if doc_type == "markdown" or filename.endswith(".md"):
            spec.requirements = self._parse_markdown(content)
        elif doc_type == "pdf" or filename.endswith(".pdf"):
            spec.requirements = self._parse_pdf(content)
        elif doc_type == "word" or filename.endswith(".docx"):
            spec.requirements = self._parse_word(content)
        else:
            # Try to auto-detect
            spec.requirements = self._parse_generic(content)

        spec.metadata = {
            "total_requirements": len(spec.requirements),
            "by_category": self._count_by_category(spec.requirements),
            "by_priority": self._count_by_priority(spec.requirements),
        }

        return spec

    def _parse_markdown(self, content: str) -> list[Requirement]:
        """Parse Markdown specification into requirements."""
        requirements = []

        # Pattern 1: Structured tables with requirements
        table_reqs = self._parse_markdown_tables(content)
        requirements.extend(table_reqs)

        # Pattern 2: Numbered lists with requirement-like text
        list_reqs = self._parse_markdown_lists(content)
        requirements.extend(list_reqs)

        # Pattern 3: Headers with requirement keywords
        header_reqs = self._parse_markdown_headers(content)
        requirements.extend(header_reqs)

        # Deduplicate by ID
        seen_ids = set()
        unique_reqs = []
        for req in requirements:
            if req.id not in seen_ids:
                seen_ids.add(req.id)
                unique_reqs.append(req)

        return unique_reqs

    def _parse_markdown_tables(self, content: str) -> list[Requirement]:
        """Parse markdown tables containing requirements."""
        requirements = []

        # Find markdown tables
        table_pattern = re.compile(
            r'\|.*?\|[\r\n]+\|[-:| ]+\|[\r\n]+((?:\|.*?\|[\r\n]+)*)',
            re.MULTILINE
        )

        for match in table_pattern.finditer(content):
            header_line = content[match.start():match.start()+200].split('\n')[0]
            if not self._is_requirement_table(header_line):
                continue

            rows = match.group(1).strip().split('\n')
            for row in rows:
                req = self._parse_table_row(row)
                if req:
                    requirements.append(req)

        return requirements

    def _is_requirement_table(self, header: str) -> bool:
        """Check if a markdown table header indicates requirements."""
        header_lower = header.lower()
        req_keywords = ["requirement", "req", "id", "description", "priority",
                        "category", "title", "spec"]
        return any(kw in header_lower for kw in req_keywords)

    def _parse_table_row(self, row: str) -> Optional[Requirement]:
        """Parse a single table row into a requirement."""
        cells = [cell.strip() for cell in row.split('|') if cell.strip()]
        if len(cells) < 2:
            return None

        # Try to identify columns
        req_id = ""
        title = ""
        description = ""
        category = RequirementCategory.FUNCTIONAL
        priority = 5

        for i, cell in enumerate(cells):
            if re.match(r'REQ-\w+', cell, re.IGNORECASE) or re.match(r'\d+\.\d+', cell):
                req_id = cell.upper()
            elif i == 0 and not req_id:
                req_id = cell
            elif not title:
                title = cell
            elif not description:
                description = cell

        if not req_id:
            self.requirement_counter += 1
            req_id = f"{self._requirement_id_prefix}-{self.requirement_counter:03d}"

        # Infer category from content
        category = self._infer_category(title + " " + description)

        return Requirement(
            id=req_id,
            category=category,
            title=title or "Untitled Requirement",
            description=description or title,
            priority=priority,
            source=RequirementSource.SPECIFICATION,
        )

    def _parse_markdown_lists(self, content: str) -> list[Requirement]:
        """Parse numbered/bulleted lists that look like requirements."""
        requirements = []

        # Pattern: numbered items with requirement language
        patterns = [
            r'^\s*(\d+[\.\)]\s+)(.+)$',  # 1. Requirement text
            r'^\s*[-*]\s+\[?REQ[-_]?(\d+)\]?\s*(.+)$',  # - REQ-1: text
            r'^\s*[-*]\s+(REQ-\w+)\s*:?\s*(.+)$',  # - REQ-001: text
        ]

        lines = content.split('\n')
        for i, line in enumerate(lines):
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    req_id = match.group(1).strip() if match.lastindex >= 1 else ""
                    text = match.group(match.lastindex).strip()

                    # Clean up requirement ID
                    if re.match(r'\d+[\.\)]', req_id):
                        # Numbered list item
                        self.requirement_counter += 1
                        req_id = f"{self._requirement_id_prefix}-{self.requirement_counter:03d}"

                    category = self._infer_category(text)
                    priority = self._infer_priority(text)

                    requirements.append(Requirement(
                        id=req_id,
                        category=category,
                        title=self._extract_title(text),
                        description=text,
                        priority=priority,
                        source=RequirementSource.SPECIFICATION,
                        source_location=f"line:{i+1}",
                    ))
                    break

        return requirements

    def _parse_markdown_headers(self, content: str) -> list[Requirement]:
        """Parse headers that indicate requirements sections."""
        requirements = []

        header_pattern = re.compile(
            r'^(#{2,4})\s+(.+)$',
            re.MULTILINE
        )

        lines = content.split('\n')
        for i, line in enumerate(lines):
            match = header_pattern.match(line)
            if match:
                header_text = match.group(2).strip()
                # Check if this looks like a requirement section
                if self._looks_like_requirement(header_text):
                    self.requirement_counter += 1
                    req_id = f"{self._requirement_id_prefix}-{self.requirement_counter:03d}"
                    category = self._infer_category(header_text)

                    # Get content until next header
                    content_lines = []
                    for j in range(i + 1, min(i + 20, len(lines))):
                        if lines[j].startswith('#'):
                            break
                        content_lines.append(lines[j])

                    requirements.append(Requirement(
                        id=req_id,
                        category=category,
                        title=header_text,
                        description='\n'.join(content_lines).strip() or header_text,
                        priority=5,
                        source=RequirementSource.SPECIFICATION,
                        source_location=f"line:{i+1}",
                    ))

        return requirements

    def _parse_generic(self, content: str) -> list[Requirement]:
        """Generic parser for plain text specifications."""
        requirements = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Look for requirement-like patterns
            if self._looks_like_requirement(line):
                self.requirement_counter += 1
                req_id = f"{self._requirement_id_prefix}-{self.requirement_counter:03d}"
                category = self._infer_category(line)

                requirements.append(Requirement(
                    id=req_id,
                    category=category,
                    title=self._extract_title(line),
                    description=line,
                    priority=self._infer_priority(line),
                    source=RequirementSource.INFORMAL,
                    source_location=f"line:{i+1}",
                ))

        return requirements

    def _parse_pdf(self, content: str) -> list[Requirement]:
        """Parse PDF content (extracted text)."""
        # PDF text is typically plain text, use generic parser
        return self._parse_generic(content)

    def _parse_word(self, content: str) -> list[Requirement]:
        """Parse Word document content."""
        # Word documents converted to text, use generic parser
        return self._parse_generic(content)

    def _looks_like_requirement(self, text: str) -> bool:
        """Heuristic: does this text look like a requirement?"""
        text_lower = text.lower()
        req_indicators = [
            "shall", "must", "should", "will", "require",
            "verify", "test", "ensure", "guarantee",
            "not allow", "prevent", "detect", "handle"
        ]
        return any(indicator in text_lower for indicator in req_indicators)

    def _infer_category(self, text: str) -> RequirementCategory:
        """Infer requirement category from text."""
        text_lower = text.lower()

        category_keywords = {
            RequirementCategory.TIMING: ["timing", "clock", "cycle", "latency", "setup", "hold", "frequency"],
            RequirementCategory.PROTOCOL: ["protocol", "handshake", "interface", "axi", "valid", "ready", "bus"],
            RequirementCategory.RESET: ["reset", "power-up", "initialization", "por"],
            RequirementCategory.ERROR_HANDLING: ["error", "exception", "fault", "overflow", "underflow", "invalid"],
            RequirementCategory.PERFORMANCE: ["throughput", "bandwidth", "performance", "speed", "rate"],
            RequirementCategory.POWER: ["power", "energy", "low power", "sleep", "wakeup"],
            RequirementCategory.SECURITY: ["security", "encryption", "authentication", "access control", "trust"],
            RequirementCategory.CORNER_CASE: ["corner", "boundary", "edge case", "maximum", "minimum", "extreme"],
        }

        for category, keywords in category_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return category

        return RequirementCategory.FUNCTIONAL

    def _infer_priority(self, text: str) -> int:
        """Infer priority from requirement text."""
        text_lower = text.lower()

        if any(kw in text_lower for kw in ["critical", "must", "shall", "safety", "security"]):
            return 1
        if any(kw in text_lower for kw in ["important", "key", "primary", "essential"]):
            return 3
        if any(kw in text_lower for kw in ["should", "recommended", "preferable"]):
            return 5
        if any(kw in text_lower for kw in ["may", "optional", "nice to have", "future"]):
            return 8

        return 5

    def _extract_title(self, text: str) -> str:
        """Extract a concise title from requirement text."""
        # Take first sentence or first 80 chars
        sentences = re.split(r'[.!?]', text)
        if sentences:
            title = sentences[0].strip()
            if len(title) > 80:
                title = title[:77] + "..."
            return title
        return text[:80]

    def _count_by_category(self, requirements: list[Requirement]) -> dict:
        counts = {}
        for req in requirements:
            cat = req.category.value
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def _count_by_priority(self, requirements: list[Requirement]) -> dict:
        counts = {}
        for req in requirements:
            counts[str(req.priority)] = counts.get(str(req.priority), 0) + 1
        return counts


# Convenience function
def parse_specification(content: str, filename: str = "spec.md",
                         doc_type: str = "markdown") -> Specification:
    """Parse a specification document into structured requirements."""
    parser = SpecParser()
    return parser.parse(content, filename, doc_type)