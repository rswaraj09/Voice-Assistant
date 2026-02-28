import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from engine.config import EMAIL_SENDER, EMAIL_PASSWORD

def send_email(receiver, subject, body):
    """
    Sends an email using Gmail SMTP and the credentials from .env.
    Returns True if successful, False otherwise.
    """
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("Error: EMAIL_SENDER or EMAIL_PASSWORD not set in .env")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = receiver
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
