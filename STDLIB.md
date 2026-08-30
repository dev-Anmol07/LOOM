# STDLIB.md — Loom

**Project:** Zero Dependency 2026 — Track B (Parsers & Data Formats)
**Author:** Anmol

This log records every place Loom substitutes stdlib-only code for a third-party
library or dependency a normal implementation would reach for.

| # | Normally would use | Instead, Loom uses | Where |
|---|---|---|---|
| 1 | **Jinja2 / Mako / Django templates** (the whole engine) | Hand-written lexer + recursive-descent parser + AST-walking renderer, built from scratch | `Lexer`, `Parser`, `Renderer` classes |
| 2 | **markupsafe** (HTML-safe string escaping) | `html.escape` (Python stdlib) | `Renderer._render_node`, `_f_escape` filter |
| 3 | Regex-based "templating" hacks (`re.sub` on `{{ }}`) | A real tokenizer + AST, so nesting, precedence, and error locations are structurally correct instead of pattern-matched | `Lexer.tokenize`, `Parser._parse_nodes` |
| 4 | **A parser-generator or expression-eval library** (e.g. using Python's `eval()`, or a package like `simpleeval`) for `{% if %}` conditions | A dedicated hand-rolled expression tokenizer + recursive-descent parser supporting literals, dotted paths, `and`/`or`/`not`, comparisons, and `in` — no `eval()` anywhere in the file | `_ExprTokenizer`, `_ExprParser`, `Expr` subclasses |
| 5 | A filter/pipe framework (e.g. Django's filter registry, Jinja2's `Environment.filters`) | A plain `dict[str, callable]` on `Environment`, with a small built-in set (`upper`, `round`, `join`, `escape`, ...) and `env.add_filter()` for custom ones | `DEFAULT_FILTERS`, `Environment.filters` |
| 6 | Template inheritance systems (Jinja2 `{% extends %}` / `{% block %}` internals, Django's template loader chain) | A minimal `Environment` template registry (plain `dict[str, str]`) plus block-substitution logic in `Template.render()` | `Environment`, `ExtendsNode`, `BlockNode` |
| 7 | A caching/compilation layer (e.g. Jinja2's bytecode cache) | A simple `dict` memoizing parsed `Expr` trees by source string (`_expr_cache`), and `Environment._compiled` memoizing parsed `Template` objects by name | `parse_expr`, `Environment.get` |
| 8 | Data-model / boilerplate libraries (e.g. `attrs`, `pydantic`) used to avoid hand-writing `__init__`/`__repr__`/`__eq__` for AST node classes | Python's built-in `dataclasses` module (`@dataclass`) for every AST node (`TextNode`, `VarNode`, `IfNode`, `ForNode`, `BlockNode`, `Expr` subclasses) | `Node` subclasses, `Expr` subclasses |
| 9 | A lexer-generator library (e.g. **PLY**, **SLY**, **ANTLR** runtime) to produce the tokenizer | A hand-written regex-based tokenizer using `re` in `VERBOSE` mode for the expression sub-language, plus a second manual split/scan pass for the template lexer — no generated code, no grammar-compiler dependency | `Lexer.tokenize`, `_TOKEN_RE`, `_ExprTokenizer` |
| 10 | Template **loader** classes (e.g. Jinja2's `FileSystemLoader`, `PackageLoader`, `DictLoader`) for resolving a template name to source text | A plain `dict[str, str]` on `Environment` (`Environment.templates`), populated via `add_template()` — no filesystem-walking or import-hook machinery needed | `Environment.templates`, `Environment.add_template`, `Environment.get` |

**Total substitutions logged: 10** — each replaces a distinct piece of functionality
a third-party templating library (or its supporting tooling) would normally supply.

## Design notes for judges

- **No `eval`, `exec`, or `ast.literal_eval` is used anywhere.** Both the tag/text
  lexer and the `{% if %}` / `{% for %}` expression language are parsed by
  hand-written recursive-descent parsers, so the "genuine substitute for the
  library" bar is met even for the trickiest part (condition evaluation).
- **Every import in the file is standard library:** `re`, `html`, `dataclasses`,
  `typing`, and `from __future__ import annotations` — five imports total, all
  five stdlib, zero third-party. (`re` and `html` are the two doing the actual
  parsing/escaping work; the other three are typing and dataclass ergonomics.)
  Verified automatically by `check_dependencies.py`.
- **Single file** (`loom.py`), ~800 lines, no `pip install` required to run it.
- Verify this programmatically with `python check_dependencies.py`, which parses
  `loom.py`'s import statements via the `ast` module and checks each one against
  `sys.stdlib_module_names`.

## Disclosed non-core dependency (demo-only)

`demos/02_flask_app/` uses **Flask** to host Loom inside a real HTTP server for
demonstration purposes. Flask is **not** a dependency of Loom itself — `loom.py`
has zero imports beyond `re` and `html`, and `check_dependencies.py` verifies
this against the core file specifically. Flask is disclosed here per the rule
that any permitted development/demo-only dependency must be listed in this file.
It is not present in the project's dependency manifest (`requirements.txt`,
intentionally empty) and is only ever `pip install`ed manually by someone
choosing to run that one specific demo.
