from pathlib import Path

from resume_agent.schemas import JDRequirements
from resume_agent.tools.jd_parser import parse_jd

FIXTURE = Path(__file__).parent / "fixtures" / "sample_jd.txt"

EXPECTED = JDRequirements(
    job_title="Senior Data Engineer",
    seniority_level="Senior",
    hard_skills=["Python", "SQL", "Apache Kafka", "Airflow", "AWS"],
    soft_skills=["communication", "stakeholder management"],
    domain_experience=["fintech", "real-time fraud detection"],
    key_responsibilities=[
        "Design and build scalable ETL pipelines",
        "Collaborate with data science teams on model deployment",
        "Mentor junior engineers",
    ],
    min_years_experience=5,
)


class FakeStructuredLLM:
    def __init__(self, result: JDRequirements):
        self._result = result
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return self._result


class FakeChatModel:
    def __init__(self, result: JDRequirements):
        self._structured = FakeStructuredLLM(result)

    def with_structured_output(self, schema):
        assert schema is JDRequirements
        return self._structured


def test_parse_jd_reads_file_and_returns_structured_output():
    llm = FakeChatModel(EXPECTED)
    result = parse_jd(FIXTURE, llm)
    assert result == EXPECTED
    # the raw JD text should have been forwarded to the LLM
    human_message = llm._structured.last_messages[-1]
    assert "Senior Data Engineer" in human_message.content


def test_parse_jd_accepts_raw_text_string():
    llm = FakeChatModel(EXPECTED)
    result = parse_jd("Senior Data Engineer JD text...", llm)
    assert result == EXPECTED
