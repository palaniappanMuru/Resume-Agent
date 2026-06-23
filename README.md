# Resume Agent

Turns a raw Job Description into a tailored, ATS-scored resume sourced from a Neo4j graph of your
career data (Skills, Projects, Accomplishments, Courses).

## Pipeline

1. **JD Parser** (`resume_agent/tools/jd_parser.py`) — LLM + structured Pydantic output extracts
   hard skills, soft skills, domain experience, and responsibilities from a JD text/PDF.
2. **Neo4j Retrieval** (`resume_agent/tools/graph_retrieval.py`) — normalizes JD skill phrasing
   against canonical graph `Skill` names via embeddings, then runs parameterized Cypher to fetch
   matching Projects, Accomplishments, and Courses.
3. **Graph Write-Back** (`resume_agent/tools/graph_writer.py`) — persists this JD's requirements
   into Neo4j on every run: every required hard/soft skill becomes/updates a `Skill` node with an
   `is_missing` ("yes"/"no") flag that self-heals across runs (a skill marked missing is cleared
   once it later matches), and a deduplicated `JobRole` node is linked to every required skill via
   a `REQUIRED` relationship (`job_title` is canonicalized by the LLM and reused via embedding
   similarity against existing `JobRole` names so repeated postings for the same role don't create
   duplicates).
4. **ATS Evaluation & Gap Analysis** (`resume_agent/tools/ats_evaluator.py`) — scores keyword match,
   semantic similarity, and experience depth into a 0-100 ATS score, and always lists any missing
   qualifications (honesty guardrail).
5. **Document Generation** (`resume_agent/tools/doc_generator.py`) — compiles the result into a
   JSON file and an ATS-friendly `.docx`.

`resume_agent/pipeline.py` wires all of these into a deterministic LangGraph pipeline: parse → retrieve
→ sync (write-back) → evaluate → generate.

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv\Scripts\activate.bat for cmd.exe
pip install -r requirements.txt
cp .env.example .env   # fill in Neo4j + LLM credentials + candidate contact info
```

## Run

```bash
python -m resume_agent.cli run --jd path/to/job_description.pdf
```

Outputs land in `output/<job_title>_resume.json` and `output/<job_title>_resume.docx`.

## Tests

```bash
pip install pytest numpy
pytest tests/ -q
```

Unit tests mock the LLM, Neo4j client, and embedding similarity — no live API keys, database, or
the `sentence-transformers` model download are required to run them.
