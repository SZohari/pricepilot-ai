"""Vendor the official Latin variable WOFF2 builds; no font CDN at runtime."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FONTS = {
    "manrope-latin.woff2": "manrope/v20/xn7gYHE41ni1AdIRggexSg.woff2",
    "manrope-latin-ext.woff2": "manrope/v20/xn7gYHE41ni1AdIRggmxSuXd.woff2",
    "newsreader-latin.woff2": "newsreader/v26/cY9VfjOCX1hbuyalUrK49dLac06G1ZGsZBtoBAbNJYQ.woff2",
    "newsreader-latin-ext.woff2": "newsreader/v26/cY9VfjOCX1hbuyalUrK49dLac06G1ZGsZBtoBAbDJYQraA.woff2",
    "newsreader-italic-latin.woff2": "newsreader/v26/cY9XfjOCX1hbuyalUrK439vogqC9yFZCYg7oRZaLFYYzbA.woff2",
    "newsreader-italic-latin-ext.woff2": "newsreader/v26/cY9XfjOCX1hbuyalUrK439vogqC9yFZCYg7oRZaLFYgzbBZD.woff2",
}
def download(item):
    name, source = item
    folder = ROOT / "src/web/static/assets/fonts"
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / name
    if not destination.exists():
        temporary = destination.with_suffix(".part")
        subprocess.run(["curl", "-fsSL", "--retry", "2", "--connect-timeout", "10", "--max-time", "25",
                        "-o", str(temporary), "https://fonts.gstatic.com/s/" + source], check=True)
        data = temporary.read_bytes()
        if data[:4] != b"wOF2" or int.from_bytes(data[8:12], "big") != len(data):
            raise ValueError("Incomplete WOFF2 font: " + name)
        temporary.replace(destination)
    print(name, destination.stat().st_size, flush=True)

if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(download, FONTS.items()))
