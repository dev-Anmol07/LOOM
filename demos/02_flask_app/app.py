"""
A small real Flask app where every page is rendered by Loom — not Flask's
built-in Jinja2. This is meant to show Loom doing the actual job a templating
library does in production: routes hand it a context dict, it hands back HTML.

Run it:
    pip install flask --break-system-packages   # only Flask itself is a dependency — Loom has none
    python app.py
Then open http://127.0.0.1:5050/
"""

import os
from flask import Flask, request, redirect, url_for
import sys

# There is exactly one loom.py in this whole submission — at the project root.
# This demo imports that same file rather than keeping its own copy.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from loom import Environment

app = Flask(__name__)

# ---- set up Loom: register every .html file in templates/ by name -------
env = Environment(autoescape=True)  # on, because real user input flows through the "add task" form
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

for root, _dirs, files in os.walk(TEMPLATES_DIR):
    for filename in files:
        if not filename.endswith(".html"):
            continue
        full_path = os.path.join(root, filename)
        rel_path = os.path.relpath(full_path, TEMPLATES_DIR)
        name = rel_path[:-5].replace(os.sep, "/")  # "_partials/nav.html" -> "_partials/nav"
        with open(full_path) as f:
            env.add_template(name, f.read())


def render(template_name, **context):
    """Thin helper: render a Loom template with the shared site-wide context merged in."""
    base_context = {
        "site_name": "Acme Ops",
        "year": 2026,
        "static_css": url_for("static", filename="style.css"),
        "nav_links": [
            {"label": "Tasks", "url": "/", "active": request.path == "/"},
            {"label": "Dashboard", "url": "/dashboard", "active": request.path == "/dashboard"},
        ],
    }
    base_context.update(context)
    return env.get(template_name).render(base_context)


# ---- fake in-memory "database" -------------------------------------------
TEAM = [
    {"name": "anmol", "role": "engineer", "active": True},
    {"name": "rhea", "role": "designer", "active": True},
    {"name": "kabir", "role": "pm", "active": False},
]
TASKS = [
    {"id": 1, "title": "Fix lexer edge case", "owner": "anmol", "done": True},
    {"id": 2, "title": "Update README", "owner": None, "done": False},
    {"id": 3, "title": "Record demo video", "owner": "rhea", "done": False},
]
_next_id = 4


# ---- routes ----------------------------------------------------------------
@app.route("/")
def home():
    return render("index", tasks=TASKS)


@app.route("/dashboard")
def dashboard():
    user = {"name": "anmol", "is_admin": True}
    return render("dashboard", user=user, team=TEAM, tasks=TASKS)


@app.route("/tasks/<int:task_id>")
def task_detail(task_id):
    task = next((t for t in TASKS if t["id"] == task_id), None)
    if task is None:
        return render("404"), 404
    return render("task_detail", task=task)


@app.route("/tasks/new", methods=["POST"])
def new_task():
    global _next_id
    title = request.form.get("title", "").strip()
    owner = request.form.get("owner", "").strip() or None
    if title:
        TASKS.append({"id": _next_id, "title": title, "owner": owner, "done": False})
        _next_id += 1
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=False, port=5050)
