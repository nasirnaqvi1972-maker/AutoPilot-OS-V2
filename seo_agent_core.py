import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load from the V2 .env file
load_dotenv()

# --- CONFIGURATION & VALIDATION ---
API_KEY = os.getenv("FREE_LLM_API_KEY")
BASE_URL = os.getenv("FREE_LLM_API_BASE", "http://127.0.0.1:31415/v1")

if not API_KEY:
    print("❌ ERROR: FREE_LLM_API_KEY is not set in your .env file!")
    print("Please create a .env file in D:\\Projects\\AutoPilot_OS_v2\\ with:")
    print('FREE_LLM_API_KEY="your_actual_key_here"')
    print('FREE_LLM_API_BASE="http://127.0.0.1:31415/v1"')
    exit(1)

# Remove any accidental quotes from the key if the user pasted them
API_KEY = API_KEY.strip('"').strip("'")

def audit_draft(blog_text, current_title=""):
    llm = ChatOpenAI(
        openai_api_key=API_KEY,
        openai_api_base=BASE_URL,
        model="gpt-oss-120b",
        temperature=0.2
    )

    prompt = ChatPromptTemplate.from_template("""
    You are a strict SEO and AdSense Auditor. Analyze the following draft.
    You MUST respond ONLY in valid JSON format. Do not add markdown formatting like ```json.

    Draft Title: {title}
    Draft Text: {text}

    Provide a JSON object with exactly these keys:
    {{
        "adsense_safe": true/false,
        "adsense_violations": ["list of violations, empty if safe"],
        "seo_score": 1-100,
        "seo_critique": "A short, brutal paragraph on what is wrong.",
        "suggested_title": "A clickable SEO title under 60 chars",
        "suggested_meta_description": "A meta description under 155 chars",
        "required_changes": ["list of actionable changes"]
    }}
    """)

    chain = prompt | llm | StrOutputParser()
    
    print(f"🤖 Sending draft to FreeLLMAPI at {BASE_URL}...")
    try:
        result_text = chain.invoke({"text": blog_text, "title": current_title})
    except Exception as e:
        print(f"❌ API ERROR: {e}")
        return None
    
    result_text = result_text.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        print("⚠️ Error parsing JSON from LLM. Raw output:")
        print(result_text)
        return None

# --- TEST BLOCK ---
if __name__ == "__main__":
    print("Testing SEO Agent connection to FreeLLMAPI...")
    
    test_text = "<h1>My Trip</h1><p>I went to Paris. It was fun. Buy my stuff.</p>"
    test_title = "My Trip to Paris"
    
    result = audit_draft(test_text, test_title)
    
    if result:
        print("\n✅ SUCCESS! Here is the audit:")
        print(json.dumps(result, indent=4))
    else:
        print("\n❌ FAILED to get a valid response. Check your .env file and ensure FreeLLMAPI desktop app is running.")