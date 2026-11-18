import os
from pathlib import Path

DRAFTS_DIR = Path("drafts")
PROMPTS_DIR = Path("prompts")

PROMPT_TEMPLATE = """Act as a historical research assistant specializing in archaeology. 
Develop a distinctive, accurate, readable article about {site_name}.

Do NOT merely summarize the source. Explain the historical significance of the evidence. 
Maintain a research ledger. Distinguish established facts from scholarly interpretations. 
Do not invent controversies. Check the chronology carefully. 
Write for readers interested in South Asian and global history. Use clear prose. 
Include citations for important claims. 

Deliverables:
1. Research findings
2. Evidence gaps
3. Article outline
4. Draft article (Format this in pure HTML using <p>, <h2>, and <strong>. Do not wrap it in markdown ```html blocks, just give the raw HTML code).
5. Fact-check report

Here is the source text:
{source_text}
"""

def main():
    PROMPTS_DIR.mkdir(exist_ok=True)
    
    source_files = list(DRAFTS_DIR.glob("*_source.txt"))
    print(f"Found {len(source_files)} source files. Generating prompts...")

    count = 0
    for file_path in source_files:
        # Skip files that aren't source text (like previous revisions)
        if "revision" in file_path.name:
            continue
            
        site_name = file_path.name.replace("_source.txt", "").replace("_", " ").title()
        
        with open(file_path, "r", encoding="utf-8") as f:
            source_text = f.read()

        prompt_content = PROMPT_TEMPLATE.format(
            site_name=site_name,
            source_text=source_text
        )

        # Save the prompt to the prompts folder
        prompt_file = PROMPTS_DIR / file_path.name.replace("_source.txt", "_prompt.txt")
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(prompt_content)
            
        count += 1
        if count % 20 == 0:
            print(f"  Generated {count} prompts...")

    print(f"\nSUCCESS: Generated {count} prompts in the '{PROMPTS_DIR}' folder.")
    print("NEXT STEP: Open a prompt file, paste it into ChatGPT/Claude, and save the resulting HTML as '[site_name]_revision.html' in the drafts folder.")

if __name__ == "__main__":
    main()