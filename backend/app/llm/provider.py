"""
LLM Provider definitions and base classes.
Supports multiple LLM providers with unified interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from ..config import get_config


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    QWEN = "qwen"  # Alibaba DashScope
    AZURE_OPENAI = "azure_openai"  # Azure OpenAI


class LLMError(RuntimeError):
    """Base exception for LLM API errors."""
    pass


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, api_key: Optional[str] = None, config=None):
        self.api_key = api_key or self._get_api_key()
        self._config = config or get_config()

    @abstractmethod
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment or config."""
        pass

    @abstractmethod
    def _get_base_url(self) -> str:
        """Get base URL for the API."""
        pass

    @abstractmethod
    def _get_model_name(self) -> str:
        """Get model name from config."""
        pass

    @abstractmethod
    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to LLM API."""
        pass

    @abstractmethod
    def _make_stream_request(self, endpoint: str, payload: Dict[str, Any]):
        """Make streaming HTTP request to LLM API. Returns generator of chunks."""
        pass

    @abstractmethod
    def _normalize_payload(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> Dict[str, Any]:
        """Normalize payload format for the specific provider."""
        pass

    @abstractmethod
    def _extract_response(self, data: Dict[str, Any]) -> str:
        """Extract response text from provider-specific response format."""
        pass

    @abstractmethod
    def _extract_stream_chunk(self, chunk_data: Dict[str, Any]) -> Optional[str]:
        """Extract text chunk from streaming response. Returns None if not a content chunk."""
        pass

    @property
    def has_api_key(self) -> bool:
        """Check if API key is available."""
        return bool(self.api_key)

    @property
    def model(self) -> str:
        """Get model name."""
        return self._get_model_name()


class QwenClient(BaseLLMClient):
    """Qwen (Alibaba DashScope) LLM client."""

    def _get_api_key(self) -> Optional[str]:
        import os
        return os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")

    def _get_base_url(self) -> str:
        return "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def _get_model_name(self) -> str:
        return self._config.llm_model

    def _normalize_payload(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> Dict[str, Any]:
        """Normalize payload for DashScope/Qwen API."""
        return {
            "model": model or self._get_model_name(),
            "messages": messages,
        }

    def _extract_response(self, data: Dict[str, Any]) -> str:
        """Extract response from DashScope/Qwen format."""
        return data.get("choices", [{}])[0].get("message", {}).get("content", "未能获取模型回复。")

    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to DashScope API."""
        import logging
        import time

        logger = logging.getLogger(__name__)
        headers = {"Authorization": f"Bearer {self.api_key}"}
        base_url = self._get_base_url()
        url = f"{base_url}/{endpoint}"

        timeout = httpx.Timeout(
            connect=30.0,
            read=self._config.llm_timeout,
            write=30.0,
            pool=30.0
        )

        model = payload.get("model", "unknown")
        messages_count = len(payload.get("messages", []))
        logger.debug(f"Qwen API request - URL: {url}, Model: {model}, Messages: {messages_count}")

        request_start = time.time()
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload, headers=headers)
                request_time = time.time() - request_start

                logger.debug(f"Qwen API response - Status: {response.status_code}, Time: {request_time:.2f}s")
                response.raise_for_status()

                result = response.json()
                logger.debug(f"Qwen response parsed successfully - Size: {len(str(result))} chars")
                return result

        except httpx.TimeoutException as exc:
            request_time = time.time() - request_start
            logger.error(f"Qwen API timeout after {request_time:.2f}s")
            raise LLMError(f"请求超时：API响应时间超过 {self._config.llm_timeout} 秒。") from exc
        except httpx.ConnectError as exc:
            request_time = time.time() - request_start
            logger.error(f"Qwen API connection error after {request_time:.2f}s: {str(exc)}")
            error_msg = str(exc)
            if "nodename" in error_msg or "not known" in error_msg:
                raise LLMError(
                    "网络连接错误：无法解析服务器地址。请检查网络连接和DNS设置。"
                ) from exc
            raise LLMError(f"连接错误：无法连接到AI服务。请检查网络连接。") from exc
        except httpx.HTTPStatusError as exc:
            request_time = time.time() - request_start
            logger.error(f"Qwen API HTTP error {exc.response.status_code}")
            raise LLMError(f"HTTP错误 {exc.response.status_code}：{exc.response.text[:200]}") from exc
        except Exception as exc:
            request_time = time.time() - request_start
            logger.error(f"Qwen API error after {request_time:.2f}s: {str(exc)}", exc_info=True)
            error_msg = str(exc)
            if "nodename" in error_msg or "not known" in error_msg or "getaddrinfo" in error_msg:
                raise LLMError(
                    "网络连接错误：无法解析服务器地址。请检查网络连接和DNS设置。"
                ) from exc
            raise LLMError(f"API错误：{error_msg}") from exc

    def _make_stream_request(self, endpoint: str, payload: Dict[str, Any]):
        """Make streaming HTTP request to DashScope API."""
        import logging
        import time

        logger = logging.getLogger(__name__)
        headers = {"Authorization": f"Bearer {self.api_key}"}
        base_url = self._get_base_url()
        url = f"{base_url}/{endpoint}"

        timeout = httpx.Timeout(
            connect=30.0,
            read=self._config.llm_timeout,
            write=30.0,
            pool=30.0
        )

        # Enable streaming
        payload = payload.copy()
        payload["stream"] = True

        logger.debug(f"Qwen streaming request - URL: {url}, Model: {payload.get('model', 'unknown')}")

        try:
            with httpx.Client(timeout=timeout) as client:
                with client.stream("POST", url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if line:
                            if line.startswith("data: "):
                                data_str = line[6:]  # Remove "data: " prefix
                                if data_str == "[DONE]":
                                    break
                                try:
                                    import json
                                    chunk_data = json.loads(data_str)
                                    content = self._extract_stream_chunk(chunk_data)
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    continue
                                except Exception as e:
                                    logger.warning(f"Error parsing stream chunk: {e}")
                                    continue
        except httpx.TimeoutException as exc:
            logger.error(f"Qwen streaming timeout: {str(exc)}")
            raise LLMError(f"请求超时：流式响应时间超过限制。") from exc
        except httpx.ConnectError as exc:
            logger.error(f"Qwen streaming connection error: {str(exc)}")
            error_msg = str(exc)
            if "nodename" in error_msg or "not known" in error_msg:
                raise LLMError(
                    "网络连接错误：无法解析服务器地址。请检查网络连接和DNS设置。"
                ) from exc
            raise LLMError(f"连接错误：无法连接到AI服务。请检查网络连接。") from exc
        except httpx.HTTPStatusError as exc:
            logger.error(f"Qwen streaming HTTP error {exc.response.status_code}: {str(exc)}")
            raise LLMError(f"HTTP错误 {exc.response.status_code}：{exc.response.text[:200]}") from exc
        except Exception as exc:
            logger.error(f"Qwen streaming error: {str(exc)}", exc_info=True)
            error_msg = str(exc)
            if "nodename" in error_msg or "not known" in error_msg or "getaddrinfo" in error_msg:
                raise LLMError(
                    "网络连接错误：无法解析服务器地址。请检查网络连接和DNS设置。"
                ) from exc
            raise LLMError(f"流式请求错误：{error_msg}") from exc

    def _extract_stream_chunk(self, chunk_data: Dict[str, Any]) -> Optional[str]:
        """Extract text chunk from Qwen streaming response."""
        if "choices" not in chunk_data or not chunk_data["choices"]:
            return None
        delta = chunk_data["choices"][0].get("delta", {})
        content = delta.get("content", "")
        return content if content else None


class AzureOpenAIClient(BaseLLMClient):
    """Azure OpenAI LLM client."""

    def _get_api_key(self) -> Optional[str]:
        import os
        return os.getenv("AZURE_OPENAI_API_KEY")

    def _get_base_url(self) -> str:
        import os
        base_url = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not base_url:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT environment variable is required for Azure OpenAI. "
                "Format: https://<resource-name>.openai.azure.com"
            )
        # Azure OpenAI uses different endpoint format
        return base_url.rstrip("/")

    def _get_model_name(self) -> str:
        # Azure OpenAI model name from config
        llm_config = self._config._config.get("llm", {})
        return llm_config.get("azure_model", llm_config.get("model", "gpt-4"))

    def _normalize_payload(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> Dict[str, Any]:
        """Normalize payload for Azure OpenAI API."""
        import os
        # Azure OpenAI uses deployment name, which might be different from model name
        deployment_name = model or self._get_model_name()
        
        # Azure OpenAI also needs API version
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        return {
            "model": deployment_name,
            "messages": messages,
            # Azure OpenAI specific parameters can be added here
        }

    def _extract_response(self, data: Dict[str, Any]) -> str:
        """Extract response from Azure OpenAI format."""
        return data.get("choices", [{}])[0].get("message", {}).get("content", "未能获取模型回复。")

    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to Azure OpenAI API."""
        import logging
        import os
        import time

        logger = logging.getLogger(__name__)
        
        # Azure OpenAI uses different header format
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        base_url = self._get_base_url()
        deployment_name = payload.get("model")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        # Azure OpenAI endpoint format: /openai/deployments/{deployment}/chat/completions?api-version={version}
        url = f"{base_url}/openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"

        timeout = httpx.Timeout(
            connect=30.0,
            read=self._config.llm_timeout,
            write=30.0,
            pool=30.0
        )

        messages_count = len(payload.get("messages", []))
        logger.debug(f"Azure OpenAI API request - URL: {url}, Deployment: {deployment_name}, Messages: {messages_count}")

        # Remove model from payload for Azure OpenAI (it's in the URL)
        request_payload = {k: v for k, v in payload.items() if k != "model"}

        request_start = time.time()
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=request_payload, headers=headers)
                request_time = time.time() - request_start

                logger.debug(f"Azure OpenAI API response - Status: {response.status_code}, Time: {request_time:.2f}s")
                response.raise_for_status()

                result = response.json()
                logger.debug(f"Azure OpenAI response parsed successfully")
                return result

        except httpx.TimeoutException as exc:
            request_time = time.time() - request_start
            logger.error(f"Azure OpenAI API timeout after {request_time:.2f}s")
            raise LLMError(f"请求超时：API响应时间超过 {self._config.llm_timeout} 秒。") from exc
        except httpx.HTTPStatusError as exc:
            request_time = time.time() - request_start
            logger.error(f"Azure OpenAI API HTTP error {exc.response.status_code}")
            raise LLMError(f"HTTP错误 {exc.response.status_code}：{exc.response.text[:200]}") from exc
        except Exception as exc:
            request_time = time.time() - request_start
            logger.error(f"Azure OpenAI API error after {request_time:.2f}s: {str(exc)}")
            raise LLMError(f"API错误：{str(exc)}") from exc

    def _make_stream_request(self, endpoint: str, payload: Dict[str, Any]):
        """Make streaming HTTP request to Azure OpenAI API."""
        import logging
        import os

        logger = logging.getLogger(__name__)
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        base_url = self._get_base_url()
        deployment_name = payload.get("model", self._get_model_name())
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        # Azure OpenAI endpoint format: /openai/deployments/{deployment}/chat/completions?api-version={version}
        url = f"{base_url}/openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"

        timeout = httpx.Timeout(
            connect=30.0,
            read=self._config.llm_timeout,
            write=30.0,
            pool=30.0
        )

        # Enable streaming
        request_payload = {k: v for k, v in payload.items() if k != "model"}
        request_payload["stream"] = True

        logger.debug(f"Azure OpenAI streaming request - URL: {url}, Deployment: {deployment_name}")

        try:
            with httpx.Client(timeout=timeout) as client:
                with client.stream("POST", url, json=request_payload, headers=headers) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if line:
                            if line.startswith("data: "):
                                data_str = line[6:]  # Remove "data: " prefix
                                if data_str == "[DONE]":
                                    break
                                try:
                                    import json
                                    chunk_data = json.loads(data_str)
                                    content = self._extract_stream_chunk(chunk_data)
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    continue
                                except Exception as e:
                                    logger.warning(f"Error parsing stream chunk: {e}")
                                    continue
        except Exception as exc:
            logger.error(f"Azure OpenAI streaming error: {str(exc)}")
            raise LLMError(f"流式请求错误：{str(exc)}") from exc

    def _extract_stream_chunk(self, chunk_data: Dict[str, Any]) -> Optional[str]:
        """Extract text chunk from Azure OpenAI streaming response."""
        if "choices" not in chunk_data or not chunk_data["choices"]:
            return None
        delta = chunk_data["choices"][0].get("delta", {})
        content = delta.get("content", "")
        return content if content else None


