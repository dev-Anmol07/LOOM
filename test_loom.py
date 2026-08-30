"""
Test suite for Loom.

Covers the core feature set plus every edge case listed in Section 7 of the
design doc: unclosed tags, nested loops/conditionals, missing variables,
special-character escaping, and whitespace control.

Run with:  python -m unittest test_loom.py -v
"""

import unittest
from loom import (
    Template, Environment, LoomSyntaxError, LoomRenderError,
)


class TestVariables(unittest.TestCase):
    def test_simple_variable(self):
        self.assertEqual(Template("Hello {{ name }}!").render({"name": "Anmol"}), "Hello Anmol!")

    def test_dotted_access(self):
        self.assertEqual(
            Template("{{ user.name }}").render({"user": {"name": "Anmol"}}),
            "Anmol",
        )

    def test_deep_dotted_access(self):
        self.assertEqual(
            Template("{{ a.b.c }}").render({"a": {"b": {"c": 42}}}),
            "42",
        )

    def test_missing_variable_is_silent_by_default(self):
        self.assertEqual(Template("[{{ missing }}]").render({}), "[]")

    def test_missing_nested_path_is_silent_by_default(self):
        self.assertEqual(Template("[{{ a.b.c }}]").render({"a": {}}), "[]")

    def test_strict_undefined_raises(self):
        env = Environment(strict_undefined=True)
        with self.assertRaises(LoomRenderError):
            env.from_string("{{ missing }}").render({})

    def test_list_index_access(self):
        self.assertEqual(Template("{{ items.0 }}").render({"items": ["a", "b"]}), "a")


class TestFilters(unittest.TestCase):
    def test_upper(self):
        self.assertEqual(Template("{{ x | upper }}").render({"x": "abc"}), "ABC")

    def test_round_with_arg(self):
        self.assertEqual(Template("{{ x | round(2) }}").render({"x": 3.14159}), "3.14")

    def test_chained_filters(self):
        self.assertEqual(Template("{{ x | trim | upper }}").render({"x": "  abc  "}), "ABC")

    def test_default_filter(self):
        self.assertEqual(Template("{{ x | default('none') }}").render({"x": None}), "none")

    def test_join_filter(self):
        self.assertEqual(Template("{{ items | join(', ') }}").render({"items": ["a", "b", "c"]}), "a, b, c")

    def test_unknown_filter_raises(self):
        with self.assertRaises(LoomRenderError):
            Template("{{ x | nope }}").render({"x": 1})


class TestConditionals(unittest.TestCase):
    def test_if_true(self):
        self.assertEqual(Template("{% if x %}yes{% endif %}").render({"x": True}), "yes")

    def test_if_false_no_else(self):
        self.assertEqual(Template("{% if x %}yes{% endif %}").render({"x": False}), "")

    def test_elif_chain(self):
        t = Template("{% if x == 1 %}one{% elif x == 2 %}two{% else %}other{% endif %}")
        self.assertEqual(t.render({"x": 2}), "two")
        self.assertEqual(t.render({"x": 3}), "other")

    def test_comparisons(self):
        t = Template("{% if a >= b %}yes{% else %}no{% endif %}")
        self.assertEqual(t.render({"a": 5, "b": 3}), "yes")
        self.assertEqual(t.render({"a": 1, "b": 3}), "no")

    def test_and_or_not(self):
        t = Template("{% if a and not b %}yes{% else %}no{% endif %}")
        self.assertEqual(t.render({"a": True, "b": False}), "yes")
        self.assertEqual(t.render({"a": True, "b": True}), "no")

    def test_in_operator(self):
        t = Template("{% if x in items %}found{% else %}missing{% endif %}")
        self.assertEqual(t.render({"x": 2, "items": [1, 2, 3]}), "found")
        self.assertEqual(t.render({"x": 9, "items": [1, 2, 3]}), "missing")

    def test_unclosed_if_raises(self):
        with self.assertRaises(LoomSyntaxError):
            Template("{% if x %}no endif here")

    def test_dangling_endif_raises(self):
        with self.assertRaises(LoomSyntaxError):
            Template("{% endif %}")


class TestLoops(unittest.TestCase):
    def test_basic_loop(self):
        self.assertEqual(
            Template("{% for i in items %}{{ i }}{% endfor %}").render({"items": [1, 2, 3]}),
            "123",
        )

    def test_empty_iterable(self):
        self.assertEqual(Template("{% for i in items %}{{ i }}{% endfor %}").render({"items": []}), "")

    def test_none_iterable_is_treated_as_empty(self):
        self.assertEqual(Template("{% for i in items %}{{ i }}{% endfor %}").render({"items": None}), "")

    def test_dict_iteration(self):
        out = Template("{% for k, v in d %}{{ k }}={{ v }};{% endfor %}").render({"d": {"a": 1, "b": 2}})
        self.assertEqual(out, "a=1;b=2;")

    def test_loop_index_first_last(self):
        t = Template("{% for i in items %}{{ loop.index }}:{{ loop.first }}:{{ loop.last }} {% endfor %}")
        out = t.render({"items": ["x", "y"]})
        self.assertEqual(out, "1:True:False 2:False:True ")

    def test_nested_loops(self):
        t = Template("{% for row in rows %}{% for cell in row %}{{ cell }}{% endfor %}|{% endfor %}")
        out = t.render({"rows": [[1, 2], [3, 4]]})
        self.assertEqual(out, "12|34|")

    def test_nested_loop_and_conditional(self):
        t = Template(
            "{% for i in items %}{% if i > 1 %}{{ i }}{% endif %}{% endfor %}"
        )
        self.assertEqual(t.render({"items": [1, 2, 3]}), "23")

    def test_unclosed_for_raises(self):
        with self.assertRaises(LoomSyntaxError):
            Template("{% for i in items %}no endfor")


class TestComments(unittest.TestCase):
    def test_comment_stripped(self):
        self.assertEqual(Template("a{# comment #}b").render({}), "ab")

    def test_multiline_comment_stripped(self):
        self.assertEqual(Template("a{#\nmultiline\ncomment\n#}b").render({}), "ab")


class TestEscaping(unittest.TestCase):
    def test_autoescape_off_by_default(self):
        self.assertEqual(
            Template("{{ x }}").render({"x": "<b>hi</b>"}),
            "<b>hi</b>",
        )

    def test_autoescape_on(self):
        env = Environment(autoescape=True)
        self.assertEqual(
            env.from_string("{{ x }}").render({"x": "<script>alert(1)</script>"}),
            "&lt;script&gt;alert(1)&lt;/script&gt;",
        )

    def test_escape_filter(self):
        self.assertEqual(
            Template("{{ x | escape }}").render({"x": "<b>"}),
            "&lt;b&gt;",
        )


class TestWhitespaceControl(unittest.TestCase):
    def test_trim_right(self):
        out = Template("{% for x in items -%}\n{{ x }}\n{%- endfor %}").render({"items": ["a", "b"]})
        self.assertEqual(out, "ab")

    def test_no_trim_keeps_whitespace(self):
        out = Template("{% for x in items %}\n{{ x }}\n{% endfor %}").render({"items": ["a"]})
        self.assertIn("\n", out)


class TestInheritance(unittest.TestCase):
    def test_extends_and_block_override(self):
        env = Environment()
        env.add_template("base", "<body>{% block content %}default{% endblock %}</body>")
        env.add_template("child", '{% extends "base" %}{% block content %}custom{% endblock %}')
        self.assertEqual(env.get("child").render({}), "<body>custom</body>")

    def test_block_default_used_if_not_overridden(self):
        env = Environment()
        env.add_template("base", "<body>{% block content %}default{% endblock %}</body>")
        env.add_template("child", '{% extends "base" %}')
        self.assertEqual(env.get("child").render({}), "<body>default</body>")

    def test_include(self):
        env = Environment()
        env.add_template("partial", "Hi {{ name }}")
        out = env.from_string('{% include "partial" %}!').render({"name": "Anmol"})
        self.assertEqual(out, "Hi Anmol!")


class TestFullPipeline(unittest.TestCase):
    def test_spec_worked_example(self):
        """Reproduces Section 3 of the design doc exactly."""
        template = (
            "<h1>Hello {{ user.name }}!</h1>\n"
            "{% if user.is_admin %}\n"
            "  <p>You have admin access.</p>\n"
            "{% endif %}\n"
            "<ul>\n"
            "{% for item in items %}\n"
            "  <li>{{ item }}</li>\n"
            "{% endfor %}\n"
            "</ul>"
        )
        context = {"user": {"name": "Anmol", "is_admin": True}, "items": ["Pen", "Book"]}
        out = Template(template).render(context)
        self.assertIn("<h1>Hello Anmol!</h1>", out)
        self.assertIn("<p>You have admin access.</p>", out)
        self.assertIn("<li>Pen</li>", out)
        self.assertIn("<li>Book</li>", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
