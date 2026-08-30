# Loom — Hackathon Submission

**Grand Hack IPEC 2026 — Zero Dependency 2026, Track B (Parsers & Data Formats)**
**Author:** Anmol

A zero-dependency template engine for Python, built from a real lexer → parser
→ AST → renderer pipeline — a genuine substitute for Jinja2's core feature
set, not a shortcut around it.

---

## Where to look first

| If you want to... | Look at |
|---|---|
| Read how the engine works, feature by feature | `README.md` |
| See the substitutions log (bonus challenge) | `STDLIB.md` |
| Read the engine itself | `loom.py` — single file, ~800 lines |
| Verify it works | `test_loom.py` — 40 tests, run with `python -m unittest test_loom.py -v` |
| See the pitch | `Loom_Pitch_Deck.pptx` |
| See it used in a real project | `demos/` (below) |

## Quick verification

**One command, does everything** (dependency proof + tests + self-demo):
```bash
make
```

Or individually:
```bash
python check_dependencies.py            # proves loom.py imports only stdlib
python -m unittest test_loom.py -v       # 40/40 tests
python loom.py                           # self-demo
```

All of this runs with zero installs — `loom.py` imports only `re`, `html`,
`dataclasses`, `typing`, and `from __future__ import annotations`, all five
standard library. `requirements.txt` is intentionally empty and documents why.

## Demos — three real, working use cases

Each demo has its own README with exact run instructions.

### `demos/01_quickstart/`
The smallest possible real use: one script, one template with inheritance,
loops, conditionals, and filters, rendered to an HTML file you can open
directly. Best starting point to understand the syntax.
```bash
cd demos/01_quickstart && python run_demo.py
```

### `demos/02_flask_app/`
A real multi-page Flask web app — every page (including the 404 page)
rendered by Loom, not Flask's built-in Jinja2. Includes a live HTML form
that POSTs user input back through the app, demonstrating `autoescape=True`
against a real request, not just a unit test.
```bash
cd demos/02_flask_app
pip install flask --break-system-packages
python app.py
# open http://127.0.0.1:5050/
```

### `demos/03_static_site_generator/`
Loom used as a static site generator: the same templates, but the output is
a folder of plain, finished `.html` files — no server, no install, just
double-click `site/index.html` to open it. `site/` is pre-built and ready
to view immediately; `build_site.py` is the generator source.
```bash
cd demos/03_static_site_generator && python build_site.py
```

## Bonus challenges targeted

- **Single File (+5)** — there is exactly one `loom.py` in this entire submission, at the project root. Every demo imports that same file (`sys.path` points back to the root) rather than vendoring a copy — verified with `find . -name loom.py`, which returns a single result.
- **Package Killer (+3)** — a drop-in substitute for Jinja2's core feature set, demonstrated three different ways above.
- **STDLIB Log (+3)** — 10 substitutions logged in `STDLIB.md` (meets the "10 meaningful substitutions" threshold for this bonus).

## Judging criteria fit

| Criterion | Weight | Where it's addressed |
|---|---|---|
| Functionality | 35% | Full feature set in `loom.py`; three working demos prove it end-to-end |
| Zero-Dependency Craft | 30% | Only `re`/`html` imports; hand-written expression parser (no `eval`) — see `STDLIB.md` |
| Code Quality | 25% | Typed exceptions, docstrings, 40-case test suite, clean separation of lexer/parser/renderer |
| Innovation | 10% | Template inheritance, whitespace control, dict-iteration loops — beyond the core spec |

## Submitting: this needs to be a public GitHub repo, not a zip

Per the official rules, submission requires **a public GitHub repository**
containing this exact structure — not a zip upload. From inside this
`submission/` folder:

```bash
git init
git add .
git commit -m "Loom — zero-dependency template engine"
git branch -M main
git remote add origin https://github.com/<your-username>/loom.git   # create this repo on GitHub first, public, empty
git push -u origin main
```

Then submit the repo URL per the Discord instructions (submission channel —
all instructions are posted there, not elsewhere). Double check at submission
time that the repo is actually set to **Public** in GitHub's settings — the
rules state it must be public *at submission time*.

## Demo video (required, 5 minutes) — suggested outline

Not yet recorded — here's a structure that hits every judging criterion in
the time limit:

| Time | Show |
|---|---|
| 0:00–0:30 | The problem: templating needs a library, but the challenge forbids one. State the track and what Loom is. |
| 0:30–1:30 | `python check_dependencies.py` and `python loom.py` running live in a terminal — zero-dependency proof and the self-demo, unscripted. |
| 1:30–2:30 | Open `loom.py`, scroll through the Lexer → Parser → Renderer sections, point at the hand-written expression parser (no `eval`). |
| 2:30–3:30 | `python -m unittest test_loom.py -v` running live — 40/40 — then jump to one interesting edge case in `test_loom.py`. |
| 3:30–4:30 | Run demo 02 (Flask) live: open the browser, click Tasks → Dashboard → a task detail page, then submit `<script>alert(1)</script>` in the form and show it comes back escaped, not executed. |
| 4:30–5:00 | `STDLIB.md` on screen, scroll the substitutions table, close on the repo URL. |

```
submission/
├── LICENSE                           MIT
├── loom.py                          the engine — the only copy in this submission
├── test_loom.py                     40-case test suite
├── check_dependencies.py            dependency proof — verifies loom.py imports only stdlib
├── requirements.txt                 intentionally empty — the dependency manifest
├── Makefile                         `make` runs deps-check + tests + demo, single command
├── README.md                        full feature reference
├── STDLIB.md                        substitutions log (10 entries)
├── Loom_Pitch_Deck.pptx             9-slide pitch deck
└── demos/
    ├── 01_quickstart/               imports ../../loom.py
    ├── 02_flask_app/                imports ../../loom.py (Flask: disclosed demo-only dep)
    └── 03_static_site_generator/    imports ../../loom.py
```
