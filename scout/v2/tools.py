"""Tool definitions for the narrowly scoped Scout v2 workers."""

from __future__ import annotations

import json
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from langchain_core.tools import tool


@tool
def web_search(query: str) -> str:
    """Search the public web for current company facts; return concise source snippets."""
    query = query.strip()
    if not query:
        return "No query supplied."

    # The DuckDuckGo instant-answer endpoint keeps this Day 1 tool dependency-free.
    # Its raw results stay within the Researcher subgraph and never cross to Writer.
    endpoint = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
    request = Request(endpoint, headers={"User-Agent": "ScoutV2/0.1"})
    try:
        with urlopen(request, timeout=10) as response:  # nosec B310 - fixed HTTPS host
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # The agent can still produce an explicitly sparse brief.
        return f"Search unavailable: {exc}"

    results = []
    if payload.get("AbstractText"):
        results.append({"title": payload.get("Heading", query), "url": payload.get("AbstractURL", ""), "snippet": payload["AbstractText"]})
    for topic in payload.get("RelatedTopics", [])[:5]:
        if isinstance(topic, dict) and topic.get("Text"):
            results.append({"title": topic.get("FirstURL", query), "url": topic.get("FirstURL", ""), "snippet": topic["Text"]})
    return json.dumps(results, ensure_ascii=False)
