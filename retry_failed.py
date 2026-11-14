import os, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parent
FAILED = ROOT / "content" / "failed"
PENDING = ROOT / "content" / "pending"
PENDING.mkdir(parents=True, exist_ok=True)
for f in FAILED.glob("*.html"):
    shutil.move(str(f), str(PENDING / f.name))
    print(f"Moved {f.name} back to pending.")
print("Retry reset complete.")
