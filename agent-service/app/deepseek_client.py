"""Small, dependency-light client for DeepSeek's chat-completions endpoint."""

import json
from typing import Any
import httpx

from app.config import DeepSeekConfigurationError, Settings, get_settings


class DeepSeekClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def json_completion(self, system_prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.deepseek_configured:
            raise DeepSeekConfigurationError("未配置 DEEPSEEK_API_KEY；请在 agent-service/.env 中填写后重启服务。")
        request_body = {"model": self.settings.deepseek_model, "temperature": self.settings.deepseek_temperature, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]}
        headers = {"Authorization": f"Bearer {self.settings.deepseek_api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(f"{self.settings.deepseek_base_url}/chat/completions", headers=headers, json=request_body)
        if response.is_error:
            raise RuntimeError(f"DeepSeek 请求失败（HTTP {response.status_code}）：{response.text[:500]}")
        try:
            return json.loads(response.json()["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise RuntimeError("DeepSeek 未返回有效 JSON 计划。") from error
