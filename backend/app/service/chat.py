"""Chat service for conversational MRT review agent."""
from __future__ import annotations

import logging
from typing import Dict, Generator, List, Optional

from ..config import get_config
from ..llm import LLMClient, LLMError
from ..models import ChatRequest
from .chat_file_handler import format_files_for_message

logger = logging.getLogger(__name__)


class ChatService:
    """Service for conversational MRT review agent based on conversation history."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize chat service."""
        self.llm_client = llm_client or LLMClient()

    def _build_agent_system_prompt(self) -> str:
        """Build unified system prompt for MRT review agent."""
        config = get_config()
        checklist = config.default_checklist
        checklist_string = "\n".join([f"- {item.id}: {item.description}" for item in checklist])

        return f"""You are a professional MRT (Manual Regression Test) review assistant. Your goal is to review MRT test cases.

Checklist:
{checklist_string}

Workflow:
1. When MRT content is detected (file upload or message), first ask if the user has software requirement documents (SRD/user stories)
2. Review MRT against the checklist above
3. If requirements are provided, also ensure:
   - Each requirement is covered by test cases
   - All scenarios, conditions, and edge cases are addressed
4. Provide specific, actionable improvement suggestions

Answer user questions about the review process."""

    def _trim_history(self, messages: List[Dict[str, str]], max_turns: int = 30) -> List[Dict[str, str]]:
        """
        Trim conversation history to keep only recent messages.
        
        Args:
            messages: Full conversation history
            max_turns: Maximum number of message turns to keep
            
        Returns:
            Trimmed conversation history
        """
        if len(messages) <= max_turns:
            return messages

        # Keep system message if exists, then recent messages
        if messages and messages[0].get("role") == "system":
            return [messages[0]] + messages[-(max_turns - 1):]
        return messages[-max_turns:]

    def chat_stream(self, request: ChatRequest) -> Generator[str, None, None]:
        """
        Handle chat request with streaming response.
        
        This method processes user messages and files, formats them for the conversation,
        and streams LLM responses. All context is maintained in conversation history.
        """
        try:
            # Handle file uploads - format as part of user message
            file_content = format_files_for_message(request.files)
            
            # Build user message
            user_message = request.message or ""
            if file_content:
                if user_message:
                    user_message = f"{user_message}\n\n{file_content}"
                else:
                    user_message = file_content

            # Get conversation history from request
            messages = request.messages or []
            
            # Add current user message to history
            if user_message:
                messages.append({"role": "user", "content": user_message})

            # Trim history to keep it manageable
            messages = self._trim_history(messages, max_turns=30)

            # Build system prompt
            system_prompt = self._build_agent_system_prompt()

            # Stream LLM response
            if messages:
                try:
                    for chunk in self.llm_client.chat_stream(messages, system_prompt=system_prompt):
                        yield chunk
                except LLMError as exc:
                    error_str = str(exc)
                    if "Connection reset" in error_str or "Connection reset by peer" in error_str:
                        error_msg = "Connection was reset. This might be due to large file size or network instability. Please try: 1) Upload smaller files 2) Check network connection 3) Retry later"
                    elif "timeout" in error_str.lower() or "timed out" in error_str.lower():
                        error_msg = "Request timeout: Processing took too long. Please try uploading smaller files or upload in batches."
                    elif "Connection" in error_str:
                        error_msg = "Connection error: Unable to connect to AI service. Please check network connection or retry later."
                    else:
                        error_msg = f"Error processing request: {error_str}"
                    yield error_msg
                except Exception as exc:
                    logger.error(f"Unexpected error during LLM streaming: {exc}", exc_info=True)
                    yield f"An unexpected error occurred: {str(exc)}"
            else:
                # No messages yet, return welcome message
                yield "Hello! I'm a professional MRT (Manual Regression Test) review assistant. I can help you review test cases according to a checklist. Please upload MRT files or paste test case content to get started."

        except Exception as exc:
            logger.error(f"Error in chat_stream: {exc}", exc_info=True)
            yield f"An error occurred while processing your request: {str(exc)}"
