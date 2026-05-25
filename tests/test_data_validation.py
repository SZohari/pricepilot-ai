"""Tests for data validation utilities."""

import pytest
import pandas as pd
import sys
from pathlib import Path
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.validation import (
    validate_csv_columns,
    validate_csv_data,
    load_and_validate_csv,
    get_column_info,
    REQUIRED_COLUMNS,
)


@pytest.fixture
def valid_csv_data():
    """Create a valid sample CSV DataFrame."""
    return pd.DataFrame({
        "product_id": ["SW001", "SW002"],
        "product_name": ["Product 1", "Product 2"],
        "brand": ["Brand A", "Brand B"],
        "model": ["Model X", "Model Y"],
        "category": ["Premium", "Budget"],
        "current_price": [2000000.0, 1500000.0],
        "cost_price": [1000000.0, 750000.0],
        "inventory": [50, 30],
        "competitor_min_price": [1900000.0, 1400000.0],
        "competitor_median_price": [2100000.0, 1600000.0],
        "competitor_max_price": [2300000.0, 1800000.0],
        "usd_rate": [45000.0, 45000.0],
        "usd_change_7d": [2.5, 1.5],
        "sales_7d": [10, 5],
        "sales_30d": [40, 20],
        "views_30d": [500, 300],
        "conversion_rate": [0.08, 0.06],
        "target_margin": [0.35, 0.30],
        "supplier_lead_time_days": [15, 10],
    })


class TestValidateCSVColumns:
    """Test CSV column validation."""
    
    def test_valid_columns(self, valid_csv_data):
        """Test that valid data passes column check."""
        is_valid, missing = validate_csv_columns(valid_csv_data)
        assert is_valid is True
        assert len(missing) == 0
    
    def test_missing_single_column(self, valid_csv_data):
        """Test detection of single missing column."""
        df = valid_csv_data.drop("current_price", axis=1)
        is_valid, missing = validate_csv_columns(df)
        assert is_valid is False
        assert "current_price" in missing
    
    def test_missing_multiple_columns(self, valid_csv_data):
        """Test detection of multiple missing columns."""
        df = valid_csv_data.drop(["current_price", "inventory"], axis=1)
        is_valid, missing = validate_csv_columns(df)
        assert is_valid is False
        assert "current_price" in missing
        assert "inventory" in missing


class TestValidateCSVData:
    """Test CSV data validation."""
    
    def test_valid_data(self, valid_csv_data):
        """Test that valid data passes checks."""
        is_valid, issues = validate_csv_data(valid_csv_data)
        assert is_valid is True
        assert len(issues) == 0
    
    def test_empty_dataframe(self):
        """Test that empty DataFrame is detected."""
        df = pd.DataFrame()
        is_valid, issues = validate_csv_data(df)
        assert is_valid is False
        assert any("empty" in issue.lower() for issue in issues)
    
    def test_negative_price(self, valid_csv_data):
        """Test detection of negative price."""
        df = valid_csv_data.copy()
        df.loc[0, "current_price"] = -1000
        is_valid, issues = validate_csv_data(df)
        assert is_valid is False
    
    def test_negative_inventory(self, valid_csv_data):
        """Test detection of negative inventory."""
        df = valid_csv_data.copy()
        df.loc[0, "inventory"] = -10
        is_valid, issues = validate_csv_data(df)
        assert is_valid is False
    
    def test_conversion_rate_out_of_range(self, valid_csv_data):
        """Test detection of invalid conversion rate."""
        df = valid_csv_data.copy()
        df.loc[0, "conversion_rate"] = 1.5  # Should be 0-1
        is_valid, issues = validate_csv_data(df)
        assert is_valid is False


class TestLoadAndValidateCSV:
    """Test complete CSV loading and validation."""
    
    def test_load_valid_csv(self, valid_csv_data):
        """Test loading valid CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            valid_csv_data.to_csv(f.name, index=False)
            temp_path = f.name
        
        try:
            is_valid, df, errors = load_and_validate_csv(temp_path)
            assert is_valid is True
            assert len(errors) == 0
            assert df is not None
            assert len(df) == 2
        finally:
            import os
            os.unlink(temp_path)
    
    def test_load_nonexistent_file(self):
        """Test handling of nonexistent file."""
        is_valid, df, errors = load_and_validate_csv("/nonexistent/path.csv")
        assert is_valid is False
        assert len(errors) > 0
    
    def test_load_missing_columns(self, valid_csv_data):
        """Test loading CSV with missing columns."""
        df_missing = valid_csv_data.drop("current_price", axis=1)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df_missing.to_csv(f.name, index=False)
            temp_path = f.name
        
        try:
            is_valid, df, errors = load_and_validate_csv(temp_path)
            assert is_valid is False
            assert any("Missing required columns" in e for e in errors)
        finally:
            import os
            os.unlink(temp_path)


class TestColumnInfo:
    """Test column information function."""
    
    def test_column_info_contains_all_columns(self):
        """Test that column info includes all required columns."""
        info = get_column_info()
        
        for col in REQUIRED_COLUMNS.keys():
            assert col in info
    
    def test_column_info_is_readable(self):
        """Test that column info is readable."""
        info = get_column_info()
        
        assert "Required CSV Columns" in info
        assert "-" in info  # Should have bullet points


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
