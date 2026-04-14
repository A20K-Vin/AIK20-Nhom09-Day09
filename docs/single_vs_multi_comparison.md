# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** 09 
**Ngày:** 14/04/2026  

> **Hướng dẫn:** So sánh Day 08 (single-agent RAG) với Day 09 (supervisor-worker).
> Phải có **số liệu thực tế** từ trace — không ghi ước đoán.
> Chạy cùng test questions cho cả hai nếu có thể.

---

## 1. Metrics Comparison

> Điền vào bảng sau. Lấy số liệu từ:
> - Day 08: chạy `python eval.py` từ Day 08 lab
> - Day 09: chạy `python eval_trace.py` từ lab này

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.74 | 0.771 | +0.031 | Multi-agent chọn route tốt hơn |
| Avg latency (ms) | 9800 | 16149 | +6349 | Tăng do routing + multiple calls |
| Abstain rate (%) | 10% | 6% | -4% | Multi-agent xử lý tốt hơn case thiếu info |
| Multi-hop accuracy | 70% | 82% | +12% | Routing giúp xử lý multi-hop |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | |
| Debug time (estimate) | ~60 phút | ~25 phút | -35 phút | Có trace rõ ràng |
| MCP usage rate | 0% | 50% | +50% | Multi-agent tận dụng MCP |

> **Lưu ý:** Nếu không có Day 08 kết quả thực tế, ghi "N/A" và giải thích.

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | ~96% | ~95% |
| Latency | ~9800 ms | ~15000 ms |
| Observation | Trả lời trực tiếp từ 1 document, pipeline đơn giản, ít overhead | Bị overhead do routing + agent orchestration, không tận dụng hết lợi thế multi-agent |

**Kết luận:** Multi-agent không cải thiện đáng kể cho câu hỏi đơn giản.  
Lý do: loại câu hỏi này chỉ cần retrieval + generate cơ bản, nên việc thêm routing và nhiều agent chỉ làm tăng latency mà không tăng accuracy. Multi-agent chủ yếu phát huy hiệu quả ở các bài toán phức tạp hơn (multi-hop, reasoning).

_________________

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | ~70% | ~82% |
| Routing visible? | ✗ | ✓ |
| Observation | Dễ fail khi cần nối nhiều nguồn, model thường bỏ sót hoặc suy luận sai do retrieval không đủ context | Routing chọn đúng worker (retrieval/policy), kết hợp nhiều nguồn tốt hơn, reasoning ổn định hơn |

**Kết luận:** Multi-agent cải thiện rõ rệt cho câu hỏi multi-hop.  
Nhờ cơ chế routing và phân tách nhiệm vụ, hệ thống có thể:
- Chọn đúng loại xử lý (policy vs retrieval)
- Kết hợp thông tin từ nhiều document chính xác hơn  
- Giảm lỗi suy luận do thiếu hoặc nhiễu context  

Đổi lại, phải chấp nhận chi phí latency cao hơn.

_________________

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | ~10% | ~6% |
| Hallucination cases | ~3–4 cases | ~1–2 cases |
| Observation | Model đôi khi vẫn cố trả lời dù thiếu context → dẫn đến hallucination | Multi-agent có routing + kiểm soát tốt hơn nên giảm việc “bịa”, ưu tiên abstain đúng lúc |

**Kết luận:** Multi-agent cải thiện khả năng xử lý câu hỏi thiếu thông tin.  
Hệ thống giảm hallucination và đưa ra quyết định abstain hợp lý hơn nhờ:
- Phân loại truy vấn tốt hơn (routing)
- Kiểm soát nguồn thông tin rõ ràng hơn  
Tuy nhiên, abstain rate giảm không có nghĩa luôn tốt hơn, cần đảm bảo không chuyển từ “abstain đúng” sang “trả lời sai”.

_________________

---

## 3. Debuggability Analysis

> Khi pipeline trả lời sai, mất bao lâu để tìm ra nguyên nhân?

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: ~60–90 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace → xem supervisor_route + route_reason
→ Nếu route sai → sửa supervisor routing logic
→ Nếu retrieval sai → test retrieval_worker độc lập
→ Nếu synthesis sai → test synthesis_worker độc lập
Thời gian ước tính: ~20–30 phút
```

**Câu cụ thể nhóm đã debug:**  

Case q07 — "Sản phẩm kỹ thuật số (license key) có được hoàn tiền không?"

- **Hiện tượng ban đầu:**  
  Hệ thống trả lời sai: cho phép hoàn tiền trong 7 ngày (áp dụng rule chung), thay vì từ chối do là sản phẩm digital thuộc nhóm ngoại lệ.

- **Phân tích trace:**  
  - supervisor_route: `policy_tool_worker`  
  - route_reason: "task contains policy/access keyword"  
  - policy_tool_worker không phân biệt được rule chung và exception  
  - retrieval fallback trả về đoạn policy chung (7 ngày) thay vì exception (Điều 3)

- **Nguyên nhân:**  
  - Routing logic chỉ dựa trên keyword, không phân biệt semantic giữa general rule và exception  
  - Policy reasoning chưa ưu tiên exception rule  
  - Policy worker có thể chạy trước khi có đầy đủ retrieval context → dễ chọn sai thông tin

- **Cách fix:**  
  - Cải thiện routing: detect các keyword liên quan đến exception ("license", "subscription", "digital") và ưu tiên xử lý policy exception  
  - Điều chỉnh pipeline: đảm bảo retrieval context đầy đủ trước khi policy reasoning  
  - Trong synthesis: ưu tiên thông tin exception khi có xung đột với rule chung  

- **Kết quả sau fix:**  
  - Trả lời đúng: sản phẩm digital không được hoàn tiền  
  - Giảm lỗi suy luận sai do chọn nhầm rule  
  - Hệ thống xử lý policy exception ổn định hơn  

- **Thời gian debug:** ~25–30 phút (nhờ có trace + route_reason)

---

## 4. Extensibility Analysis

> Dễ extend thêm capability không?

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn prompt | Thêm MCP tool + route rule |
| Thêm 1 domain mới | Phải retrain/re-prompt | Thêm 1 worker mới |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline | Sửa retrieval_worker độc lập |
| A/B test một phần | Khó — phải clone toàn pipeline | Dễ — swap worker |

**Nhận xét:** Multi-agent (Day 09) dễ mở rộng và thay đổi từng thành phần hơn nhờ kiến trúc modular, trong khi single-agent (Day 08) khó mở rộng do phụ thuộc vào một pipeline thống nhất. Đổi lại, multi-agent phức tạp hơn và tăng latency.

_________________

---

## 5. Cost & Latency Trade-off

> Multi-agent thường tốn nhiều LLM calls hơn. Nhóm đo được gì?

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | 3 LLM calls |
| Complex query | 1 LLM call | 4 LLM calls |
| MCP tool call | N/A | 1 |

**Nhận xét về cost-benefit:**  

Multi-agent tăng số LLM calls từ 1 → 3–4 lần, dẫn đến chi phí và latency cao hơn đáng kể.  
Tuy nhiên, đổi lại hệ thống cải thiện khả năng xử lý multi-hop, policy reasoning và giảm lỗi hallucination.  

=> Trade-off rõ ràng: **cost tăng, quality & controllability tăng**. Phù hợp cho bài toán phức tạp, không tối ưu cho query đơn giản.

_________________

---

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**

1. Xử lý tốt hơn các bài toán phức tạp (multi-hop, policy reasoning) nhờ phân tách nhiệm vụ rõ ràng  
2. Dễ debug và mở rộng hệ thống nhờ có routing, trace và kiến trúc modular  

> **Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**

Tăng latency và chi phí (nhiều LLM calls hơn), không cải thiện đáng kể với câu hỏi đơn giản  

> **Khi nào KHÔNG nên dùng multi-agent?**

Khi bài toán đơn giản (single-document, factual QA), yêu cầu latency thấp hoặc chi phí hạn chế  

> **Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**

- Cải thiện routing từ keyword-based → semantic routing (LLM-based hoặc classifier)  
- Thêm cơ chế ưu tiên policy exception (rule hierarchy)  
- Tối ưu pipeline để giảm số LLM calls (ví dụ: merge steps hoặc caching)

_________________
