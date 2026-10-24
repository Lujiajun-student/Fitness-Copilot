"""Local Markdown chunking and scope-filtered BM25 retrieval.

Indexing runs offline; selected chunks are subsequently sent to the generation
model by the workflow. Each role can access only its own public knowledge folder.
"""

import re
import math
import asyncio
import logging
import os
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any
from app.rag_index import load_role, windows


KNOWLEDGE_ROOT = Path(__file__).resolve().parents[1] / "knowledge"
ALLOWED_KNOWLEDGE_BASES = {"strength", "endurance", "nutrition"}


AGENT_SCOPES = {
    "strength": ("strength",),
    "endurance": ("endurance",),
    "nutrition": ("nutrition",),
}


def _tokens(text: str) -> list[str]:
    """English words and Chinese bigrams, preserving frequencies for BM25."""
    tokens = []
    for word in re.findall(r"[a-z0-9_]{2,}|[\u4e00-\u9fff]+", unicodedata.normalize("NFKC", text).lower()):
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


def _expanded_query(query):
    # Bilingual lexical bridge for Chinese user queries against English PDFs.
    terms = {"力量": "strength resistance training", "肌肥大": "hypertrophy", "增肌": "hypertrophy muscle",
             "组数": "sets volume", "频率": "frequency", "负荷": "load intensity", "深蹲": "squat",
             "有氧": "aerobic", "心肺": "cardiorespiratory", "恢复": "recovery fatigue rest",
             "减脂": "fat loss energy deficit", "蛋白质": "protein", "三餐": "meal dietary nutrition",
             "乳糖": "lactose", "睡眠": "sleep", "新手": "untrained novice beginner",
             "碳水": "carbohydrate", "久坐": "sedentary", "体能": "endurance"}
    return query + " " + " ".join(value for key, value in terms.items() if key in query)


def _recall(agent, query, limit):
    if agent not in ALLOWED_KNOWLEDGE_BASES:
        raise ValueError("只允许 strength、endurance 或 nutrition Agent 查询各自的知识库。")
    documents, parents = load_role(agent)
    for scope in AGENT_SCOPES[agent]:
        root = KNOWLEDGE_ROOT.resolve()
        scope_root = root / scope
        # Do not follow a role-directory junction or document symlink into another scope.
        if scope_root.resolve() != scope_root:
            continue
        for path in sorted(scope_root.glob("*.md")):
            if path.resolve().parent != scope_root:
                continue
            for parent in _chunks(path, scope):
                parent = {**parent, "tenant": "public", "reviewStatus": "project-rules"}
                parents[parent["id"]] = parent
                for number, child in enumerate(windows(parent["content"], 450, 80), 1):
                    documents.append({**parent, "id": parent["id"] + f"/c{number}", "parentId": parent["id"], "content": child})
    frequencies = [Counter(_tokens(d["title"] + " " + d["section"] + " " + d["content"])) for d in documents]
    lengths = [sum(f.values()) for f in frequencies]
    average = sum(lengths) / len(lengths) if lengths else 1
    terms = set(_tokens(_expanded_query(query)))
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
            # Separate lexical reranking feature (coverage), not a second BM25 call.
            coverage = len(terms.intersection(frequency)) / max(1, len(terms))
            ranked.append({**document, "score": round(score, 6), "rerankScore": round(math.log1p(score) + coverage, 6)})
    ranked.sort(key=lambda item: (-item["score"], item["id"]))
    return ranked[:max(50, limit * 5)], parents


def _assemble(agent, query, limit, candidates, parents, reranker, error=None):
    results, seen = [], set()
    for child in candidates:
        parent_id = child["parentId"]
        if parent_id in seen:
            continue
        parent = parents[parent_id]
        if parent.get("knowledgeBase") != agent or parent.get("tenant") != "public":
            raise ValueError("Invalid parent scope")
        seen.add(parent_id)
        results.append({**parent, "parentId": parent_id, "matchedChildId": child["id"],
                        "matchedChildContent": child["content"], "score": child["score"], "rerankScore": child["rerankScore"]})
        if len(results) >= limit:
            break
    return {"agent": agent, "query": query, "strategy": "parent-child-bm25-rerank", "topK": limit,
            "candidateCount": len(candidates), "reranker": reranker, "rerankError": error, "results": results}


def retrieve_agent_knowledge(agent: str, query: str, limit: int = 10) -> dict[str, Any]:
    """Offline lexical fallback and deterministic test entry point."""
    limit = max(1, min(int(limit), 10))
    candidates, parents = _recall(agent, query, limit)
    candidates.sort(key=lambda item: (-item["rerankScore"], item["id"]))
    return _assemble(agent, query, limit, candidates, parents, "lexical-fallback")


async def retrieve_with_rerank(agent: str, query: str, limit: int = 10, reranker=None):
    from app.cross_encoder import CrossEncoderClient, validate_scores

    limit = max(1, min(int(limit), 10))
    candidates, parents = await asyncio.to_thread(_recall, agent, query, limit)
    if not candidates:
        return _assemble(agent, query, limit, [], parents, "not-needed")
    if os.getenv("RAG_RERANK_PROVIDER", "cross-encoder") == "lexical":
        candidates.sort(key=lambda item: (-item["rerankScore"], item["id"]))
        return _assemble(agent, query, limit, candidates, parents, "lexical-fallback")
    try:
        if os.getenv("RAG_RERANK_PROVIDER", "cross-encoder") != "cross-encoder":
            raise ValueError("Unsupported reranker; LLM reranking has been removed")
        timeout = max(1, float(os.getenv("RAG_RERANK_TIMEOUT_SECONDS", "120")))
        scores = await asyncio.wait_for((reranker or CrossEncoderClient()).score_pairs(
            query, [item["title"] + "\n" + item["content"] for item in candidates]), timeout=timeout)
        scores = validate_scores(scores, len(candidates))
        # CrossEncoder logits may be negative: rank them, do not apply the former 0..100 gate.
        candidates = [{**item, "rerankScore": score} for item, score in zip(candidates, scores)]
        candidates.sort(key=lambda item: (-item["rerankScore"], -item["score"], item["id"]))
        return _assemble(agent, query, limit, candidates, parents, "cross-encoder")
    except Exception:
        logging.getLogger(__name__).warning("CrossEncoder unavailable for %s; lexical fallback", agent)
        candidates.sort(key=lambda item: (-item["rerankScore"], item["id"]))
        return _assemble(agent, query, limit, candidates, parents, "lexical-fallback", "cross-encoder-unavailable")
