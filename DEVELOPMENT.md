# DEVELOPMENT.md - Scout v0 Development Guide

## Setup

1. Create virtual environment: python -m venv venv
2. Activate: source venv/bin/activate (Linux/Mac) or venv\Scripts\activate (Windows)
3. Install: pip install -r requirements.txt
4. Set API key: export GOOGLE_API_KEY="your-key-here"

## Project Structure

- scout/schemas.py: Pydantic models with prompt engineering
- scout/core.py: Extraction and analysis functions
- scout/cli.py: Typer CLI commands
- scout/logger.py: Logging configuration
- main.py: Entry point

## Running

python main.py extract --resume resume.pdf --jd job.txt --out output.json

## Development Workflow

1. Modify code as needed
2. Test with: python -m py_compile scout/*.py
3. Run full pipeline with examples
4. Check scout_retries.log for errors
5. Commit and push changes

See ARCHITECTURE.md for detailed technical design.
