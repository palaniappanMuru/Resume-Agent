from pydantic import BaseModel, Field


class JDRequirements(BaseModel):
    job_title: str
    seniority_level: str | None = None
    hard_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    domain_experience: list[str] = Field(default_factory=list)
    key_responsibilities: list[str] = Field(default_factory=list)
    min_years_experience: float | None = None


class MatchedSkill(BaseModel):
    jd_skill: str
    graph_skill: str
    similarity: float
    projects: list[str] = Field(default_factory=list)
    accomplishments: list[str] = Field(default_factory=list)
    courses: list[str] = Field(default_factory=list)


class ProjectInfo(BaseModel):
    name: str
    description: str | None = None
    accomplishments: list[str] = Field(default_factory=list)


class AccomplishmentInfo(BaseModel):
    description: str
    skill: str | None = None
    project: str | None = None


class CourseInfo(BaseModel):
    name: str
    skill: str | None = None


class GraphContext(BaseModel):
    matched_skills: list[MatchedSkill] = Field(default_factory=list)
    unmatched_jd_skills: list[str] = Field(default_factory=list)
    projects: list[ProjectInfo] = Field(default_factory=list)
    accomplishments: list[AccomplishmentInfo] = Field(default_factory=list)
    courses: list[CourseInfo] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    keyword_match_score: float
    semantic_similarity_score: float
    experience_depth_score: float
    overall_ats_score: float


class ATSReport(BaseModel):
    score: ScoreBreakdown
    gaps: list[str] = Field(default_factory=list)
    matched_items: list[str] = Field(default_factory=list)


class JDMatchStatus(BaseModel):
    matched: bool
    ats_score: float
    threshold: float
    resume_generated: bool


class ExperienceEntry(BaseModel):
    project: str
    bullets: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    course: str
    related_skill: str | None = None


class ResumeContent(BaseModel):
    """LLM-authored resume content, grounded only in the evidence provided in the prompt."""

    summary: str
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)


class TailoredResume(BaseModel):
    candidate_name: str
    contact: dict[str, str] = Field(default_factory=dict)
    job_title: str
    summary: str
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    ats_report: ATSReport
    jd_match_status: JDMatchStatus
