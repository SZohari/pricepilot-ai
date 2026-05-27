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
    get_known_brands,
    normalize_brand,
    generate_product_id,
    product_id_exists,
    validate_new_product_payload,
    append_new_product,
    validate_retailer_internal_payload,
    upsert_retailer_internal_data,
    get_latest_update_for_product,
    get_products_missing_update_today,
    validate_daily_market_update,
    validate_fx_rate_snapshot,
)
from src.data.build_pricing_dataset import load_retailer_internal_data, load_global_usd_reference


class TestLoadProductsMaster:
    """Tests for loading products master."""
    
    def test_load_products_master(self):
        """Load products master successfully."""
        df = load_products_master('data/raw/products_master.csv')
        assert len(df) > 0
        assert 'product_id' in df.columns
        assert 'brand' in df.columns
        assert 'product_name' in df.columns
    
    def test_products_master_keeps_baseline_catalog(self):
        """Products master contains the baseline products and may include user additions."""
        df = load_products_master('data/raw/products_master.csv')
        assert len(df) >= 10, f"Expected at least 10 products, got {len(df)}"
    
    def test_load_missing_file_raises_error(self):
        """Loading missing products file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_products_master('data/raw/nonexistent.csv')


class TestAddNewProduct:
    """Tests for creating new catalog products from dashboard payloads."""

    @staticmethod
    def valid_payload():
        return {
            'product_id': 'APPLE-WATCH-ULTRA-2',
            'brand': 'Apple',
            'model': 'Watch Ultra 2',
            'product_name': 'Apple Watch Ultra 2',
            'product_query': 'Apple Watch Ultra 2',
            'priority': 'high',
            'active': True,
            'torob_url': '',
            'digikala_url': '',
            'global_reference_url': '',
            'catalog_notes': 'new item',
            'our_current_price': '40,000,000',
            'our_cost_price': '30,000,000',
            'our_inventory': 0,
            'our_sales_7d': 0,
            'our_sales_30d': 0,
            'our_target_margin': 0.30,
            'our_strategy': 'balanced',
            'base_usd_price': '799.00',
            'base_usd_price_source': 'official_site',
            'usd_rate': '90,000',
            'source_url': 'example.com/reference',
            'observed_at': '2026-05-27',
            'usd_notes': 'reference',
        }

    def test_generate_product_id_is_stable_and_hyphenated(self):
        assert generate_product_id('Apple', 'Watch Ultra 2') == 'APPLE-WATCH-ULTRA-2'
        assert generate_product_id(' Apple ', 'Watch / Ultra 2!') == 'APPLE-WATCH-ULTRA-2'

    def test_duplicate_product_id_is_detected(self):
        products = pd.DataFrame({'product_id': ['APPLE-WATCH-ULTRA-2']})
        retailer = pd.DataFrame({'product_id': []})
        usd = pd.DataFrame({'product_id': []})
        assert product_id_exists('APPLE-WATCH-ULTRA-2', products, retailer, usd)

    def test_valid_new_product_payload_passes_validation(self):
        is_valid, issues = validate_new_product_payload(self.valid_payload())
        assert is_valid, issues

    def test_missing_required_fields_fail_validation(self):
        payload = self.valid_payload()
        payload['brand'] = ''
        is_valid, issues = validate_new_product_payload(payload)
        assert not is_valid
        assert any('brand' in issue for issue in issues)

    def test_current_price_below_cost_price_fails_validation(self):
        payload = self.valid_payload()
        payload['our_current_price'] = '20,000,000'
        is_valid, issues = validate_new_product_payload(payload)
        assert not is_valid
        assert any('greater' in issue for issue in issues)

    def test_invalid_target_margin_fails_validation(self):
        payload = self.valid_payload()
        payload['our_target_margin'] = 1.2
        is_valid, issues = validate_new_product_payload(payload)
        assert not is_valid
        assert any('our_target_margin' in issue for issue in issues)

    def test_append_new_product_writes_and_loads_all_three_files(self, tmp_path):
        products_file = tmp_path / 'products.csv'
        retailer_file = tmp_path / 'retailer.csv'
        usd_file = tmp_path / 'usd.csv'
        products_file.write_text(
            'product_id,brand,model,product_name,product_query,torob_url,digikala_url,global_reference_url,priority,active,notes\n'
        )
        retailer_file.write_text(
            'product_id,our_current_price,our_cost_price,our_inventory,our_sales_7d,our_sales_30d,our_target_margin,our_strategy\n'
        )
        usd_file.write_text(
            'product_id,brand,model,base_usd_price,base_usd_price_source,usd_rate,source_url,observed_at,notes\n'
        )

        product_id = append_new_product(
            str(products_file), str(retailer_file), str(usd_file), self.valid_payload()
        )

        products = load_products_master(str(products_file))
        retailer = load_retailer_internal_data(str(retailer_file))
        usd = load_global_usd_reference(str(usd_file))
        assert product_id == 'APPLE-WATCH-ULTRA-2'
        assert product_id in set(products['product_id'])
        assert product_id in set(retailer['product_id'])
        assert product_id in set(usd['product_id'])
        assert retailer.iloc[0]['our_current_price'] == 40_000_000
        assert usd.iloc[0]['usd_rate'] == 90_000

    def test_get_known_brands_and_normalize_brand(self):
        products = pd.DataFrame([
            {'product_id': 'P1', 'brand': 'Samsung', 'model': 'M1', 'product_name': 'S1'},
            {'product_id': 'P2', 'brand': 'Xiaomi', 'model': 'M2', 'product_name': 'X1'},
        ])
        known = get_known_brands(products)
        assert 'Samsung' in known and 'Xiaomi' in known

        # Normalize to existing canonical brand
        assert normalize_brand('samsung', known_brands=known) == 'Samsung'
        # Unknown brand gets title-cased
        assert normalize_brand('newbrand ltd') == 'Newbrand Ltd'


class TestRetailerInternalUpdate:
    """Tests for seller-owned store data updates."""

    @staticmethod
    def valid_payload():
        return {
            'our_current_price': '40,000,000',
            'our_cost_price': '30,000,000',
            'our_inventory': 5,
            'our_sales_7d': 2,
            'our_sales_30d': 8,
            'our_target_margin': 0.30,
            'our_strategy': 'balanced',
        }

    @staticmethod
    def write_retailer_file(path):
        path.write_text(
            'product_id,our_current_price,our_cost_price,our_inventory,our_sales_7d,our_sales_30d,our_target_margin,our_strategy\n'
            'P1,10000000,7000000,1,0,0,0.3,balanced\n'
            'P2,20000000,15000000,2,1,2,0.25,trust_builder\n'
        )

    def test_valid_payload_passes_validation(self):
        is_valid, issues = validate_retailer_internal_payload(self.valid_payload())
        assert is_valid, issues

    def test_missing_or_invalid_price_fails_validation(self):
        payload = self.valid_payload()
        payload['our_current_price'] = ''
        is_valid, issues = validate_retailer_internal_payload(payload)
        assert not is_valid
        payload['our_current_price'] = 'not-a-price'
        is_valid, issues = validate_retailer_internal_payload(payload)
        assert not is_valid

    def test_current_price_below_cost_price_fails_validation(self):
        payload = self.valid_payload()
        payload['our_current_price'] = '20,000,000'
        is_valid, issues = validate_retailer_internal_payload(payload)
        assert not is_valid
        assert any('greater' in issue for issue in issues)

    def test_invalid_target_margin_fails_validation(self):
        payload = self.valid_payload()
        payload['our_target_margin'] = 1.1
        is_valid, issues = validate_retailer_internal_payload(payload)
        assert not is_valid

    def test_invalid_strategy_fails_validation(self):
        payload = self.valid_payload()
        payload['our_strategy'] = 'unknown'
        is_valid, issues = validate_retailer_internal_payload(payload)
        assert not is_valid

    def test_upsert_updates_existing_row_without_duplication(self, tmp_path):
        retailer_file = tmp_path / 'retailer.csv'
        self.write_retailer_file(retailer_file)

        upsert_retailer_internal_data(str(retailer_file), 'P1', self.valid_payload())
        loaded = load_retailer_internal_data(str(retailer_file))

        assert (loaded['product_id'] == 'P1').sum() == 1
        assert loaded.set_index('product_id').loc['P1', 'our_current_price'] == 40_000_000
        assert loaded.set_index('product_id').loc['P2', 'our_current_price'] == 20_000_000

    def test_upsert_adds_new_product_row_if_missing(self, tmp_path):
        retailer_file = tmp_path / 'retailer.csv'
        self.write_retailer_file(retailer_file)

        upsert_retailer_internal_data(str(retailer_file), 'P3', self.valid_payload())
        loaded = load_retailer_internal_data(str(retailer_file))

        assert 'P3' in set(loaded['product_id'])
        assert loaded.set_index('product_id').loc['P3', 'our_current_price'] == 40_000_000


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

    def test_formatted_and_persian_fx_rates_pass(self):
        for rate in ["90,000", "۹۰,۰۰۰"]:
            fx = {'source': 'manual', 'symbol': 'USDIRT', 'rate_toman': rate}
            is_valid, issues = validate_fx_rate_snapshot(fx)
            assert is_valid, f"Validation failed for {rate}: {issues}"
    
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

    def test_invalid_string_rate_fails(self):
        fx = {'source': 'manual', 'symbol': 'USDIRT', 'rate_toman': 'invalid'}
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

    def test_append_formatted_fx_rate_saves_numeric_toman(self, tmp_path):
        fx_file = tmp_path / "fx_rates.csv"
        fx_file.write_text("observed_at,source,symbol,rate_toman,rate_irr,notes\n")
        fx = {'source': 'manual', 'symbol': 'USDIRT', 'rate_toman': '۹۰,۰۰۰'}

        append_fx_rate_snapshot(str(fx_file), fx)

        saved = pd.read_csv(str(fx_file))
        assert saved.iloc[0]['rate_toman'] == 90000


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

    def test_get_latest_update_uses_timestamp_then_last_row(self):
        updates_df = pd.DataFrame([
            {'update_id': 'UPD-LATE-FIRST', 'observed_at': '2026-05-27T12:00:00', 'product_id': 'APUL-GPS-1'},
            {'update_id': 'UPD-OLD', 'observed_at': '2026-05-27T10:00:00', 'product_id': 'APUL-GPS-1'},
            {'update_id': 'UPD-LATE-LAST', 'observed_at': '2026-05-27T12:00:00', 'product_id': 'APUL-GPS-1'},
        ])
        latest = get_latest_update_for_product(updates_df, 'APUL-GPS-1')
        assert latest['update_id'] == 'UPD-LATE-LAST'


class TestGetProductsMissingToday:
    """Tests for finding products missing today's update."""
    
    def test_missing_update_all_products(self):
        """All active products are missing when no updates exist."""
        products_df = load_products_master('data/raw/products_master.csv')
        updates_df = load_daily_market_updates('data/raw/daily_market_updates.csv').iloc[0:0].copy()
        
        missing = get_products_missing_update_today(products_df, updates_df)
        active_count = len(products_df[products_df.get('active', True) == True])
        
        assert len(missing) == active_count
