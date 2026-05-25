"""
Tests for market aggregation utilities.

Tests verify:
- Correct calculation of market min/median/max prices
- Accurate seller counting (total and available)
- Price spread percentage calculations
- Data validation
- Aggregation with empty datasets
"""

import pytest
import pandas as pd
from src.data.market_aggregation import (
    aggregate_market_observations,
    calculate_market_min_median_max,
    calculate_seller_counts,
    calculate_price_spread_percent,
    merge_market_observations_with_internal,
    validate_market_observations,
)


class TestCalculateMarketMinMedianMax:
    """Tests for min/median/max price calculation."""
    
    def test_min_price_calculated_correctly(self):
        """Min price should be the lowest listed_price."""
        df = pd.DataFrame({
            'listed_price': [100, 200, 300, 150],
            'product_id': ['P1'] * 4,
        })
        result = calculate_market_min_median_max(df)
        assert result['min'] == 100
    
    def test_median_price_calculated_correctly(self):
        """Median price should be the middle value."""
        df = pd.DataFrame({
            'listed_price': [100, 200, 300],
            'product_id': ['P1'] * 3,
        })
        result = calculate_market_min_median_max(df)
        assert result['median'] == 200
    
    def test_max_price_calculated_correctly(self):
        """Max price should be the highest listed_price."""
        df = pd.DataFrame({
            'listed_price': [100, 200, 300, 150],
            'product_id': ['P1'] * 4,
        })
        result = calculate_market_min_median_max(df)
        assert result['max'] == 300
    
    def test_handles_single_price(self):
        """With single price, min=median=max."""
        df = pd.DataFrame({
            'listed_price': [250],
            'product_id': ['P1'],
        })
        result = calculate_market_min_median_max(df)
        assert result['min'] == 250
        assert result['median'] == 250
        assert result['max'] == 250
    
    def test_handles_empty_dataframe(self):
        """Empty dataframe returns zeros."""
        df = pd.DataFrame({
            'listed_price': [],
            'product_id': [],
        })
        result = calculate_market_min_median_max(df)
        assert result['min'] == 0.0
        assert result['median'] == 0.0
        assert result['max'] == 0.0
    
    def test_handles_nan_prices(self):
        """NaN prices are ignored."""
        df = pd.DataFrame({
            'listed_price': [100, None, 300, 200],
            'product_id': ['P1'] * 4,
        })
        result = calculate_market_min_median_max(df)
        assert result['min'] == 100
        assert result['median'] == 200
        assert result['max'] == 300


class TestCalculateSellerCounts:
    """Tests for seller counting logic."""
    
    def test_total_seller_count(self):
        """Count unique sellers."""
        df = pd.DataFrame({
            'seller_name': ['Store A', 'Store B', 'Store A', 'Store C'],
            'availability_status': ['available'] * 4,
        })
        result = calculate_seller_counts(df)
        assert result['total'] == 3
    
    def test_available_seller_count_includes_available(self):
        """Available sellers includes 'available' status."""
        df = pd.DataFrame({
            'seller_name': ['Store A', 'Store B', 'Store C', 'Store D'],
            'availability_status': ['available', 'available', 'unavailable', 'available'],
        })
        result = calculate_seller_counts(df)
        assert result['available'] == 3
    
    def test_available_seller_count_includes_low_stock(self):
        """Available sellers includes 'low_stock' status."""
        df = pd.DataFrame({
            'seller_name': ['Store A', 'Store B', 'Store C'],
            'availability_status': ['available', 'low_stock', 'unavailable'],
        })
        result = calculate_seller_counts(df)
        assert result['available'] == 2
    
    def test_available_seller_count_excludes_unavailable(self):
        """Available sellers excludes 'unavailable' status."""
        df = pd.DataFrame({
            'seller_name': ['Store A', 'Store B'],
            'availability_status': ['unavailable', 'unavailable'],
        })
        result = calculate_seller_counts(df)
        assert result['available'] == 0
    
    def test_duplicate_sellers_counted_once(self):
        """Duplicate seller entries count as single seller."""
        df = pd.DataFrame({
            'seller_name': ['Store A', 'Store A', 'Store A'],
            'availability_status': ['available'] * 3,
        })
        result = calculate_seller_counts(df)
        assert result['total'] == 1
        assert result['available'] == 1
    
    def test_empty_dataframe_returns_zero_sellers(self):
        """Empty dataframe returns zero sellers."""
        df = pd.DataFrame({
            'seller_name': [],
            'availability_status': [],
        })
        result = calculate_seller_counts(df)
        assert result['total'] == 0
        assert result['available'] == 0


class TestCalculatePriceSpreadPercent:
    """Tests for price spread calculation."""
    
    def test_spread_with_identical_prices(self):
        """Identical prices result in 0% spread."""
        df = pd.DataFrame({
            'listed_price': [100, 100, 100],
        })
        result = calculate_price_spread_percent(df)
        assert result == 0.0
    
    def test_spread_with_different_prices(self):
        """(max - min) / median * 100."""
        df = pd.DataFrame({
            'listed_price': [100, 200, 300],  # min=100, median=200, max=300
        })
        result = calculate_price_spread_percent(df)
        expected = (300 - 100) / 200 * 100  # 100%
        assert result == expected
    
    def test_spread_with_single_price(self):
        """Single price results in 0% spread."""
        df = pd.DataFrame({
            'listed_price': [250],
        })
        result = calculate_price_spread_percent(df)
        assert result == 0.0
    
    def test_spread_with_empty_dataframe(self):
        """Empty dataframe returns 0% spread."""
        df = pd.DataFrame({
            'listed_price': [],
        })
        result = calculate_price_spread_percent(df)
        assert result == 0.0
    
    def test_spread_is_positive(self):
        """Spread is always non-negative."""
        df = pd.DataFrame({
            'listed_price': [10000, 15000, 20000],
        })
        result = calculate_price_spread_percent(df)
        assert result >= 0.0
    
    def test_spread_realistic_scenario(self):
        """Realistic market spread (smartwatch prices)."""
        df = pd.DataFrame({
            'listed_price': [32500000, 35200000, 38900000],  # Toman
        })
        result = calculate_price_spread_percent(df)
        expected = (38900000 - 32500000) / 35200000 * 100
        assert abs(result - expected) < 0.01


class TestAggregateMarketObservations:
    """Tests for full aggregation function."""
    
    def test_aggregates_single_product(self):
        """Aggregates multiple observations into single product row."""
        df = pd.DataFrame({
            'product_id': ['P1', 'P1', 'P1'],
            'normalized_product_name': ['Watch', 'Watch', 'Watch'],
            'brand': ['Apple', 'Apple', 'Apple'],
            'model': ['Ultra', 'Ultra', 'Ultra'],
            'listed_price': [100, 150, 200],
            'availability_status': ['available', 'available', 'low_stock'],
            'seller_name': ['Store A', 'Store B', 'Store A'],
            'source': ['Torob', 'Digikala', 'Torob'],
        })
        result = aggregate_market_observations(df)
        assert len(result) == 1
        assert result.iloc[0]['product_id'] == 'P1'
    
    def test_aggregates_multiple_products(self):
        """Aggregates multiple products separately."""
        df = pd.DataFrame({
            'product_id': ['P1', 'P1', 'P2', 'P2'],
            'normalized_product_name': ['Watch A', 'Watch A', 'Watch B', 'Watch B'],
            'brand': ['Apple', 'Apple', 'Samsung', 'Samsung'],
            'model': ['Ultra', 'Ultra', 'Galaxy', 'Galaxy'],
            'listed_price': [100, 150, 200, 250],
            'availability_status': ['available', 'available', 'available', 'low_stock'],
            'seller_name': ['Store A', 'Store B', 'Store C', 'Store D'],
            'source': ['Torob', 'Digikala', 'Torob', 'Digikala'],
        })
        result = aggregate_market_observations(df)
        assert len(result) == 2
        assert set(result['product_id']) == {'P1', 'P2'}
    
    def test_output_has_correct_columns(self):
        """Output dataframe has all required columns."""
        df = pd.DataFrame({
            'product_id': ['P1'],
            'normalized_product_name': ['Watch'],
            'brand': ['Apple'],
            'model': ['Ultra'],
            'listed_price': [100],
            'availability_status': ['available'],
            'seller_name': ['Store A'],
            'source': ['Torob'],
        })
        result = aggregate_market_observations(df)
        expected_cols = [
            'product_id',
            'product_name',
            'brand',
            'model',
            'market_min_price',
            'market_median_price',
            'market_max_price',
            'market_avg_price',
            'seller_count',
            'available_seller_count',
            'price_spread_percent',
        ]
        for col in expected_cols:
            assert col in result.columns
    
    def test_empty_dataframe_returns_empty(self):
        """Empty input returns empty output with correct columns."""
        df = pd.DataFrame()
        result = aggregate_market_observations(df)
        assert result.empty
        assert 'product_id' in result.columns
    
    def test_aggregation_with_realistic_data(self):
        """Aggregation works with realistic smartwatch data."""
        df = pd.DataFrame({
            'product_id': ['APUL-GPS-1'] * 5,
            'normalized_product_name': ['Apple Watch Ultra GPS'] * 5,
            'brand': ['Apple'] * 5,
            'model': ['Watch Ultra GPS'] * 5,
            'listed_price': [37200000, 38900000, 35400000, 36800000, 39500000],
            'availability_status': ['available', 'available', 'available', 'unavailable', 'available'],
            'seller_name': ['TechMart', 'ElectroShop', 'SmartDevice', 'OnlineElectro', 'Premium'],
            'source': ['Torob', 'Digikala', 'Torob', 'Digikala', 'Torob'],
        })
        result = aggregate_market_observations(df)
        assert len(result) == 1
        assert result.iloc[0]['market_min_price'] == 35400000
        assert result.iloc[0]['market_max_price'] == 39500000
        assert result.iloc[0]['seller_count'] == 5
        assert result.iloc[0]['available_seller_count'] == 4


class TestMergeMarketWithInternal:
    """Tests for merging market aggregates with internal data."""
    
    def test_merge_creates_combined_dataset(self):
        """Merge joins market and internal data on product_id."""
        market_df = pd.DataFrame({
            'product_id': ['P1', 'P2'],
            'market_min_price': [100, 200],
            'seller_count': [5, 3],
        })
        internal_df = pd.DataFrame({
            'product_id': ['P1', 'P2'],
            'our_current_price': [150, 250],
            'our_cost_price': [100, 180],
        })
        result = merge_market_observations_with_internal(market_df, internal_df)
        assert len(result) == 2
        assert 'market_min_price' in result.columns
        assert 'our_current_price' in result.columns
    
    def test_merge_only_includes_products_in_both(self):
        """Merge uses inner join (only common products)."""
        market_df = pd.DataFrame({
            'product_id': ['P1', 'P2', 'P3'],
            'market_min_price': [100, 200, 300],
        })
        internal_df = pd.DataFrame({
            'product_id': ['P1', 'P2'],
            'our_current_price': [150, 250],
        })
        result = merge_market_observations_with_internal(market_df, internal_df)
        assert len(result) == 2
        assert set(result['product_id']) == {'P1', 'P2'}


class TestValidateMarketObservations:
    """Tests for data validation."""
    
    def test_valid_data_passes(self):
        """Valid dataframe passes validation."""
        df = pd.DataFrame({
            'observation_id': ['OBS-001'],
            'observed_at': ['2026-05-26'],
            'product_id': ['P1'],
            'normalized_product_name': ['Watch'],
            'brand': ['Apple'],
            'model': ['Ultra'],
            'listed_price': [100],
            'availability_status': ['available'],
            'seller_name': ['Store A'],
        })
        is_valid, issues = validate_market_observations(df)
        assert is_valid is True
        assert len(issues) == 0
    
    def test_missing_column_fails(self):
        """Missing required column fails validation."""
        df = pd.DataFrame({
            'observation_id': ['OBS-001'],
            'product_id': ['P1'],
            'brand': ['Apple'],
            # Missing other required columns
        })
        is_valid, issues = validate_market_observations(df)
        assert is_valid is False
        assert len(issues) > 0
    
    def test_empty_dataframe_fails(self):
        """Empty dataframe fails validation."""
        df = pd.DataFrame()
        is_valid, issues = validate_market_observations(df)
        assert is_valid is False
        assert 'empty' in ' '.join(issues).lower()
    
    def test_negative_price_detected(self):
        """Negative prices are flagged."""
        df = pd.DataFrame({
            'observation_id': ['OBS-001', 'OBS-002'],
            'observed_at': ['2026-05-26', '2026-05-26'],
            'product_id': ['P1', 'P1'],
            'normalized_product_name': ['Watch', 'Watch'],
            'brand': ['Apple', 'Apple'],
            'model': ['Ultra', 'Ultra'],
            'listed_price': [100, -50],
            'availability_status': ['available', 'available'],
            'seller_name': ['Store A', 'Store B'],
        })
        is_valid, issues = validate_market_observations(df)
        assert is_valid is False
        assert any('negative' in issue.lower() for issue in issues)
    
    def test_missing_product_id_detected(self):
        """Missing product_id is flagged."""
        df = pd.DataFrame({
            'observation_id': ['OBS-001'],
            'observed_at': ['2026-05-26'],
            'product_id': [None],
            'normalized_product_name': ['Watch'],
            'brand': ['Apple'],
            'model': ['Ultra'],
            'listed_price': [100],
            'availability_status': ['available'],
            'seller_name': ['Store A'],
        })
        is_valid, issues = validate_market_observations(df)
        assert is_valid is False
        assert any('product_id' in issue.lower() for issue in issues)
