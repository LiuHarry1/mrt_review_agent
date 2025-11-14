from __future__ import annotations

from typing import List

from .config import get_config
from .schemas import ChecklistItem


def get_default_checklist() -> List[ChecklistItem]:
    """Get default checklist from configuration."""
    return get_config().default_checklist


def resolve_checklist(items):
    """Resolve checklist items, using default if none provided."""
    if not items:
        return get_default_checklist()
    return items
