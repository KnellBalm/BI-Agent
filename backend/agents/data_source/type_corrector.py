"""
Data Type Auto-Correction Module
Detects and suggests type corrections for DataFrame columns.
"""
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime


@dataclass
class TypeCorrectionSuggestion:
    """A single type correction suggestion"""
    column: str
    current_type: str
    suggested_type: str
    confidence: float  # 0.0 to 1.0
    sample_values: List[str] = field(default_factory=list)
    reason: str = ""
    status: str = "pending"  # pending, approved, rejected


class TypeCorrector:
    """
    Detects and corrects data types in a DataFrame.

    Capabilities:
    - detect_date_strings(): Find text columns that should be datetime
    - detect_numeric_strings(): Find text with numeric values like "1,234.56"
    - suggest_type_corrections(): Return list of correction suggestions
    - apply_corrections(): Apply approved corrections to DataFrame
    """

    # Common date patterns
    DATE_PATTERNS = [
        # ISO format
        r'^\d{4}-\d{2}-\d{2}$',
        r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}',
        # US format
        r'^\d{1,2}/\d{1,2}/\d{2,4}$',
        # European format
        r'^\d{1,2}\.\d{1,2}\.\d{2,4}$',
        r'^\d{1,2}-\d{1,2}-\d{2,4}$',
        # Written format
        r'^[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}$',
        r'^\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}$',
        # Korean format
        r'^\d{4}[./-]\d{1,2}[./-]\d{1,2}$',
        r'^\d{4}년\s*\d{1,2}월\s*\d{1,2}일$',
    ]

    # Numeric string patterns
    NUMERIC_PATTERNS = [
        # With thousand separators
        r'^-?[\d,]+\.?\d*$',
        r'^-?[\d.]+,?\d*$',  # European style
        # Currency
        r'^[$€£¥₩]?\s*-?[\d,]+\.?\d*$',
        r'^-?[\d,]+\.?\d*\s*[$€£¥₩]?$',
        # Percentage
        r'^-?[\d,]+\.?\d*\s*%$',
        # Scientific notation
        r'^-?\d+\.?\d*[eE][+-]?\d+$',
    ]

    # Minimum sample ratio for detection
    MIN_DETECTION_RATIO = 0.7  # 70% of non-null values must match

    def __init__(self, df: Optional[pd.DataFrame] = None):
        self.df = df
        self._suggestions: List[TypeCorrectionSuggestion] = []

    def set_dataframe(self, df: pd.DataFrame) -> None:
        """Set the DataFrame to analyze"""
        self.df = df
        self._suggestions = []

    def detect_date_strings(self) -> List[TypeCorrectionSuggestion]:
        """
        Find text columns that should be datetime.

        Returns:
            List of TypeCorrectionSuggestion for columns that appear to contain dates
        """
        if self.df is None:
            return []

        suggestions = []

        for col in self.df.columns:
            series = self.df[col]

            # Skip if already datetime or numeric
            if pd.api.types.is_datetime64_any_dtype(series):
                continue
            if pd.api.types.is_numeric_dtype(series):
                continue

            # Get non-null string values
            str_series = series.dropna().astype(str)
            if str_series.empty:
                continue

            # Count matches for date patterns
            total_values = len(str_series)
            matching_values = []

            for value in str_series:
                for pattern in self.DATE_PATTERNS:
                    if re.match(pattern, value.strip()):
                        matching_values.append(value)
                        break

            match_ratio = len(matching_values) / total_values

            if match_ratio >= self.MIN_DETECTION_RATIO:
                # Try to parse a sample to validate
                parse_success = self._validate_date_parsing(matching_values[:10])

                if parse_success:
                    confidence = min(1.0, match_ratio + 0.1 * parse_success)
                    suggestion = TypeCorrectionSuggestion(
                        column=col,
                        current_type="text",
                        suggested_type="datetime",
                        confidence=round(confidence, 2),
                        sample_values=matching_values[:5],
                        reason=f"{match_ratio*100:.1f}% of values match date patterns"
                    )
                    suggestions.append(suggestion)

        return suggestions

    def _validate_date_parsing(self, samples: List[str]) -> float:
        """
        Validate that sample values can be parsed as dates.

        Returns:
            Ratio of successfully parsed values (0.0 to 1.0)
        """
        if not samples:
            return 0.0

        success_count = 0
        for value in samples:
            try:
                pd.to_datetime(value, format='mixed')
                success_count += 1
            except (ValueError, TypeError):
                pass

        return success_count / len(samples)

    def detect_numeric_strings(self) -> List[TypeCorrectionSuggestion]:
        """
        Find text columns with numeric values like "1,234.56".

        Returns:
            List of TypeCorrectionSuggestion for columns that appear to contain numbers
        """
        if self.df is None:
            return []

        suggestions = []

        for col in self.df.columns:
            series = self.df[col]

            # Skip if already numeric or datetime
            if pd.api.types.is_numeric_dtype(series):
                continue
            if pd.api.types.is_datetime64_any_dtype(series):
                continue

            # Get non-null string values
            str_series = series.dropna().astype(str)
            if str_series.empty:
                continue

            # Count matches for numeric patterns
            total_values = len(str_series)
            matching_values = []
            is_integer = True

            for value in str_series:
                cleaned = value.strip()
                for pattern in self.NUMERIC_PATTERNS:
                    if re.match(pattern, cleaned):
                        matching_values.append(cleaned)
                        # Check if it contains decimal point
                        if '.' in cleaned and not cleaned.endswith('.'):
                            is_integer = False
                        break

            match_ratio = len(matching_values) / total_values

            if match_ratio >= self.MIN_DETECTION_RATIO:
                # Try to parse a sample to validate
                parse_success = self._validate_numeric_parsing(matching_values[:10])

                if parse_success:
                    suggested_type = "int64" if is_integer else "float64"
                    confidence = min(1.0, match_ratio + 0.1 * parse_success)
                    suggestion = TypeCorrectionSuggestion(
                        column=col,
                        current_type="text",
                        suggested_type=suggested_type,
                        confidence=round(confidence, 2),
                        sample_values=matching_values[:5],
                        reason=f"{match_ratio*100:.1f}% of values match numeric patterns"
                    )
                    suggestions.append(suggestion)

        return suggestions

    def _validate_numeric_parsing(self, samples: List[str]) -> float:
        """
        Validate that sample values can be parsed as numbers.

        Returns:
            Ratio of successfully parsed values (0.0 to 1.0)
        """
        if not samples:
            return 0.0

        success_count = 0
        for value in samples:
            try:
                # Remove common formatting
                cleaned = value.replace(',', '').replace(' ', '')
                cleaned = re.sub(r'[$€£¥₩%]', '', cleaned)
                float(cleaned)
                success_count += 1
            except (ValueError, TypeError):
                pass

        return success_count / len(samples)

    def suggest_type_corrections(self) -> List[TypeCorrectionSuggestion]:
        """
        Analyze DataFrame and return all type correction suggestions.

        Returns:
            List of TypeCorrectionSuggestion objects sorted by confidence (highest first)
        """
        if self.df is None:
            return []

        suggestions = []

        # Detect date strings
        date_suggestions = self.detect_date_strings()
        suggestions.extend(date_suggestions)

        # Detect numeric strings
        numeric_suggestions = self.detect_numeric_strings()
        suggestions.extend(numeric_suggestions)

        # Sort by confidence (highest first)
        suggestions.sort(key=lambda x: x.confidence, reverse=True)

        self._suggestions = suggestions
        return suggestions

    def approve_correction(self, column: str) -> None:
        """Mark a correction as approved"""
        for suggestion in self._suggestions:
            if suggestion.column == column:
                suggestion.status = "approved"
                break

    def reject_correction(self, column: str) -> None:
        """Mark a correction as rejected"""
        for suggestion in self._suggestions:
            if suggestion.column == column:
                suggestion.status = "rejected"
                break

    def apply_corrections(
        self,
        df: Optional[pd.DataFrame] = None,
        approved_only: bool = True
    ) -> pd.DataFrame:
        """
        Apply approved corrections to DataFrame.

        Args:
            df: DataFrame to correct (uses self.df if not provided)
            approved_only: If True, only apply approved corrections

        Returns:
            Corrected DataFrame (original is not modified)
        """
        target_df = df if df is not None else self.df
        if target_df is None:
            raise ValueError("No DataFrame provided")

        # Make a copy to avoid modifying original
        result_df = target_df.copy()

        for suggestion in self._suggestions:
            # Skip if not approved (when approved_only is True)
            if approved_only and suggestion.status != "approved":
                continue

            col = suggestion.column
            if col not in result_df.columns:
                continue

            try:
                if suggestion.suggested_type == "datetime":
                    result_df[col] = pd.to_datetime(
                        result_df[col],
                        format='mixed',
                        errors='coerce'
                    )
                elif suggestion.suggested_type in ["int64", "float64"]:
                    # Clean the values first
                    cleaned = result_df[col].astype(str).apply(self._clean_numeric_string)
                    result_df[col] = pd.to_numeric(cleaned, errors='coerce')

                    # Convert to int if suggested
                    if suggestion.suggested_type == "int64":
                        # Only convert to int if no NaN values
                        if not result_df[col].isna().any():
                            result_df[col] = result_df[col].astype('int64')

            except Exception:
                # If conversion fails, leave column unchanged
                pass

        return result_df

    def _clean_numeric_string(self, value: str) -> str:
        """Clean a numeric string for parsing"""
        if pd.isna(value) or value.strip().lower() in ['nan', 'null', 'none', '']:
            return ''

        cleaned = value.strip()
        # Remove currency symbols
        cleaned = re.sub(r'[$€£¥₩]', '', cleaned)
        # Remove percentage sign
        cleaned = cleaned.rstrip('%')
        # Remove thousand separators (comma in US, period in EU)
        # Assume comma is thousand separator if both comma and period exist
        if ',' in cleaned and '.' in cleaned:
            cleaned = cleaned.replace(',', '')
        elif ',' in cleaned and '.' not in cleaned:
            # Could be thousand separator or decimal - check position
            if len(cleaned.split(',')[-1]) == 3:
                cleaned = cleaned.replace(',', '')
            else:
                cleaned = cleaned.replace(',', '.')

        return cleaned.strip()

    def get_correction_summary(self) -> Dict[str, Any]:
        """Get a summary of all corrections"""
        return {
            "total_suggestions": len(self._suggestions),
            "approved": len([s for s in self._suggestions if s.status == "approved"]),
            "rejected": len([s for s in self._suggestions if s.status == "rejected"]),
            "pending": len([s for s in self._suggestions if s.status == "pending"]),
            "suggestions": [
                {
                    "column": s.column,
                    "current_type": s.current_type,
                    "suggested_type": s.suggested_type,
                    "confidence": s.confidence,
                    "sample_values": s.sample_values,
                    "reason": s.reason,
                    "status": s.status
                }
                for s in self._suggestions
            ]
        }
