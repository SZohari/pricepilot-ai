"""Serving and archive checks for the self-contained editorial homepage."""
from pathlib import Path
from zipfile import ZipFile
import re
import pytest
from fastapi.testclient import TestClient
from src.web.app import create_app
from scripts.package_web_demo import package

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "src/web/static"

@pytest.fixture
def homepage_client(monkeypatch):
    monkeypatch.delenv("PRICEPILOT_DB_PATH", raising=False)
    with TestClient(create_app()) as client:
        yield client

def test_self_hosted_fonts_are_complete_and_match_the_stylesheet(homepage_client):
    css = homepage_client.get("/static/fonts.css").text
    fonts = re.findall(r"url\('\./([^']+\.woff2)'\)", css)
    assert len(fonts) == 6
    for font in fonts:
        response = homepage_client.get("/static/" + font)
        assert response.status_code == 200
        assert "font/woff2" in response.headers["content-type"]
        assert response.content[:4] == b"wOF2"
        assert int.from_bytes(response.content[8:12], "big") == len(response.content)
    assert "https:" not in css
    assert (STATIC / "assets/fonts/newsreader-OFL.txt").read_text().startswith("Copyright")
    assert "SIL OPEN FONT LICENSE" in (STATIC / "assets/fonts/manrope-OFL.txt").read_text()

def test_every_responsive_photo_is_served_complete_and_under_budget(homepage_client):
    for name in ("design-store", "portrait-studio", "cycle-workshop", "watch-packing", "watch-details", "journey-stock", "journey-compare", "journey-review"):
        for width in (640, 960, 1536):
            response = homepage_client.get(f"/static/assets/images/{name}-{width}.webp")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("image/webp")
            assert response.content[:4] == b"RIFF" and response.content[8:12] == b"WEBP"
            assert int.from_bytes(response.content[4:8], "little") + 8 == len(response.content)
            assert len(response.content) < 160_000
    page = homepage_client.get("/").text
    assert '/static/homepage.css' in page and '/static/fonts.css' in page
    for path in ("homepage.js", "homepage.css", "journey.js", "journey.css"):
        assert homepage_client.get("/static/" + path).status_code == 200

def test_public_archive_contains_every_served_asset_and_both_licenses():
    with ZipFile(package()) as archive:
        names = set(archive.namelist())
        for asset in (STATIC / "assets").rglob("*"):
            if asset.is_file() and asset.suffix in (".woff2", ".webp", ".txt"):
                assert asset.relative_to(ROOT).as_posix() in names
        assert len([name for name in names if name.endswith('.webp')]) == 24
        assert len([name for name in names if name.endswith('.woff2')]) == 6
        assert "src/web/static/homepage.js" in names
        assert not any(name.startswith("design/") or name.endswith((".db", ".sqlite", ".env")) for name in names)
