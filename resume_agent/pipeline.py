from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph

from resume_agent.config import settings
from resume_agent.graph.neo4j_client import Neo4jClient
from resume_agent.llm import get_chat_model
from resume_agent.schemas import ATSReport, GraphContext, JDMatchStatus, JDRequirements, TailoredResume
from resume_agent.tools.ats_evaluator import evaluate_ats
from resume_agent.tools.doc_generator import build_resume, generate_documents
from resume_agent.tools.graph_retrieval import retrieve_graph_context
from resume_agent.tools.graph_writer import sync_job_role_and_skills
from resume_agent.tools.jd_parser import parse_jd


class PipelineState(TypedDict, total=False):
    jd_source: str
    jd_requirements: JDRequirements
    graph_context: GraphContext
    job_role_name: str
    ats_report: ATSReport
    jd_match_status: JDMatchStatus
    resume: TailoredResume
    json_path: str
    docx_path: str


def _parse_jd_node(state: PipelineState) -> PipelineState:
    llm = get_chat_model(settings.jd_llm_provider, settings.jd_llm_model)
    jd = parse_jd(state["jd_source"], llm)
    return {"jd_requirements": jd}


def _retrieve_graph_node(state: PipelineState) -> PipelineState:
    with Neo4jClient() as client:
        ctx = retrieve_graph_context(state["jd_requirements"], client)
    return {"graph_context": ctx}


def _sync_graph_node(state: PipelineState) -> PipelineState:
    with Neo4jClient() as client:
        role_name = sync_job_role_and_skills(state["jd_requirements"], state["graph_context"], client)
    return {"job_role_name": role_name}


def _evaluate_ats_node(state: PipelineState) -> PipelineState:
    report = evaluate_ats(state["jd_requirements"], state["graph_context"])
    threshold = settings.ats_min_score_threshold
    matched = report.score.overall_ats_score >= threshold
    match_status = JDMatchStatus(
        matched=matched,
        ats_score=report.score.overall_ats_score,
        threshold=threshold,
        # Resume generation is gated solely on this match, so the two stay in lockstep.
        resume_generated=matched,
    )
    return {"ats_report": report, "jd_match_status": match_status}


def _route_after_ats(state: PipelineState) -> str:
    return "generate_docs" if state["jd_match_status"].matched else END


def _generate_docs_node(state: PipelineState) -> PipelineState:
    llm = get_chat_model(settings.cv_llm_provider, settings.cv_llm_model)
    resume = build_resume(
        state["jd_requirements"],
        state["graph_context"],
        state["ats_report"],
        state["jd_match_status"],
        llm,
        job_role_name=state.get("job_role_name"),
    )
    json_path, docx_path = generate_documents(resume)
    return {"resume": resume, "json_path": str(json_path), "docx_path": str(docx_path)}


def build_pipeline():
    graph = StateGraph(PipelineState)
    graph.add_node("parse_jd", _parse_jd_node)
    graph.add_node("retrieve_graph", _retrieve_graph_node)
    graph.add_node("sync_graph", _sync_graph_node)
    graph.add_node("evaluate_ats", _evaluate_ats_node)
    graph.add_node("generate_docs", _generate_docs_node)

    graph.set_entry_point("parse_jd")
    graph.add_edge("parse_jd", "retrieve_graph")
    graph.add_edge("retrieve_graph", "sync_graph")
    graph.add_edge("sync_graph", "evaluate_ats")
    graph.add_conditional_edges("evaluate_ats", _route_after_ats, {"generate_docs": "generate_docs", END: END})
    graph.add_edge("generate_docs", END)

    return graph.compile()


def run_pipeline(jd_source: str | Path) -> PipelineState:
    app = build_pipeline()
    return app.invoke({"jd_source": str(jd_source)})
