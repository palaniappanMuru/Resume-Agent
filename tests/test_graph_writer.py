from resume_agent.graph.cypher_templates import (
    ALL_JOB_ROLE_NAMES,
    LINK_JOB_ROLE_REQUIRES_SKILL,
    MERGE_JOB_ROLE,
    MERGE_SKILL_WITH_MISSING_FLAG,
)
from resume_agent.schemas import GraphContext, JDRequirements, MatchedSkill
from resume_agent.tools import graph_writer


class FakeNeo4jClient:
    def __init__(self, existing_job_roles=None):
        self.existing_job_roles = existing_job_roles or []
        self.merged_skills = []
        self.merged_roles = []
        self.linked = []

    def run_query(self, cypher, params=None):
        if cypher == ALL_JOB_ROLE_NAMES:
            return [{"name": n} for n in self.existing_job_roles]
        if cypher == MERGE_SKILL_WITH_MISSING_FLAG:
            self.merged_skills.append((params["name"], params["is_missing"]))
            return [{"name": params["name"]}]
        if cypher == MERGE_JOB_ROLE:
            self.merged_roles.append(params["name"])
            return [{"name": params["name"]}]
        if cypher == LINK_JOB_ROLE_REQUIRES_SKILL:
            self.linked.append((params["role_key"], params["skill_name"]))
            return []
        return []


def test_sync_job_role_and_skills_marks_missing_and_links_required(monkeypatch):
    jd = JDRequirements(
        job_title="DevOps Manager",
        hard_skills=["Python", "Kubernetes"],
        soft_skills=["communication"],
    )
    graph_ctx = GraphContext(
        matched_skills=[
            MatchedSkill(jd_skill="Python", graph_skill="Python", similarity=0.95)
        ],
        unmatched_jd_skills=["Kubernetes", "communication"],
    )

    monkeypatch.setattr(graph_writer, "best_match", lambda query, candidates: (None, 0.0))

    client = FakeNeo4jClient()
    role_name = graph_writer.sync_job_role_and_skills(jd, graph_ctx, client)

    assert role_name == "DevOps Manager"
    assert ("Python", "no") in client.merged_skills
    assert ("Kubernetes", "yes") in client.merged_skills
    assert ("communication", "yes") in client.merged_skills
    assert client.merged_roles == ["DevOps Manager"]
    assert ("devops manager", "Python") in client.linked
    assert ("devops manager", "Kubernetes") in client.linked
    assert ("devops manager", "communication") in client.linked


def test_sync_job_role_and_skills_reuses_existing_similar_role(monkeypatch):
    jd = JDRequirements(job_title="Senior DevOps Manager", hard_skills=[], soft_skills=[])
    graph_ctx = GraphContext()

    monkeypatch.setattr(graph_writer, "best_match", lambda query, candidates: ("DevOps Manager", 0.9))

    client = FakeNeo4jClient(existing_job_roles=["DevOps Manager"])
    role_name = graph_writer.sync_job_role_and_skills(jd, graph_ctx, client)

    assert role_name == "DevOps Manager"
    assert client.merged_roles == ["DevOps Manager"]
