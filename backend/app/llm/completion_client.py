from __future__ import annotations

import logging
import time
from typing import List, Optional

from ..config import get_config
from ..schemas import ChecklistItem, ReviewResponse, Suggestion
from .base_client import BaseLLMClient, DashScopeError

logger = logging.getLogger(__name__)


class CompletionClient(BaseLLMClient):
    """Client for LLM completion tasks (e.g., MRT review)."""

    def review(self, mrt_content: str, checklist: List[ChecklistItem], system_prompt: Optional[str] = None) -> ReviewResponse:
        """Review MRT content against checklist using LLM completion."""
        if not self.has_api_key:
            logger.warning("No API key available, using heuristic review")
            return self._heuristic_review(mrt_content, checklist)

        # Use custom system prompt if provided, otherwise use default
        prompt = system_prompt if system_prompt is not None else self._config.system_prompt

        model_name = self._config.llm_model
        mrt_length = len(mrt_content)
        checklist_count = len(checklist)
        
        logger.info(f"Starting LLM review request - Model: {model_name}, MRT length: {mrt_length} chars, Checklist items: {checklist_count}")
        start_time = time.time()

        try:
            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": prompt,
                    },
                    {
                        "role": "user",
                        "content": f"Review the following MRT against the checklist. Provide brief, concise suggestions only.\n\nMRT Content:\n{mrt_content}\n\nChecklist: {checklist}",
                    },
                ],
                "max_tokens": 1000,  # Limit response length for faster output
            }

            logger.debug(f"Making API request to {self.base_url}/chat/completions")
            data = self._make_request("chat/completions", payload)
            
            elapsed_time = time.time() - start_time
            response_length = len(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
            logger.info(f"LLM review completed successfully - Elapsed time: {elapsed_time:.2f}s, Response length: {response_length} chars")
            
        except DashScopeError as exc:
            elapsed_time = time.time() - start_time
            logger.error(f"LLM review failed after {elapsed_time:.2f}s - Error: {str(exc)}")
            raise
        except Exception as exc:
            elapsed_time = time.time() - start_time
            logger.error(f"LLM review failed after {elapsed_time:.2f}s - Unexpected error: {str(exc)}", exc_info=True)
            raise DashScopeError(str(exc)) from exc

        # Extract raw content from model response
        raw_content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Return only raw content, no need to parse suggestions or summary
        return ReviewResponse(suggestions=[], summary=None, raw_content=raw_content)

    def _heuristic_review(self, mrt_content: str, checklist: List[ChecklistItem]) -> ReviewResponse:
        """Fallback heuristic review when API key is not available."""
        # Simple fallback: return a message indicating API key is not available
        raw_content = "API key is not available. Please configure your API key to use the review feature."
        return ReviewResponse(suggestions=[], summary=None, raw_content=raw_content)

