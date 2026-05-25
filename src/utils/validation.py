"""Data validation utilities for CSV import."""

import pandas as pd
from typing import Tuple, List


REQUIRED_COLUMNS = {
    "product_id": str,
    "product_name": str,
    "brand": str,
    "model": str,
    "category": str,
    "current_price": float,
    "cost_price": float,
    "inventory": int,
    "competitor_min_price": float,
    "competitor_median_price": float,
    "competitor_max_price": float,
    "usd_rate": float,
    "usd_change_7d": float,
    "sales_7d": int,
    "sales_30d": int,
    "views_30d": int,
    "conversion_rate": float,
    "target_margin": float,
    "supplier_lead_time_days": int,
}


def validate_csv_columns(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate that a DataFrame has all required columns.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        Tuple of (is_valid, list_of_missing_columns)
        
    Examples:
        is_valid, missing = validate_csv_columns(df)
        if not is_valid:
            print(f"Missing columns: {missing}")
    """
    missing_columns = []
    
    for col in REQUIRED_COLUMNS.keys():
        if col not in df.columns:
            missing_columns.append(col)
    
    return len(missing_columns) == 0, missing_columns


def validate_csv_data(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate that data in DataFrame meets requirements.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Check for empty dataframe
    if len(df) == 0:
        issues.append("CSV file is empty")
        return False, issues
    
    # Check for negative prices
    price_cols = ["current_price", "cost_price", "competitor_min_price", 
                  "competitor_median_price", "competitor_max_price"]
    for col in price_cols:
        if col in df.columns:
            if (df[col] < 0).any():
                issues.append(f"Column '{col}' contains negative values")
    
    # Check for negative inventory
    if "inventory" in df.columns:
        if (df["inventory"] < 0).any():
            issues.append("Column 'inventory' contains negative values")
    
    # Check conversion rate is between 0 and 1
    if "conversion_rate" in df.columns:
        if ((df["conversion_rate"] < 0) | (df["conversion_rate"] > 1)).any():
            issues.append("Column 'conversion_rate' should be between 0 and 1")
    
    # Check target_margin is between 0 and 1
    if "target_margin" in df.columns:
        if ((df["target_margin"] < 0) | (df["target_margin"] > 1)).any():
            issues.append("Column 'target_margin' should be between 0 and 1")
    
    return len(issues) == 0, issues


def load_and_validate_csv(file_path: str) -> Tuple[bool, pd.DataFrame, List[str]]:
    """
    Load and validate a CSV file.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Tuple of (is_valid, dataframe, error_messages)
    """
    errors = []
    df = None
    
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        errors.append(f"Failed to read CSV: {str(e)}")
        return False, None, errors
    
    # Check columns
    col_valid, missing_cols = validate_csv_columns(df)
    if not col_valid:
        errors.append(f"Missing required columns: {', '.join(missing_cols)}")
        return False, df, errors
    
    # Check data
    data_valid, data_issues = validate_csv_data(df)
    if not data_valid:
        errors.extend(data_issues)
        return False, df, errors
    
    return True, df, errors


def get_column_info() -> str:
    """
    Get human-readable information about required columns.
    
    Returns:
        Formatted string describing all required columns
    """
    lines = []
    lines.append("Required CSV Columns:")
    lines.append("")
    
    for col, dtype in REQUIRED_COLUMNS.items():
        type_name = dtype.__name__
        lines.append(f"- {col} ({type_name})")
    
    return "\n".join(lines)
