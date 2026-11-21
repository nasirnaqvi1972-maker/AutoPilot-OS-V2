# v2_context.md

## Directory tree (max depth 2)

```
AutoPilot_OS_v2/
├── core/
│   ├── blogger_publisher.py
│   ├── html_cleaner.py
│   ├── image_curator.py
│   ├── image_validator.py
│   ├── quality_gate.py
│   └── section_finder.py
├── content/
│   ├── pending/
│   ├── processed/
│   └── failed/
├── os_env/
├── data/
├── drafts/
├── logs/
├── seo/
└── (numerous root-level *.py scripts)
```

## Main orchestrator script

- Name: `safe_batch.py`
- Location: `D:\Projects\AutoPilot_OS_v2\safe_batch.py`
- Entry point: `main()` -> iterates `content/pending/*.html`, calls `process_post(html_file)`.

## Script writer output format

- `sync_writer_to_publisher.py` writes the draft as an HTML file (string content wrapped in `<h1>` title) to `content/pending/<slug>.html` via `save_to_pending()`.

## Image fetcher attachment method

- `core/image_curator.py` (called in `process_post`) attaches images as local file paths; images are saved into `img_folder` (e.g. `content/processed/<slug>/`) and referenced by relative filename in `<img src="...">`. The publisher then uploads these local files to ImgBB and replaces `src` with hosted URLs.

## Draft upload function call

- Exact call (in `safe_batch.py` `process_post`):
```python
post_id = publish_post(
    html_path=curated_html_path,
    img_folder=img_folder,
    title=title,
    labels=labels,
    post_id=existing_id
)
```
- Defined in `core/blogger_publisher.py`:
```python
def publish_post(html_path, img_folder, title, labels, post_id=None):
```

## Main pipeline execution block (writer -> uploader)

```python
    print(f"\n--- Publishing to Blogger ---")
    # Check for existing post (draft or live) with same title
    existing_id = None
    try:
        service = get_blogger_service()
        blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
        blog_id = blog['id']
        target_title = unicodedata.normalize('NFC', title.strip().lower())
        page_token = None
        while True:
            res = service.posts().list(blogId=blog_id, maxResults=100, pageToken=page_token).execute()
            for d in res.get('items', []):
                d_title = unicodedata.normalize('NFC', d.get('title', '').strip().lower())
                if d_title == target_title:
                    existing_id = d['id']
                    break
            if existing_id:
                break
            page_token = res.get('nextPageToken')
            if not page_token:
                break
    except Exception as e:
        print(f"  [post check] failed: {e}")
    if existing_id:
        print(f"  [Engine] UPDATED existing draft (ID: {existing_id}) in place. No duplicates created.")
    else:
        print("  [Engine] CREATED new draft.")

    labels = detect_location(title, html_content)
    print(f"  [Engine] Assigned labels: {', '.join(labels) if labels else 'none'}.")

    post_id = publish_post(
        html_path=curated_html_path,
        img_folder=img_folder,
        title=title,
        labels=labels,
        post_id=existing_id
    )
```