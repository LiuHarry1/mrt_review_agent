from __future__ import annotations

from typing import List, Optional

from ..checklist import resolve_checklist
from ..llm import CompletionClient
from ..schemas import ChecklistItem, ReviewRequest, ReviewResponse


class MRTReviewService:
    """Business logic for single-pass MRT checklist reviews."""

    def __init__(self, llm_client: Optional[CompletionClient] = None):
        self.llm_client = llm_client or CompletionClient()

    def review(self, request: ReviewRequest) -> ReviewResponse:
        return self.review_with_checklist(request.mrt_content, request.checklist, request.system_prompt)

    def review_with_checklist(
        self,
        mrt_content: str,
        checklist_items: Optional[List[ChecklistItem]],
        system_prompt: Optional[str] = None,
    ) -> ReviewResponse:
        checklist = resolve_checklist(checklist_items)
        return self.llm_client.review(mrt_content, checklist, system_prompt)

