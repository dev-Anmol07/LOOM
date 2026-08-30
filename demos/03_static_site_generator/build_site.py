"""
Builds a plain, static HTML site using Loom — no Flask, no server, no install.

Run it:
    python build_site.py

Then just double-click site/index.html to open it in your browser.
Every page in site/ is a real, finished .html file that Loom generated once —
you can email it, host it anywhere, or open it offline.
"""

import os
import shutil
import sys

# There is exactly one loom.py in this whole submission — at the project root.
# This generator imports that same file rather than keeping its own copy.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from loom import Environment

HERE = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.join(HERE, "templates")
OUTPUT_DIR = os.path.join(HERE, "site")

# ---- register every template by name (needed for {% extends %} / {% include %}) ----
env = Environment(autoescape=True)
for root, _dirs, files in os.walk(TEMPLATES_DIR):
    for filename in files:
        if not filename.endswith(".html"):
            continue
        full_path = os.path.join(root, filename)
        rel_path = os.path.relpath(full_path, TEMPLATES_DIR)
        name = rel_path[:-5].replace(os.sep, "/")
        with open(full_path) as f:
            env.add_template(name, f.read())


def nav_links(active):
    return [
        {"label": "Tasks", "url": "index.html", "active": active == "index"},
        {"label": "Dashboard", "url": "dashboard.html", "active": active == "dashboard"},
    ]


def render(template_name, active, **context):
    base_context = {
        "site_name": "Acme Ops",
        "year": 2026,
        "static_css": "static/style.css",
        "nav_links": nav_links(active),
    }
    base_context.update(context)
    return env.get(template_name).render(base_context)


# ---- the "data" — in a real project this could come from a CSV, a database
#      export, a CMS API, anything. Loom doesn't care where it came from. ----
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

# ---- build the output folder ----
if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
os.makedirs(os.path.join(OUTPUT_DIR, "static"))
shutil.copy(os.path.join(HERE, "static", "style.css"), os.path.join(OUTPUT_DIR, "static", "style.css"))

pages_built = []

with open(os.path.join(OUTPUT_DIR, "index.html"), "w") as f:
    f.write(render("index", "index", tasks=TASKS))
pages_built.append("index.html")

with open(os.path.join(OUTPUT_DIR, "dashboard.html"), "w") as f:
    f.write(render("dashboard", "dashboard", user={"name": "anmol", "is_admin": True}, team=TEAM, tasks=TASKS))
pages_built.append("dashboard.html")

for task in TASKS:
    filename = f"task-{task['id']}.html"
    with open(os.path.join(OUTPUT_DIR, filename), "w") as f:
        f.write(render("task_detail", "index", task=task))
    pages_built.append(filename)

print(f"Built {len(pages_built)} pages into {OUTPUT_DIR}/:")
for p in pages_built:
    print(f"  - {p}")
print(f"\nOpen {os.path.join(OUTPUT_DIR, 'index.html')} in a browser to view the site.")
