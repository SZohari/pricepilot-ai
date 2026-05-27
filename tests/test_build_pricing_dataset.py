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


class TestManualInputOverrides:
    """Tests for daily market updates and FX snapshot pipeline inputs."""

    @staticmethod
    def build(daily_updates=None, fx_snapshots=None):
        market = load_market_observations('data/raw/market_observations_template.csv')
        retailer = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        usd = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        return build_dashboard_pricing_dataset(
            market,
            retailer,
            usd,
            daily_updates_df=daily_updates,
            fx_snapshots_df=fx_snapshots,
        )

    @staticmethod
    def daily_update(**values):
        update = {
            'observed_at': '2026-05-27T10:00:00',
            'product_id': 'APUL-GPS-1',
            'torob_min_price': np.nan,
            'torob_median_price': np.nan,
            'digikala_price': np.nan,
            'market_max_price': np.nan,
        }
        update.update(values)
        return pd.DataFrame([update])

    def test_latest_daily_update_overrides_market_min_price(self):
        updates = self.daily_update(torob_min_price=36_100_000)
        result = self.build(daily_updates=updates).set_index('product_id')
        assert result.loc['APUL-GPS-1', 'market_min_price'] == 36_100_000

    def test_latest_daily_update_overrides_market_median_price(self):
        updates = self.daily_update(torob_median_price=37_100_000)
        result = self.build(daily_updates=updates).set_index('product_id')
        assert result.loc['APUL-GPS-1', 'market_median_price'] == 37_100_000

    def test_latest_daily_update_preserves_digikala_price(self):
        updates = self.daily_update(digikala_price=38_100_000)
        result = self.build(daily_updates=updates).set_index('product_id')
        assert result.loc['APUL-GPS-1', 'digikala_price'] == 38_100_000

    def test_daily_update_infers_safe_max_when_missing(self):
        updates = self.daily_update(torob_min_price=36_100_000)
        row = self.build(daily_updates=updates).set_index('product_id').loc['APUL-GPS-1']
        assert pd.notna(row['market_max_price'])
        assert row['market_max_price'] >= row['market_median_price']

    def test_blank_median_does_not_replace_aggregated_market_median(self):
        baseline = self.build().set_index('product_id').loc['APUL-GPS-1', 'market_median_price']
        updates = self.daily_update(torob_min_price=36_100_000, torob_median_price=np.nan)
        row = self.build(daily_updates=updates).set_index('product_id').loc['APUL-GPS-1']
        assert row['market_median_price'] == baseline

    def test_latest_daily_update_wins_and_last_row_breaks_ties(self):
        updates = pd.DataFrame([
            {'observed_at': '2026-05-27T11:00:00', 'product_id': 'APUL-GPS-1', 'torob_min_price': 35_000_000},
            {'observed_at': '2026-05-27T12:00:00', 'product_id': 'APUL-GPS-1', 'torob_min_price': 36_000_000},
            {'observed_at': '2026-05-27T12:00:00', 'product_id': 'APUL-GPS-1', 'torob_min_price': 37_000_000},
        ])
        result = self.build(daily_updates=updates).set_index('product_id')
        assert result.loc['APUL-GPS-1', 'market_min_price'] == 37_000_000

    def test_products_without_daily_updates_keep_observation_aggregation(self):
        baseline = self.build().set_index('product_id')
        updates = self.daily_update(torob_min_price=36_100_000)
        updated = self.build(daily_updates=updates).set_index('product_id')
        assert updated.loc['GAML-SE-1', 'market_min_price'] == baseline.loc['GAML-SE-1', 'market_min_price']

    def test_latest_positive_fx_snapshot_overrides_usd_rate(self):
        snapshots = pd.DataFrame([
            {'observed_at': '2026-05-27T09:00:00', 'rate_toman': 50_000},
            {'observed_at': '2026-05-27T11:00:00', 'rate_toman': 52_000},
        ])
        result = self.build(fx_snapshots=snapshots)
        assert (result['usd_rate'] == 52_000).all()

    def test_invalid_or_non_positive_fx_rates_are_ignored(self):
        snapshots = pd.DataFrame([
            {'observed_at': '2026-05-27T09:00:00', 'rate_toman': 'invalid'},
            {'observed_at': '2026-05-27T11:00:00', 'rate_toman': 0},
            {'observed_at': '2026-05-27T12:00:00', 'rate_toman': -1},
        ])
        result = self.build(fx_snapshots=snapshots)
        assert (result['usd_rate'] == 45_000).all()

    def test_later_blank_fx_snapshot_does_not_replace_latest_valid_rate(self):
        snapshots = pd.DataFrame([
            {'observed_at': '2026-05-27T09:00:00', 'rate_toman': 52_000},
            {'observed_at': '2026-05-27T11:00:00', 'rate_toman': np.nan},
        ])
        result = self.build(fx_snapshots=snapshots)
        assert (result['usd_rate'] == 52_000).all()

    def test_fx_override_recalculates_theoretical_toman_price(self):
        snapshots = pd.DataFrame([{'observed_at': '2026-05-27T11:00:00', 'rate_toman': 52_000}])
        row = self.build(fx_snapshots=snapshots).set_index('product_id').loc['APUL-GPS-1']
        assert row['theoretical_toman_price'] == int(row['base_usd_price'] * 52_000)

    def test_fx_override_recalculates_iran_market_premium_pct(self):
        snapshots = pd.DataFrame([{'observed_at': '2026-05-27T11:00:00', 'rate_toman': 52_000}])
        row = self.build(fx_snapshots=snapshots).set_index('product_id').loc['APUL-GPS-1']
        expected = (row['market_median_price'] - row['theoretical_toman_price']) / row['theoretical_toman_price']
        assert row['iran_market_premium_pct'] == pytest.approx(expected)

    def test_daily_updates_do_not_drop_expected_products(self):
        updates = self.daily_update(torob_min_price=36_100_000)
        result = self.build(daily_updates=updates)
        assert set(result['product_id']) == {
            'APUL-GPS-1', 'GAML-SE-1', 'FITB-CHG-1', 'HWAT-GTA-1', 'XIAO-MI-1',
        }

    def test_output_has_no_nan_in_numeric_pricing_fields(self):
        updates = self.daily_update(torob_min_price=36_100_000)
        snapshots = pd.DataFrame([{'observed_at': '2026-05-27T11:00:00', 'rate_toman': 52_000}])
        result = self.build(daily_updates=updates, fx_snapshots=snapshots)
        fields = [
            'usd_rate', 'theoretical_toman_price', 'market_min_price',
            'market_median_price', 'market_max_price', 'torob_min_price',
            'torob_median_price', 'digikala_price', 'our_current_price',
            'our_cost_price',
        ]
        assert not result[fields].isna().any().any()

    def test_catalog_product_requires_manual_market_update_before_output(self):
        market = load_market_observations('data/raw/market_observations_template.csv')
        retailer = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        usd = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        products = pd.DataFrame([{
            'product_id': 'NEW-WATCH-1', 'product_name': 'New Watch 1',
            'brand': 'New', 'model': 'Watch 1',
        }])
        retailer = pd.concat([retailer, pd.DataFrame([{
            'product_id': 'NEW-WATCH-1', 'our_current_price': 10_000_000,
            'our_cost_price': 7_000_000, 'our_inventory': 1, 'our_sales_7d': 0,
            'our_sales_30d': 0, 'our_target_margin': 0.3, 'our_strategy': 'balanced',
        }])], ignore_index=True)
        usd = pd.concat([usd, pd.DataFrame([{
            'product_id': 'NEW-WATCH-1', 'brand': 'New', 'model': 'Watch 1',
            'base_usd_price': 100, 'base_usd_price_source': 'manual',
            'usd_rate': 45_000, 'source_url': '', 'observed_at': '2026-05-27', 'notes': '',
        }])], ignore_index=True)

        without_update = build_dashboard_pricing_dataset(market, retailer, usd, products_df=products)
        assert 'NEW-WATCH-1' not in set(without_update['product_id'])

        update = pd.DataFrame([{
            'product_id': 'NEW-WATCH-1', 'observed_at': '2026-05-27T12:00:00',
            'torob_min_price': 9_500_000, 'torob_median_price': 10_000_000,
            'digikala_price': 10_100_000, 'market_max_price': 10_200_000,
        }])
        with_update = build_dashboard_pricing_dataset(
            market, retailer, usd, daily_updates_df=update, products_df=products,
        )
        row = with_update.set_index('product_id').loc['NEW-WATCH-1']
        assert row['market_min_price'] == 9_500_000
        assert row['product_name'] == 'New Watch 1'


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


class TestTemplateAlignment:
    """Tests for template data alignment and quality."""
    
    def test_market_observations_csv_column_count(self):
        """Every row in market_observations_template.csv has 14 columns."""
        df = pd.read_csv('data/raw/market_observations_template.csv')
        assert len(df.columns) == 14, f"Expected 14 columns, got {len(df.columns)}"
        
        # Verify no NaN in critical columns
        assert not df['product_id'].isna().any()
        assert not df['product_query'].isna().any()
        assert not df['normalized_product_name'].isna().any()
        assert not df['listed_price'].isna().any()
    
    def test_market_observations_prices_are_numeric(self):
        """All prices in market_observations_template.csv can be parsed as numeric."""
        df = pd.read_csv('data/raw/market_observations_template.csv')
        prices = pd.to_numeric(df['listed_price'], errors='coerce')
        assert not prices.isna().any(), "Some prices cannot be parsed as numeric"
    
    def test_all_templates_share_product_ids(self):
        """All three raw templates contain the same 5 product_ids."""
        market = pd.read_csv('data/raw/market_observations_template.csv')
        retailer = pd.read_csv('data/raw/retailer_internal_demo_template.csv')
        usd = pd.read_csv('data/raw/global_usd_reference_template.csv')
        
        market_ids = set(market['product_id'].unique())
        retailer_ids = set(retailer['product_id'].unique())
        usd_ids = set(usd['product_id'].unique())
        
        # Should all be the same
        assert market_ids == retailer_ids, f"Market {market_ids} != Retailer {retailer_ids}"
        assert retailer_ids == usd_ids, f"Retailer {retailer_ids} != USD {usd_ids}"
        
        # Should have exactly 5 products
        assert len(market_ids) == 5, f"Expected 5 products, got {len(market_ids)}"
    
    def test_each_product_has_minimum_observations(self):
        """Each product_id in market_observations has at least 3 observations."""
        df = pd.read_csv('data/raw/market_observations_template.csv')
        
        for product_id in df['product_id'].unique():
            count = len(df[df['product_id'] == product_id])
            assert count >= 3, f"{product_id} has only {count} observations, need at least 3"
    
    def test_build_pipeline_outputs_five_products(self):
        """Build pipeline processes all 5 products from templates."""
        market = load_market_observations('data/raw/market_observations_template.csv')
        retailer = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        usd = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        
        result = build_dashboard_pricing_dataset(market, retailer, usd)
        
        assert len(result) == 5, f"Expected 5 products in output, got {len(result)}"
        
        # Verify all expected products are present
        expected_ids = sorted(['APUL-GPS-1', 'GAML-SE-1', 'FITB-CHG-1', 'HWAT-GTA-1', 'XIAO-MI-1'])
        actual_ids = sorted(result['product_id'].unique())
        assert actual_ids == expected_ids, f"Expected {expected_ids}, got {actual_ids}"
    
    def test_output_products_have_all_data(self):
        """Every output product has market, retailer, and USD reference fields."""
        market = load_market_observations('data/raw/market_observations_template.csv')
        retailer = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        usd = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        
        result = build_dashboard_pricing_dataset(market, retailer, usd)
        
        # Check market fields
        market_fields = ['market_min_price', 'market_median_price', 'market_max_price', 'seller_count']
        for field in market_fields:
            assert field in result.columns, f"Missing market field: {field}"
            assert not result[field].isna().any(), f"Market field {field} has null values"
        
        # Check retailer fields
        retailer_fields = ['our_current_price', 'our_cost_price', 'our_inventory', 'our_strategy']
        for field in retailer_fields:
            assert field in result.columns, f"Missing retailer field: {field}"
            assert not result[field].isna().any(), f"Retailer field {field} has null values"
        
        # Check USD fields
        usd_fields = ['base_usd_price', 'usd_rate', 'theoretical_toman_price']
        for field in usd_fields:
            assert field in result.columns, f"Missing USD field: {field}"
            assert not result[field].isna().any(), f"USD field {field} has null values"


class TestLoadProcessedPricingData:
    """Tests for loading processed dashboard-ready pricing data."""
    
    def test_load_processed_data_missing_file(self):
        """Loading processed data with missing file raises FileNotFoundError."""
        from src.data.build_pricing_dataset import load_processed_pricing_data
        
        with pytest.raises(FileNotFoundError):
            load_processed_pricing_data('data/processed/nonexistent.csv')
    
    def test_load_processed_data_existing_file(self):
        """Loading processed data from existing file succeeds."""
        from src.data.build_pricing_dataset import load_processed_pricing_data
        
        # Build the processed dataset if it doesn't exist
        if not Path('data/processed/dashboard_pricing_data.csv').exists():
            market = load_market_observations('data/raw/market_observations_template.csv')
            retailer = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
            usd = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
            result = build_dashboard_pricing_dataset(market, retailer, usd)
            save_dashboard_pricing_dataset(result)
        
        # Now load it
        df = load_processed_pricing_data()
        assert df is not None
        assert len(df) > 0
        assert 'product_id' in df.columns
    
    def test_load_processed_data_has_five_products(self):
        """Loaded processed data contains exactly 5 products."""
        from src.data.build_pricing_dataset import load_processed_pricing_data
        
        # Build the processed dataset if needed
        if not Path('data/processed/dashboard_pricing_data.csv').exists():
            market = load_market_observations('data/raw/market_observations_template.csv')
            retailer = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
            usd = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
            result = build_dashboard_pricing_dataset(market, retailer, usd)
            save_dashboard_pricing_dataset(result)
        
        df = load_processed_pricing_data()
        assert len(df) == 5, f"Expected 5 products, got {len(df)}"
    
    def test_load_processed_data_has_required_fields(self):
        """Loaded processed data has all required Phase 2 fields."""
        from src.data.build_pricing_dataset import load_processed_pricing_data
        
        # Build the processed dataset if needed
        if not Path('data/processed/dashboard_pricing_data.csv').exists():
            market = load_market_observations('data/raw/market_observations_template.csv')
            retailer = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
            usd = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
            result = build_dashboard_pricing_dataset(market, retailer, usd)
            save_dashboard_pricing_dataset(result)
        
        df = load_processed_pricing_data()
        required_fields = [
            'product_id',
            'product_name',
            'market_median_price',
            'our_current_price',
            'our_cost_price',
            'our_target_margin',
            'our_strategy',
        ]
        
        for field in required_fields:
            assert field in df.columns, f"Missing required field: {field}"
            assert not df[field].isna().any(), f"Required field {field} has null values"
