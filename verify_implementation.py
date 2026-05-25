#!/usr/bin/env python
"""Verify Phase 2 strategy-based pricing implementation."""

from src.data.sample_data_generator import generate_smartwatch_data
from src.pricing.recommendation import recommend_price
from src.pricing.strategies import calculate_strategy_prices

# Generate Phase 2 data
df = generate_smartwatch_data(seed=42, n_products=5)
print(f"✓ Phase 2 data generated successfully")
print(f"✓ Data shape: {df.shape}")
print(f"✓ Phase 2 schema: {'our_strategy' in df.columns}")

# Test strategy pricing
row = df.iloc[0].to_dict()
strategies = calculate_strategy_prices(row)
print(f"\n✓ Strategy prices calculated for first product:")
for strategy, price in strategies.items():
    print(f"  - {strategy}: {price:,.0f} toman")

# Test recommendation
recommendation = recommend_price(row)
print(f"\n✓ Recommendation generated:")
print(f"  - Product: {recommendation['product_name']}")
print(f"  - Recommended price: {recommendation['recommended_price']:,.0f} toman")
print(f"  - Selected strategy: {recommendation.get('selected_strategy', 'N/A')}")
print(f"  - Risk level: {recommendation['risk_level']}")
print(f"  - Action: {recommendation['action']}")
print(f"  - Theoretical toman price: {recommendation.get('theoretical_toman_price', 'N/A')}")
iran_premium = recommendation.get('iran_market_premium_pct')
if iran_premium is not None:
    print(f"  - Iran market premium: {iran_premium:.1%}")
else:
    print(f"  - Iran market premium: N/A")

# Verify contract
print(f"\n✓ Contract verification:")
assert recommendation['recommended_price'] == recommendation.get('selected_strategy_price'), \
    f"recommended_price ({recommendation['recommended_price']}) != selected_strategy_price ({recommendation.get('selected_strategy_price')})"
print(f"  ✓ recommended_price matches selected_strategy_price")

assert recommendation.get('strategy_prices'), "strategy_prices should be present"
print(f"  ✓ strategy_prices present with {len(recommendation['strategy_prices'])} strategies")

all_strategies = ['trust_builder', 'balanced', 'profit_protection', 'market_penetration', 'premium_positioning', 'clearance_cashflow']
for s in all_strategies:
    assert s in recommendation['strategy_prices'], f"Missing strategy: {s}"
    assert isinstance(recommendation['strategy_prices'][s], (int, float)), f"{s} price should be numeric"
    assert recommendation['strategy_prices'][s] > 0, f"{s} price should be positive"
print(f"  ✓ All 6 strategies present with numeric positive prices")

print(f"\n✓ All Phase 2 strategy features working correctly!")
