"""Formatting utilities for readable display of prices and metrics."""


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
