import os, sys, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import safe_batch

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / "os_env" / "Scripts" / "python.exe"

def main():
    pending = sorted(safe_batch.PENDING_DIR.glob("*.html"))
    if not pending:
        print("No pending posts.")
        return
    # process first pending by calling safe_batch.process_post but capture post id? safe_batch doesn't return id.
    # Instead run safe_batch for one? It processes all. Keep simple: process first via safe_batch module by monkey? 
    print("run_engine: delegating to safe_batch for all pending")
    subprocess.run([str(PYTHON), str(ROOT / "safe_batch.py")], cwd=str(ROOT))

if __name__ == "__main__":
    main()
