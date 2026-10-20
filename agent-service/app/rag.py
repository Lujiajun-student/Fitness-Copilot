"""Local Markdown chunking and scope-filtered BM25 retrieval.

Indexing runs offline; selected chunks are subsequently sent to the generation
model by the workflow. Role scopes include allowed shared subject documents.
"""

import re
import math
from collections import Counter
from pathlib import Path
from typing import Any


KNOWLEDGE_ROOT = Path(__file__).resolve().parents[1] / "knowledge"
ALLOWED_KNOWLEDGE_BASES = {"strength", "endurance", "nutrition"}


AGENT_SCOPES = {
    "strength": ("strength", "sports_training", "human_science"),
    "endurance": ("endurance", "sports_training", "human_science"),
    "nutrition": ("nutrition", "sports_nutrition", "human_science"),
}


def _tokens(text: str) -> list[str]:
    """English words and Chinese bigrams, preserving frequencies for BM25."""
    tokens = []
    for word in re.findall(r"[a-z0-9_]{2,}|[\u4e00-\u9fff]+", text.lower()):
        if re.search(r"[\u4e00-\u9fff]", word):
            tokens.extend(word[i:i + 2] for i in range(max(0, len(word) - 1)))
        else:
            tokens.append(word)
    return tokens


def _chunks(path: Path, scope: str) -> list[dict[str, Any]]:
    """Split Markdown by heading, then paragraphs with a bounded character size."""
    text = path.read_text(encoding="utf-8")
    source_match = re.search(r"^来源：(.+)$", text, re.MULTILINE)
    source = source_match.group(1).strip() if source_match else "项目内部规划规则（未经外部认证）"
    title_match = re.search(r"^# (.+)$", text, re.MULTILINE)
    title = title_match.group(1) if title_match else path.stem
    results = []
    section = title
    buffer = ""

    def emit():
        if buffer.strip():
            results.append({"id": f"{scope}/{path.stem}#{len(results) + 1}",
                            "knowledgeBase": scope, "title": title, "section": section,
                            "source": source, "content": buffer.strip()})

    for block in re.split(r"(\n?^#{1,6} .+$)", text, flags=re.MULTILINE):
        if block.strip().startswith("#"):
            emit()
            buffer = ""
            section = block.strip().lstrip("# ")
            continue
        for paragraph in re.split(r"\n\s*\n", block):
            paragraph = paragraph.strip()
            if not paragraph or paragraph.startswith(("来源：", "审核日期：")):
                continue
            for start in range(0, len(paragraph), 800):
                part = paragraph[start:start + 800]
                if len(buffer) + len(part) > 1000:
                    emit()
                    buffer = ""
                buffer += ("\n" if buffer else "") + part
    emit()
    return results


def retrieve_agent_knowledge(agent: str, query: str, limit: int = 3) -> dict[str, Any]:
    """Scope-filtered BM25 retrieval; never return unrelated zero-score chunks."""
    if agent not in ALLOWED_KNOWLEDGE_BASES:
        raise ValueError("只允许 strength、endurance 或 nutrition Agent 查询各自的知识库。")
    documents = []
    for scope in AGENT_SCOPES[agent]:
        for path in sorted((KNOWLEDGE_ROOT / scope).glob("*.md")):
            documents.extend(_chunks(path, scope))
    frequencies = [Counter(_tokens(d["title"] + " " + d["section"] + " " + d["content"])) for d in documents]
    lengths = [sum(f.values()) for f in frequencies]
    average = sum(lengths) / len(lengths) if lengths else 1
    terms = set(_tokens(query))
    document_frequency = Counter(term for f in frequencies for term in f)
    ranked = []
    for document, frequency, length in zip(documents, frequencies, lengths):
        score = 0.0
        for term in terms:
            count = frequency[term]
            if not count:
                continue
            idf = math.log(1 + (len(documents) - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            score += idf * count * 2.5 / (count + 1.5 * (0.25 + 0.75 * length / (average or 1)))
        if score > 0:
            ranked.append({**document, "score": round(score, 6)})
    ranked.sort(key=lambda item: (-item["score"], item["id"]))
    return {"agent": agent, "query": query, "strategy": "bm25", "results": ranked[:max(1, min(limit, 5))]}
