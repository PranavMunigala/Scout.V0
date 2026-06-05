"""Scout v0 - Resume and Job Description Gap Analysis Tool"""

from scout.core import extract_resume, extract_jd, analyze_gaps
from scout.schemas import ResumeSchema, JobDescriptionSchema, GapAnalysisSchema

__version__ = "0.1.0"
__all__ = [
    "extract_resume",
    "extract_jd",
    "analyze_gaps",
    "ResumeSchema",
    "JobDescriptionSchema",
    "GapAnalysisSchema",
]
