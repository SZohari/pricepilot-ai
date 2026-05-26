"""
Tests for manual market data entry helpers.

Tests verify:
- Loading products master, daily updates, and FX snapshots
- Appending new market updates and FX snapshots
- Validating market update and FX snapshot inputs
- Finding latest updates and missing products
"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
from datetime import datetime

from src.data.manual_entry import (
    load_products_master,
    load_daily_market_updates,
    load_fx_rate_snapshots,
    append_daily_market_update,
    append_fx_rate_snapshot,
    get_latest_update_for_product,
    get_products_missing_update_today,
    validate_daily_market_update,
    validate_fx_rate_snapshot,
)


class TestLoadProductsMaster:
    """Tests for loading products master."""
    
    def test_load_products_master(self):
        """Load products master successfully."""
        df = load_products_master('data/raw/products_master.csv')
        assert len(df) > 0
        assert 'product_id' in df.columns
        assert 'brand' in df.columns
        assert 'product_name' in df.columns
    
    def test_products_master_has_ten_products(self):
        """Products master contains 10 products."""
        df = load_products_master('data/raw/products_master.csv')
        assert len(df) == 10, f"Expected 10 products, got {len(df)}"
    
    def test_load_missing_file_raises_error(self):
        """Loading missing products file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_products_master('data/raw/nonexistent.csv')


class TestLoadDailyMarketUpdates:
    """Tests for loading daily market updates."""
    
    def test_load_daily_updates_empty_file(self):
        """Load daily updates file with only headers."""
        df = load_daily_market_updates('data/raw/daily_market_updates.csv')
        assert isinstance(df, pd.DataFrame)
        assert 'product_id' in df.columns
    
    def test_load_missing_updates_file_raises_error(self):
        """Loading missing updates file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_daily_market_updates('data/raw/nonexistent_updates.csv')


class TestLoadFXRateSnapshots:
    """Tests for loading FX rate snapshots."""
    
    def test_load_fx_snapshots_empty_file(self):
        """Load FX snapshots file with only headers."""
        df = load_fx_rate_snapshots('data/raw/fx_rate_snapshots.csv')
        assert isinstance(df, pd.DataFrame)
        assert 'rate_toman' in df.columns
    
    def test_load_missing_fx_file_raises_error(self):
        """Loading missing FX file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_fx_rate_snapshots('data/raw/nonexistent_fx.csv')


class TestValidateDailyMarketUpdate:
    """Tests for market update validation."""
    
    def test_valid_update_passes(self):
        """Valid market update passes validation."""
        update = {
            'product_id': 'APUL-GPS-1',
            'torob_min_price': 35000000,
            'observed_at': '2026-05-26T14:30:00',
        }
        is_valid, issues = validate_daily_market_update(update)
        assert is_valid, f"Validation failed: {issues}"
    
    def test_missing_product_id_fails(self):
        """Update without product_id fails validation."""
        update = {
            'torob_min_price': 35000000,
        }
        is_valid, issues = validate_daily_market_update(update)
        assert not is_valid
        assert any('product_id' in issue for issue in issues)
    
    def test_missing_all_prices_fails(self):
        """Update without any price field fails validation."""
        update = {
            'product_id': 'APUL-GPS-1',
        }
        is_valid, issues = validate_daily_market_update(update)
        assert not is_valid
        assert any('price' in issue for issue in issues)
    
    def test_non_numeric_price_fails(self):
        """Update with non-numeric price fails validation."""
        update = {
            'product_id': 'APUL-GPS-1',
            'torob_min_price': 'not_a_number',
        }
        is_valid, issues = validate_daily_market_update(update)
        assert not is_valid
        assert any('numeric' in issue for issue in issues)
    
    def test_multiple_prices_passes(self):
        """Update with multiple price fields passes."""
        update = {
            'product_id': 'APUL-GPS-1',
            'torob_min_price': 35000000,
            'torob_median_price': 37200000,
            'digikala_price': 38000000,
        }
        is_valid, issues = validate_daily_market_update(update)
        assert is_valid


class TestValidateFXSnapshot:
    """Tests for FX snapshot validation."""
    
    def test_valid_fx_snapshot_passes(self):
        """Valid FX snapshot passes validation."""
        fx = {
            'source': 'manual',
            'symbol': 'USDIRT',
            'rate_toman': 45000.0,
        }
        is_valid, issues = validate_fx_rate_snapshot(fx)
        assert is_valid, f"Validation failed: {issues}"
    
    def test_missing_source_fails(self):
        """Snapshot without source fails."""
        fx = {
            'symbol': 'USDIRT',
            'rate_toman': 45000.0,
        }
        is_valid, issues = validate_fx_rate_snapshot(fx)
        assert not is_valid
    
    def test_missing_symbol_fails(self):
        """Snapshot without symbol fails."""
        fx = {
            'source': 'manual',
            'rate_toman': 45000.0,
        }
        is_valid, issues = validate_fx_rate_snapshot(fx)
        assert not is_valid
    
    def test_missing_rate_fails(self):
        """Snapshot without rate fails."""
        fx = {
            'source': 'manual',
            'symbol': 'USDIRT',
        }
        is_valid, issues = validate_fx_rate_snapshot(fx)
        assert not is_valid
    
    def test_non_positive_rate_fails(self):
        """Snapshot with non-positive rate fails."""
        fx = {
            'source': 'manual',
            'symbol': 'USDIRT',
            'rate_toman': -100.0,
        }
        is_valid, issues = validate_fx_rate_snapshot(fx)
        assert not is_valid
        assert any('positive' in issue for issue in issues)
    
    def test_zero_rate_fails(self):
        """Snapshot with zero rate fails."""
        fx = {
            'source': 'manual',
            'symbol': 'USDIRT',
            'rate_toman': 0.0,
        }
        is_valid, issues = validate_fx_rate_snapshot(fx)
        assert not is_valid


class TestAppendDailyMarketUpdate:
    """Tests for appending market updates."""
    
    def test_append_update_to_empty_file(self, tmp_path):
        """Append market update to empty file."""
        update_file = tmp_path / "updates.csv"
        update_file.write_text("update_id,observed_at,product_id,torob_min_price,torob_median_price,digikala_price,market_max_price,availability_note,notes\n")
        
        update = {
            'product_id': 'APUL-GPS-1',
            'torob_min_price': 35000000,
            'observed_at': '2026-05-26T14:30:00',
        }
        
        result = append_daily_market_update(str(update_file), update)
        assert result is True
        
        # Verify file has one row plus header
        df = pd.read_csv(str(update_file))
        assert len(df) == 1
    
    def test_append_invalid_update_fails(self, tmp_path):
        """Appending invalid update raises ValueError."""
        update_file = tmp_path / "updates.csv"
        update_file.write_text("update_id,observed_at,product_id,torob_min_price,torob_median_price,digikala_price,market_max_price,availability_note,notes\n")
        
        update = {
            # Missing product_id
            'torob_min_price': 35000000,
        }
        
        with pytest.raises(ValueError):
            append_daily_market_update(str(update_file), update)


class TestAppendFXSnapshot:
    """Tests for appending FX snapshots."""
    
    def test_append_fx_snapshot_to_empty_file(self, tmp_path):
        """Append FX snapshot to empty file."""
        fx_file = tmp_path / "fx_rates.csv"
        fx_file.write_text("observed_at,source,symbol,rate_toman,rate_irr,notes\n")
        
        fx = {
            'source': 'manual',
            'symbol': 'USDIRT',
            'rate_toman': 45000.0,
        }
        
        result = append_fx_rate_snapshot(str(fx_file), fx)
        assert result is True
        
        # Verify file has one row plus header
        df = pd.read_csv(str(fx_file))
        assert len(df) == 1
    
    def test_append_invalid_fx_fails(self, tmp_path):
        """Appending invalid FX snapshot raises ValueError."""
        fx_file = tmp_path / "fx_rates.csv"
        fx_file.write_text("observed_at,source,symbol,rate_toman,rate_irr,notes\n")
        
        fx = {
            'source': 'manual',
            # Missing symbol
            'rate_toman': 45000.0,
        }
        
        with pytest.raises(ValueError):
            append_fx_rate_snapshot(str(fx_file), fx)


class TestGetLatestUpdate:
    """Tests for getting latest product update."""
    
    def test_get_latest_update_existing_product(self, tmp_path):
        """Get latest update for product that has updates."""
        update_file = tmp_path / "updates.csv"
        
        # Create file with two updates for same product
        df = pd.DataFrame([
            {
                'update_id': 'UPD-001',
                'observed_at': '2026-05-26T10:00:00',
                'product_id': 'APUL-GPS-1',
                'torob_min_price': 35000000,
                'torob_median_price': 36000000,
                'digikala_price': 38000000,
                'market_max_price': 39000000,
                'availability_note': 'available',
                'notes': 'first',
            },
            {
                'update_id': 'UPD-002',
                'observed_at': '2026-05-26T14:00:00',
                'product_id': 'APUL-GPS-1',
                'torob_min_price': 35200000,
                'torob_median_price': 37000000,
                'digikala_price': 38500000,
                'market_max_price': 40000000,
                'availability_note': 'available',
                'notes': 'second',
            },
        ])
        df.to_csv(str(update_file), index=False)
        
        updates_df = pd.read_csv(str(update_file))
        latest = get_latest_update_for_product(updates_df, 'APUL-GPS-1')
        
        assert latest is not None
        assert latest['update_id'] == 'UPD-002'
        assert latest['notes'] == 'second'
    
    def test_get_latest_update_nonexistent_product(self):
        """Get latest update for product with no updates returns None."""
        updates_df = load_daily_market_updates('data/raw/daily_market_updates.csv')
        latest = get_latest_update_for_product(updates_df, 'NONEXISTENT')
        assert latest is None


class TestGetProductsMissingToday:
    """Tests for finding products missing today's update."""
    
    def test_missing_update_all_products(self):
        """All active products are missing when no updates exist."""
        products_df = load_products_master('data/raw/products_master.csv')
        updates_df = load_daily_market_updates('data/raw/daily_market_updates.csv')
        
        missing = get_products_missing_update_today(products_df, updates_df)
        active_count = len(products_df[products_df.get('active', True) == True])
        
        assert len(missing) == active_count
