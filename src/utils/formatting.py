"""Formatting utilities for readable display of prices and metrics."""

from typing import Optional


def format_toman(value: float, compact: bool = False) -> str:
    """
    Format a number as Iranian Toman with readable separators.
    
    Args:
        value: Numeric value to format
        compact: If True, use compact format (e.g., "7.8 میلیون تومان")
        
    Returns:
        Formatted string with separators and تومان suffix
        
    Examples:
        format_toman(7800000) -> "7,800,000 تومان"
        format_toman(7800000, compact=True) -> "7.8 میلیون تومان"
    """
    if not isinstance(value, (int, float)):
        return "0 تومان"
    
    value = int(value)
    
    if compact:
        if abs(value) >= 1_000_000:
            millions = value / 1_000_000
            return f"{millions:.1f} میلیون تومان"
        elif abs(value) >= 1_000:
            thousands = value / 1_000
            return f"{thousands:.0f} هزار تومان"
    
    # Standard format with separators
    formatted = f"{value:,}".replace(",", ",")
    return f"{formatted} تومان"


def parse_price_input(value) -> Optional[int]:
    """
    Parse a user-entered price string into an integer toman amount.

    Accepts English, Persian, and Arabic digits, commas, Persian comma, and spaces.

    Args:
        value: Numeric or string price input.

    Returns:
        Parsed integer toman value, or None if input is empty or invalid.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            parsed = int(float(value))
            return parsed
        except (ValueError, TypeError):
            return None

    raw_value = str(value).strip()
    if raw_value == "":
        return None

    digit_map = {
        "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
        "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
        "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
        "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
        "،": ",", "٬": ",", "\u200f": "", "\u200e": "", "\u202f": "",
    }
    normalized = raw_value.translate(str.maketrans(digit_map))
    normalized = normalized.replace(",", "").replace(" ", "")

    if normalized == "":
        return None

    try:
        if "." in normalized:
            parsed = float(normalized)
            return int(parsed)
        return int(normalized)
    except (ValueError, TypeError):
        return None


def format_million_toman(value) -> str:
    """
    Format a toman amount with both full and compact million display.

    Args:
        value: Numeric toman amount.

    Returns:
        String like "12,500,000 تومان | 12.5 میلیون تومان".
    """
    if not isinstance(value, (int, float)):
        return "0 تومان"

    value_int = int(value)
    if value_int <= 0:
        return "0 تومان"

    return f"{format_toman(value_int)} | {format_toman(value_int, compact=True)}"


def format_price_preview(value) -> str:
    """
    Create a compact price preview string for display next to inputs.

    Args:
        value: Numeric or string price input.

    Returns:
        Compact formatted price string or empty string when no valid value is available.
    """
    parsed = parse_price_input(value)
    if parsed is None or parsed <= 0:
        return ""
    return format_million_toman(parsed)


def humanize_label(value: str) -> str:
    """
    Convert a snake_case label into a readable title label.

    Args:
        value: Snake_case string.

    Returns:
        Human-readable label.
    """
    if not value or not isinstance(value, str):
        return ""

    label_map = {
        "trust_builder": "Trust Builder",
        "profit_protection": "Profit Protection",
        "market_penetration": "Market Penetration",
        "premium_positioning": "Premium Positioning",
        "clearance_cashflow": "Clearance / Cashflow",
        "increase_price": "Increase Price",
        "decrease_price": "Decrease Price",
        "hold_price": "Hold Price",
        "urgent_review": "Urgent Review",
        "low_stock": "Low Stock",
        "available": "Available",
        "unavailable": "Unavailable",
    }
    return label_map.get(value, value.replace("_", " ").title())


def format_percent(value: float, decimals: int = 1) -> str:
    """
    Create a compact price preview string for display next to inputs.

    Args:
        value: Numeric or string price input.

    Returns:
        Compact formatted price string or empty string when no valid value is available.
    """
    parsed = parse_price_input(value)
    if parsed is None or parsed <= 0:
        return ""
    return format_toman(parsed, compact=True)


def format_percent(value: float, decimals: int = 1) -> str:
    """
    Format a decimal as a percentage.
    
    Args:
        value: Decimal value (e.g., 0.35 for 35%)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
        
    Examples:
        format_percent(0.35) -> "35.0%"
        format_percent(0.0534, 2) -> "5.34%"
    """
    if not isinstance(value, (int, float)):
        return "0%"
    
    return f"{value * 100:.{decimals}f}%"


def format_margin(value: float) -> str:
    """
    Format margin as a percentage with sign.
    
    Args:
        value: Margin as decimal (e.g., 0.35 for 35% margin)
        
    Returns:
        Formatted margin string
        
    Examples:
        format_margin(0.35) -> "+35.0%"
        format_margin(-0.05) -> "-5.0%"
    """
    if not isinstance(value, (int, float)):
        return "0%"
    
    pct = value * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


def format_action_label(action: str) -> str:
    """
    Format action string to readable label with emoji.
    
    Args:
        action: Action string (increase_price, decrease_price, hold_price, urgent_review)
        
    Returns:
        Formatted label with emoji
        
    Examples:
        format_action_label("increase_price") -> "📈 Increase Price"
        format_action_label("urgent_review") -> "⚠️ Urgent Review"
    """
    action_map = {
        "increase_price": "📈 Increase Price",
        "decrease_price": "📉 Decrease Price",
        "hold_price": "➡️ Hold Price",
        "urgent_review": "⚠️ Urgent Review",
    }
    return action_map.get(action, action.replace("_", " ").title())


def format_risk_label(risk_level: str) -> str:
    """
    Format risk level to readable label with emoji.
    
    Args:
        risk_level: Risk level (low, medium, high, critical)
        
    Returns:
        Formatted label with emoji
        
    Examples:
        format_risk_label("low") -> "✅ Low Risk"
        format_risk_label("critical") -> "🔴 Critical Risk"
    """
    risk_map = {
        "low": "✅ Low Risk",
        "medium": "⚠️ Medium Risk",
        "high": "🔴 High Risk",
        "critical": "🚨 Critical Risk",
    }
    return risk_map.get(risk_level, risk_level.title())


def format_price_comparison(current: float, recommended: float) -> str:
    """
    Format a price comparison arrow.
    
    Args:
        current: Current price
        recommended: Recommended price
        
    Returns:
        Formatted comparison string
        
    Examples:
        format_price_comparison(2000000, 2200000) -> "2,000,000 تومان → 2,200,000 تومان"
    """
    current_str = format_toman(current)
    recommended_str = format_toman(recommended)
    return f"{current_str} → {recommended_str}"


def get_risk_color(risk_level: str) -> str:
    """
    Get RGB color for risk level.
    
    Args:
        risk_level: Risk level (low, medium, high, critical)
        
    Returns:
        RGB color code
    """
    colors = {
        "low": "#00CC00",
        "medium": "#FFAA00",
        "high": "#FF6600",
        "critical": "#CC0000",
    }
    return colors.get(risk_level, "#666666")


def get_action_color(action: str) -> str:
    """
    Get RGB color for action.
    
    Args:
        action: Action string
        
    Returns:
        RGB color code
    """
    colors = {
        "increase_price": "#90EE90",
        "decrease_price": "#FFB6C1",
        "hold_price": "#FFFFCC",
        "urgent_review": "#FF6347",
    }
    return colors.get(action, "#CCCCCC")

def humanize_label(value: object) -> str:
    """Convert internal snake_case labels into user-friendly display labels.

    This only affects UI display. It must not change stored/internal values.
    """
    if value is None:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    explicit_labels = {
        "trust_builder": "Trust Builder",
        "balanced": "Balanced",
        "profit_protection": "Profit Protection",
        "market_penetration": "Market Penetration",
        "premium_positioning": "Premium Positioning",
        "clearance_cashflow": "Clearance / Cashflow",
        "increase_price": "Increase Price",
        "decrease_price": "Decrease Price",
        "hold_price": "Hold Price",
        "urgent_review": "Urgent Review",
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "critical": "Critical",
        "available": "Available",
        "low_stock": "Low Stock",
        "limited": "Limited",
        "unavailable": "Unavailable",
        "manual": "Manual",
        "nobitex_usdt_proxy": "Nobitex USDT Proxy",
        "navasan": "Navasan",
        "tgju": "TGJU",
        "bonbast": "Bonbast",
    }

    if text in explicit_labels:
        return explicit_labels[text]

    return text.replace("_", " ").replace("-", " ").title()
def humanize_label(value: object) -> str:
    """Convert internal snake_case labels into clean user-facing labels."""
    if value is None:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    explicit_labels = {
        "trust_builder": "Trust Builder",
        "balanced": "Balanced",
        "profit_protection": "Profit Protection",
        "market_penetration": "Market Penetration",
        "premium_positioning": "Premium Positioning",
        "clearance_cashflow": "Clearance / Cashflow",
        "increase_price": "Increase Price",
        "decrease_price": "Decrease Price",
        "hold_price": "Hold Price",
        "urgent_review": "Urgent Review",
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "critical": "Critical",
        "available": "Available",
        "low_stock": "Low Stock",
        "limited": "Limited",
        "unavailable": "Unavailable",
        "manual": "Manual",
        "nobitex_usdt_proxy": "Nobitex USDT Proxy",
        "navasan": "Navasan",
        "tgju": "TGJU",
        "bonbast": "Bonbast",
    }

    if text in explicit_labels:
        return explicit_labels[text]

    return text.replace("_", " ").replace("-", " ").title()
