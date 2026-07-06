.PHONY: install dev test run clean

# Create a virtual environment and install the package.
install:
	python3 -m venv .venv && .venv/bin/pip install -e .

# Install with development dependencies (pytest).
dev:
	python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

# Run the test suite.
test:
	.venv/bin/pytest -q

# Run the agent against the bundled sample role and candidate.
run:
	.venv/bin/python -m talent_strategist --role examples/sample_role.txt --candidate examples/sample_candidate.txt

# Remove the virtual environment and Python caches.
clean:
	rm -rf .venv .pytest_cache **/__pycache__
