from resume_agent.graph.cypher_templates import ALL_SKILL_NAMES, CONTEXT_FOR_SKILLS
from resume_agent.schemas import JDRequirements
from resume_agent.tools import graph_retrieval


class FakeNeo4jClient:
    def __init__(self, skill_names, context_rows):
        self._skill_names = skill_names
        self._context_rows = context_rows
        self.queries = []

    def run_query(self, cypher, params=None):
        self.queries.append((cypher, params))
        if cypher == ALL_SKILL_NAMES:
            return [{"name": n} for n in self._skill_names]
        if cypher == CONTEXT_FOR_SKILLS:
            requested = set(params["skills"])
            return [row for row in self._context_rows if row["skill"] in requested]
        return []


def test_retrieve_graph_context_matches_skills_and_collects_evidence(monkeypatch):
    jd = JDRequirements(
        job_title="Data Engineer",
        hard_skills=["Python", "Kubernetes"],
        soft_skills=[],
        domain_experience=[],
        key_responsibilities=[],
    )

    # Deterministic fake similarity: "Python" matches "Python" at 0.95, "Kubernetes" has no match.
    def fake_best_matches(queries, candidates):
        return [
            ("Python", 0.95) if query == "Python" and "Python" in candidates else (None, 0.0)
            for query in queries
        ]

    monkeypatch.setattr(graph_retrieval, "best_matches", fake_best_matches)

    client = FakeNeo4jClient(
        skill_names=["Python", "Java"],
        context_rows=[
            {
                "skill": "Python",
                "projects": ["Fraud Detection Platform"],
                "accomplishments": ["Built real-time ETL pipeline"],
                "courses": ["Advanced Python"],
            }
        ],
    )

    ctx = graph_retrieval.retrieve_graph_context(jd, client)

    assert len(ctx.matched_skills) == 1
    matched = ctx.matched_skills[0]
    assert matched.jd_skill == "Python"
    assert matched.graph_skill == "Python"
    assert matched.projects == ["Fraud Detection Platform"]
    assert matched.accomplishments == ["Built real-time ETL pipeline"]
    assert matched.courses == ["Advanced Python"]

    assert ctx.unmatched_jd_skills == ["Kubernetes"]
