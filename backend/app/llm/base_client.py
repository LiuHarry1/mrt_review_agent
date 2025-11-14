from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

from ..config import get_config


class DashScopeError(RuntimeError):
    """Raised when the DashScope API returns an error response."""


class BaseLLMClient:
    """Base client for DashScope API with common functionality."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        config=None,
    ):
        # self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.api_key = "sk-f256c03643e9491fb1ebc278dd958c2d"
        self.base_url = base_url.rstrip("/")
        self._config = config or get_config()

    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to DashScope API."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        # Increase timeout for large requests
        timeout = httpx.Timeout(
            connect=30.0,
            read=self._config.llm_timeout,
            write=30.0,
            pool=30.0
        )
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(f"{self.base_url}/{endpoint}", json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            raise DashScopeError(f"请求超时：API响应时间超过 {self._config.llm_timeout} 秒。请尝试上传较小的文件或稍后重试。") from exc
        except httpx.ConnectError as exc:
            raise DashScopeError(f"连接错误：无法连接到API服务器。请检查网络连接。") from exc
        except httpx.ReadError as exc:
            raise DashScopeError(f"读取错误：连接被重置。可能是文件太大或网络不稳定，请尝试上传较小的文件。") from exc
        except httpx.HTTPStatusError as exc:
            raise DashScopeError(f"HTTP错误 {exc.response.status_code}：{exc.response.text}") from exc

    @property
    def has_api_key(self) -> bool:
        """Check if API key is available."""
        return bool(self.api_key)

