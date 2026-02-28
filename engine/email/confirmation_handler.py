def confirm_and_send(recipient, subject, body, send_func):
    """
    Reads a preview of the email and asks the user for confirmation.
    If confirmed, triggers the send_func.
    """
    from engine.command import speak, takecommand
    
    preview = f"Email to {recipient}. Subject: {subject}. Should I send it?"
    print(f"\n[EMAIL PREVIEW]\nTo: {recipient}\nSubject: {subject}\nBody:\n{body}\n")
    print(preview)
    speak(preview)
    
    confirmation = takecommand()
    print(f"User confirmation: {confirmation}")
    
    if "yes" in confirmation.lower() or "yeah" in confirmation.lower() or "sure" in confirmation.lower() or "send" in confirmation.lower():
        speak("Sending email now.")
        success = send_func(recipient, subject, body)
        if success:
            speak("Email sent successfully.")
        else:
            speak("Failed to send the email. Please check your credentials.")
    else:
        speak("Okay, email canceled.")
