from fastapi import APIRouter

from backend.api.auth import router as auth_router
from backend.api.chat import router as chat_router
from backend.api.conversations import router as conversations_router
from backend.api.files import router as files_router
from backend.api.memories import router as memories_router
from backend.api.suggestions import router as suggestions_router
from backend.api.feedback import router as feedback_router
from backend.api.quota import router as quota_router
from backend.api.pricing import router as pricing_router
from backend.api.models import router as models_router
from backend.api.onboarding import router as onboarding_router
from backend.api.profile import router as profile_router
from backend.api.skills import router as skills_router
from backend.api.stats import router as stats_router
from backend.api.tools import router as tools_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(models_router)
api_router.include_router(tools_router)
api_router.include_router(conversations_router)
api_router.include_router(files_router)
api_router.include_router(stats_router)
api_router.include_router(onboarding_router)
api_router.include_router(profile_router)
api_router.include_router(skills_router)
api_router.include_router(memories_router)
api_router.include_router(suggestions_router)
api_router.include_router(feedback_router)
api_router.include_router(quota_router)
api_router.include_router(pricing_router)
