"""Day 1 LangGraph supervisor and scoped worker subgraphs for Scout v2."""

from __future__ import annotations

import os
from typing import Annotated, Literal, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from scout.schemas import CompanyBrief, JobDescriptionSchema, ResumeSchema, Revision
from scout.v2.tools import web_search


class PipelineState(TypedDict, total=False):
    """Parent state. Inter-worker context is always typed, never a research text blob."""

    resume: ResumeSchema
    job_description: JobDescriptionSchema
    company_name: str
    company_brief: CompanyBrief
    draft: str
    approved: bool
    revisions: list[Revision]
    next: Literal["researcher", "writer", "editor", "done"]


class ResearchState(TypedDict, total=False):
    company_name: str
    messages: Annotated[list, add_messages]
    company_brief: CompanyBrief


class WriterState(TypedDict, total=False):
    resume: ResumeSchema
    job_description: JobDescriptionSchema
    company_brief: CompanyBrief
    draft: str


class EditorState(TypedDict, total=False):
    draft: str
    approved: bool
    revisions: list[Revision]


def _content(message: object) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    return str(content)


def _model() -> ChatAnthropic:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY environment variable not set for Scout v2.")
    return ChatAnthropic(model=os.getenv("SCOUT_V2_MODEL", "claude-sonnet-4-20250514"), temperature=0)


def build_researcher_subgraph(model: ChatAnthropic):
    """Researcher has exactly one tool: web_search."""
    researcher = model.bind_tools([web_search])

    def research(state: ResearchState):
        messages = state.get("messages") or [HumanMessage(content=(
            "Research this company for a cover letter: " + state["company_name"] + ". "
            "Use web_search before answering. Find only source-backed mission, recent news, and hiring signals."
        ))]
        return {"messages": [researcher.invoke(messages)]}

    def summarize(state: ResearchState):
        brief_model = model.with_structured_output(CompanyBrief)
        prompt = (
            "Create a CompanyBrief from the following research tool transcript. "
            "Do not invent facts. Put supporting URLs in sources; use empty lists when evidence is absent. "
            f"Company: {state['company_name']}\nTranscript: {state.get('messages', [])}"
        )
        return {"company_brief": brief_model.invoke(prompt)}

    graph = StateGraph(ResearchState)
    graph.add_node("research", research)
    graph.add_node("web_search", ToolNode([web_search]))
    graph.add_node("summarize", summarize)
    graph.add_edge(START, "research")
    graph.add_conditional_edges("research", tools_condition, {"tools": "web_search", END: "summarize"})
    graph.add_edge("web_search", "research")
    graph.add_edge("summarize", END)
    return graph.compile()


def build_writer_subgraph(model: ChatAnthropic):
    """Writer receives structured context and deliberately has no tools."""
    def write(state: WriterState):
        prompt = f"""Draft a concise, tailored cover letter using only these structured inputs.
Never claim experience or company facts not represented below. If the company brief is sparse,
keep company references general rather than inventing details.

Resume: {state['resume'].model_dump_json()}
Job description: {state['job_description'].model_dump_json()}
Company brief: {state['company_brief'].model_dump_json()}
"""
        return {"draft": _content(model.invoke(prompt))}

    graph = StateGraph(WriterState)
    graph.add_node("write", write)
    graph.add_edge(START, "write")
    graph.add_edge("write", END)
    return graph.compile()


def build_editor_subgraph():
    """Day 1 stub: the real grammar-checking Editor is intentionally a Day 2 task."""
    def approve(_: EditorState):
        return {"approved": True, "revisions": []}

    graph = StateGraph(EditorState)
    graph.add_node("approve", approve)
    graph.add_edge(START, "approve")
    graph.add_edge("approve", END)
    return graph.compile()


def supervisor_node(state: PipelineState) -> dict:
    """Deterministic Day 1 supervisor routing through the three worker subgraphs."""
    if "company_brief" not in state:
        return {"next": "researcher"}
    if "draft" not in state:
        return {"next": "writer"}
    if "approved" not in state:
        return {"next": "editor"}
    return {"next": "done"}


def _route(state: PipelineState) -> str:
    return state["next"]


def build_cover_letter_graph(model: ChatAnthropic | None = None):
    """Assemble the Day 1 supervisor with Researcher -> Writer -> stub Editor -> END."""
    model = model or _model()
    graph = StateGraph(PipelineState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("researcher", build_researcher_subgraph(model))
    graph.add_node("writer", build_writer_subgraph(model))
    graph.add_node("editor", build_editor_subgraph())
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", _route, {
        "researcher": "researcher", "writer": "writer", "editor": "editor", "done": END,
    })
    graph.add_edge("researcher", "supervisor")
    graph.add_edge("writer", "supervisor")
    graph.add_edge("editor", "supervisor")
    return graph.compile()


def run_cover_letter(
    resume: ResumeSchema, job_description: JobDescriptionSchema, company_name: str
) -> PipelineState:
    """Run the Day 1 end-to-end pipeline and return its typed final state."""
    return build_cover_letter_graph().invoke({
        "resume": resume,
        "job_description": job_description,
        "company_name": company_name,
    })
