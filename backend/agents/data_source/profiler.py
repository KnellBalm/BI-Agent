"""
Data Profiler Module
Analyzes data sources and provides statistical summaries and insights.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import os

class DataProfiler:
    """
    Analyzes a DataFrame or a data file to extract profiling information.
    """
    
    def __init__(self, data: Optional[pd.DataFrame] = None):
        self.df = data

    def load_file(self, file_path: str):
        """Loads data from a file path (CSV or Excel)"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.csv':
            self.df = pd.read_csv(file_path)
        elif ext in ['.xlsx', '.xls']:
            self.df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
        return self

    def profile(self) -> Dict[str, Any]:
        """Performs full profiling of the loaded DataFrame"""
        if self.df is None:
            raise ValueError("No data loaded to profile.")

        column_details = self._get_column_details()
        overall_quality = self._calculate_overall_quality_score(column_details)

        summary = {
            "overview": self._get_overview(),
            "columns": column_details,
            "overall_quality_score": overall_quality,
            "sample": self.df.head(5).to_dict(orient='records')
        }
        return summary

    def _calculate_overall_quality_score(self, column_details: List[Dict[str, Any]]) -> int:
        """Calculates overall dataset quality score"""
        if not column_details:
            return 0
        scores = [col.get("quality_score", 0) for col in column_details]
        return round(sum(scores) / len(scores))

    def _get_overview(self) -> Dict[str, Any]:
        """Gets high-level summary of the dataset"""
        return {
            "rows": len(self.df),
            "columns": len(self.df.columns),
            "missing_cells": int(self.df.isnull().sum().sum()),
            "missing_percentage": float((self.df.isnull().sum().sum() / (self.df.size)) * 100),
            "duplicate_rows": int(self.df.duplicated().sum()),
            "memory_usage": f"{self.df.memory_usage(deep=True).sum() / 1024:.2f} KB"
        }

    def _get_column_details(self) -> List[Dict[str, Any]]:
        """Analyzes each column in detail with enhanced statistics"""
        column_info = []

        for col in self.df.columns:
            series = self.df[col]
            dtype = str(series.dtype)
            col_type = self._infer_type(series)
            total_count = len(series)
            missing_count = int(series.isnull().sum())

            # Basic info with enhancements
            details = {
                "name": col,
                "type": col_type,
                "native_dtype": dtype,
                "missing": missing_count,
                "missing_pct": round((missing_count / total_count) * 100, 2) if total_count > 0 else 0.0,
                "unique": int(series.nunique()),
                "mode": self._get_mode(series),
                "quality_score": self._calculate_column_quality_score(series, col_type)
            }

            # Statistical info based on type
            if col_type == "numerical":
                clean_series = series.dropna()
                if not clean_series.empty:
                    details.update({
                        "mean": round(float(clean_series.mean()), 4),
                        "std": round(float(clean_series.std()), 4),
                        "min": float(clean_series.min()),
                        "max": float(clean_series.max()),
                        "median": float(clean_series.median()),
                        "q25": float(clean_series.quantile(0.25)),
                        "q50": float(clean_series.quantile(0.50)),
                        "q75": float(clean_series.quantile(0.75)),
                        "distribution": self._get_distribution(clean_series)
                    })
                else:
                    details.update({
                        "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0,
                        "median": 0.0, "q25": 0.0, "q50": 0.0, "q75": 0.0,
                        "distribution": {"bins": [], "counts": []}
                    })
            elif col_type == "categorical":
                details.update({
                    "top_values": series.value_counts().head(5).to_dict(),
                    "distribution": self._get_categorical_distribution(series)
                })
            elif col_type == "datetime":
                clean_series = series.dropna()
                if not clean_series.empty:
                    details.update({
                        "min": str(clean_series.min()),
                        "max": str(clean_series.max())
                    })

            column_info.append(details)

        return column_info

    def _get_mode(self, series: pd.Series) -> Any:
        """Gets the most frequent value in a series"""
        clean_series = series.dropna()
        if clean_series.empty:
            return None
        mode_result = clean_series.mode()
        if len(mode_result) == 0:
            return None
        mode_val = mode_result.iloc[0]
        if isinstance(mode_val, (np.integer, np.floating)):
            return float(mode_val) if isinstance(mode_val, np.floating) else int(mode_val)
        elif pd.api.types.is_datetime64_any_dtype(type(mode_val)):
            return str(mode_val)
        return mode_val

    def _get_distribution(self, series: pd.Series, bins: int = 10) -> Dict[str, Any]:
        """Gets histogram distribution for numerical data"""
        try:
            counts, edges = np.histogram(series, bins=bins)
            bin_labels = [f"{round(edges[i], 2)}-{round(edges[i+1], 2)}" for i in range(len(edges) - 1)]
            return {
                "bins": bin_labels,
                "counts": [int(c) for c in counts]
            }
        except (ValueError, TypeError):
            return {"bins": [], "counts": []}

    def _get_categorical_distribution(self, series: pd.Series, top_n: int = 10) -> Dict[str, Any]:
        """Gets value distribution for categorical data"""
        value_counts = series.value_counts()
        top_values = value_counts.head(top_n)
        bins = [str(v) for v in top_values.index.tolist()]
        counts = top_values.tolist()
        return {"bins": bins, "counts": counts}

    def _calculate_column_quality_score(self, series: pd.Series, col_type: str) -> int:
        """Calculates a quality score (0-100) for a column based on completeness and consistency"""
        total = len(series)
        if total == 0:
            return 0

        # Completeness score (no missing values = high score)
        missing_pct = series.isnull().sum() / total
        completeness_score = (1 - missing_pct) * 100

        # Uniqueness score (depends on column type)
        unique_ratio = series.nunique() / total if total > 0 else 0
        if col_type == "categorical":
            # For categorical, moderate uniqueness is good
            if unique_ratio < 0.05:
                uniqueness_score = unique_ratio * 1000
            elif unique_ratio > 0.5:
                uniqueness_score = max(0, 100 - (unique_ratio - 0.5) * 100)
            else:
                uniqueness_score = 100
        else:
            uniqueness_score = min(100, unique_ratio * 100 + 50)

        # Weighted final score
        final_score = completeness_score * 0.7 + uniqueness_score * 0.3
        return round(max(0, min(100, final_score)))

    def _infer_type(self, series: pd.Series) -> str:
        """Infers a logical BI type for a column"""
        # Drop Nulls for accurate type checking
        clean_series = series.dropna()
        if clean_series.empty:
            return "empty"
            
        if pd.api.types.is_numeric_dtype(clean_series):
            return "numerical"
        elif pd.api.types.is_datetime64_any_dtype(clean_series):
            return "datetime"
        
        # Heuristic for categorical
        unique_count = clean_series.nunique()
        total_count = len(clean_series)
        
        # Categorical if:
        # 1. Very small number of unique values (e.g. < 20)
        # 2. Or unique values are less than 30% of total (for larger datasets)
        if unique_count <= 20 or (unique_count / total_count) < 0.3:
            return "categorical"
        
        return "text"

if __name__ == "__main__":
    # Quick test
    df = pd.DataFrame({
        "A": [1, 2, 3, 4, 5, 2],
        "B": ["X", "Y", "X", "Z", "X", "Y"],
        "C": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05", "2023-01-06"])
    })
    profiler = DataProfiler(df)
    import pprint
    pprint.pprint(profiler.profile())
