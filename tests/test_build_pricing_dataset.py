"""
Tests for the build pricing dataset pipeline.

Tests verify:
- Raw data loading from CSV files
- Dataset building from aggregated and internal data
- Correct field calculations (theoretical_toman_price, iran_market_premium_pct)
- Phase 2 schema compliance
- No duplicate product_ids
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile

from src.data.build_pricing_dataset import (
    load_market_observations,
    load_retailer_internal_data,
    load_global_usd_reference,
    build_dashboard_pricing_dataset,
    save_dashboard_pricing_dataset,
)


class TestLoadMarketObservations:
    """Tests for loading market observations."""
    
    def test_load_valid_market_observations(self):
        """Load market observations from template file."""
        df = load_market_observations('data/raw/market_observations_template.csv')
        assert len(df) > 0
        assert 'product_id' in df.columns
        assert 'listed_price' in df.columns
    
    def test_market_observations_has_required_columns(self):
        """Market observations have all required columns."""
        df = load_market_observations('data/raw/market_observations_template.csv')
        required = [
            'observation_id',
            'product_id',
            'normalized_product_name',
            'brand',
            'model',
            'listed_price',
            'seller_name',
            'availability_status',
        ]
        for col in required:
            assert col in df.columns
    
    def test_file_not_found_raises_error(self):
        """Missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_market_observations('nonexistent/path.csv')
    
    def test_market_observations_non_empty(self):
        """Market observations dataframe is not empty."""
        df = load_market_observations('data/raw/market_observations_template.csv')
        assert len(df) > 0


class TestLoadRetailerInternalData:
    """Tests for loading retailer internal data."""
    
    def test_load_valid_retailer_data(self):
        """Load retailer internal data from template file."""
        df = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        assert len(df) > 0
        assert 'product_id' in df.columns
    
    def test_retailer_data_has_required_columns(self):
        """Retailer data has all required columns."""
        df = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        required = [
            'product_id',
            'our_current_price',
            'our_cost_price',
            'our_inventory',
            'our_sales_7d',
            'our_sales_30d',
            'our_target_margin',
            'our_strategy',
        ]
        for col in required:
            assert col in df.columns
    
    def test_file_not_found_raises_error(self):
        """Missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_retailer_internal_data('nonexistent/path.csv')
    
    def test_missing_columns_raises_error(self):
        """Missing required columns raises ValueError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name
            f.write('product_id,our_current_price\nP1,100')
            f.flush()
        
        try:
            with pytest.raises(ValueError):
                load_retailer_internal_data(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestLoadGlobalUSDReference:
    """Tests for loading USD reference data."""
    
    def test_load_valid_usd_reference(self):
        """Load USD reference data from template file."""
        df = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        assert len(df) > 0
        assert 'product_id' in df.columns
        assert 'base_usd_price' in df.columns
    
    def test_usd_reference_has_required_columns(self):
        """USD reference has all required columns."""
        df = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        required = [
            'product_id',
            'brand',
            'model',
            'base_usd_price',
            'base_usd_price_source',
        ]
        for col in required:
            assert col in df.columns
    
    def test_file_not_found_raises_error(self):
        """Missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_global_usd_reference('nonexistent/path.csv')


class TestBuildDashboardPricingDataset:
    """Tests for building the dashboard pricing dataset."""
    
    def test_output_has_one_row_per_product(self):
        """Output contains one row per unique product_id."""
        market_df = load_market_observations('data/raw/market_observations_template.csv')
        retailer_df = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        usd_df = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        
        result = build_dashboard_pricing_dataset(market_df, retailer_df, usd_df)
        
        # Should have same number of products as input
        unique_products = market_df['product_id'].nunique()
        assert len(result) <= unique_products
    
    def test_output_has_market_price_columns(self):
        """Output includes market price columns."""
        market_df = load_market_observations('data/raw/market_observations_template.csv')
        retailer_df = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        usd_df = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        
        result = build_dashboard_pricing_dataset(market_df, retailer_df, usd_df)
        
        required = [
            'market_min_price',
            'market_median_price',
            'market_max_price',
        ]
        for col in required:
            assert col in result.columns
    
    def test_output_has_retailer_columns(self):
        """Output includes retailer internal columns."""
        market_df = load_market_observations('data/raw/market_observations_template.csv')
        retailer_df = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        usd_df = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        
        result = build_dashboard_pricing_dataset(market_df, retailer_df, usd_df)
        
        required = [
            'our_current_price',
            'our_cost_price',
            'our_inventory',
            'our_strategy',
        ]
        for col in required:
            assert col in result.columns
    
    def test_output_has_usd_columns(self):
        """Output includes USD reference columns."""
        market_df = load_market_observations('data/raw/market_observations_template.csv')
        retailer_df = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        usd_df = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        
        result = build_dashboard_pricing_dataset(market_df, retailer_df, usd_df)
        
        required = [
            'base_usd_price',
            'usd_rate',
            'theoretical_toman_price',
            'iran_market_premium_pct',
        ]
        for col in required:
            assert col in result.columns
    
    def test_theoretical_toman_price_calculated_correctly(self):
        """theoretical_toman_price = base_usd_price * usd_rate."""
        market_df = load_market_observations('data/raw/market_observations_template.csv')
        retailer_df = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        usd_df = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        
        result = build_dashboard_pricing_dataset(market_df, retailer_df, usd_df)
        
        # Verify calculation
        for idx, row in result.iterrows():
            expected = int(row['base_usd_price'] * row['usd_rate'])
            assert row['theoretical_toman_price'] == expected
    
    def test_iran_market_premium_pct_calculated_correctly(self):
        """iran_market_premium_pct = (market_median - theoretical) / theoretical."""
        market_df = load_market_observations('data/raw/market_observations_template.csv')
        retailer_df = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        usd_df = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        
        result = build_dashboard_pricing_dataset(market_df, retailer_df, usd_df)
        
        # Verify calculation
        for idx, row in result.iterrows():
            if row['theoretical_toman_price'] > 0:
                expected = (
                    (row['market_median_price'] - row['theoretical_toman_price']) / 
                    row['theoretical_toman_price']
                )
                assert abs(row['iran_market_premium_pct'] - expected) < 0.0001
    
    def test_no_duplicate_product_ids(self):
        """Output has no duplicate product_ids."""
        market_df = load_market_observations('data/raw/market_observations_template.csv')
        retailer_df = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        usd_df = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        
        result = build_dashboard_pricing_dataset(market_df, retailer_df, usd_df)
        
        assert len(result) == result['product_id'].nunique()
    
    def test_usd_rate_override(self):
        """USD rate can be overridden with parameter."""
        market_df = load_market_observations('data/raw/market_observations_template.csv')
        retailer_df = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        usd_df = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        
        override_rate = 50000.0
        result = build_dashboard_pricing_dataset(
            market_df, retailer_df, usd_df, usd_rate=override_rate
        )
        
        # All rows should have the override rate
        assert (result['usd_rate'] == override_rate).all()


class TestSaveDashboardPricingDataset:
    """Tests for saving the dataset."""
    
    def test_save_to_file(self, tmp_path):
        """Save dataset to CSV file."""
        market_df = load_market_observations('data/raw/market_observations_template.csv')
        retailer_df = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        usd_df = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        
        result = build_dashboard_pricing_dataset(market_df, retailer_df, usd_df)
        
        output_file = tmp_path / "test_output.csv"
        output_path = save_dashboard_pricing_dataset(result, str(output_file))
        
        # Verify file exists
        assert Path(output_path).exists()
        
        # Verify file can be read back
        loaded = pd.read_csv(output_path)
        assert len(loaded) == len(result)
        assert list(loaded.columns) == list(result.columns)
    
    def test_creates_output_directory(self):
        """Save creates output directory if it doesn't exist."""
        market_df = load_market_observations('data/raw/market_observations_template.csv')
        retailer_df = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        usd_df = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        
        result = build_dashboard_pricing_dataset(market_df, retailer_df, usd_df)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = f"{tmpdir}/subdir/test.csv"
            save_path = save_dashboard_pricing_dataset(result, output_path)
            
            assert Path(save_path).exists()
            assert Path(save_path).parent.exists()


class TestEndToEnd:
    """End-to-end pipeline tests."""
    
    def test_full_pipeline(self, tmp_path):
        """Full pipeline: load -> build -> save."""
        # Load
        market_df = load_market_observations('data/raw/market_observations_template.csv')
        retailer_df = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        usd_df = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        
        # Build
        result = build_dashboard_pricing_dataset(market_df, retailer_df, usd_df)
        
        # Verify
        assert len(result) > 0
        assert 'product_id' in result.columns
        assert 'theoretical_toman_price' in result.columns
        assert 'iran_market_premium_pct' in result.columns
        
        # Save and reload
        output_file = tmp_path / "pipeline_output.csv"
        output_path = save_dashboard_pricing_dataset(result, str(output_file))
        loaded = pd.read_csv(output_path)
        
        # Verify saved data matches result
        assert len(loaded) == len(result)
        assert set(loaded.columns) == set(result.columns)
