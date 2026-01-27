import os
import json
import shutil
from typing import Dict, Any, List
from backend.utils.path_config import path_manager

class OutputPackager:
    """
    Standardizes the packaging of analysis results.
    Bundles HTML report, raw data JSON, and a summary README.
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

        return package_path
