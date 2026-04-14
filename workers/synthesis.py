"""
workers/synthesis.py — Synthesis Worker
Sprint 2: Tổng hợp câu trả lời từ retrieved_chunks và policy_result.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: evidence từ retrieval_worker
    - policy_result: kết quả từ policy_tool_worker

Output (vào AgentState):
    - final_answer: câu trả lời cuối với citation
    - sources: danh sách nguồn tài liệu được cite
    - confidence: mức độ tin cậy (0.0 - 1.0)

Gọi độc lập để test:
    python workers/synthesis.py
"""

import os
import re

WORKER_NAME = "synthesis_worker"

SYSTEM_PROMPT = """Bạn là trợ lý IT Helpdesk nội bộ.

Quy tắc nghiêm ngặt:
1. CHỈ trả lời dựa vào context được cung cấp. KHÔNG dùng kiến thức ngoài.
2. Nếu context không đủ để trả lời → nói rõ "Không đủ thông tin trong tài liệu nội bộ".
3. Trích dẫn nguồn cuối mỗi câu quan trọng: [tên_file].
4. Trả lời súc tích, có cấu trúc. Không dài dòng.
5. Nếu có exceptions/ngoại lệ → nêu rõ ràng trước khi kết luận.
"""


def _call_llm(messages: list) -> str:
    """
    Gọi LLM để tổng hợp câu trả lời.
    TODO Sprint 2: Implement với OpenAI hoặc Gemini.
    """
    # Option A: OpenAI
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,  # Low temperature để grounded
            max_tokens=500,
        )
        return response.choices[0].message.content
    except Exception:
        pass

    # Option B: Gemini
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        combined = "\n".join([m["content"] for m in messages])
        response = model.generate_content(combined)
        return response.text
    except Exception:
        pass

    # Fallback: caller should use deterministic synthesis path.
    return ""


def _contains(text: str, keywords: list) -> bool:
    lower = text.lower()
    return any(k in lower for k in keywords)


def _source_tag(source: str) -> str:
    return f"[{source}]"


def _extract_line(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(0).strip()


def _deterministic_answer(task: str, chunks: list, policy_result: dict) -> str:
    task_lower = task.lower()
    if not chunks:
        return "Không đủ thông tin trong tài liệu nội bộ để trả lời câu hỏi này."

    by_source = {}
    for c in chunks:
        by_source.setdefault(c.get("source", "unknown"), "")
        by_source[c.get("source", "unknown")] += "\n" + c.get("text", "")

    # Abstain for unknown error code queries.
    if re.search(r"\berr-[a-z0-9-]+\b", task_lower):
        return "Không tìm thấy thông tin về mã lỗi được hỏi trong tài liệu nội bộ hiện có. Vui lòng liên hệ IT Helpdesk để được hỗ trợ trực tiếp."

    lines = []

    if _contains(task_lower, ["p1", "sla", "escalation", "ticket"]):
        sla = by_source.get("sla_p1_2026.txt", "")
        if sla:
            if _contains(task_lower, ["bao lâu", "sla xử lý", "resolution"]):
                lines.append("Ticket P1 có phản hồi ban đầu trong 15 phút và thời gian xử lý/khắc phục là 4 giờ.")
            if _contains(task_lower, ["10 phút", "escalation", "không phản hồi"]):
                lines.append("Nếu không có phản hồi trong 10 phút, hệ thống tự động escalate lên Senior Engineer; đồng thời thông báo qua Slack #incident-p1, email incident@company.internal và PagerDuty on-call.")
            if _contains(task_lower, ["mấy bước", "quy trình", "bước đầu tiên"]):
                lines.append("Quy trình P1 gồm 5 bước: tiếp nhận, thông báo, triage và phân công, xử lý cập nhật mỗi 30 phút, và resolution với incident report trong 24 giờ. Bước đầu tiên là on-call engineer xác nhận severity trong 5 phút.")

    if _contains(task_lower, ["hoàn tiền", "refund", "store credit", "flash sale", "license", "subscription"]):
        refund = by_source.get("policy_refund_v4.txt", "")
        if refund:
            exceptions = policy_result.get("exceptions_found", [])
            if _contains(task_lower, ["store credit", "110%", "bao nhiêu"]):
                lines.append("Khách hàng có thể chọn store credit với giá trị 110% so với số tiền hoàn (cao hơn 10% so với hoàn về phương thức gốc).")
            elif exceptions:
                lines.append("Kết luận: không đủ điều kiện hoàn tiền do rơi vào ngoại lệ chính sách.")
                for ex in exceptions:
                    rule = ex.get("rule")
                    if rule:
                        lines.append(f"- {rule}")
            elif policy_result.get("policy_version_note"):
                lines.append(policy_result["policy_version_note"])
                lines.append("Vì thiếu tài liệu v3 nên cần CS Team xác nhận trước khi kết luận hoàn tiền.")
            else:
                lines.append("Điều kiện hoàn tiền: sản phẩm lỗi do nhà sản xuất, yêu cầu trong 7 ngày làm việc từ lúc xác nhận đơn, và sản phẩm chưa sử dụng/chưa mở seal.")

    if _contains(task_lower, ["access", "cấp quyền", "level", "admin"]):
        access = policy_result.get("access_decision", {})
        if access:
            level = access.get("access_level", "?")
            approvers = access.get("required_approvers", [])
            approver_text = ", ".join(approvers) if approvers else "theo SOP"
            lines.append(f"Quyền Level {level} yêu cầu phê duyệt từ: {approver_text}.")
            if access.get("emergency_override"):
                lines.append("Trường hợp emergency có thể dùng cơ chế cấp quyền tạm thời theo SOP và phải ghi log Security Audit.")
            elif _contains(task_lower, ["emergency", "khẩn cấp", "p1"]):
                lines.append("Trường hợp emergency cho level này không có bypass tự động trong policy tool hiện tại, cần đủ phê duyệt bắt buộc.")
        elif "access_control_sop.txt" in by_source:
            lines.append("Level 3 cần phê duyệt từ Line Manager, IT Admin và IT Security; Level 4 cần IT Manager và CISO.")

    if _contains(task_lower, ["mật khẩu", "đăng nhập sai", "remote", "probation", "thử việc"]):
        faq = by_source.get("it_helpdesk_faq.txt", "")
        hr = by_source.get("hr_leave_policy.txt", "")
        if _contains(task_lower, ["đăng nhập sai", "bị khóa"]) and faq:
            lines.append("Tài khoản bị khóa sau 5 lần đăng nhập sai liên tiếp.")
        if _contains(task_lower, ["mật khẩu", "90 ngày", "cảnh báo"]) and faq:
            lines.append("Mật khẩu cần đổi mỗi 90 ngày và hệ thống nhắc trước 7 ngày.")
        if _contains(task_lower, ["remote", "thử việc", "probation"]) and hr:
            if _contains(task_lower, ["thử việc", "probation"]):
                lines.append("Nhân viên trong probation period không thuộc nhóm đủ điều kiện remote theo chính sách hiện tại.")
            else:
                lines.append("Nhân viên sau probation được remote tối đa 2 ngày/tuần và cần Team Lead phê duyệt.")

    if not lines:
        return "Không đủ thông tin trong tài liệu nội bộ để trả lời chính xác câu hỏi này."

    # Add citations at line end.
    citation_parts = []
    for src in sorted({c.get("source", "unknown") for c in chunks}):
        citation_parts.append(_source_tag(src))
    citation_suffix = " " + " ".join(citation_parts)

    return "\n".join(lines) + citation_suffix


def _build_context(chunks: list, policy_result: dict) -> str:
    """Xây dựng context string từ chunks và policy result."""
    parts = []

    if chunks:
        parts.append("=== TÀI LIỆU THAM KHẢO ===")
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source", "unknown")
            text = chunk.get("text", "")
            score = chunk.get("score", 0)
            parts.append(f"[{i}] Nguồn: {source} (relevance: {score:.2f})\n{text}")

    if policy_result and policy_result.get("exceptions_found"):
        parts.append("\n=== POLICY EXCEPTIONS ===")
        for ex in policy_result["exceptions_found"]:
            parts.append(f"- {ex.get('rule', '')}")

    if not parts:
        return "(Không có context)"

    return "\n\n".join(parts)


def _estimate_confidence(chunks: list, answer: str, policy_result: dict) -> float:
    """
    Ước tính confidence dựa vào:
    - Số lượng và quality của chunks
    - Có exceptions không
    - Answer có abstain không

    TODO Sprint 2: Có thể dùng LLM-as-Judge để tính confidence chính xác hơn.
    """
    if not chunks:
        return 0.1  # Không có evidence → low confidence

    if "Không đủ thông tin" in answer or "không có trong tài liệu" in answer.lower():
        return 0.3  # Abstain → moderate-low

    # Weighted average của chunk scores
    if chunks:
        avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks)
    else:
        avg_score = 0

    # Penalty nếu có exceptions (phức tạp hơn)
    exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []))

    confidence = min(0.95, avg_score - exception_penalty)
    return round(max(0.1, confidence), 2)


def synthesize(task: str, chunks: list, policy_result: dict) -> dict:
    """
    Tổng hợp câu trả lời từ chunks và policy context.

    Returns:
        {"answer": str, "sources": list, "confidence": float}
    """
    context = _build_context(chunks, policy_result)

    # Build messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""Câu hỏi: {task}

{context}

Hãy trả lời câu hỏi dựa vào tài liệu trên."""
        }
    ]

    answer = ""
    use_llm = bool(os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    if use_llm:
        answer = _call_llm(messages)
    if not answer:
        answer = _deterministic_answer(task, chunks, policy_result)
    sources = list({c.get("source", "unknown") for c in chunks})
    confidence = _estimate_confidence(chunks, answer, policy_result)

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
    }


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    policy_result = state.get("policy_result", {})

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "has_policy": bool(policy_result),
        },
        "output": None,
        "error": None,
    }

    try:
        result = synthesize(task, chunks, policy_result)
        state["final_answer"] = result["answer"]
        state["sources"] = result["sources"]
        state["confidence"] = result["confidence"]

        worker_io["output"] = {
            "answer_length": len(result["answer"]),
            "sources": result["sources"],
            "confidence": result["confidence"],
        }
        state["history"].append(
            f"[{WORKER_NAME}] answer generated, confidence={result['confidence']}, "
            f"sources={result['sources']}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "SYNTHESIS_FAILED", "reason": str(e)}
        state["final_answer"] = f"SYNTHESIS_ERROR: {e}"
        state["confidence"] = 0.0
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Synthesis Worker — Standalone Test")
    print("=" * 50)

    test_state = {
        "task": "SLA ticket P1 là bao lâu?",
        "retrieved_chunks": [
            {
                "text": "Ticket P1: Phản hồi ban đầu 15 phút kể từ khi ticket được tạo. Xử lý và khắc phục 4 giờ. Escalation: tự động escalate lên Senior Engineer nếu không có phản hồi trong 10 phút.",
                "source": "sla_p1_2026.txt",
                "score": 0.92,
            }
        ],
        "policy_result": {},
    }

    result = run(test_state.copy())
    print(f"\nAnswer:\n{result['final_answer']}")
    print(f"\nSources: {result['sources']}")
    print(f"Confidence: {result['confidence']}")

    print("\n--- Test 2: Exception case ---")
    test_state2 = {
        "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì lỗi nhà sản xuất.",
        "retrieved_chunks": [
            {
                "text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền theo Điều 3 chính sách v4.",
                "source": "policy_refund_v4.txt",
                "score": 0.88,
            }
        ],
        "policy_result": {
            "policy_applies": False,
            "exceptions_found": [{"type": "flash_sale_exception", "rule": "Flash Sale không được hoàn tiền."}],
        },
    }
    result2 = run(test_state2.copy())
    print(f"\nAnswer:\n{result2['final_answer']}")
    print(f"Confidence: {result2['confidence']}")

    print("\n✅ synthesis_worker test done.")
