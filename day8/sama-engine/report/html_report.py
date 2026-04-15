"""HTML compliance report generator — professional dark-sidebar design."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .json_report import ComplianceReport

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_TEMPLATE_FILE = "report.html.j2"


class HTMLReporter:
    """Render a ComplianceReport as a self-contained HTML page."""

    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, report: ComplianceReport) -> str:
        template = self._env.get_template(_TEMPLATE_FILE)
        return template.render(report=report)

    def write(self, report: ComplianceReport, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.render(report))
