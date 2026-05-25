"""Unit tests for pricing engine."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pricing.recommendation import recommend_price
from src.pricing.rules import calculate_current_margin, round_to_retail_price
from src.pricing.risk import calculate_risk_level
from src.data.sample_data_generator import generate_smartwatch_data


@pytest.fixture
def sample_product():
    """Create a sample product for testing."""
    return {
        "product_id": "SW001",
        "product_name": "Test Smartwatch",
        "brand": "TestBrand",
        "model": "Test",
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
    
    def test_data_has_required_columns(self):
        """Test that generated data has required columns."""
        df = generate_smartwatch_data(n_products=5)
        
        required_columns = [
            "product_id",
            "product_name",
            "current_price",
            "cost_price",
            "inventory",
            "competitor_median_price",
            "usd_change_7d",
            "target_margin",
        ]
        
        for col in required_columns:
            assert col in df.columns
    
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
