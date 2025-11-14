from __future__ import annotations

from typing import List, Optional

from ..config import get_config
from ..schemas import ChecklistItem, ReviewResponse, Suggestion
from .base_client import BaseLLMClient, DashScopeError


class CompletionClient(BaseLLMClient):
    """Client for LLM completion tasks (e.g., MRT review)."""

    def review(self, mrt_content: str, checklist: List[ChecklistItem]) -> ReviewResponse:
        """Review MRT content against checklist using LLM completion."""
        if not self.has_api_key:
            print("no model api key")
            return self._heuristic_review(mrt_content, checklist)

        try:
            payload = {
                "model": self._config.llm_model,
                "messages": [
                    {
                        "role": "system",
                        "content": self._config.system_prompt,
                    },
                    {
                        "role": "user",
                        "content": f"MRT 内容:\n{mrt_content}\n\nChecklist: {checklist}",
                    },
                ],
            }

            data = self._make_request("chat/completions", payload)
        except Exception as exc:
            if isinstance(exc, DashScopeError):
                raise
            raise DashScopeError(str(exc)) from exc

        suggestions = self._parse_suggestions_from_llm(data, checklist)
        summary = self._extract_summary(data)
        return ReviewResponse(suggestions=suggestions, summary=summary)

    def _heuristic_review(self, mrt_content: str, checklist: List[ChecklistItem]) -> ReviewResponse:
        """Fallback heuristic review when API key is not available."""
        text = mrt_content.lower()
        suggestions: List[Suggestion] = []

        # Get keyword mapping from configuration
        keyword_map = self._config.keyword_mapping

        for item in checklist:
            candidates = keyword_map.get(item.id)
            if candidates:
                if not any(keyword.lower() in text for keyword in candidates):
                    suggestions.append(
                        Suggestion(
                            checklist_id=item.id,
                            message=f"未检测到 `{item.description}` 的相关内容，请补充。",
                        )
                    )
            else:
                # For checklist items without keyword mapping, use generic message
                suggestions.append(
                    Suggestion(
                        checklist_id=item.id,
                        message=f"请确认 `{item.description}` 的内容已在 MRT 中体现。",
                    )
                )

        # Apply additional suggestions from configuration
        for additional in self._config.additional_suggestions:
            keywords = additional.get("keywords", [])
            if keywords and not any(keyword.lower() in text for keyword in keywords):
                suggestions.append(
                    Suggestion(
                        checklist_id=additional["id"],
                        message=additional["message"],
                    )
                )

        summary = (
            f"共识别到 {len(suggestions)} 条改进建议。" if suggestions else "未发现明显问题。继续保持当前质量。"
        )
        return ReviewResponse(suggestions=suggestions, summary=summary)

    @staticmethod
    def _parse_suggestions_from_llm(data, checklist: List[ChecklistItem]) -> List[Suggestion]:  # pragma: no cover
        """Parse suggestions from LLM response."""
        suggestions: List[Suggestion] = []
        # OpenAI-compatible format: choices[0].message.content
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        for item in checklist:
            if item.id in text:
                suggestions.append(Suggestion(checklist_id=item.id, message=f"请检查 {item.description}"))
        return suggestions or [
            Suggestion(checklist_id="LLM-FALLBACK", message="未能解析模型输出，请人工确认。")
        ]

    @staticmethod
    def _extract_summary(data) -> Optional[str]:  # pragma: no cover
        """Extract summary from LLM response."""
        # OpenAI-compatible format: choices[0].message.content
        return data.get("choices", [{}])[0].get("message", {}).get("content")

