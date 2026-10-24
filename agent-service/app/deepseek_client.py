"""Small, dependency-light client for DeepSeek's chat-completions endpoint."""

import json
import logging
import re
from time import perf_counter
from typing import Any
import httpx

from app.config import DeepSeekConfigurationError, Settings, get_settings
from app.diagnostics import task_id, node_name

logger = logging.getLogger(__name__)


class DeepSeekResponseError(RuntimeError):
    """The provider response is incomplete or not a JSON object."""


class DeepSeekOutputTruncated(DeepSeekResponseError):
    """The provider explicitly reports hitting the output/context limit."""


def _usage(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else "-"


class DeepSeekClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def json_completion(self, system_prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.deepseek_configured:
            raise DeepSeekConfigurationError("未配置 DEEPSEEK_API_KEY；请在 agent-service/.env 中填写后重启服务。")
        started = perf_counter()
        node, task = node_name.get(), task_id.get()
        budget = self.settings.deepseek_planner_max_tokens if node == "planner" else self.settings.deepseek_max_tokens
        user_content = json.dumps(payload, ensure_ascii=False)
        request_body = {"model": self.settings.deepseek_model, "temperature": self.settings.deepseek_temperature,
                        "max_tokens": budget, "response_format": {"type": "json_object"},
                        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]}
        logger.info("llm_request task=%s node=%s model=%s max_tokens=%s input_chars=%s", task, node,
                    self.settings.deepseek_model, budget, len(system_prompt) + len(user_content))
        headers = {"Authorization": f"Bearer {self.settings.deepseek_api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(f"{self.settings.deepseek_base_url}/chat/completions", headers=headers, json=request_body)
        except httpx.HTTPError as error:
            logger.error("llm_transport_error task=%s node=%s error_type=%s elapsed_ms=%d", task, node,
                         type(error).__name__, (perf_counter() - started) * 1000)
            raise DeepSeekResponseError("DeepSeek 网络请求失败或超时。") from error
        if response.is_error:
            logger.error("llm_http_error task=%s node=%s http_status=%s elapsed_ms=%d", task, node,
                         response.status_code, (perf_counter() - started) * 1000)
            # Error bodies can echo prompts or credentials. Never include them in logs/exceptions.
            raise DeepSeekResponseError(f"DeepSeek 请求失败（HTTP {response.status_code}）。")
        try:
            data = response.json()
            choice = data["choices"][0]
            content = choice["message"]["content"]
            finish = choice.get("finish_reason")
            finish = finish if finish in ("stop", "length", "content_filter", "tool_calls", "insufficient_system_resource") else "unknown"
            usage = data.get("usage") or {}
            provider_id = data.get("id")
            provider_id = provider_id if isinstance(provider_id, str) and re.fullmatch(r"[\w.-]{1,128}", provider_id, re.ASCII) else "-"
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as error:
            logger.error("llm_envelope_error task=%s node=%s http_status=%s response_bytes=%s error_type=%s", task,
                         node, response.status_code, len(response.content), type(error).__name__)
            raise DeepSeekResponseError("DeepSeek 响应结构异常。") from error
        logger.info("llm_response task=%s node=%s provider_id=%s http_status=%s finish_reason=%s output_chars=%s prompt_tokens=%s completion_tokens=%s elapsed_ms=%d",
                    task, node, provider_id, response.status_code, finish, len(content) if isinstance(content, str) else 0,
                    _usage(usage.get("prompt_tokens")) if isinstance(usage, dict) else "-",
                    _usage(usage.get("completion_tokens")) if isinstance(usage, dict) else "-", (perf_counter() - started) * 1000)
        if finish == "length":
            logger.error("llm_output_truncated task=%s node=%s max_tokens=%s", task, node, budget)
            raise DeepSeekOutputTruncated("DeepSeek 输出被截断，请检查输出预算或缩减当前节点的输出内容。")
        if not isinstance(content, str) or not content.strip():
            logger.error("llm_empty_content task=%s node=%s", task, node)
            raise DeepSeekResponseError("DeepSeek 返回了空内容。")
        try:
            output = json.loads(content)
        except json.JSONDecodeError as error:
            logger.error("llm_json_error task=%s node=%s finish_reason=%s output_chars=%s line=%s column=%s position=%s",
                         task, node, finish, len(content), error.lineno, error.colno, error.pos)
            raise DeepSeekResponseError("DeepSeek 未返回有效 JSON。") from error
        if not isinstance(output, dict):
            logger.error("llm_json_type_error task=%s node=%s", task, node)
            raise DeepSeekResponseError("DeepSeek 返回的 JSON 必须为对象。")
        return output
