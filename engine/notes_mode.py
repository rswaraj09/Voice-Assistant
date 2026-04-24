import os
import time
import textwrap
import tempfile
import re
import eel
import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib import colors
from engine.config import LLM_KEY
from engine.command import speak, takecommand

def generate_beautiful_pdf(text, filename):
    """
    Converts markdown-like text to a beautiful PDF using ReportLab Platypus.
    Supports basic HTML-like tags for colors and formatting.
    """
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=26,
        textColor=colors.dodgerblue,
        alignment=1, # Center
        spaceAfter=30
    )
    
    h1_style = ParagraphStyle(
        'H1Style',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.darkblue,
        spaceBefore=15,
        spaceAfter=10
    )
    
    h2_style = ParagraphStyle(
        'H2Style',
        parent=styles['Heading2'],
        fontSize=15,
        textColor=colors.darkcyan,
        spaceBefore=12,
        spaceAfter=8
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=12,
        leading=16,
        spaceAfter=6
    )
    
    story = []
    
    # Add Title
    story.append(Paragraph("Voice Assistant Notes", title_style))
    story.append(Spacer(1, 12))
    
    # Process lines
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 10))
            continue
            
        p_style = body_style
        processed_line = line
        
        # Headings
        if line.startswith('### '):
            p_style = styles['Heading3']
            processed_line = line[4:]
        elif line.startswith('## '):
            p_style = h2_style
            processed_line = line[3:]
        elif line.startswith('# '):
            p_style = h1_style
            processed_line = line[2:]
        elif line.startswith('- ') or line.startswith('* '):
            processed_line = "• " + line[2:]
            
        # Bold **text** -> <b>text</b>
        processed_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', processed_line)
        
        # Colors: [blue]text[/blue] -> <font color="blue">text</font>
        # We'll support standard colors
        processed_line = re.sub(r'\[(red|blue|green|orange|purple|dodgerblue|cyan|magenta)\](.*?)\[/\1\]', 
                               r'<font color="\1">\2</font>', processed_line, flags=re.IGNORECASE)
        
        try:
            story.append(Paragraph(processed_line, p_style))
        except:
            # Fallback if XML is malformed
            clean_line = processed_line.replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(clean_line, p_style))
            
    doc.build(story)

def handleNotesMode():
    """
    Enters a non-conversational mode that just listens and transcribes.
    Then shows raw text and offers conversion to a beautiful PDF.
    """
    speak("Notes mode activated. I'm just listening. Tell me everything. Say 'stop notes' when you're finished.")
    
    raw_transcriptions = []
    
    while True:
        print("[NotesMode] Listening...")
        query = takecommand()
        
        if not query:
            continue
            
        # Exit condition
        if any(word in query.lower() for word in ["stop notes", "stop nodes", "exit notes", "finish notes"]):
            speak("Stopping notes mode.")
            break
            
        print(f"[NotesMode] Captured: {query}")
        raw_transcriptions.append(query)
        
        # Update UI with the latest chunk
        try:
            eel.DisplayMessage(f"Captured: {query}")
        except:
            pass

    if not raw_transcriptions:
        speak("I didn't catch any notes. Returning to normal mode.")
        return

    full_raw_text = "\n".join(raw_transcriptions)
    
    # Show "plain notepad text" by opening a temporary .txt file
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w') as f:
            f.write("--- VOICE NOTES CAPTURED ---\n\n")
            f.write(full_raw_text)
            temp_path = f.name
        
        os.startfile(temp_path)
        speak("I've opened the captured text in Notepad for you.")
    except Exception as e:
        print(f"[NotesMode] Notepad Error: {e}")
        speak("I couldn't open Notepad, but I have your notes.")

    # Wait for conversion command
    speak("Would you like me to convert these into a beautiful PDF?")
    
    # We enter a small loop to wait specifically for the conversion command
    start_time = time.time()
    while time.time() - start_time < 30: # 30 second timeout
        response = takecommand()
        if not response:
            continue
            
        if any(word in response.lower() for word in ["convert it into pdf", "convert to pdf", "make pdf", "convert it", "yes", "sure"]):
            speak("Structuring your notes and creating a beautiful PDF...")
            
            # Use Gemini to structure it
            genai.configure(api_key=LLM_KEY)
            # Using gemini-2.5-flash as used in the rest of the project
            model = genai.GenerativeModel("gemini-2.5-flash") 
            
            prompt = f"""Structure these raw spoken notes into beautiful, professional markdown. 
            Use headings (# ## ###), bullet points, and bold text (**text**). 
            Add color hints for key terms or headings using the format [colorname]text[/colorname]. 
            Valid colors to use: red, blue, green, orange, purple, dodgerblue, cyan.
            
            Raw Notes:
            {full_raw_text}
            
            Return ONLY the structured markdown-like text."""
            
            try:
                gen_response = model.generate_content(prompt)
                structured_notes = gen_response.text.strip()
                
                # Save to PDF
                downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                pdf_filename = os.path.join(downloads_path, f"Structured_Notes_{timestamp}.pdf")
                
                generate_beautiful_pdf(structured_notes, pdf_filename)
                speak(f"Done! I've saved your beautiful PDF in your Downloads folder. Opening it now.")
                os.startfile(pdf_filename)
            except Exception as e:
                print(f"[NotesMode] Gemini/PDF Error: {e}")
                speak("I had some trouble creating the beautiful PDF. I'll stick to the raw text.")
            
            break
        
        elif any(word in response.lower() for word in ["no", "cancel", "stop", "exit", "nothing"]):
            speak("Alright, keeping the raw notes in Notepad.")
            break
            
    speak("Notes mode deactivated. I'm ready for your next command.")

