"""
OkChat — API v1 Router
Aggregates all module routers under the /api/v1 prefix.
Adding a new module = one include_router call here.
"""
from fastapi import APIRouter

from okchat.modules.conversations.api.router import router as conversations_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(
    conversations_router,
    prefix="/conversations",
    tags=["Conversations"],
)

# Future modules — uncomment as they are implemented:
# from okchat.modules.auth.api.router import router as auth_router
# from okchat.modules.agents.api.router import router as agents_router
# from okchat.modules.channels.api.router import router as channels_router
# from okchat.modules.voice.api.router import router as voice_router
# from okchat.modules.webhooks.api.router import router as webhooks_router

# v1_router.include_router(auth_router,     prefix="/auth",     tags=["Auth"])
# v1_router.include_router(agents_router,   prefix="/agents",   tags=["Agents"])
# v1_router.include_router(channels_router, prefix="/channels", tags=["Channels"])
# v1_router.include_router(voice_router,    prefix="/voice",    tags=["Voice"])
# v1_router.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])
