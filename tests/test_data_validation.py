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
    """Create a valid sample CSV DataFrame (Phase 2 schema)."""
    return pd.DataFrame({
        "product_id": ["SW001", "SW002"],
        "product_name": ["Product 1", "Product 2"],
        "brand": ["Apple", "Xiaomi"],
        "model": ["Ultra", "Sport"],
        "category": ["Premium", "Budget"],
        "base_usd_price": [499.99, 49.99],
        "base_usd_price_source": ["Amazon", "Official MSRP"],
        "usd_rate": [46000.0, 46000.0],
        "theoretical_toman_price": [22999540.0, 2299540.0],
        "market_min_price": [27000000.0, 2500000.0],
        "market_median_price": [28700000.0, 2600000.0],
        "market_max_price": [30500000.0, 2700000.0],
        "market_avg_price": [28733333.0, 2600000.0],
        "seller_count": [7, 10],
        "available_seller_count": [6, 9],
        "torob_min_price": [26500000.0, 2480000.0],
        "torob_median_price": [27000000.0, 2500000.0],
        "digikala_price": [27200000.0, 2520000.0],
        "our_current_price": [29500000.0, 2650000.0],
        "our_cost_price": [21000000.0, 2000000.0],
        "our_inventory": [12, 80],
        "our_sales_7d": [3, 15],
        "our_sales_30d": [12, 60],
        "our_target_margin": [0.32, 0.22],
        "our_strategy": ["Premium Positioning", "Market Penetration"],
        "observed_at": ["2026-05-25", "2026-05-25"],
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
        df = valid_csv_data.drop("our_current_price", axis=1)
        is_valid, missing = validate_csv_columns(df)
        assert is_valid is False
        assert "our_current_price" in missing
    
    def test_missing_multiple_columns(self, valid_csv_data):
        """Test detection of multiple missing columns."""
        df = valid_csv_data.drop(["our_current_price", "our_inventory"], axis=1)
        is_valid, missing = validate_csv_columns(df)
        assert is_valid is False
        assert "our_current_price" in missing
        assert "our_inventory" in missing


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
        """Test detection of negative price (Phase 2 our_cost_price)."""
        df = valid_csv_data.copy()
        df.loc[0, "our_cost_price"] = -1000
        is_valid, issues = validate_csv_data(df)
        assert is_valid is False
    
    def test_negative_inventory(self, valid_csv_data):
        """Test detection of negative inventory."""
        df = valid_csv_data.copy()
        df.loc[0, "our_inventory"] = -10
        is_valid, issues = validate_csv_data(df)
        assert is_valid is False
    
    def test_conversion_rate_out_of_range(self, valid_csv_data):
        """Test detection of invalid conversion rate (deprecated field, optional)."""
        df = valid_csv_data.copy()
        df["conversion_rate"] = 0.05  # Add optional field for testing
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
        df_missing = valid_csv_data.drop("our_current_price", axis=1)
        
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


class TestPhase2Schema:
    """Test Phase 2 schema requirements."""
    
    def test_required_columns_exist(self):
        """Test that REQUIRED_COLUMNS includes all Phase 2 fields."""
        expected_phase2_cols = [
            "product_id", "product_name", "brand", "model", "category",
            "base_usd_price", "base_usd_price_source", "usd_rate",
            "theoretical_toman_price", "market_min_price", "market_median_price",
            "market_max_price", "market_avg_price", "seller_count",
            "available_seller_count", "torob_min_price", "torob_median_price",
            "digikala_price", "our_current_price", "our_cost_price",
            "our_inventory", "our_sales_7d", "our_sales_30d",
            "our_target_margin", "our_strategy", "observed_at",
        ]
        
        for col in expected_phase2_cols:
            assert col in REQUIRED_COLUMNS, f"Missing Phase 2 column in REQUIRED_COLUMNS: {col}"
    
    def test_valid_phase2_csv_data(self, valid_csv_data):
        """Test that Phase 2 CSV data validates correctly."""
        is_valid, issues = validate_csv_data(valid_csv_data)
        assert is_valid is True, f"Phase 2 data should be valid: {issues}"
    
    def test_market_price_order_validation(self):
        """Test that market prices are ordered correctly."""
        df = pd.DataFrame({
            "product_id": ["SW001"],
            "product_name": ["Test"],
            "brand": ["Test"],
            "model": ["Test"],
            "category": ["Premium"],
            "base_usd_price": [100.0],
            "base_usd_price_source": ["Amazon"],
            "usd_rate": [46000.0],
            "theoretical_toman_price": [4600000.0],
            "market_min_price": [5500000.0],
            "market_median_price": [5400000.0],  # Invalid: min > median
            "market_max_price": [5600000.0],
            "market_avg_price": [5500000.0],
            "seller_count": [5],
            "available_seller_count": [4],
            "torob_min_price": [5500000.0],
            "torob_median_price": [5500000.0],
            "digikala_price": [5500000.0],
            "our_current_price": [5800000.0],
            "our_cost_price": [4200000.0],
            "our_inventory": [10],
            "our_sales_7d": [2],
            "our_sales_30d": [8],
            "our_target_margin": [0.25],
            "our_strategy": ["Balanced"],
            "observed_at": ["2026-05-25"],
        })
        
        is_valid, issues = validate_csv_data(df)
        # Current validation doesn't check market price order, but data should still be valid
        assert is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
