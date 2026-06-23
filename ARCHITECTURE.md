# Architecture Summary — AI Resume Tailoring Platform

This document summarizes the system design for anyone (including future-you) explaining
this project externally: what it does, how it's built, and the engineering decisions
behind it.

## 1. What it does

A platform that takes a raw job description and a candidate's career history (stored as
a knowledge graph) and produces a tailored, ATS-scored resume — with a human-friendly
admin tool to curate the underlying career data.

It is two independent systems sharing one database:

```
┌─────────────────────────┐         ┌──────────────────────────┐
│   resume_agent (Python)  │         │   graph-admin-ui (Next.js)│
│   LangGraph pipeline      │         │   Human data-curation UI │
│                          │         │                          │
│  JD → parse → retrieve   │         │  Skills / Accomplishments │
│  → score → (gate) →      │         │  / Courses / Job Roles /  │
│  generate resume          │         │  Projects — CRUD + links │
└────────────┬─────────────┘         └─────────────┬────────────┘
             │                                       │
             └──────────────┬────────────────────────┘
                             ▼
                     ┌───────────────┐
                     │     Neo4j     │
                     │  (graph DB)   │
                     └───────────────┘
```

**Why two systems, not one:** the pipeline is an automated, LLM-driven batch process;
the admin UI is a manual, human-in-the-loop data tool. They have different audiences,
different deployment lifecycles, and different risk profiles (an LLM agent shouldn't
need write access patterns built for a human clicking buttons, and vice versa). Keeping
them in separate codebases means either can be deleted, redeployed, or rewritten without
touching the other — the only shared contract is the Neo4j schema.

## 2. System 1: `resume_agent` — the generation pipeline

**Stack:** Python, LangGraph (orchestration), LangChain (LLM abstraction), Anthropic /
OpenAI (pluggable LLM providers), Neo4j (graph DB), sentence-transformers (embeddings for
semantic matching), python-docx / pypdf (document I/O), pytest (testing).

**Why LangGraph specifically:** the job naturally decomposes into a directed pipeline
with a conditional branch (generate the resume only if it clears a quality bar) — exactly
what a graph-based orchestrator is for, versus a more general agent framework where
control flow would have to be reimplemented by hand. It also makes the pipeline's shape
inspectable and testable stage-by-stage.

**Pipeline stages** (`resume_agent/pipeline.py`):

1. **Parse JD** — LLM extracts structured requirements (hard skills, soft skills, domain
   experience, responsibilities, seniority) from raw job description text/PDF.
2. **Retrieve graph context** — matches JD requirements against the candidate's graph
   using embedding similarity (handles paraphrased skill names, not just exact string
   match), pulling in supporting projects/accomplishments/courses as evidence.
3. **Sync graph** — writes back missing-skill flags and deduplicates/creates the JobRole
   node (fuzzy-matched by embedding similarity so "DevOps Manager" and "Senior DevOps
   Manager" don't fragment into duplicate roles).
4. **Evaluate ATS** — scores the match (keyword match 40% / semantic similarity 35% /
   experience depth 25%) and produces a gap list (missing skills only).
5. **Conditional gate** — only proceeds to generation if the score clears a
   configurable threshold (default 60/100); otherwise the pipeline stops and returns the
   score + gap report so the user knows why.
6. **Generate resume** — a second, independently-configurable LLM writes the tailored
   resume content, grounded strictly in the retrieved evidence (explicit anti-hallucination
   instruction: it may rephrase, not invent).

**Two independently configurable LLMs** — JD extraction and resume writing are different
tasks with different ideal models/cost profiles, so the provider/model for each is set
separately via env vars (`JD_LLM_PROVIDER`/`JD_LLM_MODEL` vs `CV_LLM_PROVIDER`/
`CV_LLM_MODEL`), both falling back to a shared default if unset. Either can be swapped
(Anthropic ↔ OpenAI, or model version) with zero code changes.

**Output:** structured JSON (ATS score breakdown, gap list, match/generation status) +
a formatted `.docx` resume, written to disk.

## 3. System 2: `graph-admin-ui` — the data curation tool

**Stack:** Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, the official
`neo4j-driver` (no ORM) — chosen specifically to be free to run (local or Vercel's free
tier) for a single user, with no separate backend service to maintain.

**What it's for:** the pipeline can only tailor a resume from what's already in the
graph — this is the tool to keep that data accurate: add accomplishments, tag them with
the skills/projects they demonstrate, manage the skill taxonomy (category, type,
seniority level, years of experience, last used), and curate reference data (courses,
job roles, projects).

**Notable engineering choices:**

- **Server Actions architecture** — every mutation is a real Next.js Server Action
  (`"use server"`), invoked via `<form action={...}>`. No client-side cache layer to keep
  in sync; every successful write calls `revalidatePath` and the UI re-fetches fresh
  truth from Neo4j. Validation errors come back as typed state (`useActionState`) and
  surface as inline messages or toasts rather than crashing the page.
- **Schema-on-read, not schema-on-write** — Skill nodes stay property-flexible in Neo4j
  (any key/value allowed), but the UI gives a known set of keys (`category`, `type`,
  `level`, `years_experience`, `last_used`) dedicated inputs/badges/filters, while
  anything else still surfaces as a free-form editable field. This avoids a migration
  every time someone wants to track a new attribute.
- **Soft delete everywhere** — Skills, Courses, Job Roles, and Projects use a `deleted`
  flag instead of removing graph nodes, so curation mistakes are always reversible. A
  `created_at` timestamp on new Skills means newly added entries surface at the top of
  the list by default, not buried in alphabetical or empty-property sort order.
- **Data-integrity validation** — Skill names are enforced unique (case-insensitive) on
  both create and rename, server-side, with friendly toast feedback instead of a raw
  exception.
- **Embedding protection** — any property matching `/embed/i` (the vector embeddings
  used elsewhere for semantic matching) is stripped before data ever reaches the browser,
  and the update path uses targeted `SET +=` / `REMOVE` instead of a full-node overwrite,
  so an embedding can never be accidentally clobbered through this UI even though the UI
  never displays or edits it.
- **`/manage` page** — simple, consistent create/rename/soft-delete CRUD for Courses,
  Job Roles, and Projects, reusing the same visual language as the main dashboard.

## 4. Shared data model (Neo4j)

```
(Candidate)-[:HAS_SKILL]->(Skill)
(Candidate)-[:WORKED_ON]->(Project)
(Candidate)-[:ACHIEVED]->(Accomplishment)
(Accomplishment)-[:USING]->(Skill)
(Accomplishment)-[:GAINED_IN]->(Project)
(Skill)-[:LEARNED_IN]->(Course)
(JobRole)-[:REQUIRED]->(Skill)
```

This is the one contract both systems agree on. Notably, the `Accomplishment.text`
property (renamed from `description` mid-project) is read by both systems via
`coalesce(text, description)` — a deliberate backward-compatible migration pattern so a
property rename never silently drops historical data.

## 5. Why this is worth presenting as "architected and led"

Talking points, concretely:

- **Decoupled-by-design system boundary** — two independently deployable applications
  in different languages/stacks, integrated only through a shared graph schema, not
  shared code. This is a real architectural choice with a real tradeoff (some
  duplication of "create a Skill" logic) made deliberately to keep blast radius small.
- **Graph-based orchestration for the AI pipeline** — not just "call an LLM," but a
  multi-stage pipeline with retrieval grounding (RAG via the candidate's own graph,
  embedding-matched), a scoring/gating stage, and a second LLM call constrained by
  explicit anti-hallucination instructions.
- **Configurability as a first-class concern** — LLM provider/model selection, ATS
  threshold, scoring weights are all environment-driven, not hardcoded, so the system
  can be retuned or re-pointed at a different model without a code change or redeploy.
- **Production-minded details that aren't "just a prototype"**: soft delete, name
  uniqueness validation, backward-compatible property migration, protection of sensitive
  derived data (embeddings) from accidental UI mutation, graceful degradation when the
  database is unreachable (the dashboard shows a clear disconnected state instead of
  crashing).
- **Test coverage on the pipeline's core logic** (JD parsing, graph retrieval, ATS
  scoring, document generation) using fakes/mocks for the LLM and embedding layers, so
  the scoring math and graph queries are verified independent of any live model or
  database.
