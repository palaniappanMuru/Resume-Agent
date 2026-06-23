ALL_SKILL_NAMES = """
MATCH (s:Skill)
RETURN DISTINCT s.name AS name
"""

CONTEXT_FOR_SKILLS = """
MATCH (c:Candidate)-[:HAS_SKILL]->(s:Skill)
WHERE s.name IN $skills
OPTIONAL MATCH (c)-[:ACHIEVED]->(a:Accomplishment)-[:USING]->(s)
OPTIONAL MATCH (a)-[:GAINED_IN]->(p:Project)
OPTIONAL MATCH (s)-[:LEARNED_IN]->(course:Course)
RETURN
    s.name AS skill,
    collect(DISTINCT p.name) AS projects,
    collect(DISTINCT coalesce(a.text, a.description)) AS accomplishments,
    collect(DISTINCT course.name) AS courses
"""

# Full candidate project list, independent of JD-matched skills, used to populate the
# resume's Experience section (a candidate's worked-on projects are not all reached via
# Accomplishment->USING->Skill, since WORKED_ON has no skill linkage in the schema).
#
# Accomplishment text lives on the `text` property (the graph-admin-ui manages it under
# that name); `description` is read as a fallback for nodes created before that rename.
ALL_PROJECTS_WITH_ACCOMPLISHMENTS = """
MATCH (c:Candidate)-[:WORKED_ON]->(p:Project)
OPTIONAL MATCH (c)-[:ACHIEVED]->(a:Accomplishment)-[:GAINED_IN]->(p)
RETURN p.name AS project, p.description AS description, collect(DISTINCT coalesce(a.text, a.description)) AS accomplishments
"""

# --- Graph write-back: missing skills + JobRole nodes (Task 2.3/2.2 follow-up) ---

ALL_JOB_ROLE_NAMES = """
MATCH (jr:JobRole)
RETURN DISTINCT jr.name AS name
"""

MERGE_JOB_ROLE = """
MERGE (jr:JobRole {name_key: $name_key})
ON CREATE SET jr.name = $name
RETURN jr.name AS name
"""

# Upserts a Skill node and sets is_missing explicitly ("yes"/"no") so a skill's status
# self-heals across runs instead of only ever being marked missing once.
MERGE_SKILL_WITH_MISSING_FLAG = """
MERGE (s:Skill {name: $name})
SET s.is_missing = $is_missing
RETURN s.name AS name
"""

LINK_JOB_ROLE_REQUIRES_SKILL = """
MATCH (jr:JobRole {name_key: $role_key})
MATCH (s:Skill {name: $skill_name})
MERGE (jr)-[:REQUIRED]->(s)
"""
