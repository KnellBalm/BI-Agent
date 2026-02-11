"""Chart Recommender Module
Analyzes data characteristics and recommends appropriate chart types.
"""
from typing import Dict, Any, List, Optional
from collections import Counter


class ChartRecommender:
    """
    Recommends chart types based on data profiling results.
    Uses heuristics to match data characteristics with optimal visualizations.
    """

    # Chart type recommendations based on data patterns
    CHART_RULES = {
        "time_series": {
            "chart_type": "LineChart",
            "conditions": ["has_datetime", "has_numerical"],
            "priority": 1
        },
        "comparison": {
            "chart_type": "BarChart",
            "conditions": ["has_categorical", "has_numerical"],
            "priority": 2
        },
        "composition": {
            "chart_type": "PieChart",
            "conditions": ["single_categorical", "has_numerical", "low_cardinality"],
            "priority": 3
        },
        "correlation": {
            "chart_type": "ScatterPlot",
            "conditions": ["multiple_numerical"],
            "priority": 4
        },
        "distribution": {
            "chart_type": "Histogram",
            "conditions": ["single_numerical"],
            "priority": 5
        },
        "hierarchy": {
            "chart_type": "TreeMap",
            "conditions": ["has_categorical", "has_numerical", "multiple_categories"],
            "priority": 6
        }
    }

    def __init__(self):
        """Initialize the ChartRecommender."""
        pass

    def recommend_chart(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recommends the most suitable chart type based on data profile.

        Args:
            profile: Data profiling results containing column metadata
                    Expected format: {
                        "columns": [
                            {"name": str, "type": str, "unique": int, ...},
                            ...
                        ],
                        "row_count": int
                    }

        Returns:
            Dictionary containing:
            - chart_type: Recommended chart type (e.g., "LineChart")
            - reason: Explanation for the recommendation
            - config: Suggested configuration for the chart
        """
        columns = profile.get("columns", [])

        # Analyze data characteristics
        characteristics = self._analyze_characteristics(columns)

        # Match characteristics to chart rules
        recommendations = self._match_chart_rules(characteristics)

        if not recommendations:
            # Default fallback
            return {
                "chart_type": "Table",
                "reason": "No specific pattern detected, showing data as table",
                "config": {"columns": [col["name"] for col in columns]}
            }

        # Return highest priority recommendation
        best_match = recommendations[0]
        config = self._generate_chart_config(best_match["chart_type"], columns, characteristics)

        return {
            "chart_type": best_match["chart_type"],
            "reason": best_match["reason"],
            "config": config
        }

    def recommend_multiple_charts(
        self,
        profile: Dict[str, Any],
        max_charts: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Recommends multiple complementary charts for a comprehensive view.

        Args:
            profile: Data profiling results
            max_charts: Maximum number of charts to recommend

        Returns:
            List of chart recommendations, sorted by priority
        """
        columns = profile.get("columns", [])
        characteristics = self._analyze_characteristics(columns)

        # Get all matching recommendations
        recommendations = self._match_chart_rules(characteristics)

        results = []
        for rec in recommendations[:max_charts]:
            config = self._generate_chart_config(rec["chart_type"], columns, characteristics)
            results.append({
                "chart_type": rec["chart_type"],
                "reason": rec["reason"],
                "config": config,
                "priority": rec["priority"]
            })

        return results

    def _analyze_characteristics(self, columns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyzes data columns to extract characteristics.

        Args:
            columns: List of column metadata

        Returns:
            Dictionary of data characteristics
        """
        datetime_cols = [col for col in columns if col.get("type") == "datetime"]
        numerical_cols = [col for col in columns if col.get("type") == "numerical"]
        categorical_cols = [col for col in columns if col.get("type") == "categorical"]

        characteristics = {
            "has_datetime": len(datetime_cols) > 0,
            "has_numerical": len(numerical_cols) > 0,
            "has_categorical": len(categorical_cols) > 0,
            "single_numerical": len(numerical_cols) == 1,
            "multiple_numerical": len(numerical_cols) >= 2,
            "single_categorical": len(categorical_cols) == 1,
            "multiple_categories": len(categorical_cols) >= 2,
            "low_cardinality": any(
                col.get("unique", 999) <= 10
                for col in categorical_cols
            ),
            "datetime_columns": datetime_cols,
            "numerical_columns": numerical_cols,
            "categorical_columns": categorical_cols
        }

        return characteristics

    def _match_chart_rules(self, characteristics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Matches data characteristics against chart rules.

        Args:
            characteristics: Data characteristics dictionary

        Returns:
            List of matching chart recommendations, sorted by priority
        """
        matches = []

        for pattern_name, rule in self.CHART_RULES.items():
            conditions = rule["conditions"]

            # Check if all conditions are met
            if all(characteristics.get(cond, False) for cond in conditions):
                matches.append({
                    "chart_type": rule["chart_type"],
                    "priority": rule["priority"],
                    "pattern": pattern_name,
                    "reason": self._generate_reason(pattern_name, characteristics)
                })

        # Sort by priority (lower number = higher priority)
        matches.sort(key=lambda x: x["priority"])

        return matches

    def _generate_reason(self, pattern_name: str, characteristics: Dict[str, Any]) -> str:
        """
        Generates a human-readable reason for the chart recommendation.

        Args:
            pattern_name: Name of the matched pattern
            characteristics: Data characteristics

        Returns:
            Explanation string
        """
        reasons = {
            "time_series": "Detected temporal data with measurements over time",
            "distribution": "Single numerical variable suggests distribution analysis",
            "comparison": "Categorical and numerical data suitable for comparison",
            "composition": "Low-cardinality categorical data with parts-of-whole relationship",
            "correlation": "Multiple numerical variables suggest correlation analysis",
            "hierarchy": "Multiple categorical dimensions suggest hierarchical view"
        }

        return reasons.get(pattern_name, "Data pattern matched for visualization")

    def _generate_chart_config(
        self,
        chart_type: str,
        columns: List[Dict[str, Any]],
        characteristics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generates configuration object for the recommended chart.

        Args:
            chart_type: Type of chart to configure
            columns: List of column metadata
            characteristics: Data characteristics

        Returns:
            Chart configuration dictionary
        """
        config = {}

        if chart_type == "LineChart":
            datetime_col = characteristics["datetime_columns"][0] if characteristics["datetime_columns"] else None
            numerical_col = characteristics["numerical_columns"][0] if characteristics["numerical_columns"] else None

            config = {
                "x_axis": datetime_col["name"] if datetime_col else None,
                "y_axis": numerical_col["name"] if numerical_col else None,
                "agg": "sum"
            }

        elif chart_type == "BarChart":
            categorical_col = characteristics["categorical_columns"][0] if characteristics["categorical_columns"] else None
            numerical_col = characteristics["numerical_columns"][0] if characteristics["numerical_columns"] else None

            config = {
                "dimension": categorical_col["name"] if categorical_col else None,
                "measure": numerical_col["name"] if numerical_col else None,
                "agg": "sum"
            }

        elif chart_type == "PieChart":
            categorical_col = characteristics["categorical_columns"][0] if characteristics["categorical_columns"] else None
            numerical_col = characteristics["numerical_columns"][0] if characteristics["numerical_columns"] else None

            config = {
                "category": categorical_col["name"] if categorical_col else None,
                "value": numerical_col["name"] if numerical_col else None,
                "agg": "sum"
            }

        elif chart_type == "Histogram":
            numerical_col = characteristics["numerical_columns"][0] if characteristics["numerical_columns"] else None

            config = {
                "column": numerical_col["name"] if numerical_col else None,
                "bins": 10
            }

        elif chart_type == "ScatterPlot":
            num_cols = characteristics["numerical_columns"]

            config = {
                "x_axis": num_cols[0]["name"] if len(num_cols) > 0 else None,
                "y_axis": num_cols[1]["name"] if len(num_cols) > 1 else None
            }

        elif chart_type == "TreeMap":
            cat_cols = characteristics["categorical_columns"]
            numerical_col = characteristics["numerical_columns"][0] if characteristics["numerical_columns"] else None

            config = {
                "hierarchy": [col["name"] for col in cat_cols[:2]],
                "value": numerical_col["name"] if numerical_col else None,
                "agg": "sum"
            }

        return config
