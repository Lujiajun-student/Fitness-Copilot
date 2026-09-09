"""DeepSeek-powered LangGraph workflow with a strength/endurance debate loop."""

from copy import deepcopy
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.deepseek_client import DeepSeekClient
from app.prompts import ENDURANCE_PROMPT, HARNESS_PROMPT, NUTRITION_PROMPT, PLANNER_PROMPT, STRENGTH_PROMPT


class PlanState(TypedDict, total=False):
    goal: str
    body: dict[str, Any]
    profile: dict[str, Any]
    training_history: list[dict[str, Any]]
    planner: dict[str, Any]
    strength_proposal: dict[str, Any]
    endurance_proposal: dict[str, Any]
    debate_round: int
    safety_revision_round: int
    harness_approved: bool
    harness_feedback: dict[str, Any]
    risks: list[str]
    monthly_plan: list[dict[str, Any]]
    nutrition_plan: list[dict[str, Any]]


def _context(state: PlanState) -> dict[str, Any]:
    return {
        "goal": state["goal"],
        "body_measurement": state["body"],
        "profile": state.get("profile", {}),
        "training_history": state.get("training_history", []),
        "harness_feedback": state.get("harness_feedback", {}),
    }


def _apply_revisions(plan: list[dict[str, Any]], proposal: dict[str, Any]) -> list[dict[str, Any]]:
    result = deepcopy(plan)
    by_day = {item.get("day"): item for item in proposal.get("revisions", []) if isinstance(item, dict)}
    for item in result:
        revision = by_day.get(item.get("day"))
        if revision and isinstance(revision.get("sessions"), list):
            item["sessions"] = revision["sessions"]
    return result


def _start_minutes(profile: dict[str, Any]) -> int:
    """Use the first stated available time; retain 09:00 as an explicit fallback."""
    match = re.search(r"([01]?\d|2[0-3]):([0-5]\d)", str(profile.get("availableTrainingTimes") or ""))
    return int(match.group(1)) * 60 + int(match.group(2)) if match else 9 * 60


def _duration_minutes(session: dict[str, Any]) -> int:
    value = session.get("durationMinutes")
    if isinstance(value, (int, float)) and value > 0:
        return int(value)
    category = (str(session.get("category") or "") + " " + str(session.get("name") or "")).lower()
    sets = session.get("sets") if isinstance(session.get("sets"), (int, float)) else 0
    if "热身" in category or "warmup" in category or "拉伸" in category or "cooldown" in category:
        return 8
    if "有氧" in category or "cardio" in category or "快走" in category or "骑" in category:
        return 25
    if "恢复" in category or "休息" in category:
        return 20
    if "核心" in category or "core" in category:
        return max(8, int(sets) * 4)
    return max(10, int(sets) * 5) if sets else 12


def _time_label(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _schedule_plan(plan: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Make all exercise blocks sequential, rather than trusting repeated LLM time ranges."""
    scheduled = deepcopy(plan)
    for day in scheduled:
        cursor = _start_minutes(profile)
        normalized_sessions = []
        for raw_session in day.get("sessions", []):
            session = {"name": raw_session} if isinstance(raw_session, str) else raw_session
            duration = _duration_minutes(session)
            session["durationMinutes"] = duration
            session["timeRange"] = _time_label(cursor) + "–" + _time_label(cursor + duration)
            cursor += duration
            normalized_sessions.append(session)
        day["sessions"] = normalized_sessions
    return scheduled


def _validate_plan(plan: list[dict[str, Any]]) -> list[str]:
    risks: list[str] = []
    if len(plan) != 30:
        risks.append("训练计划必须覆盖完整 30 天。")
    for day in plan:
        if not day.get("sessions"):
            risks.append(f"第 {day.get('day', '?')} 天缺少具体训练安排。")
            break
    return risks


def build_graph(client: DeepSeekClient | None = None):
    llm = client or DeepSeekClient()

    async def planner_node(state: PlanState) -> PlanState:
        output = await llm.json_completion(PLANNER_PROMPT, _context(state))
        plan = output.get("monthly_plan")
        if not isinstance(plan, list):
            raise RuntimeError("总规划 Agent 未返回 monthly_plan。")
        return {"planner": {"strategy": output.get("strategy", "循序渐进、恢复优先")}, "monthly_plan": _schedule_plan(plan, state.get("profile", {})), "debate_round": 0}

    async def strength_node(state: PlanState) -> PlanState:
        payload = {**_context(state), "monthly_plan": state["monthly_plan"], "previous_endurance_feedback": state.get("endurance_proposal", {})}
        output = await llm.json_completion(STRENGTH_PROMPT, payload)
        return {"strength_proposal": output, "monthly_plan": _schedule_plan(_apply_revisions(state["monthly_plan"], output), state.get("profile", {}))}

    async def endurance_node(state: PlanState) -> PlanState:
        payload = {**_context(state), "monthly_plan": state["monthly_plan"], "strength_feedback": state.get("strength_proposal", {})}
        output = await llm.json_completion(ENDURANCE_PROMPT, payload)
        return {"endurance_proposal": output, "monthly_plan": _schedule_plan(_apply_revisions(state["monthly_plan"], output), state.get("profile", {})), "debate_round": state.get("debate_round", 0) + 1}

    async def harness_node(state: PlanState) -> PlanState:
        output = await llm.json_completion(HARNESS_PROMPT, {**_context(state), "monthly_plan": state["monthly_plan"], "strength_feedback": state.get("strength_proposal", {}), "endurance_feedback": state.get("endurance_proposal", {})})
        risks = list(output.get("risks", [])) + _validate_plan(state["monthly_plan"])
        approved = bool(output.get("approved", False)) and not risks
        feedback = {"risks": risks, "required_changes": output.get("required_changes", []) or ["请降低训练强度并补充恢复日后重试。"]}
        return {"risks": risks, "harness_approved": approved, "harness_feedback": feedback, "safety_revision_round": state.get("safety_revision_round", 0) + (0 if approved else 1)}

    async def nutrition_node(state: PlanState) -> PlanState:
        output = await llm.json_completion(NUTRITION_PROMPT, {**_context(state), "monthly_plan": state["monthly_plan"]})
        nutrition_plan = output.get("nutrition_plan")
        if not isinstance(nutrition_plan, list) or len(nutrition_plan) != 30:
            raise RuntimeError("饮食 Agent 未返回完整 30 天饮食计划。")
        return {"nutrition_plan": nutrition_plan, "planner": {**state["planner"], "estimated_calories": output.get("estimated_calories"), "daily_protein_g": output.get("daily_protein_g")}}

    def debate_route(state: PlanState) -> str:
        return "strength" if state.get("debate_round", 0) < 2 else "harness"

    def harness_route(state: PlanState) -> str:
        if state.get("harness_approved", False):
            return "nutrition"
        if state.get("safety_revision_round", 0) <= 2:
            return "planner"
        return "failed"

    def failed_node(state: PlanState) -> PlanState:
        feedback = state.get("harness_feedback", {})
        reasons = feedback.get("risks") or feedback.get("required_changes") or ["计划无法满足安全约束。"]
        raise RuntimeError("安全审核连续调整两次后仍未通过：" + "；".join(reasons))

    graph = StateGraph(PlanState)
    graph.add_node("planner", planner_node)
    graph.add_node("strength", strength_node)
    graph.add_node("endurance", endurance_node)
    graph.add_node("harness", harness_node)
    graph.add_node("failed", failed_node)
    graph.add_node("nutrition", nutrition_node)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "strength")
    graph.add_edge("strength", "endurance")
    graph.add_conditional_edges("endurance", debate_route, {"strength": "strength", "harness": "harness"})
    graph.add_conditional_edges("harness", harness_route, {"planner": "planner", "nutrition": "nutrition", "failed": "failed"})
    graph.add_edge("nutrition", END)
    graph.add_edge("failed", END)
    return graph.compile()


plan_graph = build_graph()
