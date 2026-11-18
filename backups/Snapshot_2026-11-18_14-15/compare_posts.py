import csv
from pathlib import Path

LIVE_CSV = Path(r"D:\Projects\AutoPilot_OS_v2\reports\content_audit_2026-10-25.csv")
BACKUP_TXT = Path(r"D:\Projects\AutoPilot_OS_v2\backup_post_list.txt")
OUTPUT_FILE = Path(r"D:\Projects\AutoPilot_OS_v2\missing_posts_report.txt")

def main():
    live_titles = set()
    backup_titles = set()

    # Read Live Posts (from CSV)
    if LIVE_CSV.exists():
        with open(LIVE_CSV, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize title to avoid case/space mismatches
                title = row['title'].strip().lower()
                live_titles.add(title)
    else:
        print("Live CSV not found.")
        return

    # Read Backup Posts (from TXT)
    if BACKUP_TXT.exists():
        with open(BACKUP_TXT, 'r', encoding='utf-8') as f:
            for line in f:
                if "|" in line:
                    title = line.split("|")[0].strip().lower()
                    backup_titles.add(title)
    else:
        print("Backup TXT not found.")
        return

    # Compare
    missing_from_backup = live_titles - backup_titles
    missing_from_live = backup_titles - live_titles

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"LIVE POSTS: {len(live_titles)}\n")
        f.write(f"BACKUP POSTS: {len(backup_titles)}\n\n")
        
        f.write("=" * 60 + "\n")
        f.write(f"POSTS ON LIVE SITE, BUT MISSING FROM BACKUP ({len(missing_from_backup)})\n")
        f.write("=" * 60 + "\n")
        for title in sorted(missing_from_backup):
            f.write(f"- {title}\n")
            
        f.write("\n" + "=" * 60 + "\n")
        f.write(f"POSTS IN BACKUP, BUT MISSING FROM LIVE SITE ({len(missing_from_live)})\n")
        f.write("=" * 60 + "\n")
        for title in sorted(missing_from_live):
            f.write(f"- {title}\n")

    print(f"Comparison complete! Open {OUTPUT_FILE} to see the results.")

if __name__ == "__main__":
    main()