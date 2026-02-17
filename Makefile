.PHONY: install lint typecheck test run

install:
	python3 -m pip install -U pip
	python3 -m pip install -e ".[dev]"

lint:
	ruff check .

typecheck:
	mypy .

test:
	pytest

run:
	python3 -m project.main --config clusters.yaml

