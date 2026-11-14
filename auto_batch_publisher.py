import os
import sys
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from sanitize_html import sanitize_post_html

PYTHON = ROOT / "os_env" / "Scripts" / "python.exe"
PENDING = ROOT / "content" / "pending"


def sanitize_pending_posts():
    """Ensure all pending posts are SEO-compliant before batch processing."""
    pending_files = sorted(PENDING.glob("*.html"))
    if not pending_files:
        print("[auto_batch] No pending HTML posts found.")
        return []

    print(f"[auto_batch] Auditing and sanitizing {len(pending_files)} pending post(s)...")
    for f in pending_files:
        try:
            content = f.read_text(encoding="utf-8")
            sanitized = sanitize_post_html(content)
            if sanitized != content:
                f.write_text(sanitized, encoding="utf-8")
                print(f"  [SEO Sanitized] {f.name}")
        except Exception as e:
            print(f"  [ERROR] Failed to sanitize {f.name}: {e}", file=sys.stderr)

    return pending_files


def main():
    pending_files = sanitize_pending_posts()
    if not pending_files:
        return

    print(f"\nFound {len(pending_files)} pending posts. Starting batch...")
    for i in range(len(pending_files)):
        print(f"\n=== Batch run {i+1}/{len(pending_files)} ===")
        subprocess.run([str(PYTHON), str(ROOT / "run_engine.py")], cwd=str(ROOT))
        time.sleep(2)
    print(f"\nBatch complete! Processed {len(pending_files)} posts.")


if __name__ == "__main__":
    main()
