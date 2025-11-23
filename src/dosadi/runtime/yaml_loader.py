"""Minimal YAML loader for offline fixtures.

The repository intentionally avoids external dependencies in the execution
environment.  For the scenario harness we need to parse the documented
``S-0001_Pre_Sting_Quiet_Season.yaml`` fixture without pulling in PyYAML.

This module implements a tiny, indentation-driven YAML subset that supports:

* nested dictionaries and lists,
* quoted and unquoted scalars (strings, ints, floats, ``null``/``true``/``false``),
* folded ``>`` block scalars (flattened into a single line), and
* empty mappings expressed as ``{}`` or ``{{}}``.

It is **not** a general-purpose YAML parser; it only aims to cover the
structure used in the scenario documents under ``docs/latest``.  The goal is
to keep the loader small, deterministic, and dependency free so that tests can
exercise scenario loading in isolated CI sandboxes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Mapping, Tuple


class SimpleYAMLError(RuntimeError):
    """Raised when the simplified YAML parser encounters malformed input."""


def load_yaml_file(path: Path) -> Any:
    """Load the YAML file using the tiny subset parser."""

    text = path.read_text(encoding="utf-8")
    return load_yaml_string(text)


def load_yaml_string(text: str) -> Any:
    """Parse a YAML string using the supported subset."""

    preprocessed = _preprocess_blocks(text)
    lines = [line.rstrip("\n") for line in preprocessed.splitlines()]
    document, index = _parse_block(lines, 0, 0)
    # Ensure there are no trailing non-empty lines.
    while index < len(lines):
        if lines[index].strip():
            raise SimpleYAMLError(f"Unexpected trailing content on line {index + 1}: {lines[index]}")
        index += 1
    return document


def _preprocess_blocks(text: str) -> str:
    """Handle folded block scalars and template placeholders.

    * ``: >`` folded scalars are collapsed into a single quoted line so the
      indentation parser can treat them as a normal scalar.
    * ``{{}}`` placeholders (used in the docs to denote empty maps) are mapped
      to ``{}`` so they can be parsed as empty dictionaries.
    """

    lines = text.splitlines()
    output: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].replace("{{}}", "{}")
        if ": >" in line:
            indent = len(line) - len(line.lstrip(" "))
            key = line.split(": >", 1)[0].rstrip()
            i += 1
            folded: List[str] = []
            while i < len(lines):
                candidate = lines[i]
                if not candidate.strip():
                    folded.append("")
                    i += 1
                    continue
                candidate_indent = len(candidate) - len(candidate.lstrip(" "))
                if candidate_indent <= indent:
                    break
                folded.append(candidate.strip())
                i += 1
            flattened = " ".join(part for part in folded if part).strip()
            output.append(" " * indent + f"{key}: \"{flattened}\"")
            continue
        output.append(line)
        i += 1
    return "\n".join(output)


def _parse_block(lines: List[str], index: int, indent: int) -> Tuple[Any, int]:
    mode: str | None = None  # "map" or "list"
    mapping: dict[str, Any] = {}
    sequence: List[Any] = []
    i = index
    while i < len(lines):
        raw_line = lines[i]
        if not raw_line.strip():
            i += 1
            continue
        current_indent = len(raw_line) - len(raw_line.lstrip(" "))
        if current_indent < indent:
            break
        stripped = raw_line[current_indent:]
        if stripped.startswith("- "):
            if mode == "map":
                raise SimpleYAMLError(f"Mixing list and map content near line {i + 1}")
            mode = "list"
            item, i = _parse_list_item(lines, i, current_indent)
            sequence.append(item)
            continue
        if mode == "list":
            break
        mode = "map"
        key, value, has_value = _parse_key_value(stripped, i)
        i += 1
        if has_value:
            mapping[key] = value
            continue
        nested, i = _parse_block(lines, i, current_indent + 2)
        mapping[key] = nested
    if mode == "list":
        return sequence, i
    return mapping, i


def _parse_list_item(lines: List[str], index: int, indent: int) -> Tuple[Any, int]:
    raw_line = lines[index]
    stripped = raw_line[indent + 2 :]
    item_indent = indent + 2
    if not stripped:
        return _parse_block(lines, index + 1, item_indent)
    if ":" not in stripped:
        return _parse_scalar(stripped.strip(), index), index + 1
    key, value, has_value = _parse_key_value(stripped, index)
    i = index + 1
    if not has_value:
        nested, i = _parse_block(lines, i, item_indent)
        return {key: nested}, i
    if ":" in stripped:
        nested, i = _parse_block(lines, i, item_indent)
        if isinstance(nested, dict):
            nested = {**{key: value}, **nested}
        elif nested:
            raise SimpleYAMLError(f"Unexpected list payload near line {index + 1}")
        else:
            nested = {key: value}
        return nested, i
    return value, i


def _parse_key_value(segment: str, line_index: int) -> Tuple[str, Any, bool]:
    if ":" not in segment:
        return segment.strip(), None, False
    key, remainder = segment.split(":", 1)
    key = key.strip()
    value = remainder.strip()
    if not value:
        return key, None, False
    return key, _parse_scalar(value, line_index), True


def _parse_scalar(value: str, line_index: int) -> Any:
    lowered = value.lower()
    if lowered in {"null", "none"}:
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if value.startswith("\"") and value.endswith("\""):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value == "{}":
        return {}
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [] if not inner else [part.strip() for part in inner.split(",")]
    # Fallback: treat any remaining value as a string literal. The simplified
    # loader is intentionally forgiving when parsing documentation snippets
    # that include placeholders like "string" or union hints such as
    # "low | medium".
    return value


@dataclass(frozen=True)
class ParsedDocument:
    """Convenience wrapper for parsed scenario files."""

    content: Mapping[str, Any]

    @classmethod
    def from_file(cls, path: Path) -> "ParsedDocument":
        raw = load_yaml_file(path)
        if not isinstance(raw, Mapping):
            raise SimpleYAMLError("Top-level YAML content must be a mapping")
        return cls(raw)


__all__ = ["ParsedDocument", "SimpleYAMLError", "load_yaml_file", "load_yaml_string"]
