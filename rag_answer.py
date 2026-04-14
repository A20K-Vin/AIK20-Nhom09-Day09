"""
rag_answer.py — Sprint 2 + Sprint 3: Retrieval & Grounded Answer
================================================================
Sprint 2 (60 phút): Baseline RAG
  - Dense retrieval từ ChromaDB
  - Grounded answer function với prompt ép citation
  - Trả lời được ít nhất 3 câu hỏi mẫu, output có source

Sprint 3 (60 phút): Tuning tối thiểu
  - Thêm hybrid retrieval (dense + sparse/BM25)
  - Hoặc thêm rerank (cross-encoder)
  - Hoặc thử query transformation (expansion, decomposition, HyDE)
  - Tạo bảng so sánh baseline vs variant

Definition of Done Sprint 2:
  ✓ rag_answer("SLA ticket P1?") trả về câu trả lời có citation
  ✓ rag_answer("Câu hỏi không có trong docs") trả về "Không đủ dữ liệu"

Definition of Done Sprint 3:
  ✓ Có ít nhất 1 variant (hybrid / rerank / query transform) chạy được
  ✓ Giải thích được tại sao chọn biến đó để tune
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

_cross_encoder = None  # cache cross-encoder model, tránh reload mỗi lần gọi

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


# =============================================================================
# RETRIEVAL — DENSE (Vector Search)
# =============================================================================

import chromadb
from index import get_embedding, CHROMA_DB_DIR 

def retrieve_dense(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")

    # 2. Embed câu hỏi của người dùng
    query_embedding = get_embedding(query)

    # 3. Query trong collection
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    # 4. Format lại kết quả trả về theo cấu trúc pipeline yêu cầu
    formatted_results = []
    if results['documents']:
        for i in range(len(results['documents'][0])):
            # Score = 1 - distance (giả sử dùng cosine similarity)
            score = 1 - results['distances'][0][i]
            formatted_results.append({
                "text": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "score": score
            })

    return formatted_results
from openai import OpenAI

def call_llm(prompt: str) -> str:
    # Lấy API Key từ file .env
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Thiếu OPENAI_API_KEY trong file .env")
        
    client = OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "Bạn là trợ lý học tập hỗ trợ sinh viên. Luôn trả lời trung thực dựa trên tài liệu được cung cấp."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,  # Giữ mức 0 để câu trả lời ổn định và không bị "hallucination"
        max_tokens=512,
    )
    
    return response.choices[0].message.content.strip()

def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
    }

    # --- Bước 1: Retrieve (Lấy dữ liệu) ---
    if retrieval_mode == "dense":
        candidates = retrieve_dense(query, top_k=top_k_search)
    else:
        # Tạm thời các mode khác fallback về dense trong Sprint 2
        candidates = retrieve_dense(query, top_k=top_k_search)

    # --- Bước 2: Rerank/Select (Lọc dữ liệu chất lượng nhất) ---
    # Sprint 2 lấy trực tiếp top_k_select kết quả đầu tiên
    selected_chunks = candidates[:top_k_select]

    # --- Bước 3: Build Context & Prompt ---
    # Sử dụng hàm build_context_block và build_grounded_prompt đã có sẵn trong file
    context_block = build_context_block(selected_chunks)
    prompt = build_grounded_prompt(query, context_block)

    if verbose:
        print(f"\n[RAG DEBUG] Query: {query}")
        print(f"[RAG DEBUG] Sources found: {[c['metadata'].get('source') for c in selected_chunks]}")

    # --- Bước 4: Generate (Sinh câu trả lời) ---
    answer = call_llm(prompt)

    # --- Bước 5: Extract Sources (Trích xuất nguồn để hiển thị) ---
    sources = list(set([c["metadata"].get("source", "unknown") for c in selected_chunks]))

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "chunks_used": selected_chunks,
        "config": config,
    }
# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: tìm kiếm theo keyword (BM25).

    Mạnh ở: exact term, mã lỗi, tên riêng (ví dụ: "ERR-403", "P1", "refund")
    Hay hụt: câu hỏi paraphrase, đồng nghĩa

    """
    import chromadb
    from rank_bm25 import BM25Okapi
    from index import CHROMA_DB_DIR

    # Load toàn bộ corpus từ ChromaDB (BM25 cần toàn bộ docs để build index)
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")
    all_data = collection.get(include=["documents", "metadatas"])

    corpus = all_data["documents"]
    metadatas = all_data["metadatas"]
    ids = all_data["ids"]

    if not corpus:
        return []

    tokenized_corpus = [doc.lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)

    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    return [
        {
            "text": corpus[i],
            "metadata": metadatas[i],
            "score": float(scores[i]),
            "id": ids[i],
        }
        for i in top_indices
        if scores[i] > 0
    ]


# =============================================================================
# RETRIEVAL — HYBRID (Dense + Sparse với Reciprocal Rank Fusion)
# =============================================================================

def retrieve_hybrid(
    query: str,
    top_k: int = TOP_K_SEARCH,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval: kết hợp dense và sparse bằng Reciprocal Rank Fusion (RRF).

    Mạnh ở: giữ được cả nghĩa (dense) lẫn keyword chính xác (sparse)
    Phù hợp khi: corpus lẫn lộn ngôn ngữ tự nhiên và tên riêng/mã lỗi/điều khoản

    Args:
        dense_weight: Trọng số cho dense score (0-1)
        sparse_weight: Trọng số cho sparse score (0-1)

    Khi nào dùng hybrid:
    - Corpus có cả câu tự nhiên VÀ tên riêng, mã lỗi, điều khoản
    - Query dùng alias/tên cũ ("Approval Matrix" → "Access Control SOP")
    """
    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

    # Reciprocal Rank Fusion — dùng text[:120] làm key dedup
    rrf_map: Dict[str, Any] = {}

    for rank, chunk in enumerate(dense_results):
        key = chunk["text"][:120]
        if key not in rrf_map:
            rrf_map[key] = {"chunk": chunk, "rrf": 0.0}
        rrf_map[key]["rrf"] += dense_weight * (1.0 / (60 + rank))

    for rank, chunk in enumerate(sparse_results):
        key = chunk["text"][:120]
        if key not in rrf_map:
            rrf_map[key] = {"chunk": chunk, "rrf": 0.0}
        rrf_map[key]["rrf"] += sparse_weight * (1.0 / (60 + rank))

    sorted_items = sorted(rrf_map.values(), key=lambda x: x["rrf"], reverse=True)

    results = []
    for item in sorted_items[:top_k]:
        chunk = dict(item["chunk"])
        chunk["score"] = round(item["rrf"], 6)
        results.append(chunk)
    return results


# =============================================================================
# RERANK (Sprint 3 alternative)
# Cross-encoder để chấm lại relevance sau search rộng
# =============================================================================

def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:
    """
    Rerank các candidate chunks bằng cross-encoder.

    Cross-encoder: chấm lại "chunk nào thực sự trả lời câu hỏi này?"
    MMR (Maximal Marginal Relevance): giữ relevance nhưng giảm trùng lặp

    Funnel logic (từ slide):
      Search rộng (top-20) → Rerank (top-6) → Select (top-3)

    Dùng cross-encoder/ms-marco-MiniLM-L-6-v2.
    Khi nào dùng: dense/hybrid trả nhiều chunk có noise,
    muốn chắc chắn chỉ top_k tốt nhất vào prompt.
    """
    if not candidates:
        return []

    try:
        global _cross_encoder
        if _cross_encoder is None:
            from sentence_transformers import CrossEncoder
            _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

        pairs = [[query, str(chunk.get("text", ""))] for chunk in candidates]
        scores = _cross_encoder.predict(pairs)
        ranked = sorted(zip(candidates, scores), key=lambda x: float(x[1]), reverse=True)

        results = []
        for chunk, score in ranked[:top_k]:
            chunk = dict(chunk)
            chunk["rerank_score"] = float(score)
            results.append(chunk)
        return results
    except Exception as e:
        print(f"[rerank] Cross-encoder lỗi ({e}), fallback về top_{top_k}")
        return candidates[:top_k]


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng recall.

    Strategies:
      - "expansion": Thêm từ đồng nghĩa, alias, tên cũ
      - "decomposition": Tách query phức tạp thành 2-3 sub-queries
      - "hyde": Sinh câu trả lời giả (hypothetical document) để embed thay query

    Khi nào dùng:
    - expansion: query dùng alias/tên cũ ("Approval Matrix" → "Access Control SOP")
    - decomposition: query hỏi nhiều thứ cùng lúc
    - hyde: query mơ hồ, search theo nghĩa không hiệu quả
    """
    import json

    prompts = {
        "expansion": (
            f"Given this query: '{query}'\n"
            "Generate 2-3 alternative phrasings or related Vietnamese terms "
            "that would help find the same information.\n"
            "Output ONLY a JSON array of strings, no explanation."
        ),
        "decomposition": (
            f"Break this complex query into 2-3 simpler sub-queries: '{query}'\n"
            "Output ONLY a JSON array of strings, no explanation."
        ),
        "hyde": (
            f"Write a short hypothetical document excerpt (2-3 sentences in Vietnamese) "
            f"that would directly answer this question: '{query}'\n"
            "Output ONLY a JSON array with one string."
        ),
    }

    prompt_text = prompts.get(strategy, prompts["expansion"])
    try:
        raw = call_llm(prompt_text).strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines).strip()

        try:
            variants = json.loads(raw)
        except Exception:
            # Fallback: model đôi khi thêm text ngoài JSON array
            start = raw.find("[")
            end = raw.rfind("]")
            if start == -1 or end <= start:
                raise
            variants = json.loads(raw[start:end + 1])

        if isinstance(variants, list) and variants:
            base_query = query.strip()
            seen = {base_query.lower()}
            normalized = []

            for v in variants:
                item = str(v).strip()
                if not item:
                    continue
                key = item.lower()
                if key in seen:
                    continue
                seen.add(key)
                normalized.append(item)
                if len(normalized) >= 3:
                    break

            if normalized:
                return [base_query] + normalized
    except Exception:
        pass
    return [query]


# =============================================================================
# GENERATION — GROUNDED ANSWER FUNCTION
# =============================================================================

def build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """
    Đóng gói danh sách chunks thành context block để đưa vào prompt.

    Format: structured snippets với source, section, score (từ slide).
    Mỗi chunk có số thứ tự [1], [2], ... để model dễ trích dẫn.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "unknown")
        section = meta.get("section", "")
        score = chunk.get("score", 0)
        text = chunk.get("text", "")

        # TODO: Tùy chỉnh format nếu muốn (thêm effective_date, department, ...)
        header = f"[{i}] {source}"
        if section:
            header += f" | {section}"
        if score > 0:
            header += f" | score={score:.2f}"

        context_parts.append(f"{header}\n{text}")

    return "\n\n".join(context_parts)


def build_grounded_prompt(query: str, context_block: str) -> str:
    """
    Xây dựng grounded prompt theo 4 quy tắc từ slide:
    1. Evidence-only: Chỉ trả lời từ retrieved context
    2. Abstain: Thiếu context thì nói không đủ dữ liệu
    3. Citation: Gắn source/section khi có thể
    4. Short, clear, stable: Output ngắn, rõ, nhất quán

    TODO Sprint 2:
    Đây là prompt baseline. Trong Sprint 3, bạn có thể:
    - Thêm hướng dẫn về format output (JSON, bullet points)
    - Thêm ngôn ngữ phản hồi (tiếng Việt vs tiếng Anh)
    - Điều chỉnh tone phù hợp với use case (CS helpdesk, IT support)
    """
    prompt = f"""Answer ONLY using the retrieved context below. Do NOT use any outside knowledge.
If the context does not contain enough information to answer, respond exactly with: "Không đủ dữ liệu để trả lời."
Cite the source number in brackets like [1] whenever you use information from that source.
Keep your answer short, clear, and factual.
Respond in the same language as the question.

Question: {query}

Context:
{context_block}

Answer:"""
    return prompt


def call_llm(prompt: str) -> str:
    """
    Gọi LLM để sinh câu trả lời.

    TODO Sprint 2:
    Chọn một trong hai:

    Chọn provider qua biến môi trường LLM_PROVIDER:
      - "openai"  (mặc định): dùng gpt-4o-mini, cần OPENAI_API_KEY
      - "gemini"             : dùng gemini-1.5-flash, cần GOOGLE_API_KEY
    Dùng temperature=0 để output ổn định cho evaluation.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0, "max_output_tokens": 512},
        )
        return response.text
    else:  # openai
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        return response.choices[0].message.content


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    query_transform: Optional[str] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → retrieve → (rerank) → generate.

    Args:
        query: Câu hỏi
        retrieval_mode: "dense" | "sparse" | "hybrid"
        top_k_search: Số chunk lấy từ vector store (search rộng)
        top_k_select: Số chunk đưa vào prompt (sau rerank/select)
        use_rerank: Có dùng cross-encoder rerank không
        verbose: In thêm thông tin debug

    Returns:
        Dict with:
          - "answer": câu trả lời grounded
          - "sources": list source names trích dẫn
          - "chunks_used": list chunks đã dùng
          - "query": query gốc
          - "config": cấu hình pipeline đã dùng

    TODO Sprint 2 — Implement pipeline cơ bản:
    1. Chọn retrieval function dựa theo retrieval_mode
    2. Gọi rerank() nếu use_rerank=True
    3. Truncate về top_k_select chunks
    4. Build context block và grounded prompt
    5. Gọi call_llm() để sinh câu trả lời
    6. Trả về kết quả kèm metadata

    TODO Sprint 3 — Thử các variant:
    - Variant A: đổi retrieval_mode="hybrid"
    - Variant B: bật use_rerank=True
    - Variant C: thêm query transformation trước khi retrieve
    """
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
        "query_transform": query_transform,
    }

    # --- Bước 0: Query transformation (Sprint 3 variant C) ---
    queries = [query]
    if query_transform:
        queries = transform_query(query, strategy=query_transform)
        if verbose:
            print(f"[RAG] Query transform ({query_transform}): {queries}")

    def _retrieve(q: str) -> List[Dict[str, Any]]:
        if retrieval_mode == "dense":
            return retrieve_dense(q, top_k=top_k_search)
        elif retrieval_mode == "sparse":
            return retrieve_sparse(q, top_k=top_k_search)
        elif retrieval_mode == "hybrid":
            return retrieve_hybrid(q, top_k=top_k_search)
        else:
            raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")

    # --- Bước 1: Retrieve (hợp nhất kết quả nếu có nhiều queries) ---
    if len(queries) == 1:
        candidates = _retrieve(queries[0])
    else:
        seen: Dict[str, Any] = {}
        for q in queries:
            for chunk in _retrieve(q):
                key = chunk["text"][:120]
                if key not in seen or chunk["score"] > seen[key]["score"]:
                    seen[key] = chunk
        candidates = sorted(seen.values(), key=lambda c: c["score"], reverse=True)[:top_k_search]

    if verbose:
        print(f"\n[RAG] Query: {query}")
        print(f"[RAG] Retrieved {len(candidates)} candidates (mode={retrieval_mode})")
        for i, c in enumerate(candidates[:3]):
            print(f"  [{i+1}] score={c.get('score', 0):.4f} | {c['metadata'].get('source', '?')}")

    # --- Bước 2: Rerank (optional) ---
    if use_rerank:
        candidates = rerank(query, candidates, top_k=top_k_select)
    else:
        candidates = candidates[:top_k_select]

    if verbose:
        print(f"[RAG] After select: {len(candidates)} chunks")

    # --- Bước 3: Build context và prompt ---
    context_block = build_context_block(candidates)
    prompt = build_grounded_prompt(query, context_block)

    if verbose:
        print(f"\n[RAG] Prompt:\n{prompt[:500]}...\n")

    # --- Bước 4: Generate ---
    answer = call_llm(prompt)

    # --- Bước 5: Extract sources ---
    sources = list({
        c["metadata"].get("source", "unknown")
        for c in candidates
    })

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "chunks_used": candidates,
        "config": config,
    }


# =============================================================================
# SPRINT 3: SO SÁNH BASELINE VS VARIANT
# =============================================================================

def compare_retrieval_strategies(query: str) -> None:
    """
    So sánh các retrieval strategies with cùng một query.

    TODO Sprint 3:
    Chạy hàm này để thấy sự khác biệt giữa dense, sparse, hybrid.
    Dùng để justify tại sao chọn variant đó cho Sprint 3.

    A/B Rule (từ slide): Chỉ đổi MỘT biến mỗi lần.
    """
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    strategies = ["dense", "sparse", "hybrid"]

    for strategy in strategies:
        print(f"\n--- Strategy: {strategy} ---")
        try:
            result = rag_answer(query, retrieval_mode=strategy, verbose=False)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError as e:
            print(f"Chưa implement: {e}")
        except Exception as e:
            print(f"Lỗi: {e}")


# =============================================================================
# MAIN — Demo và Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 60)

    # Test queries từ data/test_questions.json
    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "ERR-403-AUTH là lỗi gì?",  # Query không có trong docs → kiểm tra abstain
    ]

    print("\n--- Sprint 2: Test Baseline (Dense) ---")
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            result = rag_answer(query, retrieval_mode="dense", verbose=True)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError:
            print("Chưa implement — hoàn thành TODO trong retrieve_dense() và call_llm() trước.")
        except Exception as e:
            print(f"Lỗi: {e}")

    print("\n--- Sprint 3: So sánh strategies ---")
    compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")
    compare_retrieval_strategies("ERR-403-AUTH")

    print("\n\nViệc cần làm Sprint 2:")
    print("  1. Implement retrieve_dense() — query ChromaDB")
    print("  2. Implement call_llm() — gọi OpenAI hoặc Gemini")
    print("  3. Chạy rag_answer() với 3+ test queries")
    print("  4. Verify: output có citation không? Câu không có docs → abstain không?")

    print("\nViệc cần làm Sprint 3:")
    print("  1. Chọn 1 trong 3 variants: hybrid, rerank, hoặc query transformation")
    print("  2. Implement variant đó")
    print("  3. Chạy compare_retrieval_strategies() để thấy sự khác biệt")
    print("  4. Ghi lý do chọn biến đó vào docs/tuning-log.md")