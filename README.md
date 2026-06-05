# Scout v0 - Resume & Job Description Gap Analysis Tool

A CLI tool that extracts structured JSON data from resumes (PDFs) and job descriptions (TXT), and performs deterministic gap analysis using Google's Gemini API with Instructor.

## Features

- **Resume Extraction**: Parses PDF resumes and extracts skills, seniority level, and years of experience
- **Job Description Analysis**: Extracts must-haves, nice-to-haves, and minimum experience requirements
- **Gap Analysis**: Deterministically evaluates if resume meets job requirements with evidence-based results
- **Structured Output**: JSON output combining all extracted data and gap analysis

## Installation

### Things you need

- Python 3.8+
- Google API Key (for Gemini 2.5 Flash)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/PranavMunigala/Scout.V0.git
cd Scout.V0
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set your Google API key:
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

## Usage

### Basic Command

```bash
python main.py extract --resume resume.pdf --jd job_description.txt --out results.json
```

### Options

- `--resume`: Path to the resume PDF file (required)
- `--jd`: Path to the job description text file (required)
- `--out`: Output JSON file path (default: `scout_output.json`)

### Example

```bash
python main.py extract \
  --resume /path/to/resume.pdf \
  --jd /path/to/job_description.txt \
  --out /path/to/analysis.json
```

## Output Format

The JSON output contains three main sections:

```json
{
  "resume": {
    "skills": ["Python", "FastAPI", "PostgreSQL", ...],
    "seniority_level": "mid",
    "years_of_experience": 5.5
  },
  "job_description": {
    "must_haves": ["5+ years Python", "AWS experience", ...],
    "nice_to_haves": ["Kubernetes", "Published work", ...],
    "years_required": 5
  },
  "gap_analysis": [
    {
      "skill_or_requirement": "5+ years Python",
      "evidence_in_resume": true,
      "notes": "Resume shows 6 years of Python experience across three companies"
    },
    {
      "skill_or_requirement": "AWS experience",
      "evidence_in_resume": false,
      "notes": "No mention of AWS in the resume; only Azure cloud experience listed"
    }
  ]
}
```

## Architecture

### Project Structure

```
scout/
├── __init__.py           # Package initialization
├── schemas.py            # Pydantic models (ResumeSchema, JobDescriptionSchema, GapAnalysisSchema)
├── core.py               # Core functions (extract_resume, extract_jd, analyze_gaps)
├── logger.py             # Logging configuration for LLM errors
└── cli.py                # CLI interface using Typer

main.py                    # Entry point
requirements.txt           # Python dependencies
README.md                  # This file
```

### Schemas

- **ResumeSchema**: skills, seniority_level, years_of_experience
- **JobDescriptionSchema**: must_haves, nice_to_haves, years_required
- **GapAnalysisSchema**: List of gap items with evidence and notes

### Key Dependencies

- **typer**: CLI framework
- **pydantic**: Schema validation (v2)
- **instructor**: Structured LLM outputs (ensures output from LLM matches Schema)
- **google-generativeai**: Gemini API access
- **pymupdf (fitz)**: PDF text extraction

## Error Handling

All LLM validation errors and retries are logged to `scout_retries.log`. The tool:
- Validates all extracted data against Pydantic schemas
- Retries on validation failures (via Instructor)
- Logs detailed error messages for debugging
- Exits gracefully with meaningful error messages

## Workflow

1. User provides resume PDF and job description text
2. Scout extracts resume data (skills, experience, seniority)
3. Scout extracts JD requirements (must-haves, nice-to-haves, years)
4. Scout performs gap analysis (checking each must-have against resume)
5. Results are saved as JSON with evidence-based analysis

## Version

- **Current Version**: 0.1.0

## License

MIT

## Author

Pranav Munigala
