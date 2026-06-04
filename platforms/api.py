import os
import uuid
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from core.llm import Conversation
from core import background

load_dotenv()

app = FastAPI(title="RIAS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_sessions: dict[str, Conversation] = {}


class MessageRequest(BaseModel):
    message: str
    images: list[str] = []  # base64 data URLs van de webapp


def _history_text(conv: Conversation) -> list:
    result = []
    for msg in conv.history:
        if msg["role"] == "system":
            continue
        if msg["role"] in ("tool",):
            continue
        content = msg.get("content")
        if not content:
            continue
        if isinstance(content, list):
            text = " ".join(p["text"] for p in content if p.get("type") == "text")
        else:
            text = content
        result.append({"role": msg["role"], "content": text})
    return result


_WEBAPP_DIST = os.getenv("WEBAPP_DIST", os.path.expanduser("~/Dev/AIwebapp/dist"))
if os.path.isdir(_WEBAPP_DIST):
    app.mount("/assets", StaticFiles(directory=f"{_WEBAPP_DIST}/assets"), name="assets")

    @app.get("/")
    def serve_webapp():
        return FileResponse(f"{_WEBAPP_DIST}/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/conversation")
def new_conversation():
    session_id = str(uuid.uuid4())
    _sessions[session_id] = Conversation()
    return {"session_id": session_id}


@app.post("/conversation/{session_id}/message")
def send_message(session_id: str, body: MessageRequest):
    conv = _sessions.get(session_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Session not found")

    def generate():
        try:
            for kind, data in conv.chat_stream(body.message, images=body.images):
                if kind == "reply":
                    yield f"data: {json.dumps({'type': 'reply', 'text': data})}\n\n"
                elif kind == "tool":
                    yield f"data: {json.dumps({'type': 'tool', 'name': data})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/conversation/{session_id}/history")
def get_history(session_id: str):
    conv = _sessions.get(session_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"history": _history_text(conv)}


@app.get("/conversation/{session_id}/agents")
def get_agent_results(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    conv = _sessions[session_id]
    results = background.drain_results()
    injected = []
    for task in results:
        reply = ""
        for kind, data in conv.inject_agent_result(task["name"], task["result"]):
            if kind == "reply":
                reply += data
        injected.append({"agent": task["name"], "reply": reply})
    return {"results": injected}
