# Demo 3 — Static site generator

Loom used the way tools like Jekyll/Hugo/Eleventy work internally: the same
templates as the Flask demo, but instead of a server responding to requests,
`build_site.py` runs once and writes a folder of plain, finished `.html`
files — no server, no install, no Flask.

## View it right now (no setup)

`site/` is already built and committed. Just open `site/index.html` in a
browser — double-click it, or drag it into a browser tab.

## Rebuild it yourself

```bash
python build_site.py
```

This imports `loom.py` from the project root (two levels up), reads every
`.html` file in `templates/`, and regenerates the entire `site/` folder from
scratch (existing output is deleted and rebuilt each run).

## What it demonstrates

- The exact same `Environment` / `{% extends %}` / `{% include %}` machinery
  as the Flask demo, just called from a plain script instead of a request
  handler — same engine, different host.
- Templates and page data live entirely in Python (`TEAM`, `TASKS` lists in
  `build_site.py`) — swap that for a CSV, a JSON export, or a CMS API and
  nothing else about the generator changes.
- All internal links (`index.html` → `task-1.html`, nav links, the
  stylesheet path) are plain relative paths, so the output folder works
  identically whether opened from disk or uploaded to any static host.

## Try this

Edit the `TASKS` list at the top of `build_site.py` — add a task, remove
one, change an owner — then re-run `python build_site.py` and refresh
`site/index.html` in your browser.

## File map

```
03_static_site_generator/
├── build_site.py              imports ../../loom.py, writes site/
├── templates/                 Loom template source
│   ├── base.html
│   ├── _partials/nav.html
│   ├── index.html
│   ├── dashboard.html
│   └── task_detail.html
├── static/style.css           copied into site/static/ on build
└── site/                      pre-built output — open site/index.html directly
    ├── index.html
    ├── dashboard.html
    ├── task-1.html / task-2.html / task-3.html
    └── static/style.css
```
