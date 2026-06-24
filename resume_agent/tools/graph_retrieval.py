from resume_agent.config import settings
from resume_agent.embeddings import best_matches
from resume_agent.graph.cypher_templates import (
    ALL_PROJECTS_WITH_ACCOMPLISHMENTS,
    ALL_SKILL_NAMES,
    CONTEXT_FOR_SKILLS,
)
from resume_agent.graph.neo4j_client import Neo4jClient
from resume_agent.schemas import (
    AccomplishmentInfo,
    CourseInfo,
    GraphContext,
    JDRequirements,
    MatchedSkill,
    ProjectInfo,
)


def _to_str(value) -> str:
    """Coerce a collected graph value to a single string.

    Some Project/Accomplishment nodes store multi-valued properties (e.g. several
    historical title variants) as a list instead of a string; collapse those so
    schema validation doesn't choke on a list where a str is expected.
    """
    if isinstance(value, list):
        return "; ".join(str(v) for v in value if v)
    return str(value)


def _normalize_skills(jd_skills: list[str], graph_skill_names: list[str]) -> tuple[dict[str, tuple[str, float]], list[str]]:
    """Map each JD skill phrase to its best-matching canonical graph Skill name.

    Returns (jd_skill -> (graph_skill, similarity), unmatched_jd_skills).
    """
    matches: dict[str, tuple[str, float]] = {}
    unmatched: list[str] = []
    for jd_skill, (graph_skill, sim) in zip(jd_skills, best_matches(jd_skills, graph_skill_names)):
        if graph_skill is not None and sim >= settings.skill_match_threshold:
            matches[jd_skill] = (graph_skill, sim)
        else:
            unmatched.append(jd_skill)
    return matches, unmatched


def retrieve_graph_context(jd: JDRequirements, client: Neo4jClient) -> GraphContext:
    """Convert extracted JD entities into Cypher query parameters and retrieve matching
    Skills, Projects, Accomplishments, and Courses from the graph.

    Task 2.2: Neo4j Cypher Generation & Retrieval Tool.
    """
    graph_skill_names = [row["name"] for row in client.run_query(ALL_SKILL_NAMES)]

    candidate_jd_skills = jd.hard_skills + jd.soft_skills
    skill_map, unmatched = _normalize_skills(candidate_jd_skills, graph_skill_names)
    canonical_skills = sorted({graph_skill for graph_skill, _ in skill_map.values()})

    rows = client.run_query(CONTEXT_FOR_SKILLS, {"skills": canonical_skills}) if canonical_skills else []
    rows_by_skill = {row["skill"]: row for row in rows}

    matched_skills: list[MatchedSkill] = []
    for jd_skill, (graph_skill, sim) in skill_map.items():
        row = rows_by_skill.get(graph_skill, {})
        matched_skills.append(
            MatchedSkill(
                jd_skill=jd_skill,
                graph_skill=graph_skill,
                similarity=sim,
                projects=[_to_str(p) for p in row.get("projects", []) if p],
                accomplishments=[_to_str(a) for a in row.get("accomplishments", []) if a],
                courses=[_to_str(c) for c in row.get("courses", []) if c],
            )
        )

    project_rows = client.run_query(ALL_PROJECTS_WITH_ACCOMPLISHMENTS)
    projects = [
        ProjectInfo(
            name=_to_str(row["project"]),
            description=_to_str(row["description"]) if row.get("description") else None,
            accomplishments=[_to_str(a) for a in row.get("accomplishments", []) if a],
        )
        for row in project_rows
    ]

    accomplishments = [
        AccomplishmentInfo(description=desc, skill=ms.graph_skill, project=proj)
        for ms in matched_skills
        for desc in ms.accomplishments
        for proj in (ms.projects or [None])
    ]

    courses = [
        CourseInfo(name=course, skill=ms.graph_skill)
        for ms in matched_skills
        for course in ms.courses
    ]

    return GraphContext(
        matched_skills=matched_skills,
        unmatched_jd_skills=unmatched,
        projects=projects,
        accomplishments=accomplishments,
        courses=courses,
    )
