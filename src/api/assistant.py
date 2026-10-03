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
_warm_state = 'not_requested'


def owner_config():
    try:
        with MODEL_CONFIG.open(encoding='utf-8') as handle:
            config = json.loads(handle.read(4097))
        return config if isinstance(config, dict) else {}
    except (OSError, ValueError):
        return {}


def model_path():
    explicit = os.getenv("PRICEPILOT_GGUF_MODEL_PATH")
    if explicit is not None:
        return explicit.strip()
    # Owner-only configuration for hosts whose process command cannot be edited.
    # No request value, uploaded note or demo workspace can choose this path.
    path = owner_config().get("gguf_model_path", "")
    return path if isinstance(path, str) and Path(path).is_absolute() else ""


def settings():
    extra = find_spec("langgraph") is not None and find_spec("langchain_core") is not None
    path = model_path()
    if extra and path and Path(path).is_file() and find_spec("llama_cpp") is not None:
        return extra, "embedded", path
    # A server-owned embedded model works publicly; an owner's laptop is not a public endpoint.
    model = os.getenv("PRICEPILOT_OLLAMA_MODEL", "").strip() if os.getenv("PRICEPILOT_PUBLIC_DEMO") != "1" else ""
    return extra, "ollama" if extra and model else None, model


def warm_assistant():
    """Opt-in startup preparation, using no customer question or shop data."""
    global _warm_state
    if owner_config().get('warm_on_startup') is not True:
        return
    _warm_state = 'preparing'
    extra, backend, path = settings()
    if not extra or backend != 'embedded':
        _warm_state = 'unavailable'
        return
    # Load optional imports before accepting requests on a slow shared host.
    try:
        from langgraph.graph import StateGraph  # noqa: F401
        from src.infrastructure.assistant_model import MODEL_SLOT
        from src.infrastructure.assistant_worker import request_generation
    except ImportError:
        _warm_state = 'unavailable'
        return
    if not MODEL_SLOT.acquire(blocking=False):
        _warm_state = 'busy'
        return
    try:
        request_generation(path, [{'role':'user', 'content':'Choose option 0.'}], ['startup'])
        _warm_state = 'ready'
    except (OSError, ValueError):
        _warm_state = 'unavailable'
        import logging
        logging.getLogger(__name__).warning('Assistant warm-up failed; source mode remains available')
    finally:
        MODEL_SLOT.release()


@router.get("/capabilities")
def capabilities():
    extra, backend, model = settings()
    preparing = owner_config().get('warm_on_startup') is True and _warm_state in ('not_requested', 'preparing')
    return dict(default_mode="rag" if backend and not preparing else "evidence", rag_configured=bool(backend),
                preparing=preparing,
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
