from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ChecklistItem(BaseModel):
    id: str = Field(..., description="Checklist identifier")
    description: str = Field(..., description="Description of the checklist item")


class Suggestion(BaseModel):
    checklist_id: str = Field(..., description="Checklist identifier the suggestion refers to")
    message: str = Field(..., description="Suggested improvement text")


class ReviewRequest(BaseModel):
    mrt_content: str = Field(..., description="Raw manual regression test content provided by the user")
    checklist: Optional[List[ChecklistItem]] = Field(
        default=None,
        description="Optional custom checklist to use for the review. If omitted, the default checklist is applied.",
    )


class ReviewResponse(BaseModel):
    suggestions: List[Suggestion] = Field(..., description="List of suggestions derived from the review")
    summary: Optional[str] = Field(default=None, description="Optional overall summary of the review")


class ConversationState(str, Enum):
    AWAITING_MRT = "awaiting_mrt"
    AWAITING_CHECKLIST = "awaiting_checklist"
    READY = "ready"


class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(
        default=None,
        description="Existing session identifier. Leave empty to start a new session.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Free form user message to the agent.",
    )
    mrt_content: Optional[str] = Field(
        default=None,
        description="Manual regression test content provided outside of the conversational message.",
    )
    checklist: Optional[List[ChecklistItem]] = Field(
        default=None,
        description="Optional custom checklist provided outside of the conversational message.",
    )
    files: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="List of uploaded files with name and content. Format: [{'name': '...', 'content': '...'}, ...]",
    )


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    session_id: str
    state: ConversationState
    replies: List[str]
    suggestions: Optional[List[Suggestion]] = None
    summary: Optional[str] = None
    history: List[ChatTurn] = Field(default_factory=list)
