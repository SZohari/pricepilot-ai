# One pricing routine, five reviewed steps

PricePilot 1.7 extends the five-step setup introduced in 1.6. It addresses a concrete usability failure: a visitor could reach a
recommendation without understanding the inputs, and changing a candidate price
left the current-price cost breakdown visually unchanged. The primary `#shop`
route now builds the decision in order. `#products` retains the advanced library.

| Stage | Visitor's task | Result of completing it |
| --- | --- | --- |
| Your shop | Choose one SKU and acceptable sales loss | A selected product and explicit objective |
| Costs & limits | Check actual costs and dated sales; preview changes | A confirmed, versioned cost basis |
| Market & customers | Inspect offers; state the observed customer signal | Attributed evidence and visible gaps |
| Choose a move | Change the price and review limits | Current/candidate contribution and required sales |
| Your plan | Save the reviewed action and evidence | Exportable handoff and existing execution/outcome tracking |

The demo remains Kiez & Co, a fictional German online watch shop. All bundled
costs, sales and competitor prices are simulated. Importing a catalog or creating
one product returns to the same guided route. A plan can also be a useful
non-price action when costs, history, capacity or evidence do not support a test.

## Reactive input contract

- A cost edit waits 300 ms, validates a full draft Product and recalculates on the
  server using the saved version. Preview changes do not update the database or
  audit log. The response is hypothetical and cannot become a saved action plan.
- Confirmation saves through the versioned product endpoint, then re-analyzes
  the saved product. Product identity/provenance and existing variant evidence
  cannot silently change. Historical purchase and replacement cost stay separate.
- Editing the current price or sales period clears representative-baseline
  confirmation. Unknown expenses and owner confirmation stay explicit.
- Every candidate price uses the same server accounting as the advisor. The
  insight compares contribution before/after fees, VAT and variable costs.
  Required sales preserve baseline contribution and the chosen volume limit.
  It is a feasibility condition; no demand forecast or retention claim is added.
- Customer visibility, price objections, capacity and offer differences affect
  the policy. Owner-entered comparable offers remain attributed and validated.
- New edits invalidate dependent stages and the unsaved plan. In-flight or failed
  calculations disable Continue and label the earlier result. Generation tokens
  discard stale replies. Mutating confirmation/save prevents navigation races.
- Returning from another route refreshes evidence and preserves progress when
  valid. Changed product versions restart review; changed evidence sends a final
  plan back to the decision. Unsaved costs return to their input step. A full
  browser refresh restarts the UI sequence; confirmed data follows the existing
  server session lifetime (two hours inactivity or server restart).

## Automation shown honestly

Data validation, price arithmetic and decision rechecks run automatically.
Competitor collection requires configured supported product URLs and exact
matching; the selected product's source count is visible. No retailer URLs are invented.
Publishing a store price remains manual. The final page links to the price review
CSV, recorded execution and actual outcome review. A saved plan is not proof that
a shop's price changed. The evaluated ML lab remains a separate, disclosed tool.

## Homepage assets

Three distinct fictional editorial images were generated with the **built-in
image generation tool**, inspected and copied into the project:

- [Prepare product data](../design/homepage/journey-stock.png)
- [Compare offers](../design/homepage/journey-compare.png)
- [Review orders](../design/homepage/journey-review.png)

The [exact prompt set and tool provenance](../design/homepage/journey-prompts.json)
are retained. Each image has 640/960/1536 px WebP variants. Desktop scroll and
keyboard controls change the active photo and explanation together; mobile
chapters contain their own images. Reduced-motion settings remain supported.

## Verification

Python tests cover draft accounting/no writes, version/provenance checks, rejection
of hypothetical plans, conditional sales thresholds and owner context. Existing
tests exercise import, save, price-sheet export, execution and outcome review.
Node event/form fixtures cover gating, draft payloads, cost confirmation, stale
replies, candidate inputs, failed-update retry, evidence refresh, escaping and
homepage image switching. These are interaction tests, not rendered-browser tests.

The generated images were visually inspected. A browser layout/interaction pass
is still outstanding because local-browser access was previously denied by a
saved preference. That restriction has not been bypassed. Commercial usability
and pricing outcomes also need testing with a real shop. This version does not
claim production readiness or a public Render deployment.

Verified locally on 2026-09-28: **548 Python tests passed**, one optional legacy
Streamlit/PyArrow test skipped, and **70 Node tests passed**. A direct HTTP check
against the running 1.6.0 server used the actual client product-field helpers:
raising replacement cost by EUR 10 changed contribution from EUR 125.26 to
EUR 115.26; low visibility changed the action to visibility work; a EUR 435.53
candidate showed EUR 104.17 contribution and a requirement of 10 sales in 14 days.
The revised product, evidence-backed plan and price CSV saved successfully;
`published` remained false. This used an isolated test session, not visitor data.


## Continuous navigation and owner knowledge (1.7)

Welcome, Continue setup, Saved plans and secondary tools share a navigation bar.
The guided route records `#shop/1` through `#shop/5` in browser history. Returning
from Welcome resumes the reviewed step and restores the landing scroll position.
Future stages remain locked; edits invalidate dependent reviews. UI progress is
in memory, not durable storage: a full reload restarts the sequence.

At Market & customers, questions, hypotheses and dated owner observations have
an explicit basis. An observation requires a note describing its evidence. Each
of seven topics has a concrete collection suggestion and interpretation limit.
No trust, customer value or retention score is invented. Owners may mark a
question as a prerequisite; it pauses an otherwise eligible price test without
masking incomplete costs or unsafe-price checks. It can also remain context only.

Update finding edits the same note. Saved plans preserve its reviewed snapshot.
A completed linked action returns to the guided setup, carries the questions
forward and asks for current cost review before the owner updates their findings.
The previous plan stays unchanged. This does not identify a causal price effect.

Merchant products can connect exact competitor URLs in this stage. Entering the
stage refreshes configured sources for that SKU, at most once per five minutes
while navigating this setup; manual refresh is also available. There is no
unattended scheduler. Each seller's failure or dated observation remains visible.
Cache hits do not duplicate evidence; a product change during collection rejects
the stale observation atomically. Demo prices remain simulated. No real competitor
coverage was established by the fixture-based collector tests.

Verified on 2026-09-28 for 1.7: **553 Python tests passed**, one optional legacy
Streamlit/PyArrow test skipped, and **80 Node tests passed**. New checks cover
step/history state, resume, note editing and failed-update recovery, collection
scope/cache/partial failures, atomic version checks, and accounting consistency
when a candidate is paused. These are API/domain and controller-fixture checks.
**Rendered browser QA is still blocked by the saved website permission.**


A separate HTTP session against the running 1.7.0 server also completed this
workflow: EUR 449.00 watch -> EUR 435.53 candidate -> prerequisite question pauses
it -> action recorded -> dated finding retained as context -> candidate eligible
again with EUR 114.17 contribution and 10 required sales. The original action
snapshot stayed unchanged and the price review CSV exported. No shop price was
published and no real competitor URL was fetched. This was an API smoke check,
not a browser interaction test.
