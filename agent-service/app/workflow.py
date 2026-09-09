"""DeepSeek-powered LangGraph workflow with a strength/endurance debate loop."""

from copy import deepcopy
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
    risks: list[str]
    monthly_plan: list[dict[str, Any]]
    nutrition_plan: list[dict[str, Any]]


def _context(state: PlanState) -> dict[str, Any]:
    return {
        "goal": state["goal"],
        "body_measurement": state["body"],
        "profile": state.get("profile", {}),
        "training_history": state.get("training_history", []),
    }


def _apply_revisions(plan: list[dict[str, Any]], proposal: dict[str, Any]) -> list[dict[str, Any]]:
    result = deepcopy(plan)
    by_day = {item.get("day"): item for item in proposal.get("revisions", []) if isinstance(item, dict)}
    for item in result:
        revision = by_day.get(item.get("day"))
        if revision and isinstance(revision.get("sessions"), list):
            item["sessions"] = revision["sessions"]
    return result


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
        return {"planner": {"strategy": output.get("strategy", "循序渐进、恢复优先")}, "monthly_plan": plan, "debate_round": 0}

    async def strength_node(state: PlanState) -> PlanState:
        payload = {**_context(state), "monthly_plan": state["monthly_plan"], "previous_endurance_feedback": state.get("endurance_proposal", {})}
        output = await llm.json_completion(STRENGTH_PROMPT, payload)
        return {"strength_proposal": output, "monthly_plan": _apply_revisions(state["monthly_plan"], output)}

    async def endurance_node(state: PlanState) -> PlanState:
        payload = {**_context(state), "monthly_plan": state["monthly_plan"], "strength_feedback": state.get("strength_proposal", {})}
        output = await llm.json_completion(ENDURANCE_PROMPT, payload)
        return {"endurance_proposal": output, "monthly_plan": _apply_revisions(state["monthly_plan"], output), "debate_round": state.get("debate_round", 0) + 1}

    async def harness_node(state: PlanState) -> PlanState:
        output = await llm.json_completion(HARNESS_PROMPT, {**_context(state), "monthly_plan": state["monthly_plan"], "strength_feedback": state.get("strength_proposal", {}), "endurance_feedback": state.get("endurance_proposal", {})})
        risks = list(output.get("risks", [])) + _validate_plan(state["monthly_plan"])
        if risks or not output.get("approved", False):
            changes = "；".join(output.get("required_changes", [])) or "请降低训练强度并补充恢复日后重试。"
            raise RuntimeError("安全审核未通过：" + "；".join(risks or [changes]))
        return {"risks": []}

    async def nutrition_node(state: PlanState) -> PlanState:
        output = await llm.json_completion(NUTRITION_PROMPT, {**_context(state), "monthly_plan": state["monthly_plan"]})
        nutrition_plan = output.get("nutrition_plan")
        if not isinstance(nutrition_plan, list) or len(nutrition_plan) != 30:
            raise RuntimeError("饮食 Agent 未返回完整 30 天饮食计划。")
        return {"nutrition_plan": nutrition_plan, "planner": {**state["planner"], "estimated_calories": output.get("estimated_calories"), "daily_protein_g": output.get("daily_protein_g")}}

    def debate_route(state: PlanState) -> str:
        return "strength" if state.get("debate_round", 0) < 2 else "harness"

    graph = StateGraph(PlanState)
    graph.add_node("planner", planner_node)
    graph.add_node("strength", strength_node)
    graph.add_node("endurance", endurance_node)
    graph.add_node("harness", harness_node)
    graph.add_node("nutrition", nutrition_node)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "strength")
    graph.add_edge("strength", "endurance")
    graph.add_conditional_edges("endurance", debate_route, {"strength": "strength", "harness": "harness"})
    graph.add_edge("harness", "nutrition")
    graph.add_edge("nutrition", END)
    return graph.compile()


plan_graph = build_graph()
