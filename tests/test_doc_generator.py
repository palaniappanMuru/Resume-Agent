import json

from docx import Document

from resume_agent.schemas import (
    ATSReport,
    CourseInfo,
    EducationEntry,
    ExperienceEntry,
    GraphContext,
    JDMatchStatus,
    JDRequirements,
    MatchedSkill,
    ProjectInfo,
    ResumeContent,
    ScoreBreakdown,
)
from resume_agent.tools.doc_generator import build_resume, generate_documents


class FakeStructuredLLM:
    def __init__(self, result: ResumeContent):
        self._result = result
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return self._result


class FakeChatModel:
    def __init__(self, result: ResumeContent):
        self._structured = FakeStructuredLLM(result)

    def with_structured_output(self, schema):
        assert schema is ResumeContent
        return self._structured


def _sample_inputs():
    jd = JDRequirements(job_title="Senior Data Engineer", seniority_level="Senior")
    graph_ctx = GraphContext(
        matched_skills=[
            MatchedSkill(jd_skill="Python", graph_skill="Python", similarity=0.95)
        ],
        projects=[
            ProjectInfo(
                name="Fraud Detection Platform",
                description="Real-time fraud detection",
                accomplishments=["Built real-time ETL pipeline"],
            )
        ],
        courses=[CourseInfo(name="Advanced Python", skill="Python")],
    )
    ats_report = ATSReport(
        score=ScoreBreakdown(
            keyword_match_score=1.0,
            semantic_similarity_score=1.0,
            experience_depth_score=1.0,
            overall_ats_score=100.0,
        )
    )
    match_status = JDMatchStatus(matched=True, ats_score=100.0, threshold=60.0, resume_generated=True)
    llm = FakeChatModel(
        ResumeContent(
            summary="Senior data professional targeting the Senior Data Engineer role.",
            skills=["Python"],
            experience=[
                ExperienceEntry(project="Fraud Detection Platform", bullets=["Built real-time ETL pipeline"])
            ],
            education=[EducationEntry(course="Advanced Python", related_skill="Python")],
        )
    )
    return jd, graph_ctx, ats_report, match_status, llm


def test_build_resume_compiles_expected_sections():
    jd, graph_ctx, ats_report, match_status, llm = _sample_inputs()
    resume = build_resume(jd, graph_ctx, ats_report, match_status, llm)

    assert resume.job_title == "Senior Data Engineer"
    assert resume.skills == ["Python"]
    assert resume.experience[0].project == "Fraud Detection Platform"
    assert resume.experience[0].bullets == ["Built real-time ETL pipeline"]
    assert resume.education[0].course == "Advanced Python"
    assert resume.jd_match_status.matched is True


def test_generate_documents_writes_json_and_docx(tmp_path):
    jd, graph_ctx, ats_report, match_status, llm = _sample_inputs()
    resume = build_resume(jd, graph_ctx, ats_report, match_status, llm)

    json_path, docx_path = generate_documents(resume, output_dir=tmp_path)

    assert json_path.exists()
    assert docx_path.exists()

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["job_title"] == "Senior Data Engineer"
    assert data["ats_report"]["score"]["overall_ats_score"] == 100.0

    doc = Document(str(docx_path))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Fraud Detection Platform" in full_text
    assert "Built real-time ETL pipeline" in full_text
