"""Risk scoring for smartwatch pricing."""


def calculate_risk_level(
    current_margin: float,
    target_margin: float,
    inventory: int,
    supplier_lead_time_days: int,
    usd_change: float,
    competitor_median: float,
    current_price: float,
) -> str:
    """
    Calculate risk level for a product (low/medium/high/critical).
    
    Risk increases when:
    - Margin is below target
    - Inventory is very low (hard to replace)
    - USD has increased sharply (cost will rise)
    - Supplier lead time is high (slow to replenish)
    - Price gap with competitors is risky
    
    Args:
        current_margin: Current profit margin as decimal
        target_margin: Target profit margin as decimal
        inventory: Current inventory level
        supplier_lead_time_days: Days to get new stock
        usd_change: USD rate change in last 7 days
        competitor_median: Competitor median price
        current_price: Current product price
        
    Returns:
        Risk level: "low", "medium", "high", or "critical"
    """
    risk_score = 0
    
    # Margin risk
    margin_gap = target_margin - current_margin
    if margin_gap > 0.20:  # 20+ points below target
        risk_score += 40
    elif margin_gap > 0.10:  # 10-20 points below target
        risk_score += 25
    elif margin_gap > 0.05:  # 5-10 points below target
        risk_score += 10
    
    # Inventory risk
    if inventory < 10:
        risk_score += 35
    elif inventory < 25:
        risk_score += 20
    elif inventory < 50:
        risk_score += 5
    
    # Supply chain risk
    if supplier_lead_time_days > 30:
        risk_score += 20
    elif supplier_lead_time_days > 20:
        risk_score += 10
    
    # USD volatility risk
    if usd_change > 10:
        risk_score += 25
    elif usd_change > 5:
        risk_score += 15
    elif usd_change < -8:
        risk_score += 15
    
    # Competitor price gap risk
    price_gap_pct = abs(current_price - competitor_median) / competitor_median if competitor_median > 0 else 0
    if price_gap_pct > 0.25:  # 25%+ above median
        risk_score += 15
    elif price_gap_pct > 0.15:  # 15-25% above median
        risk_score += 8
    
    # Determine risk level
    if risk_score >= 100:
        return "critical"
    elif risk_score >= 65:
        return "high"
    elif risk_score >= 35:
        return "medium"
    else:
        return "low"


def get_risk_color(risk_level: str) -> str:
    """
    Get color for risk level visualization.
    
    Args:
        risk_level: Risk level string
        
    Returns:
        Color code or name
    """
    risk_colors = {
        "low": "#00CC00",
        "medium": "#FFAA00",
        "high": "#FF6600",
        "critical": "#CC0000",
    }
    return risk_colors.get(risk_level, "#666666")
