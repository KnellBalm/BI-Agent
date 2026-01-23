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

        summary = {
            "overview": self._get_overview(),
            "columns": self._get_column_details(),
            "sample": self.df.head(5).to_dict(orient='records')
        }
        return summary

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
        """Analyzes each column in detail"""
        column_info = []
        
        for col in self.df.columns:
            series = self.df[col]
            dtype = str(series.dtype)
            
            # Basic info
            details = {
                "name": col,
                "type": self._infer_type(series),
                "native_dtype": dtype,
                "missing": int(series.isnull().sum()),
                "unique": int(series.nunique())
            }
            
            # Statistical info based on type
            if details["type"] == "numerical":
                details.update({
                    "mean": float(series.mean()) if not series.empty else 0,
                    "std": float(series.std()) if not series.empty else 0,
                    "min": float(series.min()) if not series.empty else 0,
                    "max": float(series.max()) if not series.empty else 0,
                    "median": float(series.median()) if not series.empty else 0
                })
            elif details["type"] == "categorical":
                details.update({
                    "top_values": series.value_counts().head(5).to_dict()
                })
            elif details["type"] == "datetime":
                details.update({
                    "min": str(series.min()),
                    "max": str(series.max())
                })
            
            column_info.append(details)
            
        return column_info

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
