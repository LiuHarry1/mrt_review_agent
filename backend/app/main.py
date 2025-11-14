from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .llm import ChatbotClient, CompletionClient, DashScopeError
from .schemas import ChatRequest, ChatResponse, ChecklistItem, ReviewRequest, ReviewResponse
from .services.chat_agent import MRTReviewAgent
from .services.review_service import MRTReviewService

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


