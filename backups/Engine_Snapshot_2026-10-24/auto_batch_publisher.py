import os, sys, subprocess, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / "os_env" / "Scripts" / "python.exe"
PENDING = ROOT / "content" / "pending"

pending_files = sorted(PENDING.glob("*.html"))
print(f"Found {len(pending_files)} pending posts. Starting batch...")
for i in range(len(pending_files)):
    print(f"\n=== Batch run {i+1}/{len(pending_files)} ===")
    subprocess.run([str(PYTHON), str(ROOT / "run_engine.py")], cwd=str(ROOT))
    time.sleep(2)
print(f"\nBatch complete! Processed {len(pending_files)} posts.")
