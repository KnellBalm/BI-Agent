import os
import json
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path
import pandas as pd
from backend.utils.path_config import path_manager

# Optional dependencies for Excel/PDF export
try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    from weasyprint import HTML
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class OutputPackager:
    """
    Standardizes the packaging of analysis results.
    Bundles HTML report, raw data JSON, and a summary README.

    Step 15 enhancement: Excel/PDF export support.
    """
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.base_dir = path_manager.get_project_path(project_id) / "packages"
        self.base_dir.mkdir(exist_ok=True)

    def package_result(self, result_name: str, analysis_result: Dict[str, Any]) -> str:
        """
        Creates a structured package folder for the analysis result.
        Returns the path to the package directory.
        """
        safe_name = result_name.replace(" ", "_").lower()
        package_path = self.base_dir / safe_name
        package_path.mkdir(exist_ok=True)

        # 1. Save summary reasoning/README
        readme_path = os.path.join(package_path, "INSIGHTS.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"# Analysis Insights: {result_name}\n\n")
            f.write(f"## Reasoning\n{analysis_result.get('reasoning', 'N/A')}\n\n")
            f.write(f"## Summary\n{json.dumps(analysis_result.get('summary', {}), indent=2)}\n\n")

            proactive = analysis_result.get("proactive_questions", [])
            if proactive:
                f.write("## Recommended Next Steps\n")
                for q in proactive:
                    f.write(f"- {q}\n")

        # 2. Copy/Link Dashboard if exists
        dash_url = analysis_result.get("dashboard_url")
        if dash_url and os.path.exists(dash_url):
            dest_html = os.path.join(package_path, "dashboard.html")
            shutil.copy(dash_url, dest_html)

        # 3. Save raw result as JSON
        raw_json_path = os.path.join(package_path, "metadata.json")
        with open(raw_json_path, "w", encoding="utf-8") as f:
            json.dump(analysis_result, f, indent=2)

        return str(package_path)

    def export_to_excel(
        self,
        data: pd.DataFrame,
        output_path: str,
        sheet_name: str = "Data",
        summary: Optional[Dict[str, Any]] = None,
        chart_settings: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Export data to Excel file with formatting

        Args:
            data: DataFrame to export
            output_path: Output file path (.xlsx)
            sheet_name: Sheet name for data
            summary: Optional summary data for separate sheet
            chart_settings: Optional chart configuration

        Returns:
            Path to generated Excel file

        Raises:
            ImportError: If openpyxl is not installed
        """
        if not EXCEL_AVAILABLE:
            raise ImportError(
                "openpyxl is required for Excel export. "
                "Install it with: pip install openpyxl"
            )

        # Create Excel writer
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Write main data
            data.to_excel(writer, sheet_name=sheet_name, index=False)

            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]

            # Apply header formatting
            header_fill = PatternFill(start_color="38BDF8", end_color="38BDF8", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF")

            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter

                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass

                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

            # Add summary sheet if provided
            if summary:
                summary_df = pd.DataFrame([summary]).T
                summary_df.columns = ["Value"]
                summary_df.to_excel(writer, sheet_name="Summary")

                # Format summary sheet
                summary_ws = writer.sheets["Summary"]
                for cell in summary_ws["A"]:
                    cell.font = Font(bold=True)

            # Add chart settings sheet if provided
            if chart_settings:
                settings_df = pd.DataFrame([chart_settings])
                settings_df.to_excel(writer, sheet_name="Chart Settings", index=False)

        return output_path

    def export_to_pdf(
        self,
        html_content: str,
        output_path: str,
        css_path: Optional[str] = None
    ) -> str:
        """
        Export HTML content to PDF

        Args:
            html_content: HTML content or file path
            output_path: Output PDF file path
            css_path: Optional CSS file path for styling

        Returns:
            Path to generated PDF file

        Raises:
            ImportError: If weasyprint is not installed
        """
        if not PDF_AVAILABLE:
            raise ImportError(
                "weasyprint is required for PDF export. "
                "Install it with: pip install weasyprint"
            )

        # Check if html_content is a file path
        if os.path.exists(html_content):
            html = HTML(filename=html_content)
        else:
            html = HTML(string=html_content)

        # Generate PDF
        if css_path and os.path.exists(css_path):
            html.write_pdf(output_path, stylesheets=[css_path])
        else:
            html.write_pdf(output_path)

        return output_path

    def create_full_package(
        self,
        result_name: str,
        analysis_result: Dict[str, Any],
        data: Optional[pd.DataFrame] = None,
        export_formats: List[str] = None
    ) -> Dict[str, str]:
        """
        Create a complete package with multiple export formats

        Args:
            result_name: Name of the analysis result
            analysis_result: Analysis result dictionary
            data: Optional DataFrame for Excel export
            export_formats: List of formats to export ["excel", "pdf", "json", "html"]

        Returns:
            Dictionary of format -> file path
        """
        if export_formats is None:
            export_formats = ["json", "html"]

        # Create base package
        package_path = self.package_result(result_name, analysis_result)
        exported_files = {
            "package_dir": package_path,
            "metadata": os.path.join(package_path, "metadata.json"),
            "insights": os.path.join(package_path, "INSIGHTS.md")
        }

        # Excel export
        if "excel" in export_formats and data is not None and EXCEL_AVAILABLE:
            try:
                excel_path = os.path.join(package_path, f"{result_name}.xlsx")
                summary = analysis_result.get("summary", {})

                self.export_to_excel(
                    data=data,
                    output_path=excel_path,
                    summary=summary
                )
                exported_files["excel"] = excel_path
            except Exception as e:
                print(f"[OutputPackager] Excel export failed: {e}")

        # PDF export
        if "pdf" in export_formats and PDF_AVAILABLE:
            try:
                html_path = analysis_result.get("dashboard_url")
                if html_path and os.path.exists(html_path):
                    pdf_path = os.path.join(package_path, f"{result_name}.pdf")
                    self.export_to_pdf(html_path, pdf_path)
                    exported_files["pdf"] = pdf_path
            except Exception as e:
                print(f"[OutputPackager] PDF export failed: {e}")

        # HTML (already handled in package_result)
        html_path = os.path.join(package_path, "dashboard.html")
        if os.path.exists(html_path):
            exported_files["html"] = html_path

        return exported_files

    def get_export_capabilities(self) -> Dict[str, bool]:
        """
        Check which export formats are available

        Returns:
            Dictionary of format -> availability
        """
        return {
            "excel": EXCEL_AVAILABLE,
            "pdf": PDF_AVAILABLE,
            "json": True,
            "html": True,
            "markdown": True
        }
