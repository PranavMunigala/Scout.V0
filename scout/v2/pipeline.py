"""Bounded, cost-accounted LangGraph cover-letter pipeline for Scout v2."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field, model_validator

from scout.schemas import (
    CompanyBrief,
    JobDescriptionSchema,
    ResumeSchema,
    Revision,
    RunTokenSpend,
    TokenUsage,
)
from scout.v2.tools import grammar_check, web_search

logger = logging.getLogger(__name__)
DEFAULT_TOKEN_BUDGET = 50_000
MAX_REVISION_CYCLES = 2
DEFAULT_SKILL_PATH = Path(__file__).resolve().parents[3] / "claude-skills" / "cover-letter" / "SKILL.md"


class EditorDecision(BaseModel):
    """Structured result returned from the Editor to the supervisor."""

    approved: bool
    revisions: list[Revision] = Field(default_factory=list)

    @model_validator(mode="after")
    def decision_is_actionable(self) -> "EditorDecision":
        if not self.approved and not self.revisions:
            raise ValueError("A rejected draft must include at least one Revision.")
        if self.approved and self.revisions:
            raise ValueError("An approved draft cannot include revisions.")
        return self


class TokenBudgetExceeded(RuntimeError):
    """Raised once actual Claude usage exhausts the configured run budget."""

    def __init__(self, spend: RunTokenSpend):
        self.spend = spend
        super().__init__(
            f"Scout v2 token budget exceeded: {spend.total_tokens}/{spend.budget_tokens} tokens"
        )


class UsageTracker:
    """Collect actual provider usage across the subgraphs for one synchronous run."""

    def __init__(self, budget_tokens: int):
        self._spend = RunTokenSpend(budget_tokens=budget_tokens)

    @property
    def spend(self) -> RunTokenSpend:
        return self._spend.model_copy(deep=True)

    def record(self, agent: str, response: object) -> None:
        metadata = getattr(response, "usage_metadata", None) or getattr(
            response, "response_metadata", {}
        ).get("usage", {})
        input_tokens = int(metadata.get("input_tokens", 0) or 0)
        output_tokens = int(metadata.get("output_tokens", 0) or 0)
        total_tokens = int(metadata.get("total_tokens", input_tokens + output_tokens) or 0)
        usage = self._spend.by_agent.setdefault(agent, TokenUsage())
        usage.input_tokens += input_tokens
        usage.output_tokens += output_tokens
        usage.total_tokens += total_tokens
        self._spend.total_tokens += total_tokens
        if self._spend.total_tokens > self._spend.budget_tokens:
            raise TokenBudgetExceeded(self.spend)


class PipelineState(TypedDict, total=False):
    resume: ResumeSchema
    job_description: JobDescriptionSchema
    company_name: str
    company_brief: CompanyBrief
    draft: str
    revisions: list[Revision]
    approved: bool
    draft_version: int
    editor_reviewed_version: int
    revision_cycles: int
    completed_reason: Literal["approved", "revision_cap"]
    next: Literal["researcher", "writer", "editor", "done"]
    token_spend: RunTokenSpend


class ResearchState(TypedDict, total=False):
    company_name: str
    messages: Annotated[list, add_messages]
    company_brief: CompanyBrief


class WriterState(TypedDict, total=False):
    resume: ResumeSchema
    job_description: JobDescriptionSchema
    company_brief: CompanyBrief
    revisions: list[Revision]
    draft: str
    draft_version: int
    revision_cycles: int


class EditorState(TypedDict, total=False):
    draft: str
    draft_version: int
    messages: Annotated[list, add_messages]
    approved: bool
    revisions: list[Revision]
    editor_reviewed_version: int


def _content(message: object) -> str:
    content = getattr(message, "content", message)
    return content if isinstance(content, str) else str(content)


def _budget_from_env() -> int:
    value = int(os.getenv("SCOUT_V2_TOKEN_BUDGET", str(DEFAULT_TOKEN_BUDGET)))
    if value <= 0:
        raise ValueError("SCOUT_V2_TOKEN_BUDGET must be a positive integer.")
    return value


def _model() -> ChatAnthropic:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY environment variable not set for Scout v2.")
    return ChatAnthropic(
        model=os.getenv("SCOUT_V2_MODEL", "claude-sonnet-5"),
        temperature=0,
        max_tokens=4096,
    )


def load_cover_letter_skill() -> str:
    """Load the portable cover-letter Skill; it is the Writer's only drafting logic."""
    skill_path = Path(os.getenv("SCOUT_COVER_LETTER_SKILL", DEFAULT_SKILL_PATH))
    try:
        return skill_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"Cover-letter Skill was not found at {skill_path}. "
            "Set SCOUT_COVER_LETTER_SKILL to cover-letter/SKILL.md."
        ) from exc


def _invoke(model: Any, payload: object, tracker: UsageTracker, agent: str) -> object:
    response = model.invoke(payload)
    tracker.record(agent, response)
    return response


def _invoke_structured(
    model: Any, schema: type[BaseModel], prompt: str, tracker: UsageTracker, agent: str
) -> BaseModel:
    result = model.with_structured_output(schema, include_raw=True).invoke(prompt)
    if isinstance(result, dict):
        raw, parsed = result.get("raw"), result.get("parsed")
        if raw is not None:
            tracker.record(agent, raw)
        if parsed is None:
            raise ValueError(f"{agent} returned an invalid structured response: {result.get('parsing_error')}")
        return parsed
    # Compatibility fallback for model wrappers that return the parsed Pydantic value directly.
    return result


def build_researcher_subgraph(model: ChatAnthropic, tracker: UsageTracker):
    """Researcher has exactly one externally callable tool: web_search."""
    researcher = model.bind_tools([web_search])

    def research(state: ResearchState):
        messages = state.get("messages") or [HumanMessage(content=(
            "Research this company for a cover letter: " + state["company_name"] + ". "
            "Use web_search before answering. Find only source-backed mission, recent news, and hiring signals."
        ))]
        return {"messages": [_invoke(researcher, messages, tracker, "researcher")]}

    def summarize(state: ResearchState):
        prompt = (
            "Create a CompanyBrief from the following research tool transcript. "
            "Do not invent facts. Put supporting URLs in sources; use empty lists when evidence is absent. "
            f"Company: {state['company_name']}\nTranscript: {state.get('messages', [])}"
        )
        return {"company_brief": _invoke_structured(model, CompanyBrief, prompt, tracker, "researcher")}

    graph = StateGraph(ResearchState)
    graph.add_node("research", research)
    graph.add_node("web_search", ToolNode([web_search]))
    graph.add_node("summarize", summarize)
    graph.add_edge(START, "research")
    graph.add_conditional_edges("research", tools_condition, {"tools": "web_search", END: "summarize"})
    graph.add_edge("web_search", "research")
    graph.add_edge("summarize", END)
    return graph.compile()


def build_writer_subgraph(model: ChatAnthropic, tracker: UsageTracker):
    """Writer receives typed context and has no tool binding."""
    def write(state: WriterState):
        revision_context = [revision.model_dump() for revision in state.get("revisions", [])]
        skill = load_cover_letter_skill()
        prompt = "\n\n".join(
            [
                skill,
                "## Runtime inputs",
                f"Resume: {state['resume'].model_dump_json()}",
                f"Job description: {state['job_description'].model_dump_json()}",
                f"Company brief: {state['company_brief'].model_dump_json()}",
                f"Revisions: {revision_context}",
            ]
        )
        return {
            "draft": _content(_invoke(model, prompt, tracker, "writer")),
            "draft_version": state.get("draft_version", 0) + 1,
            "revision_cycles": state.get("revision_cycles", 0) + (1 if state.get("draft") else 0),
        }

    graph = StateGraph(WriterState)
    graph.add_node("write", write)
    graph.add_edge(START, "write")
    graph.add_edge("write", END)
    return graph.compile()


def build_editor_subgraph(model: ChatAnthropic, tracker: UsageTracker):
    """Editor is tool-scoped to grammar_check and emits a typed approval decision."""
    checker = model.bind_tools([grammar_check], tool_choice="grammar_check")

    def request_check(state: EditorState):
        message = HumanMessage(content=(
            "Review this cover letter for grammar and mechanics. Call grammar_check with the complete draft.\n\n"
            + state["draft"]
        ))
        return {"messages": [_invoke(checker, [message], tracker, "editor")]}

    def decide(state: EditorState):
        prompt = f"""You are the final grammar editor for this cover letter.
Use the grammar_check transcript below. Approve only if there are no grammar or mechanical issues.
If changes are needed, return precise Revision objects with real line numbers and actionable suggestions.

Draft:\n{state['draft']}

grammar_check transcript:\n{state.get('messages', [])}
"""
        decision = _invoke_structured(model, EditorDecision, prompt, tracker, "editor")
        return {
            "approved": decision.approved,
            "revisions": decision.revisions,
            "editor_reviewed_version": state["draft_version"],
        }

    graph = StateGraph(EditorState)
    graph.add_node("request_check", request_check)
    graph.add_node("grammar_check", ToolNode([grammar_check]))
    graph.add_node("decide", decide)
    graph.add_edge(START, "request_check")
    graph.add_edge("request_check", "grammar_check")
    graph.add_edge("grammar_check", "decide")
    graph.add_edge("decide", END)
    return graph.compile()


def supervisor_node(state: PipelineState, tracker: UsageTracker) -> dict:
    """Route deterministically and terminate on approval or the two-revision limit."""
    if "company_brief" not in state:
        return {"next": "researcher"}
    if "draft" not in state:
        return {"next": "writer"}
    if state.get("editor_reviewed_version", 0) < state.get("draft_version", 0):
        return {"next": "editor"}
    if state.get("approved"):
        return {"next": "done", "completed_reason": "approved", "token_spend": tracker.spend}
    if state.get("revision_cycles", 0) >= MAX_REVISION_CYCLES:
        return {"next": "done", "completed_reason": "revision_cap", "token_spend": tracker.spend}
    return {"next": "writer"}


def _route(state: PipelineState) -> str:
    return state["next"]


def build_cover_letter_graph(model: ChatAnthropic | None = None, *, budget_tokens: int | None = None):
    """Build Day 2's bounded supervisor workflow with per-run spend tracking."""
    model = model or _model()
    tracker = UsageTracker(budget_tokens if budget_tokens is not None else _budget_from_env())
    graph = StateGraph(PipelineState)
    graph.add_node("supervisor", lambda state: supervisor_node(state, tracker))
    graph.add_node("researcher", build_researcher_subgraph(model, tracker))
    graph.add_node("writer", build_writer_subgraph(model, tracker))
    graph.add_node("editor", build_editor_subgraph(model, tracker))
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
    """Run the Day 2 pipeline and log actual Claude token spend."""
    result = build_cover_letter_graph().invoke({
        "resume": resume,
        "job_description": job_description,
        "company_name": company_name,
        "revision_cycles": 0,
        "draft_version": 0,
        "editor_reviewed_version": 0,
    })
    spend = result["token_spend"]
    logger.info("Scout v2 token spend: %s/%s tokens by agent=%s", spend.total_tokens, spend.budget_tokens, spend.by_agent)
    return result
