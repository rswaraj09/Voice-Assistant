import os
import re
import json
import subprocess
import time
import threading
import webbrowser



def handleCodeGeneration(query):
    from engine.command import speak, takecommand
    from engine.config import LLM_KEY
    import google.generativeai as genai

    speak("Sure!")

    # Ask where to save
    speak("Where would you like to save this project?")
    save_path_response = takecommand()
    save_dir     = _parse_save_path(save_path_response)
    stack        = _detect_stack(query)
    project_name = _extract_project_name(query)

    speak(f"Saving to {save_dir}. Generating all files now.")
    print(f"[CodeGen] Project: {project_name} | Stack: {stack['backend']} + {stack['database']}")

    genai.configure(api_key=LLM_KEY)

    file_specs      = _get_file_specs(query, stack, project_name)
    total           = len(file_specs)

    # Generate all files — parallel batched with rate limiting
    speak("Generating project files.")
    generated_files = smart_generate_with_batching(file_specs, genai)

    # If the fast path failed catastrophically, fall back to sequential.
    if len(generated_files) < total // 2:
        print("[CodeGen] Parallel path underperformed — falling back to sequential.")
        generated_files = _sequential_generate(file_specs, genai)

    print(f"[CodeGen] Generated {len(generated_files)}/{total} files.")

    # Validate + one targeted re-generation pass for syntax failures
    report = _validate_and_maybe_regenerate(
        generated_files, file_specs, genai, stack.get("lang", "flask")
    )
    speak(
        f"Generated {len(generated_files)} files. "
        f"{report['summary']['syntax_errors']} syntax issues."
    )

    if not generated_files:
        speak("Sorry, generation failed completely. Please try again.")
        return

    # Inject guaranteed MongoDB connection into backend
    backend_file = stack["backend_file"]
    if backend_file in generated_files:
        generated_files[backend_file] = _inject_mongo_connection(
            generated_files[backend_file], stack["lang"], project_name
        )
        print(f"[CodeGen] MongoDB connection injected into {backend_file}")

    # Build project data
    project_data = {
        "project_name":    project_name,
        "description":     query,
        "tech_stack":      stack,
        "files":           [{"path": k, "content": v} for k, v in generated_files.items()],
        "run_command":     stack["run_command"],
        "install_command": stack["install_command"],
        "start_url":       "http://localhost:5000",
        "notes":           f"MongoDB database: {project_name} | mongodb://localhost:27017/{project_name}"
    }

    # Create project files
    project_dir = os.path.join(save_dir, project_name)
    speak(f"Creating {len(generated_files)} files.")
    success = _create_project_files(project_dir, project_data)

    if not success:
        speak("Sorry, I had trouble creating the files. Please check folder permissions.")
        return

    speak(f"Project created with {len(generated_files)} files.")

    # Install dependencies
    install_cmd = stack["install_command"]
    if install_cmd:
        speak("Installing dependencies.")
        try:
            subprocess.run(install_cmd, shell=True, cwd=project_dir, timeout=120)
            speak("Done.")
        except subprocess.TimeoutExpired:
            speak("Installation is taking long. It will continue in background.")
        except Exception as e:
            print(f"[CodeGen] Install error: {e}")
            speak("Installation may need manual check.")

    # Open in VS Code
    speak("Open in VS Code?")
    if _yes(takecommand()):
        _open_in_vscode(project_dir)
        speak("Opened.")
    else:
        speak("No problem.")

    # Run server
    run_cmd   = stack["run_command"]
    start_url = "http://localhost:5000"

    speak("Start the server?")
    if _yes(takecommand()):
        speak(f"Starting server and opening {start_url}.")
        _run_server(run_cmd, project_dir, start_url)
    else:
        speak(f"When ready, run: {run_cmd} in the project folder.")

    speak(f"MongoDB database name is {project_name}. Make sure MongoDB is running.")
    speak("Project is ready!")


def _strip_fences(content):
    content = re.sub(r'^```\w*\s*\n?', '', content)
    content = re.sub(r'\n?```\s*$',    '', content)
    return content.strip()


def _generate_one(spec, genai_mod, max_attempts=3):
    name, prompt = spec
    if prompt.startswith("PREFILLED:"):
        return name, prompt[10:], True
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            model = genai_mod.GenerativeModel("gemini-2.5-flash")
            resp  = model.generate_content(prompt)
            content = _strip_fences((resp.text or "").strip())
            if len(content) < 50:
                raise ValueError(f"Response too short ({len(content)} chars)")
            return name, content, True
        except Exception as e:
            last_err = e
            # Exponential backoff: 1s, 2s, 4s
            time.sleep(2 ** (attempt - 1))
    print(f"[CodeGen] ✗ {name}: {last_err}")
    return name, "", False


def smart_generate_with_batching(file_specs, genai_mod, max_workers=4):
    """
    Parallel generation with a worker cap to respect Gemini rate limits.
    Pre-filled specs run synchronously (free); the rest go through the pool.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {}
    prefilled = [s for s in file_specs if s[1].startswith("PREFILLED:")]
    live      = [s for s in file_specs if not s[1].startswith("PREFILLED:")]

    for name, prompt in prefilled:
        results[name] = prompt[10:]
        print(f"[CodeGen] ✓ {name} (pre-filled)")

    total = len(live)
    if not live:
        return results

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_generate_one, spec, genai_mod): spec[0] for spec in live}
        done = 0
        for fut in as_completed(futures):
            name, content, ok = fut.result()
            done += 1
            if ok and content:
                results[name] = content
                print(f"[CodeGen] ✓ {name} ({done}/{total})")
            else:
                print(f"[CodeGen] ✗ {name} ({done}/{total})")
    return results


def _validate_and_maybe_regenerate(generated_files, file_specs, genai_mod, backend_kind):
    """
    Run the completeness report and re-generate any files whose content
    failed syntax validation. Only one re-try pass — avoids infinite loops
    when a prompt is inherently buggy.
    """
    try:
        from engine.validators import verify_project_completeness, validate_generated_file
    except Exception as e:
        print(f"[CodeGen] Validation skipped: {e}")
        return {"summary": {"syntax_errors": 0, "files": len(generated_files),
                            "missing_critical": 0, "py_undeclared": 0, "js_undeclared": 0},
                "issues": [], "missing": [], "ok": True}

    report = verify_project_completeness(generated_files, backend_kind=backend_kind)
    print(f"[CodeGen] Validation: {report['summary']}")

    bad_paths = [p for p, c in generated_files.items() if not validate_generated_file(p, c)["ok"]]
    if not bad_paths:
        return report

    print(f"[CodeGen] Retrying {len(bad_paths)} failed file(s): {bad_paths}")
    specs_by_name = {s[0]: s for s in file_specs}
    retry_specs = [specs_by_name[p] for p in bad_paths if p in specs_by_name]
    if not retry_specs:
        return report

    regenerated = smart_generate_with_batching(retry_specs, genai_mod, max_workers=2)
    # Only replace if the retry actually improved things.
    for path, content in regenerated.items():
        if validate_generated_file(path, content)["ok"]:
            generated_files[path] = content
            print(f"[CodeGen] ✓ re-gen succeeded for {path}")

    final = verify_project_completeness(generated_files, backend_kind=backend_kind)
    print(f"[CodeGen] After re-gen: {final['summary']}")
    return final


def _sequential_generate(file_specs, genai_mod):
    """Original slow-but-stable path, used as fallback."""
    results = {}
    for i, spec in enumerate(file_specs, 1):
        name, content, ok = _generate_one(spec, genai_mod)
        if ok and content:
            results[name] = content
            print(f"[CodeGen] ✓ {name} ({i}/{len(file_specs)})")
        time.sleep(0.5)
    return results



#  INJECT GUARANTEED MONGODB CONNECTION

def _inject_mongo_connection(code, lang, project_name):
    if lang == "flask":
        mongo_block = f"""
# ── MongoDB Connection ────────────────────────────────────────────────────
from pymongo import MongoClient
import bcrypt

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME   = os.getenv('DB_NAME',   '{project_name}')

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()
    db    = client[DB_NAME]
    users = db['users']
    print(f"[MongoDB] Connected to database: {{DB_NAME}}")
except Exception as e:
    print(f"[MongoDB] Connection failed: {{e}}")
    print("[MongoDB] Make sure MongoDB is running: net start MongoDB")
# ─────────────────────────────────────────────────────────────────────────
"""
        # Remove existing connection code
        code = re.sub(r'.*MongoClient.*\n',        '', code)
        code = re.sub(r'.*client\s*=\s*Mongo.*\n', '', code)
        code = re.sub(r'.*db\s*=\s*client\[.*\n',  '', code)
        code = re.sub(r'.*users\s*=\s*db\[.*\n',   '', code)
        code = re.sub(r'.*import pymongo.*\n',      '', code)
        code = re.sub(r'.*from pymongo.*\n',        '', code)
        code = re.sub(r'.*import bcrypt.*\n',       '', code)

        # Remove in-memory fake database lists Gemini generates
        # These lists overwrite the real MongoDB collections if not removed
        # e.g. users = [...], rooms = [...], bookings = [...]
        code = re.sub(r'^users\s*=\s*\[.*?\]',    '', code, flags=re.DOTALL | re.MULTILINE)
        code = re.sub(r'^rooms\s*=\s*\[.*?\]',    '', code, flags=re.DOTALL | re.MULTILINE)
        code = re.sub(r'^bookings\s*=\s*\[.*?\]', '', code, flags=re.DOTALL | re.MULTILINE)
        code = re.sub(r'^products\s*=\s*\[.*?\]', '', code, flags=re.DOTALL | re.MULTILINE)
        code = re.sub(r'^orders\s*=\s*\[.*?\]',   '', code, flags=re.DOTALL | re.MULTILINE)
        code = re.sub(r'^students\s*=\s*\[.*?\]', '', code, flags=re.DOTALL | re.MULTILINE)
        code = re.sub(r'^employees\s*=\s*\[.*?\]','', code, flags=re.DOTALL | re.MULTILINE)
        code = re.sub(r'^items\s*=\s*\[.*?\]',    '', code, flags=re.DOTALL | re.MULTILINE)

        # Remove simulated/in-memory database comment blocks
        code = re.sub(r'#\s*[-–—=]+\s*[Ss]imulat.*?#\s*[-–—=]+\s*\n', '', code, flags=re.DOTALL)
        code = re.sub(r'#.*[Ii]n-[Mm]emory.*\n',  '', code)
        code = re.sub(r'#.*[Ss]imulat.*\n',        '', code)
        code = re.sub(r'#.*[Ff]ake\s*[Dd]ata.*\n', '', code)

        # Remove fake ID counter variables
        code = re.sub(r'^\w+_id_counter\s*=.*\n', '', code, flags=re.MULTILINE)
        code = re.sub(r'^user_id_counter\s*=.*\n', '', code, flags=re.MULTILINE)
        code = re.sub(r'^room_id_counter\s*=.*\n', '', code, flags=re.MULTILINE)
        code = re.sub(r'^booking_id_counter\s*=.*\n', '', code, flags=re.MULTILINE)

        # Remove helper functions that use in-memory lists
        code = re.sub(r'def is_logged_in\(\).*?(?=\ndef |\n@app)', '', code, flags=re.DOTALL)
        code = re.sub(r'def get_current_user\(\).*?(?=\ndef |\n@app)', '', code, flags=re.DOTALL)
        code = re.sub(r'def is_admin\(\).*?(?=\ndef |\n@app)', '', code, flags=re.DOTALL)

        # Guaranteed login route
        login_fix = '''
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user     = users.find_one({'email': email})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            session['user_id'] = str(user['_id'])
            session['name']    = user.get('name', 'User')
            session['role']    = user.get('role', 'user')
            if session['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        flash('Invalid email or password. Please try again.', 'danger')
        return redirect(url_for('login'))
    return render_template('login.html')
'''
        #  Guaranteed signup route
        signup_fix = '''
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role     = request.form.get('role', 'user')
        if users.find_one({'email': email}):
            flash('Email already registered. Please login.', 'danger')
            return redirect(url_for('signup'))
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        users.insert_one({'name': name, 'email': email, 'password': hashed, 'role': role})
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')
'''
        # Replace Gemini login/signup with guaranteed versions
        code = re.sub(
            r'@app\.route\([\'\"]/login.*?(?=@app\.route|if __name__)',
            login_fix + '\n\n', code, flags=re.DOTALL
        )
        code = re.sub(
            r'@app\.route\([\'\"]/signup.*?(?=@app\.route|if __name__)',
            signup_fix + '\n\n', code, flags=re.DOTALL
        )

        # Inject mongo block after last import line
        lines       = code.split('\n')
        last_import = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                last_import = i
        lines.insert(last_import + 1, mongo_block)
        return '\n'.join(lines)

    elif lang == "node":
        mongo_block = f"""
// ── MongoDB Connection ──────────────────────────────────────────────────
const mongoose = require('mongoose');
const MONGO_URI = process.env.MONGO_URI || 'mongodb://localhost:27017/';
const DB_NAME   = process.env.DB_NAME   || '{project_name}';
mongoose.connect(MONGO_URI + DB_NAME)
    .then(() => console.log('[MongoDB] Connected to database:', DB_NAME))
    .catch(err => {{
        console.error('[MongoDB] Connection failed:', err.message);
        console.log('[MongoDB] Make sure MongoDB is running');
    }});
// ────────────────────────────────────────────────────────────────────────
"""
        code = re.sub(r'mongoose\.connect\(.*?\);?\n', '', code, flags=re.DOTALL)
        code = re.sub(r'.*require\([\'"]mongoose[\'"]\).*\n', '', code)

        lines        = code.split('\n')
        last_require = 0
        for i, line in enumerate(lines):
            if 'require(' in line:
                last_require = i
        lines.insert(last_require + 1, mongo_block)
        return '\n'.join(lines)

    return code



#  DETECT TECH STACK

def _detect_stack(query):
    q = query.lower()
    if "node" in q or "express" in q:
        return {
            "frontend": "HTML5/CSS3/JS", "backend": "Node.js Express", "database": "MongoDB",
            "backend_file": "server.js", "run_command": "node server.js",
            "install_command": "npm install express mongoose bcryptjs express-session dotenv",
            "lang": "node"
        }
    elif "django" in q:
        return {
            "frontend": "Django Templates", "backend": "Python Django", "database": "SQLite",
            "backend_file": "manage.py", "run_command": "python manage.py runserver",
            "install_command": "pip install django", "lang": "django"
        }
    elif "php" in q:
        return {
            "frontend": "HTML5/CSS3/JS", "backend": "PHP", "database": "MySQL",
            "backend_file": "index.php", "run_command": "php -S localhost:5000",
            "install_command": "", "lang": "php"
        }
    else:
        return {
            "frontend": "HTML5/CSS3/JS", "backend": "Python Flask", "database": "MongoDB",
            "backend_file": "app.py", "run_command": "python app.py",
            "install_command": "pip install flask pymongo flask-session bcrypt python-dotenv",
            "lang": "flask"
        }


# FILE SPECS — focused prompts per file

def _get_file_specs(query, stack, project_name):
    lang = stack["lang"]

    if lang == "flask":
        backend_prompt = f"""Write a complete Flask backend Python file for: "{query}"

Include these exact imports at the top:
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback-key')

Include ALL these routes:
- GET /  → render_template('index.html')
- GET /login, POST /login
- GET /signup, POST /signup
- GET /logout → session.clear(), redirect to /
- GET /dashboard → check session['user_id'], render dashboard.html
- GET /admin_dashboard → check session + role == admin, render admin.html
- Any additional routes relevant to: "{query}"

CRITICAL RULES:
- DO NOT create any Python lists like users = [...] or rooms = [...] or bookings = [...]
- DO NOT create any in-memory fake database or simulated data
- DO NOT create helper functions like is_logged_in(), get_current_user(), is_admin()
- DO NOT include MongoClient, bcrypt imports or db connection (added automatically)
- DO NOT use csrf_token anywhere
- Use flash() for all user messages
- Use session['user_id'] to check authentication in protected routes
- End with: if __name__ == '__main__': app.run(debug=True)

Return ONLY complete Python code, no markdown."""

    elif lang == "node":
        backend_prompt = f"""Write a complete Express.js backend for: "{query}"
Include all auth and feature routes.
DO NOT include mongoose.connect (added automatically).
DO NOT create any in-memory arrays or fake data.
app.listen(process.env.PORT || 5000);
Return ONLY JavaScript, no markdown."""
    else:
        backend_prompt = f"Write complete {stack['backend']} backend for: '{query}'. Return ONLY code."

    login_prompt = f"""Write a COMPLETE login page HTML file for a {query} system.

Requirements:
- Full HTML document: <!DOCTYPE html>, <html>, <head> with charset and title, <body>
- ALL CSS must be inside a <style> tag in <head>
- Beautiful modern login form design with good colors
- Email input: <input type="email" name="email" required>
- Password input: <input type="password" name="password" required>
- Show/hide password toggle button with eye icon
- Flash message display using Jinja2 EXACTLY like this (NO csrf_token):
  {{% with messages = get_flashed_messages(with_categories=true) %}}
    {{% for category, message in messages %}}
      <div class="alert alert-{{{{ category }}}}">{{{{ message }}}}</div>
    {{% endfor %}}
  {{% endwith %}}
- .alert-danger = red background, .alert-success = green background
- Submit button
- Link to signup: <a href="/signup">Create account</a>
- Form tag: <form method="POST" action="/login">
- Closing </body> and </html> tags

Return ONLY the complete HTML file, no explanation, no markdown."""

    signup_prompt = f"""Write a COMPLETE signup/registration HTML file for a {query} system.

Requirements:
- Full HTML document with ALL CSS in <style> tag
- Beautiful modern signup form
- Full Name: <input type="text" name="name" required>
- Email: <input type="email" name="email" required>
- Password: <input type="password" name="password" required>
- Confirm Password: <input type="password" name="confirm_password" required>
- Role dropdown: <select name="role"><option value="user">User</option><option value="admin">Admin</option></select>
- Flash message display (same Jinja2 pattern, NO csrf_token)
- JavaScript to check passwords match before submit
- <form method="POST" action="/signup">
- Link to login: <a href="/login">Already have account? Login</a>
- Closing </body></html>

Return ONLY the complete HTML file, no explanation, no markdown."""

    index_prompt = f"""Write a COMPLETE homepage HTML file for a {query} system.

Requirements:
- Full HTML document with ALL CSS in <style> tag
- Professional navigation bar with: site name/logo, Login button (/login), Signup button (/signup)
- Hero section: title, subtitle, call-to-action buttons
- Features section: 3-4 feature cards describing the system
- Footer with copyright
- Modern professional design with good color scheme
- Closing </body></html>

Return ONLY the complete HTML file, no explanation, no markdown."""

    dashboard_prompt = f"""Write a COMPLETE user dashboard HTML file for a {query} system.

Requirements:
- Full HTML document with ALL CSS in <style> tag
- Top navbar: site name | Welcome {{{{ session.get('name', 'User') }}}} | Logout link (/logout)
- Sidebar with navigation menu relevant to: "{query}"
- Main content: 3-4 stat cards, recent activity section, relevant widgets
- Professional dashboard design (dark sidebar, light content area)
- Closing </body></html>

Return ONLY the complete HTML file, no explanation, no markdown."""

    admin_prompt = f"""Write a COMPLETE admin dashboard HTML file for a {query} system.

Requirements:
- Full HTML document with ALL CSS in <style> tag
- Top navbar: site name | Admin badge | {{{{ session.get('name', 'Admin') }}}} | Logout (/logout)
- Sidebar: Dashboard, Manage Users, All Records, Reports, Settings
- Stats cards: Total Users, Active Sessions, Total Records, Revenue (if applicable)
- Users table with columns: Name, Email, Role, Date Joined, Actions
- Professional admin panel design
- Closing </body></html>

Return ONLY the complete HTML file, no explanation, no markdown."""

    css_prompt = f"""Write a COMPLETE CSS stylesheet for a {query} web application.

Include ALL of these:
- CSS reset: *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
- Root variables: --primary, --secondary, --danger, --success, --bg, --text
- Body base styles and typography
- .navbar styles with flexbox layout
- .btn, .btn-primary, .btn-secondary, .btn-danger styles
- .form-group, .form-control, .form-label styles
- .card, .card-header, .card-body styles
- .alert, .alert-danger {{ background: #f8d7da; color: #721c24; }}, .alert-success {{ background: #d4edda; color: #155724; }} styles
- .sidebar styles for dashboard layout
- .main-content styles
- .stat-card styles with icons
- .table, .table-striped styles
- Responsive @media (max-width: 768px) rules

Return ONLY CSS code, no markdown."""

    js_prompt = f"""Write COMPLETE JavaScript for a {query} web application.

Include:
- DOMContentLoaded event listener wrapper
- Email format validation (regex test)
- Password length check (minimum 6 characters)
- Confirm password match validation on signup
- Show/hide password toggle function (toggles input type between password and text)
- Auto-hide flash/alert messages after 4 seconds with fadeOut effect
- Form submit validation that prevents submission if required fields are empty
- Any interactive features specific to: "{query}"

Return ONLY JavaScript code, no markdown."""

    # Config files — pre-filled, no Gemini needed
    if lang == "flask":
        config = [
            ("requirements.txt", "PREFILLED:flask\npymongo\nbcrypt\nflask-session\npython-dotenv\ndnspython"),
            (".env", f"PREFILLED:MONGO_URI=mongodb://localhost:27017/\nDB_NAME={project_name}\nSECRET_KEY=nora-super-secret-key-change-in-production\nDEBUG=True"),
        ]
    elif lang == "node":
        pkg = json.dumps({
            "name": project_name, "version": "1.0.0", "main": "server.js",
            "scripts": {"start": "node server.js"},
            "dependencies": {
                "express": "^4.18.0", "mongoose": "^7.0.0",
                "bcryptjs": "^2.4.3", "express-session": "^1.17.3", "dotenv": "^16.0.0"
            }
        }, indent=2)
        config = [
            ("package.json", f"PREFILLED:{pkg}"),
            (".env", f"PREFILLED:MONGO_URI=mongodb://localhost:27017/\nDB_NAME={project_name}\nSECRET_KEY=nora-super-secret-key\nPORT=5000"),
        ]
    else:
        config = [(".env", f"PREFILLED:MONGO_URI=mongodb://localhost:27017/\nDB_NAME={project_name}\nSECRET_KEY=nora-super-secret-key")]

    return [
        (stack["backend_file"],       backend_prompt),
        ("templates/index.html",      index_prompt),
        ("templates/login.html",      login_prompt),
        ("templates/signup.html",     signup_prompt),
        ("templates/dashboard.html",  dashboard_prompt),
        ("templates/admin.html",      admin_prompt),
        ("static/css/style.css",      css_prompt),
        ("static/js/main.js",         js_prompt),
    ] + config



#  EXTRACT PROJECT NAME

def _extract_project_name(query):
    match = re.search(
        r'(?:create|make|build|generate)\s+(?:a\s+|an\s+)?(.+?)(?:\s+in\s+|\s+using\s+|\s+with\s+|$)',
        query, re.IGNORECASE
    )
    if match:
        name = match.group(1).strip().lower()
        name = re.sub(r'[^a-z0-9\s]', '', name)
        return name.replace(' ', '_')[:40]
    return "my_project"



#  PARSE SAVE PATH FROM VOICE

def _parse_save_path(response):
    if not response:
        return os.path.join("D:\\", "Projects")
    response = response.lower().strip()

    path_match = re.search(r'[a-z]:\\[\w\\]+', response, re.IGNORECASE)
    if path_match:
        return path_match.group()

    if "desktop"  in response: return os.path.join(os.path.expanduser("~"), "Desktop",   "Projects")
    if "document" in response: return os.path.join(os.path.expanduser("~"), "Documents", "Projects")
    if "download" in response: return os.path.join(os.path.expanduser("~"), "Downloads", "Projects")

    drive_match = re.search(r'\b([a-z])\s*(?:drive|disk)?\b', response)
    if drive_match:
        drive = drive_match.group(1).upper()
        folder_match = re.search(r'(?:in|inside|folder|at)\s+(\w+)', response)
        if folder_match:
            return os.path.join(f"{drive}:\\", folder_match.group(1), "Projects")
        return os.path.join(f"{drive}:\\", "Projects")

    return os.path.join("D:\\", "Projects")



#  CREATE ALL PROJECT FILES

def _create_project_files(project_dir, project_data):
    try:
        os.makedirs(project_dir, exist_ok=True)
        project_name = project_data["project_name"]

        for file_info in project_data.get("files", []):
            file_path = file_info.get("path", "").strip()
            content   = file_info.get("content", "")
            if not file_path:
                continue
            if content.startswith("PREFILLED:"):
                content = content[10:]
            full_path = os.path.join(project_dir, file_path)
            dir_path  = os.path.dirname(full_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[CodeGen] Created: {file_path}")

        # README
        tech  = project_data["tech_stack"]
        readme = f"""# {project_name.replace('_', ' ').title()}

{project_data.get('description', '')}

## Tech Stack
| Layer    | Technology |
|----------|------------|
| Frontend | {tech.get('frontend', '')} |
| Backend  | {tech.get('backend', '')} |
| Database | {tech.get('database', '')} |

## Database Setup
- Install MongoDB: https://www.mongodb.com/try/download/community
- Start MongoDB (Windows): `net start MongoDB`
- **Database name:** `{project_name}`
- **Connection:** `mongodb://localhost:27017/{project_name}`
- Collections are created automatically on first signup

## Installation
```bash
{project_data.get('install_command', '')}
```

## Run
```bash
{project_data.get('run_command', '')}
```

Open: **http://localhost:5000**

## Default Accounts
Create accounts via the signup page.
Select **Admin** role to access the admin dashboard.

## Notes
{project_data.get('notes', '')}
"""
        with open(os.path.join(project_dir, "README.md"), 'w', encoding='utf-8') as f:
            f.write(readme)
        print("[CodeGen] Created: README.md")
        return True

    except PermissionError as e:
        print(f"[CodeGen] Permission error: {e}")
        return False
    except Exception as e:
        print(f"[CodeGen] Error: {e}")
        return False


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════
def _yes(response):
    if not response:
        return False
    return any(w in response.lower() for w in
               ["yes", "yeah", "sure", "okay", "ok", "please", "yep", "open", "run", "start", "do it"])


def _open_in_vscode(project_dir):
    try:
        subprocess.run(f'code "{project_dir}"', shell=True, timeout=5)
    except Exception:
        local  = os.environ.get("LOCALAPPDATA", "")
        vscode = os.path.join(local, "Programs", "Microsoft VS Code", "Code.exe")
        if os.path.exists(vscode):
            subprocess.Popen([vscode, project_dir])
        else:
            subprocess.Popen(f'explorer "{project_dir}"', shell=True)


def _run_server(run_cmd, project_dir, start_url):
    def _start():
        subprocess.Popen(
            f'start cmd /k "cd /d "{project_dir}" && {run_cmd}"',
            shell=True
        )
        time.sleep(4)
        webbrowser.open(start_url)
    threading.Thread(target=_start, daemon=True).start()