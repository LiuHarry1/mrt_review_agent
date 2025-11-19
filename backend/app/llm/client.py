"""Unified LLM client for both completion and chat tasks."""
from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from ..models import ReviewResponse
from .factory import LLMClientFactory
from .provider import LLMError

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client for both completion and chat tasks."""

    def __init__(self, provider_client=None):
        """Initialize LLM client. Uses provider from config if not specified."""
        self._client = provider_client or LLMClientFactory.get_default_client()
        self._config = self._client._config
    
    def _get_client(self):
        """Get provider client, recreating it if needed to use latest config."""
        # Always get a fresh client to ensure we use the latest config
        # This allows config updates to take effect without restarting the server
        return LLMClientFactory.get_default_client()

    @property
    def has_api_key(self) -> bool:
        """Check if API key is available."""
        return self._get_client().has_api_key

    @property
    def model(self) -> str:
        """Get model name."""
        return self._get_client().model

    def review(self, mrt_content: str, software_requirement: Optional[str] = None) -> ReviewResponse:
        """Review MRT content against checklist and software requirement."""
        from ..config import get_config
        
        if not self.has_api_key:
            logger.warning("No API key available, using heuristic review")
            return ReviewResponse(
                suggestions=[],
                summary=None,
                raw_content="API key is not available. Please configure your API key to use the review feature."
            )

        config = get_config()
        client = self._get_client()
        model_name = client.model
        mrt_length = len(mrt_content)
        checklist_count = len(config.default_checklist)
        has_requirement = software_requirement is not None and software_requirement.strip() != ""
        
        logger.info(f"LLM review - Provider: {type(client).__name__}, Model: {model_name}, MRT: {mrt_length} chars, Checklist: {checklist_count}, Has requirement: {has_requirement}")
        start_time = time.time()

        # Import here to avoid circular dependency
        from ..service.prompt import build_system_prompt, build_user_message
        system_prompt = build_system_prompt(software_requirement)
        user_message = build_user_message(mrt_content, software_requirement)

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]

            logger.info("-------------  messages begin-------------------")
            logger.info(f"System prompt length: {len(system_prompt)} chars")
            logger.info(f"System prompt preview: {system_prompt[:300]}...")
            logger.info(f"User message length: {len(user_message)} chars")
            logger.info(f"User message preview: {user_message[:300]}...")
            logger.info("-------------  messages end-------------------")  

            payload = client._normalize_payload(messages, model=model_name)
            payload["max_tokens"] = 2000

            data = client._make_request("chat/completions", payload)
            raw_content = client._extract_response(data)
            
            elapsed_time = time.time() - start_time
            logger.info(f"LLM review completed - Time: {elapsed_time:.2f}s, Response: {len(raw_content)} chars")
            
            return ReviewResponse(suggestions=[], summary=None, raw_content=raw_content)
            
        except LLMError as exc:
            elapsed_time = time.time() - start_time
            logger.error(f"LLM review failed after {elapsed_time:.2f}s - {exc}")
            raise
        except Exception as exc:
            elapsed_time = time.time() - start_time
            logger.error(f"LLM review failed after {elapsed_time:.2f}s - Unexpected error: {exc}", exc_info=True)
            raise LLMError(str(exc)) from exc

    def chat_stream(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None):
        """Send chat messages to LLM and get streaming response."""
        if not self.has_api_key:
            # Fallback: yield complete heuristic response
            response = self._heuristic_chat(messages)
            yield response
            return

        try:
            client = self._get_client()
            system_msg = {"role": "system", "content": system_prompt or ""}
            all_messages = [system_msg] + messages
            
            payload = client._normalize_payload(all_messages, model=client.model)
            
            # Make streaming request
            for chunk in client._make_stream_request("chat/completions", payload):
                yield chunk
                
        except LLMError as exc:
            raise
        except Exception as exc:
            raise LLMError(str(exc)) from exc

    def _heuristic_chat(self, messages: List[Dict[str, str]]) -> str:
        """Fallback response when API key is not available."""
        if not messages:
            return "您好，我可以帮助您。请告诉我您需要什么帮助。"

        last_message = messages[-1].get("content", "")
        if not last_message:
            return "请提供您的消息内容。"

        return f"收到您的消息：{last_message[:100]}。这是一个测试回复，请配置 API key 以使用真实 LLM。"

