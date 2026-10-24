import unittest

from app.rag import retrieve_agent_knowledge
from app.workflow import build_graph
from app.prompts import CONVERSATION_PROMPT
from app.plan_document import build_generation_response


class LocalRag:
    async def retrieve(self, agent, query, limit=3):
        return retrieve_agent_knowledge(agent, query, limit)


class FakeModel:
    def __init__(self, allow_empty=False):
        self.retrieved_agents = []
        self.allow_empty = allow_empty

    async def json_completion(self, prompt, payload):
        if prompt == CONVERSATION_PROMPT:
            return {"intent": "plan"}
        if "rag_knowledge" in payload:
            knowledge = payload["rag_knowledge"]
            if not self.allow_empty:
                assert knowledge["results"], "No retrieved context before model invocation"
            assert "knowledge_references" in prompt
            self.retrieved_agents.append(knowledge["agent"])
        if "健身总规划" in prompt:
            return {"monthly_plan": [{"day": day, "type": "strength" if day % 2 else "cardio", "focus": "依据个人基础安排适度训练，注意动作控制和疲劳恢复，逐步建立规律。"} for day in range(1, 31)]}
        if "Harness Agent" in prompt:
            return {"suggestions": []}
        if "运动营养 Agent" in prompt:
            return {"knowledge_references": ["fake-source"], "nutrition_plan": [{"day": day, "meals": [{"name": name} for name in ("早餐", "午餐", "晚餐")]} for day in payload["target_days"]]}
        ids = [item["id"] for item in payload.get("rag_knowledge", {}).get("results", [])]
        required = payload.get("required_days", payload.get("pending_days", []))
        return {"revisions": [{"day": day, "sessions": [{"name": "模拟训练", "durationMinutes": 20}]} for day in required], "knowledge_references": ids[:1] + ["fake-source"]}


def initial_state():
    return {"goal": "减脂", "body": {"heightCm": 175, "weightKg": 70},
            "profile": {"trainingExperience": "BEGINNER", "dietaryRestrictions": "乳糖不耐受",
                        "weeklyTrainingDays": 3, "sessionDurationMinutes": 45, "availableTrainingTimes": "19:00",
                        "injuryOrMedicalNotes": "无", "averageSleepHours": 8}}


class WorkflowRetrievalTests(unittest.IsolatedAsyncioTestCase):
    async def test_each_specialist_receives_context_before_generation(self):
        model = FakeModel()
        graph = build_graph(model, LocalRag())
        result = await graph.ainvoke(initial_state())
        self.assertEqual(model.retrieved_agents, [agent for agent in ("strength", "endurance", "strength", "endurance", "nutrition") for _ in range(6)])
        self.assertEqual(len(result["nutrition_plan"]), 30)
        document = build_generation_response(result["goal"], result["profile"], result)["plan"]
        references = document["summary"]["knowledge_references"]
        self.assertTrue(references["strength"])
        self.assertEqual(references["nutrition"], [])
        self.assertNotIn("fake-source", str(references))

    async def test_retrieval_error_does_not_break_generation(self):
        class BrokenRag:
            async def retrieve(self, *args, **kwargs):
                raise RuntimeError("MCP unavailable")
        with self.assertLogs("app.workflow", level="WARNING"):
            result = await build_graph(FakeModel(allow_empty=True), BrokenRag()).ainvoke(initial_state())
        self.assertEqual(len(result["nutrition_plan"]), 30)
        self.assertEqual(result["knowledge_references"], {"strength": [], "endurance": [], "nutrition": []})

    async def test_cross_role_tool_response_is_not_sent_to_model(self):
        class WrongRoleRag:
            async def retrieve(self, agent, query, limit=3):
                return {"agent": agent, "results": [{"id": "other/private", "knowledgeBase": "other", "content": "must not reach model"}]}
        with self.assertLogs("app.workflow", level="WARNING"):
            result = await build_graph(FakeModel(allow_empty=True), WrongRoleRag()).ainvoke(initial_state())
        self.assertEqual(result["knowledge_references"], {"strength": [], "endurance": [], "nutrition": []})


if __name__ == "__main__":
    unittest.main()
