# Vinyl Recommendation System - Development Commands

.PHONY: install test lint format clean run dev

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests
test:
	pytest tests/ -v

# Lint code
lint:
	flake8 src/
	mypy src/

# Format code
format:
	black src/ tests/
	black *.py

# Clean cache files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Run the application
run:
	python -m src.api.main

# Development mode with auto-reload
dev:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Setup development environment
setup:
	python -m venv venv
	@echo "Activate virtual environment with: source venv/bin/activate"
	@echo "Then run: make install"

# Initialize database (future)
init-db:
	python -m src.data.database init

# Sync Discogs collection
sync:
	python -m src.data.discogs_client sync