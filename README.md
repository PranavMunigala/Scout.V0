# Scout v2

Scout turns a resume and job description into a grounded cover-letter draft. It keeps
the original Gemini + Instructor extraction flow intact, then passes typed data through a
bounded Claude/LangGraph Researcher → Writer → Editor workflow.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set `GOOGLE_API_KEY` for the original `extract` command and `ANTHROPIC_API_KEY` for
`cover-letter`. Scout v2 also expects the sibling
[`claude-skills`](https://github.com/PranavMunigala/claude-skills) repository; override
its location with `SCOUT_COVER_LETTER_SKILL` when needed.

## Use

```powershell
python main.py cover-letter --resume examples/PranavResume28.pdf --jd examples/bdjobdesc.txt --company BD --out bd-cover-letter.md
```

The legacy extraction command remains available:

```powershell
python main.py extract --resume resume.pdf --jd job-description.txt --out analysis.json
```

## Pipeline

```mermaid
flowchart LR
    I[Resume PDF + JD] --> X[Scout v0 extraction]
    X --> S[Typed ResumeSchema + JobDescriptionSchema]
    S --> R[Researcher\nweb_search only]
    R --> B[CompanyBrief]
    B --> W[Writer\ncover-letter Skill, no tools]
    S --> W
    W --> E[Editor\ngrammar_check only]
    E -->|revisions, max 2 cycles| W
    E -->|approved| O[Cover letter + token spend]
```

The supervisor owns routing and has an explicit `done` exit. Agent boundaries carry
Pydantic objects (`CompanyBrief`, `Revision`) rather than free-text research notes.

## Sample run

**Input:** A mid-level candidate with four years of Python, FastAPI, PostgreSQL, and
Docker experience applies to Northstar Health's backend role. The source-backed company
brief says it is simplifying care coordination and expanding clinician workflow tools.

**Output:**

> Dear Hiring Team,
>
> My four years of experience with Python, FastAPI, and PostgreSQL align directly with
> the backend requirements for Northstar Health. These technologies map to the role's
> Python, API design, and relational-database requirements.
>
> Northstar Health's focus on simplifying care coordination for clinics, alongside its
> clinician-facing workflow tools, gives that match a concrete context. My Python,
> FastAPI, PostgreSQL, and Docker background can support the backend work behind those
> services.
>
> I would welcome the opportunity to discuss how that experience could contribute to
> your backend team. Thank you for your consideration.

## Evaluation

[`evals/cover_letter/cases.json`](evals/cover_letter/cases.json) contains five varied
profile/JD/company-brief cases with quality checklists. The Skill is also runnable outside
Scout through `claude-skills/cover-letter/run_standalone.py`, making its standalone and
agent outputs directly comparable.
