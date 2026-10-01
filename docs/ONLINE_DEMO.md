# A public, install-free MVP

**Live demo: [sepas.eu.pythonanywhere.com](https://sepas.eu.pythonanywhere.com/).**
Published and checked on 2026-10-01 using PythonAnywhere EU's free account, without
a payment card. The site runs independently of the owner's computer. Visitors
need no installation or account.

The owner requires free hosting without a payment card. Creating a Render **Free**
service returned HTTP 402, requiring payment information; no Render service or paid
resource was created. [PythonAnywhere setup](PYTHONANYWHERE.md) records the working
alternative and its limits. Its ASGI hosting is experimental, outbound Internet is
restricted, and free accounts have finite resources. This is a portfolio demo,
not a promise of production uptime or unrestricted competitor collection.

## Current deployment

The existing FastAPI app runs on Python 3.13.1 with one Uvicorn worker and
PythonAnywhere's Unix domain socket. Set `PRICEPILOT_PUBLIC_DEMO=1` and allow only
the exact public hostname using `PRICEPILOT_ALLOWED_HOSTS`. The startup executable
must use its absolute path: `/usr/bin/env`, not bare `env`. `pip check` passed on
the Linux host. The required web packages and the official hosting CLI are the
only packages installed in this project's hosting environment.

The public welcome screenshot used for link previews is an unedited capture of
the real deployed page. The scene in that page is an AI-generated illustration,
not a photograph of a merchant using the product.

## Render path

1. Push this reviewed project to a repository you control.
2. In Render, create a Blueprint using that repository and its `render.yaml`.
3. Review the free web-service configuration (Frankfurt, Python, one worker) and deploy. The public link is the service's assigned `onrender.com` address.
4. If you select another hosting plan, review its price before confirming.

Render provides `RENDER_EXTERNAL_HOSTNAME`; the app adds that exact hostname to its host allowlist. HTTPS cookies are enabled by `PRICEPILOT_PUBLIC_DEMO=1`. The application refuses a persistent merchant database in public demo mode.

Visitors need only the link. Each browser starts in a preloaded, isolated Kiez & Co. demo without registration. They can run the example, inspect explanations, edit demo data and experiment. Sessions are in-memory and expire after two hours of inactivity or a restart. Export preserves their data; this is not account storage.

Use **one worker** with this in-memory session implementation. Scaling to multiple workers requires shared session/storage infrastructure. The app bounds request size and session count, but a public MVP still has finite capacity. Free services may sleep when idle, so first access may be slower. A custom domain is optional.

## Live updates

The browser reads streamed collection events and recalculates recommendations after completion. Optional five-minute checks run while the tab is visible. For actual competitors, configure sources as described in [LIVE_COLLECTION.md](LIVE_COLLECTION.md). Do not expose a private retailer database through the public demonstration.

The PythonAnywhere public deployment succeeded. No paid service was purchased and
no retailer credentials are required for the replay example.

The current remote is `https://github.com/SZohari/pricepilot-ai.git`. The 1.7
implementation was published on `main` in commit `2471663` on 2026-10-01.
[GitHub Actions passed](https://github.com/SZohari/pricepilot-ai/actions/runs/36871521121).
GitHub authentication works. The Render configuration remains available as an
alternative, but that account's payment-information requirement was not accepted.
Auto-deploy is intentionally off for the initial release: deploy the reviewed
commit manually, then verify `/health`, the welcome/setup/return flow and a saved
plan on the public URL. An update to GitHub alone does not update this service.
Publishing can be automated later after the repository's CI has run successfully.

The local `127.0.0.1` URL is only usable on the owner's machine while the local
server runs. Share the HTTPS public URL above with employers.
The proposed announcement and screen-recording sequence are in [LAUNCH_KIT.md](LAUNCH_KIT.md).

`python scripts/package_web_demo.py` creates `dist/pricepilot-public-demo.zip`, a minimal source bundle for transferring the MVP. It includes only the web application, shared pricing modules and synthetic catalog, excluding local workspaces, original merchant CSVs, environment files, Git history and credentials. It is a deployment source package, not a published service.

The free plan can sleep after 15 minutes of inactivity and take approximately one minute to resume. Demo sessions are disposable and reset on restarts. Do not add a paid database or upgrade the compute plan for this portfolio example. See [Render free-plan limits](https://render.com/docs/free).

Official instructions: [Deploy FastAPI](https://render.com/docs/deploy-fastapi), [Blueprint reference](https://render.com/docs/blueprint-spec).

## Release verification — 2026-10-01

The four pinned web dependencies installed successfully from PyPI into a fresh,
ignored Python 3.12.14 Windows environment. `pip check` passed. With only those
dependencies, public-mode application import, OpenAPI generation and the default
watch's EUR 435.53 candidate calculation passed (10 required sales). This did not
reuse the project's old `.venv`. It verifies the web dependency set locally; the
hosting provider's Linux installation and public workflow were then checked too.
Local regression checks passed: 553 Python tests (one optional legacy test skipped)
and 80 JavaScript tests. These are not a substitute for using the deployed interface.

### Checks on the actual public service

- HTTPS `/health` returned HTTP 200 and application version 1.7.0.
- The welcome page loaded its local images and fonts. The five-step workflow was
  completed through a saved plan and downloaded price-review CSV.
- Raising replacement cost from EUR 240 to EUR 250 changed contribution from
  EUR 125.26 to EUR 115.26 and the chosen-margin price floor to EUR 344.16.
- Returning to Welcome offered **Continue my pricing setup**; browser Back kept
  the EUR 250 draft. Confirming the inputs saved the change.
- Reporting low visibility changed the next action to improving visibility;
  explicit price objections enabled a bounded price-test recommendation.
- A EUR 435.53 candidate with the edited cost required 10 sales over 14 days.
  The exported CSV matched the page and correctly said `published=false`.
- Independent API clients retained separate products after one was edited;
  test inputs were restored. Session cookies were Secure, and a write without a
  workspace token was rejected. No account token was copied out of the host.
- Both ML examples ran on the live server: stable synthetic MAE 1.96 versus
  best baseline 3.29; demand-shock MAE 5.88 versus baseline 2.99. The failed
  comparison was clearly displayed. These are synthetic results, not merchant ROI.
- The plan layout was inspected at a 390-pixel viewport; the normal viewport was
  restored. Browser logs showed no application warnings or errors during the flow.

No live competitor coverage, shop-price publication, measured merchant outcome or
long-term uptime was established by these checks. The earlier local-browser access
restriction remains separate from this successful public-browser audit.
