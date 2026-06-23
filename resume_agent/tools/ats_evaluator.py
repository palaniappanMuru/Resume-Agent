from resume_agent.config import settings
from resume_agent.embeddings import best_match
from resume_agent.schemas import ATSReport, GraphContext, JDRequirements, ScoreBreakdown

# Evidence text pool that semantic similarity is matched against: project/accomplishment
# descriptions are the candidate's actual demonstrated experience.
def _evidence_texts(graph_ctx: GraphContext) -> list[str]:
    texts: list[str] = []
    for p in graph_ctx.projects:
        if p.description:
            texts.append(p.description)
        texts.extend(p.accomplishments)
    for a in graph_ctx.accomplishments:
        texts.append(a.description)
    return [t for t in texts if t]


def _keyword_match_score(jd: JDRequirements, graph_ctx: GraphContext) -> float:
    required = jd.hard_skills + jd.soft_skills
    if not required:
        return 1.0
    matched_jd_skills = {ms.jd_skill for ms in graph_ctx.matched_skills}
    return len(matched_jd_skills) / len(required)


def _semantic_similarity_score(jd: JDRequirements, evidence: list[str]) -> tuple[float, dict[str, float]]:
    items = jd.domain_experience + jd.key_responsibilities
    if not items:
        return 1.0, {}
    per_item_sim: dict[str, float] = {}
    for item in items:
        _, sim = best_match(item, evidence)
        per_item_sim[item] = sim
    avg = sum(per_item_sim.values()) / len(per_item_sim)
    return avg, per_item_sim


def _experience_depth_score(graph_ctx: GraphContext) -> float:
    if not graph_ctx.matched_skills:
        return 0.0
    depths = [
        min(1.0, (len(ms.projects) + len(ms.accomplishments)) / 3)
        for ms in graph_ctx.matched_skills
    ]
    return sum(depths) / len(depths)


def evaluate_ats(jd: JDRequirements, graph_ctx: GraphContext) -> ATSReport:
    """Compare parsed JD requirements against retrieved graph context, score the match,
    and surface any missing qualifications (honesty guardrail).

    Task 2.3: ATS Evaluation & Gap Analysis Tool.
    """
    evidence = _evidence_texts(graph_ctx)

    keyword_score = _keyword_match_score(jd, graph_ctx)
    semantic_score, _domain_resp_sims = _semantic_similarity_score(jd, evidence)
    depth_score = _experience_depth_score(graph_ctx)

    overall = 100 * (
        settings.weight_keyword_match * keyword_score
        + settings.weight_semantic_similarity * semantic_score
        + settings.weight_experience_depth * depth_score
    )

    score = ScoreBreakdown(
        keyword_match_score=round(keyword_score, 3),
        semantic_similarity_score=round(semantic_score, 3),
        experience_depth_score=round(depth_score, 3),
        overall_ats_score=round(overall, 1),
    )

    matched_jd_skills = {ms.jd_skill for ms in graph_ctx.matched_skills}
    gaps: list[str] = [
        skill for skill in jd.hard_skills + jd.soft_skills if skill not in matched_jd_skills
    ]

    matched_items = sorted(matched_jd_skills)

    return ATSReport(score=score, gaps=gaps, matched_items=matched_items)
