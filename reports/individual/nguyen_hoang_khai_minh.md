# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Hoàng Khải Minh
**Vai trò trong nhóm:** Worker Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

> **Lưu ý quan trọng:**
> - Viết ở ngôi **"tôi"**, gắn với chi tiết thật của phần bạn làm
> - Phải có **bằng chứng cụ thể**: tên file, đoạn code, kết quả trace, hoặc commit
> - Nội dung phân tích phải khác hoàn toàn với các thành viên trong nhóm
> - Deadline: Được commit **sau 18:00** (xem SCORING.md)
> - Lưu file với tên: `reports/individual/[ten_ban].md` (VD: `nguyen_van_a.md`)

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

> Mô tả cụ thể module, worker, contract, hoặc phần trace bạn trực tiếp làm.
> Không chỉ nói "tôi làm Sprint X" — nói rõ file nào, function nào, quyết định nào.

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/retrieval.py`, `workers/policy_tool.py`, `workers/synthesis.py`
- Functions tôi implement: `retrieve_dense()`, `run()` (retrieval), `analyze_policy()`, `run()` (policy tool), `_deterministic_answer()`, `synthesize()`, `run()` (synthesis)

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Tôi chịu trách nhiệm toàn bộ lớp worker trong Sprint 2, nghĩa là biến routing quyết định từ supervisor thành hành động thật trong pipeline. Cụ thể, retrieval worker nhận `task` từ graph để lấy bằng chứng; policy tool worker kiểm tra ngoại lệ và gọi tool khi `needs_tool=True`; synthesis worker nhận kết quả trung gian để tạo câu trả lời cuối cùng có nguồn và confidence. Phần này kết nối trực tiếp với supervisor (Sprint 1) và trace/eval (Sprint 4): nếu output worker sai schema hoặc thiếu trường, cả graph và scoring đều bị ảnh hưởng. Vì vậy tôi bám chặt worker contract trong `contracts/worker_contracts.yaml`, giữ I/O nhất quán để các thành viên làm supervisor, MCP và docs có thể tích hợp mà không phải sửa tay logic phụ thuộc.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

- Commit Sprint 2: `955158fdeea5cc4a32406d1e7675abcc553ffc00`
- Các file worker có trong commit: `workers/retrieval.py`, `workers/policy_tool.py`, `workers/synthesis.py`
- Trong commit cũng có index liên quan retrieval: `index.py`, `chroma_db/chroma.sqlite3`

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Tôi chọn thiết kế retrieval theo hướng “dense-first, lexical-fallback” thay vì phụ thuộc hoàn toàn vào vector DB.

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:**

Khi triển khai Sprint 2, tôi thấy rủi ro lớn nhất là môi trường chạy không đồng nhất: có máy thiếu model embedding, có máy thiếu API key, hoặc collection Chroma chưa index đủ. Nếu retrieval chỉ có một đường chạy dense thì pipeline sẽ rơi vào fail-hard, làm supervisor route đúng nhưng downstream vẫn trả về rỗng. Vì vậy tôi tách retrieval thành hai lớp: (1) cố gắng dense retrieval qua Chroma (`retrieve_dense`), (2) nếu lỗi import/query hoặc không có kết quả thì fallback sang lexical bằng overlap từ khóa trên `data/docs/*.txt`. Đồng thời tôi thêm `_preferred_sources(query)` để boost theo domain (SLA, refund, access, FAQ, HR), giúp fallback không chỉ “chống chết” mà vẫn có định hướng nghiệp vụ.

Quyết định này tạo hiệu ứng thực tế: pipeline hoạt động ổn định hơn trong điều kiện offline/thiếu cấu hình, và vẫn trả được chunks có `source`, `score`, `metadata` đúng contract để synthesis dùng tiếp. Nó cũng giảm phụ thuộc vào một điểm lỗi duy nhất ở tầng vector store.

**Trade-off đã chấp nhận:**

Trade-off tôi chấp nhận là lexical fallback có thể kém chính xác ngữ nghĩa hơn dense embedding, nhất là câu hỏi paraphrase mạnh hoặc đa nghĩa. Để bù lại, tôi giới hạn fallback như “safety net”, không thay dense retrieval; đồng thời giữ score bảo thủ và ưu tiên nguồn theo intent để giảm nhiễu.

**Bằng chứng từ trace/code:**

```
# workers/retrieval.py
def retrieve_dense(query: str, top_k: int = DEFAULT_TOP_K) -> list:
	try:
		...
		if chunks:
			return chunks
		return _retrieve_lexical(query, top_k=top_k)
	except Exception as e:
		return _retrieve_lexical(query, top_k=top_k)

# workers/retrieval.py
def _preferred_sources(query: str) -> list:
	if any(k in q for k in ["p1", "sla", "ticket", "escalation", "incident"]):
		return ["sla_p1_2026.txt"]
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** Synthesis worker phụ thuộc quá cứng vào LLM, dẫn đến trả lỗi thay vì trả lời grounded khi thiếu API key.

**Symptom (pipeline làm gì sai?):**

Trong trace chạy thực tế, pipeline đi đúng route và worker trước đó chạy xong, nhưng đầu ra cuối cùng vẫn hỏng. Ở `artifacts/traces/run_20260414_150648.json`, trường `final_answer` là:
`[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env.`
Kèm theo đó `confidence` tụt về `0.1` dù task thuộc nhóm có thể trả lời bằng rule/evidence sẵn có.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Root cause nằm ở worker logic của synthesis: đường xử lý cũ coi LLM là nguồn bắt buộc cho answer generation, chưa có cơ chế degrade gracefully khi không có `OPENAI_API_KEY` hoặc `GOOGLE_API_KEY`. Nói cách khác, pipeline có evidence nhưng không có “engine dự phòng” để tổng hợp câu trả lời.

**Cách sửa:**

Tôi thêm deterministic synthesis path trong `workers/synthesis.py` với `_deterministic_answer()`, và chỉ gọi `_call_llm()` khi phát hiện có API key (`use_llm`). Nếu không có key hoặc call thất bại, worker tự tổng hợp theo rule từ chunks/policy_result rồi vẫn xuất `answer`, `sources`, `confidence` đúng contract. Cách này giữ pipeline luôn chạy được trong môi trường lab, đồng thời vẫn cho phép bật LLM khi có cấu hình đầy đủ.

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.

Trước khi sửa (trace):
- `final_answer`: `[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env.`
- `confidence`: `0.1`

Sau khi sửa (chạy `python workers/synthesis.py`):
- Answer test 1: `Ticket P1 có phản hồi ban đầu trong 15 phút và thời gian xử lý/khắc phục là 4 giờ. [sla_p1_2026.txt]`
- Sources: `['sla_p1_2026.txt']`
- Confidence: `0.92`

Kết quả cho thấy worker không còn fail-hard khi thiếu API key, và chất lượng đầu ra tăng rõ rệt.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

Điểm tôi làm tốt nhất là biến các worker thành khối độc lập, test được riêng và vẫn tích hợp trơn với graph. Tôi chú ý cả “happy path” lẫn “failure path”, nên pipeline chịu lỗi môi trường tốt hơn (thiếu key, lỗi vector query, dữ liệu chưa đầy đủ).

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Điểm còn yếu là tôi vẫn để một số rule ở policy/synthesis theo hướng heuristic, chưa chuẩn hóa bằng một lớp schema validator xuyên suốt cho mọi edge case. Ngoài ra, tôi cần viết thêm test tự động thay vì mới dừng ở standalone test thủ công.

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Nhóm phụ thuộc vào tôi ở toàn bộ đường dữ liệu sau routing: nếu worker chưa xong, supervisor chỉ route được mà không tạo ra `retrieved_chunks`, `policy_result`, `final_answer` đúng chuẩn; lúc đó trace/eval không thể chấm meaningful quality.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Tôi phụ thuộc vào supervisor owner ở route_reason/risk flags ổn định để worker vào đúng nhánh; phụ thuộc MCP owner ở độ tin cậy của tool output; và phụ thuộc trace/docs owner để phản hồi các lỗi quan sát được từ run thật nhằm tôi tinh chỉnh worker logic.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thêm một bước “evidence sufficiency check” ngay trong synthesis worker trước khi generate answer. Lý do: trace `run_20260414_150648` cho thấy `retrieved_chunks=[]` nhưng pipeline vẫn đi đến câu trả lời lỗi, chứng tỏ chưa có cơ chế chặn sớm khi evidence rỗng. Nếu thêm check này, worker có thể trả về dạng abstain chuẩn hóa ngay từ đầu, giúp confidence phản ánh đúng mức thiếu dữ liệu và giảm câu trả lời sai/ngẫu nhiên.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*
