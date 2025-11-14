from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .schemas import ChecklistItem


class Config:
    """Application configuration loader."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.getenv("MRT_REVIEW_CONFIG", str(Path(__file__).parent / "config.yaml"))
        self._config = self._load_config(config_path)
        self._default_checklist: Optional[List[ChecklistItem]] = None

    @staticmethod
    def _load_config(path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_file = Path(path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def system_prompt(self) -> str:
        """Get LLM system prompt."""
        return self._config.get("llm", {}).get("system_prompt", "你是专业的软件测试审查员。请根据检查清单对给定的手动回归测试进行审核，输出每条改进建议以及对应的 Checklist ID。")

    @property
    def llm_model(self) -> str:
        """Get LLM model name."""
        return self._config.get("llm", {}).get("model", "qwen-max")

    @property
    def llm_timeout(self) -> float:
        """Get LLM request timeout in seconds."""
        return float(self._config.get("llm", {}).get("timeout", 30.0))

    @property
    def default_checklist(self) -> List[ChecklistItem]:
        """Get default checklist items."""
        if self._default_checklist is None:
            items = self._config.get("default_checklist", [])
            self._default_checklist = [
                ChecklistItem(id=str(item["id"]), description=str(item["description"]))
                for item in items
                if isinstance(item, dict) and "id" in item and "description" in item
            ]
        return self._default_checklist

    @property
    def keyword_mapping(self) -> Dict[str, List[str]]:
        """Get keyword mapping for heuristic review."""
        mapping = self._config.get("keyword_mapping", {})
        result: Dict[str, List[str]] = {}
        for checklist_id, keywords in mapping.items():
            if isinstance(keywords, list):
                result[str(checklist_id)] = [str(kw) for kw in keywords]
        return result

    @property
    def additional_suggestions(self) -> List[Dict[str, Any]]:
        """Get additional suggestions configuration."""
        suggestions = self._config.get("additional_suggestions", [])
        result: List[Dict[str, Any]] = []
        for suggestion in suggestions:
            if isinstance(suggestion, dict) and "id" in suggestion and "keywords" in suggestion and "message" in suggestion:
                result.append({
                    "id": str(suggestion["id"]),
                    "keywords": [str(kw) for kw in suggestion["keywords"]] if isinstance(suggestion["keywords"], list) else [],
                    "message": str(suggestion["message"]),
                })
        return result


# Global configuration instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def reload_config(config_path: Optional[str] = None) -> Config:
    """Reload configuration from file."""
    global _config_instance
    _config_instance = Config(config_path)
    return _config_instance

