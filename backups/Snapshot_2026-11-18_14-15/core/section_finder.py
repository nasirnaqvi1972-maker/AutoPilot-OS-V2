"""
section_finder.py -- robust section detection + safe image insertion
for AutoPilot OS V2.
"""
from __future__ import annotations

import re
from bs4 import BeautifulSoup

DEFAULTS = {
    "min_words": 40,            # preferred paragraph length
    "fallback_min_words": 18,   # shortest paragraph we will ever attach an image to
    "min_section_words": 35,    # section prose needed to justify an image when no single p is long
    "min_gap_words": 150,       # minimum words between two images
    "max_images": 7,
    "fallback_gap_words": 300,  # spacing used when the page has no usable headings
}

HEAD_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6"]

BLOCK_TAGS = {
    "table", "thead", "tbody", "tr", "td", "th", "ul", "ol", "dl", "li",
    "details", "summary", "blockquote", "figure", "figcaption", "aside",
    "nav", "footer", "pre", "header", "form", "script", "style", "noscript",
}

BLOCK_TOKENS = {
    "faq", "faqs", "quick", "facts", "infobox", "toc", "sources", "source",
    "references", "reference", "refs", "related", "widget", "accordion",
    "callout", "sidebar", "disclaimer", "cta", "affiliate", "ad", "ads",
    "sponsored", "newsletter",
}

_LEAD = r"(?:\d+[\.\)]\s*)?(?:the\s+)?"
BLOCK_HEADING = re.compile(
    r"^\W*" + _LEAD +
    r"(?:quick\s+facts?|key\s+facts?|fast\s+facts?|at\s+a\s+glance|"
    r"frequently\s+asked|q\s*&(?:amp;)?\s*a|sources?|references?|bibliography|"
    r"further\s+reading|see\s+also|related|table\s+of\s+contents|conclusion|"
    r"final\s+thoughts?|summary|visitor\s+information|disclaimer)\b"
    r"|\bfaqs?\b|\bfrequently\s+asked\s+questions\b",
    re.I,
)

DATA_LABEL = re.compile(
    r"^(built|location|type|status|year|period|region|country|founded|unesco|"
    r"coordinates|area|elevation|architect|style|condition|hours|entry|ticket|"
    r"address|source)\b[^.]{0,30}:",
    re.I,
)

INLINE_TAGS = {"a", "span", "strong", "b", "em", "i", "u", "small", "mark",
               "font", "sup", "sub"}

def _clean(t):
    return re.sub(r"\s+", " ", t or "").strip()

def _words(t):
    return len(t.split())

def _tokens(val):
    if isinstance(val, (list, tuple)):
        val = " ".join(val)
    return {x for x in re.split(r"[^a-z0-9]+", (val or "").lower()) if x}

def _is_article_wrapper(anc):
    return anc.find("h1") is not None or len(anc.find_all("h2", limit=2)) >= 2

def blocked_container(el):
    for anc in el.parents:
        name = getattr(anc, "name", None)
        if not name or name == "[document]":
            continue
        if name in BLOCK_TAGS:
            return f"inside <{name}>"
        soft = None
        if (_tokens(anc.get("id")) | _tokens(anc.get("class"))) & BLOCK_TOKENS:
            soft = "container class/id looks like FAQ/Facts/Sources/widget"
        elif "faqpage" in str(anc.get("itemtype", "")).lower():
            soft = "FAQPage schema container"
        elif anc.get("role") in {"complementary", "navigation", "contentinfo"}:
            soft = f"role={anc.get('role')}"
        elif name in {"div", "section"} and re.search(
                r"background|border", str(anc.get("style", "")), re.I):
            if _words(anc.get_text(" ")) < 150:
                soft = "small styled callout box"
        if soft and not _is_article_wrapper(anc):
            return soft
    return None

def _pseudo_heading(p):
    kids = [c for c in p.children if not (isinstance(c, str) and not c.strip())]
    if len(kids) == 1 and getattr(kids[0], "name", None) in {"strong", "b"}:
        t = _clean(kids[0].get_text(" "))
        if t and _words(t) <= 12 and not t.endswith((".", "\u2026", ",")):
            return t
    return None

def _looks_like_data(p):
    t = _clean(p.get_text(" "))
    if len(p.find_all("br")) >= 3:
        return True
    if DATA_LABEL.match(t):
        return True
    link_chars = sum(len(a.get_text()) for a in p.find_all("a"))
    return link_chars / max(len(t), 1) > 0.5

def _intro_to_block(p):
    if _clean(p.get_text(" ")).endswith(":"):
        return True
    nxt = p.find_next_sibling()
    return bool(nxt is not None and (
        nxt.name in {"ul", "ol", "dl", "table", "figure", "img"}
        or nxt.get("data-autopilot")))

def _slot(heading, entry, mode):
    el, n, pos, _ = entry
    return {"heading": heading, "p": el, "words": n, "pos": pos, "mode": mode}

def _thin(picks, cfg, t):
    kept, last = [], None
    for s in picks:
        if last is None or s["pos"] - last >= cfg["min_gap_words"]:
            kept.append(s)
            last = s["pos"]
        else:
            t(f"drop {s['heading']!r}: only {s['pos'] - last} words after previous image")
    m = cfg["max_images"]
    if len(kept) > m:
        idx = [0] if m <= 1 else sorted({round(i * (len(kept) - 1) / (m - 1)) for i in range(m)})
        kept = [kept[i] for i in idx]
    return kept

def _scan(soup, cfg, trace):
    t = trace.append if trace is not None else (lambda *_: None)
    h1 = soup.find("h1")
    page_title = _clean(h1.get_text(" ")) if h1 else ""

    sections, stream = [], []
    cur = None
    h2_blocked = False
    blocked_now = False
    heading_text = page_title
    pos = 0

    for el in soup.find_all(HEAD_TAGS + ["p"]):
        is_head, level, text = False, 0, ""
        if el.name == "p":
            ph = _pseudo_heading(el)
            if ph and not blocked_container(el):
                is_head, level, text = True, 3, ph
        else:
            is_head, level, text = True, int(el.name[1]), _clean(el.get_text(" "))

        if is_head:
            why = None
            if BLOCK_HEADING.search(text):
                why = "heading is FAQ/Sources/Quick Facts/Conclusion-type"
            else:
                why = blocked_container(el)

            if level == 1:
                heading_text = text or page_title
                cur, h2_blocked, blocked_now = None, False, False
                continue
            if level >= 4:
                if why:
                    blocked_now = True
                continue
            if level == 2:
                h2_blocked = bool(why)
                blocked_now = h2_blocked
            else:
                blocked_now = h2_blocked or bool(why)

            heading_text = text
            cur = {"heading": text, "paras": [], "words": 0}
            sections.append(cur)
            continue

        text = _clean(el.get_text(" "))
        n = _words(text)
        pos += n
        if not n:
            continue

        if blocked_now:
            why = "inside blocked section"
        else:
            why = (blocked_container(el)
                   or ("looks like key:value data" if _looks_like_data(el) else None)
                   or ("introduces a list/table" if _intro_to_block(el) else None))
        if why:
            continue

        entry = (el, n, pos, heading_text)
        stream.append(entry)
        if cur is not None:
            cur["paras"].append(entry)
            cur["words"] += n

    picks = []
    for s in sections:
        ps = s["paras"]
        if not ps:
            continue
        choice, mode = next((e for e in ps if e[1] >= cfg["min_words"]), None), "long-paragraph"
        if choice is None and s["words"] >= cfg["min_section_words"]:
            choice, mode = ps[-1], "end-of-section"
        if choice is None:
            best = max(ps, key=lambda e: e[1])
            if best[1] >= cfg["fallback_min_words"]:
                choice, mode = best, "longest-short-paragraph"
        if choice is None:
            continue
        picks.append(_slot(s["heading"], choice, mode))

    picks = _thin(picks, cfg, t)

    if not picks and stream:
        last = -cfg["fallback_gap_words"] // 2
        for e in stream:
            if e[1] < cfg["fallback_min_words"]:
                continue
            if e[2] - last >= cfg["fallback_gap_words"]:
                picks.append(_slot(e[3] or page_title or "Article image", e, "word-gap-fallback"))
                last = e[2]
        picks = _thin(picks, cfg, t)

    return picks

def find_sections(soup, trace=None, **overrides):
    cfg = {**DEFAULTS, **overrides}
    try:
        return _scan(soup, cfg, trace)
    except Exception as e:
        print(f"[section_finder] error: {e!r}")
        return []

def _block_anchor(p):
    while p.parent is not None and p.parent.name in INLINE_TAGS:
        p = p.parent
    return p

def insert_image(soup, slot, src, alt="", max_width=800):
    box = soup.new_tag("div", attrs={
        "class": "separator",
        "data-autopilot": "1",
        "style": "clear:both;text-align:center;margin:24px 0;",
    })
    a = soup.new_tag("a", href=src)
    img = soup.new_tag(
        "img", src=src, alt=alt, loading="lazy", border="0",
        style=f"width:100%;max-width:{max_width}px;height:auto;display:block;margin:0 auto;")
    a.append(img)
    box.append(a)
    _block_anchor(slot["p"]).insert_after(box)
    return box
