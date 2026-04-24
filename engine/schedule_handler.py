import sqlite3
import threading
import datetime
import re
from engine.command import speak

DB_PATH = "nora.db"
_db_lock = threading.Lock()

def _get_connection():
    con = sqlite3.connect(DB_PATH)
    return con

def init_reminder_tables():
    """Initialize the reminders table."""
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                reminder_date TEXT,
                reminder_time TEXT,
                is_completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.commit()
        con.close()

def add_reminder(task, date=None, time=None):
    """Add a new reminder to the database."""
    if not date:
        date = datetime.date.today().strftime("%Y-%m-%d")
    
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO reminders (task, reminder_date, reminder_time) VALUES (?, ?, ?)",
            (task, date, time)
        )
        con.commit()
        con.close()
    return True

def remove_reminder(task_query):
    """Mark a task as completed/remove it based on a fuzzy search."""
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        # Simple fuzzy match: task contains the query
        cur.execute(
            "UPDATE reminders SET is_completed = 1 WHERE task LIKE ? AND is_completed = 0",
            ('%' + task_query + '%',)
        )
        rows_affected = cur.rowcount
        con.commit()
        con.close()
    return rows_affected > 0

def get_todays_reminders():
    """Get all uncompleted tasks for today."""
    today = datetime.date.today().strftime("%Y-%m-%d")
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute(
            "SELECT task FROM reminders WHERE reminder_date = ? AND is_completed = 0",
            (today,)
        )
        tasks = [row[0] for row in cur.fetchall()]
        con.close()
    return tasks

def clear_schedule():
    """Clear all uncompleted tasks for today."""
    today = datetime.date.today().strftime("%Y-%m-%d")
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute(
            "UPDATE reminders SET is_completed = 1 WHERE reminder_date = ? AND is_completed = 0",
            (today,)
        )
        count = cur.rowcount
        con.commit()
        con.close()
    return count

def daily_briefing():
    """Speak the list of tasks for today."""
    tasks = get_todays_reminders()
    if not tasks:
        speak("You have no tasks scheduled for today. It's a clear day!")
    else:
        speak(f"Sir, you have {len(tasks)} tasks remaining for today.")
        for i, task in enumerate(tasks, 1):
            speak(f"Task {i}: {task}")
        speak("Would you like to complete any of these or add a new task?")

def handle_reminder_command(query):
    """
    Parse the query to add, remove, or view reminders.
    """
    q = query.lower()

    # VIEW SCHEDULE
    if any(w in q for w in ["show my schedule", "view my schedule", "what is my schedule", "what's my schedule", "tell me my schedule", "daily briefing"]):
        daily_briefing()
        return True

    # CLEAR ALL TASKS
    if any(w in q for w in ["clear my schedule", "remove all tasks", "delete all tasks", "cancel all my schedule", "clear schedule"]):
        count = clear_schedule()
        if count > 0:
            speak(f"Sir, I've cleared your schedule for today. {count} tasks removed.")
        else:
            speak("Your schedule is already clear.")
        return True

    # REMOVE TASK
    if any(w in q for w in ["remove", "delete", "complete", "done with"]):
        # Check for task numbers like "remove task 1"
        num_match = re.search(r'(?:task|reminder|number)\s+(\d+)', q)
        if num_match:
            index = int(num_match.group(1)) - 1
            tasks = get_todays_reminders()
            if 0 <= index < len(tasks):
                task_to_remove = tasks[index]
                if remove_reminder(task_to_remove):
                    speak(f"Okay, I've marked task {index + 1}, {task_to_remove}, as completed.")
                    return True
            else:
                speak(f"I don't see a task with number {index + 1}.")
                return True

        # Extract what to remove (fuzzy name)
        match = re.search(r'(?:remove|delete|done with|complete)\s+(.+?)(?:\s+from|\s+task|\s+reminder|$)', q)
        if match:
            task_to_remove = match.group(1).strip()
            if task_to_remove == "it":
                # Special case: "remove it" — if there's only one task, remove it.
                tasks = get_todays_reminders()
                if len(tasks) == 1:
                    task_to_remove = tasks[0]
                else:
                    speak("Which task should I remove?")
                    return True
            
            if remove_reminder(task_to_remove):
                speak(f"Okay, I've marked {task_to_remove} as completed.")
                return True

    # ADD TASK
    # Stricter trigger to avoid false positives with 'show' or 'clear'
    if any(w in q for w in ["remind me to", "add to schedule", "add to my schedule", "add schedule"]):
        # Extract task
        task = ""
        if "remind me to" in q:
            task = q.split("remind me to")[-1].strip()
        elif "add to my schedule" in q:
            task = q.split("add to my schedule")[-1].strip()
        elif "add to schedule" in q:
            task = q.split("add to schedule")[-1].strip()
        elif "add schedule" in q:
            task = q.split("add schedule")[-1].strip()
        
        if task:
            # Basic time extraction
            time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))', task)
            task_time = time_match.group(1) if time_match else None
            if task_time:
                task = task.replace(task_time, "").strip()
            
            # Remove filler words
            task = task.replace("my calendar", "").replace("my tasks", "").replace("to do", "").strip()
            
            if task:
                add_reminder(task, time=task_time)
                speak(f"Sure, I've added {task} to your schedule" + (f" for {task_time}." if task_time else "."))
                return True

    return False

# Initialize on import
init_reminder_tables()
