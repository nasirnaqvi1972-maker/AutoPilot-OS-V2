# AGENTS.md - Shared Working Agreement

This file is the source of truth for every AI agent on Auto Pilot OS.
Read this completely before doing anything else.

## 1. PROJECT

Auto Pilot OS is a Python pipeline. It takes UNESCO posts (.docx) from
content/pending/, fetches images from Wikimedia Commons via a Cloudflare
relay, watermarks them, builds Blogger HTML, uploads images to ImgBB,
and creates or updates a Blogger draft. Re-running updates instead of
duplicating.

## 2. ENVIRONMENT

Project root : D:\Projects\Auto Pilot OS
Code root    : D:\Projects\Auto Pilot OS\AutoPilot_OS
Venv Python  : D:\Projects\Auto Pilot OS\AutoPilot_OS\os_env\Scripts\python.exe
Env file     : D:\Projects\Auto Pilot OS\AutoPilot_OS\.env
Blog         : https://dustanddynasty.blogspot.com
Blog ID      : 1922469613291345636

Rules:
- ALWAYS use the venv Python above. Never system python.
- Windows only. PowerShell, not bash.
- Wikimedia direct access is blocked. Use the relay in wikimedia_fetcher.py.

## 3. FOLDERS

AutoPilot_OS/core/          - pipeline modules
  wikimedia_fetcher.py      - step 0, fetch images
  image_processor.py        - step 1, watermark and resize
  html_builder.py           - step 2, build HTML
  blogger_publisher.py      - step 3, upload and publish
  post_parser.py            - read docx
  blogger_resolver.py       - slug to URL lookup
AutoPilot_OS/main_autopilot.py - full pipeline
AutoPilot_OS/os_env/        - venv
AutoPilot_OS/.env           - GEMINI_API_KEY

content/pending/            - waiting
content/processed/          - done
content/failed/             - failed
content/_pending_hold/      - held
content/images/<slug>/      - images and _manifest.json
content/image_overrides.json - SACRED, never delete
content/post_registry.json  - SACRED, never delete

## 4. PIPELINE

Step 0 wikimedia_fetcher.py : checks overrides, else searches Commons via relay
Step 1 image_processor.py   : watermarks, resizes, saves img_NN_web.jpg
Step 2 html_builder.py      : builds _output.html
Step 3 blogger_publisher.py : ImgBB upload, Blogger draft create or update

Success: docx goes pending -> processed.
Failure: docx goes pending -> failed.

## 5. GOLDEN RULES

1. Backup any .py before editing: Copy-Item $f "$f.bak-$((Get-Date).ToString('yyyyMMdd-HHmmss'))"
2. image_overrides.json is the user's trusted list. Never ignore. Never overwrite.
3. Do not run main_autopilot.py without confirmation if pending has more than 3 files.
4. Never touch post_registry.json.
5. If pending > 3, ask first. ImgBB rate-limits big batches.
6. Never delete a Blogger post unless asked.
7. Only ADD entries to image_overrides.json, never remove.
8. Never install new Python packages without asking.
9. If a command hangs over 3 minutes, kill python and report the post.
10. If unsure, ask.

## 6. HANDOFF PROTOCOL

At START of session:
1. Read AGENTS.md fully.
2. Read AGENT_STATE.md.
3. If Status = IN_PROGRESS and Started-by is a different agent, continue from
   the Next action field. Do not restart.
4. If Status = DONE or file missing, start fresh.
5. Say: "Resuming from: <Next action>" or "Starting fresh."

At END of session:
1. Update AGENT_STATE.md.
2. Set Status = DONE / IN_PROGRESS / BLOCKED.
3. Fill Next action with ONE executable step.
4. List every file modified.
5. If blocked, describe the blocker.

AGENT_STATE.md format:
# AGENT STATE
## Current task
## Started by
## Status
## Last action completed
## Next action
## Files modified this session
## Decisions made this session
## Open questions for the user
## Known problems

## 7. COMMON TASKS

7.1 Post has wrong images:
    - Ask which post.
    - Run diagnostic to list every slot and its actual Commons file.
    - Search Commons via relay.
    - Add overrides. Never remove.
    - Move docx processed -> pending.
    - Delete content/images/<slug>/.
    - Run main_autopilot.py.
    - Update AGENT_STATE.md.

7.2 Post failed:
    - ImgBB timeout: re-run main_autopilot.py.
    - Missing slot: add override.
    - Missing image on disk: clear folder, re-run.
    - Move docx failed -> pending first.

7.3 Duplicate post:
    - Merge unique images into original FIRST.
    - Then delete duplicate.

7.4 Home too few posts:
    - Check html_builder.py has parts.append("<!--more-->") after hero figure.
    - Blogger Settings -> Posts -> Max posts = 10.

7.5 New post:
    - Place docx in content/pending/.
    - Run main_autopilot.py.

## 8. WIKIMEDIA RELAY

RELAY = "https://wikimedia-relay.nasirabbasnaqvi.workers.dev"
TOKEN = "ddd-secret-2026"

def relay(url):
    import urllib.request, urllib.parse
    params = urllib.parse.urlencode({"url": url, "token": TOKEN})
    req = urllib.request.Request(RELAY + "?" + params,
                                 headers={"User-Agent": "DustAndDynastyBot/1.0"})
    return urllib.request.urlopen(req, timeout=25).read()

Never call commons.wikimedia.org directly.

## 9. MERGE DUPLICATE IMAGES

1. Fetch both posts via Blogger API.
2. Extract figure blocks.
3. Skip figures whose img src already in original.
4. Insert unique figures before the map iframe.
5. service.posts().update on the original.
6. Wait for confirmation, then delete the duplicate.

## 10. BACKUP AND ROLLBACK

Backup file:
  Copy-Item $file "$file.bak-$((Get-Date).ToString('yyyyMMdd-HHmmss'))"

Backup post: write original_html to disk before update.
Rollback: service.posts().update with the backup.

## 11. DO NOT

- Use git unless asked.
- Create folders outside content/ without telling user.
- Hand-edit post_registry.json or image_overrides.json (only add).
- Run live-post commands without a backup.
- Assume. Run the diagnostic.
- Touch .env, token.json, credentials.
- Use sys.exit() in patched scripts.

## 12. SESSION CHECKLIST

Start:
  [ ] Read AGENTS.md
  [ ] Read AGENT_STATE.md
  [ ] Confirm venv Python
  [ ] Greet user with state

End:
  [ ] Write AGENT_STATE.md
  [ ] List modified files
  [ ] Set Status
  [ ] Fill Next action
  [ ] Say "Handoff ready for next agent."

## 13. SEO & HTML Standards

- **Headings:** Never skip heading levels. Use `<h2>` for main sections and `<h3>` for subsections. Do not use `<h1>` in the post body (the Blogger theme handles the H1).
- **Links:** All external links MUST include `target="_blank"` and `rel="noopener noreferrer"`.
- **Images:** All images MUST have a descriptive `alt` tag. Never use "Additional View" or "Image 1".

End of AGENTS.md.
