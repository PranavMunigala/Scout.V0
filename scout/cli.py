"""CLI interface for Scout v0."""

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from scout.core import extract_resume, extract_jd, analyze_gaps
from scout.logger import setup_logger
from scout.schemas import ResumeSchema, JobDescriptionSchema, GapAnalysisSchema

app = typer.Typer(
    name="scout",
    help="Scout v0 - Extract and analyze resumes against job descriptions.",
)
logger = setup_logger(__name__)


@app.command()
def extract(
    resume: str = typer.Option(
        ...,
        "--resume",
        help="Path to the resume PDF file.",
        exists=True,
    ),
    jd: str = typer.Option(
        ...,
        "--jd",
        help="Path to the job description text file.",
        exists=True,
    ),
    out: str = typer.Option(
        "scout_output.json",
        "--out",
        help="Path to save the output JSON file.",
    ),
) -> None:
    """
    Extract resume and JD data, perform gap analysis, and save combined results.

    This command:
    1. Extracts structured data from the resume PDF
    2. Extracts structured data from the job description
    3. Analyzes gaps between resume and JD must-haves
    4. Saves all results to a JSON file
    """
    try:
        typer.echo("🔍 Extracting resume data...", err=False)
        resume_data = extract_resume(resume)
        typer.echo("✓ Resume extracted successfully", err=False)

        typer.echo("🔍 Extracting job description data...", err=False)
        with open(jd, "r", encoding="utf-8") as f:
            jd_text = f.read()
        jd_data = extract_jd(jd_text)
        typer.echo("✓ Job description extracted successfully", err=False)

        typer.echo("🔍 Performing gap analysis...", err=False)
        gap_data = analyze_gaps(resume_data, jd_data)
        typer.echo("✓ Gap analysis completed successfully", err=False)

        # Combine all data into a single output
        output = {
            "resume": resume_data.model_dump(),
            "job_description": jd_data.model_dump(),
            "gap_analysis": gap_data.model_dump()["gap_analysis"],
        }

        # Save to JSON file
        output_path = Path(out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        typer.echo(f"✅ Results saved to {output_path}", err=False)
        typer.echo(f"\nSummary:")
        typer.echo(f"  Resume Skills: {len(resume_data.skills)}")
        typer.echo(f"  Seniority: {resume_data.seniority_level}")
        typer.echo(f"  Experience: {resume_data.years_of_experience} years")
        typer.echo(f"  Must-Haves: {len(jd_data.must_haves)}")
        typer.echo(f"  Years Required: {jd_data.years_required}")

        # Calculate gap percentage
        gaps_found = sum(
            1 for item in gap_data.gap_analysis if not item.evidence_in_resume
        )
        gap_percentage = (
            (gaps_found / len(gap_data.gap_analysis) * 100)
            if gap_data.gap_analysis
            else 0
        )
        typer.echo(f"  Gap Percentage: {gap_percentage:.1f}%")

    except FileNotFoundError as e:
        typer.echo(f"❌ File error: {e}", err=True)
        logger.error(f"File not found: {e}")
        sys.exit(1)

    except ValueError as e:
        typer.echo(f"❌ Validation error: {e}", err=True)
        logger.error(f"Validation error: {e}")
        sys.exit(1)

    except Exception as e:
        typer.echo(f"❌ Unexpected error: {e}", err=True)
        logger.error(f"Unexpected error during extraction: {e}")
        sys.exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    from scout import __version__

    typer.echo(f"Scout v{__version__}")


if __name__ == "__main__":
    app()
