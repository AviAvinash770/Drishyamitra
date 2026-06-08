"""
Orchestrator agent – the supervisor that classifies user intent and routes
to the correct specialised agent.

Uses the Groq LLM (``llama-3.3-70b-versatile``) to perform zero-shot intent
classification.  The result is written into *state['next_step']* which the
LangGraph conditional edge reads to decide the next node.
"""

import logging
from typing import Dict, Any

from flask import current_app
from groq import Groq

logger = logging.getLogger(__name__)

# ── Classification prompt ────────────────────────────────────────────────────
_CLASSIFICATION_PROMPT = (
    "You are a request classifier for a photo-management assistant called "
    "Drishyamitra.  Classify the following user request into EXACTLY ONE of "
    "these categories:\n"
    "  • search  – looking for photos, finding pictures, browsing images\n"
    "  • memory  – asking about a person, relationship, or who someone is\n"
    "  • album   – creating, managing, or organising albums\n"
    "  • sharing – sending, sharing, emailing, or WhatsApp-ing photos\n"
    "  • general – greetings, small-talk, help, or anything else\n\n"
    "User request: {query}\n\n"
    "Respond with ONLY the category name in lowercase, nothing else."
)

# Valid routing targets (after mapping 'general' → 'end')
_VALID_ROUTES = {"search", "memory", "album", "sharing", "end"}


class OrchestratorAgent:
    """Supervisor agent that routes user requests to specialized agents.

    The orchestrator never performs domain work itself.  It analyses the
    user query with a lightweight LLM call, writes the resulting route
    into the shared workflow state, and hands control to the LangGraph
    conditional edge.
    """

    @staticmethod
    def route(state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse *state['user_query']* and set *state['next_step']*.

        Routing targets
        ---------------
        * ``search``  – photo finding / browsing
        * ``memory``  – person / relationship queries
        * ``album``   – album creation / management
        * ``sharing`` – send / share requests
        * ``end``     – general conversation (maps from ``general``)

        Returns
        -------
        dict
            Updated state with ``next_step`` and an entry appended to
            ``action_logs``.
        """
        query: str = state.get("user_query", "")
        action_logs: list = list(state.get("action_logs", []))

        try:
            api_key = current_app.config["GROQ_API_KEY"]
            model = current_app.config.get("GROQ_MODEL", "llama-3.3-70b-versatile")

            if not api_key:
                logger.warning("GROQ_API_KEY is empty – falling back to keyword routing.")
                route = OrchestratorAgent._keyword_fallback(query)
            else:
                client = Groq(api_key=api_key)
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a concise intent classifier.  Reply with a single word.",
                        },
                        {
                            "role": "user",
                            "content": _CLASSIFICATION_PROMPT.format(query=query),
                        },
                    ],
                    temperature=0.0,
                    max_tokens=10,
                )
                raw = completion.choices[0].message.content.strip().lower()
                # Map 'general' → 'end'; guard against unexpected responses.
                route = "end" if raw == "general" else raw
                if route not in _VALID_ROUTES:
                    logger.warning(
                        "LLM returned unexpected route '%s' – falling back to keyword routing.",
                        raw,
                    )
                    route = OrchestratorAgent._keyword_fallback(query)

        except Exception as exc:
            logger.error("Orchestrator LLM call failed: %s", exc, exc_info=True)
            route = OrchestratorAgent._keyword_fallback(query)
            action_logs.append(f"[orchestrator] LLM error, used keyword fallback → {route}")

        action_logs.append(f"[orchestrator] Classified intent as '{route}' for query: {query!r}")
        state["next_step"] = route
        state["action_logs"] = action_logs
        return state

    # ── Keyword-based fallback ───────────────────────────────────────────────
    @staticmethod
    def _keyword_fallback(query: str) -> str:
        """Simple keyword heuristic used when the LLM is unavailable.

        Parameters
        ----------
        query : str
            The user's natural-language request.

        Returns
        -------
        str
            One of ``search``, ``memory``, ``album``, ``sharing``, or ``end``.
        """
        q = query.lower()

        sharing_kw = {"send", "share", "email", "whatsapp", "deliver", "forward"}
        album_kw = {"album", "group", "organise", "organize", "collection", "folder"}
        search_kw = {
            "find", "search", "show", "look", "where", "photo", "picture",
            "image", "browse", "display", "get",
        }
        memory_kw = {"who", "person", "people", "relation", "family", "friend", "name"}

        for kw in sharing_kw:
            if kw in q:
                return "sharing"
        for kw in album_kw:
            if kw in q:
                return "album"
        for kw in search_kw:
            if kw in q:
                return "search"
        for kw in memory_kw:
            if kw in q:
                return "memory"

        return "end"
