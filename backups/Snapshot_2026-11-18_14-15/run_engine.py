import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import safe_batch

ROOT = Path(__file__).resolve().parent

def main():
    pending = sorted(safe_batch.PENDING_DIR.glob("*.html"))
    if not pending:
        print("No pending posts.")
        return
    print(f"run_engine: processing {len(pending)} pending posts via safe_batch")
    safe_batch.main()

if __name__ == "__main__":
    main()
