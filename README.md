# Loom

A zero-dependency template engine, built for **Grand Hack IPEC 2026 — Zero
Dependency 2026, Track B (Parsers & Data Formats)**.

Loom takes a template string with `{{ variable }}` placeholders and
`{% logic %}` tags, combines it with a Python dict of real data, and produces
plain output text (usually HTML) — the same job Jinja2 does, implemented from
scratch with only `re` and `html` from the standard library.

```
template string ──▶ Lexer ──▶ tokens ──▶ Parser ──▶ AST ──▶ Renderer ──▶ output
                                                        ▲
                                                   context data
```

## Files

| File | Purpose |
|---|---|
| `loom.py` | The engine. Single file, zero dependencies. Run it directly (`python loom.py`) for a live self-test/demo. |
| `test_loom.py` | 40-case `unittest` suite covering every feature and every edge case from the design doc. |
| `STDLIB.md` | Log of every place a third-party dependency was replaced with stdlib-only code — for the bonus challenge. |

## Quick start

```python
from loom import Template

tpl = Template("Hello {{ user.name }}!")
print(tpl.render({"user": {"name": "Anmol"}}))
# Hello Anmol!
```

## Feature reference

### Variables
```
{{ name }}              simple lookup
{{ user.name }}         dotted path, walks dicts / objects / list indices
{{ items.0 }}           numeric segment = list index
```

### Filters
```
{{ name | upper }}
{{ price | round(2) }}
{{ items | join(', ') }}
{{ value | default('n/a') }}
```
Built in: `upper`, `lower`, `capitalize`, `title`, `trim`, `length`, `round`,
`default`, `join`, `escape` (`e`), `first`, `last`. Add your own with
`env.add_filter("name", fn)`.

### Conditionals
```
{% if user.is_admin %}
  admin
{% elif user.is_member %}
  member
{% else %}
  guest
{% endif %}
```
Supports `==`, `!=`, `<`, `<=`, `>`, `>=`, `in`, `not in`, `and`, `or`, `not`,
and parentheses — evaluated by a hand-written expression parser, not `eval()`.

### Loops
```
{% for item in items %}{{ item }}{% endfor %}
{% for key, value in a_dict %}{{ key }}={{ value }}{% endfor %}
```
Inside a loop, `loop.index`, `loop.index0`, `loop.first`, `loop.last`, and
`loop.length` are available, same idea as Jinja2's `loop` object.

### Comments
```
{# this is stripped entirely and never appears in output #}
```

### Whitespace control
```
{% for x in items -%}
  {{ x }}
{%- endfor %}
```
A `-` on either side of a tag trims adjacent whitespace, so loops don't spray
blank lines into generated HTML.

### Template inheritance
```python
env = Environment()
env.add_template("base", "<body>{% block content %}default{% endblock %}</body>")
env.add_template("page", '{% extends "base" %}{% block content %}<h1>{{ title }}</h1>{% endblock %}')
env.get("page").render({"title": "Loom"})
# <body><h1>Loom</h1></body>
```

### Include
```python
env.add_template("footer", "<footer>{{ year }}</footer>")
env.from_string('<body>{% include "footer" %}</body>').render({"year": 2026})
```

### Autoescaping & undefined-variable policy
```python
env = Environment(autoescape=True, strict_undefined=True)
```
- `autoescape=True` — every `{{ }}` output is HTML-escaped automatically.
- `strict_undefined=True` — looking up a missing variable raises
  `LoomRenderError` instead of silently rendering `""`.

## Error handling

Both stages raise typed exceptions:
- `LoomSyntaxError` — bad template structure (unclosed `{% if %}`, unknown tag,
  malformed expression), includes the offending line number.
- `LoomRenderError` — a problem discovered while walking the AST (unknown
  filter, non-iterable in a `{% for %}`, undefined variable in strict mode).

```python
try:
    Template("{% if x %}no endif")
except LoomSyntaxError as e:
    print(e)  # Unexpected end of template, expected one of ('elif', 'else', 'endif')
```

## Running the tests

```
python -m unittest test_loom.py -v
```

40 tests, 0 dependencies beyond the standard library.

## Bonus challenges targeted

- **Single File (+5)** — the entire engine is `loom.py`.
- **Package Killer (+3)** — a drop-in substitute for Jinja2's core feature set.
- **STDLIB Log (+3)** — see `STDLIB.md` for the itemized substitutions log.
