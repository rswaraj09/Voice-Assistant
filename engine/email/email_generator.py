import google.generativeai as genai
from engine.config import LLM_KEY

genai.configure(api_key=LLM_KEY)

def generate_email_content(intent_data):
    """
    Generates the subject and body of the email based on intent data.
    Returns a tuple: (subject, body)
    """
    entities = intent_data.get("entities", {})
    email_type = entities.get("email_type", "general inquiry")
    tone = entities.get("tone", "formal")
    
    prompt = f"""
    Write a {tone} email about the following topic: {email_type}
    
    IMPORTANT: Provide the response in this exact format with NO markdown wrapping:
    SUBJECT: [Your Subject Line]
    BODY:
    [Your Email Body]
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # parse out subject and body
        subject = ""
        body = ""
        
        lines = content.split('\n')
        is_body = False
        for line in lines:
            if line.startswith("SUBJECT:"):
                subject = line.replace("SUBJECT:", "").strip()
            elif line.startswith("BODY:"):
                is_body = True
            elif is_body:
                body += line + "\n"
                
        return subject.strip(), body.strip()
    except Exception as e:
        print(f"Error generating email: {e}")
        return "", ""
