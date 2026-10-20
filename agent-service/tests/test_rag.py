import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import rag


class RetrievalTests(unittest.TestCase):
    def test_nutrition_retrieves_dietary_restrictions(self):
        result = rag.retrieve_agent_knowledge("nutrition", "乳糖不耐受 食物过敏 三餐 蛋白质")
        self.assertTrue(result["results"])
        self.assertTrue(any("乳糖不耐受" in d["content"] for d in result["results"]))
        self.assertTrue(all(d["knowledgeBase"] in rag.AGENT_SCOPES["nutrition"] for d in result["results"]))

    def test_strength_can_access_training_and_human_science(self):
        result = rag.retrieve_agent_knowledge("strength", "膝盖旧伤 关节疼痛")
        self.assertEqual(result["results"][0]["knowledgeBase"], "human_science")
        self.assertIn("source", result["results"][0])

    def test_no_match_and_invalid_agent(self):
        self.assertEqual(rag.retrieve_agent_knowledge("nutrition", "zzzznotfound")["results"], [])
        with self.assertRaises(ValueError):
            rag.retrieve_agent_knowledge("../../strength", "训练")

    def test_late_section_is_retrieved_without_prefix_truncation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "strength").mkdir()
            (root / "strength" / "long.md").write_text("# 文档\n\n## 起始\n\n" + "无关内容" * 500 + "\n\n## 目标\n\n独特哑铃调整建议", encoding="utf-8")
            with patch.object(rag, "KNOWLEDGE_ROOT", root):
                result = rag.retrieve_agent_knowledge("strength", "独特哑铃")
            self.assertIn("独特哑铃", result["results"][0]["content"])
            self.assertLessEqual(len(result["results"][0]["content"]), 1000)


if __name__ == "__main__":
    unittest.main()
