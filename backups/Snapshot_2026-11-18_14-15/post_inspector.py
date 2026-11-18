import sys
import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import os, sys, glob
from pathlib import Path
from bs4 import BeautifulSoup
ROOT = Path(r"D:\Projects\AutoPilot_OS_v2")
PENDING = ROOT / "content" / "pending"

def inspect_file(fp):
    soup = BeautifulSoup(fp.read_text(encoding="utf-8"), "html.parser")
    critical = []
    warnings = []

    # SEO
    title = soup.find("title")
    if not title or not (30 <= len(title.get_text(strip=True)) <= 65):
        critical.append("title length invalid/missing")
    meta = soup.find("meta", attrs={"name": "description"})
    if not meta or not meta.get("content") or not (120 <= len(meta["content"]) <= 160):
        critical.append("meta description invalid/missing")
    h1s = soup.find_all("h1")
    if len(h1s) != 1:
        critical.append(f"h1 count={len(h1s)} (need 1)")
    if len(soup.find_all("h2")) < 2:
        critical.append("need at least 2 h2")
    # Images
    imgs = soup.find_all("img")
    if len(imgs) == 0:
        critical.append("no images found")
    elif len(imgs) != 7:
        warnings.append(f"image count={len(imgs)} (auto-image posts need 7)")
    for im in imgs:
        if not im.get("alt"):
            warnings.append("img missing alt")
    # Jump break
    if "<!--more-->" not in str(soup):
        warnings.append("missing <!--more-->")
    # Length
    words = len(soup.get_text(" ").split())
    if words < 300:
        critical.append(f"word count {words} < 300")
    # Interlinking
    internal = [a for a in soup.find_all("a", href=True) if "dustanddynasty.blogspot.com" in a["href"]]
    if len(internal) < 2:
        warnings.append(f"internal links={len(internal)} (need 2)")
    empty = [a for a in soup.find_all("a", href=True) if a["href"].strip() == ""]
    if empty:
        critical.append("empty href found")

    if critical:
        print(f"[CRITICAL] {fp.name} will crash AutoPilot ({'; '.join(critical)})")
    elif warnings:
        print(f"[WARNING] {fp.name} passed but has minor issues ({'; '.join(warnings)})")
    else:
        print(f"[PASS] {fp.name} is ready for AutoPilot.")

def main():
    files = sorted(PENDING.glob("*.html"))
    if not files:
        print("No pending posts.")
        return
    for f in files:
        inspect_file(f)

if __name__ == "__main__":
    main()
