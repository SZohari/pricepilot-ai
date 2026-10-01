# PythonAnywhere EU deployment candidate

Reviewed 2026-10-01. **Prepared, not deployed.** The owner requires a free account
without a payment card. Render's create-service API required payment information,
so it did not create a service. PythonAnywhere EU's Beginner signup form has no
payment fields, and its pricing page lists Beginner at EUR 0/month.

This route runs the existing FastAPI application. It does not replace the pricing
engine with a static mockup, and it does not require the owner's computer to stay on.
Actual account eligibility and a successful free ASGI deployment must still be
verified before sharing a demo link.

## Limits to check before announcing

- PythonAnywhere's ASGI hosting is experimental. Its documentation does not promise
  unchanged future pricing or API syntax. If setup requires payment, stop rather
  than upgrading.
- A new free account has one web app, one worker, 512 MiB of disk and a one-month
  web-app expiry. Check the displayed expiry and renew the app manually as required.
- Outbound Internet access is restricted. Arbitrary competitor collection cannot
  be promised on this host. The bundled replay uses clearly labelled simulated
  observations; no live retailer is preconfigured. Validate each supported source
  separately and report a restricted request as failed, never as a live price.
- Sessions remain disposable: two hours of inactivity or a process restart clears
  them. Use one application worker. Visitors can export their work.
- The free console CPU quota is separate from web-app requests. Avoid running the
  project's entire test suite in the hosting console; CI already covers it.

## Owner setup

1. Open [EU Beginner signup](https://eu.pythonanywhere.com/registration/register/beginner/).
   The owner enters their account details, chooses their password and accepts the
   terms themselves. Select Beginner, not a paid plan.
2. Sign in and open **Account → API token**. PythonAnywhere's documented ASGI CLI
   needs an API token. Create it in the account; keep it there. Do not paste it
   into chat, source code, a command argument or this document. A fresh hosting
   Bash console can use the token through PythonAnywhere's built-in environment.
3. Open a **Bash** console. Do not add a separate WSGI web app: this app uses ASGI.

## First deployment

Run these in the hosting Bash console, not Windows PowerShell. Use a fresh checkout
directory. If a directory or website already exists, inspect it first rather than
overwriting it or creating a duplicate. Python 3.13 is documented as available on
current PythonAnywhere systems; the project's CI passed on both 3.12 and 3.13.

```bash
git clone --depth 1 https://github.com/SZohari/pricepilot-ai.git ~/pricepilot-ai
python3.13 -m venv ~/.virtualenvs/pricepilot
~/.virtualenvs/pricepilot/bin/python -m pip install --no-cache-dir -r ~/pricepilot-ai/requirements-web.txt
~/.virtualenvs/pricepilot/bin/python -m pip check
~/.virtualenvs/pricepilot/bin/python -m pip install --no-cache-dir pythonanywhere
```

Set `PRICEPILOT_DOMAIN` to the **actual** account hostname. The example below is a
placeholder, not a published URL. Keep the escaped socket variable: PythonAnywhere
must expand it when starting the app, not while creating the website.

```bash
PRICEPILOT_DOMAIN='YOURUSERNAME.eu.pythonanywhere.com'
~/.virtualenvs/pricepilot/bin/pa website get
~/.virtualenvs/pricepilot/bin/pa website create --domain "$PRICEPILOT_DOMAIN" --command "env PRICEPILOT_PUBLIC_DEMO=1 PRICEPILOT_ALLOWED_HOSTS=$PRICEPILOT_DOMAIN $HOME/.virtualenvs/pricepilot/bin/python -m uvicorn --app-dir $HOME/pricepilot-ai --uds \${DOMAIN_SOCKET} --workers 1 src.web.app:app"
```

Do not set `PRICEPILOT_DB_PATH`: public mode refuses a merchant database. Public
mode enables secure session cookies, so use HTTPS. The exact hostname is allowed;
there is no need for a wildcard. FastAPI serves its own local CSS, JavaScript,
images and fonts; the ASGI platform's missing static mappings are not required.

## Verify the result

Confirm the hosting API reports a running site, then check its real HTTPS URL:

- `/health` returns the expected application and version.
- The welcome page, fonts and all scroll images load.
- Opening the shop and returning to Welcome preserves progress; browser Back works.
- A cost edit changes the preview; confirming it changes the saved calculation.
- A different private browser session has independent demo data.
- The market step identifies simulated offers. No restricted request appears as live.
- A reviewed plan saves and exports. Resetting one session does not affect another.
- The owner can see how to renew the free app before its displayed expiry.

Only then add the verified URL to the README and LinkedIn draft. A successful
local check or hosting command alone is not proof that this workflow works online.

## Updates

After a reviewed commit is pushed and CI passes, inspect the hosting checkout for
local changes, then use `git pull --ff-only`. If dependencies changed, install the
web requirements again before reloading:

```bash
~/.virtualenvs/pricepilot/bin/pa website reload --domain "$PRICEPILOT_DOMAIN"
```

Reloading clears in-memory demo sessions. Run the public checks again after an
update. GitHub pushes do not automatically deploy this host.

## Official references

- [EU plans and pricing](https://eu.pythonanywhere.com/pricing/)
- [Free account limits](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/)
- [ASGI / FastAPI deployment](https://help.pythonanywhere.com/pages/ASGICommandLine/)
- [API-token setup](https://help.pythonanywhere.com/pages/GettingYourAPIToken/)
- [Python versions and environments](https://help.pythonanywhere.com/pages/InstallingNewModules/)
