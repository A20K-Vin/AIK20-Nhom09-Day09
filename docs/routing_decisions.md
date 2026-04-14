# Routing Decisions Log — Lab Day 09

**Nhóm:** Nhóm 09  
**Ngày:** 14/04/2026

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/`).
> 
> Mỗi entry phải có: task đầu vào → worker được chọn → route_reason → kết quả thực tế.

---

## Routing Decision #1

**Task đầu vào:**
> SLA xử lý ticket P1 là bao lâu?

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `task contains SLA/ticket keyword`  
**MCP tools được gọi:** Không có (needs_tool = false)  
**Workers called sequence:** retrieval_worker → synthesis_worker

**Kết quả thực tế:**
- final_answer (ngắn): SLA ticket P1: first response 15 phút, resolution 4 giờ, auto-escalate nếu không phản hồi trong 10 phút
- confidence: 0.79
- Correct routing? Yes

**Nhận xét:** Routing đúng. Task chứa keyword `sla` và `ticket` → rơi vào nhánh `retrieval_worker` đúng theo logic keyword matching trong `graph.py:117`. Không cần MCP tool vì đây là câu hỏi factual có thể trả lời từ KB. Latency cao bất thường (60 464ms) do lần chạy đầu LLM call mất nhiều thời gian, không phải lỗi routing.

**Trace:** `run_20260414_155714.json` (question_id: q01)

---

## Routing Decision #2

**Task đầu vào:**
> Store credit khi hoàn tiền có giá trị bao nhiêu so với tiền gốc?

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keyword`  
**MCP tools được gọi:** `search_kb(query="Store credit khi hoàn tiền...", top_k=3)`  
**Workers called sequence:** policy_tool_worker → synthesis_worker

**Kết quả thực tế:**
- final_answer (ngắn): Store credit có giá trị 110% so với số tiền hoàn gốc (Điều 5, policy_refund_v4)
- confidence: 0.82
- Correct routing? Yes

**Nhận xét:** Routing đúng. Task chứa từ `hoàn tiền` → match policy_keywords trong `graph.py:106-115`, route sang `policy_tool_worker` với `needs_tool=true`. MCP `search_kb` trả về chunk từ `policy_refund_v4.txt` với score 0.95 — đây là source đúng. Answer chính xác theo policy.

**Trace:** `run_20260414_160001.json` (question_id: q10)

---

## Routing Decision #3

**Task đầu vào:**
> Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keyword | risk_high flagged`  
**MCP tools được gọi:** `search_kb` → `check_access_permission(level=3, emergency=true)` → `get_ticket_info(P1-LATEST)`  
**Workers called sequence:** policy_tool_worker → synthesis_worker

**Kết quả thực tế:**
- final_answer (ngắn): Level 3 cần phê duyệt từ Line Manager + IT Admin + IT Security (3 approvers), KHÔNG có emergency bypass. Riêng escalation khẩn cấp: on-call IT Admin có thể cấp tạm thời max 24h nếu Tech Lead phê duyệt bằng lời
- confidence: 0.91
- Correct routing? Yes

**Nhận xét:** Routing đúng và đầy đủ. Task chứa `cấp quyền` + `khẩn cấp` → kích hoạt cả `policy_keywords` lẫn `risk_keywords` (`graph.py:111-121`). Supervisor set `risk_high=true` và `needs_tool=true`. Policy tool gọi 3 MCP tools riêng biệt để cross-check: KB search lấy policy text, `check_access_permission` xác nhận approver matrix, `get_ticket_info` lấy context ticket P1 đang active. Confidence 0.91 — cao nhất trong các run, do multi-source corroboration.

**Trace:** `run_20260414_152624.json`

---

## Routing Decision #4 (tuỳ chọn — bonus)

**Task đầu vào:**
> ERR-403-AUTH là lỗi gì và cách xử lý?

**Worker được chọn:** `human_review` (→ sau đó tiếp tục với `retrieval_worker`)  
**Route reason:** `unknown error code + risk_high → human review`

**Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**

Task chứa chuỗi `err-` → supervisor match `risk_keywords` ở `graph.py:111`, set `risk_high=true`. Kết hợp với `"err-" in task` ở điều kiện `graph.py:126-128` → route bị override sang `human_review`. HITL triggered (`hitl_triggered=true`), sau đó auto-approve và tiếp tục với `retrieval_worker`.

Tuy nhiên KB không có tài liệu về ERR-403-AUTH nên retrieval trả về 3 chunks không liên quan (score chỉ 0.7 đồng đều), confidence cuối chỉ 0.3, final_answer là "Không đủ thông tin trong tài liệu nội bộ."

**Routing này đúng hay sai?** Về kỹ thuật: đúng — mã lỗi không rõ nên HITL là hợp lý. Về thực tế: nếu có human in the loop thật sự, human có thể cung cấp context để trả lời. Vấn đề là KB thiếu tài liệu về error codes, không phải routing sai.

**Trace:** `run_20260414_155917.json` (question_id: q09)

---

## Tổng kết

### Routing Distribution

*(Tính trên 18 traces; trace human_review được đếm riêng dựa theo `hitl_triggered` vì sau approval `supervisor_route` bị ghi đè thành `retrieval_worker`)*

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 7 | 39% |
| policy_tool_worker | 10 | 55% |
| human_review | 1 | 6% |

### Routing Accuracy

> Trong số 18 câu nhóm đã chạy, bao nhiêu câu supervisor route đúng?

- Câu route đúng: 18 / 18
- Câu route sai (đã sửa bằng cách nào?): 0 — tất cả routing đều match đúng keyword rules trong `graph.py`
- Câu trigger HITL: 1 (ERR-403-AUTH, `run_20260414_155917`)

> **Lưu ý:** Routing đúng ≠ answer đúng. Run `run_20260414_150648` route đúng (`policy_tool_worker`) nhưng synthesis lỗi `[SYNTHESIS ERROR] Không thể gọi LLM` vì thiếu API key lúc chạy lần đầu. Sau khi fix env, các run sau cho answer đúng.

### Lesson Learned về Routing

> Quyết định kỹ thuật quan trọng nhất nhóm đưa ra về routing logic là gì?

1. **Keyword matching tầng double-check (policy + risk):** Supervisor dùng hai danh sách keyword độc lập — `policy_keywords` để quyết định worker, `risk_keywords` để flag `risk_high`. Điều này cho phép routing giữ nguyên worker (policy_tool_worker) nhưng vẫn bổ sung context risk để synthesis worker có thể cảnh báo user. Nếu chỉ dùng một danh sách, sẽ khó phân biệt "cần policy check" vs "cần human oversight".

2. **Policy worker luôn fallback sang retrieval nếu chunks rỗng:** Logic trong `graph.py:238-239` — sau khi policy_tool_worker chạy, nếu `retrieved_chunks` vẫn rỗng thì tiếp tục gọi `retrieval_worker_node`. Điều này tránh synthesis worker nhận input trống, đảm bảo luôn có ít nhất một nguồn để tổng hợp, dù confidence sẽ thấp.

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?  
> Nếu chưa, nhóm sẽ cải tiến format route_reason thế nào?

**Hiện tại:** Các `route_reason` khá ngắn gọn và đủ debug cơ bản:
- `"task contains policy/access keyword"` — biết *tại sao* nhưng không biết *keyword nào* match
- `"task contains SLA/ticket keyword | risk_high flagged"` — format pipe (`|`) khi có nhiều trigger là tốt

**Cải tiến đề xuất:** Thêm keyword đã match vào reason string:

```
route_reason = f"policy_keyword_matched='{matched_kw}' → policy_tool_worker"
# Ví dụ: "policy_keyword_matched='hoàn tiền' → policy_tool_worker"
```

Với format này, khi debug một trace sai, engineer có thể ngay lập tức biết keyword nào triggered routing mà không cần re-read toàn bộ task text, đặc biệt hữu ích khi task dài hoặc có nhiều keyword tiềm năng.
