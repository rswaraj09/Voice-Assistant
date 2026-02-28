import re

def validate_email_data(recipient, subject, body):
    """
    Validates the generated email parameters before sending.
    Returns True if valid, False otherwise.
    """
    if not recipient or not subject or not body:
        print("Validation Failed: Missing required fields.")
        return False
        
    # Basic email regex
    email_regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if not re.match(email_regex, recipient):
        print(f"Validation Failed: Invalid recipient email address: {recipient}")
        return False
        
    if len(body.strip()) < 10:
        print("Validation Failed: Body too short.")
        return False
        
    return True
