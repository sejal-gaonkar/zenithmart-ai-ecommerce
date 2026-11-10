import os
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

import database
import shop_db
import shop_routes
from bot_engine import bot_engine, session_manager, knowledge_loader

HOST = os.getenv("HOST", "127.0.0.1").strip()
PORT = int(os.getenv("PORT", "8000"))

shop_db.init()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        kb = knowledge_loader.get_content()
        print(f"[Bot] Knowledge base loaded successfully ({len(kb)} characters).")
    except FileNotFoundError as e:
        print(f"[Bot] WARNING: {e}")
    print(f"[Bot] Gemini model: {bot_engine.model}")
    yield


app = FastAPI(title="ZenithMart", lifespan=lifespan)
app.include_router(shop_routes.router)

os.makedirs(os.path.join(BASE_DIR, "static", "img"), exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

_hits = defaultdict(deque)


def rate_limit(request: Request, limit: int = 15, window: int = 60):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(status_code=429, detail="Too many messages. Please wait a minute.")
    q.append(now)


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=1000)
    session_id: Optional[str] = None


class ClearRequest(BaseModel):
    session_id: str


@app.get("/")
async def index():
    return FileResponse(os.path.join(BASE_DIR, "shop.html"))


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": bot_engine.model, "api_key_loaded": bool(bot_engine.api_key)}


@app.post("/api/chat")
def chat(req: ChatRequest, request: Request):
    rate_limit(request)
    return bot_engine.generate_response(req.session_id or str(uuid.uuid4()), req.message)


@app.get("/api/history/{session_id}")
def history(session_id: str):
    return {"session_id": session_id, "history": database.get_session_history(session_id, limit=50)}


@app.post("/api/clear")
def clear(req: ClearRequest):
    session_manager.clear(req.session_id)
    return {"status": "cleared"}


@app.get("/api/stats")
def stats():
    return database.get_stats()


if __name__ == "__main__":
    print(f"Starting ZenithMart server at http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, proxy_headers=True, forwarded_allow_ips="*")