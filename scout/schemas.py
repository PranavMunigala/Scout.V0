"""Pydantic schemas for Scout v0 - strict prompt engineering definitions."""

from typing import List, Literal
from pydantic import BaseModel, Field


class ResumeSchema(BaseModel):
    """Extracted resume data with careful prompt engineering."""

    skills: List[str] = Field(
        ...,
        description=(
            "Extract a comprehensive list of all technical and soft skills explicitly mentioned "
            "or strongly evidenced in the resume. Include programming languages, frameworks, tools, "
            "methodologies, and interpersonal skills. Be specific; avoid generic terms. "
            "Example: ['Python', 'FastAPI', 'PostgreSQL', 'Docker', 'AWS', 'Team Leadership'] not ['Technical Skills']."
        ),
    )

    seniority_level: Literal["junior", "mid", "senior"] = Field(
        ...,
        description=(
            "Determine the professional seniority level based on: job titles, years of experience, "
            "scope of responsibilities, and technical depth. "
            "'junior': 0-2 years, entry-level roles, learning-focused. "
            "'mid': 2-7 years, intermediate responsibilities, some leadership. "
            "'senior': 7+ years, leadership, architectural decisions, mentorship roles. "
            "Base judgment on context, not just years; a 5-year senior engineer may be 'mid' if in a junior role."
        ),
    )

    years_of_experience: float = Field(
        ...,
        description=(
            "Calculate total professional experience in years as a decimal. "
            "Sum all employment periods; if overlapping, count only once. "
            "Include only full-time work and substantial part-time (6+ months) roles. "
            "If no dates provided, infer conservatively from job count and titles. "
            "Return as a float (e.g., 5.5 for 5 years 6 months)."
        ),
    )


class JobDescriptionSchema(BaseModel):
    """Extracted job description requirements."""

    must_haves: List[str] = Field(
        ...,
        description=(
            "Extract only hard requirements explicitly stated as mandatory, required, or essential. "
            "Include skills, certifications, experience levels, and constraints marked as 'must have', "
            "'required', 'minimum', or in phrases like 'you must', 'required', 'essential'. "
            "Do NOT include implied requirements or nice-to-haves. "
            "Example: ['5+ years Python', 'AWS certification', 'Bachelor in CS'] not ['Strong communication']."
        ),
    )

    nice_to_haves: List[str] = Field(
        ...,
        description=(
            "Extract optional, preferred, or bonus qualifications. "
            "These are marked as 'nice to have', 'preferred', 'bonus', 'a plus', 'ideally', 'preferred'. "
            "Include nice-to-haves only; do NOT duplicate must-haves. "
            "Example: ['Kubernetes experience', 'Published research', 'Remote work availability']."
        ),
    )

    years_required: int = Field(
        ...,
        description=(
            "Extract the minimum required years of experience as an integer. "
            "If a range like '3-5 years' is given, take the lower bound (3). "
            "If none specified, default to 0. "
            "If stated as 'entry-level' or 'fresh graduate', use 0. "
            "Return only the integer value (e.g., 5 not '5 years')."
        ),
    )


class GapAnalysisItem(BaseModel):
    """Individual gap analysis result."""

    skill_or_requirement: str = Field(
        ...,
        description="The specific must-have requirement from the job description.",
    )

    evidence_in_resume: bool = Field(
        ...,
        description=(
            "True if the requirement is clearly found in the resume with strong evidence. "
            "False if missing, weakly evidenced, or absent. "
            "Use a high threshold for True; be conservative and require explicit mention or very strong context."
        ),
    )

    notes: str = Field(
        ...,
        description=(
            "If evidence_in_resume is True: provide the exact contextual proof from the resume (quote or paraphrase). "
            "If evidence_in_resume is False: explain what is missing or why the evidence is insufficient. "
            "Be concise but specific (1-2 sentences)."
        ),
    )


class GapAnalysisSchema(BaseModel):
    """Complete gap analysis between resume and job description."""

    gap_analysis: List[GapAnalysisItem] = Field(
        ...,
        description=(
            "A list of gap analysis items, one for each must-have requirement from the job description. "
            "Analyze the resume against ONLY the must-haves; do NOT analyze nice-to-haves. "
            "Each item must have skill_or_requirement, evidence_in_resume (bool), and notes (explanation)."
        ),
    )
