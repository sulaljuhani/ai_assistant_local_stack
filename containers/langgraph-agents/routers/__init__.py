"""API routers for the LangGraph agents application."""

from .tasks import router as tasks_router
from .reminders import router as reminders_router
from .events import router as events_router
from .vault import router as vault_router
from .documents import router as documents_router

__all__ = ["tasks_router", "reminders_router", "events_router", "vault_router", "documents_router"]
