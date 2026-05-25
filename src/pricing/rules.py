"""Pricing rules engine for smartwatch recommendations."""

from typing import List, Tuple


def calculate_current_margin(current_price: float, cost_price: float) -> float:
    """
    Calculate current profit margin.
    
    Args:
        current_price: Current selling price
        cost_price: Product cost price
        
    Returns:
        Margin as decimal (e.g., 0.35 for 35%)
    """
    if cost_price <= 0:
        return 0.0
    return (current_price - cost_price) / cost_price


def round_to_retail_price(price: float, round_to: int = 10_000) -> float:
    """
    Round price to clean Iranian retail value.
    
    Args:
        price: Price to round
        round_to: Rounding increment (default: 10,000 toman)
        
    Returns:
        Rounded price
    """
    return round(price / round_to) * round_to


def apply_pricing_rules(row: dict, usd_shock: float = 0.0) -> Tuple[float, List[str]]:
    """
    Apply pricing rules to recommend a new price.
    
    Rules:
    1. Margin Rule: If margin below target, increase to match target
    2. Competitor Rule: If price is too far above median, bring it closer
    3. Inventory Rule: If inventory is high and sales are slow, decrease price
    4. USD Shock Rule: If USD has risen, increase price proportionally
    5. Low Inventory Rule: If inventory is critically low, hold or increase
    6. Conversion Rule: If conversion rate is low, consider small decrease
    
    Args:
        row: Product data dict
        usd_shock: Additional USD rate change in percentage (for simulation)
        
    Returns:
        (recommended_price, triggered_rules)
    """
    current_price = row["current_price"]
    cost_price = row["cost_price"]
    current_margin = calculate_current_margin(current_price, cost_price)
    target_margin = row["target_margin"]
    inventory = row["inventory"]
    competitor_median = row["competitor_median_price"]
    competitor_min = row["competitor_min_price"]
    competitor_max = row["competitor_max_price"]
    usd_change = row["usd_change_7d"]
    sales_7d = row["sales_7d"]
    sales_30d = row["sales_30d"]
    conversion_rate = row["conversion_rate"]
    
    recommended_price = current_price
    triggered_rules = []
    
    # Rule 1: Margin Rule
    min_required_price = cost_price * (1 + target_margin * 0.5)
    if current_margin < target_margin:
        target_price = cost_price * (1 + target_margin)
        recommended_price = max(recommended_price, target_price)
        triggered_rules.append("margin_below_target")
    
    # Rule 2: Competitor Rule - Price too high above median
    if current_price > competitor_median * 1.15:
        # Bring closer to median but don't drop too much
        recommended_price = min(recommended_price, competitor_median * 1.10)
        triggered_rules.append("price_too_high_vs_competitors")
    
    # Rule 3: Inventory Rule - High inventory + low sales
    if inventory > 100 and sales_7d < 5:
        # Decrease price to move inventory
        recommended_price *= 0.93  # 7% reduction
        triggered_rules.append("high_inventory_low_sales")
    
    # Rule 4: USD Shock Rule
    total_usd_change = usd_change + usd_shock
    if total_usd_change > 3:  # USD has increased significantly
        shock_multiplier = 1 + (total_usd_change / 100) * 0.5  # 50% of USD increase flows to price
        recommended_price *= shock_multiplier
        triggered_rules.append("usd_rate_increase")
    elif total_usd_change < -5:  # USD has decreased
        shock_multiplier = 1 + (total_usd_change / 100) * 0.3
        recommended_price *= shock_multiplier
        triggered_rules.append("usd_rate_decrease")
    
    # Rule 5: Low Inventory Rule
    if inventory < 15:
        recommended_price *= 1.05  # 5% increase to be selective
        triggered_rules.append("low_inventory_premium")
    
    # Rule 6: Conversion Rule
    if conversion_rate < 0.03:  # Very low conversion
        recommended_price *= 0.97  # 3% reduction
        triggered_rules.append("low_conversion_rate")
    
    # Ensure minimum price is maintained
    recommended_price = max(recommended_price, min_required_price)
    
    # Round to clean retail price
    recommended_price = round_to_retail_price(recommended_price)
    
    return recommended_price, triggered_rules


def determine_action(current_price: float, recommended_price: float, risk_level: str) -> str:
    """
    Determine action based on price change and risk level.
    
    Args:
        current_price: Current selling price
        recommended_price: Recommended selling price
        risk_level: Risk level (low/medium/high/critical)
        
    Returns:
        Action string: increase_price, decrease_price, hold_price, or urgent_review
    """
    price_change_pct = (recommended_price - current_price) / current_price if current_price > 0 else 0
    
    # Critical risk always gets urgent review
    if risk_level == "critical":
        return "urgent_review"
    
    # Small changes (< 2%) are holds
    if abs(price_change_pct) < 0.02:
        return "hold_price"
    
    if price_change_pct > 0.02:
        return "increase_price"
    else:
        return "decrease_price"
