# From a retailer's inputs to a defensible decision

PricePilot 1.6 uses **Kiez & Co**, a fictional German online watch shop, as its
main working example. The welcome page introduces the workflow. The workspace
presents decisions. The 24 model references are real; all bundled financial
values and competitor offers are simulated. Generic images do not depict the models.

## A complete working path

1. Open **Your pricing setup** (`#shop`). Pick a product and a sales-loss limit.
2. Review costs and sales inputs. Draft edits recalculate without writing; confirmation saves a versioned product.
3. Inspect comparable offers and add the owner's customer context.
4. Choose a price/action. Compare current and candidate contribution and required sales.
5. Save the reviewed plan, export its evidence/price review sheet, record manual execution and the observed result.

The [guided setup contract](GUIDED_SETUP.md) documents stage gating and reactive inputs. `#products` retains the advanced library. `#onboarding` imports CSV/TSV or adds a product, then returns to the guided path. `#plans` holds the journal. The detailed consultation and ML evaluation remain secondary tools.

## Every input has a meaning

| Input | Meaning and treatment |
| --- | --- |
| SKU and variant | Stable merchant identifier plus exact size, connectivity, strap and condition. Model names alone are not exact matches. |
| GTIN / EAN | Optional at intake, required for automatic matching; valid length/checksum, preserved leading zeroes. A source must match the saved GTIN. |
| Item price + customer delivery | Sum to total customer payment including VAT. Export separates them again, avoiding double-counted delivery. |
| Historical purchase cost | Past commitment for stocked units. Changing it does not alter the replenishment-based floor/test. |
| Replacement cost | Dated EUR supplier quote for the next unit; used for the replenishment constraint, not willingness to pay. |
| Order costs | Inbound freight/duty, outbound delivery, packaging, unrecovered returns reserve, fixed transaction fees and other variable costs. Exclude recoverable VAT; include nonrecoverable tax. |
| Percentage fee | Explicit gross/customer-payment or net/revenue basis. Fixed fees are separate. |
| Minimum and target margins | Owner choices: contribution divided by net revenue, not markup. Target-margin price is a cost calculation, not a recommended market price. |
| Dated sales and stock | Completed 30-day units at the current price, with availability/campaign confirmation. Optional seven-day units distinguish missing from zero. Stock limits feasible tests. |
| Customer knowledge | Dated, attributed observations or hypotheses. A claimed service benefit earns no invented premium. |

The returns allowance estimates unrecovered loss after refunds/recoveries; it
must not count the full purchase cost again for a recoverable return. This MVP
does not estimate that reserve or reconcile a refund ledger. Fixed overhead is
outside contribution. Single-item EUR orders are the supported intake scope.

## Exact conditional accounting

For total customer payment `P`, VAT `v`, percentage fee `r`, replacement plus
order costs `C`, and chosen minimum margin `m`:

```text
N = P / (1 + v)
fee = r * P  [gross basis] or r * N  [net basis]
contribution = N - fee - C
margin = contribution / N
effective_net_fee = r * (1 + v)  [gross basis], otherwise r
minimum_total_price = ceil_to_cent(C * (1 + v) / (1 - effective_net_fee - m))
```

At EUR 119 including 19% VAT, net revenue is EUR 100. With EUR 55 costs and a
2% fee on customer payment, contribution is EUR 42.62. The same percentage on
net revenue gives EUR 43.00. The wrong fee basis quietly overstates margin.
Authoritative calculations use Decimal without intermediate rounding. The
visible waterfall reconciles displayed cents to its final residual.

A test must preserve total contribution **and** respect the allowed sales loss.
The larger integer sales threshold applies, then stock, margin and the 10%
movement limit are checked. Suggested small moves and limits are explicit MVP
policy, not learned economic constants. Required sales are conditions, not forecasts.

## Why not an ideal price?

Costs describe business constraints; listings describe offers, not completed
purchases. Customer response depends on the whole offer and context. The advisor
therefore chooses between checking inputs, restoring availability, investigating
visibility, revising costs and running a bounded trial.

This interprets selected Austrian insights about local knowledge, subjective
value and discovery. It does not validate an economic school or imply that any
cost establishes market value. Clearance can use different objectives and limits;
this replenishment workflow does not automatically solve it. See
[Economic foundations](ECONOMIC_FOUNDATIONS.md) and Hayek's
[The Use of Knowledge in Society](https://www.econlib.org/library/Essays/hykKnw.html).

## Evidence and execution controls

- Explicit CSV separator/decimal format, column mapping, normalized preview and
  row errors. Maximum 200 rows per file, 1,000 workspace products. Unmapped costs
  are visible zeroes requiring confirmation. No history/competitors are invented.
- Preview writes nothing. Confirmed commit recalculates the fingerprint and
  inserts all rows or none. Case-insensitive SKU conflicts and capacity are checked
  within the transaction. Existing data cannot be silently overwritten.
- Detailed edits preserve provenance and use optimistic versions. GTIN/variant
  changes are blocked once evidence exists; a different offer needs a new SKU.
- Market evidence checks date, availability, freshness, seller deduplication and
  provenance. Owner-entered offers remain attributed. Source support is never
  assumed. Public visitors cannot configure fetch URLs. See [collection](LIVE_COLLECTION.md).
- Plans retain policy version, fingerprint, product version/snapshot and evidence.
  Saving and starting reject changed linked product inputs or market records.
  Starting also checks dates and the actually applied price. Only one linked trial
  can be active per SKU. An early check-in keeps it active for a later cumulative
  outcome; its observation and evaluation remain in the audit record.
- CSVs are review sheets for regular-price tests, not platform-specific bulk
  updates. Nothing publishes prices or creates discount announcements. Mixed tax
  baskets, tax compliance and multi-item orders need separate implementations.
- Demo inputs replay their stated snapshot date; merchant inputs use current
  date checks. Demonstration cost decompositions are labelled. Missing merchant
  detail is never filled from the demo.

## Data and AI: evidence for each claim

The operational advisor is deterministic accounting and rules. The separate ML
lab trains a ridge demand model with chronological holdouts, train-only
transformations, simple baselines and a visible demand-shock failure. Synthetic
performance cannot establish real accuracy or causal response to a changed price.
Passing a prediction benchmark does not authorize automatic pricing.

Next useful data: daily SKU price, units, availability, promotions, dated competitor
offers and relevant context. Causal pricing needs an experiment or defensible
identification design. Inflation/FX enters through actual EUR supplier quotes and
scenarios here; no macroeconomic effect is forecast. Product age, promotions,
stockouts and retention remain visible questions. Sales counts do not measure
retained customers.

## Verification and limits

`tests/v1/test_retail_workspace.py` checks both fee bases, cent-level floors,
purchase/replacement distinctions, missing data, stock, shipping, atomic import,
identity, session isolation, stale plans and the full HTTP import-to-outcome path.
`tests/web/retail.test.mjs` checks text escaping, form serialization, confirmations,
stale responses and file-read races. Existing pricing, ML, collection and
persistence tests remain in the suite.

Generated images were inspected. Automated interface checks passed, but the
saved browser access restriction prevented a rendered visual pass. This is a
local and packaged MVP; no Render deployment or merchant pilot was performed.
Sessions are temporary: export datasets and plans separately. Plan exports are
evidence records, not a restorable full workspace.
