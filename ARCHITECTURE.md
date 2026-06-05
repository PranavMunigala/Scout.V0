"""ARCHITECTURE.md - Scout v0 Technical Architecture"""

# Scout v0 - Technical Architecture

## Overview

Scout v0 is a production-ready CLI tool for deterministic gap analysis between resumes and job descriptions. 
It uses structured LLM outputs (via Instructor + Gemini) to extract and analyze data with high precision.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Scout CLI (typer)                         │
│                     scout/cli.py                             │
│                                                              │
│  extract --resume <pdf> --jd <txt> --out <json>            │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             ▼                                ▼
    ┌──────────────────┐         ┌──────────────────┐
    │  extract_resume  │         │   extract_jd     │
    │  scout/core.py   │         │  scout/core.py   │
    └────────┬─────────┘         └────────┬─────────┘
             │                           │
             ├─ PDF → Text (pymupdf)     └─ Load File → Text
             │                           
             ├─ LLM Prompt (Instructor)  ├─ LLM Prompt (Instructor)
             │                           │
             ├─ Structured Output        ├─ Structured Output
             │  (ResumeSchema)           │  (JobDescriptionSchema)
             │                           │
             └─────────────┬─────────────┘
                           │
                           ▼
                  ┌────────────────────┐
                  │  analyze_gaps      │
                  │  scout/core.py     │
                  │                    │
                  │ Resume + JD        │
                  │  ↓                 │
                  │ For each must-have:│
                  │  Check Resume      │
                  │  (Instructor)      │
                  │  ↓                 │
                  │ GapAnalysisSchema  │
                  └────────┬───────────┘
                           │
                           ▼
                  ┌────────────────────┐
                  │  Combined JSON     │
                  │  scout_output.json │
                  └────────────────────┘
```

## Module Breakdown

### 1. `scout/schemas.py` - Pydantic Models
**Purpose**: Define strict, prompt-engineered data structures

**Models**:
- **ResumeSchema**
  - `skills: List[str]` - Comprehensive skill list
  - `seniority_level: Literal["junior", "mid", "senior"]` - Career level
  - `years_of_experience: float` - Total years worked

- **JobDescriptionSchema**
  - `must_haves: List[str]` - Hard requirements
  - `nice_to_haves: List[str]` - Optional requirements
  - `years_required: int` - Minimum years needed

- **GapAnalysisItem**
  - `skill_or_requirement: str` - Must-have item
  - `evidence_in_resume: bool` - Found/Not found
  - `notes: str` - Proof or explanation

- **GapAnalysisSchema**
  - `gap_analysis: List[GapAnalysisItem]` - All gap items

**Design**: Every `Field(description=...)` is carefully crafted to prevent LLM hallucination.

### 2. `scout/core.py` - Core Extraction Logic
**Purpose**: Implement the three main extraction functions

**Functions**:
- **`extract_resume(pdf_path: str) -> ResumeSchema`**
  - Opens PDF with pymupdf (fitz)
  - Extracts all text from all pages
  - Sends to Instructor-wrapped Gemini API
  - Returns structured ResumeSchema
  - Logs errors to scout_retries.log

- **`extract_jd(jd_text: str) -> JobDescriptionSchema`**
  - Takes raw job description text
  - Sends to Instructor-wrapped Gemini API
  - Returns structured JobDescriptionSchema
  - Logs errors to scout_retries.log

- **`analyze_gaps(resume: ResumeSchema, jd: JobDescriptionSchema) -> GapAnalysisSchema`**
  - Iterates through JD must-haves
  - For each requirement, calls Instructor to evaluate against resume
  - Returns comprehensive gap analysis
  - Logs errors to scout_retries.log

**Key Implementation Details**:
- Instructor wraps Gemini client for structured outputs
- Pydantic validation happens automatically via Instructor
- All exceptions logged before re-raising
- Conservative extraction to prevent false positives

### 3. `scout/cli.py` - Command-Line Interface
**Purpose**: Provide user-friendly CLI commands

**Commands**:
- **`extract`** (main command)
  - `--resume <path>` (required): Resume PDF path
  - `--jd <path>` (required): Job description text path
  - `--out <path>` (optional): Output JSON path (default: scout_output.json)
  
  **Workflow**:
  1. Validates file paths exist
  2. Calls extract_resume()
  3. Calls extract_jd()
  4. Calls analyze_gaps()
  5. Combines results into single JSON
  6. Saves to output file
  7. Displays summary

- **`version`**: Show version info

**Error Handling**:
- FileNotFoundError → User-friendly message, exit code 1
- ValidationError → Logged to scout_retries.log, exit code 1
- Generic exceptions → Logged, exit code 1

### 4. `scout/logger.py` - Logging Configuration
**Purpose**: Centralized logging for LLM errors and retries

**Features**:
- Rotating file handler (max 10MB, 5 backups)
- Logs to `scout_retries.log`
- File handler: DEBUG level (detailed)
- Console handler: ERROR+ only (clean user experience)
- Automatic log directory creation

**Log Format**:
```
2024-01-15 10:30:45 - scout.core - ERROR - Resume extraction validation error: ...
```

### 5. `main.py` - Entry Point
**Purpose**: Simple entry point for CLI

**Usage**:
```bash
python main.py extract --resume resume.pdf --jd jd.txt --out output.json
```

## Data Flow

### Complete Pipeline Example

1. **User Input**
   ```bash
   scout extract --resume john.pdf --jd job.txt --out results.json
   ```

2. **Resume Extraction**
   ```
   john.pdf (PDF file)
     ↓ [pymupdf]
   "John Smith, 8 years Python..." (text)
     ↓ [Instructor + Gemini]
   ResumeSchema {
     skills: ["Python", "FastAPI", ...],
     seniority_level: "senior",
     years_of_experience: 8.0
   }
   ```

3. **JD Extraction**
   ```
   job.txt (text file)
     ↓ [Read file]
   "Senior Python Engineer required..." (text)
     ↓ [Instructor + Gemini]
   JobDescriptionSchema {
     must_haves: ["7+ Python", "AWS", ...],
     nice_to_haves: ["Kubernetes", ...],
     years_required: 7
   }
   ```

4. **Gap Analysis**
   ```
   For each must-have in JD:
     Resume + Requirement → Instructor + Gemini
       ↓
     GapAnalysisItem {
       skill_or_requirement: "7+ Python",
       evidence_in_resume: true,
       notes: "Resume shows 8 years of Python"
     }
   ```

5. **Output**
   ```json
   {
     "resume": { ... },
     "job_description": { ... },
     "gap_analysis": [ ... ]
   }
   → results.json
   ```

## Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| CLI | Typer | Easy, modern, clean syntax |
| LLM | Google Gemini 2.5 Flash | Fast, structured outputs via Instructor |
| Structured Outputs | Instructor | Pydantic validation from LLM |
| Schemas | Pydantic v2 | Type safety, validation |
| PDF Extraction | pymupdf (fitz) | Fast, reliable PDF text extraction |
| Logging | Python logging | Built-in, rotating file handlers |
| Packaging | pyproject.toml | Modern Python packaging |

## Error Handling Strategy

### LLM Validation Errors
- Caught by Pydantic (via Instructor)
- Logged to scout_retries.log with full context
- Re-raised to CLI for user feedback
- Instructor auto-retries with different prompts

### File Errors
- PDF not found → FileNotFoundError
- JD file not found → FileNotFoundError
- Output path invalid → Directory auto-created

### API Errors
- GOOGLE_API_KEY not set → ValueError
- API quota exceeded → Propagated to user
- Network timeout → Logged and re-raised

## Configuration

### Environment Variables
- `GOOGLE_API_KEY` (required): Google API key for Gemini

### Constants
- Model: `gemini-2.5-flash` (can be changed to `gemini-2.5-pro`)
- Log file: `scout_retries.log`
- Log rotation: 10MB max, 5 backups
- Output encoding: UTF-8

## Performance Considerations

- **PDF Extraction**: O(pages) - typically 0.5-2 seconds
- **LLM Calls**: ~5-10 seconds per extraction (Instructor may retry)
- **Gap Analysis**: ~2 seconds per must-have (parallel possible with async)
- **Total Pipeline**: ~15-30 seconds for typical resume/JD pair

## Security

- No credentials stored in code
- API key from environment variable only
- No sensitive data logged (only errors)
- PDF text not persisted after extraction
- Output JSON contains no API keys

## Testing (Future)

Suggested test structure:
```
tests/
├── test_schemas.py          # Pydantic model validation
├── test_core.py            # Extraction functions
├── test_cli.py             # CLI commands
└── fixtures/               # Sample resumes, JDs
    ├── resume_senior.pdf
    └── jd_backend.txt
```

## Future Enhancements

1. **Async Support**: Process resume + JD in parallel
2. **Batch Mode**: Process multiple resume/JD pairs
3. **Export Formats**: CSV, HTML, PDF reports
4. **Web Interface**: FastAPI web app frontend
5. **Custom Models**: Support Claude, GPT-4, etc.
6. **Prompt Tuning**: Configurable extraction instructions
7. **Caching**: Cache LLM responses for same inputs
8. **Metrics**: Track gap percentages, trends over time
