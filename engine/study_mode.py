import os
import time
import re
import threading
import pdfplumber
import google.generativeai as genai
import tkinter as tk
from tkinter import filedialog
import eel
from engine.config import LLM_KEY
from engine.command import speak, takecommand
from engine.image_generator import handleImageGeneration, generate_image, open_image

def select_pdfs():
    """Opens a file dialog to select multiple PDF files."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    file_paths = filedialog.askopenfilenames(
        title="Select PDF files for Study Mode",
        filetypes=[("PDF files", "*.pdf")]
    )
    root.destroy()
    return file_paths

def extract_text_from_pdfs(file_paths):
    """Extracts text from a list of PDF files."""
    combined_text = ""
    for path in file_paths:
        try:
            with pdfplumber.open(path) as pdf:
                file_name = os.path.basename(path)
                combined_text += f"\n--- Start of File: {file_name} ---\n"
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        combined_text += text + "\n"
                combined_text += f"--- End of File: {file_name} ---\n"
        except Exception as e:
            print(f"[StudyMode] Error reading {path}: {e}")
    return combined_text

def generate_study_visual(context, query):
    """Generates an infographic or flowchart based on the context."""
    speak("Analyzing the content to generate a visual representation. This might take a moment.")
    
    genai.configure(api_key=LLM_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""Based on the following study material, create a detailed prompt for an image generator to create a {query}.
    The image should be a professional, high-quality, and educational visual (like an infographic or a flowchart).
    It should be clear, readable, and visually appealing.
    
    Study Material Context (Summary):
    {context[:2000]} 
    
    Return ONLY the image generation prompt."""
    
    try:
        response = model.generate_content(prompt)
        image_prompt = response.text.strip()
        
        speak(f"Generating {query} now.")
        filepath = generate_image(image_prompt)
        
        if filepath:
            speak(f"I've generated the {query}. Opening it for you.")
            open_image(filepath)
        else:
            speak(f"I'm sorry, I couldn't generate the {query} at this time.")
    except Exception as e:
        print(f"[StudyMode] Visual Gen Error: {e}")
        speak("I encountered an error while trying to generate the visual.")

def handleStudyMode():
    """Main loop for Study Mode — optimized for Syllabus-based learning."""
    speak("Study mode activated. Please select your syllabus or study materials PDF.")
    
    file_paths = select_pdfs()
    
    if not file_paths:
        speak("No files selected. Exiting study mode.")
        return
    
    speak(f"Got it. I'm analyzing the material according to Mumbai University standards. Please wait.")
    
    combined_text = extract_text_from_pdfs(file_paths)
    
    if not combined_text.strip():
        speak("I couldn't extract any text. Please try with a different PDF.")
        return
    
    # Configure Gemini
    genai.configure(api_key=LLM_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    # Step 1: Identify Topics from Syllabus
    speak("Extracting main topics from your syllabus...")
    topic_prompt = f"""Identify the top 5 key study topics from the following syllabus/material. 
    Format them as a simple numbered list.
    
    Material:
    {combined_text[:5000]}"""
    
    try:
        response = model.generate_content(topic_prompt)
        topics = response.text.strip()
        speak(f"I've identified these main topics: {topics}. Which one would you like to start with? Or you can name any specific topic.")
    except:
        speak("I've read the material. What specific topic would you like to study first?")

    while True:
        query = takecommand()
        
        if not query:
            continue
            
        if any(word in query for word in ["exit study", "stop study", "quit study", "close study", "exit", "stop"]):
            speak("Exiting study mode. Good luck with your exams!")
            break
            
        # Specific request for flowchart/diagram outside the auto-prompt
        if any(word in query for word in ["infographic", "flowchart", "diagram", "visual"]):
            visual_type = "infographic" if "infographic" in query else "flowchart"
            generate_study_visual(combined_text, visual_type)
            continue

        # Topic Explanation
        speak(f"Explaining {query} based on Mumbai University syllabus...")
        
        explain_prompt = f"""Explain the topic '{query}' as per the Mumbai University syllabus. 
        Keep the answer CRISP, professional, and point-wise (use bullet points). 
        Ensure it covers what is typically asked in university exams.
        
        Context Material:
        {combined_text[:20000]}
        
        Return the explanation clearly."""
        
        try:
            response = model.generate_content(explain_prompt)
            explanation = response.text.strip()
            speak(explanation)
            
            # Step 2: Proactively ask for Diagram
            time.sleep(1)
            speak("Would you like me to show a diagram or flowchart for this topic?")
            
            response = takecommand()
            if response and any(word in response for word in ["yes", "yeah", "sure", "show me", "okay", "ok"]):
                generate_study_visual(combined_text, f"flowchart or diagram for {query}")
                speak("Diagram generated. What else would you like to study?")
            else:
                speak("Alright. What's the next topic on your list?")
                
        except Exception as e:
            print(f"[StudyMode] Gemini Error: {e}")
            speak("I'm sorry, I'm having trouble explaining that topic. Try another one.")
