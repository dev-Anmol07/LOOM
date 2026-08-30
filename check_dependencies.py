"""
Dependency proof for Loom.

Parses loom.py's own import statements (via the `ast` module — no third-party
static-analysis tool involved) and checks every one against Python's official
list of standard-library module names. Exits non-zero and prints a failure if
anything outside the standard library is imported.

Run it:
    python check_dependencies.py

This only checks loom.py itself — the core deliverable for the zero-dependency
claim. Files under demos/ may use disclosed, non-core dependencies (see the
"Disclosed non-core dependency" section of STDLIB.md); those are demo hosts,
not part of the engine, and are intentionally excluded from this check.
"""

import ast
import sys
import os

TARGET_FILE = os.path.join(os.path.dirname(__file__), "loom.py")


def get_imported_module_names(filepath: str) -> set[str]:
    with open(filepath) as f:
        tree = ast.parse(f.read(), filename=filepath)

    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:  # skip relative imports (level > 0)
                names.add(node.module.split(".")[0])
    return names


def main() -> int:
    if not os.path.isfile(TARGET_FILE):
        print(f"FAIL: could not find {TARGET_FILE}")
        return 1

    imported = get_imported_module_names(TARGET_FILE)

    # sys.stdlib_module_names is available on Python 3.10+ and is the
    # authoritative, version-matched list of standard-library module names —
    # more reliable than hand-maintaining our own list.
    stdlib_names = getattr(sys, "stdlib_module_names", None)
    if stdlib_names is None:
        print("FAIL: this Python version doesn't expose sys.stdlib_module_names "
              "(needs Python 3.10+) — cannot verify automatically.")
        return 1

    print(f"Checked file: {TARGET_FILE}")
    print(f"Python version: {sys.version.split()[0]}")
    print(f"Imports found: {sorted(imported) if imported else '(none)'}")
    print()

    non_stdlib = sorted(name for name in imported if name not in stdlib_names)

    if non_stdlib:
        print(f"FAIL: found {len(non_stdlib)} non-stdlib import(s): {non_stdlib}")
        return 1

    print(f"PASS: all {len(imported)} import(s) in loom.py are Python standard library.")
    print("Zero third-party runtime dependencies confirmed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
