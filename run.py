"""Start PricePilot's browser UI. No Streamlit, Node or build command is required."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import threading
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
# Local readiness checks must not be sent through a system HTTP proxy.
LOCAL_HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def prepare_dependencies():
    # Optional local fallback: reuse pure-Python web packages already in this project.
    # Existing interpreter packages always take precedence over the old environment.
    if not all(importlib.util.find_spec(name) for name in ("fastapi", "uvicorn", "pydantic", "numpy")):
        legacy = ROOT / ".venv" / "Lib" / "site-packages"
        if legacy.is_dir():
            sys.path.append(str(legacy))
    try:
        import fastapi
        import uvicorn
        import pydantic
        import numpy
    except (ImportError, OSError) as exc:
        raise SystemExit(
            "Web dependencies are missing or incompatible. Install Python 3.12, then run:\n"
            "  python -m pip install -r requirements-web.txt\n"
            "  python run.py\n"
            f"Details: {exc}"
        ) from exc


def open_when_ready(url):
    for _ in range(60):
        try:
            with LOCAL_HTTP.open(url + "/health", timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except OSError:
            time.sleep(.5)


def main():
    parser = argparse.ArgumentParser(description="Start the PricePilot dashboard")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    prepare_dependencies()
    import uvicorn
    url = f"http://127.0.0.1:{args.port}"
    try:
        with LOCAL_HTTP.open(url + "/health", timeout=1) as response:
            running = json.load(response).get("service") == "PricePilot Web"
        if running:
            print(f"PricePilot is already running at {url}", flush=True)
            if not args.no_browser:
                webbrowser.open(url)
            return
    except (OSError, ValueError):
        pass
    print(f"\nPricePilot is starting at {url}\nKeep this terminal open. Press Ctrl+C to stop.\n", flush=True)
    if not args.no_browser:
        threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()
    uvicorn.run("src.web.app:app", host="127.0.0.1", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
