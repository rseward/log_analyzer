# Build and setup targets
build:
	uv venv .venv
	uv pip install -r requirements.txt
	uv pip install -r requirements-test.txt

logs.db:
	uv run log_analyzer.py
	
query:	logs.db
	litecli logs.db
	
# Testing targets
test:
	uv run python -m pytest tests/ -v

test-unit:
	uv run python -m pytest tests/ -v -k "not integration"

test-integration:
	uv run python -m pytest tests/test_integration.py -v

# Test coverage targets
coverage:
	uv run python -m pytest tests/ --cov=. --cov-report=html --cov-report=term-missing --cov-config=.coveragerc

coverage-xml:
	uv run python -m pytest tests/ --cov=. --cov-report=xml --cov-config=.coveragerc

coverage-report:
	uv run python -m pytest tests/ --cov=. --cov-report=term-missing --cov-config=.coveragerc

# Code quality targets
ruff:
	uv run ruff check .

ruff-fix:
	uv run ruff check . --fix

ruff-format:
	uv run ruff format .

ruff-all: ruff-fix ruff-format

# Combined quality check
quality: ruff coverage

# Development helpers
clean:
	rm -rf .pytest_cache __pycache__ .coverage htmlcov .ruff_cache
	rm -f *.pyc tests/*.pyc

help:
	@echo "Available targets:"
	@echo "  build         - Set up virtual environment and install dependencies"
	@echo "  logs.db       - Generate sample logs database"
	@echo "  query         - Open interactive database query interface"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  coverage      - Run tests with HTML coverage report"
	@echo "  coverage-xml  - Run tests with XML coverage report (for CI)"
	@echo "  coverage-report - Run tests with terminal coverage report"
	@echo "  ruff          - Run ruff linter checks"
	@echo "  ruff-fix      - Run ruff linter with auto-fixes"
	@echo "  ruff-format   - Run ruff formatter"
	@echo "  ruff-all      - Run ruff with fixes and formatting"
	@echo "  quality       - Run all code quality checks (ruff + coverage)"
	@echo "  clean         - Clean up generated files and caches"
	@echo "  help          - Show this help message"

.PHONY: build test test-unit test-integration coverage coverage-xml coverage-report ruff ruff-fix ruff-format ruff-all quality clean help
