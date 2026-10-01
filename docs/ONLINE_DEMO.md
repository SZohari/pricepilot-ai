# A public, install-free MVP

The repository includes a Render Blueprint (`render.yaml`) and a minimal Docker image. **These are deployment configuration, not an already published URL.** The current implementation was pushed to GitHub on 2026-10-01, and its GitHub Actions checks passed. Public hosting is still pending.

The owner requires free hosting without a payment card. Creating a Render **Free** service in the confirmed workspace returned HTTP 402, requiring payment information. No service was created and no paid resource was enabled. The next candidate is [PythonAnywhere's free EU account](PYTHONANYWHERE.md); its FastAPI hosting is experimental and must pass a real deployment before a public link is announced.

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

No public deployment has succeeded, no paid service was purchased and no retailer credentials are required for the replay example.

The current remote is `https://github.com/SZohari/pricepilot-ai.git`. The 1.7
implementation was published on `main` in commit `2471663` on 2026-10-01.
[GitHub Actions passed](https://github.com/SZohari/pricepilot-ai/actions/runs/36871521121).
GitHub authentication and the Render connection now work; the outstanding Render
blocker is its payment-information requirement, not repository access.
Auto-deploy is intentionally off for the initial release: deploy the reviewed
commit manually, then verify `/health`, the welcome/setup/return flow and a saved
plan on the public URL. An update to GitHub alone does not update this service.
Publishing can be automated later after the repository's CI has run successfully.

The local `127.0.0.1` URL is only usable on the owner's machine while the local
server runs. Share the assigned HTTPS public URL with employers after verification.
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
hosting provider's Linux build and rendered public workflow are still unverified.
Local regression checks passed: 553 Python tests (one optional legacy test skipped)
and 80 JavaScript tests. These are not a substitute for using the deployed interface.
