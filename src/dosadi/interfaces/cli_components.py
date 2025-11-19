"""Tiny text UI primitives used by CLI dashboards.

These helpers intentionally stay dependency-free so they can run inside unit
tests or bare notebooks.  They allow us to compose higher level admin views
without committing to a larger TUI/GUI stack.  Inspired by the "simple UI"
requirement that accompanies D-INTERFACE-0001.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence


@dataclass(slots=True)
class TableColumn:
    header: str
    width: int
    align: str = "left"

    def format(self, value: str) -> str:
        truncated = value[: self.width]
        if self.align == "right":
            return truncated.rjust(self.width)
        if self.align == "center":
            return truncated.center(self.width)
        return truncated.ljust(self.width)


@dataclass
class Table:
    columns: Sequence[TableColumn]
    rows: Sequence[Sequence[str]] = field(default_factory=list)

    def render(self) -> str:
        header = " | ".join(col.format(col.header.upper()) for col in self.columns)
        separator = "-+-".join("-" * col.width for col in self.columns)
        rendered_rows = [" | ".join(col.format(str(cell)) for col, cell in zip(self.columns, row)) for row in self.rows]
        return "\n".join([header, separator, *rendered_rows]) if rendered_rows else "\n".join([header, separator, "<empty>"])


@dataclass(slots=True)
class ProgressBar:
    value: float
    width: int = 20
    label: str | None = None

    def render(self) -> str:
        value = max(0.0, min(1.0, self.value))
        filled = int(round(value * self.width))
        empty = self.width - filled
        bar = f"{'█' * filled}{'░' * empty}"
        label = self.label or f"{int(value * 100):3d}%"
        return f"[{bar}] {label}"


@dataclass
class Section:
    title: str
    body_lines: Sequence[str]
    width: int = 80

    def render(self) -> str:
        width = max(self.width, len(self.title) + 4)
        border = "=" * width
        return "\n".join([border, self.title.center(width), border, *self._body(width)])

    def _body(self, width: int) -> Iterable[str]:
        for line in self.body_lines:
            if not line:
                yield ""
                continue
            if len(line) <= width:
                yield line
                continue
            start = 0
            while start < len(line):
                yield line[start : start + width]
                start += width


__all__ = ["Table", "TableColumn", "ProgressBar", "Section"]
