"""CLI interface for Scout v0 and the Day 1 Scout v2 pipeline."""

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from scout.core import analyze_gaps, extract_jd, extract_resume
from scout.logger import setup_logger

app = typer.Typer(name="scout", help="Scout - resume and job-description tools.")
logger = setup_logger(__name__)


@app.command()
def extract(
    resume: str = typer.Option(..., "--resume", help="Path to the resume PDF file.", exists=True),
    jd: str = typer.Option(..., "--jd", help="Path to the job description text file.", exists=True),
    out: str = typer.Option("scout_output.json", "--out", help="Path to save the output JSON file."),
) -> None:
    """Run the unchanged Scout v0 extraction and gap-analysis flow."""
    try:
        resume_data = extract_resume(resume)
        jd_data = extract_jd(Path(jd).read_text(encoding="utf-8"))
        gap_data = analyze_gaps(resume_data, jd_data)
        output = {
            "resume": resume_data.model_dump(),
            "job_description": jd_data.model_dump(),
            "gap_analysis": gap_data.model_dump()["gap_analysis"],
        }
        Path(out).write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        typer.echo(f"Results saved to {out}")
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"Validation error: {exc}", err=True)
        logger.error("Extraction failed: %s", exc)
        raise typer.Exit(code=1)
    except Exception as exc:
        typer.echo(f"Unexpected error: {exc}", err=True)
        logger.error("Unexpected extraction error: %s", exc)
        raise typer.Exit(code=1)


@app.command("cover-letter")
def cover_letter(
    resume: str = typer.Option(..., "--resume", help="Path to the resume PDF file.", exists=True),
    jd: str = typer.Option(..., "--jd", help="Path to the job description text file.", exists=True),
    company: str = typer.Option(..., "--company", help="Target company name for the Researcher."),
    out: Optional[str] = typer.Option(None, "--out", help="Optional path to save the cover letter."),
) -> None:
    """Run the bounded Day 2 Researcher -> Writer -> Editor workflow."""
    try:
        from scout.v2.pipeline import TokenBudgetExceeded, run_cover_letter

        resume_data = extract_resume(resume)
        jd_data = extract_jd(Path(jd).read_text(encoding="utf-8"))
        result = run_cover_letter(resume_data, jd_data, company)
        letter = result["draft"]
        if out:
            Path(out).write_text(letter, encoding="utf-8")
            typer.echo(f"Cover letter saved to {out}")
        else:
            typer.echo(letter)
        spend = result["token_spend"]
        typer.echo(
            f"Token usage: {spend.total_tokens}/{spend.budget_tokens} "
            f"(completion: {result['completed_reason']})",
            err=True,
        )
    except TokenBudgetExceeded as exc:
        spend = exc.spend
        typer.echo(
            f"Token usage: {spend.total_tokens}/{spend.budget_tokens} (budget exceeded)",
            err=True,
        )
        raise typer.Exit(code=1)
    except Exception as exc:
        typer.echo(f"Cover-letter pipeline failed: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Show version information."""
    from scout import __version__

    typer.echo(f"Scout v{__version__}")


if __name__ == "__main__":
    app()
