# Interactive pricing cockpit

The default page is now a product-level sensitivity workspace. Controls update immediately without submitting a form or changing stored data. The prior store overview remains under Store example.

Controls: own price, replacement cost, competitor price level, underlying demand and assumed price elasticity. Presets cover cost pressure, a competitor sale and ageing stock. Users can pin a scenario for comparison, reset controls, select another product, or click an alternative price in the contribution chart.

The 30-day illustration uses historical demo sales as its reference quantity, constant assumed elasticity, and no replenishment. Units are capped at current inventory. It includes VAT, payment fees, replacement and variable costs; it excludes fixed overhead and profit taxes. It does not predict customer retention. Prices below the minimum-margin floor are visibly flagged, not silently corrected. This lets a visitor inspect the sales/contribution trade-off.

This is a client-side assumption calculator, not a trained demand model or a causal estimate. It does not modify competitor observations or the backend policy recommendations. Calculations use JavaScript floating point and are display simulations; persisted monetary policy calculations continue to use backend Decimal arithmetic.

Verification: seven new model tests cover accounting, discounted sales versus contribution, cost shocks, stock caps, zero sales, relative market prices and elasticity. All 14 web model/presentation tests and 8 Python web integration tests passed on 2026-09-26. Browser visual verification is pending: a saved browser permission blocks localhost. Render deployment was attempted through the existing user tab but its dashboard returned ERR_CONNECTION_CLOSED. No public deployment is claimed.
