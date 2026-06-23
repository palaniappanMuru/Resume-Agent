import re
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from resume_agent.schemas import JDRequirements

SYSTEM_PROMPT = """You are an expert technical recruiter. Extract structured requirements from the \
job description below. Rules:
- job_title: a concise, canonical role category title, not the verbatim posting title \
(e.g. "Senior Backend Eng II, Payments Risk" -> "Backend Development Manager"; "Site Reliability \
& DevOps Lead" -> "DevOps Manager"). This name is reused to deduplicate the same role across \
multiple job postings, so prefer a short, standard, widely-recognized title \
(e.g. "Operations Manager", "DevOps Manager", "Backend Development Manager", \
"Agentic AI Solution Architect") over an overly specific or company-internal one.
- hard_skills: concrete tools, technologies, languages, platforms, certifications (e.g. "Python", \
"AWS", "PMP certification"). Do not include soft skills here.
- soft_skills: interpersonal/behavioral traits (e.g. "communication", "stakeholder management").
- domain_experience: industry/business-domain phrases (e.g. "fintech", "healthcare claims processing").
- key_responsibilities: short bullet phrases describing what the role actually does day to day.
- min_years_experience: a number if the JD states a minimum years requirement, else null.
- seniority_level: e.g. "Junior", "Mid", "Senior", "Lead" if inferable, else null.
Only use information present in the JD. Do not invent skills or responsibilities."""


def _extract_pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _load_text(source: str | Path) -> str:
    path = Path(source) if isinstance(source, (str, Path)) and Path(source).exists() else None
    if path is None:
        return str(source)
    if path.suffix.lower() == ".pdf":
        return _extract_pdf_text(path)
    return path.read_text(encoding="utf-8")


def _clean(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_jd(source: str | Path, llm: BaseChatModel) -> JDRequirements:
    """Parse a raw Job Description (text or PDF path) into structured requirements.

    Task 2.1: JD Parser Tool.
    """
    raw_text = _clean(_load_text(source))
    structured_llm = llm.with_structured_output(JDRequirements)
    result = structured_llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Job Description:\n\n{raw_text}"),
        ]
    )
    return result
