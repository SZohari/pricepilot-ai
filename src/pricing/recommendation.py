"""Main recommendation engine for pricing decisions."""

from typing import Dict, List
from src.pricing.rules import calculate_current_margin, apply_pricing_rules, determine_action
from src.pricing.risk import calculate_risk_level
from src.pricing.strategies import (
    select_strategy_price,
    _calculate_iran_market_premium,
)


def recommend_price(row: dict, usd_shock: float = 0.0, strategy: str = None) -> dict:
    """
    Generate a pricing recommendation for a product.
    
    Supports both MVP (old) and Phase 2 (new) schema fields.
    MVP fields: current_price, cost_price, competitor_median_price, etc.
    Phase 2 fields: our_current_price, our_cost_price, market_median_price, our_strategy, etc.
    
    Args:
        row: Product data dictionary with required fields
        usd_shock: Additional USD rate change for simulation (in percentage)
        strategy: (Optional) Override the product's our_strategy with this value for Phase 2 data
        
    Returns:
        Dictionary with recommendation details including strategy-based pricing (if Phase 2)
    """
    # Determine if this is Phase 2 data (has our_current_price) or MVP data (has current_price)
    is_phase2 = "our_current_price" in row
    
    # Extract product metadata
    product_id = row.get("product_id", "UNKNOWN")
    product_name = row.get("product_name", "Unknown Product")
    brand = row.get("brand", "Unknown")
    model = row.get("model", "Unknown")
    category = row.get("category", "Unknown")
    
    if is_phase2:
        # Phase 2: Use new schema fields
        our_current_price = row.get("our_current_price", 0.0)
        our_cost_price = row.get("our_cost_price", 0.0)
        our_inventory = row.get("our_inventory", 0)
        our_target_margin = row.get("our_target_margin", 0.25)
        # Use provided strategy override, fallback to row's strategy, default to "balanced"
        our_strategy = strategy if strategy is not None else row.get("our_strategy", "balanced")
        
        market_median = row.get("market_median_price", our_current_price)
        market_min = row.get("market_min_price", our_current_price * 0.95)
        market_max = row.get("market_max_price", our_current_price * 1.05)
        
        # For backward compatibility, also set MVP field names if not present
        current_price = our_current_price
        cost_price = our_cost_price
        inventory = our_inventory
        target_margin = our_target_margin
        competitor_median = market_median
        competitor_min = market_min
        competitor_max = market_max
        
        # Phase 2 specific fields
        theoretical_toman = row.get("theoretical_toman_price", 0.0)
        iran_premium = _calculate_iran_market_premium(market_median, theoretical_toman)
        
        # Calculate strategy-based prices
        strategy_result = select_strategy_price(row, our_strategy)
        recommended_price = strategy_result["selected_strategy_price"]
        strategy_prices = strategy_result["strategy_prices"]
        strategy_explanation = strategy_result["strategy_explanation"]
        
    else:
        # MVP: Use old schema fields
        current_price = row.get("current_price", 0.0)
        cost_price = row.get("cost_price", 0.0)
        inventory = row.get("inventory", 0)
        target_margin = row.get("target_margin", 0.25)
        competitor_median = row.get("competitor_median_price", current_price)
        competitor_min = row.get("competitor_min_price", current_price * 0.95)
        competitor_max = row.get("competitor_max_price", current_price * 1.05)
        
        # Phase 2 fields set to None for MVP
        theoretical_toman = None
        iran_premium = None
        strategy_prices = None
        strategy_explanation = None
        our_strategy = None
    
    # Optional fields (both schemas)
    usd_change = row.get("usd_change_7d", 0.0)
    supplier_lead_time = row.get("supplier_lead_time_days", 10)
    
    # If Phase 2 but no strategy-based pricing yet, use MVP rules as fallback
    if not is_phase2 or recommended_price is None:
        recommended_price, triggered_rules = apply_pricing_rules(row, usd_shock)
    else:
        triggered_rules = []
    
    # Calculate margins
    current_margin = calculate_current_margin(current_price, cost_price)
    expected_margin = calculate_current_margin(recommended_price, cost_price)
    
    # Calculate risk level
    total_usd_change = usd_change + usd_shock
    risk_level = calculate_risk_level(
        current_margin=current_margin,
        target_margin=target_margin,
        inventory=inventory,
        supplier_lead_time_days=supplier_lead_time,
        usd_change=total_usd_change,
        competitor_median=competitor_median,
        current_price=current_price,
    )
    
    # Determine action
    action = determine_action(current_price, recommended_price, risk_level)
    
    # Determine competitor position
    if current_price < competitor_min:
        competitor_position = "Below minimum (aggressive)"
    elif current_price < competitor_median * 0.90:
        competitor_position = "Well below median (very competitive)"
    elif current_price < competitor_median:
        competitor_position = "Below median (competitive)"
    elif current_price < competitor_median * 1.10:
        competitor_position = "Near median (market rate)"
    elif current_price < competitor_max:
        competitor_position = "Above median (premium)"
    else:
        competitor_position = "Above maximum (aggressive premium)"
    
    # Build explanation
    if strategy_explanation is None:
        # MVP: Use old explanation logic
        explanation = _build_explanation(
            action=action,
            current_price=current_price,
            recommended_price=recommended_price,
            current_margin=current_margin,
            target_margin=target_margin,
            expected_margin=expected_margin,
            inventory=inventory,
            competitor_median=competitor_median,
            usd_change=total_usd_change,
            triggered_rules=triggered_rules,
            risk_level=risk_level,
        )
    else:
        # Phase 2: Use strategy explanation
        explanation = strategy_explanation
    
    # Build recommendation result
    result = {
        "product_id": product_id,
        "product_name": product_name,
        "brand": brand,
        "model": model,
        "category": category,
        "current_price": float(current_price),
        "recommended_price": float(recommended_price),
        "action": action,
        "risk_level": risk_level,
        "current_margin": float(current_margin),
        "expected_margin": float(expected_margin),
        "competitor_position": competitor_position,
        "explanation": explanation,
        "triggered_rules": triggered_rules,
    }
    
    # Add Phase 2 fields if applicable
    if is_phase2:
        result["theoretical_toman_price"] = float(theoretical_toman) if theoretical_toman else None
        result["iran_market_premium_pct"] = float(iran_premium) if iran_premium is not None else None
        result["strategy_prices"] = strategy_prices
        result["selected_strategy"] = our_strategy
        result["selected_strategy_price"] = float(recommended_price)
    
    # Add common fields
    result["competitor_position"] = competitor_position
    result["explanation"] = explanation
    result["triggered_rules"] = triggered_rules
    
    return result


def _build_explanation(
    action: str,
    current_price: float,
    recommended_price: float,
    current_margin: float,
    target_margin: float,
    expected_margin: float,
    inventory: int,
    competitor_median: float,
    usd_change: float,
    triggered_rules: List[str],
    risk_level: str,
) -> str:
    """
    Build human-readable explanation for the recommendation.
    
    Args:
        action: Recommended action
        current_price: Current selling price
        recommended_price: Recommended selling price
        current_margin: Current profit margin
        target_margin: Target profit margin
        expected_margin: Expected margin after recommendation
        inventory: Current inventory level
        competitor_median: Competitor median price
        usd_change: USD rate change
        triggered_rules: List of triggered rules
        risk_level: Product risk level
        
    Returns:
        Human-readable explanation string
    """
    price_change_pct = (recommended_price - current_price) / current_price * 100 if current_price > 0 else 0
    margin_diff = (expected_margin - current_margin) * 100
    
    lines = []
    lines.append(f"**Action: {action.replace('_', ' ').title()}**")
    
    if action == "increase_price":
        lines.append(
            f"Recommend increasing price from {current_price:,.0f} to {recommended_price:,.0f} "
            f"({price_change_pct:+.1f}%)."
        )
    elif action == "decrease_price":
        lines.append(
            f"Recommend decreasing price from {current_price:,.0f} to {recommended_price:,.0f} "
            f"({price_change_pct:+.1f}%)."
        )
    elif action == "hold_price":
        lines.append(f"Hold current price at {current_price:,.0f}.")
    elif action == "urgent_review":
        lines.append(f"⚠ Urgent review required. Product is at {risk_level.upper()} risk.")
    
    # Margin explanation
    if current_margin < target_margin:
        lines.append(
            f"Current margin ({current_margin:.1%}) is below target ({target_margin:.1%}). "
            f"Recommendation brings margin to {expected_margin:.1%} ({margin_diff:+.1f} points)."
        )
    
    # Competitor context
    price_vs_median_pct = (current_price - competitor_median) / competitor_median * 100 if competitor_median > 0 else 0
    if price_vs_median_pct > 5:
        lines.append(f"Currently {price_vs_median_pct:.1f}% above competitor median price.")
    elif price_vs_median_pct < -5:
        lines.append(f"Currently {abs(price_vs_median_pct):.1f}% below competitor median price.")
    
    # Inventory context
    if inventory < 15:
        lines.append(f"Low inventory ({inventory} units) - premium pricing justified.")
    elif inventory > 100:
        lines.append(f"High inventory ({inventory} units) - consider price reduction to move stock.")
    
    # USD context
    if abs(usd_change) > 2:
        direction = "increased" if usd_change > 0 else "decreased"
        lines.append(f"USD rate has {direction} by {abs(usd_change):.1f}% - affecting cost structure.")
    
    # Triggered rules
    if triggered_rules:
        rule_descriptions = {
            "margin_below_target": "Margin below target",
            "price_too_high_vs_competitors": "Price too high vs competitors",
            "high_inventory_low_sales": "High inventory + low sales",
            "usd_rate_increase": "USD rate increased",
            "usd_rate_decrease": "USD rate decreased",
            "low_inventory_premium": "Low inventory justifies premium",
            "low_conversion_rate": "Low conversion rate suggests price resistance",
        }
        rules_text = ", ".join([rule_descriptions.get(r, r) for r in triggered_rules])
        lines.append(f"**Triggered rules:** {rules_text}")
    
    return "\n".join(lines)
