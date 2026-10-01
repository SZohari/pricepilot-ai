# Continuous setup and evidence collection — 2026-09-28

Version 1.7 adds explicit Welcome/resume navigation, five hash-addressed stages,
product-specific refresh inside the market step, and dated owner questions with
observation plans. A question can pause a price test without becoming an invented
numerical predictor. Findings can be updated and carried into a fresh review.

Validated with 553 Python tests (one optional legacy skip) and 80 Node tests.
The saved browser-site restriction still prevents a rendered UI walkthrough;
no visual sign-off, commercial outcome or public deployment is claimed.
See [GUIDED_SETUP.md](GUIDED_SETUP.md) for scope and remaining boundaries.

---

# Guided pricing setup — 2026-09-28

Version 1.6 replaces the primary decision desk with five sequential stages.
Costs are previewed before confirmation; market/context precedes advice; price
controls explain contribution and required sales; the final step records a plan
and states exactly which work is automated. Three independently generated photos
now change with the homepage chapters. The advanced library remains secondary.

See [GUIDED_SETUP.md](GUIDED_SETUP.md) for interaction and verification details.
This is a local update and source package; Render publication is still pending.

---

# Retail decision workspace — 2026-09-27

Version 1.5 replaces the main journey with one fictional online watch shop.
The welcome landing remains distinct from the working product decisions. New
watch-packing and watch-detail illustrations replace the repeated photographer.

Implemented: CSV/TSV mapping and preview; atomic import; itemised order costs;
purchase/replacement distinction; gross/net fee basis; dated sales and cost
confirmation; supplier scenarios; server-calculated decisions; SKU-linked plans;
price review CSV; stale-plan checks; observed result review and audit snapshots.

See [RETAIL_DECISION_SYSTEM.md](RETAIL_DECISION_SYSTEM.md) for exact logic,
[HOMEPAGE_DESIGN.md](HOMEPAGE_DESIGN.md) for asset provenance and the browser
verification limitation, and [RUN_ME_FA.md](../RUN_ME_FA.md) for the owner guide.
The update is local and packaged. No live merchant outcome or Render deployment
has been claimed. Earlier delivery notes below describe previous versions.

---

# Scroll-led homepage — 2026-09-27

The landing page is now a full-width dark editorial experience with three bespoke
generated business images, self-hosted Newsreader/Manrope fonts and a studio story
whose answer changes as the visitor scrolls. Each chapter opens its exact case in
the working advisor. The consultation workspace returns after entry. Primary
copy and several form labels now use everyday business language.

Native scroll, keyboard chapter buttons, a motion toggle, device reduced-motion
support and mobile inline answers are implemented. Navigation releases listeners
and pending frames. Windows asset MIME types were corrected for WebP and WOFF2.
The source archive includes the images, fonts and both font licenses (about
1.1 MB total). Source artwork and prompts remain in `design/homepage`.

Verification: 497 Python tests passed, one optional legacy PyArrow test skipped.
Frontend tests cover the homepage's response-driven answers, escaped inputs,
scroll selection, keyboard navigation, motion preferences and cleanup. Local HTTP
checks confirm correct asset MIME types and the three server-computed story
decisions. The local server has been restarted. Browser visual inspection remains
unverified because the saved local-access restriction is still in effect. No
public Render deployment was performed. See [homepage design](HOMEPAGE_DESIGN.md).

# Economic discovery layer — 2026-09-27

Version 1.4.0 adds a three-step fictional walkthrough, dated owner knowledge, a saved learning contract, a conditional price–sales boundary and a source-linked method page. The consultation policy is versioned as `consultation-2`. Identical financial inputs produce a bounded reduction, a value-validation action or an explicit candidate test as the interpretation and chosen hypothesis change.

Verification: 494 Python tests passed (one optional legacy PyArrow test skipped); 41 Node tests passed. Real HTTP checks on the restarted local server confirmed the three diagnoses, stable report fingerprints, saving local-knowledge evidence and rejection conditions, and successful/missed/confounded simulated outcomes. Static discovery modules and CSS were served successfully. Visual browser QA is still unverified due to the saved local-access restriction. The public deployment has not been updated.

# Consultation rebuild — 2026-09-27

The primary screen is now a business consultation, not the former guided numerical comparison. Three fictional German cases and merchant intake lead to server-calculated advice, saved action plans, applied-price records and actual outcome reviews. Live product source setup is available inside local merchant consultations; public URL configuration remains disabled.

Validation performed: full Python suite; frontend Node tests; actual HTTP checks against the restarted local 1.3.0 server for all three diagnoses, three simulated outcome conditions, the planned → active → completed lifecycle, and HTML/JS/CSS responses. Simulated outcome previews do not mutate plan state. Browser visual and interaction QA remains unverified because a saved local-browser permission blocks that access. No public Render deployment was made in this change.

Older delivery notes below describe prior interfaces and should not be read as the current entry flow.

# Dashboard delivery - 2026-09-26

**Historical first redesign.** The current dark store example and live-collection implementation are documented in [MVP_STORE_REVIEW.md](MVP_STORE_REVIEW.md).

## Delivered
The default interface is now a browser dashboard served by FastAPI at localhost:8000. It includes Overview, Pricing decisions, Product catalog, Scenario lab and Data workspace, plus product detail and edit dialogs. Search, brand/status filters, sort, pagination, cost simulation, export, import, product writes and observation writes connect to the application service.

The browser uses native ES modules and local CSS; no CDN, Node build or PyArrow is needed. Responsive layouts are implemented for desktop and small screens. Keyboard focus, dialog semantics, field labels and reduced-motion support are included.

The catalog has 24 real model references across 10 brands, covering smartwatches, outdoor/running watches, fitness trackers and hybrid watches. Source URLs and verification dates travel with the exported products. Prices, sales, costs, inventory and seller offers are simulated. The previous fictional dataset is archived separately. The generator never modifies persistent user data.

Model references include [Apple](https://www.apple.com/de/apple-watch-series-12/), [Samsung](https://www.samsung.com/de/watches/), [Google/Fitbit](https://store.google.com/de/category/watches_trackers?hl=de) and [Huawei](https://consumer.huawei.com/de/wearables/watch-gt7-pro/). Every product has its own reference URL in the dataset and detail dialog. Some references are official category pages or manuals. They confirm model identity, not exact SKU or availability.

## Verification actually completed
- 397 Python tests passed; one optional legacy Streamlit smoke test skipped because the available PyArrow build targets a different Python version.
- New web integration tests cover session isolation, session-bound write tokens, optimistic concurrency, invalid saves, atomic import conflicts, export, evidence writes and non-mutating scenarios.
- JavaScript syntax checks passed for app.js and utils.js.
- The local web server started successfully on 127.0.0.1:8000.

## Verification limitation
Browser control was denied after an initial automatic-review timeout. Therefore no screenshot review, live UI click-through, responsive viewport inspection or browser accessibility audit is claimed. These remain unverified despite implemented responsive styles and interaction handlers.

## Data lifecycle and boundaries
Demo sessions are isolated per browser and expire after two hours of inactivity; restarting the server resets them. Export preserves data. Persistent mode is read-only in the UI and requires configured API credentials for writes. This remains a local portfolio application, not a publicly deployed multi-user service.

The decision engine is an explainable deterministic baseline, not a trained AI forecast. Scenario output measures policy responses to changed assumptions; it is not a claim of causal business uplift.

Additional checks: the Windows PowerShell launcher started a second server on port 8001, then that test process was stopped. UI helper checks for HTML escaping, unsafe reference URLs and empty metrics passed. The 18-strategy/cost evaluation scenarios completed with zero proposed-price floor breaches. Docker and remote CI were not executed.
