import os
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import errors
from sanitize_html import sanitize_post_html

load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not set. Add it to your .env file or environment variables.")

# Initialize the client
client = genai.Client(api_key=GOOGLE_API_KEY)

PROMPTS_DIR = Path("prompts")
DRAFTS_DIR = Path("drafts")

PILOT_MODE = False 
PILOT_LIMIT = 3

def test_api():
    print("Testing API connectivity...")
    # Try 3.8 first, fallback to 3.5-lite if Google is having a spike
    models_to_test = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
    
    for model_name in models_to_test:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents="Reply with exactly: MODEL_OK"
                )
                if "MODEL_OK" in response.text:
                    print(f"API Test Successful. Using model: {model_name}")
                    return model_name
            except errors.APIError as e:
                if e.code == 503:
                    print(f"  [{model_name} is overloaded] Waiting 15 seconds... (Attempt {attempt+1}/3)")
                    time.sleep(15)
                else:
                    print(f"  [{model_name} failed] {e}")
                    break # Try next model
            except Exception as e:
                 print(f"  [{model_name} error] {e}")
                 break
                 
    print("All models failed during testing.")
    return None

def main():
    model_name = test_api()
    if not model_name:
        print("Aborting. API connection failed entirely.")
        return

    prompt_files = list(PROMPTS_DIR.glob("*_prompt.txt"))
    print(f"Found {len(prompt_files)} prompts to process.")
    
    if PILOT_MODE:
        prompt_files = prompt_files[:PILOT_LIMIT]
        print(f"--- PILOT MODE: Processing only the first {PILOT_LIMIT} prompts ---")
    
    for i, prompt_path in enumerate(prompt_files, 1):
        revision_name = prompt_path.name.replace("_prompt.txt", "_revision.html")
        output_path = DRAFTS_DIR / revision_name
        
        if output_path.exists():
            print(f"[{i}/{len(prompt_files)}] Skipping {revision_name} (already exists).")
            continue
            
        print(f"[{i}/{len(prompt_files)}] Generating {revision_name}...")
        
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_text = f.read()
            
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt_text,
                )
                full_response = response.text
                
                if "<h2>" in full_response or "<p>" in full_response:
                    start_index = full_response.find("<")
                    html_content = full_response[start_index:] if start_index != -1 else full_response
                else:
                    html_content = f"<p>Error parsing AI response.</p><p>{full_response}</p>"

                # Automatically sanitize HTML before saving draft to disk
                html_content = sanitize_post_html(html_content)

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                    
                print(f"  [OK] Saved {revision_name}")
                time.sleep(5) 
                break 
                
            except errors.APIError as e:
                if e.code in [429, 503]:
                    print(f"  [API SPIKE/LIMIT: {e.code}] Sleeping for 30 seconds... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(30)
                else:
                    print(f"  [ERROR] API Error: {e}")
                    break
            except Exception as e:
                print(f"  [ERROR] Failed on {revision_name}: {e}")
                break

if __name__ == "__main__":
    main()
