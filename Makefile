.PHONY: install vendor lint typecheck test run

install:
	python3 -m pip install -U pip
	python3 -m pip install -e ".[dev]"

# Populate vendor/ so the app can run without pip on the target (e.g. closed network).
# Run once on a machine with internet, then ship the tree; no pip install needed in prod.
vendor:
	rm -rf vendor
	python3 -m pip install -t vendor -r requirements.txt

lint:
	ruff check .

typecheck:
	mypy .

test:
	pytest

run:
	python3 -m project.main --config clusters.yaml

