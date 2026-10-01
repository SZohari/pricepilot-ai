# Germany wearable demo

20 fictional wearable products; 80 synthetic observations; reference date 2026-09-26.
All monetary data is EUR. No seller, price or product here represents verified current market data.

The scenario includes:
- normal three-seller market evidence;
- an unavailable fourth seller;
- a high sourcing-cost product;
- zero inventory;
- entirely stale observations for one product;
- only one available seller for another.

Load demo.json through src.application.service.load_demo. The default UI uses a session-isolated in-memory workspace. Explicit persistent import uses python -m scripts.load_german_demo. No existing data is reset by either workflow.
