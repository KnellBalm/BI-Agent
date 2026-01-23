"""Theme Engine Module
Provides consistent styling, color palettes, and layout tokens for BI dashboards.
"""
from typing import Dict, Any

class ThemeEngine:
    """
    Manages visual themes (Dark, Light, Premium) and provides style objects
    for BI components.
    """

    PALETTES = {
        "premium_dark": {
            "background": "#0F172A",
            "card_bg": "#1E293B",
            "primary": "#38BDF8",
            "secondary": "#818CF8",
            "accent": "#F472B6",
            "text": "#F8FAFC",
            "subtext": "#94A3B8",
            "chart_colors": ["#38BDF8", "#818CF8", "#F472B6", "#FB923C", "#4ADE80"]
        },
        "corporate_light": {
            "background": "#FFFFFF",
            "card_bg": "#F8FAFC",
            "primary": "#2563EB",
            "secondary": "#475569",
            "accent": "#EA580C",
            "text": "#1E293B",
            "subtext": "#64748B",
            "chart_colors": ["#2563EB", "#475569", "#EA580C", "#16A34A", "#D97706"]
        }
    }

    def __init__(self, theme_name: str = "premium_dark"):
        self.theme = self.PALETTES.get(theme_name, self.PALETTES["premium_dark"])

    def get_style(self, component_type: str) -> Dict[str, Any]:
        """Returns style options for a specific component type."""
        base_style = {
            "fontFamily": "Inter, Roboto, sans-serif",
            "textColor": self.theme["text"],
            "backgroundColor": self.theme["card_bg"],
            "borderRadius": "8px",
            "padding": "16px"
        }

        if component_type in ["BarChart", "LineChart", "PieChart"]:
            return {
                **base_style,
                "colors": self.theme["chart_colors"],
                "gridColor": self.theme["subtext"],
                "axisColor": self.theme["text"]
            }
        elif component_type == "Label":
            return {
                **base_style,
                "fontSize": "24px",
                "fontWeight": "bold",
                "color": self.theme["primary"]
            }
        elif component_type.endswith("Filter"):
            return {
                **base_style,
                "borderColor": self.theme["primary"],
                "hoverColor": self.theme["secondary"]
            }
        
        return base_style

    def get_layout_tokens(self) -> Dict[str, int]:
        """Returns standard layout units (e.g. grid spacing)."""
        return {
            "margin": 10,
            "padding": 20,
            "grid_cols": 12
        }
