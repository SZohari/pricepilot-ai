# Dark store demonstration - delivery review

## Visitor experience
The public-facing interface is English. The Persian launch guide is owner-only documentation. Kiez & Co. is explicitly fictional: a Berlin wearable shop with 24 real model references and simulated store economics. The default design uses a dark navy palette, lilac emphasis and semantic decision colors.

The old scatter plot is replaced by ranked percentage gaps against delivered market medians, with both prices printed. The case cards explain six operational decisions: compete, protect contribution, hold, escalate sourcing cost, wait for evidence and clear slow inventory.

The Run the store example action streams twelve simulated offers, recalculates recommendations and reports the changes. It never changes saved selling prices. Reset explicitly affects only the current browser's demo; its dialog explains the data loss and export option.

## Working technical capabilities
- Session-bound POST streams for case replay and live collection.
- Exact-GTIN JSON-LD collector with explicit delivery, source URLs, timestamps and origin metadata.
- Demo/live evidence selection without fallback mixing.
- Opt-in five-minute collection while the browser tab is visible.
- Public-demo hosting configuration, secure production cookies, exact allowed hostnames and refusal to expose a persistent retailer database.
- Request size limits, bounded session capacity, shared source caching and private-network/redirect protections.

## Verification
- 428 Python tests passed; one optional legacy Streamlit test skipped for unavailable compatible PyArrow.
- Seven Node tests passed: decision semantics, market-gap meaning, empty live evidence and untrusted text escaping.
- The store replay was exercised via the same streaming HTTP routes used by the UI; cached live collection was verified with controlled HTML fixtures.
- Eighteen strategy/cost evaluations completed with zero proposed-price floor breaches.
- JavaScript syntax checks and Git whitespace checks passed.

## Remaining external dependencies
No competitor URLs were selected, so the live connector has no configured retailers. This is not a claim of complete competitor coverage, automatic discovery or verified live operation against a specific shop. See LIVE_COLLECTION.md.

No public hosting account was connected and no site was published. The Render Blueprint and Docker setup are ready for a reviewed deployment. See ONLINE_DEMO.md. Docker/Render themselves were not executed in this environment.

The user approved browser review, but the browser tool still returned a permission-denied result. No visual screenshot inspection, click-through or viewport QA is claimed. Automated tests do not replace that review.
