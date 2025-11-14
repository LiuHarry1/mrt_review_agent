from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_config
from .llm import ChatbotClient, CompletionClient, DashScopeError
from .schemas import ChatRequest, ChatResponse, ConfigUpdateRequest, ReviewRequest, ReviewResponse
from .services.chat_agent import MRTReviewAgent
from .services.review_service import MRTReviewService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = FastAPI(title="MRT Review Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Chatbot client for conversational review
chatbot_client = ChatbotClient()
# Completion client for traditional review endpoint
completion_client = CompletionClient()
review_service = MRTReviewService(llm_client=completion_client)
agent = MRTReviewAgent(chatbot_client=chatbot_client)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/config")
def get_default_config() -> dict:
    """Get default configuration including system prompt and checklist."""
    config = get_config()
    return {
        "system_prompt": config.system_prompt,
        "checklist": [{"id": item.id, "description": item.description} for item in config.default_checklist],
    }


@app.post("/config")
def save_config(request: ConfigUpdateRequest) -> dict:
    """Save system prompt and checklist configuration."""
    try:
        from .config import reload_config
        config = get_config()
        config.save_config(request.system_prompt, request.checklist)
        # Reload the global config instance to reflect changes
        reload_config()
        return {"status": "success", "message": "Configuration saved successfully"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {str(exc)}") from exc


@app.post("/review", response_model=ReviewResponse)
def review(request: ReviewRequest) -> ReviewResponse:
    try:
        return review_service.review(request)
    except DashScopeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/agent/message", response_model=ChatResponse)
def agent_message(request: ChatRequest) -> ChatResponse:
    try:
        return agent.chat(request)
    except DashScopeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


