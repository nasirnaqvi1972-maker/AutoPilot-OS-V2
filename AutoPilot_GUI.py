# -*- coding: utf-8 -*-
import os
import sys

os.environ["PYTHONIOENCODING"] = "utf-8"
import threading
import subprocess
import datetime
import tkinter as tk
from tkinter import ttk, messagebox

# --- CONFIGURATION ---
V2_ROOT = r"D:\Projects\AutoPilot_OS_v2"
LOG_DIR = os.path.join(V2_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
PYTHON_EXE = os.path.join(V2_ROOT, "os_env", "Scripts", "python.exe")

class AutoPilotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AutoPilot OS V2 - Control Center")
        self.root.geometry("900x600")
        self.root.configure(bg="#2b2b2b")

        # Styling
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=5)
        style.configure("TLabel", background="#2b2b2b", foreground="white", font=("Segoe UI", 12))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#4CAF50")

        # Header
        ttk.Label(self.root, text="AutoPilot OS V2 Control Center", style="Header.TLabel").pack(pady=10)

        # Main Layout: Left for buttons, Right for logs
        main_frame = tk.Frame(self.root, bg="#2b2b2b")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        btn_frame = tk.Frame(main_frame, bg="#2b2b2b", width=250)
        btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        log_frame = tk.Frame(main_frame, bg="#2b2b2b")
        log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # --- BUTTONS ---
        ttk.Label(btn_frame, text="Operations", style="TLabel").pack(pady=(0, 10))

        self.btn_publish = ttk.Button(btn_frame, text="🚀 Publish Next Draft", command=lambda: self.run_script("Publisher", "run_engine.py"))
        self.btn_publish.pack(fill=tk.X, pady=5)

        self.btn_inspect = ttk.Button(btn_frame, text="Inspect Pending Posts", command=lambda: self.run_script("Inspector", "post_inspector.py"))
        self.btn_inspect.pack(fill=tk.X, pady=5)

        self.btn_doctor = ttk.Button(btn_frame, text="Inspect & Fix Blogger Drafts", command=lambda: self.run_script("DraftDoctor", "draft_doctor.py"))
        self.btn_doctor.pack(fill=tk.X, pady=5)

        self.btn_auto = ttk.Button(btn_frame, text="⚡ Auto Post (All Pending)", command=lambda: self.run_script("Auto_Batch", "auto_batch_publisher.py"))
        self.btn_auto.pack(fill=tk.X, pady=5)

        self.btn_retry = ttk.Button(btn_frame, text="♻️ Retry Failed Posts", command=lambda: self.run_script("Retry_Failed", "retry_failed.py"))
        self.btn_retry.pack(fill=tk.X, pady=5)

        ttk.Label(btn_frame, text="Post ID:", style="TLabel").pack(anchor=tk.W, pady=(10,0))
        self.post_id_entry = ttk.Entry(btn_frame)
        self.post_id_entry.pack(fill=tk.X, pady=5)
        self.btn_republish = ttk.Button(btn_frame, text="🔄 Fetch & Republish", command=lambda: self.run_script("Republish", "republish_post.py", [self.post_id_entry.get().strip()]))
        self.btn_republish.pack(fill=tk.X, pady=5)

        self.btn_pull = ttk.Button(btn_frame, text="Pull All Blogger Drafts", command=lambda: self.run_script("PullDrafts", "pull_all_drafts.py"))
        self.btn_pull.pack(fill=tk.X, pady=5)

        self.btn_smart = ttk.Button(btn_frame, text="Smart Replace Images", command=lambda: self.run_script("SmartReplace", "smart_image_replacer.py", [self.post_id_entry.get().strip()]))
        self.btn_smart.pack(fill=tk.X, pady=5)

        self.btn_seo = ttk.Button(btn_frame, text="📊 Run SEO Auditor", command=lambda: self.run_script("SEO_Auditor", "seo/seo_optimizer.py"))
        self.btn_seo.pack(fill=tk.X, pady=5)

        self.btn_repair = ttk.Button(btn_frame, text="🔧 Repair Links (Live)", command=lambda: self.run_script("Link_Repair", "seo/link_repair.py"))
        self.btn_repair.pack(fill=tk.X, pady=5)

        self.btn_curator = ttk.Button(btn_frame, text="🤖 Run Curator (Live)", command=lambda: self.run_script("Curator", "seo/curator_engine.py"))
        self.btn_curator.pack(fill=tk.X, pady=5)

        self.btn_img_audit = ttk.Button(btn_frame, text="🖼️ Image Auditor", command=lambda: self.run_script("Image_Auditor", "image_auditor.py"))
        self.btn_img_audit.pack(fill=tk.X, pady=5)

        self.btn_pattern = ttk.Button(btn_frame, text="Pattern Auditor", command=lambda: self.run_script("Pattern_Auditor", "pattern_auditor.py"))
        self.btn_pattern.pack(fill=tk.X, pady=5)

        ttk.Label(btn_frame, text="Topic Tracking", style="TLabel").pack(pady=(10, 5))

        self.btn_topic_update = ttk.Button(btn_frame, text="📊 Update Topic Lists", command=lambda: self.run_script("Topic_Tracker", "topic_tracker.py"))
        self.btn_topic_update.pack(fill=tk.X, pady=5)

        # Status
        self.status_label = ttk.Label(btn_frame, text="Status: Idle", foreground="#4CAF50")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        # --- LOG VIEWER ---
        ttk.Label(log_frame, text="Live Execution Log", style="TLabel").pack(anchor=tk.W)
        self.log_text = tk.Text(log_frame, bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 10), wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)

# --- FOOTER ---
        footer = tk.Frame(self.root, bg="#2b2b2b")
        footer.pack(fill=tk.X, padx=10, pady=5)
        
        self.btn_open_reports = ttk.Button(footer, text="📁 Open Reports Folder", command=lambda: os.startfile(os.path.join(V2_ROOT, "reports")))
        self.btn_open_reports.pack(side=tk.LEFT)
        
        self.btn_open_logs = ttk.Button(footer, text="📁 Open Logs Folder", command=lambda: os.startfile(LOG_DIR))
        self.btn_open_logs.pack(side=tk.LEFT, padx=10)
        
        self.btn_open_topics = ttk.Button(footer, text="📁 Open Topic Lists", command=lambda: os.startfile(os.path.join(V2_ROOT, "topic_lists")))
        self.btn_open_topics.pack(side=tk.LEFT, padx=10)

    def log(self, message):
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)

    def run_script(self, task_name, script_relative_path, args=None):
        script_path = os.path.join(V2_ROOT, script_relative_path)
        
        if not os.path.exists(script_path):
            messagebox.showerror("Error", f"Script not found:\n{script_path}")
            return

        self.toggle_buttons(tk.DISABLED)
        self.status_label.config(text=f"Status: Running {task_name}...", foreground="#FFC107")
        self.log_text.delete(1.0, tk.END)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file_path = os.path.join(LOG_DIR, f"{task_name}_{timestamp}.log")
        
        self.log(f"--- Starting {task_name} ---\n")
        self.log(f"Logging to: {log_file_path}\n\n")

        threading.Thread(target=self.execute_process, args=(script_path, log_file_path, task_name, args or []), daemon=True).start()

    def execute_process(self, script_path, log_file_path, task_name, args=None):
        try:
            with open(log_file_path, "w", encoding="utf-8") as log_file:
                process = subprocess.Popen(
                    [PYTHON_EXE, script_path] + (args or []),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=V2_ROOT
                )

                for line in process.stdout:
                    self.root.after(0, self.log, line)
                    log_file.write(line)

                process.wait()

            if process.returncode == 0:
                self.root.after(0, self.finish_task, task_name, True)
            else:
                self.root.after(0, self.finish_task, task_name, False)
                
        except Exception as e:
            self.root.after(0, self.log, f"\nCRITICAL ERROR: {e}\n")
            self.root.after(0, self.finish_task, task_name, False)

    def finish_task(self, task_name, success):
        self.toggle_buttons(tk.NORMAL)
        if success:
            self.status_label.config(text="Status: Idle (Success)", foreground="#4CAF50")
            self.log(f"\n✅ {task_name} completed successfully.")
            messagebox.showinfo("Success", f"{task_name} finished successfully!")
        else:
            self.status_label.config(text="Status: Idle (Failed)", foreground="#F44336")
            self.log(f"\n❌ {task_name} encountered an error. Check logs.")

    def toggle_buttons(self, state):
        for btn in [self.btn_publish, self.btn_inspect, self.btn_doctor, self.btn_auto, self.btn_retry, self.btn_republish, self.btn_smart, self.btn_seo, self.btn_repair, self.btn_curator, self.btn_img_audit, self.btn_pattern, self.btn_topic_update]:
            btn.config(state=state)

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoPilotGUI(root)
    root.mainloop()

