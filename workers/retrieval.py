"""
workers/retrieval.py — Retrieval Worker
Sprint 2: Implement retrieval từ ChromaDB, trả về chunks + sources.

Input (từ AgentState):
    - task: câu hỏi cần retrieve
    - (optional) retrieved_chunks nếu đã có từ trước

Output (vào AgentState):
    - retrieved_chunks: list of {"text", "source", "score", "metadata"}
    - retrieved_sources: list of source filenames
    - worker_io_log: log input/output của worker này

Gọi độc lập để test:
    python workers/retrieval.py
"""

import os
import re
from pathlib import Path

# ─────────────────────────────────────────────
# Worker Contract (xem contracts/worker_contracts.yaml)
# Input:  {"task": str, "top_k": int = 3}
# Output: {"retrieved_chunks": list, "retrieved_sources": list, "error": dict | None}
# ─────────────────────────────────────────────

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 3
DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "docs"
_VECTOR_IMPORT_ERROR_REPORTED = False


def _get_embedding_fn():
    """
    Trả về embedding function.
    TODO Sprint 1: Implement dùng OpenAI hoặc Sentence Transformers.
    """
    # Option A: Sentence Transformers (offline, không cần API key)
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        def embed(text: str) -> list:
            return model.encode([text])[0].tolist()
        return embed
    except ImportError:
        pass

    # Option B: OpenAI (cần API key)
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        client = OpenAI(api_key=api_key)
        def embed(text: str) -> list:
            resp = client.embeddings.create(input=text, model="text-embedding-3-small")
            return resp.data[0].embedding
        return embed
    except Exception:
        pass

    # Fallback: random embeddings cho test (KHÔNG dùng production)
    import random
    def embed(text: str) -> list:
        return [random.random() for _ in range(384)]
    return embed


def _get_collection():
    """
    Kết nối ChromaDB collection.
    TODO Sprint 2: Đảm bảo collection đã được build từ Step 3 trong README.
    """
    import chromadb
    chroma_path = Path(__file__).resolve().parent.parent / "chroma_db"
    client = chromadb.PersistentClient(path=str(chroma_path))
    try:
        collection = client.get_collection("day09_docs")
    except Exception:
        # Auto-create nếu chưa có
        collection = client.get_or_create_collection(
            "day09_docs",
            metadata={"hnsw:space": "cosine"}
        )
        print(f"⚠️  Collection 'day09_docs' chưa có data. Chạy index script trong README trước.")
    return collection


def _load_local_docs() -> list:
    """Load raw docs for lexical fallback retrieval when vector DB is unavailable."""
    docs = []
    if not DOCS_DIR.exists():
        return docs

    for path in DOCS_DIR.glob("*.txt"):
        text = path.read_text(encoding="utf-8")
        docs.append({
            "source": path.name,
            "text": text,
        })
    return docs


def _keyword_overlap_score(query: str, text: str) -> float:
    """Simple lexical score to keep retrieval fully offline-capable."""
    q_tokens = set(re.findall(r"[a-zA-Z0-9_]+", query.lower()))
    if not q_tokens:
        return 0.0
    t_tokens = set(re.findall(r"[a-zA-Z0-9_]+", text.lower()))
    overlap = len(q_tokens & t_tokens)
    return overlap / len(q_tokens)


def _preferred_sources(query: str) -> list:
    q = query.lower()
    if any(k in q for k in ["p1", "sla", "ticket", "escalation", "incident"]):
        return ["sla_p1_2026.txt"]
    if any(k in q for k in ["hoàn tiền", "refund", "flash sale", "store credit", "license", "subscription"]):
        return ["policy_refund_v4.txt"]
    if any(k in q for k in ["access", "cấp quyền", "level", "admin", "contractor"]):
        return ["access_control_sop.txt"]
    if any(k in q for k in ["mật khẩu", "đăng nhập sai", "vpn", "helpdesk"]):
        return ["it_helpdesk_faq.txt"]
    if any(k in q for k in ["remote", "probation", "thử việc", "hr", "nghỉ phép"]):
        return ["hr_leave_policy.txt"]
    return []


def _retrieve_lexical(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    docs = _load_local_docs()
    preferred = set(_preferred_sources(query))
    scored = []
    for doc in docs:
        score = _keyword_overlap_score(query, doc["text"])
        if preferred and doc["source"] in preferred:
            score += 0.35
        if score <= 0:
            continue
        scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    chunks = []
    for score, doc in scored[:top_k]:
        chunks.append({
            "text": doc["text"][:1800],
            "source": doc["source"],
            "score": round(min(0.95, max(0.1, score)), 4),
            "metadata": {"retrieval": "lexical_fallback"},
        })
    return chunks


def retrieve_dense(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Dense retrieval: embed query → query ChromaDB → trả về top_k chunks.

    TODO Sprint 2: Implement phần này.
    - Dùng _get_embedding_fn() để embed query
    - Query collection với n_results=top_k
    - Format result thành list of dict

    Returns:
        list of {"text": str, "source": str, "score": float, "metadata": dict}
    """
    global _VECTOR_IMPORT_ERROR_REPORTED
    try:
        embed = _get_embedding_fn()
        query_embedding = embed(query)
        collection = _get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"]
        )

        chunks = []
        for doc, dist, meta in zip(
            results["documents"][0],
            results["distances"][0],
            results["metadatas"][0]
        ):
            meta = meta or {}
            chunks.append({
                "text": doc,
                "source": meta.get("source", "unknown"),
                "score": round(1 - dist, 4),  # cosine similarity
                "metadata": meta,
            })
        if chunks:
            return chunks
        return _retrieve_lexical(query, top_k=top_k)

    except Exception as e:
        if not _VECTOR_IMPORT_ERROR_REPORTED:
            print(f"⚠️  ChromaDB query failed, fallback lexical mode enabled: {e}")
            _VECTOR_IMPORT_ERROR_REPORTED = True
        return _retrieve_lexical(query, top_k=top_k)


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với retrieved_chunks và retrieved_sources
    """
    task = state.get("task", "")
    top_k = state.get("retrieval_top_k", DEFAULT_TOP_K)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])

    state["workers_called"].append(WORKER_NAME)

    # Log worker IO (theo contract)
    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "top_k": top_k},
        "output": None,
        "error": None,
    }

    try:
        chunks = retrieve_dense(task, top_k=top_k)

        sources = sorted({c["source"] for c in chunks})

        state["retrieved_chunks"] = chunks
        state["retrieved_sources"] = sources

        worker_io["output"] = {
            "chunks_count": len(chunks),
            "sources": sources,
            "retrieval_mode": chunks[0]["metadata"].get("retrieval", "dense") if chunks else "none",
        }
        state["history"].append(
            f"[{WORKER_NAME}] retrieved {len(chunks)} chunks from {sources}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "RETRIEVAL_FAILED", "reason": str(e)}
        state["retrieved_chunks"] = []
        state["retrieved_sources"] = []
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    # Ghi worker IO vào state để trace
    state.setdefault("worker_io_logs", []).append(worker_io)

    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Retrieval Worker — Standalone Test")
    print("=" * 50)

    test_queries = [
        "SLA ticket P1 là bao lâu?",
        "Điều kiện được hoàn tiền là gì?",
        "Ai phê duyệt cấp quyền Level 3?",
    ]

    for query in test_queries:
        print(f"\n▶ Query: {query}")
        result = run({"task": query})
        chunks = result.get("retrieved_chunks", [])
        print(f"  Retrieved: {len(chunks)} chunks")
        for c in chunks[:2]:
            print(f"    [{c['score']:.3f}] {c['source']}: {c['text'][:80]}...")
        print(f"  Sources: {result.get('retrieved_sources', [])}")

    print("\n✅ retrieval_worker test done.")
