from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import httpx

from ..config import get_config

logger = logging.getLogger(__name__)


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
        url = f"{self.base_url}/{endpoint}"
        
        # Increase timeout for large requests
        timeout = httpx.Timeout(
            connect=30.0,
            read=self._config.llm_timeout,
            write=30.0,
            pool=30.0
        )
        
        # Log request details (without sensitive content)
        model = payload.get("model", "unknown")
        messages_count = len(payload.get("messages", []))
        logger.debug(f"HTTP request - URL: {url}, Model: {model}, Messages: {messages_count}")
        
        request_start = time.time()
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload, headers=headers)
                request_time = time.time() - request_start
                
                logger.debug(f"HTTP response received - Status: {response.status_code}, Time: {request_time:.2f}s")
                response.raise_for_status()
                
                result = response.json()
                logger.debug(f"Response parsed successfully - Size: {len(str(result))} chars")
                return result
                
        except httpx.TimeoutException as exc:
            request_time = time.time() - request_start
            logger.error(f"Request timeout after {request_time:.2f}s - Timeout limit: {self._config.llm_timeout}s")
            raise DashScopeError(f"请求超时：API响应时间超过 {self._config.llm_timeout} 秒。请尝试上传较小的文件或稍后重试。") from exc
        except httpx.ConnectError as exc:
            request_time = time.time() - request_start
            logger.error(f"Connection error after {request_time:.2f}s - {str(exc)}")
            raise DashScopeError(f"连接错误：无法连接到API服务器。请检查网络连接。") from exc
        except httpx.ReadError as exc:
            request_time = time.time() - request_start
            logger.error(f"Read error after {request_time:.2f}s - {str(exc)}")
            raise DashScopeError(f"读取错误：连接被重置。可能是文件太大或网络不稳定，请尝试上传较小的文件。") from exc
        except httpx.HTTPStatusError as exc:
            request_time = time.time() - request_start
            logger.error(f"HTTP error {exc.response.status_code} after {request_time:.2f}s - Response: {exc.response.text[:200]}")
            raise DashScopeError(f"HTTP错误 {exc.response.status_code}：{exc.response.text}") from exc

    @property
    def has_api_key(self) -> bool:
        """Check if API key is available."""
        return bool(self.api_key)

