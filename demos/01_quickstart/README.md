# Demo 1 — Quickstart

The smallest real use of Loom: one script, one context dict, one template
that uses inheritance, a loop, a conditional, and filters — rendered to an
HTML file you can open directly.

## Run it

```bash
python run_demo.py
```

This imports `loom.py` from the project root (two levels up) — there's no
separate copy in this folder.

It prints the rendered HTML to the terminal and also writes
`dashboard_output.html` right here. Open that file in a browser to see it
rendered.

## What it demonstrates

| Feature | Where |
|---|---|
| `Environment` + `add_template()` | Needed because `dashboard.html` extends `base.html` |
| `{% extends %}` / `{% block %}` | `templates/dashboard.html` fills in `templates/base.html`'s content block |
| `{{ user.name }}` | Dotted-path variable lookup |
| `{{ name \| title }}`, `\| upper` | Chained filters |
| `{{ team \| length }}` | Filter with no args |
| `{% if user.is_admin %}` | Conditional badge |
| `{% for member in team %}` + `loop.index` | Looping with the built-in loop counter |
| `{{ task.owner \| default('unassigned') }}` | Handling missing/`None` values |

## Try this

Open `run_demo.py`, flip `"is_admin": True` to `False`, or empty out the
`tasks` list, then re-run. Diff the output to see the `{% if %}`/`{% else %}`
and `{% for %}` branches actually respond to the data change.

## File map

```
01_quickstart/
├── run_demo.py               imports ../../loom.py
├── dashboard_output.html     generated output (already included, re-runnable)
└── templates/
    ├── base.html              shared layout
    └── dashboard.html         extends base.html
```
