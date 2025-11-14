from __future__ import annotations

from typing import Dict, List, Optional

from ..config import get_config
from .base_client import BaseLLMClient, DashScopeError


class ChatbotClient(BaseLLMClient):
    """Client for LLM chatbot/conversation tasks."""

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Send chat messages to LLM and get response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            system_prompt: Optional system prompt (uses config default if not provided)

        Returns:
            Response text from LLM
        """
        if not self.has_api_key:
            return self._heuristic_chat(messages)

        try:
            system_msg = {
                "role": "system",
                "content": system_prompt or self._config.system_prompt,
            }

            payload = {
                "model": self._config.llm_model,
                "messages": [system_msg] + messages,
            }

            data = self._make_request("chat/completions", payload)
        except Exception as exc:
            if isinstance(exc, DashScopeError):
                raise
            raise DashScopeError(str(exc)) from exc

        return self._extract_response(data)

    def _heuristic_chat(self, messages: List[Dict[str, str]]) -> str:
        """Fallback heuristic response when API key is not available."""
        if not messages:
            return "您好，我可以帮助您。请告诉我您需要什么帮助。"

        last_message = messages[-1].get("content", "")
        if not last_message:
            return "请提供您的消息内容。"

        # Simple echo response for testing
        return f"收到您的消息：{last_message[:100]}。这是一个测试回复，请配置 API key 以使用真实 LLM。"

    @staticmethod
    def _extract_response(data: Dict) -> str:
        """Extract response text from LLM API response."""
        # OpenAI-compatible format: choices[0].message.content
        return data.get("choices", [{}])[0].get("message", {}).get("content", "未能获取模型回复。")

