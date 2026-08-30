"""
Loom — a zero-dependency template engine.

Pipeline:  template string -> Lexer -> tokens -> Parser -> AST -> Renderer -> output string

Supports:
  {{ expr }}                          variable interpolation (dotted paths, filters)
  {{ name | upper }}                  filters, chainable, with args: {{ price | round(2) }}
  {% if cond %} ... {% elif %} ... {% else %} ... {% endif %}
  {% for item in items %} ... {% endfor %}
  {% for k, v in mapping %} ... {% endfor %}     (dict iteration)
  {# comment #}                       stripped entirely, never rendered
  {% extends "base" %} / {% block name %}...{% endblock %}   template inheritance
  {% include "partial" %}             sub-template inclusion
  Autoescaping (opt-in per Template/Environment)
  {%- if x -%} / {{- x -}}            whitespace control (trims adjacent text)

No third-party libraries are used anywhere in this file — only `re` and `html` from stdlib.

Public API:

    from loom import Template, Environment

    tpl = Template("Hello {{ name }}!")
    tpl.render({"name": "Anmol"})

    env = Environment(templates={"base": "...", "page": "..."})
    env.get("page").render({...})
"""

from __future__ import annotations

import re
import html
from dataclasses import dataclass, field
from typing import Any


# =====================================================================================
# Errors
# =====================================================================================

class LoomError(Exception):
    """Base class for all Loom errors."""


class LoomSyntaxError(LoomError):
    def __init__(self, message: str, line: int | None = None):
        self.line = line
        loc = f" (line {line})" if line is not None else ""
        super().__init__(f"{message}{loc}")


class LoomRenderError(LoomError):
    pass


# =====================================================================================
# Stage 1 — Lexer
# =====================================================================================
#
# The lexer only recognizes SHAPE, not meaning: it slices the raw template into
# TEXT chunks and directive chunks ({{ }}, {% %}, {# #}) without knowing yet whether
# a {% %} tag is "if", "for", "endif", etc.
#
# A directive may carry a leading/trailing "-" (e.g. {%- if x -%}) requesting that
# whitespace in the *adjacent* TEXT chunks be trimmed — this is what keeps
# {% for %} blocks from spraying blank lines into the rendered HTML.

_DIRECTIVE_RE = re.compile(
    r"(\{\{-?.*?-?\}\}|\{%-?.*?-?%\}|\{#-?.*?-?#\})",
    re.DOTALL,
)


@dataclass
class Token:
    kind: str          # "TEXT" | "VAR" | "TAG" | "COMMENT"
    value: str          # raw text, or the trimmed inner expression
    line: int


class Lexer:
    def __init__(self, source: str):
        self.source = source

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        line = 1
        pending_ltrim = False  # set when the previous directive ended with "-", i.e. {%- ... -%}

        for piece in _DIRECTIVE_RE.split(self.source):
            if piece == "":
                continue

            is_var = piece.startswith("{{") and piece.endswith("}}")
            is_tag = piece.startswith("{%") and piece.endswith("%}")
            is_comment = piece.startswith("{#") and piece.endswith("#}")

            if is_var or is_tag or is_comment:
                inner = piece[2:-2]
                trim_left = inner.startswith("-")
                trim_right = inner.endswith("-")
                if trim_left:
                    inner = inner[1:]
                if trim_right:
                    inner = inner[:-1]
                inner = inner.strip()

                if trim_left and tokens and tokens[-1].kind == "TEXT":
                    tokens[-1].value = tokens[-1].value.rstrip()

                if is_var:
                    tokens.append(Token("VAR", inner, line))
                elif is_tag:
                    tokens.append(Token("TAG", inner, line))
                # comments are dropped at the lexer stage — they carry no meaning downstream

                pending_ltrim = trim_right
            else:
                if pending_ltrim:
                    piece = piece.lstrip()
                    pending_ltrim = False
                tokens.append(Token("TEXT", piece, line))

            line += piece.count("\n")

        return tokens


# =====================================================================================
# Stage 2 — Parser  (tokens -> AST)
# =====================================================================================
#
# This is where "{% if %} ... {% endif %}" stops being two independent tags and
# becomes a single IfNode wrapping everything between them.

class Node:
    pass


@dataclass
class TextNode(Node):
    text: str


@dataclass
class VarNode(Node):
    expr: "Expr"


@dataclass
class IfNode(Node):
    branches: list[tuple["Expr", list[Node]]]   # [(cond, body), ...] in order: if, elif*, else(cond=None)


@dataclass
class ForNode(Node):
    loop_vars: list[str]      # 1 item for "for x in xs", 2 for "for k, v in mapping"
    iterable: "Expr"
    body: list[Node]


@dataclass
class BlockNode(Node):
    name: str
    body: list[Node]


@dataclass
class ExtendsNode(Node):
    parent_name: str


@dataclass
class IncludeNode(Node):
    template_name: str


class Parser:
    """Recursive-descent parser over the flat token stream."""

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse(self) -> list[Node]:
        nodes = self._parse_nodes(stop_tags=())
        if self.pos < len(self.tokens):
            leftover = self._peek()
            raise LoomSyntaxError(f"Unexpected tag '{leftover.value}' with no opener", leftover.line)
        return nodes

    def _parse_nodes(self, stop_tags: tuple[str, ...]) -> list[Node]:
        """Parse nodes until EOF or a tag whose keyword is in stop_tags (which is left unconsumed)."""
        nodes: list[Node] = []

        while True:
            tok = self._peek()
            if tok is None:
                if stop_tags:
                    raise LoomSyntaxError(f"Unexpected end of template, expected one of {stop_tags}")
                return nodes

            if tok.kind == "TEXT":
                nodes.append(TextNode(tok.value))
                self._advance()
                continue

            if tok.kind == "VAR":
                nodes.append(VarNode(parse_expr(tok.value)))
                self._advance()
                continue

            if tok.kind == "TAG":
                keyword = tok.value.split(None, 1)[0] if tok.value else ""
                if keyword in stop_tags:
                    return nodes
                nodes.append(self._parse_tag())
                continue

            raise LoomSyntaxError(f"Unknown token kind {tok.kind}", tok.line)

    def _parse_tag(self) -> Node:
        tok = self._advance()
        body = tok.value
        keyword, _, rest = body.partition(" ")
        rest = rest.strip()

        if keyword == "if":
            return self._parse_if(rest, tok.line)
        if keyword == "for":
            return self._parse_for(rest, tok.line)
        if keyword == "block":
            return self._parse_block(rest, tok.line)
        if keyword == "extends":
            return ExtendsNode(_unquote(rest))
        if keyword == "include":
            return IncludeNode(_unquote(rest))
        if keyword in ("elif", "else", "endif", "endfor", "endblock"):
            raise LoomSyntaxError(f"'{keyword}' with no matching opening tag", tok.line)

        raise LoomSyntaxError(f"Unknown tag '{keyword}'", tok.line)

    def _parse_if(self, cond_src: str, line: int) -> IfNode:
        branches: list[tuple[Expr | None, list[Node]]] = []
        cond = parse_expr(cond_src)
        body = self._parse_nodes(stop_tags=("elif", "else", "endif"))
        branches.append((cond, body))

        while True:
            tok = self._peek()
            if tok is None:
                raise LoomSyntaxError("Unclosed '{% if %}' — missing '{% endif %}'", line)
            keyword, _, rest = tok.value.partition(" ")
            rest = rest.strip()

            if keyword == "elif":
                self._advance()
                cond = parse_expr(rest)
                body = self._parse_nodes(stop_tags=("elif", "else", "endif"))
                branches.append((cond, body))
                continue

            if keyword == "else":
                self._advance()
                body = self._parse_nodes(stop_tags=("endif",))
                branches.append((None, body))
                # after else there must be endif next
                tok2 = self._peek()
                if tok2 is None or tok2.value.partition(" ")[0] != "endif":
                    raise LoomSyntaxError("Unclosed '{% if %}' — missing '{% endif %}'", line)
                self._advance()
                return IfNode(branches)

            if keyword == "endif":
                self._advance()
                return IfNode(branches)

            raise LoomSyntaxError(f"Unexpected '{keyword}' inside if-block", tok.line)

    def _parse_for(self, header: str, line: int) -> ForNode:
        m = re.match(r"^(.+?)\s+in\s+(.+)$", header)
        if not m:
            raise LoomSyntaxError(f"Malformed for-loop header: 'for {header}'", line)
        vars_part, iterable_part = m.group(1).strip(), m.group(2).strip()
        loop_vars = [v.strip() for v in vars_part.split(",")]
        for v in loop_vars:
            if not re.match(r"^[A-Za-z_]\w*$", v):
                raise LoomSyntaxError(f"Invalid loop variable name '{v}'", line)

        iterable = parse_expr(iterable_part)
        body = self._parse_nodes(stop_tags=("endfor",))

        tok = self._peek()
        if tok is None or tok.value.partition(" ")[0] != "endfor":
            raise LoomSyntaxError("Unclosed '{% for %}' — missing '{% endfor %}'", line)
        self._advance()

        return ForNode(loop_vars, iterable, body)

    def _parse_block(self, name: str, line: int) -> BlockNode:
        name = name.strip()
        if not re.match(r"^[A-Za-z_]\w*$", name):
            raise LoomSyntaxError(f"Invalid block name '{name}'", line)
        body = self._parse_nodes(stop_tags=("endblock",))
        tok = self._peek()
        if tok is None or tok.value.partition(" ")[0] != "endblock":
            raise LoomSyntaxError("Unclosed '{% block %}' — missing '{% endblock %}'", line)
        self._advance()
        return BlockNode(name, body)


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


# =====================================================================================
# Expression sub-language — powers {{ ... }} and {% if ... %} / {% for x in ... %}
# =====================================================================================
#
# Grammar (recursive descent, lowest to highest precedence):
#   expr        := or_expr
#   or_expr     := and_expr ("or" and_expr)*
#   and_expr    := not_expr ("and" not_expr)*
#   not_expr    := "not" not_expr | comparison
#   comparison  := pipeline (("=="|"!="|"<="|">="|"<"|">"|"in"|"not in") pipeline)?
#   pipeline    := atom ("|" filter_call)*
#   atom        := NUMBER | STRING | "True" | "False" | "None"
#                | dotted_name | "(" expr ")"

_TOKEN_RE = re.compile(r"""
    \s*(?:
        (?P<string>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')
      | (?P<number>\d+\.\d+|\d+)
      | (?P<op>==|!=|<=|>=|\bnot\s+in\b|\bnot\b|\band\b|\bor\b|\bin\b|<|>|\||\(|\)|,)
      | (?P<name>[A-Za-z_]\w*(?:\.(?:[A-Za-z_]\w*|\d+))*)
    )
""", re.VERBOSE)


class Expr:
    """Base class for expression AST nodes. Evaluated via .eval(ctx)."""
    def eval(self, ctx: "RenderContext") -> Any:
        raise NotImplementedError


@dataclass
class Literal(Expr):
    value: Any
    def eval(self, ctx):
        return self.value


@dataclass
class Name(Expr):
    path: str
    def eval(self, ctx):
        return ctx.lookup(self.path)


@dataclass
class UnaryOp(Expr):
    op: str
    operand: Expr
    def eval(self, ctx):
        val = self.operand.eval(ctx)
        if self.op == "not":
            return not _truthy(val)
        raise LoomRenderError(f"Unknown unary operator '{self.op}'")


@dataclass
class BinOp(Expr):
    op: str
    left: Expr
    right: Expr
    def eval(self, ctx):
        if self.op == "and":
            lv = self.left.eval(ctx)
            return self.right.eval(ctx) if _truthy(lv) else lv
        if self.op == "or":
            lv = self.left.eval(ctx)
            return lv if _truthy(lv) else self.right.eval(ctx)

        lv, rv = self.left.eval(ctx), self.right.eval(ctx)
        if self.op == "==":
            return lv == rv
        if self.op == "!=":
            return lv != rv
        if self.op == "<":
            return lv < rv
        if self.op == "<=":
            return lv <= rv
        if self.op == ">":
            return lv > rv
        if self.op == ">=":
            return lv >= rv
        if self.op == "in":
            return lv in rv
        if self.op == "not in":
            return lv not in rv
        raise LoomRenderError(f"Unknown binary operator '{self.op}'")


@dataclass
class FilterExpr(Expr):
    target: Expr
    name: str
    args: list[Expr]
    def eval(self, ctx):
        val = self.target.eval(ctx)
        fn = ctx.env.filters.get(self.name)
        if fn is None:
            raise LoomRenderError(f"Unknown filter '{self.name}'")
        args = [a.eval(ctx) for a in self.args]
        return fn(val, *args)


def _truthy(v: Any) -> bool:
    return bool(v)


class _ExprTokenizer:
    def __init__(self, src: str):
        self.tokens: list[tuple[str, str]] = []
        pos = 0
        while pos < len(src):
            m = _TOKEN_RE.match(src, pos)
            if not m or m.end() == pos:
                if src[pos:].strip() == "":
                    break
                raise LoomSyntaxError(f"Cannot parse expression near: {src[pos:pos+20]!r}")
            pos = m.end()
            if m.group("string") is not None:
                self.tokens.append(("string", m.group("string")))
            elif m.group("number") is not None:
                self.tokens.append(("number", m.group("number")))
            elif m.group("op") is not None:
                self.tokens.append(("op", re.sub(r"\s+", " ", m.group("op").strip())))
            elif m.group("name") is not None:
                self.tokens.append(("name", m.group("name")))
        self.i = 0

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else (None, None)

    def next(self):
        tok = self.peek()
        self.i += 1
        return tok


class _ExprParser:
    def __init__(self, src: str):
        self.src = src
        self.t = _ExprTokenizer(src)

    def parse(self) -> Expr:
        expr = self._or_expr()
        if self.t.peek() != (None, None):
            raise LoomSyntaxError(f"Unexpected token near end of expression: '{self.src}'")
        return expr

    def _or_expr(self) -> Expr:
        node = self._and_expr()
        while self.t.peek() == ("op", "or"):
            self.t.next()
            node = BinOp("or", node, self._and_expr())
        return node

    def _and_expr(self) -> Expr:
        node = self._not_expr()
        while self.t.peek() == ("op", "and"):
            self.t.next()
            node = BinOp("and", node, self._not_expr())
        return node

    def _not_expr(self) -> Expr:
        if self.t.peek() == ("op", "not"):
            self.t.next()
            return UnaryOp("not", self._not_expr())
        return self._comparison()

    def _comparison(self) -> Expr:
        node = self._pipeline()
        kind, val = self.t.peek()
        if kind == "op" and val in ("==", "!=", "<", "<=", ">", ">=", "in", "not in"):
            self.t.next()
            rhs = self._pipeline()
            node = BinOp(val, node, rhs)
        return node

    def _pipeline(self) -> Expr:
        node = self._atom()
        while self.t.peek() == ("op", "|"):
            self.t.next()
            kind, name = self.t.next()
            if kind != "name":
                raise LoomSyntaxError(f"Expected filter name after '|' in '{self.src}'")
            args: list[Expr] = []
            if self.t.peek() == ("op", "("):
                self.t.next()
                if self.t.peek() != ("op", ")"):
                    args.append(self._or_expr())
                    while self.t.peek() == ("op", ","):
                        self.t.next()
                        args.append(self._or_expr())
                if self.t.next() != ("op", ")"):
                    raise LoomSyntaxError(f"Expected ')' to close filter args in '{self.src}'")
            node = FilterExpr(node, name, args)
        return node

    def _atom(self) -> Expr:
        kind, val = self.t.next()
        if kind == "string":
            return Literal(val[1:-1].encode().decode("unicode_escape"))
        if kind == "number":
            return Literal(float(val) if "." in val else int(val))
        if kind == "name":
            if val == "True":
                return Literal(True)
            if val == "False":
                return Literal(False)
            if val == "None":
                return Literal(None)
            return Name(val)
        if kind == "op" and val == "(":
            inner = self._or_expr()
            if self.t.next() != ("op", ")"):
                raise LoomSyntaxError(f"Expected ')' in '{self.src}'")
            return inner
        raise LoomSyntaxError(f"Unexpected token in expression: '{self.src}'")


_expr_cache: dict[str, Expr] = {}


def parse_expr(src: str) -> Expr:
    if src not in _expr_cache:
        _expr_cache[src] = _ExprParser(src).parse()
    return _expr_cache[src]


# =====================================================================================
# Stage 3 — Renderer
# =====================================================================================

class RenderContext:
    """Wraps the user-supplied data dict plus a stack of loop-local scopes."""

    def __init__(self, data: dict, env: "Environment"):
        self.scopes: list[dict] = [data]
        self.env = env

    def push(self, scope: dict):
        self.scopes.append(scope)

    def pop(self):
        self.scopes.pop()

    def lookup(self, dotted_path: str) -> Any:
        first, *rest = dotted_path.split(".")
        value = _UNSET = object()
        for scope in reversed(self.scopes):
            if first in scope:
                value = scope[first]
                break
        if value is _UNSET:
            if self.env.strict_undefined:
                raise LoomRenderError(f"Undefined variable '{dotted_path}'")
            return ""
        for part in rest:
            value = _resolve_attr(value, part)
            if value is _UNSET_MARKER:
                if self.env.strict_undefined:
                    raise LoomRenderError(f"Undefined variable '{dotted_path}'")
                return ""
        return value


_UNSET_MARKER = object()


def _resolve_attr(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name, _UNSET_MARKER)
    if isinstance(value, (list, tuple)):
        try:
            return value[int(name)]
        except (ValueError, IndexError):
            return _UNSET_MARKER
    return getattr(value, name, _UNSET_MARKER)


class Renderer:
    def __init__(self, env: "Environment"):
        self.env = env

    def render(self, nodes: list[Node], ctx: RenderContext, blocks: dict[str, list[Node]] | None = None) -> str:
        out: list[str] = []
        blocks = blocks or {}
        for node in nodes:
            out.append(self._render_node(node, ctx, blocks))
        return "".join(out)

    def _render_node(self, node: Node, ctx: RenderContext, blocks: dict[str, list[Node]]) -> str:
        if isinstance(node, TextNode):
            return node.text

        if isinstance(node, VarNode):
            value = node.expr.eval(ctx)
            text = "" if value is None else str(value)
            return html.escape(text) if self.env.autoescape else text

        if isinstance(node, IfNode):
            for cond, body in node.branches:
                if cond is None or _truthy(cond.eval(ctx)):
                    return self.render(body, ctx, blocks)
            return ""

        if isinstance(node, ForNode):
            iterable = node.iterable.eval(ctx)
            if iterable is None:
                iterable = []
            pieces: list[str] = []
            items = iterable.items() if (isinstance(iterable, dict) and len(node.loop_vars) == 2) else iterable
            try:
                seq = list(items)
            except TypeError:
                raise LoomRenderError(f"Value is not iterable in for-loop")
            n = len(seq)
            for idx, item in enumerate(seq):
                scope: dict[str, Any] = {}
                if len(node.loop_vars) == 2:
                    k, v = item
                    scope[node.loop_vars[0]] = k
                    scope[node.loop_vars[1]] = v
                else:
                    scope[node.loop_vars[0]] = item
                scope["loop"] = {
                    "index": idx + 1, "index0": idx,
                    "first": idx == 0, "last": idx == n - 1,
                    "length": n,
                }
                ctx.push(scope)
                pieces.append(self.render(node.body, ctx, blocks))
                ctx.pop()
            return "".join(pieces)

        if isinstance(node, BlockNode):
            # a child template's block overrides the parent's default body
            body = blocks.get(node.name, node.body)
            return self.render(body, ctx, blocks)

        if isinstance(node, IncludeNode):
            sub = self.env.get(node.template_name)
            return self.render(sub.nodes, ctx, blocks={})

        if isinstance(node, ExtendsNode):
            # handled at Template.render() time, never reached during normal walk
            return ""

        raise LoomRenderError(f"Cannot render unknown node type {type(node).__name__}")


# =====================================================================================
# Built-in filters
# =====================================================================================

def _f_upper(v, *_): return str(v).upper()
def _f_lower(v, *_): return str(v).lower()
def _f_capitalize(v, *_): return str(v).capitalize()
def _f_title(v, *_): return str(v).title()
def _f_trim(v, *_): return str(v).strip()
def _f_length(v, *_): return len(v)
def _f_round(v, ndigits=0, *_): return round(float(v), int(ndigits))
def _f_default(v, fallback="", *_): return fallback if (v is None or v == "") else v
def _f_join(v, sep=", ", *_): return str(sep).join(str(x) for x in v)
def _f_escape(v, *_): return html.escape(str(v))
def _f_first(v, *_): return v[0] if len(v) else ""
def _f_last(v, *_): return v[-1] if len(v) else ""

DEFAULT_FILTERS = {
    "upper": _f_upper, "lower": _f_lower, "capitalize": _f_capitalize,
    "title": _f_title, "trim": _f_trim, "length": _f_length,
    "round": _f_round, "default": _f_default, "join": _f_join,
    "escape": _f_escape, "e": _f_escape, "first": _f_first, "last": _f_last,
}


# =====================================================================================
# Public API — Template & Environment
# =====================================================================================

class Template:
    def __init__(self, source: str, env: "Environment | None" = None, name: str = "<string>"):
        self.source = source
        self.name = name
        self.env = env or Environment()
        tokens = Lexer(source).tokenize()
        self.nodes = Parser(tokens).parse()

    def render(self, context: dict | None = None) -> str:
        context = context or {}
        ctx = RenderContext(context, self.env)
        renderer = Renderer(self.env)

        # template inheritance: if this template starts with {% extends %},
        # collect its top-level {% block %} overrides and render the parent
        # with those blocks substituted in.
        extends = next((n for n in self.nodes if isinstance(n, ExtendsNode)), None)
        if extends is not None:
            own_blocks = {n.name: n.body for n in self.nodes if isinstance(n, BlockNode)}
            parent = self.env.get(extends.parent_name)
            return renderer.render(parent.nodes, ctx, blocks=own_blocks)

        return renderer.render(self.nodes, ctx)


@dataclass
class Environment:
    """Holds shared config (filters, autoescape, undefined policy) and a template registry."""
    templates: dict[str, str] = field(default_factory=dict)
    autoescape: bool = False
    strict_undefined: bool = False
    filters: dict = field(default_factory=lambda: dict(DEFAULT_FILTERS))
    _compiled: dict = field(default_factory=dict, repr=False)

    def add_filter(self, name: str, fn):
        self.filters[name] = fn

    def add_template(self, name: str, source: str):
        self.templates[name] = source
        self._compiled.pop(name, None)

    def get(self, name: str) -> Template:
        if name not in self._compiled:
            if name not in self.templates:
                raise LoomError(f"No such template registered: '{name}'")
            self._compiled[name] = Template(self.templates[name], env=self, name=name)
        return self._compiled[name]

    def from_string(self, source: str) -> Template:
        return Template(source, env=self)


# =====================================================================================
# Demo / self-test — run `python loom.py`
# =====================================================================================

if __name__ == "__main__":
    template = """<h1>Hello {{ user.name }}!</h1>
{% if user.is_admin %}
  <p>You have admin access.</p>
{% endif %}
<ul>
{% for item in items %}
  <li>{{ item }}</li>
{% endfor %}
</ul>"""

    context = {"user": {"name": "Anmol", "is_admin": True}, "items": ["Pen", "Book"]}

    print("=== Worked example from the spec ===")
    print(Template(template).render(context))

    print("\n=== Filters ===")
    print(Template("{{ name | upper }} costs {{ price | round(2) }}").render(
        {"name": "pen", "price": 12.3456}))

    print("\n=== elif/else ===")
    t = Template("{% if score >= 90 %}A{% elif score >= 75 %}B{% else %}C{% endif %}")
    for s in (95, 80, 50):
        print(s, "->", t.render({"score": s}))

    print("\n=== dict for-loop + loop var ===")
    t = Template("{% for k, v in scores %}{{ loop.index }}. {{ k }}={{ v }}{% if not loop.last %}, {% endif %}{% endfor %}")
    print(t.render({"scores": {"Anmol": 95, "Rhea": 88}}))

    print("\n=== template inheritance ===")
    env = Environment()
    env.add_template("base", "<html><body>{% block content %}default{% endblock %}</body></html>")
    env.add_template("page", '{% extends "base" %}{% block content %}<h1>{{ title }}</h1>{% endblock %}')
    print(env.get("page").render({"title": "Loom"}))

    print("\n=== autoescape ===")
    env2 = Environment(autoescape=True)
    print(env2.from_string("{{ payload }}").render({"payload": "<script>alert(1)</script>"}))

    print("\n=== missing variable (silent) & strict mode ===")
    print(repr(Template("{{ missing.deep.path }}").render({})))
    strict_env = Environment(strict_undefined=True)
    try:
        strict_env.from_string("{{ missing }}").render({})
    except LoomRenderError as e:
        print("raised as expected:", e)

    print("\n=== whitespace control ===")
    t = Template("Items:\n{% for x in items -%}\n  {{ x }}\n{%- endfor %}\nDone")
    print(repr(t.render({"items": ["a", "b"]})))

    print("\n=== unclosed tag error ===")
    try:
        Template("{% if x %}no endif")
    except LoomSyntaxError as e:
        print("raised as expected:", e)
