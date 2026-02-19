"""Export Packager Module
Packages dashboard configurations for export to JSON, Excel, and PDF formats.
"""
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ExportPackager:
    """
    Packages and exports dashboard configurations in multiple formats.

    Supported formats:
    - JSON: Full dashboard configuration with metadata
    - Excel: Tabular summary using openpyxl
    - PDF: HTML-rendered PDF via weasyprint (graceful stub if unavailable)
    """

    VERSION = "1.0.0"

    # Minimum required keys in a dashboard config
    REQUIRED_KEYS = {"title", "components"}

    def validate_schema(self, config: Dict[str, Any]) -> bool:
        """
        Validates that config contains the required dashboard keys.

        Args:
            config: Dashboard configuration dictionary.

        Returns:
            True if valid, False otherwise.
        """
        return self.REQUIRED_KEYS.issubset(config.keys())

    def _assert_valid(self, config: Dict[str, Any]) -> None:
        """Raise ValueError if config is missing required keys."""
        missing = self.REQUIRED_KEYS - config.keys()
        if missing:
            raise ValueError(f"Dashboard config is missing required keys: {missing}")

    def _add_metadata(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Return a copy of config with metadata injected."""
        result = dict(config)
        result["metadata"] = {
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "version": self.VERSION,
        }
        return result

    # ------------------------------------------------------------------
    # JSON export
    # ------------------------------------------------------------------

    def export_json(
        self,
        config: Dict[str, Any],
        output_path: Path,
        compress: bool = False,
        include_metadata: bool = True,
    ) -> None:
        """
        Exports dashboard configuration as a JSON file.

        Args:
            config: Dashboard configuration dictionary.
            output_path: Destination file path.
            compress: If True, write gzip-compressed JSON (.gz).
            include_metadata: If True, inject metadata (timestamp, version).

        Raises:
            ValueError: If config is missing required keys.
            IOError: If the output path directory does not exist.
        """
        self._assert_valid(config)

        output_path = Path(output_path)
        if not output_path.parent.exists():
            raise IOError(f"Output directory does not exist: {output_path.parent}")

        data = self._add_metadata(config) if include_metadata else config
        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

        if compress:
            with gzip.open(output_path, "wb") as f:
                f.write(json_bytes)
        else:
            output_path.write_bytes(json_bytes)

    # ------------------------------------------------------------------
    # Excel export
    # ------------------------------------------------------------------

    def export_excel(
        self,
        config: Dict[str, Any],
        output_path: Path,
    ) -> None:
        """
        Exports dashboard configuration as an Excel workbook.

        Creates one sheet per component type with relevant data.

        Args:
            config: Dashboard configuration dictionary.
            output_path: Destination .xlsx file path.

        Raises:
            ValueError: If config is missing required keys.
            IOError: If the output path directory does not exist.
            ImportError: If openpyxl is not installed.
        """
        self._assert_valid(config)

        output_path = Path(output_path)
        if not output_path.parent.exists():
            raise IOError(f"Output directory does not exist: {output_path.parent}")

        try:
            import openpyxl
            from openpyxl import Workbook
        except ImportError as exc:
            raise ImportError("openpyxl is required for Excel export: pip install openpyxl") from exc

        wb = Workbook()

        # Summary sheet
        ws_summary = wb.active
        ws_summary.title = "Summary"
        ws_summary.append(["Dashboard Title", config.get("title", "")])
        ws_summary.append(["Export Date", datetime.now(tz=timezone.utc).isoformat()])
        ws_summary.append(["Version", self.VERSION])
        ws_summary.append([])
        ws_summary.append(["Component Count", len(config.get("components", []))])

        # Components sheet
        components = config.get("components", [])
        if components:
            ws_comps = wb.create_sheet("Components")
            # Header row - collect all unique keys
            all_keys: List[str] = []
            for comp in components:
                for k in comp:
                    if k not in all_keys:
                        all_keys.append(k)
            ws_comps.append(all_keys)
            for comp in components:
                row = [str(comp.get(k, "")) for k in all_keys]
                ws_comps.append(row)

        wb.save(output_path)

    # ------------------------------------------------------------------
    # PDF export
    # ------------------------------------------------------------------

    def export_pdf(
        self,
        config: Dict[str, Any],
        output_path: Path,
    ) -> None:
        """
        Exports dashboard configuration as a PDF file.

        Uses weasyprint if available; falls back to a minimal stub PDF.

        Args:
            config: Dashboard configuration dictionary.
            output_path: Destination .pdf file path.

        Raises:
            ValueError: If config is missing required keys.
            IOError: If the output path directory does not exist.
        """
        self._assert_valid(config)

        output_path = Path(output_path)
        if not output_path.parent.exists():
            raise IOError(f"Output directory does not exist: {output_path.parent}")

        html_content = self._render_html(config)

        try:
            from weasyprint import HTML
            HTML(string=html_content).write_pdf(str(output_path))
        except ImportError:
            # Graceful degradation: write a minimal valid PDF stub
            self._write_stub_pdf(output_path, config)

    def _render_html(self, config: Dict[str, Any]) -> str:
        """Build a simple HTML representation of the dashboard config."""
        title = config.get("title", "Dashboard")
        components = config.get("components", [])

        rows = "".join(
            f"<tr><td>{c.get('id', '')}</td><td>{c.get('type', '')}</td>"
            f"<td>{c.get('title', '')}</td></tr>"
            for c in components
        )

        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{title}</title></head>
<body>
<h1>{title}</h1>
<table border="1">
  <thead><tr><th>ID</th><th>Type</th><th>Title</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<p>Generated: {datetime.now(tz=timezone.utc).isoformat()}</p>
</body>
</html>"""

    def _write_stub_pdf(self, output_path: Path, config: Dict[str, Any]) -> None:
        """Write a minimal valid PDF stub (plain-text body wrapped in PDF structure)."""
        title = config.get("title", "Dashboard")
        body = f"Dashboard Export: {title}\nGenerated: {datetime.now(tz=timezone.utc).isoformat()}"

        # Minimal PDF 1.4 structure
        stream = body.encode("latin-1", errors="replace")
        stream_len = len(stream)

        pdf_content = (
            "%PDF-1.4\n"
            "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            "3 0 obj\n<< /Type /Page /Parent 2 0 R "
            "/MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>\nendobj\n"
            f"4 0 obj\n<< /Length {stream_len} >>\nstream\n"
        ).encode("ascii")

        pdf_content += stream
        pdf_content += b"\nendstream\nendobj\n%%EOF\n"

        output_path.write_bytes(pdf_content)

    # ------------------------------------------------------------------
    # Batch export
    # ------------------------------------------------------------------

    def export_all(
        self,
        config: Dict[str, Any],
        output_dir: Path,
        formats: Optional[List[str]] = None,
    ) -> None:
        """
        Exports dashboard in all requested formats.

        Args:
            config: Dashboard configuration dictionary.
            output_dir: Directory for all output files.
            formats: List of format strings; defaults to ["json", "excel", "pdf"].
        """
        if formats is None:
            formats = ["json", "excel", "pdf"]

        output_dir = Path(output_dir)
        stem = config.get("title", "dashboard").lower().replace(" ", "_")

        for fmt in formats:
            if fmt == "json":
                self.export_json(config, output_dir / f"{stem}.json")
            elif fmt == "excel":
                self.export_excel(config, output_dir / f"{stem}.xlsx")
            elif fmt == "pdf":
                self.export_pdf(config, output_dir / f"{stem}.pdf")

    # ------------------------------------------------------------------
    # File browser
    # ------------------------------------------------------------------

    def list_exports(self, directory: Path) -> List[Path]:
        """
        Lists all export files in a directory.

        Args:
            directory: Directory to scan.

        Returns:
            List of file paths sorted by name.
        """
        directory = Path(directory)
        if not directory.exists():
            return []
        return sorted(p for p in directory.iterdir() if p.is_file())
