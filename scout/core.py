"""Core extraction and analysis functions for Scout v0."""

import os
from typing import Optional

from pypdf import PdfReader
import google.generativeai as genai
import instructor
from pydantic import ValidationError

from scout.logger import setup_logger
from scout.schemas import ResumeSchema, JobDescriptionSchema, GapAnalysisSchema

logger = setup_logger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"


def _initialize_client():
    """Initialize Instructor-wrapped Google GenAI client."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")

    genai.configure(api_key=api_key)
    # Use instructor to wrap the Gemini client for structured outputs
    client = instructor.from_gemini(genai.GenerativeModel(GEMINI_MODEL))
    return client


def extract_resume(pdf_path: str) -> ResumeSchema:
    """
    Extract structured resume data from a PDF file.

    Args:
        pdf_path: Path to the resume PDF file.

    Returns:
        ResumeSchema containing skills, seniority_level, and years_of_experience.

    Raises:
        FileNotFoundError: If PDF file does not exist.
        ValidationError: If LLM response fails validation.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Resume PDF not found: {pdf_path}")

    try:
        # Extract text from PDF
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()

        if not text.strip():
            logger.warning(f"No text extracted from resume PDF: {pdf_path}")
            raise ValueError("Resume PDF is empty or unreadable.")

        # Initialize client and extract data
        client = _initialize_client()

        resume = client.messages.create(
            response_model=ResumeSchema,
            messages=[
                {
                    "role": "user",
                    "content": f"""Analyze the following resume and extract structured data.

Resume:
{text}

Extract:
1. All technical and soft skills explicitly mentioned or strongly evidenced.
2. Seniority level (junior/mid/senior) based on titles, experience, and scope.
3. Total years of professional experience as a decimal.

Be precise and conservative; do not hallucinate skills or experience not evidenced in the resume.""",
                }
            ],
        )

        logger.info(f"Successfully extracted resume from {pdf_path}")
        return resume

    except ValidationError as e:
        logger.error(f"Resume extraction validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error extracting resume from {pdf_path}: {e}")
        raise


def extract_jd(jd_text: str) -> JobDescriptionSchema:
    """
    Extract structured job description data from raw text.

    Args:
        jd_text: Raw job description text.

    Returns:
        JobDescriptionSchema containing must_haves, nice_to_haves, and years_required.

    Raises:
        ValidationError: If LLM response fails validation.
    """
    if not jd_text.strip():
        raise ValueError("Job description text is empty.")

    try:
        client = _initialize_client()

        jd = client.messages.create(
            response_model=JobDescriptionSchema,
            messages=[
                {
                    "role": "user",
                    "content": f"""Analyze the following job description and extract structured data.

Job Description:
{jd_text}

Extract:
1. Must-have requirements (hard requirements, explicitly stated as required/essential/mandatory).
2. Nice-to-have requirements (optional, preferred, bonus qualifications).
3. Minimum years of experience (if range, take lower bound; if none, default to 0).

Be precise:
- Only include explicit requirements in must-haves.
- Do not duplicate must-haves in nice-to-haves.
- For years_required, return only the integer (e.g., 5 not '5 years').""",
                }
            ],
        )

        logger.info("Successfully extracted job description")
        return jd

    except ValidationError as e:
        logger.error(f"Job description extraction validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error extracting job description: {e}")
        raise


def analyze_gaps(resume: ResumeSchema, jd: JobDescriptionSchema) -> GapAnalysisSchema:
    """
    Perform gap analysis: check if resume meets job description must-haves.

    Args:
        resume: Extracted ResumeSchema data.
        jd: Extracted JobDescriptionSchema data.

    Returns:
        GapAnalysisSchema containing analysis of each must-have requirement.

    Raises:
        ValidationError: If LLM response fails validation.
    """
    try:
        client = _initialize_client()

        # Build context for gap analysis
        resume_text = f"""
Resume Summary:
- Skills: {', '.join(resume.skills)}
- Seniority Level: {resume.seniority_level}
- Years of Experience: {resume.years_of_experience}
"""

        jd_text = f"""
Job Requirements:
Must-Haves: {', '.join(jd.must_haves)}
Years Required: {jd.years_required}
"""

        gap_analysis = client.messages.create(
            response_model=GapAnalysisSchema,
            messages=[
                {
                    "role": "user",
                    "content": f"""Perform a gap analysis between a resume and job description must-haves.

{resume_text}

{jd_text}

For EACH must-have requirement, determine:
1. If it's clearly evidenced in the resume (True/False).
2. Provide evidence (quote from resume if True) or explanation of missing requirement (if False).

Be conservative: require explicit mention or very strong context for True.
Analyze ONLY must-haves; ignore nice-to-haves.
Return a list where each item has:
- skill_or_requirement: The must-have item
- evidence_in_resume: True/False
- notes: Contextual proof or explanation""",
                }
            ],
        )

        logger.info("Successfully completed gap analysis")
        return gap_analysis

    except ValidationError as e:
        logger.error(f"Gap analysis validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error performing gap analysis: {e}")
        raise
