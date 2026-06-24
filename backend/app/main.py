from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.integrations.mocks import build_mock_registry
from app.services.executor import WorkflowExecutor
from app.services.planner_graph import LangGraphPlanner
from app.services.store import InMemoryPrototypeStore


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Workflow MVP Challenge",
        version="0.1.0",
        description="Natural-language to executable workflow API. Submit an instruction, get a structured plan, execute it against mocked integrations.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.planner = LangGraphPlanner()
    app.state.executor = WorkflowExecutor(connector_registry=build_mock_registry())
    app.state.store = InMemoryPrototypeStore()

    app.include_router(router)
    return app


app = create_app()
