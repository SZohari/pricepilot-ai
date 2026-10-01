# PricePilot launch kit

Published 2026-10-01 from Sepas Zohari's LinkedIn profile, with public visibility.
[View the announcement](https://www.linkedin.com/feed/update/urn:li:activity:7511459294463193088/).

## LinkedIn post — English

The final publication copy is in [LINKEDIN_POST.txt](LINKEDIN_POST.txt).

Prepared attachments, in order:

1. [Pricing decision](screenshots/pricing-decision.jpg).
2. [Demand model evaluation](screenshots/demand-evaluation.jpg).
3. [Welcome page](../src/web/static/assets/images/pricepilot-preview.jpg).

These are real interface screenshots. LinkedIn confirmed successful publication
with all three attachments. The post identifies the business data as simulated
and links to the public demo and GitHub repository. No paid promotion was enabled.

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
- The English LinkedIn announcement was published with three screenshots on
  2026-10-01; the direct link is at the top of this document. No video has been
  recorded or published by this release task.
