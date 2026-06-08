"""
Chat Blueprint
===============
AI Assistant endpoint with Groq tool calling and LangGraph agent workflow.

Endpoints:
    POST /api/chat
"""

import json
import logging

from flask import Blueprint, request, jsonify, current_app

from database.db import db
from models.photo import Photo
from models.person import Person
from models.album import Album
from models.face import Face
from models.sharing import DeliveryHistory
from models.log import AgentLog

logger = logging.getLogger(__name__)
bp = Blueprint("chat", __name__, url_prefix="/api/chat")

# ── System prompt matching the frontend CHAT_SYSTEM constant ──────────────
SYSTEM_PROMPT = (
    "You are Drishyamitra, an intelligent AI photo management assistant. "
    "You help users find and organize photos by person, date, event, or location, "
    "send photos via email or WhatsApp, get insights about their photo collection, "
    "and manage face recognition. Be helpful, concise, and conversational. "
    "Keep responses under 120 words. "
    "You have access to tools. Use them when the user asks about photos, people, "
    "albums, or sharing. Always provide factual data from the tools. "
    "CRITICAL RULE: You can ONLY assist with queries directly related to this application (managing, searching, organizing, sharing, and analyzing the user's photo library). "
    "You are strictly forbidden from answering general knowledge, coding, math, essay writing, or any other non-application queries. "
    "If the user asks an unrelated question (such as 'write a python script', 'explain gravity', 'who is the president', etc.), "
    "you MUST politely refuse to answer and state: 'I am sorry, but I can only assist with photo library management and search queries.'"
)

# ── Tool definitions for Groq function calling ────────────────────────────
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_photos",
            "description": "Search photos by text query — person name, event, date, or description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query text",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_person",
            "description": "Get details about a recognised person and the photos they appear in.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The person's name to look up",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_album",
            "description": "Create a new photo album.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Album name",
                    },
                    "description": {
                        "type": "string",
                        "description": "Album description",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "share_photos",
            "description": "Share a person's photos via email or WhatsApp.",
            "parameters": {
                "type": "object",
                "properties": {
                    "person_name": {
                        "type": "string",
                        "description": "Name of the person whose photos to share",
                    },
                    "recipient": {
                        "type": "string",
                        "description": "Email address or phone number",
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["email", "whatsapp"],
                        "description": "Delivery platform",
                    },
                },
                "required": ["person_name", "recipient", "platform"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analytics_summary",
            "description": "Get a summary of analytics: total photos, people, storage, accuracy.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


# ── Tool execution functions ──────────────────────────────────────────────

def _tool_search_photos(query):
    """Execute search_photos tool."""
    results = []

    # Structured: person name
    persons = Person.query.filter(Person.name.ilike(f"%{query}%")).all()
    for person in persons:
        photo_ids = list({f.photo_id for f in person.faces})
        photos = Photo.query.filter(Photo.id.in_(photo_ids)).all() if photo_ids else []
        for p in photos:
            results.append({"id": p.id, "name": p.filename, "date": p.date, "persons": [person.name]})

    # Structured: description / location
    db_photos = Photo.query.filter(
        db.or_(
            Photo.description.ilike(f"%{query}%"),
            Photo.location.ilike(f"%{query}%"),
            Photo.filename.ilike(f"%{query}%"),
        )
    ).limit(10).all()
    seen_ids = {r["id"] for r in results}
    for p in db_photos:
        if p.id not in seen_ids:
            results.append({"id": p.id, "name": p.filename, "date": p.date})

    # Semantic search
    try:
        from services.vector_service import VectorService
        vector_ids = VectorService.search_photos(query, limit=10)
        for vid in vector_ids:
            if vid not in seen_ids:
                photo = Photo.query.get(vid)
                if photo:
                    results.append({"id": photo.id, "name": photo.filename, "date": photo.date})
    except Exception:
        pass

    return {"count": len(results), "photos": results[:15]}


def _tool_get_person(name):
    """Execute get_person tool."""
    person = Person.query.filter(Person.name.ilike(f"%{name}%")).first()
    if not person:
        return {"error": f"No person found matching '{name}'"}

    photo_ids = list({f.photo_id for f in person.faces})
    return {
        "id": person.id,
        "name": person.name,
        "photoCount": person.photo_count,
        "tags": person.tags or [],
        "photos": photo_ids[:20],
    }


def _tool_create_album(name, description=""):
    """Execute create_album tool."""
    existing = Album.query.filter(db.func.lower(Album.name) == name.lower()).first()
    if existing:
        return {"message": f'Album "{name}" already exists', "id": existing.id}

    album = Album(name=name, description=description)
    db.session.add(album)
    db.session.commit()
    return {"message": f'Album "{name}" created', "id": album.id}


def _tool_share_photos(person_name, recipient, platform):
    """Execute share_photos tool."""
    try:
        from services.sharing_service import SharingService

        person = Person.query.filter(Person.name.ilike(f"%{person_name}%")).first()
        if not person:
            return {"error": f"No person found matching '{person_name}'"}

        photo_ids = list({f.photo_id for f in person.faces})
        photos = Photo.query.filter(Photo.id.in_(photo_ids)).all() if photo_ids else []
        photo_paths = [p.file_path for p in photos]

        if platform == "whatsapp":
            result = SharingService.send_whatsapp(recipient, person.name, photo_paths)
        else:
            result = SharingService.send_email(recipient, person.name, photo_paths)

        return {
            "message": f"Sent {len(photo_paths)} photos of {person.name} to {recipient} via {platform}",
            "delivery": result,
        }
    except Exception as exc:
        return {"error": str(exc)}


def _tool_analytics_summary():
    """Execute analytics_summary tool."""
    total_photos = Photo.query.count()
    total_people = Person.query.count()
    total_faces = Face.query.count()
    unrecognised = Face.query.filter_by(person_id=None).count()
    recognised = total_faces - unrecognised
    accuracy = round((recognised / total_faces * 100), 1) if total_faces else 0
    deliveries = DeliveryHistory.query.count()

    return {
        "total_photos": total_photos,
        "total_people": total_people,
        "faces_detected": total_faces,
        "recognised": recognised,
        "unrecognised": unrecognised,
        "accuracy": f"{accuracy}%",
        "deliveries_sent": deliveries,
    }


TOOL_HANDLERS = {
    "search_photos": lambda args: _tool_search_photos(args.get("query", "")),
    "get_person": lambda args: _tool_get_person(args.get("name", "")),
    "create_album": lambda args: _tool_create_album(args.get("name", ""), args.get("description", "")),
    "share_photos": lambda args: _tool_share_photos(
        args.get("person_name", ""), args.get("recipient", ""), args.get("platform", "email")
    ),
    "analytics_summary": lambda args: _tool_analytics_summary(),
}


# ── POST /api/chat ────────────────────────────────────────────────────────

@bp.route("/", methods=["POST"])
def chat():
    """AI Assistant chat endpoint.

    Expects JSON::

        {
            "prompt": "Show me photos of Priya",
            "history": [                          // optional
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }

    First attempts the LangGraph agent workflow.  Falls back to direct
    Groq API with tool calling.
    """
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    history = data.get("history", [])
    photo_ids = data.get("photo_ids", [])

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    actions = []

    # ── Attempt 1: LangGraph agent workflow ───────────────────────────
    try:
        from workflows.agent_workflow import run_agent_workflow

        result = run_agent_workflow(prompt, history, photo_ids=photo_ids)
        if result and result.get("response"):
            _log_interaction(prompt, "langgraph", "agent_workflow", result["response"])
            return jsonify({
                "response": result["response"],
                "actions": result.get("actions", []),
            }), 200
    except Exception as exc:
        logger.info("LangGraph workflow unavailable, falling back to Groq: %s", exc)

    # ── Attempt 2: Direct Groq API with tool calling ──────────────────
    try:
        from groq import Groq

        api_key = current_app.config.get("GROQ_API_KEY", "")
        if not api_key or api_key == "your-groq-api-key-here":
            raise ValueError("GROQ_API_KEY not configured")

        client = Groq(api_key=api_key)
        model = current_app.config.get("GROQ_MODEL", "llama-3.3-70b-versatile")

        # Build messages
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in history[-8:]:
            role = h.get("role", "user")
            if role == "bot":
                role = "assistant"
            messages.append({"role": role, "content": h.get("content", h.get("text", ""))})
        messages.append({"role": "user", "content": prompt})

        # First call — may produce tool_calls
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            max_tokens=500,
            temperature=0.7,
        )

        msg = response.choices[0].message

        # Process tool calls if any
        if msg.tool_calls:
            messages.append(msg)  # append assistant message with tool_calls

            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                try:
                    fn_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                handler = TOOL_HANDLERS.get(fn_name)
                if handler:
                    tool_result = handler(fn_args)
                    actions.append({"tool": fn_name, "args": fn_args, "result": tool_result})
                else:
                    tool_result = {"error": f"Unknown tool: {fn_name}"}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result),
                })

            # Second call — generate response using tool results
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
            )
            reply = response.choices[0].message.content or "I've completed the action."
        else:
            reply = msg.content or "I couldn't process that request."

        _log_interaction(prompt, "groq_direct", "chat", reply)
        return jsonify({"response": reply, "actions": actions}), 200

    except Exception as exc:
        logger.warning("Groq API call failed: %s", exc)

    # ── Attempt 3: Offline fallback ───────────────────────────────────
    reply = _offline_fallback(prompt)
    _log_interaction(prompt, "offline", "fallback", reply)
    return jsonify({"response": reply, "actions": actions}), 200


def _offline_fallback(prompt):
    """Generate a basic response without any LLM by querying the DB."""
    prompt_lower = prompt.lower()

    # Person queries
    persons = Person.query.all()
    for person in persons:
        if person.name.lower() in prompt_lower:
            return (
                f"I found {person.photo_count} photos of {person.name}. "
                f"Tags: {', '.join(person.tags) if person.tags else 'none'}. "
                f"Would you like me to share them or create an album?"
            )

    # Photo count queries
    if any(w in prompt_lower for w in ["how many", "total", "count"]):
        total = Photo.query.count()
        people = Person.query.count()
        return (
            f"Your library has {total} photos with {people} recognised people. "
            f"You can ask me to search, share, or organise them!"
        )

    # Album queries
    if "album" in prompt_lower:
        albums = Album.query.all()
        names = ", ".join(a.name for a in albums) if albums else "none yet"
        return f"Your albums: {names}. Want me to create a new one?"

    return (
        "I'm your Drishyamitra AI assistant! I can help you find photos by person, "
        "date, or event, share photos via email or WhatsApp, create albums, and show "
        "analytics. What would you like to do?"
    )


def _log_interaction(prompt, agent_name, action, response_text):
    """Write an AgentLog record for auditing."""
    try:
        log = AgentLog(
            prompt=prompt,
            agent_name=agent_name,
            action=action,
            log_text=response_text[:500],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()
