"""Unit tests for pricing engine."""

import pytest
import sys
import pandas as pd
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pricing.recommendation import recommend_price
from src.pricing.rules import calculate_current_margin, round_to_retail_price
from src.pricing.risk import calculate_risk_level
from src.data.sample_data_generator import generate_smartwatch_data


@pytest.fixture
def sample_product():
    """Create a sample product for testing (backward compatible fields for old pricing logic)."""
    return {
        "product_id": "SW001",
        "product_name": "Test Smartwatch",
        "brand": "TestBrand",
        "model": "Test",
        "category": "Premium",
        # Old schema fields (for backward compatibility with existing pricing rules)
        "current_price": 2_000_000.0,
        "cost_price": 1_000_000.0,
        "inventory": 50,
        "competitor_min_price": 1_900_000.0,
        "competitor_median_price": 2_100_000.0,
        "competitor_max_price": 2_300_000.0,
        "usd_rate": 45_000.0,
        "usd_change_7d": 2.5,
        "sales_7d": 10,
        "sales_30d": 40,
        "views_30d": 500,
        "conversion_rate": 0.08,
        "target_margin": 0.35,
        "supplier_lead_time_days": 15,
    }


class TestMarginCalculation:
    """Test margin calculation."""
    
    def test_positive_margin(self):
        """Test positive margin calculation."""
        margin = calculate_current_margin(2_000_000, 1_000_000)
        assert margin == 1.0  # 100% margin
    
    def test_zero_margin(self):
        """Test zero margin at cost price."""
        margin = calculate_current_margin(1_000_000, 1_000_000)
        assert margin == 0.0
    
    def test_negative_margin(self):
        """Test negative margin when selling below cost."""
        margin = calculate_current_margin(900_000, 1_000_000)
        assert margin < 0
    
    def test_zero_cost(self):
        """Test handling of zero cost price."""
        margin = calculate_current_margin(100, 0)
        assert margin == 0.0


class TestRetailPriceRounding:
    """Test retail price rounding."""
    
    def test_round_to_10k(self):
        """Test rounding to nearest 10,000."""
        price = round_to_retail_price(2_345_678)
        assert price == 2_350_000
    
    def test_round_down(self):
        """Test rounding down."""
        price = round_to_retail_price(2_234_999)
        assert price == 2_230_000
    
    def test_exact_multiple(self):
        """Test exact multiple of rounding unit."""
        price = round_to_retail_price(2_000_000)
        assert price == 2_000_000


class TestRiskLevelCalculation:
    """Test risk level calculation."""
    
    def test_low_risk(self):
        """Test low risk conditions."""
        risk = calculate_risk_level(
            current_margin=0.40,
            target_margin=0.30,
            inventory=100,
            supplier_lead_time_days=5,
            usd_change=-2.0,
            competitor_median=2_000_000,
            current_price=2_000_000,
        )
        assert risk == "low"
    
    def test_high_risk_low_margin(self):
        """Test high risk from low margin."""
        risk = calculate_risk_level(
            current_margin=0.05,
            target_margin=0.30,
            inventory=50,
            supplier_lead_time_days=10,
            usd_change=2.0,
            competitor_median=2_000_000,
            current_price=2_000_000,
        )
        assert risk in ["medium", "high"]
    
    def test_critical_risk_low_inventory(self):
        """Test critical risk from very low inventory."""
        risk = calculate_risk_level(
            current_margin=0.20,
            target_margin=0.30,
            inventory=5,
            supplier_lead_time_days=35,
            usd_change=12.0,
            competitor_median=2_000_000,
            current_price=2_300_000,
        )
        assert risk in ["critical", "high"]


class TestRecommendation:
    """Test pricing recommendation engine."""
    
    def test_recommend_price_returns_all_fields(self, sample_product):
        """Test that recommendation returns all required fields."""
        rec = recommend_price(sample_product)
        
        required_fields = [
            "product_id",
            "product_name",
            "brand",
            "model",
            "category",
            "current_price",
            "recommended_price",
            "action",
            "risk_level",
            "current_margin",
            "expected_margin",
            "competitor_position",
            "explanation",
            "triggered_rules",
        ]
        
        for field in required_fields:
            assert field in rec, f"Missing field: {field}"
    
    def test_recommended_price_above_minimum(self, sample_product):
        """Test that recommended price is not below minimum allowed."""
        rec = recommend_price(sample_product)
        
        min_allowed = sample_product["cost_price"] * (1 + sample_product["target_margin"] * 0.5)
        assert rec["recommended_price"] >= min_allowed * 0.99  # Allow small rounding
    
    def test_risk_level_is_valid(self, sample_product):
        """Test that risk level is one of valid values."""
        rec = recommend_price(sample_product)
        assert rec["risk_level"] in ["low", "medium", "high", "critical"]
    
    def test_action_is_valid(self, sample_product):
        """Test that action is one of valid values."""
        rec = recommend_price(sample_product)
        assert rec["action"] in ["increase_price", "decrease_price", "hold_price", "urgent_review"]
    
    def test_explanation_not_empty(self, sample_product):
        """Test that explanation is provided."""
        rec = recommend_price(sample_product)
        assert len(rec["explanation"]) > 0
    
    def test_triggered_rules_is_list(self, sample_product):
        """Test that triggered rules is a list."""
        rec = recommend_price(sample_product)
        assert isinstance(rec["triggered_rules"], list)
    
    def test_usd_shock_affects_price(self, sample_product):
        """Test that USD shock affects recommendation."""
        rec_normal = recommend_price(sample_product, usd_shock=0.0)
        rec_shock = recommend_price(sample_product, usd_shock=10.0)
        
        # With positive USD shock, price should generally increase
        assert rec_shock["recommended_price"] >= rec_normal["recommended_price"] * 0.98
    
    def test_negative_margin_handling(self):
        """Test handling of products selling below cost."""
        product = {
            "product_id": "SW_LOSS",
            "product_name": "Loss-Making Product",
            "current_price": 900_000.0,
            "cost_price": 1_000_000.0,
            "inventory": 20,
            "competitor_min_price": 950_000.0,
            "competitor_median_price": 1_000_000.0,
            "competitor_max_price": 1_100_000.0,
            "usd_rate": 45_000.0,
            "usd_change_7d": 0.0,
            "sales_7d": 5,
            "sales_30d": 20,
            "views_30d": 200,
            "conversion_rate": 0.05,
            "target_margin": 0.30,
            "supplier_lead_time_days": 10,
        }
        
        rec = recommend_price(product)
        
        # Recommended price should be higher to restore margin
        assert rec["recommended_price"] > product["current_price"]
        assert rec["action"] == "increase_price"
        assert rec["risk_level"] in ["medium", "high", "critical"]


class TestDataGeneration:
    """Test sample data generation."""
    
    def test_generate_data_creates_dataframe(self):
        """Test that data generation creates valid DataFrame."""
        df = generate_smartwatch_data(n_products=10)
        
        assert len(df) == 10
        assert len(df.columns) > 0
    
    def test_data_has_phase2_schema(self):
        """Test that generated data has Phase 2 schema columns (not old MVP schema)."""
        df = generate_smartwatch_data(n_products=5)
        
        phase2_columns = [
            "product_id", "product_name", "brand", "model", "category",
            "base_usd_price", "base_usd_price_source", "usd_rate",
            "theoretical_toman_price",
        ]
        
        for col in phase2_columns:
            assert col in df.columns, f"Missing Phase 2 column: {col}"
    
    def test_deterministic_generation(self):
        """Test that same seed produces same data."""
        df1 = generate_smartwatch_data(seed=42, n_products=10)
        df2 = generate_smartwatch_data(seed=42, n_products=10)
        
        assert df1.equals(df2)
    
    def test_different_seeds_produce_different_data(self):
        """Test that different seeds produce different data."""
        df1 = generate_smartwatch_data(seed=42, n_products=10)
        df2 = generate_smartwatch_data(seed=43, n_products=10)
        
        assert not df1.equals(df2)
    
    def test_metadata_preservation_with_complete_data(self, sample_product):
        """Test that metadata (brand, model, category) is preserved in recommendation."""
        rec = recommend_price(sample_product)
        
        assert rec["brand"] == sample_product["brand"]
        assert rec["model"] == sample_product["model"]
        assert "category" in rec
    
    def test_metadata_preservation_with_missing_fields(self):
        """Test that metadata has safe defaults when missing from input."""
        minimal_product = {
            "product_id": "TEST001",
            "product_name": "Test",
            "current_price": 1_000_000.0,
            "cost_price": 500_000.0,
            "inventory": 10,
            "competitor_min_price": 950_000.0,
            "competitor_median_price": 1_000_000.0,
            "competitor_max_price": 1_100_000.0,
            "usd_change_7d": 0.0,
            "sales_7d": 5,
            "sales_30d": 20,
            "views_30d": 100,
            "conversion_rate": 0.05,
            "target_margin": 0.25,
            "supplier_lead_time_days": 10,
            # Note: brand, model, category deliberately missing
        }
        
        rec = recommend_price(minimal_product)
        
        # Should have metadata fields with safe defaults
        assert "brand" in rec
        assert "model" in rec
        assert "category" in rec
        assert rec["brand"] == "Unknown"
        assert rec["model"] == "Unknown"
        assert rec["category"] == "Unknown"
    
    def test_recommendation_preserves_all_metadata(self):
        """Test that recommendation engine preserves all metadata through the full pipeline."""
        product = {
            "product_id": "SW_META_TEST",
            "product_name": "Metadata Test",
            "brand": "TestBrand",
            "model": "TestModel",
            "category": "Premium",
            "current_price": 2_000_000.0,
            "cost_price": 1_000_000.0,
            "inventory": 50,
            "competitor_min_price": 1_900_000.0,
            "competitor_median_price": 2_100_000.0,
            "competitor_max_price": 2_300_000.0,
            "usd_change_7d": 0.0,
            "sales_7d": 10,
            "sales_30d": 40,
            "views_30d": 500,
            "conversion_rate": 0.08,
            "target_margin": 0.35,
            "supplier_lead_time_days": 10,
        }
        
        rec = recommend_price(product)
        
        # All metadata should be preserved exactly
        assert rec["brand"] == "TestBrand"
        assert rec["model"] == "TestModel"
        assert rec["category"] == "Premium"


class TestPhase2DataModel:
    """Test Phase 2 data model and schema requirements."""
    
    def test_generate_data_has_phase2_columns(self):
        """Test that generated data includes all Phase 2 required columns."""
        df = generate_smartwatch_data(n_products=10)
        
        required_phase2_cols = [
            "product_id",
            "product_name",
            "brand",
            "model",
            "category",
            "base_usd_price",
            "base_usd_price_source",
            "usd_rate",
            "theoretical_toman_price",
            "market_min_price",
            "market_median_price",
            "market_max_price",
            "market_avg_price",
            "seller_count",
            "available_seller_count",
            "torob_min_price",
            "torob_median_price",
            "digikala_price",
            "our_current_price",
            "our_cost_price",
            "our_inventory",
            "our_sales_7d",
            "our_sales_30d",
            "our_target_margin",
            "our_strategy",
            "observed_at",
        ]
        
        for col in required_phase2_cols:
            assert col in df.columns, f"Missing Phase 2 column: {col}"
    
    def test_theoretical_toman_price_calculation(self):
        """Test that theoretical_toman_price ≈ base_usd_price * usd_rate (within rounding)."""
        df = generate_smartwatch_data(n_products=20)
        
        for idx, row in df.iterrows():
            expected = row["base_usd_price"] * row["usd_rate"]
            actual = row["theoretical_toman_price"]
            # Allow small rounding differences
            assert abs(actual - expected) < 1.0, f"Row {idx}: theoretical_toman_price mismatch"
    
    def test_market_prices_ordered_correctly(self):
        """Test that market_min_price <= market_median_price <= market_max_price."""
        df = generate_smartwatch_data(n_products=20)
        
        for idx, row in df.iterrows():
            assert row["market_min_price"] <= row["market_median_price"], \
                f"Row {idx}: market_min_price > market_median_price"
            assert row["market_median_price"] <= row["market_max_price"], \
                f"Row {idx}: market_median_price > market_max_price"
    
    def test_our_current_price_above_cost(self):
        """Test that our_current_price > our_cost_price for all products."""
        df = generate_smartwatch_data(n_products=20)
        
        for idx, row in df.iterrows():
            assert row["our_current_price"] > row["our_cost_price"], \
                f"Row {idx}: our_current_price <= our_cost_price"
    
    def test_seller_count_and_availability(self):
        """Test that available_seller_count <= seller_count."""
        df = generate_smartwatch_data(n_products=20)
        
        for idx, row in df.iterrows():
            assert row["available_seller_count"] <= row["seller_count"], \
                f"Row {idx}: available_seller_count > seller_count"
            assert row["available_seller_count"] >= 1, \
                f"Row {idx}: available_seller_count should be at least 1"
    
    def test_target_margin_in_valid_range(self):
        """Test that our_target_margin is between 0 and 1."""
        df = generate_smartwatch_data(n_products=20)
        
        for idx, row in df.iterrows():
            assert 0 <= row["our_target_margin"] <= 1, \
                f"Row {idx}: our_target_margin out of range (0-1)"
    
    def test_strategy_is_valid(self):
        """Test that our_strategy is one of the defined strategies."""
        df = generate_smartwatch_data(n_products=20)
        
        valid_strategies = [
            "Trust Builder", "Balanced", "Profit Protection", 
            "Market Penetration", "Premium Positioning", "Clearance / Cashflow"
        ]
        
        for idx, row in df.iterrows():
            assert row["our_strategy"] in valid_strategies, \
                f"Row {idx}: invalid strategy '{row['our_strategy']}'"
    
    def test_brand_affects_inventory_realistic(self):
        """Test that inventory levels are realistic for different brands."""
        df = generate_smartwatch_data(n_products=30)
        
        apple_products = df[df["brand"] == "Apple"]
        xiaomi_products = df[df["brand"] == "Xiaomi"]
        
        # Apple should have lower inventory on average
        if len(apple_products) > 0 and len(xiaomi_products) > 0:
            apple_avg_inv = apple_products["our_inventory"].mean()
            xiaomi_avg_inv = xiaomi_products["our_inventory"].mean()
            assert apple_avg_inv < xiaomi_avg_inv, \
                "Apple should have lower average inventory than Xiaomi"
    
    def test_phase2_deterministic_generation(self):
        """Test that same seed produces identical Phase 2 data."""
        df1 = generate_smartwatch_data(seed=999, n_products=10)
        df2 = generate_smartwatch_data(seed=999, n_products=10)
        
        pd.testing.assert_frame_equal(df1, df2)


class TestStrategyBasedPricing:
    """Test strategy-based pricing for Phase 2."""
    
    def test_all_strategies_return_valid_prices(self):
        """Test that all strategies return positive prices."""
        from src.pricing.strategies import calculate_strategy_prices
        
        phase2_product = {
            "our_cost_price": 2_000_000.0,
            "our_target_margin": 0.30,
            "market_min_price": 2_700_000.0,
            "market_median_price": 3_000_000.0,
            "market_max_price": 3_500_000.0,
            "torob_min_price": 2_650_000.0,
            "torob_median_price": 2_950_000.0,
            "digikala_price": 3_050_000.0,
            "theoretical_toman_price": 2_300_000.0,
            "our_inventory": 50,
            "our_sales_7d": 5,
            "our_sales_30d": 20,
        }
        
        prices = calculate_strategy_prices(phase2_product)
        
        for strategy, price in prices.items():
            assert price > 0, f"{strategy}: price should be positive"
            assert price >= 1_000_000, f"{strategy}: price seems too low"
    
    def test_no_strategy_price_below_minimum_allowed(self):
        """Test that no strategy price goes below minimum allowed threshold."""
        from src.pricing.strategies import calculate_strategy_prices, _calculate_minimum_allowed_price
        
        phase2_product = {
            "our_cost_price": 1_000_000.0,
            "our_target_margin": 0.35,
            "market_min_price": 1_400_000.0,
            "market_median_price": 1_600_000.0,
            "market_max_price": 1_800_000.0,
            "torob_min_price": 1_380_000.0,
            "torob_median_price": 1_580_000.0,
            "digikala_price": 1_620_000.0,
            "theoretical_toman_price": 1_200_000.0,
            "our_inventory": 30,
            "our_sales_7d": 3,
            "our_sales_30d": 12,
        }
        
        min_allowed = _calculate_minimum_allowed_price(
            phase2_product["our_cost_price"],
            phase2_product["our_target_margin"]
        )
        
        prices = calculate_strategy_prices(phase2_product)
        
        for strategy, price in prices.items():
            assert price >= min_allowed, \
                f"{strategy}: price {price} is below minimum allowed {min_allowed}"
    
    def test_theoretical_toman_price_included(self):
        """Test that theoretical_toman_price is included in recommendation."""
        phase2_product = {
            "product_id": "SW_PHASE2_001",
            "product_name": "Phase 2 Product",
            "brand": "TestBrand",
            "model": "TestModel",
            "category": "Premium",
            "our_current_price": 3_000_000.0,
            "our_cost_price": 2_000_000.0,
            "our_inventory": 20,
            "our_sales_7d": 2,
            "our_sales_30d": 8,
            "our_target_margin": 0.30,
            "our_strategy": "balanced",
            "base_usd_price": 200.0,
            "usd_rate": 45_000.0,
            "theoretical_toman_price": 9_000_000.0,
            "market_min_price": 2_700_000.0,
            "market_median_price": 3_000_000.0,
            "market_max_price": 3_500_000.0,
            "torob_min_price": 2_650_000.0,
            "torob_median_price": 2_950_000.0,
            "digikala_price": 3_050_000.0,
        }
        
        rec = recommend_price(phase2_product)
        
        assert "theoretical_toman_price" in rec
        assert rec["theoretical_toman_price"] is not None
        assert rec["theoretical_toman_price"] > 0
    
    def test_iran_market_premium_calculated(self):
        """Test that iran_market_premium_pct is calculated."""
        phase2_product = {
            "product_id": "SW_PHASE2_002",
            "product_name": "Phase 2 Product 2",
            "brand": "TestBrand",
            "model": "TestModel",
            "category": "Mid-Range",
            "our_current_price": 3_000_000.0,
            "our_cost_price": 2_000_000.0,
            "our_inventory": 40,
            "our_sales_7d": 5,
            "our_sales_30d": 20,
            "our_target_margin": 0.25,
            "our_strategy": "balanced",
            "base_usd_price": 100.0,
            "usd_rate": 45_000.0,
            "theoretical_toman_price": 4_500_000.0,
            "market_min_price": 5_000_000.0,
            "market_median_price": 5_500_000.0,
            "market_max_price": 6_000_000.0,
            "torob_min_price": 4_900_000.0,
            "torob_median_price": 5_400_000.0,
            "digikala_price": 5_600_000.0,
        }
        
        rec = recommend_price(phase2_product)
        
        assert "iran_market_premium_pct" in rec
        assert rec["iran_market_premium_pct"] is not None
        # Premium should be positive (market price > theoretical)
        assert rec["iran_market_premium_pct"] > 0
    
    def test_selected_strategy_maps_to_recommended_price(self):
        """Test that selected_strategy_price matches recommended_price."""
        phase2_product = {
            "product_id": "SW_PHASE2_003",
            "product_name": "Phase 2 Product 3",
            "brand": "TestBrand",
            "model": "TestModel",
            "category": "Budget",
            "our_current_price": 1_500_000.0,
            "our_cost_price": 800_000.0,
            "our_inventory": 80,
            "our_sales_7d": 10,
            "our_sales_30d": 40,
            "our_target_margin": 0.22,
            "our_strategy": "market_penetration",
            "base_usd_price": 50.0,
            "usd_rate": 45_000.0,
            "theoretical_toman_price": 2_250_000.0,
            "market_min_price": 1_300_000.0,
            "market_median_price": 1_500_000.0,
            "market_max_price": 1_700_000.0,
            "torob_min_price": 1_280_000.0,
            "torob_median_price": 1_480_000.0,
            "digikala_price": 1_520_000.0,
        }
        
        rec = recommend_price(phase2_product)
        
        assert "selected_strategy_price" in rec
        assert rec["selected_strategy_price"] == rec["recommended_price"]
    
    def test_unknown_strategy_falls_back_to_balanced(self):
        """Test that unknown strategy falls back to balanced."""
        from src.pricing.strategies import select_strategy_price
        
        phase2_product = {
            "our_cost_price": 1_000_000.0,
            "our_target_margin": 0.30,
            "market_min_price": 1_400_000.0,
            "market_median_price": 1_600_000.0,
            "market_max_price": 1_800_000.0,
            "torob_min_price": 1_380_000.0,
            "torob_median_price": 1_580_000.0,
            "digikala_price": 1_620_000.0,
            "theoretical_toman_price": 1_200_000.0,
            "our_inventory": 30,
            "our_sales_7d": 3,
            "our_sales_30d": 12,
        }
        
        result = select_strategy_price(phase2_product, strategy="unknown_strategy")
        
        # Should fallback to balanced
        assert result["strategy"] == "balanced"
    
    def test_strategy_prices_dict_contains_all_strategies(self):
        """Test that strategy_prices dict includes all valid strategies."""
        phase2_product = {
            "product_id": "SW_PHASE2_004",
            "product_name": "Phase 2 Product 4",
            "brand": "TestBrand",
            "model": "TestModel",
            "category": "Premium",
            "our_current_price": 5_000_000.0,
            "our_cost_price": 3_000_000.0,
            "our_inventory": 15,
            "our_sales_7d": 2,
            "our_sales_30d": 8,
            "our_target_margin": 0.35,
            "our_strategy": "premium_positioning",
            "base_usd_price": 300.0,
            "usd_rate": 45_000.0,
            "theoretical_toman_price": 13_500_000.0,
            "market_min_price": 15_000_000.0,
            "market_median_price": 16_000_000.0,
            "market_max_price": 17_000_000.0,
            "torob_min_price": 14_800_000.0,
            "torob_median_price": 15_800_000.0,
            "digikala_price": 16_200_000.0,
        }
        
        rec = recommend_price(phase2_product)
        
        assert "strategy_prices" in rec
        expected_strategies = {
            "trust_builder",
            "balanced",
            "profit_protection",
            "market_penetration",
            "premium_positioning",
            "clearance_cashflow",
        }
        for strategy in expected_strategies:
            assert strategy in rec["strategy_prices"], f"Missing strategy: {strategy}"
            assert rec["strategy_prices"][strategy] > 0, f"{strategy} price should be positive"
    
    def test_trust_builder_close_to_market_min(self):
        """Test that trust_builder strategy prices near market minimum."""
        from src.pricing.strategies import calculate_strategy_prices
        
        phase2_product = {
            "our_cost_price": 1_000_000.0,
            "our_target_margin": 0.25,
            "market_min_price": 1_400_000.0,
            "market_median_price": 1_600_000.0,
            "market_max_price": 1_800_000.0,
            "torob_min_price": 1_380_000.0,
            "torob_median_price": 1_580_000.0,
            "digikala_price": 1_620_000.0,
            "theoretical_toman_price": 1_200_000.0,
            "our_inventory": 60,
            "our_sales_7d": 4,
            "our_sales_30d": 16,
        }
        
        prices = calculate_strategy_prices(phase2_product)
        
        # Trust builder should be lowest (or tied with market penetration)
        trust_builder = prices["trust_builder"]
        balanced = prices["balanced"]
        profit_protection = prices["profit_protection"]
        
        # Trust builder should be below or equal to balanced
        assert trust_builder <= balanced, "trust_builder should be <= balanced"
        # Trust builder should be below profit_protection
        assert trust_builder < profit_protection, "trust_builder should be < profit_protection"
    
    def test_premium_positioning_above_market_median(self):
        """Test that premium_positioning strategy prices above market median."""
        from src.pricing.strategies import calculate_strategy_prices
        
        phase2_product = {
            "our_cost_price": 1_000_000.0,
            "our_target_margin": 0.35,
            "market_min_price": 1_400_000.0,
            "market_median_price": 1_600_000.0,
            "market_max_price": 1_800_000.0,
            "torob_min_price": 1_380_000.0,
            "torob_median_price": 1_580_000.0,
            "digikala_price": 1_620_000.0,
            "theoretical_toman_price": 1_200_000.0,
            "our_inventory": 10,
            "our_sales_7d": 1,
            "our_sales_30d": 4,
        }
        
        prices = calculate_strategy_prices(phase2_product)
        
        premium = prices["premium_positioning"]
        market_median = phase2_product["market_median_price"]
        market_max = phase2_product["market_max_price"]
        
        # Premium positioning should be above median
        assert premium > market_median * 1.05, "premium_positioning should be > median * 1.05"
        # But should not exceed market max significantly
        assert premium <= market_max * 1.10, "premium_positioning should not exceed market_max * 1.10"
    
    def test_clearance_discounted_with_high_inventory(self):
        """Test that clearance strategy applies discounts with high inventory."""
        from src.pricing.strategies import calculate_strategy_prices
        
        high_inventory = {
            "our_cost_price": 1_000_000.0,
            "our_target_margin": 0.25,
            "market_min_price": 1_400_000.0,
            "market_median_price": 1_600_000.0,
            "market_max_price": 1_800_000.0,
            "torob_min_price": 1_380_000.0,
            "torob_median_price": 1_580_000.0,
            "digikala_price": 1_620_000.0,
            "theoretical_toman_price": 1_200_000.0,
            "our_inventory": 150,  # High inventory
            "our_sales_7d": 2,  # Weak sales
            "our_sales_30d": 8,
        }
        
        low_inventory = {
            **high_inventory,
            "our_inventory": 10,  # Low inventory
            "our_sales_7d": 5,  # Decent sales
        }
        
        prices_high = calculate_strategy_prices(high_inventory)
        prices_low = calculate_strategy_prices(low_inventory)
        
        # Clearance with high inventory should be lower than with low inventory
        assert prices_high["clearance_cashflow"] < prices_low["clearance_cashflow"], \
            "clearance_cashflow should be lower with high inventory"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
