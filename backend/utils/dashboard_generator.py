import json
import os
import webbrowser
from typing import Dict, Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from backend.utils.path_config import path_manager

class DashboardGenerator:
    """
    Generates a local interactive HTML dashboard from BI-Agent analysis results.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.output_dir = path_manager.get_output_path(project_id)

    def generate_dashboard(self, analysis_result: Dict[str, Any], data_df: pd.DataFrame = None) -> str:
        """
        Creates an HTML file and returns the path.
        """
        summary = analysis_result.get("summary", {})
        table_name = summary.get("table", "Unknown Table")
        visuals = summary.get("visuals", [])
        
        # Build Title & Basic Info
        html_content = f"""
        <html>
        <head>
            <title>BI-Agent Insights: {table_name}</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --bg: #020617;
                    --card: rgba(30, 41, 59, 0.7);
                    --accent: #38bdf8;
                    --accent-soft: rgba(56, 189, 248, 0.1);
                    --text: #f8fafc;
                    --text-dim: #94a3b8;
                }}
                body {{ 
                    font-family: 'Outfit', sans-serif; 
                    background: var(--bg); 
                    color: var(--text); 
                    padding: 40px;
                    margin: 0;
                    line-height: 1.6;
                }}
                .container {{ max-width: 1400px; margin: auto; }}
                header {{ margin-bottom: 40px; }}
                h1 {{ 
                    font-weight: 600; 
                    font-size: 2.5rem;
                    color: var(--accent); 
                    margin: 0;
                    letter-spacing: -0.02em;
                }}
                .card {{ 
                    background: var(--card); 
                    backdrop-filter: blur(8px);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 20px; 
                    padding: 30px; 
                    margin-bottom: 24px; 
                    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
                }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 30px; }}
                .reasoning-card {{ border-left: 4px solid var(--accent); }}
                .proactive {{ 
                    background: var(--accent-soft); 
                    border: 1px solid var(--accent);
                    color: var(--accent);
                    padding: 25px; 
                }}
                .proactive h3 {{ margin-top: 0; color: var(--accent); }}
                .proactive ul {{ padding-left: 20px; }}
                .badge {{
                    display: inline-block;
                    padding: 4px 12px;
                    background: var(--accent-soft);
                    color: var(--accent);
                    border-radius: 100px;
                    font-size: 0.8rem;
                    font-weight: 600;
                    margin-bottom: 12px;
                }}
                h3 {{ font-weight: 600; color: var(--text); margin-bottom: 15px; }}
                p {{ color: var(--text-dim); }}
                li {{ margin-bottom: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <span class="badge">BI-AGENT ANALYSIS REPORT</span>
                    <h1>📊 {table_name.capitalize()} Insights</h1>
                </header>
                
                <div class="card reasoning-card">
                    <h3>Analytical Reasoning</h3>
                    <p>{analysis_result.get('reasoning', '데이터 흐름과 목적에 기반한 전략적 분석이 수행되었습니다.')}</p>
                </div>
                
                <div class="grid">
        """
        
        # Add Visuals (Enhanced placeholders for now)
        for i, v_type in enumerate(visuals):
            div_id = f"chart_{i}"
            html_content += f"""
            <div class="card">
                <h3>{v_type} Exploration</h3>
                <div id="{div_id}" style="height: 400px; width: 100%;"></div>
            </div>
            """
        
        # Add Proactive Questions (Enhanced Box)
        proactive = analysis_result.get("proactive_questions", [])
        if proactive:
            html_content += """
            <div class="card proactive">
                <h3>💡 Strategic Follow-up Questions</h3>
                <p>데이터의 숨겨진 가치를 발굴하기 위한 추가 분석 제안입니다.</p>
                <ul>
            """
            for q in proactive:
                html_content += f"<li>{q}</li>"
            html_content += "</ul></div>"
            
        html_content += """
                </div>
            </div>
            <footer style="text-align: center; margin-top: 60px; color: #475569; font-size: 0.9rem;">
                Generated by BI-Agent Proactive Core &copy; 2026
            </footer>
        </body>
        </html>
        """
        
        file_path = os.path.join(self.output_dir, f"report_{table_name}.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        return file_path

    def open_in_browser(self, file_path: str):
        """Opens the generated dashboard in the default browser."""
        abs_path = os.path.abspath(file_path)
        webbrowser.open(f"file://{abs_path}")
