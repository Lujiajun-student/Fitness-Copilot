"""Small MCP client used by the LangGraph workflow."""

import asyncio
import json
import os
import sys
from typing import Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class BackendMcpClient:
    async def retrieve(self, agent: str, query: str, limit: int = 10) -> dict[str, Any]:
        if agent not in ("strength", "endurance", "nutrition"):
            raise ValueError("未知的知识库角色")
        params = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp_server"], env=dict(os.environ))
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as client:
                await client.initialize()
                result = await client.call_tool("retrieve_" + agent + "_knowledge", {"query": query, "limit": limit})
                return self._json_content(result)

    async def load_user_context(self, access_token: str) -> dict[str, Any]:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.mcp_server"],
            env=dict(os.environ),
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as client:
                await client.initialize()
                profile, measurement, training_history, monthly_plan = await asyncio.gather(
                    client.call_tool("get_current_user", {"access_token": access_token}),
                    client.call_tool("get_latest_body_measurement", {"access_token": access_token}),
                    client.call_tool("get_training_history", {"access_token": access_token}),
                    client.call_tool("get_current_monthly_plan", {"access_token": access_token}),
                )
                document = self._json_content(monthly_plan) or {}
                return {
                    "profile": self._json_content(profile),
                    "body_measurement": self._json_content(measurement),
                    "training_history": self._json_content(training_history),
                    "current_plan": document.get("content"),
                }

    @staticmethod
    def _json_content(result: Any) -> Any:
        if getattr(result, "isError", False):
            raise RuntimeError("MCP 工具调用失败")
        content = getattr(result, "content", [])
        if not content:
            return {}
        return json.loads(content[0].text)
