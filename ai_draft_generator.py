#!/usr/bin/env python3
"""
ai_draft_generator.py - Generate AI draft using local FreeLLMAPI (OpenAI-compatible)
"""

import csv
import os
import re
import sys
import time
from pathlib import Path

from openai import OpenAI

# FreeLLMAPI endpoint (OpenAI-compatible)
UNIFIED_API_KEY = "freellmapi-1d1a45a24fc0a9e7d626522fe2e89fa95d449e8d7a8cbfa9"
client = OpenAI(
    base_url="http://127.0.0.1:31415/v1",
    api_key=UNIFIED_API_KEY
)

PENDING_DIR = Path(r"D:\Projects\AutoPilot_OS_v2\content\pending")
REMAINING_CSV = Path(r"D:\Projects\AutoPilot_OS_v2\topic_lists\remaining_topics.csv")

# Models to test - FreeLLMAPI serves these models
MODELS_TO_TEST = ["auto", "qwen3.8-max", "glm-5.3", "claude-sonnet-4-5"]

def load_next_topic():
    """Load first topic from remaining_topics.csv"""
    with open(REMAINING_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            return row['master_title'], row['country'], row['year_inscribed']
    return None, None, None

def build_prompt(topic, country, year):
    """Build strict prompt enforcing the exact HTML structure."""
    prompt = (
        'You are a professional travel writer for "Dust and Dynasty" \u2014 a UNESCO World Heritage site encyclopedia.\n\n'
        'Write a comprehensive 3000-word article about: ' + topic + ' (' + country + ', inscribed ' + year + ').\n\n'
        'OUTPUT REQUIREMENTS \u2014 FOLLOW EXACTLY:\n\n'
        '1. Start with <h1>[Topic] \u2014 [Poetic Subtitle]</h1> followed by JSON-LD schema (exactly as shown below).\n'
        '   - The combined title MUST be under 65 characters total for SEO.\n'
        '   - Example: <h1>Lower Valley of the Omo \u2014 Echoes of Antiquity in the Rift</h1>\n'
        '2. Then a lead paragraph: <p style="font-size: 1.05em; color: #555; font-style: italic; margin-top: 0;">[1-2 sentence poetic summary with location and UNESCO status]</p>\n'
        '3. Then a summary table in this EXACT format:\n'
        '<div style="background: #f8f9fa; border-left: 4px solid #2563eb; padding: 14px 18px; margin: 20px 0; border-radius: 4px;"><table style="border-collapse: collapse; width: 100%;"><tr><td style="padding: 4px 10px 4px 0; vertical-align: top; font-weight: bold; white-space: nowrap;">Location:</td><td style="padding: 4px 0;">[Country, region, coordinates]</td></tr><tr><td style="padding: 4px 10px 4px 0; vertical-align: top; font-weight: bold; white-space: nowrap;">Year of UNESCO Inscription:</td><td style="padding: 4px 0;">' + year + '</td></tr><tr><td style="padding: 4px 10px 4px 0; vertical-align: top; font-weight: bold; white-space: nowrap;">Category:</td><td style="padding: 4px 0;">[Cultural/Natural/Mixed]</td></tr><tr><td style="padding: 4px 10px 4px 0; vertical-align: top; font-weight: bold; white-space: nowrap;">UNESCO Reference:</td><td style="padding: 4px 0;">[Reference number]</td></tr><tr><td style="padding: 4px 10px 4px 0; vertical-align: top; font-weight: bold; white-space: nowrap;">Criteria:</td><td style="padding: 4px 0;">[e.g., (i)(ii)(iv)]</td></tr><tr><td style="padding: 4px 10px 4px 0; vertical-align: top; font-weight: bold; white-space: nowrap;">Coordinates:</td><td style="padding: 4px 0;">[Lat, Long]</td></tr><tr><td style="padding: 4px 10px 4px 0; vertical-align: top; font-weight: bold; white-space: nowrap;">Area:</td><td style="padding: 4px 0;">[Area in hectares/sq km]</td></tr></table></div>\n'
        '4. Then <!--more--> on its own line.\n'
        '5. Then AT LEAST 7 <h2> sections (no inline styles on h2), each with 2-4 <p> paragraphs.\n'
        '   - Use bold for key terms on first mention.\n'
        '   - Include internal links to other posts where relevant: <a href="https://dustanddynasty.blogspot.com/2026/10/..." rel="noopener noreferrer" style="color:#0b5ed7;font-weight:700;text-decoration:underline;text-decoration-color:#0b5ed7;" target="_blank">Linked Post Title</a>\n'
        '6. REQUIRED SPECIAL SECTIONS (in this order):\n'
        '   <h2>\u2726 Also Read \u2014 [Related Post]</h2>\n'
        '   <p><a href="..." rel="noopener noreferrer" style="color:#0b5ed7;font-weight:700;text-decoration:underline;text-decoration-color:#0b5ed7;" target="_blank">Related Post Title</a></p>\n'
        '   <p>One sentence description.</p>\n\n'
        '   <h2>\u2726 Conclusion</h2>\n'
        '   <p>Final reflective paragraph tying history, significance, and threats.</p>\n'
        '   <p>Call to reflection or action.</p>\n\n'
        '   <h2>\u2726 Frequently Asked Questions</h2>\n'
        '   <p>Question 1?</p>\n'
        '   <p>Answer.</p>\n'
        '   <p>Question 2?</p>\n'
        '   <p>Answer.</p>\n'
        '   (minimum 4 Q&A pairs)\n\n'
        '   <h2>\U0001f9fe Summary Table of Facts</h2>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Site Name \u2014 ' + topic + '</p>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Country \u2014 ' + country + '</p>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Continent \u2014 [Continent]</p>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Category \u2014 [Cultural/Natural/Mixed]</p>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Year of Inscription \u2014 ' + year + '</p>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">UNESCO Reference \u2014 [Reference]</p>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Criteria \u2014 [Criteria]</p>\n'
        '   (add 5-8 more fact lines)\n\n'
        '   <h2>\U0001f9f3 Visitor\'s Guide</h2>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Access \u2014 [How to reach]</p>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Best Time to Visit \u2014 [Season]</p>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Permits \u2014 [If any]</p>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Activities \u2014 [What to do]</p>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">What to Bring \u2014 [Essentials]</p>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Etiquette \u2014 [Behavior rules]</p>\n\n'
        '   <h2>\U0001f4cd Location Map</h2>\n'
        '   <div style="margin: 30px 0;"><iframe height="400" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://www.google.com/maps?q=[LAT],[LON]&z=12&output=embed" style="border: 0; border-radius: 6px;" width="100%"></iframe></div>\n'
        '   <p style="font-size: 0.9em; color: #666; margin-top: 8px;">Map showing the location of ' + topic + '. Coordinates: [LAT], [LON]</p>\n\n'
        '   <h2>\U0001f4da Sources and Further Reading</h2>\n'
        '   <p>UNESCO World Heritage Centre \u2014 ' + topic + ': https://whc.unesco.org/en/list/[REF]</p>\n'
        '   <p>IUCN World Heritage Outlook \u2014 ' + topic + ': https://worldheritageoutlook.iucn.org/explore-sites/[slug]</p>\n'
        '   <p>Wikipedia \u2014 ' + topic + ': https://en.wikipedia.org/wiki/[slug]</p>\n'
        '   (add 2-3 more sources)\n\n'
        'IMPORTANT: Use the SAME latitude,longitude coordinates in the Summary Table "Coordinates" row, the Location Map iframe src, and the map caption. Replace [LAT],[LON] with actual decimal coordinates (e.g., 4.5333,36.3333).\n\n'
        '7. DO NOT include: <html>, <head>, <body>, <img>, <figure>, <figcaption>, or any image tags.\n'
        '8. DO NOT include the sidebar support banner (engine adds it).\n'
        '9. RETURN ONLY RAW HTML \u2014 no markdown, no code fences, no explanations.\n\n'
        'JSON-LD SCHEMA (copy exactly, just change headline to the COMBINED title from <h1>):\n'
        '<script type="application/ld+json">{\n'
        '    "@context": "https://schema.org",\n'
        '    "@type": "BlogPosting",\n'
        '    "headline": "[COMBINED TITLE FROM H1 — MUST MATCH EXACTLY]",\n'
        '    "author": {\n'
        '        "@type": "Person",\n'
        '        "name": "Nasir A Naqvi"\n'
        '    }\n'
        '}</script>'
    )
    return prompt

def test_api():
    print("Testing API connectivity...")
    for model_name in MODELS_TO_TEST:
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": "Reply with exactly: MODEL_OK"}],
                    max_tokens=10
                )
                if "MODEL_OK" in response.choices[0].message.content:
                    print(f"API Test Successful. Using model: {model_name}")
                    return model_name
            except Exception as e:
                if "404" in str(e) or "model_not_found" in str(e).lower():
                    print(f"  [{model_name} not available] Trying next model...")
                    break
                print(f"  [{model_name} error] {e}")
                break
    print("All models failed during testing.")
    return None

def sanitize_filename(title):
    """Create safe filename from title."""
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = re.sub(r'\s+', '-', safe)
    return safe[:100] + '.html'

def main():
    model_name = test_api()
    if not model_name:
        print("Aborting. API connection failed entirely.")
        return

    print("[Generator] Loading next topic...")
    topic, country, year = load_next_topic()
    
    if not topic:
        print("[ERROR] No topics remaining")
        return
    
    print(f"[Generator] Topic: {topic} ({country}, {year})")
    
    prompt = build_prompt(topic, country, year)
    print(f"[Generator] Calling LLM with model {model_name}...")
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a professional UNESCO World Heritage travel writer. Output ONLY raw HTML."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=8000
            )
            full_response = response.choices[0].message.content
            
            if "<h2>" in full_response or "<p>" in full_response:
                start_index = full_response.find("<")
                html = full_response[start_index:] if start_index != -1 else full_response
            else:
                html = f"<p>Error parsing AI response.</p><p>{full_response}</p>"
            
            # Clean up any markdown code fences if present
            html = re.sub(r'^```html\s*', '', html, flags=re.IGNORECASE)
            html = re.sub(r'^```\s*', '', html)
            html = re.sub(r'\s*```$', '', html)
            
            PENDING_DIR.mkdir(parents=True, exist_ok=True)
            filename = sanitize_filename(topic)
            output_path = PENDING_DIR / filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            print(f"[Generator] Saved draft to: {output_path}")
            print(f"[Generator] Topic: {topic}")
            return
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "503" in error_str or "rate_limit" in error_str.lower():
                print(f"  [API SPIKE/LIMIT] Sleeping for 30 seconds... (Attempt {attempt+1}/{max_retries})")
                time.sleep(30)
            else:
                print(f"  [ERROR] {e}")
                break
    
    print("[ERROR] Failed to generate HTML after retries")

if __name__ == "__main__":
    main()