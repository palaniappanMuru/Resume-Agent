from resume_agent.config import settings
from resume_agent.embeddings import best_match
from resume_agent.graph.cypher_templates import (
    ALL_JOB_ROLE_NAMES,
    LINK_JOB_ROLE_REQUIRES_SKILL,
    MERGE_JOB_ROLE,
    MERGE_SKILL_WITH_MISSING_FLAG,
)
from resume_agent.graph.neo4j_client import Neo4jClient
from resume_agent.schemas import GraphContext, JDRequirements


def _resolve_job_role_name(draft_name: str, client: Neo4jClient) -> str:
    """Reuse an existing JobRole node if it's a close semantic match to the LLM-drafted
    name (e.g. "Senior DevOps Engineer" JD run twice shouldn't create two nodes); otherwise
    register the draft name as a new role.
    """
    existing = [row["name"] for row in client.run_query(ALL_JOB_ROLE_NAMES)]
    match, sim = best_match(draft_name, existing)
    return match if match and sim >= settings.role_match_threshold else draft_name


def sync_job_role_and_skills(jd: JDRequirements, graph_ctx: GraphContext, client: Neo4jClient) -> str:
    """Persist this JD's requirements back to the graph:
    - every required hard/soft skill becomes a Skill node, flagged is_missing "yes"/"no"
      depending on whether it matched the candidate's existing skills (self-healing: a skill
      previously marked missing is cleared back to "no" once it matches in a later run).
    - a JobRole node (deduped against existing roles) is linked to every required skill via
      a REQUIRED relationship, with new skills appended to an existing role if seen again.

    Returns the resolved (possibly reused) JobRole name.
    """
    matched_graph_skill_by_jd_skill = {ms.jd_skill: ms.graph_skill for ms in graph_ctx.matched_skills}
    required_jd_skills = jd.hard_skills + jd.soft_skills

    skill_node_names: list[str] = []
    for jd_skill in required_jd_skills:
        if jd_skill in matched_graph_skill_by_jd_skill:
            name = matched_graph_skill_by_jd_skill[jd_skill]
            is_missing = "no"
        else:
            name = jd_skill
            is_missing = "yes"
        client.run_query(MERGE_SKILL_WITH_MISSING_FLAG, {"name": name, "is_missing": is_missing})
        skill_node_names.append(name)

    role_name = _resolve_job_role_name(jd.job_title, client)
    role_key = role_name.strip().lower()
    client.run_query(MERGE_JOB_ROLE, {"name_key": role_key, "name": role_name})

    for skill_name in skill_node_names:
        client.run_query(LINK_JOB_ROLE_REQUIRES_SKILL, {"role_key": role_key, "skill_name": skill_name})

    return role_name
