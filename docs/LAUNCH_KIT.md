# PricePilot launch kit

Prepared 2026-10-01. This is a draft, not a published announcement. The public
workflow has been checked and the live link below is ready to use.

## LinkedIn post — English

Would lowering a price actually help this business?

I built PricePilot to explore that question through a working pricing decision,
from the business inputs to an action the owner can review.

The demo follows a fictional German smartwatch retailer. You can change supplier
costs, inspect competitor evidence, record what customers are saying, and compare
a proposed price with the sales it would need to justify the change.

One design choice matters to me: sometimes the next useful action is to clarify
a warranty, improve visibility or collect missing evidence before testing a price.
The software should make those gaps visible too.

Under the hood:

- Python/FastAPI, validated imports and traceable decision records.
- An exact-product competitor collector for supported, configured URLs.
- A separate trained demand model, evaluated on later data against simple
  baselines, including an example where a demand shock makes it fail.

The pricing workflow uses explicit accounting and decision rules. The ML model
does not claim to discover an optimal price. The demo's business data is synthetic;
real merchant validation is the next step.

Try the interactive demo: https://sepas.eu.pythonanywhere.com/
Explore the code: https://github.com/SZohari/pricepilot-ai

I'm exploring opportunities at the intersection of data, applied AI and business
in Germany. I'd welcome feedback from people building decision tools or working
with retail pricing: what evidence would you need before trying a new price?

#AppliedAI #DataScience #Python #RetailAnalytics

## 60–75 second recording

Record the real interface after a rendered-browser check. Keep the demo label
visible. Do not edit fake outcomes into the recording or use historical Iran UI
screenshots as if they showed this release.

| Time | Show | Explain |
| --- | --- | --- |
| 0–7 s | Brief welcome scroll; open the watch shop | A pricing decision from inputs to follow-up |
| 7–20 s | Select the default watch; change replacement cost by EUR 10 | The amount left per order updates; costs constrain a decision |
| 20–34 s | Confirm costs; inspect market and customer context | Competitor listings and the owner's knowledge have different sources |
| 34–49 s | Compare a small price change and the required sales | Required sales are a condition, not a demand forecast |
| 49–62 s | Save the reviewed plan; show its next action | The plan is traceable; publishing a shop price stays with the owner |
| 62–75 s | Briefly show the demand model evaluation | ML is evaluated separately; failure and synthetic data remain visible |

Before recording, restore the demo to a clean state and rehearse once. The demo
price, edited costs and sales threshold must all come from the current screen;
do not reuse numbers from a different scenario. Avoid showing account, email or
workspace-token details. Start the public service before recording if it has slept.

## Publication status

- Source remote: `https://github.com/SZohari/pricepilot-ai.git`.
- Implementation pushed to `main` in `2471663`; its GitHub Actions run passed.
  The subsequent deployment-documentation commit `0fa2605` also passed CI.
- Public service: https://sepas.eu.pythonanywhere.com/ on PythonAnywhere EU,
  Beginner (free), Python 3.13.1, one worker, public-demo mode, HTTPS.
- Local app: 1.7.0. Startup requires the local process to remain running.
- A fresh Python 3.12.14 installation of the web dependencies and public-mode
  application/calculation smoke check passed on 2026-10-01. The actual Linux host's
  dependency check and the public browser workflow then passed too.
- Render's create-service API rejected the Free request with HTTP 402 (payment
  information required). No Render service or paid resource was created.
  PythonAnywhere's free deployment succeeded. See [setup and limits](PYTHONANYWHERE.md).
- Local regression checks: 553 Python tests passed, one optional legacy test
  skipped; 80 JavaScript tests passed. No commercial outcome is implied.
- The public browser audit covered cost changes, Welcome/Back navigation,
  context-dependent advice, saving a plan, CSV download and both ML examples.
  Separate visitor data and protected API writes were also checked.
- The public page's social preview uses an actual screenshot. The site is an MVP;
  live competitor coverage and merchant ROI have not been established.
- No LinkedIn post or video has been published by this release task.
