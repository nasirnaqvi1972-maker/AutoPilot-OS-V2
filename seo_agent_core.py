import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load from the V2 .env file
load_dotenv()

API_KEY = os.getenv("FREE_LLM_API_KEY", "sk-local")
BASE_URL = os.getenv("FREE_LLM_API_BASE", "http://127.0.0.1:31415/v1")

def audit_draft(blog_text, current_title=""):
    llm = ChatOpenAI(
        openai_api_key=API_KEY,
        openai_api_base=BASE_URL,
        model="gemini-3.5-flash",
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
    
    print("🤖 Sending draft to FreeLLMAPI for Audit...")
    result_text = chain.invoke({"text": blog_text, "title": current_title})
    
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
        print("\n❌ FAILED to get a valid response.")