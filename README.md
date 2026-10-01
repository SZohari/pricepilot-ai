# PricePilot — Pricing consultation and follow-up

**A better price. A clearer next step.** The welcome page leads into a fictional German online watch shop. Import a catalog, inspect one order's costs, compare the actual offer, choose a bounded action and follow the observed result. Selected ideas from Hayek and Menger inform how the system treats local knowledge and uncertainty; [the economic foundations](docs/ECONOMIC_FOUNDATIONS.md) explain the interpretation and its limits.

A **Data + AI + Business** MVP for a concrete business question: **what should I do about this price, and how will I know whether it helped?** It diagnoses costs, sales signals and capacity, proposes a bounded action, records what the owner actually did, and reviews the observed result against contribution and volume guardrails. The initial audience is Germany/EUR; the consultation supports repeatable goods and services. Commercial effectiveness has not yet been validated with merchants.

## Run the dashboard

**Windows: double-click `Start PricePilot.cmd` in the project folder.** Keep the terminal window open. Your browser opens at **http://127.0.0.1:8000**. Close the terminal or press Ctrl+C to stop.

The launcher checks available Python environments, including the compatible runtime on this machine. A clean installation needs Python 3.12 and:

```bash
python -m pip install -r requirements-web.txt
python run.py
```

No Node build, Streamlit or PyArrow is needed for the new dashboard. If port 8000 is busy: `python run.py --port 8001`. API documentation: http://127.0.0.1:8000/docs.

Persian instructions: [RUN_ME_FA.md](RUN_ME_FA.md).

## The interactive MVP

The English welcome page introduces one fictional watch shop. Each scroll chapter has its own AI-generated editorial image. **Build my pricing routine** opens five guided steps: **Your shop → Costs & limits → Market & customers → Choose a move → Your plan**. Later steps unlock as the visitor reviews the earlier ones. [Guided setup](docs/GUIDED_SETUP.md) and [design/asset provenance](docs/HOMEPAGE_DESIGN.md).

Start with a product and a sales-loss limit. Editing supplier or order costs updates a read-only preview and explains the change in money left per sale; confirmation saves the product. Review comparable offers and customer signals before seeing the advice. At the price step, compare current and proposed contribution and the sales required to meet both limits. These are conditions for a test, not predicted demand. Incomplete/failed updates cannot advance to a plan. **Product library** retains the detailed workspace and hypothetical supplier scenarios under the secondary tools.

**Import products** accepts CSV/TSV with column mapping, explicit number format, shared or per-product settings, a row preview and all-or-nothing commit. Historical purchase cost, current replacement cost, VAT, gross/net fee basis, delivery, packaging, returns reserve and chosen margins have separate meanings. Existing SKUs are never silently overwritten. [Retail decision system and accounting](docs/RETAIL_DECISION_SYSTEM.md).

In **Market & customers**, use **What might the numbers miss?** for a dated question, hypothesis or owner observation. Keep it as context or pause a price test until it is investigated. Each topic has an observation plan; update the finding as you learn. Exact competitor URLs can be connected and refreshed for that product in the same step. Welcome/resume navigation keeps the reviewed setup when moving between pages. The accounting boundary shows the sales a price would require, not a demand forecast. The economic method and ML evaluation remain directly accessible.

Save the consultation as an action plan. A linked product test can export a CSV review sheet separating item price and customer delivery. This is a handoff sheet, not an automatic shop integration. For a price trial, record when you applied the price yourself, then enter actual sales and costs. The review checks contribution, sales volume and unit margin, normalizes for period length, and marks incomplete or confounded comparisons. A fictional case also lets visitors preview good, bad and confounded outcomes immediately, without creating fake business records. [Consultation method and limits](docs/PRICING_CONSULTANT.md).

The market-gap chart shows the percentage difference between store price and delivered market median, with both prices visible. It does not imply demand or profit uplift. Decision labels and colors communicate different actions.

## The workspace

- **Your pricing setup:** five sequential steps, live input consequences and a reviewed action plan.
- **Product library:** the detailed catalog/decision workspace under secondary tools.
- **Import products:** preview-first CSV/TSV intake or detailed single-product entry, separate purchased/replacement costs and explicit fee bases.
- **Pricing consultant:** business intake → diagnosis → bounded action → saved plan → observed follow-up. A reduction must earn enough additional sales to preserve contribution; an increase must also respect the owner's volume-loss limit. The figures are required outcomes, not forecasts.
- **Price sandbox:** optional instant, reversible sensitivity analysis and comparison.
- **Decision workbench:** a ranked review queue, financial/evidence checks, accept/reject/defer with reasons, immutable input snapshots and an exportable journal. Stale reviews are rejected; no shop price is changed.
- **Demand model lab:** real supervised ridge training, temporal validation/calibration/test, two simple baselines, empirical error bands and an explicit demand-shock failure case. Upload a single-SKU daily JSON history or use the synthetic example.
- **Store example:** a guided business case, market-gap chart, operational metrics and six decision stories.
- **Competitor monitor:** a configured JSON-LD price collector, streamed source results, separate demo/live evidence and opt-in five-minute refresh. A local merchant consultation can connect exact product URLs and GTINs from the interface; public visitors cannot add fetch URLs.
- **Pricing decisions:** searchable, filterable products, suggested prices, evidence coverage and detailed explanations.
- **Product catalog:** 24 real wearable models across 10 brands, with official references.
- **Scenario lab:** replacement-cost stress, six strategies and evidence-age/date controls. Simulations do not mutate inputs.
- **Data workspace:** validated product edits, append-only observations, atomic JSON import/export and audit history.

**All bundled prices, costs, sales, inventory and competitor offers are simulated.** Model names and official references are real; the dataset does not claim live availability, exact SKU specifications or current market prices. Generic watch illustrations are not product photographs. Reference date: 2026-09-26.

The default demo is isolated by browser session. Edits survive page refresh, but reset after server restart or two hours of inactivity. **Export datasets and action plans separately to keep your work.** Dataset imports add new IDs; conflicting IDs reject the whole import. Saved plan exports are evidence records; this MVP does not restore an entire action journal from an export. Original Iran CSV files are preserved. Older retail policy tables and sensitivity tools remain under **Tools & project details**; they do not authorize the consultant's plans.

## Live prices and a public link

The generic collector requires exact GTINs and explicit delivery assumptions, reports unsupported sources and never disguises demo offers as live. No supported live retailer is preconfigured. A direct Decathlon check on 2026-09-27 was allowed by robots.txt but returned HTTP 403 for the product page; it imported no price. A configured source is not a promise of coverage. See [live collection setup](docs/LIVE_COLLECTION.md).

A Render Blueprint and minimal Docker deployment are included. The current source is on GitHub and its release checks passed. **No verified public URL yet:** Render requested payment information even for its Free service; a free, card-free alternative is being evaluated. Visitors will need only the hosted URL, with no installation or signup. See [deployment status](docs/ONLINE_DEMO.md) and [PythonAnywhere setup and limits](docs/PYTHONANYWHERE.md).

## What the intelligence actually does

The primary consultant is a versioned, deterministic decision service with Decimal unit economics. It can advise improving visibility, refreshing evidence, revising cost or scope, or running a small price trial. It does not optimize an invented elasticity curve. The older retail policy engine remains a comparison baseline. The separate **learned demand model** estimates one-day-ahead unit sales from price, competitor price, promotion, calendar patterns and recent sales; its coefficients are fitted to data. It cannot authorize a price change or prove a causal price effect.

The default synthetic benchmark produces lower holdout error than both simple baselines; an unseen demand shock reverses that result. Both are visible rather than hiding failure. Neither result proves real-world accuracy, price elasticity or profit uplift. See the [model card](docs/MODEL_CARD.md) and [five-seed evaluation](docs/demand-evaluation.json).

```text
net revenue = gross price / (1 + VAT rate)
percentage fee = fee rate * gross price [gross basis], or fee rate * net revenue [net basis]
contribution = net revenue - percentage fee - replacement cost - variable cost
contribution margin = contribution / net revenue
```

The demo's VAT assumption is 0.19. Costs are net; customer prices are gross. The fee basis is explicit: legacy demo products use net revenue; new retail intake starts with the editable gross-payment basis. These assumptions are explicit inputs, not a tax-compliance implementation. No measured demand, revenue or profit uplift is claimed. Suggestions are never automatically applied.

## Architecture

```text
src/web/static/       Browser UI: native ES modules, CSS, accessible HTML
src/web/app.py        FastAPI host, isolated demo sessions, write-token protection
src/api/v1.py         Versioned API contracts and routes
src/application/     Application services
src/domain/          Validated contracts and Decimal pricing rules
src/infrastructure/  SQLite repository, optimistic concurrency and audit
```

The browser consumes the same service as the API. CSS and application JavaScript are independent of pricing policy. The previous Streamlit adapter remains available at `src/dashboard/app.py` as an optional legacy UI.

## Persistent local data

```bash
python -m scripts.load_german_demo --database data/workspaces/pricepilot.sqlite3
```

Set `PRICEPILOT_DB_PATH` to that absolute path before launching. The web interface is read-only in persistent mode. API writes require `PRICEPILOT_API_KEY` and the `X-API-Key` header. An empty database stays empty. This is a local development gate, not multi-user authentication.

## Verification and reproducibility

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
python -m scripts.evaluate --output docs/evaluation-baseline.json
python -m scripts.evaluate_demand --output docs/demand-evaluation.json
node --test tests/web/*.test.mjs
```

The optional legacy Streamlit smoke test skips if a compatible PyArrow is unavailable. The primary web workspace has independent integration tests. See [dashboard delivery notes](docs/DASHBOARD_DELIVERY.md) for actual checks performed.

The catalog generator is `scripts/generate_demo_catalog.py`; it archives the old fictional demo once as `demo.synthetic-v1.json`. Regenerating the demo file does not reset a running or persistent workspace.

Project direction and limitations: [Project brief](PROJECT_BRIEF.md), [Architecture](docs/ARCHITECTURE.md), [Evaluation](docs/EVALUATION.md), [Roadmap](ROADMAP.md).

For buyers/reviewers: [commercial case and pilot scorecard](docs/PRODUCT_STRATEGY.md), [model card](docs/MODEL_CARD.md), [current delivery and remaining gaps](docs/CORE_UPGRADE.md).
