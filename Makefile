.PHONY: help test import clean venv install setup

# Default target
help:
	@echo "Available commands:"
	@echo "  make test         - Run the full test suite"
	@echo "  make import       - Run the importer (uses config.ini)"
	@echo "  make import-batch - Run importer for single batch"
	@echo "  make import-chaos - Run importer (chaos mode - ignores errors)"
	@echo "  make setup        - Interactive setup (creates config.ini)"
	@echo "  make venv         - Create virtual environment"
	@echo "  make install      - Install dependencies"
	@echo "  make clean        - Clean up generated files"

# Run tests
test:
	@echo "Running test suite..."
	. venv/bin/activate && python -m pytest -v

# Run importer with common options
import:
	@echo "Running importer..."
	. venv/bin/activate && python -m keep.importer

# Run importer for single batch (common use case)
import-batch:
	@echo "Running importer (single batch)..."
	. venv/bin/activate && python -m keep.importer --max-batches 1

# Run importer with error tolerance (chaos mode!)
import-chaos:
	@echo "Running importer (chaos mode - ignoring all errors)..."
	. venv/bin/activate && python -m keep.importer --ignore-errors

# Create virtual environment
venv:
	@echo "Creating virtual environment..."
	python3 -m venv venv
	@echo "Virtual environment created. Run 'source venv/bin/activate' to activate."

# Install dependencies
install:
	@echo "Installing dependencies..."
	. venv/bin/activate && pip install -r requirements.txt

# Interactive setup
setup:
	@echo "Running interactive setup..."
	. venv/bin/activate && python configure.py

# Clean up
clean:
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf build/
	rm -rf dist/ 