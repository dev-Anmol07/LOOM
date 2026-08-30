# Loom + Flask demo

A small, real, working web app where **every page is rendered by Loom** —
not Flask's built-in Jinja2. Flask handles routing/requests (that's Flask's
job); Loom handles turning data into HTML (that's the part built from
scratch with zero dependencies).

## Setup

```bash
pip install flask --break-system-packages
```

This demo imports `loom.py` from the project root (two levels up) — there's
no separate copy in this folder, so you're always running the exact same
engine file as everything else in the submission.
Flask is the only third-party dependency here, and it's not part of Loom
itself; Loom stays zero-dependency regardless of what app you plug it into.

## Run it

```bash
python app.py
```

Then open **http://127.0.0.1:5050/** in a browser.

## What to click through

| Page | URL | What it shows |
|---|---|---|
| Tasks | `/` | Loop over a task list, `{% if %}` for empty state, a real `<form>` that POSTs back to Flask |
| Dashboard | `/dashboard` | Team list with `loop.index`, filters (`title`, `upper`), nested conditionals |
| Task detail | `/tasks/1` | A dynamic per-item page driven by the URL |
| 404 | `/tasks/999` | Loom-rendered error page, not Flask's default |

**Try this:** on the Tasks page, add a task titled `<b>test</b>`. It'll show
up on the page as literal text, not bold — that's `Environment(autoescape=True)`
protecting you from anything a real user could type into that form.

## How the wiring works (`app.py`)

1. On startup, every `.html` file under `templates/` gets registered into a
   single `loom.Environment` by name (so `{% extends "base" %}` and
   `{% include "_partials/nav" %}` can find each other).
2. A small `render(name, **context)` helper merges route-specific data with
   site-wide context (site name, year, nav links) and calls
   `env.get(name).render(context)`.
3. Each Flask route just gathers data (here: from in-memory Python lists —
   swap in a real database and nothing else changes) and calls `render(...)`.

## File map

```
submission/
├── loom.py                    the one engine file, imported from here
├── demos/02_flask_app/
│   ├── app.py                 Flask routes + Loom wiring
│   ├── static/style.css
│   └── templates/
│       ├── base.html          shared layout, {% block content %}
│       ├── _partials/nav.html {% include %}'d into base.html
│       ├── index.html         task list + add-task form
│       ├── dashboard.html     team dashboard
│       ├── task_detail.html   single task page
│       └── 404.html
```
