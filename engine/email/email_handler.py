"""
📧 Email Handler - Complete Rewrite
=====================================
Flow:
1. User says "send email" or "send a mail"
2. Assistant asks → "What is the email address?"
3. User speaks the email address
4. Assistant asks → "What is the subject?"
5. User speaks the subject
6. Gemini AI writes the full email body based on subject
7. Assistant reads preview and asks for confirmation
8. Sends via Gmail SMTP

Drop this file in your engine/ folder and update command.py (see bottom of file).
"""

import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import google.generativeai as genai
from engine.config import LLM_KEY, EMAIL_SENDER, EMAIL_PASSWORD
from engine.command import speak, takecommand

genai.configure(api_key=LLM_KEY)


# ════════════════════════════════════════════════════════════════════════════
#  STEP 1: Ask for email address via voice
# ════════════════════════════════════════════════════════════════════════════
def ask_email_address() -> str:
    """Ask user to speak the email address and clean it up."""
    speak("Sure! What is the recipient's email address?")
    
    for attempt in range(3):  # 3 attempts
        raw = takecommand()
        print(f"[Email] Raw spoken email: {raw}")
        
        if not raw:
            speak("I didn't catch that. Please say the email address again.")
            continue
        
        # Clean up common speech-to-text issues with email addresses
        email = raw.strip().lower()
        email = email.replace(" at ", "@")
        email = email.replace(" dot ", ".")
        email = email.replace(" ", "")          # remove all spaces
        email = email.replace("gmail", "gmail") # already fine
        
        # Fix common spoken patterns like "abc at the rate gmail dot com"
        email = re.sub(r'attherate', '@', email)
        email = re.sub(r'@+', '@', email)       # remove duplicate @
        email = re.sub(r'\.+', '.', email)      # remove duplicate dots
        
        # Validate it looks like an email
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            speak(f"Got it. Sending to {email}")
            return email
        else:
            speak(f"I heard {raw}, but that doesn't look like a valid email. Please try again. Say it like: example at gmail dot com")
    
    speak("I couldn't get a valid email address. Email cancelled.")
    return ""


# ════════════════════════════════════════════════════════════════════════════
#  STEP 2: Ask for subject via voice
# ════════════════════════════════════════════════════════════════════════════
def ask_subject() -> str:
    """Ask user to speak the email subject."""
    speak("What is the subject of the email?")
    subject = takecommand()
    
    if not subject or subject.strip() == "":
        speak("I didn't catch the subject. Email cancelled.")
        return ""
    
    speak(f"Subject is: {subject}. Got it.")
    return subject.strip()


# ════════════════════════════════════════════════════════════════════════════
#  STEP 3: Generate email body using Gemini AI
# ════════════════════════════════════════════════════════════════════════════
def generate_email_body(subject: str, recipient: str) -> str:
    """Use Gemini to write a professional email body based on subject."""
    speak("Let me write the email for you. One moment...")
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""Write a professional, formal email body for the following subject: "{subject}"

Rules:
- Write ONLY the email body text, nothing else
- No subject line, no "Subject:" prefix
- Start directly with the greeting like "Dear Sir/Madam," or appropriate greeting
- End with a professional sign-off like "Regards," followed by a blank line
- Keep it concise but complete (3-5 paragraphs max)
- No markdown, no bullet points, plain text only
- Make it sound human and natural
"""
        response = model.generate_content(prompt)
        body = response.text.strip()
        
        # Remove any accidental markdown
        body = re.sub(r'\*+', '', body)
        body = re.sub(r'#+', '', body)
        
        return body
        
    except Exception as e:
        print(f"[Email] Gemini error: {e}")
        speak("I had trouble writing the email body.")
        return ""


# ════════════════════════════════════════════════════════════════════════════
#  STEP 4: Preview & Confirm
# ════════════════════════════════════════════════════════════════════════════
def preview_and_confirm(recipient: str, subject: str, body: str) -> bool:
    """Read out email preview and ask for confirmation."""
    # Read a short preview (first 2 lines of body)
    preview_lines = [l for l in body.split('\n') if l.strip()]
    short_preview = " ".join(preview_lines[:2]) if preview_lines else body[:100]
    
    speak(f"Here is your email. To: {recipient}. Subject: {subject}. Preview: {short_preview}. Should I send it?")
    
    print(f"\n{'='*50}")
    print(f"📧 EMAIL PREVIEW")
    print(f"To: {recipient}")
    print(f"Subject: {subject}")
    print(f"Body:\n{body}")
    print(f"{'='*50}\n")
    
    confirmation = takecommand()
    print(f"[Email] Confirmation response: {confirmation}")
    
    if confirmation and any(w in confirmation.lower() for w in ["yes", "yeah", "sure", "send", "ok", "okay", "yep"]):
        return True
    else:
        speak("Okay, email cancelled.")
        return False


# ════════════════════════════════════════════════════════════════════════════
#  STEP 5: Send via Gmail SMTP
# ════════════════════════════════════════════════════════════════════════════
def send_email(recipient: str, subject: str, body: str) -> bool:
    """Send email via Gmail SMTP."""
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        speak("Email credentials are not set. Please update your config file.")
        print("[Email] ERROR: EMAIL_SENDER or EMAIL_PASSWORD not set in config.py")
        return False
    
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"[Email] ✅ Email sent to {recipient}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        speak("Authentication failed. Please check your Gmail app password in config.")
        print("[Email] ERROR: Gmail authentication failed. Make sure you're using an App Password.")
        return False
    except Exception as e:
        print(f"[Email] Send error: {e}")
        speak("Failed to send the email. Please check your internet connection.")
        return False


# ════════════════════════════════════════════════════════════════════════════
#  MAIN FUNCTION — call this from command.py
# ════════════════════════════════════════════════════════════════════════════
def handleEmail():
    """
    Full email pipeline triggered by voice command.
    Call this from command.py when 'email' or 'mail' is detected.
    """
    # Step 1: Get email address
    recipient = ask_email_address()
    if not recipient:
        return
    
    # Step 2: Get subject
    subject = ask_subject()
    if not subject:
        return
    
    # Step 3: Generate body with AI
    body = generate_email_body(subject, recipient)
    if not body:
        return
    
    # Step 4: Preview and confirm
    confirmed = preview_and_confirm(recipient, subject, body)
    if not confirmed:
        return
    
    # Step 5: Send
    speak("Sending your email now.")
    success = send_email(recipient, subject, body)
    
    if success:
        speak(f"Email sent successfully to {recipient}!")
    else:
        speak("Email could not be sent. Please check your credentials.")


"""
════════════════════════════════════════════════════════════════════════════
HOW TO UPDATE command.py
════════════════════════════════════════════════════════════════════════════

Replace the entire email block in command.py with this:

        elif "email" in query or "mail" in query:
            from engine.email_handler import handleEmail
            handleEmail()

That's it! Delete all the old intent_handler, email_generator,
email_validator, confirmation_handler imports — they are all 
handled inside this single file now.
════════════════════════════════════════════════════════════════════════════
"""
