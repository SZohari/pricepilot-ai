"""Create a minimal public-demo source archive; never includes local data or secrets."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]

def package():
    selected=["run.py","requirements-web.txt","Dockerfile","render.yaml","README.md",
              "src/api/v1.py","src/api/intelligence.py","src/api/advisor.py","src/api/retail.py","data/scenarios/germany_wearables/demo.json",
              "config/price_sources.example.json","docs/LIVE_COLLECTION.md","docs/ONLINE_DEMO.md","docs/LAUNCH_KIT.md","docs/PYTHONANYWHERE.md","docs/READINESS_REVIEW.md",
              "docs/MODEL_CARD.md","docs/PRODUCT_STRATEGY.md","docs/CORE_UPGRADE.md","docs/GUIDED_PRICING.md","docs/PRICING_CONSULTANT.md","docs/ECONOMIC_FOUNDATIONS.md","docs/HOMEPAGE_DESIGN.md","docs/RETAIL_DECISION_SYSTEM.md","docs/GUIDED_SETUP.md","docs/APPLICATION_NARRATIVE.md","RUN_ME_FA.md"]
    for folder in ("src/web","src/domain","src/application","src/infrastructure"):
        selected.extend(str(p.relative_to(ROOT)) for p in (ROOT/folder).rglob("*")
                        if p.is_file() and "__pycache__" not in p.parts and p.suffix in (".py",".js",".css",".html",".svg"))
    for name in ("src/__init__.py","src/api/__init__.py"):
        if (ROOT/name).exists(): selected.append(name)
    assets = ROOT / "src/web/static/assets"
    selected.extend(str(p.relative_to(ROOT)) for p in assets.rglob("*")
                    if p.is_file() and (p.suffix in (".webp", ".jpg", ".woff2") or p.name.endswith("-OFL.txt")))
    screenshots = ROOT / "docs/screenshots"
    selected.extend(str(p.relative_to(ROOT)) for p in screenshots.glob("*.jpg") if p.is_file())
    destination=ROOT/"dist/pricepilot-public-demo.zip"
    destination.parent.mkdir(exist_ok=True)
    with ZipFile(destination,"w",ZIP_DEFLATED) as archive:
        for name in sorted(set(selected)):
            archive.write(ROOT/name,Path(name).as_posix())
    return destination

if __name__=="__main__":
    print(package())
