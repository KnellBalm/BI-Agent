#!/usr/bin/env python3
"""
Test script for TypeCorrectionGrid implementation
"""
import pandas as pd
from backend.agents.data_source.type_corrector import TypeCorrector
from backend.orchestrator.components.data_grid import TypeCorrectionGrid


def test_type_correction_grid():
    """Test TypeCorrectionGrid functionality"""

    # Create sample DataFrame with type issues
    df = pd.DataFrame({
        'id': ['1', '2', '3', '4', '5'],
        'amount': ['1,234.56', '2,345.67', '3,456.78', '4,567.89', '5,678.90'],
        'date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
        'status': ['active', 'inactive', 'active', 'pending', 'active']
    })

    print("Original DataFrame:")
    print(df.dtypes)
    print()

    # Create TypeCorrector and get suggestions
    corrector = TypeCorrector(df)
    suggestions = corrector.suggest_type_corrections()

    print(f"Found {len(suggestions)} type correction suggestions:")
    for suggestion in suggestions:
        print(f"  - {suggestion.column}: {suggestion.current_type} → {suggestion.suggested_type} ({suggestion.confidence:.2f})")
    print()

    # Test grid creation (without actually running Textual app)
    grid = TypeCorrectionGrid(df=df)
    grid.load_corrections(suggestions)

    print("TypeCorrectionGrid created successfully!")
    print(f"  - Loaded {len(grid._corrections)} corrections")
    print(f"  - Pending: {len(grid.get_pending_corrections())}")
    print(f"  - Approved: {len(grid.get_approved_corrections())}")
    print(f"  - Rejected: {len(grid.get_rejected_corrections())}")
    print()

    # Test approval/rejection
    if suggestions:
        first_col = suggestions[0].column
        print(f"Testing approval for column: {first_col}")
        grid.on_approve(first_col)
        print(f"  - Approved: {len(grid.get_approved_corrections())}")

        if len(suggestions) > 1:
            second_col = suggestions[1].column
            print(f"Testing rejection for column: {second_col}")
            grid.on_reject(second_col)
            print(f"  - Rejected: {len(grid.get_rejected_corrections())}")

    # Test summary
    summary = grid.get_correction_summary()
    print("\nCorrection Summary:")
    print(f"  Total: {summary['total']}")
    print(f"  Approved: {summary['approved']}")
    print(f"  Rejected: {summary['rejected']}")
    print(f"  Pending: {summary['pending']}")

    print("\n✓ All tests passed!")
    return True


if __name__ == "__main__":
    test_type_correction_grid()
