import os
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- CONFIGURATION ---
PROJECT_DIR = r"D:\Projects\AutoPilot_OS_v2"
DEBOUNCE_SECONDS = 60  # Wait 60 seconds after the last change before committing
IGNORE_DIRS = {'.git', 'os_env', '__pycache__', 'content', 'logs', 'backups', 'reports', 'image_audits', 'pattern_audits'}

class GitAutoSync(FileSystemEventHandler):
    def __init__(self):
        self.last_modified = time.time()
        self.timer_running = False

    def on_modified(self, event):
        if event.is_directory:
            return
        # Ignore files in ignored directories
        if any(ignored in event.src_path for ignored in IGNORE_DIRS):
            return
        self.last_modified = time.time()
        if not self.timer_running:
            self.timer_running = True
            import threading
            threading.Thread(target=self.auto_commit, daemon=True).start()

    def auto_commit(self):
        while True:
            time.sleep(5)
            # Wait for the debounce period to pass without any new changes
            if time.time() - self.last_modified > DEBOUNCE_SECONDS:
                break

        try:
            # Check if there are actual changes
            status = subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT_DIR, capture_output=True, text=True)
            if not status.stdout.strip():
                self.timer_running = False
                return  # No changes, exit

            print("\n[Auto-Sync] Changes detected. Committing and pushing...")
            subprocess.run(["git", "add", "."], cwd=PROJECT_DIR, check=True)
            
            # Commit (This will trigger Gitleaks!)
            commit_msg = f"Auto-commit: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            commit = subprocess.run(["git", "commit", "-m", commit_msg], cwd=PROJECT_DIR, capture_output=True, text=True)
            
            if commit.returncode != 0:
                print("[Auto-Sync] Commit blocked! (Did Gitleaks find a secret?)")
                print(commit.stdout)
                print(commit.stderr)
            else:
                print("[Auto-Sync] Commit successful. Pushing to GitHub...")
                subprocess.run(["git", "push"], cwd=PROJECT_DIR, check=True)
                print("[Auto-Sync] Push complete!")
                
        except subprocess.CalledProcessError as e:
            print(f"[Auto-Sync] Git command failed: {e}")
        
        self.timer_running = False

if __name__ == "__main__":
    event_handler = GitAutoSync()
    observer = Observer()
    observer.schedule(event_handler, PROJECT_DIR, recursive=True)
    observer.start()
    print(f"👀 Auto-Sync active. Watching {PROJECT_DIR}...")
    print(f"Will commit and push {DEBOUNCE_SECONDS} seconds after you stop saving.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
