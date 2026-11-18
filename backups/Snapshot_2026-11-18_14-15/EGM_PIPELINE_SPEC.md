# EGM_PIPELINE_SPEC.md — Pipeline Audit & Review Specification
**Architecture:** AutoPilot OS Publish Pipeline  
**Role:** EGM Elephant (Lead System Architect)  
**Target Reviewers:** Stateless Goldfish Personas (Security, Reliability, Architecture) in Kilo Code  
**Audit Target Modules:**
- `main_autopilot.py` (Pipeline Orchestrator & Batch State Manager)
- `core/image_curator.py` (Asset Acquisition, Relay Interface & CLIP Validation)
- `core/html_cleaner.py` (DOM Sanitization & Structural Normalization)
- `core/quality_gate.py` (AdSense Compliance, Monetization Stripping & Attribution)
- `core/blogger_publisher.py` (ImgBB Upload, Blogger API Transport & Post Lifecycles)

---

## 1. Data Flow & Trust Boundaries

### 1.1 End-to-End Pipeline Data Flow

```text
[Input Document: .docx / .html]
       │
       ▼ (Step 0: Ingestion & Extraction)
┌─────────────────────────────────────────────────────────┐
│ post_parser.py / html_parser.py                         │
│ - Extracts Title, Metadata Header, Raw Body Text/HTML   │
│ - Generates post Slug & Slot definitions                │
└─────────────────────────────────────────────────────────┘
       │
       ▼ (Step 1: Visual Asset Curation)
┌─────────────────────────────────────────────────────────┐
│ core/image_curator.py                                   │
│ - Reads overrides from content/image_overrides.json     │
│ - Queries Wikimedia Commons via Cloudflare Relay        │
│ - Downloads candidate binaries (urllib/requests)        │
│ - Evaluates semantic relevance via OpenCLIP (ViT-B-32)  │
│ - Embeds local <img> references & initial <figcaption>s │
└─────────────────────────────────────────────────────────┘
       │
       ▼ (Step 2: Structural Cleaning & Normalization)
┌─────────────────────────────────────────────────────────┐
│ core/html_cleaner.py                                    │
│ - Strips LLM prompt remnants ("Image Description: ...") │
│ - Deduplicates consecutive identical paragraphs         │
│ - Upgrades pseudo-headings (<p><strong>...</strong>)    │
│ - Standardizes semantic section headers                 │
└─────────────────────────────────────────────────────────┘
       │
       ▼ (Step 3: SEO Optimization & Schema Injection)
┌─────────────────────────────────────────────────────────┐
│ seo/seo_optimizer.py                                    │
│ - Enforces single H1 title; demotes rogue H1s to H2     │
│ - Injects schema.org BlogPosting JSON-LD markup         │
│ - Sets image dimensions (1280x720) and loading="lazy"   │
│ - Generates fallback meta description (first 150 chars) │
└─────────────────────────────────────────────────────────┘
       │
       ▼ (Step 4: AdSense & Safety Quality Gate)
┌─────────────────────────────────────────────────────────┐
│ core/quality_gate.py (enforce_adsense_compliance)       │
│ - Strips all monetization funnels (Patreon, Gumroad,    │
│   BuyMeACoffee, PayPal, donation phrases)               │
│ - Recursively collapses emptied container elements      │
│ - Injects required CC BY-SA 4.0 Wikimedia attributions  │
│ - Injects Unsplash attributions                         │
│ - Calls sanitize_post_html:                             │
│     * Fixes heading level skipping (H1 -> H3 => H2)     │
│     * Sanitizes external links (target="_blank",        │
│       rel="noopener noreferrer")                        │
└─────────────────────────────────────────────────────────┘
       │
       ▼ (Step 5: Remote Upload & Remote Publishing)
┌─────────────────────────────────────────────────────────┐
│ core/blogger_publisher.py                               │
│ - Scans local <img> tags; uploads binaries to ImgBB     │
│ - Replaces local paths with hosted ImgBB HTTPS URLs     │
│ - Authenticates to Google Blogger API via OAuth2 pickle │
│ - Resolves existing draft by normalized title (dedup)   │
│ - Issues posts().patch or posts().insert (isDraft=True) │
│ - Executes post-publish fixers (Smart Replacer, Doctor) │
└─────────────────────────────────────────────────────────┘
       │
       ▼ (Step 6: State Transition)
[Move input file: content/pending/ ──► content/processed/ OR content/failed/]
```

### 1.2 Untrusted Data Entry Points

| Boundary ID | Source / Origin | Vector / Payload Type | Risk Profile |
| :--- | :--- | :--- | :--- |
| **UB-01** | Input Files (`content/pending/*.docx`, `*.html`) | Arbitrary HTML, Malformed XML, Unsanitized Word tags, Embedded Scripts | Stored XSS, parser crashes, DOM corruption, encoding glitches. |
| **UB-02** | Wikimedia Cloudflare Relay / Commons API | JSON payloads, File URLs, Image metadata, SVG files, EXIF tags | SSRF redirection, malicious image payloads, malformed JSON, poisoned attribution strings. |
| **UB-03** | Gemini LLM Completions / Automated Drafts | Generated HTML, Markdown code blocks, Refusal strings ("As an AI...") | Prompt injection artifacts, hallucinated tags, broken nesting, unclosed elements. |
| **UB-04** | ImgBB Hosting API Responses | JSON responses, Hosted image URLs | API hijacking, truncated URLs, HTTP downgrade, unexpected hosting error formats. |
| **UB-05** | Google Blogger API Responses | JSON responses, Status codes, Error payloads | Rate limits (429), partial updates, network timeouts, OAuth token expiration. |

---

## 2. Security Contracts (Hard Invariants)

These invariants **MUST** hold true across all pipeline paths before any payload leaves the local machine.

### SEC-01: Enforcement Gate Invariance
* **Contract:** No HTML string or DOM tree may be transmitted to the Blogger API without executing `enforce_adsense_compliance()` as the **final transformation step** before serialization.
* **Invariant:** If `enforce_adsense_compliance()` fails or throws an unhandled exception, the pipeline **MUST NOT** fall back to publishing unvalidated HTML. It must abort and quarantine the post.

### SEC-02: Strict Link Sanitization & Protocol Lockdown
* **Contract:** All anchor tags (`<a href="...">`) pointing to destinations outside the internal domain whitelist (`dustanddynasty.blogspot.com`, `blogger.com`, `googleusercontent.com`) **MUST**:
  1. Enforce `target="_blank"`.
  2. Enforce `rel="noopener noreferrer"`.
  3. Strip any URI with non-HTTP(S) schemes (e.g., `javascript:`, `data:`, `file:`, `vbscript:`).
* **Exemption:** Named page jump markers (e.g., `<a name="more"></a>`) are allowed without `href` or external attributes, provided they contain no remote destination.

### SEC-03: Zero Monetization Leakage
* **Contract:** Post bodies must be 100% free of inline monetization links (Patreon, Gumroad, BuyMeACoffee, Ko-fi, PayPal, Liberapay, Payhip, Sellfy) and patron solicitation text.
* **Invariant:** Any container (`<div>`, `<p>`, `<section>`) emptied as a result of link stripping must be decomposed, ensuring Google AdSense spiders never encounter orphan donation blocks.
* **Map Protection:** Google Maps embed iframes (`google.com/maps`) must be preserved and never inadvertently stripped during container pruning.

### SEC-04: Credential & Token Boundary Isolation
* **Contract:** API tokens, OAuth pickle binaries (`blogger_token.pickle`), client secret JSONs (`client_secrets.json`), `IMGBB_API_KEY`, and relay secrets (`ddd-secret-2026`) must **NEVER**:
  1. Be leaked into post HTML, alt text, or JSON-LD schema.
  2. Be written to public log files, reports, or stdout streams in production mode.
  3. Be passed as query parameters in unencrypted HTTP connections.

### SEC-05: Mandatory Image Attribution
* **Contract:** Every image sourced from Wikimedia Commons or Unsplash **MUST** include a legal CC attribution block inside an adjacent `<figcaption>` or wrapper element before publishing. Unattributed third-party images must fail the compliance gate.

---

## 3. Reliability Contracts (Fault Tolerance & Resilience)

### REL-01: Explicit Timeouts on All Network I/O
* **Contract:** Every external network call **MUST** have an explicit timeout configured. Default infinite socket waits are strictly forbidden.
  - **Wikimedia Relay Requests:** `timeout=30` seconds max.
  - **ImgBB Upload POSTs:** `timeout=45` seconds max.
  - **Google Blogger API Service Calls:** Transport layer must enforce `socket_timeout=30` seconds.
  - **CLI / Subprocess Executions:** `timeout=180` seconds max (enforcing AGENTS.md Rule 9: hang-proof execution).

### REL-02: Blogger API Exponential Backoff & Retry
* **Contract:** Calls to `service.posts().insert()` or `service.posts().patch()` that fail due to transient HTTP status codes (`429 Too Many Requests`, `500 Internal Server Error`, `502 Bad Gateway`, `503 Service Unavailable`, `504 Gateway Timeout`):
  1. Must retry with exponential backoff and jitter (`base=2s`, `max_retries=4`).
  2. Batch processing runs must enforce a deliberate pacing pause (`time.sleep(2)`) between consecutive post operations to prevent rate limit tripwires.

### REL-03: Fail-Closed Gate Behavior
* **Contract:** The compliance engine (`quality_gate.py`) and HTML parser must follow a **fail-closed** policy for fatal errors:
  - If BeautifulSoup fails to parse the document, the process returns `False` and logs the error.
  - Under no circumstances should a corrupt or half-parsed DOM be forwarded to `blogger_publisher.py`.

### REL-04: OpenCLIP & Neural Resource Bounds
* **Contract:** In `core/image_curator.py`, CLIP model initialization (`open_clip.create_model_and_transforms`) must be cached as a singleton to prevent out-of-memory (OOM) churn during batch operations.
* **Fallback:** If torch/CUDA fails or OpenCLIP encounters corrupted image binaries, the image curator must catch the exception, discard the invalid image candidate, and fall back to metadata matching or fallback stock rather than crashing the batch runner.

---

## 4. State Contracts & Idempotency

### STA-01: Idempotent Draft Creation & In-Place Patching
* **Contract:** Re-running the pipeline on a previously published or drafted post **MUST NOT** create duplicate entries on Blogger.
* **Mechanism:**
  1. Check incoming metadata for explicit `Post ID`.
  2. If missing, query Blogger API by normalized Unicode NFC title.
  3. If found, issue `posts().patch(postId=...)` to update in-place.
  4. If and only if no match exists, issue `posts().insert(isDraft=True)`.

### STA-02: Atomic File Ingestion Transitions
* **Contract:** The source document in `content/pending/` must remain untouched until the downstream publishing call returns verified success.
* **Transition States:**
  - `SUCCESS`: Move `content/pending/{file}` -> `content/processed/{file}`.
  - `FAILURE`: Move `content/pending/{file}` -> `content/failed/{file}`.
* **Invariant:** Input files must **NEVER** be deleted or truncated in-place. Moves must be atomic using safe copy-then-unlink semantics to withstand process termination midway.

### STA-03: Inviolability of Sacred State Repositories
* **Contract:** Per AGENTS.md Rule 4 & 7:
  1. `content/post_registry.json` is SACRED. The pipeline may append verified mappings, but must **NEVER** overwrite, re-index, or purge existing records.
  2. `content/image_overrides.json` is SACRED. The pipeline must **NEVER** delete or clear user-defined slot overrides.
  3. All disk writes to state JSON files must use atomic writes (write to `.tmp` file on the same volume, followed by `os.replace`).

### STA-04: Image Pipeline Interlock
* **Contract:** If `image_curator.py` or image processing fails (missing required slots, relay unreachable, or zero valid images curated):
  1. The pipeline must halt immediately for that post.
  2. It must **NOT** proceed to `html_builder.py` or `blogger_publisher.py`.
  3. It must log the slot failure and move the post to `content/failed/`.
  4. No post with unresolved local image paths (`src="img_01_web.jpg"`) may be submitted to Blogger. If ImgBB upload fails for an image, the post must abort or strip the broken figure cleanly.

---

## 5. Review Checklist for Goldfish Personas

When evaluating the codebase against this specification, the Goldfish reviewers should verify:

- [ ] **Security Goldfish:**
  - Does any code path bypass `enforce_adsense_compliance()` before calling the Blogger API?
  - Are external link regexes able to be bypassed with weird URI schemes (e.g. `javascript:alert(1)`)?
  - Are API credentials or secrets exposed in error logs or string formatting?
  - Is Google Maps iframe preservation secure against nested DOM exploits?

- [ ] **Reliability Goldfish:**
  - Are all `urllib.request.urlopen`, `requests.post`, and Google API `execute()` calls bounded by timeouts?
  - What happens when ImgBB returns a 400/500 or rate limit response? Does it raise an unhandled exception or return None?
  - Does `main_autopilot.py` handle subprocess hangs gracefully within 180 seconds?
  - Does the OAuth token refresh handle invalid or expired pickles cleanly?

- [ ] **Architecture & State Goldfish:**
  - Are file moves between `pending`, `processed`, and `failed` strictly atomic?
  - Is `post_registry.json` or `image_overrides.json` ever opened in bare `'w'` write mode without atomic temp-file replacement?
  - Does the title normalization in Blogger draft deduplication handle case differences, trailing whitespace, and Unicode normalization (NFC)?
  - Is there any memory leak or GPU resource leak in batch CLIP runs?
