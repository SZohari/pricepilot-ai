"""Tests for formatting utilities."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.formatting import (
    format_toman,
    format_percent,
    format_margin,
    format_action_label,
    format_risk_label,
    format_price_comparison,
    get_risk_color,
    get_action_color,
    parse_price_input,
    format_price_input_value,
    format_price_preview,
    format_million_toman,
    format_rial_equivalent,
    humanize_label,
)


class TestFormatToman:
    """Test Toman formatting."""
    
    def test_format_basic(self):
        """Test basic Toman formatting."""
        result = format_toman(7800000)
        assert "7" in result and "تومان" in result
    
    def test_format_with_separators(self):
        """Test that large numbers have separators."""
        result = format_toman(7800000)
        assert "," in result
        assert "7,800,000" in result
    
    def test_format_compact_millions(self):
        """Test compact format for millions."""
        result = format_toman(7800000, compact=True)
        assert "میلیون" in result
        assert "7.8" in result
    
    def test_format_zero(self):
        """Test formatting zero."""
        result = format_toman(0)
        assert "0" in result and "تومان" in result
    
    def test_format_small_number(self):
        """Test small number formatting."""
        result = format_toman(500)
        assert "500" in result and "تومان" in result


class TestFormatPercent:
    """Test percentage formatting."""
    
    def test_basic_percent(self):
        """Test basic percentage formatting."""
        result = format_percent(0.35)
        assert "35" in result and "%" in result
    
    def test_decimal_places(self):
        """Test decimal place control."""
        result = format_percent(0.0534, decimals=2)
        assert "5.34" in result
    
    def test_single_decimal(self):
        """Test single decimal place."""
        result = format_percent(0.12345, decimals=1)
        assert "12.3" in result


class TestFormatMargin:
    """Test margin formatting."""
    
    def test_positive_margin(self):
        """Test positive margin with plus sign."""
        result = format_margin(0.35)
        assert "+" in result and "35" in result
    
    def test_negative_margin(self):
        """Test negative margin."""
        result = format_margin(-0.05)
        assert "-" in result and "5" in result
    
    def test_zero_margin(self):
        """Test zero margin."""
        result = format_margin(0.0)
        assert "0" in result


class TestFormatActionLabel:
    """Test action label formatting."""
    
    def test_increase_price(self):
        """Test increase price label."""
        result = format_action_label("increase_price")
        assert "Increase" in result and "📈" in result
    
    def test_decrease_price(self):
        """Test decrease price label."""
        result = format_action_label("decrease_price")
        assert "Decrease" in result and "📉" in result
    
    def test_hold_price(self):
        """Test hold price label."""
        result = format_action_label("hold_price")
        assert "Hold" in result
    
    def test_urgent_review(self):
        """Test urgent review label."""
        result = format_action_label("urgent_review")
        assert "Urgent" in result


class TestFormatRiskLabel:
    """Test risk level formatting."""
    
    def test_low_risk(self):
        """Test low risk label."""
        result = format_risk_label("low")
        assert "Low" in result and "✅" in result
    
    def test_critical_risk(self):
        """Test critical risk label."""
        result = format_risk_label("critical")
        assert "Critical" in result and "🔴" in result or "🚨" in result
    
    def test_medium_risk(self):
        """Test medium risk label."""
        result = format_risk_label("medium")
        assert "Medium" in result


class TestFormatPriceComparison:
    """Test price comparison formatting."""
    
    def test_price_increase(self):
        """Test price increase comparison."""
        result = format_price_comparison(2000000, 2200000)
        assert "→" in result
        assert "تومان" in result
    
    def test_price_comparison_contains_both_prices(self):
        """Test that comparison contains both prices."""
        result = format_price_comparison(1000000, 1200000)
        assert "1,000,000" in result
        assert "1,200,000" in result


class TestParsePriceInput:
    """Test parsing of numeric price strings."""

    def test_parse_price_input_english_digits(self):
        result = parse_price_input("370000000")
        assert result == 370000000

    def test_parse_price_input_with_commas(self):
        result = parse_price_input("370,000,000")
        assert result == 370000000

    def test_parse_price_input_with_spaces(self):
        result = parse_price_input(" 38 000 000 ")
        assert result == 38000000

    def test_parse_price_input_persian_digits(self):
        result = parse_price_input("۱۲۵۰۰۰۰۰")
        assert result == 12500000

    def test_parse_price_input_persian_digits_with_commas(self):
        result = parse_price_input("۳۷۰,۰۰۰,۰۰۰")
        assert result == 370000000

    def test_parse_price_input_persian_comma(self):
        result = parse_price_input("۳۷۰،۰۰۰،۰۰۰")
        assert result == 370000000

    def test_parse_price_input_arabic_digits(self):
        result = parse_price_input("١٢٥٠٠٠٠٠")
        assert result == 12500000

    def test_parse_price_input_invalid(self):
        result = parse_price_input("invalid")
        assert result is None


class TestFormatPricePreview:
    """Test compact price preview formatting."""

    def test_format_price_preview_numeric(self):
        result = format_price_preview(370000000)
        assert "370,000,000 تومان" in result
        assert "370 میلیون تومان" in result
        assert "معادل 3,700,000,000 ریال" in result

    def test_format_price_preview_invalid_returns_empty(self):
        result = format_price_preview("invalid")
        assert result == ""


class TestFormatPriceInputValue:
    """Test normalized text input formatting."""

    def test_numeric_value(self):
        assert format_price_input_value(370000000) == "370,000,000"

    def test_english_string_value(self):
        assert format_price_input_value("370000000") == "370,000,000"

    def test_persian_string_value(self):
        assert format_price_input_value("۳۷۰۰۰۰۰۰۰") == "370,000,000"

    def test_empty_or_invalid_value(self):
        assert format_price_input_value("") == ""
        assert format_price_input_value("invalid") == ""


class TestFormatMillionToman:
    """Test full and compact million formatting."""

    def test_format_million_toman(self):
        result = format_million_toman(12500000)
        assert "12,500,000 تومان" in result
        assert "12.5 میلیون تومان" in result


class TestFormatRialEquivalent:
    """Test toman-to-rial display formatting."""

    def test_format_rial_equivalent(self):
        assert format_rial_equivalent(370000000) == "معادل 3,700,000,000 ریال"


class TestHumanizeLabel:
    """Test conversion from snake_case to readable labels."""

    def test_humanize_strategy_label(self):
        assert humanize_label("trust_builder") == "Trust Builder"
        assert humanize_label("profit_protection") == "Profit Protection"
        assert humanize_label("clearance_cashflow") == "Clearance / Cashflow"

    def test_humanize_action_label(self):
        assert humanize_label("increase_price") == "Increase Price"
        assert humanize_label("decrease_price") == "Decrease Price"
        assert humanize_label("urgent_review") == "Urgent Review"
        assert humanize_label("available") == "Available"
        assert humanize_label("low_stock") == "Low Stock"
        assert humanize_label("unavailable") == "Unavailable"


class TestColorFunctions:
    """Test color utility functions."""
    
    def test_risk_color_low(self):
        """Test low risk color."""
        color = get_risk_color("low")
        assert "#" in color
    
    def test_action_color_increase(self):
        """Test increase action color."""
        color = get_action_color("increase_price")
        assert "#" in color
    
    def test_invalid_risk_returns_default(self):
        """Test that invalid risk returns default color."""
        color = get_risk_color("invalid")
        assert "#" in color


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
