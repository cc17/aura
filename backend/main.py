import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.api.router import api_router
from backend.config import settings
from backend.graph.supervisor import init_graph
from backend.memory.database import close_database, init_database
from backend.tools.registry import registry

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
logger = logging.getLogger(__name__)

if settings.debug:
    logger.warning(
        "AURA_DEBUG=true: SQLAlchemy will log all queries and parameters — "
        "do NOT run with debug=true in production"
    )

if settings.secret_key == "change-me-to-a-random-secret":
    raise RuntimeError(
        "AURA_SECRET_KEY is not set. Set it in .env before starting the server. "
        "Generate one with: python3 -c \"import secrets; print(secrets.token_hex(32))\""
    )

# litellm creates aiohttp sessions internally that may not close cleanly on stream
# cancellation — suppress the cosmetic asyncio warning so it doesn't pollute logs.
class _SuppressUnclosedSession(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "Unclosed client session" not in record.getMessage()

logging.getLogger("asyncio").addFilter(_SuppressUnclosedSession())

# Route aura.trace events to a dedicated file for easy grep/analysis
_trace_handler = logging.FileHandler("aura_trace.log")
_trace_handler.setFormatter(logging.Formatter("%(message)s"))  # raw JSON lines
logging.getLogger("aura.trace").addHandler(_trace_handler)
logging.getLogger("aura.trace").propagate = False  # don't duplicate to root logger

# Route ERROR+ to aura_error.log so the admin dashboard can surface them
_error_handler = logging.FileHandler("aura_error.log")
_error_handler.setLevel(logging.ERROR)
_error_handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
logging.getLogger().addHandler(_error_handler)

app = FastAPI(title="Aura", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.include_router(api_router)


@app.on_event("startup")
async def startup():
    await init_database()
    logger.info("Database initialized")

    registry.auto_discover()
    tools = registry.list_tools()
    logger.info(f"Registered {len(tools)} tools: {[t['name'] for t in tools]}")

    init_graph()
    logger.info("Multi-agent graph ready")

    from backend.memory.database import get_session_factory
    from backend.services.skill_registry import load_skills
    async with get_session_factory()() as session:
        await load_skills(session)
    logger.info("Skills loaded from DB")

    import asyncio
    from backend.services.skill_intent_matcher import build_skill_embeddings
    asyncio.create_task(build_skill_embeddings())
    logger.info("Skill embedding build started (background)")


@app.on_event("shutdown")
async def shutdown():
    await close_database()
