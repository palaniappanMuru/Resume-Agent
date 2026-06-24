from resume_agent.schemas import (
    AccomplishmentInfo,
    GraphContext,
    JDRequirements,
    MatchedSkill,
    ProjectInfo,
)
from resume_agent.tools import ats_evaluator


def fake_best_match_factory(sim_for_domain_experience):
    def fake_best_matches(queries, candidates):
        return [
            ((candidates[0] if candidates else None), sim_for_domain_experience.get(query, 0.9))
            for query in queries
        ]

    return fake_best_matches


def test_evaluate_ats_scores_matches_and_flags_missing_skills(monkeypatch):
    jd = JDRequirements(
        job_title="Senior Data Engineer",
        hard_skills=["Python", "Kafka"],
        soft_skills=["communication"],
        domain_experience=["fintech"],
        key_responsibilities=["Build ETL pipelines"],
    )

    graph_ctx = GraphContext(
        matched_skills=[
            MatchedSkill(
                jd_skill="Python",
                graph_skill="Python",
                similarity=0.95,
                projects=["Fraud Detection Platform"],
                accomplishments=["Built real-time ETL pipeline"],
                courses=[],
            )
        ],
        unmatched_jd_skills=["Kafka", "communication"],
        projects=[
            ProjectInfo(
                name="Fraud Detection Platform",
                description="Real-time fraud detection in fintech",
                accomplishments=["Built real-time ETL pipeline"],
            )
        ],
        accomplishments=[AccomplishmentInfo(description="Built real-time ETL pipeline", skill="Python")],
        courses=[],
    )

    monkeypatch.setattr(
        ats_evaluator,
        "best_matches",
        fake_best_match_factory({"fintech": 0.8, "Build ETL pipelines": 0.7}),
    )

    report = ats_evaluator.evaluate_ats(jd, graph_ctx)

    assert report.score.keyword_match_score == round(1 / 3, 3)
    assert 0 <= report.score.overall_ats_score <= 100
    assert report.matched_items == ["Python"]

    assert set(report.gaps) == {"Kafka", "communication"}
    assert "fintech" not in report.gaps  # domain_experience is not a skill gap


def test_evaluate_ats_with_no_requirements_scores_perfectly(monkeypatch):
    jd = JDRequirements(job_title="Anything")
    graph_ctx = GraphContext()

    monkeypatch.setattr(ats_evaluator, "best_matches", fake_best_match_factory({}))

    report = ats_evaluator.evaluate_ats(jd, graph_ctx)

    assert report.score.keyword_match_score == 1.0
    assert report.score.semantic_similarity_score == 1.0
    assert report.gaps == []
