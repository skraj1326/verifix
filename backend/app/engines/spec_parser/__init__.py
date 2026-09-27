"""Specification Parser Engine - Extracts structured requirements from documents."""

from .parser import SpecParser, Requirement, Specification, RequirementCategory, RequirementSource, parse_specification

__all__ = [
    "SpecParser",
    "Requirement",
    "Specification",
    "RequirementCategory",
    "RequirementSource",
    "parse_specification",
]