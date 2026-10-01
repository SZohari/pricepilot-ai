"""Copy generated originals and vendor the OFL fonts used by the homepage.

Run once after generating the three editorial photographs. This is a local
design utility, not a server startup dependency.
"""
from pathlib import Path
from shutil import copy2
from urllib.request import urlopen
from urllib.error import URLError
import base64
import json

ROOT = Path(__file__).resolve().parents[1]
GENERATED = Path.home() / ".codex/generated_images/01a0dd33-8faf-7762-91b9-8e6246247597"
ORIGINALS = {
    "design-store": "exec-d8cb65ab-5d76-4baa-8800-a1d7d8c432eb.png",
    "portrait-studio": "exec-933631ce-dde6-47d7-a189-311dde226d03.png",
    "cycle-workshop": "exec-2c115a89-c0ae-43b0-93dc-88a35b5bf955.png",
}
FONTS = {
    "manrope-variable.ttf": "manrope/Manrope%5Bwght%5D.ttf",
    "newsreader-variable.ttf": "newsreader/Newsreader%5Bopsz%2Cwght%5D.ttf",
    "newsreader-italic-variable.ttf": "newsreader/Newsreader-Italic%5Bopsz%2Cwght%5D.ttf",
    "manrope-OFL.txt": "manrope/OFL.txt",
    "newsreader-OFL.txt": "newsreader/OFL.txt",
}

if __name__ == "__main__":
    originals = ROOT / "design/homepage"
    originals.mkdir(parents=True, exist_ok=True)
    fonts = ROOT / "src/web/static/assets/fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    source_fonts = originals / "fonts"
    source_fonts.mkdir(exist_ok=True)
    for name, filename in ORIGINALS.items():
        copy2(GENERATED / filename, originals / f"{name}.png")
    for name, source in FONTS.items():
        destination = (source_fonts if name.endswith(".ttf") else fonts) / name
        if not destination.exists():
            try:
                with urlopen("https://raw.githubusercontent.com/google/fonts/main/ofl/" + source, timeout=12) as response:
                    data = response.read()
            except (URLError, TimeoutError):
                with urlopen("https://api.github.com/repos/google/fonts/contents/ofl/" + source, timeout=20) as response:
                    record = json.load(response)
                if record.get("encoding") != "base64":
                    raise ValueError("Font API did not return file content")
                data = base64.b64decode(record["content"])
            destination.write_bytes(data)
        print(name, destination.stat().st_size)
