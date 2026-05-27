"""Strategy-based pricing for Phase 2 (market-aware retailer pricing)."""

import math
from typing import Dict
from src.pricing.rules import round_to_retail_price, calculate_current_margin


# Defined pricing strategies
VALID_STRATEGIES = [
    "trust_builder",
    "balanced",
    "profit_protection",
    "market_penetration",
    "premium_positioning",
    "clearance_cashflow",
]

STRATEGY_DESCRIPTIONS = {
    "trust_builder": "Price at/below market minimum to build customer trust and drive volume",
    "balanced": "Price near market median, balancing margin and competitiveness",
    "profit_protection": "Preserve margin, price above median if possible",
    "market_penetration": "Aggressive below-market pricing to gain share",
    "premium_positioning": "Price above market to signal quality/exclusivity",
    "clearance_cashflow": "Price at/below cost to clear inventory and generate cash",
}


def _safe_number(value, fallback: float = 0.0) -> float:
    """Convert numeric inputs to finite floats, replacing missing values."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float(fallback)
    if not math.isfinite(numeric):
        numeric = float(fallback)
    return numeric


def _calculate_minimum_allowed_price(cost_price: float, target_margin: float) -> float:
    """
    Calculate minimum allowed price (never go below this).
    
    Business rule: Never recommend a price below our_cost_price * (1 + our_target_margin * 0.5)
    
    Args:
        cost_price: Our cost price
        target_margin: Our target margin
        
    Returns:
        Minimum allowed price
    """
    if cost_price <= 0:
        return 0.0
    return cost_price * (1 + target_margin * 0.5)


def _calculate_iran_market_premium(market_median_price: float, theoretical_toman_price: float) -> float:
    """
    Calculate Iran market premium percentage.
    
    Args:
        market_median_price: Observed median market price
        theoretical_toman_price: Calculated from base_usd_price * usd_rate
        
    Returns:
        Market premium as decimal (e.g., 0.25 for 25%)
    """
    if theoretical_toman_price <= 0:
        return 0.0
    return (market_median_price - theoretical_toman_price) / theoretical_toman_price


def calculate_strategy_prices(row: dict) -> Dict[str, float]:
    """
    Calculate prices for all strategies based on market and internal data.
    
    Phase 2 schema fields used:
    - our_cost_price, our_target_margin: Internal retailer data
    - market_min_price, market_median_price, market_max_price: Market data
    - torob_min_price, torob_median_price: Platform-specific market data
    - digikala_price: Platform-specific price
    - theoretical_toman_price: Calculated from base_usd_price * usd_rate
    - our_inventory, our_sales_7d, our_sales_30d: Inventory/demand signals
    
    Args:
        row: Product data dictionary
        
    Returns:
        Dictionary with strategy -> price mapping
    """
    # Extract Phase 2 fields
    cost_price = _safe_number(row.get("our_cost_price"), 0.0)
    target_margin = _safe_number(row.get("our_target_margin"), 0.25)
    
    # Market prices (Phase 2 schema - public observable data)
    market_min = _safe_number(row.get("market_min_price"), 0.0)
    market_median = _safe_number(row.get("market_median_price"), market_min)
    market_max = _safe_number(row.get("market_max_price"), market_median)
    
    # Platform-specific prices
    torob_min = _safe_number(row.get("torob_min_price"), market_min)
    torob_median = _safe_number(row.get("torob_median_price"), market_median)
    digikala_price = _safe_number(row.get("digikala_price"), market_median)
    
    # Global reference
    theoretical_toman = _safe_number(row.get("theoretical_toman_price"), 0.0)
    
    # Inventory and demand signals
    inventory = _safe_number(row.get("our_inventory"), 0)
    sales_7d = _safe_number(row.get("our_sales_7d"), 0)
    sales_30d = _safe_number(row.get("our_sales_30d"), 0)
    
    # Calculate constraints
    min_allowed = _calculate_minimum_allowed_price(cost_price, target_margin)
    
    # Inventory pressure: high inventory or weak sales = discount pressure
    inventory_pressure = 0.0
    if inventory > 80:
        inventory_pressure = 0.05  # 5% discount pressure
    elif inventory > 50:
        inventory_pressure = 0.03  # 3% discount pressure
    
    # Velocity pressure: low sales velocity = discount pressure
    velocity_pressure = 0.0
    if sales_30d > 0:
        velocity = sales_7d / (sales_30d / 4)  # Weekly sales vs average weekly
        if velocity < 0.5:
            velocity_pressure = 0.03  # Weak sales
    
    total_discount_pressure = min(inventory_pressure + velocity_pressure, 0.10)  # Cap at 10%
    
    # Calculate prices for each strategy
    prices = {}
    
    # 1. Trust Builder: Close to market_min_price, but protect minimum margin
    trust_builder_price = max(
        torob_min * 0.98,  # Match/beat Torob's minimum
        min_allowed,
    )
    prices["trust_builder"] = round_to_retail_price(trust_builder_price)
    
    # 2. Balanced: Near market_median_price
    balanced_price = max(
        market_median * 0.99,  # Slightly below median
        min_allowed,
    )
    prices["balanced"] = round_to_retail_price(balanced_price)
    
    # 3. Profit Protection: Preserve margin, consider theoretical_toman_price as floor
    # Price at or above median, but protect minimum margin
    profit_protection_price = max(
        market_median * 1.05,  # 5% above median for margin
        theoretical_toman * 1.20,  # At least 20% above theoretical (to capture Iran premium)
        min_allowed,
    )
    prices["profit_protection"] = round_to_retail_price(profit_protection_price)
    
    # 4. Market Penetration: Aggressive below-market pricing
    # But never below minimum allowed price
    market_penetration_price = max(
        market_min * 0.97,  # Aggressive below minimum
        min_allowed,
    )
    prices["market_penetration"] = round_to_retail_price(market_penetration_price)
    
    # 5. Premium Positioning: Above median, but not exceeding max (unless very compelling)
    # Consider being 10-15% above median for premium signal
    premium_positioning_price = max(
        market_median * 1.12,  # 12% above median
        min_allowed,
    )
    # Don't exceed market max significantly (stay within market bounds for premium)
    premium_positioning_price = min(premium_positioning_price, market_max * 1.05)
    prices["premium_positioning"] = round_to_retail_price(premium_positioning_price)
    
    # 6. Clearance/Cashflow: Discount pressure applied
    # When inventory is high or sales weak, price more aggressively
    clearance_base_price = market_min * 0.96
    clearance_price = max(
        clearance_base_price * (1 - total_discount_pressure),
        min_allowed,  # Never go below minimum even in clearance
    )
    prices["clearance_cashflow"] = round_to_retail_price(clearance_price)
    
    return prices


def select_strategy_price(row: dict, strategy: str = None) -> Dict:
    """
    Select pricing for a specific strategy.
    
    Args:
        row: Product data dictionary
        strategy: Strategy name (one of VALID_STRATEGIES)
        
    Returns:
        Dictionary with selected strategy and calculated prices
    """
    # Default to "balanced" if strategy not specified or invalid
    if strategy is None or strategy not in VALID_STRATEGIES:
        strategy = "balanced"
    
    # Calculate all strategy prices
    strategy_prices = calculate_strategy_prices(row)
    
    # Get selected strategy price
    selected_price = strategy_prices.get(strategy, strategy_prices["balanced"])
    
    # Get market data for explanation
    market_median = _safe_number(row.get("market_median_price"), 0.0)
    theoretical_toman = _safe_number(row.get("theoretical_toman_price"), 0.0)
    cost_price = _safe_number(row.get("our_cost_price"), 0.0)
    our_current_price = _safe_number(row.get("our_current_price"), 0.0)
    
    # Calculate margins for context
    expected_margin = (selected_price - cost_price) / cost_price if cost_price > 0 else 0.0
    
    # Calculate Iran market premium
    iran_premium = _calculate_iran_market_premium(market_median, theoretical_toman)
    
    # Build strategy explanation
    strategy_explanation = _build_strategy_explanation(
        strategy=strategy,
        selected_price=selected_price,
        current_price=our_current_price,
        market_median=market_median,
        theoretical_toman=theoretical_toman,
        cost_price=cost_price,
        expected_margin=expected_margin,
        iran_premium=iran_premium,
    )
    
    return {
        "strategy": strategy,
        "selected_strategy_price": float(selected_price),
        "strategy_prices": {k: float(v) for k, v in strategy_prices.items()},
        "strategy_explanation": strategy_explanation,
    }


def _build_strategy_explanation(
    strategy: str,
    selected_price: float,
    current_price: float,
    market_median: float,
    theoretical_toman: float,
    cost_price: float,
    expected_margin: float,
    iran_premium: float,
) -> str:
    """
    Build human-readable explanation for strategy-based pricing.
    
    Args:
        strategy: Strategy name
        selected_price: Selected strategy price
        current_price: Current selling price
        market_median: Market median price
        theoretical_toman: Theoretical price from USD conversion
        cost_price: Our cost price
        expected_margin: Expected margin with selected price
        iran_premium: Iran market premium percentage
        
    Returns:
        Human-readable explanation
    """
    lines = []
    lines.append(f"**Strategy: {strategy.replace('_', ' ').title()}**")
    lines.append(STRATEGY_DESCRIPTIONS[strategy])
    lines.append("")
    
    # Price positioning
    if selected_price < market_median * 0.95:
        positioning = "below market (competitive)"
    elif selected_price < market_median * 1.05:
        positioning = "at market (neutral)"
    else:
        positioning = "above market (premium)"
    lines.append(f"Selected price {selected_price:,.0f} is {positioning}.")
    
    # Price change from current
    if current_price > 0:
        price_change_pct = (selected_price - current_price) / current_price * 100
        if abs(price_change_pct) > 0.5:
            direction = "increase" if price_change_pct > 0 else "decrease"
            lines.append(f"This represents a {abs(price_change_pct):.1f}% {direction} from current price.")
    
    # Margin context
    lines.append(f"Expected margin: {expected_margin:.1%}")
    
    # Market context
    if market_median > 0:
        vs_median_pct = (selected_price - market_median) / market_median * 100
        lines.append(f"Relative to market median: {vs_median_pct:+.1f}%")
    
    # Iran premium context
    if iran_premium > 0.10:
        lines.append(f"Iran market premium: {iran_premium:.1%} (significant import scarcity)")
    
    # Theoretical reference context
    if theoretical_toman > 0:
        theoretical_multiplier = selected_price / theoretical_toman
        lines.append(f"Theoretical toman price reference: {theoretical_toman:,.0f}")
        lines.append(f"Selected price is {theoretical_multiplier:.2f}x the theoretical reference")
    
    return "\n".join(lines)
