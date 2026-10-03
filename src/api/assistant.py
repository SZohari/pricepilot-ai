"""Session-bound, read-only explanations. Background text is request-scoped."""
import hmac
import json
from importlib.util import find_spec
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.retail import analysis
from src.api.v1 import get_service
from src.application.assistant import answer_question
from src.domain.assistant import AssistantQuestion

router = APIRouter(prefix="/api/v1/assistant", tags=["Pricing assistant"])
MODEL_CONFIG = Path.home() / ".config" / "pricepilot" / "assistant.json"


def model_path():
    explicit = os.getenv("PRICEPILOT_GGUF_MODEL_PATH")
    if explicit is not None:
        return explicit.strip()
    # Owner-only configuration for hosts whose process command cannot be edited.
    # No request value, uploaded note or demo workspace can choose this path.
    try:
        with MODEL_CONFIG.open(encoding="utf-8") as handle:
            config = json.loads(handle.read(4097))
        path = config.get("gguf_model_path", "")
        return path if isinstance(path, str) and Path(path).is_absolute() else ""
    except (OSError, ValueError, AttributeError):
        return ""


def settings():
    extra = find_spec("langgraph") is not None and find_spec("langchain_core") is not None
    path = model_path()
    if extra and path and Path(path).is_file() and find_spec("llama_cpp") is not None:
        return extra, "embedded", path
    # A server-owned embedded model works publicly; an owner's laptop is not a public endpoint.
    model = os.getenv("PRICEPILOT_OLLAMA_MODEL", "").strip() if os.getenv("PRICEPILOT_PUBLIC_DEMO") != "1" else ""
    return extra, "ollama" if extra and model else None, model


@router.get("/capabilities")
def capabilities():
    extra, backend, model = settings()
    return dict(default_mode="rag" if backend else "evidence", rag_configured=bool(backend),
                workflow="langgraph" if extra else "python", notes_persisted=False,
                model_location="server_process" if backend == "embedded" else "server_loopback" if backend else None,
                model_name=Path(model).stem if backend == "embedded" else model if backend else None,
                answer_style='selected_excerpt' if backend == 'embedded' else 'interpretation',
                notice="The small server model selects an exact evidence excerpt. The pricing engine supplies the scenario and numbers. Source-only answers stay available.")


@router.post("/ask")
def ask(payload: AssistantQuestion, request: Request, service=Depends(get_service)):
    if not hmac.compare_digest(request.headers.get("X-Workspace-Token", ""), request.state.session.token):
        raise HTTPException(403, "Reload the workspace before asking a question")
    session = request.state.session
    with request.app.state.sessions.lock:
        if session.assistant_busy or session.busy:
            raise HTTPException(429, "Please wait for the current answer or evidence collection")
        session.assistant_busy = True
    try:
        extra, backend, model = settings()
        generator = None
        if backend and payload.mode == "rag":
            from src.infrastructure.assistant_model import local_generator, embedded_generator
            generator = embedded_generator(model) if backend == "embedded" else local_generator(model)
        return answer_question(payload, lambda p: analysis(p, service), generator, use_langgraph=extra)
    finally:
        with request.app.state.sessions.lock:
            session.assistant_busy = False
