# Live competitor collection

The generic connector is implemented. **No supported retailer is preconfigured.** The shipped demo never labels simulated seller prices as live. A direct Decathlon check on 2026-09-27 returned HTTP 403 for its product page after robots allowed the path; no price was imported.

## Guided product setup (1.7)

For an imported merchant product, Market & customers contains **Connect a
competitor URL once**. Owner setup requires a valid exact GTIN, HTTPS product URL,
seller, delivery charge, delivery basis and variant confirmation. Connecting a
source checks it immediately. Re-entering the step refreshes that product at most
once per five minutes; uncheck the option to stop these entry-triggered checks.
Manual refresh remains available. Results include per-seller failures and cache
status. The demo shop never triggers live collection.

`POST /api/sources/refresh-product` accepts `product_id`, requires the workspace
write token and filters configured sources to that SKU. Each observation commit
checks the saved product version atomically; exact cached duplicates are harmless.
The generic collector's robots, public-host, identity, rate and parsing safeguards
still apply. This is not automatic product discovery or a store-data connector.

## Owner configuration

In the local browser workspace, open a merchant-origin goods consultation and expand **Connect an exact product for automatic collection** below the advice. Enter the exact listing, valid GTIN, seller and delivery assumptions, and confirm the variant. This creates a merchant catalog link if necessary. Open **Competitor prices → Collect live prices**, then return to the consultant to incorporate fresh evidence. URLs are scoped to this browser session and are cleared with its demo reset. Services use owner-entered, explicitly comparable evidence instead of GTIN collection.

The local configuration endpoint is disabled on public demos and persistent workspaces. For repeatable or hosted owner configuration, use the source file below.

Copy `config/price_sources.example.json` to a local JSON file and replace every placeholder. The template intentionally fails validation until a valid exact GTIN is supplied. Each row maps a retailer listing to a catalog product. All sellers for that product must use the same GTIN/variant; broad model identity is insufficient.

Supply a public HTTPS URL, exact GTIN (including check digit), seller, product ID, delivery cost and an explicit delivery assumption. No free-shipping default is inferred. Do not use a model-family page as if it identified a precise SKU.

PowerShell:
```powershell
$env:PRICEPILOT_SOURCES_PATH = "F:\Projects\PricePilot AI\config\my_sources.json"
.\start.ps1
```

Open **Competitor monitor → Collect live prices**. Each result arrives through a streamed HTTP response. Enable the five-minute refresh checkbox for repeated collection while the tab is visible. A single shared process cache limits repeated reads of each source. This is browser-driven periodic collection, not an unattended 24/7 scheduler.

Live observations are stored with source URL, UTC collection timestamp, seller, shipping assumption and `data_origin=live`. Selecting live evidence excludes demo observations completely. There is no fallback to demo prices if a source fails. Store prices, costs and sales in the portfolio example remain simulated.

## Supported pages and failure behavior

The parser accepts one JSON-LD `Product` matching the exact GTIN, containing one explicit new-condition EUR `Offer` with price and availability. Expired offers, aggregate/range prices, ambiguous variants, unsupported availability and absent condition/currency fail closed. It does not execute retailer JavaScript, solve CAPTCHA, log in or circumvent access controls.

The collector checks robots.txt before a product fetch, rejects private/reserved destinations, pins the validated IP for the TLS connection, verifies certificates, refuses redirects, sets timeouts and bounds response size. Public configuration is server-owned; public visitors cannot enter arbitrary fetch URLs. The cache includes the whole source configuration, so identical labels/IDs from different local sessions cannot mix observations.

Some retailers need a dedicated authorized API/feed adapter. This generic connector is an initial ingestion path, **not full coverage of all competitors or automatic product discovery**. GTIN matching, request failures and parser behavior have automated fixture tests; no selected real retailer can be claimed end-to-end verified until its URLs are configured.

Schema references: [Product](https://schema.org/Product), [Offer](https://schema.org/Offer).
