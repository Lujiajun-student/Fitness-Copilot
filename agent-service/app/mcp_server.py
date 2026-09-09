"""MCP tools that provide the agent with read-only access to backend user data."""

import json
import os
import httpx
from mcp.server.fastmcp import FastMCP
from app.config import get_settings

mcp = FastMCP("fitness-backend-tools")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080").rstrip("/")


async def backend_get(path: str, access_token: str) -> dict | list:
    headers = {"Authorization": "Bearer " + access_token}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(BACKEND_URL + path, headers=headers)
    if response.status_code == 204 or not response.content:
        return {}
    response.raise_for_status()
    return response.json()


async def backend_post(path: str, access_token: str, payload: dict) -> dict:
    headers = {"Authorization": "Bearer " + access_token}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(BACKEND_URL + path, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


@mcp.tool()
async def get_current_user(access_token: str) -> str:
    """Return the authenticated user's account profile as JSON."""
    return json.dumps(await backend_get("/api/users/me", access_token), ensure_ascii=False)


@mcp.tool()
async def get_latest_body_measurement(access_token: str) -> str:
    """Return the authenticated user's latest body measurement as JSON."""
    return json.dumps(await backend_get("/api/body-measurements/latest", access_token), ensure_ascii=False)


@mcp.tool()
async def get_training_history(access_token: str) -> str:
    """Return up to 30 recent strength, cardio or recovery logs as JSON."""
    return json.dumps(await backend_get("/api/training-logs", access_token), ensure_ascii=False)


@mcp.tool()
def calculate_training_load(duration_minutes: int, perceived_exertion: int, average_heart_rate: int | None = None) -> str:
    """Calculate a transparent session load score from duration and RPE."""
    score = duration_minutes * perceived_exertion
    intensity = "低" if score < 120 else "中" if score < 300 else "高"
    if average_heart_rate and average_heart_rate >= 170:
        intensity = "高"
    return json.dumps({"loadScore": score, "intensity": intensity, "formula": "duration_minutes × perceived_exertion"}, ensure_ascii=False)


@mcp.tool()
def calculate_calorie_target(weight_kg: float, goal: str, activity_multiplier: float = 30.0) -> str:
    """Estimate a conservative daily calorie and protein target without medical diagnosis."""
    maintenance = round(weight_kg * activity_multiplier)
    calories = max(1200, maintenance - 350) if "减脂" in goal else maintenance + 200 if "增肌" in goal else maintenance
    return json.dumps({"maintenanceCalories": maintenance, "targetCalories": calories, "proteinTargetG": round(weight_kg * 1.6), "note": "这是通用估算，缺少年龄、性别和医学信息时应保守使用。"}, ensure_ascii=False)


@mcp.tool()
def search_food_nutrition(query: str) -> str:
    """Search a small curated food nutrition seed catalog by Chinese food name."""
    catalog = {"鸡胸肉": {"portion": "100 g", "calories": 133, "proteinG": 24}, "米饭": {"portion": "100 g", "calories": 116, "proteinG": 2.6}, "菠菜": {"portion": "100 g", "calories": 23, "proteinG": 2.9}, "燕麦": {"portion": "50 g", "calories": 190, "proteinG": 6.5}, "三文鱼": {"portion": "100 g", "calories": 208, "proteinG": 20}}
    matches = [{"name": name, **value} for name, value in catalog.items() if query.strip() in name or name in query.strip()]
    return json.dumps({"results": matches, "source": "seed catalog"}, ensure_ascii=False)


@mcp.tool()
def validate_plan_safety(days: list[dict], bmi: float | None = None) -> str:
    """Check a proposed daily plan for consecutive strength days and high-impact risk."""
    risks = []
    strength_streak = 0
    for day in days:
        if day.get("type") == "力量": strength_streak += 1
        else: strength_streak = 0
        if strength_streak >= 3: risks.append("连续 3 天力量训练，建议插入恢复日。")
    if bmi is not None and bmi >= 30 and any("跳" in str(day) or "冲刺" in str(day) for day in days): risks.append("BMI 较高时不建议安排跳跃或冲刺内容。")
    return json.dumps({"approved": not risks, "risks": risks, "recommendation": "通过" if not risks else "请先修改计划后重新校验"}, ensure_ascii=False)


@mcp.tool()
async def save_monthly_plan(access_token: str, goal: str, content: dict) -> str:
    """Persist an approved month-long training plan in the Java backend."""
    result = await backend_post("/api/plans/monthly", access_token, {"goal": goal, "content": content})
    return json.dumps({"planId": result["id"], "status": "saved"}, ensure_ascii=False)


@mcp.tool()
async def save_daily_nutrition_plan(access_token: str, plan_date: str, content: dict) -> str:
    """Persist one approved daily nutrition plan in the Java backend."""
    result = await backend_post("/api/plans/nutrition-daily", access_token, {"planDate": plan_date, "content": content})
    return json.dumps({"planId": result["id"], "status": "saved"}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
