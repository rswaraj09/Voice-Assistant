import google.generativeai as genai
import json
from engine.config import LLM_KEY

genai.configure(api_key=LLM_KEY)

def extract_email_intent(query):
    """
    Extracts structured email data from a user query using Gemini.
    Returns a dict or None if not an email intent.
    """
    prompt = f"""
    You are an AI assistant parsing user commands. 
    Analyze the user query to see if they want to send an email. If yes, extract the recipient, email type/topic, and tone.
    Output ONLY valid JSON. Return an empty JSON object {{}} if it's not an email command or if you cannot find a valid recipient email.
    
    Format example:
    {{
      "intent": "send_email",
      "entities": {{
        "recipient": "xyz@gmail.com",
        "email_type": "leave request",
        "tone": "formal"
      }}
    }}
    
    Query: {query}
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        # Clean the response to ensure we only parse JSON
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        data = json.loads(text)
        if data and data.get("intent") == "send_email" and data.get("entities", {}).get("recipient"):
           return data
        return None
    except Exception as e:
        print(f"Error extracting intent: {e}")
        return None
