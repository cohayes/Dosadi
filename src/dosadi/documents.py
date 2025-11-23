"""Lightweight extraction of YAML blocks from the design documents.

The MIL, IND, and INFO document families embed machine-friendly YAML blocks
that act as canonical rows for force types, guild archetypes, rumor
templates, and alert schemas.  This module provides a thin parser that
extracts those blocks, normalises their shape, and indexes them by id so the
simulation can consume the documentation directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from .runtime.yaml_loader import SimpleYAMLError, load_yaml_string


@dataclass(slots=True)
class DocBlock:
    """Single YAML block embedded in a documentation page."""

    source: str
    section: Optional[str]
    root_key: Optional[str]
    payload: Mapping[str, object]
    id: Optional[str] = None


class DocCatalog:
    """Collection of :class:`DocBlock` instances with convenience indices."""

    def __init__(self, blocks: Iterable[DocBlock]):
        self.blocks: List[DocBlock] = list(blocks)
        self.by_id: Dict[str, DocBlock] = {}
        for block in self.blocks:
            if block.id:
                self.by_id[block.id] = block

    def filter(self, *, root_key: Optional[str] = None, section_contains: Optional[str] = None) -> List[DocBlock]:
        """Return blocks matching the optional filters."""

        matches: List[DocBlock] = []
        for block in self.blocks:
            if root_key and block.root_key != root_key:
                continue
            if section_contains and (not block.section or section_contains not in block.section):
                continue
            matches.append(block)
        return matches


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _extract_yaml_blocks(path: Path) -> List[DocBlock]:
    text = path.read_text(encoding="utf-8")
    heading: Optional[str] = None
    blocks: List[DocBlock] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("###"):
            heading = stripped.lstrip("# ")
            i += 1
            continue
        if stripped == "```yaml":
            block_lines: List[str] = []
            i += 1
            while i < len(lines) and lines[i].strip() != "```":
                block_lines.append(lines[i])
                i += 1
            try:
                payload, root_key, identifier = _parse_block("\n".join(block_lines))
            except SimpleYAMLError:
                continue
            try:
                relative_source = path.resolve().relative_to(_repository_root())
            except ValueError:
                relative_source = path
            blocks.append(
                DocBlock(
                    source=str(relative_source),
                    section=heading,
                    root_key=root_key,
                    payload=payload,
                    id=identifier,
                )
            )
        i += 1
    return blocks


def _strip_inline_comment(line: str) -> str:
    """Remove trailing ``#`` comments outside of quoted strings."""

    cleaned: List[str] = []
    in_quote: Optional[str] = None
    for char in line:
        if char in {'"', "'"}:
            in_quote = None if in_quote == char else char
            cleaned.append(char)
            continue
        if char == "#" and in_quote is None:
            break
        cleaned.append(char)
    return "".join(cleaned).rstrip()


def _sanitize_block(text: str) -> str:
    return "\n".join(_strip_inline_comment(line) for line in text.splitlines())


def _parse_block(text: str) -> tuple[Mapping[str, object], Optional[str], Optional[str]]:
    try:
        parsed = load_yaml_string(_sanitize_block(text))
    except SimpleYAMLError as exc:
        raise SimpleYAMLError(f"Failed to parse YAML block: {exc}") from exc

    root_key: Optional[str] = None
    payload: Mapping[str, object]
    if isinstance(parsed, Mapping) and len(parsed) == 1 and isinstance(next(iter(parsed.values())), Mapping):
        root_key = next(iter(parsed))
        payload = parsed[root_key]
    elif isinstance(parsed, Mapping):
        payload = parsed
    else:
        payload = {"value": parsed}
    identifier = _extract_id(payload)
    return payload, root_key, identifier


def _extract_id(payload: Mapping[str, object]) -> Optional[str]:
    if not isinstance(payload, Mapping):
        return None
    raw_id = payload.get("id")
    if isinstance(raw_id, str) and raw_id.strip():
        value = raw_id.strip()
        if value.lower() in {"string", "id"}:
            return None
        return value
    return None


def _load_catalog(doc_glob: str) -> DocCatalog:
    root = _repository_root()
    blocks: List[DocBlock] = []
    for path in sorted(root.glob(doc_glob)):
        blocks.extend(_extract_yaml_blocks(path))
    return DocCatalog(blocks)


def load_industry_catalog() -> DocCatalog:
    """Parse YAML blocks from the IND document set."""

    return _load_catalog("docs/latest/13_industry/D-IND-*.md")


def load_military_catalog() -> DocCatalog:
    """Parse YAML blocks from the MIL document set."""

    return _load_catalog("docs/latest/14_military/D-MIL-*.md")


def load_info_security_catalog() -> DocCatalog:
    """Parse YAML blocks from the INFO document set."""

    root = _repository_root()
    blocks: List[DocBlock] = []
    for pattern in (
        "docs/latest/08_info_security/D-INFO-*.md",
        "docs/latest/08_info_security/Rumor_Templates_and_Motifs.md",
    ):
        for path in sorted(root.glob(pattern)):
            blocks.extend(_extract_yaml_blocks(path))
    return DocCatalog(blocks)


__all__ = [
    "DocBlock",
    "DocCatalog",
    "load_industry_catalog",
    "load_military_catalog",
    "load_info_security_catalog",
]
