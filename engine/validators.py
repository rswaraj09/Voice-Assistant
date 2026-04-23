"""
Post-generation validators for the code generator.

Each validator returns a dict:
    {"ok": bool, "issues": [str, ...], "info": {...}}

Validators are intentionally forgiving — they surface problems but never
crash the generator. They rely only on the standard library so they stay
import-safe.
"""

import ast
import json
import os
import re


#  File-level validation  

def validate_python_syntax(path, content):
    issues = []
    try:
        ast.parse(content)
    except SyntaxError as e:
        issues.append(f"{path}: syntax error at line {e.lineno}: {e.msg}")
    return {"ok": not issues, "issues": issues, "info": {}}


def validate_json(path, content):
    issues = []
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        issues.append(f"{path}: invalid JSON at line {e.lineno}: {e.msg}")
    return {"ok": not issues, "issues": issues, "info": {}}


_JS_BALANCE_RE = re.compile(r'(["\'`])(?:\\.|(?!\1).)*\1|/\*[\s\S]*?\*/|//[^\n]*', re.DOTALL)


def validate_js_syntax(path, content):
    """A cheap heuristic for JS/TS — bracket balance after stripping strings/comments."""
    stripped = _JS_BALANCE_RE.sub("", content)
    pairs = {"(": ")", "[": "]", "{": "}"}
    closers = {")": "(", "]": "[", "}": "{"}
    stack = []
    issues = []
    for ch in stripped:
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in closers:
            if not stack or stack[-1] != ch:
                issues.append(f"{path}: unbalanced '{ch}' in JS source")
                break
            stack.pop()
    if stack:
        issues.append(f"{path}: unclosed {stack}")
    return {"ok": not issues, "issues": issues, "info": {}}


def validate_generated_file(path, content):
    """Dispatch validator by extension."""
    ext = os.path.splitext(path)[1].lower()
    if not content or not content.strip():
        return {"ok": False, "issues": [f"{path}: empty file"], "info": {}}
    if ext == ".py":
        return validate_python_syntax(path, content)
    if ext == ".json":
        return validate_json(path, content)
    if ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
        return validate_js_syntax(path, content)
    return {"ok": True, "issues": [], "info": {"skipped": True}}


#  Project-level completeness 

CRITICAL_BY_KIND = {
    "flask": [
        lambda files: any(f == "app.py" or f.endswith("/app.py") for f in files),
        lambda files: any("requirements.txt" in f for f in files),
    ],
    "node": [
        lambda files: any(f.endswith("package.json") for f in files),
        lambda files: any(f.endswith("server.js") or f.endswith("index.js") or f.endswith("app.js") for f in files),
    ],
    "frontend": [
        lambda files: any(f.endswith(".html") for f in files),
    ],
}


def verify_project_completeness(generated_files, backend_kind="flask"):
    """
    generated_files: dict[path] -> content
    Returns a report — { ok, issues, missing, summary }.
    """
    files = list(generated_files.keys())
    issues  = []
    missing = []

    checks = CRITICAL_BY_KIND.get(backend_kind, []) + CRITICAL_BY_KIND["frontend"]
    for idx, check in enumerate(checks):
        try:
            if not check(files):
                missing.append(f"critical-check-{backend_kind}-{idx}")
        except Exception:
            pass

    # Dependency sanity — any `import X` referenced should ideally appear
    # in requirements.txt / package.json. We only log, never fail.
    py_imports = set()
    js_imports = set()
    for path, content in generated_files.items():
        if path.endswith(".py"):
            for m in re.finditer(r"^\s*(?:from|import)\s+([\w\.]+)", content, re.MULTILINE):
                py_imports.add(m.group(1).split(".")[0])
        elif path.endswith((".js", ".jsx", ".ts", ".tsx")):
            for m in re.finditer(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)", content):
                js_imports.add(m.group(1).split("/")[0])
            for m in re.finditer(r"from\s+['\"]([^'\"]+)['\"]", content):
                pkg = m.group(1)
                if not pkg.startswith("."):
                    js_imports.add(pkg.split("/")[0])

    requirements_txt = next((c for p, c in generated_files.items() if p.endswith("requirements.txt")), "")
    package_json     = next((c for p, c in generated_files.items() if p.endswith("package.json")), "")

    stdlib = _PY_STDLIB
    missing_py = [m for m in py_imports
                  if m not in stdlib and m not in requirements_txt and m not in {"flask", "pymongo", "bcrypt"}]
    if missing_py:
        issues.append(f"Python imports not in requirements.txt: {sorted(missing_py)}")

    missing_js = []
    if package_json:
        for pkg in js_imports:
            if pkg not in package_json:
                missing_js.append(pkg)
    if missing_js:
        issues.append(f"JS packages referenced but missing from package.json: {sorted(set(missing_js))}")

    syntax_issues = []
    for path, content in generated_files.items():
        r = validate_generated_file(path, content)
        if not r["ok"]:
            syntax_issues.extend(r["issues"])
    issues.extend(syntax_issues)

    return {
        "ok": not missing and not syntax_issues,
        "issues": issues,
        "missing": missing,
        "summary": {
            "files": len(files),
            "syntax_errors": len(syntax_issues),
            "missing_critical": len(missing),
            "py_undeclared": len(missing_py),
            "js_undeclared": len(missing_js),
        },
    }


_PY_STDLIB = {
    "os", "sys", "re", "json", "time", "datetime", "math", "random", "hashlib",
    "collections", "itertools", "functools", "typing", "pathlib", "subprocess",
    "threading", "asyncio", "logging", "unittest", "argparse", "io", "base64",
    "uuid", "sqlite3", "shutil", "tempfile", "csv", "struct", "string", "socket",
    "urllib", "http", "email", "traceback", "copy", "warnings", "pickle", "gzip",
    "zipfile", "tarfile", "glob", "contextlib", "operator", "enum", "abc",
    "inspect", "ast",
}
