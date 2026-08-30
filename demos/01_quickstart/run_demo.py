"""
Loom example — a mini "Team Dashboard" page.

What this demonstrates:
  - Environment + add_template()          (needed because dashboard.html extends base.html)
  - {% extends %} / {% block %}            (dashboard.html overrides base.html's content block)
  - {{ variable }}                         (site_name, year, user.name)
  - {{ x | filter }}                       (title, upper, length, default)
  - {% if / else %}                        (admin badge, active/offline, empty task list)
  - {% for %} + loop.index                 (team members, tasks)

Run it:
    cd loom_example
    python run_demo.py
"""

import sys
import os

# There is exactly one loom.py in this whole submission — at the project root.
# Every demo imports that same file rather than keeping its own copy.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from loom import Environment

# ---- 1. set up the environment and register every template by name ----
env = Environment(autoescape=True)

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
for filename in os.listdir(templates_dir):
    if filename.endswith(".html"):
        name = filename[:-5]  # "base.html" -> "base"
        with open(os.path.join(templates_dir, filename)) as f:
            env.add_template(name, f.read())

# ---- 2. the "real data" that would normally come from a database ----
context = {
    "site_name": "Acme Ops",
    "year": 2026,
    "user": {"name": "anmol", "is_admin": True},
    "team": [
        {"name": "anmol", "role": "engineer", "active": True},
        {"name": "rhea", "role": "designer", "active": True},
        {"name": "kabir", "role": "pm", "active": False},
    ],
    "tasks": [
        {"title": "Fix lexer edge case", "owner": "anmol"},
        {"title": "Update README", "owner": None},   # no owner -> triggers | default filter
    ],
}

# ---- 3. render ----
output = env.get("dashboard").render(context)

print(output)

# also save it so you can open it in a browser
out_path = os.path.join(os.path.dirname(__file__), "dashboard_output.html")
with open(out_path, "w") as f:
    f.write(output)
print(f"\n--- saved to {out_path}, open it in a browser to see it rendered ---")
