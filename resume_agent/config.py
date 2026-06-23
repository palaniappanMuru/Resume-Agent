import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")
    llm_model: str = os.getenv("LLM_MODEL", "claude-sonnet-4-6")

    # JD extraction and CV construction can each use a different LLM. Both fall back to the
    # generic LLM_PROVIDER/LLM_MODEL above when unset, so existing single-LLM setups keep working.
    jd_llm_provider: str = os.getenv("JD_LLM_PROVIDER", os.getenv("LLM_PROVIDER", "anthropic"))
    jd_llm_model: str = os.getenv("JD_LLM_MODEL", os.getenv("LLM_MODEL", "claude-sonnet-4-6"))
    cv_llm_provider: str = os.getenv("CV_LLM_PROVIDER", os.getenv("LLM_PROVIDER", "anthropic"))
    cv_llm_model: str = os.getenv("CV_LLM_MODEL", os.getenv("LLM_MODEL", "claude-sonnet-4-6"))

    # Resume generation is skipped unless the ATS score reaches this threshold (0-100).
    ats_min_score_threshold: float = float(os.getenv("ATS_MIN_SCORE_THRESHOLD", "60"))

    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j"))
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")
    neo4j_database: str = os.getenv("NEO4J_DATABASE", os.getenv("NEO4J_DATABASE", "neo4j"))

    candidate_name: str = os.getenv("CANDIDATE_NAME", "")
    candidate_email: str = os.getenv("CANDIDATE_EMAIL", "")
    candidate_phone: str = os.getenv("CANDIDATE_PHONE", "")
    candidate_location: str = os.getenv("CANDIDATE_LOCATION", "")
    candidate_linkedin: str = os.getenv("CANDIDATE_LINKEDIN", "")

    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # Skill-name normalization threshold (JD skill phrase -> canonical graph Skill node)
    skill_match_threshold: float = 0.75
    # Below this similarity, a JD requirement is considered a gap
    gap_similarity_threshold: float = 0.5
    # JobRole name reuse threshold (draft role name -> existing JobRole node), higher than
    # skill matching since distinct roles can be semantically close (e.g. "DevOps Manager"
    # vs "Senior DevOps Manager") and should not be merged together.
    role_match_threshold: float = 0.85

    # ATS overall score weights (must sum to 1.0)
    weight_keyword_match: float = 0.40
    weight_semantic_similarity: float = 0.35
    weight_experience_depth: float = 0.25

    output_dir: str = os.getenv("OUTPUT_DIR", "output")


settings = Settings()
