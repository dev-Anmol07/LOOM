# Loom — zero-dependency template engine
# Single-command verification, per Zero Dependency 2026 rules.
#
#   make          -> runs everything: dependency proof + tests + self-demo
#   make verify   -> same as above (explicit name)
#   make test     -> just the test suite
#   make deps     -> just the dependency proof
#   make demo     -> just the self-demo

.PHONY: all verify test deps demo

all: verify

verify: deps test demo
	@echo ""
	@echo "=== Loom: all checks passed ==="

deps:
	@echo "--- dependency proof ---"
	python3 check_dependencies.py

test:
	@echo "--- test suite ---"
	python3 -m unittest test_loom.py -v

demo:
	@echo "--- self-demo ---"
	python3 loom.py
