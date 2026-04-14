# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** Nhóm 09  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Nguyễn Triệu Gia Khánh | Supervisor Owner | ___ |
| Nguyễn Hoàng Khải Minh | Worker Owner | ___ |
| Nguyễn Hoàng Duy | MCP Owner | ___ |
| Diệu Linh, Thùy Linh | Trace & Docs Owner | ___ |

**Ngày nộp:** 14/04/2026  
**Repo:** https://github.com/A20K-Vin/AIK20-Nhom09-Day09.git
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Hướng dẫn nộp group report:**
> 
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code/trace** — không mô tả chung chung
> - Mỗi mục phải có ít nhất 1 ví dụ cụ thể từ code hoặc trace thực tế của nhóm

---

## 1. Kiến trúc nhóm đã xây dựng (150–200 từ)

> Mô tả ngắn gọn hệ thống nhóm: bao nhiêu workers, routing logic hoạt động thế nào,
> MCP tools nào được tích hợp. Dùng kết quả từ `docs/system_architecture.md`.

**Hệ thống tổng quan:**

Nhóm triển khai mô hình Supervisor-Worker chuyên biệt để giải quyết bài toán CS & IT Helpdesk. Hệ thống gồm một Supervisor trung tâm điều phối 3 Workers: retrieval_worker (truy xuất tri thức từ ChromaDB), policy_tool_worker (xử lý logic chính sách qua MCP), và synthesis_worker (tổng hợp câu trả lời cuối cùng). Dữ liệu được luân chuyển qua AgentState, cho phép các Worker kế thừa ngữ cảnh của nhau mà không cần gọi lại LLM từ đầu.

**Routing logic cốt lõi:**
> Mô tả logic supervisor dùng để quyết định route (keyword matching, LLM classifier, rule-based, v.v.)

Supervisor sử dụng logic Hybrid Routing: ưu tiên keyword matching để định tuyến nhanh các câu hỏi về SLA, policy, hoặc error code. Nếu câu hỏi chứa từ khóa rủi ro cao (risk_high) hoặc không khớp keyword, Supervisor sẽ dùng LLM để phân loại. Hệ thống cũng tích hợp Human-in-the-loop (HITL) để xử lý các trường hợp không chắc chắn, đảm bảo không có câu hỏi nào bị bỏ sót.

**MCP tools đã tích hợp:**
> Liệt kê tools đã implement và 1 ví dụ trace có gọi MCP tool.

- `search_kb`: Truy xuất tài liệu từ vector database.
- `get_ticket_info`: Lấy thông tin ticket từ Jira.
- `check_access_permission`: Kiểm tra quyền truy cập.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn phương án đã chọn.

**Quyết định:** Chuyển đổi từ Full LLM Routing sang Hybrid Keyword-Rule Routing

**Bối cảnh vấn đề:**

Trong Sprint 1, khi để LLM hoàn toàn quyết định route, hệ thống thường xuyên bị nhầm lẫn giữa các câu hỏi "kỹ thuật có chứa từ khóa chính sách". Ví dụ: "Chính sách bảo mật máy chủ" bị đẩy sang policy_tool_worker (vốn chuyên về HR/Refund) thay vì retrieval_worker (chuyên về IT Docs), dẫn đến kết quả trả về bị rỗng.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Full LLM Router | Linh hoạt, hiểu ngôn ngữ tự nhiên tốt. | Không ổn định, tốn token, dễ nhầm lẫn từ khóa. |
| Hybrid Router (Keyword + LLM) | Ổn định, tốn ít token, dễ debug. | Ít linh hoạt, khó xử lý các câu hỏi phức tạp. |

**Phương án đã chọn và lý do:**

Nhóm đã chọn Hybrid Router vì nó cân bằng được giữa tính linh hoạt và sự ổn định. Hybrid Router sử dụng keyword matching để xử lý các câu hỏi đơn giản và LLM để xử lý các câu hỏi phức tạp. Điều này giúp giảm thiểu số lượng token sử dụng và tăng cường tính ổn định của hệ thống.

**Bằng chứng từ trace/code:**
> Dẫn chứng cụ thể (VD: route_reason trong trace, đoạn code, v.v.)

```
[NHÓM ĐIỀN VÀO ĐÂY — ví dụ trace hoặc code snippet]
```

---

## 3. Kết quả grading questions (150–200 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
> - Nhóm đạt bao nhiêu điểm raw?
> - Câu nào pipeline xử lý tốt nhất?
> - Câu nào pipeline fail hoặc gặp khó khăn?

**Tổng điểm raw ước tính:** 88 / 96

**Câu pipeline xử lý tốt nhất:**
- ID: gq02 — Lý do tốt: Hệ thống truy xuất cực nhanh tài liệu policy_refund_v4.txt qua MCP và liệt kê đúng 3 bước hoàn tiền cho sản phẩm lỗi.

**Câu pipeline fail hoặc partial:**
ID: gq05 — Fail ở đâu: Không tìm thấy thông tin hệ thống legacy.

Root cause: Dữ liệu này chưa được nhóm index vào vector database trong giai đoạn chuẩn bị data.
**Câu gq07 (abstain):** Nhóm xử lý thế nào?

Nhóm thiết lập prompt cho synthesis_worker để so khớp confidence score. Nếu không có chunk nào có độ tương đồng > 0.5, Agent sẽ trả lời: "Tôi không có đủ thông tin để trả lời câu hỏi này" thay vì đoán mò.

**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?

Trace ghi nhận Supervisor route thành công qua 2 chặng: retrieval_worker lấy mốc thời gian SLA và policy_tool_worker kiểm tra điều kiện khẩn cấp. Kết quả trả về chính xác tên người chịu trách nhiệm trực ca 2am.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

> Dựa vào `docs/single_vs_multi_comparison.md` — trích kết quả thực tế.

**Metric thay đổi rõ nhất (có số liệu):**

Độ chính xác cho các câu hỏi phức tạp (Multi-hop) tăng từ 45% (Day 08) lên 85% (Day 09). Tuy nhiên, độ trễ trung bình tăng từ 4s lên 16s.

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**

Khả năng "chia để trị" (Separation of Concerns). Việc debug trở nên cực kỳ đơn giản vì mỗi Worker có một nhiệm vụ riêng. Chỉ cần nhìn vào Trace là biết lỗi do Supervisor route sai hay do Worker lấy thiếu data.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**

Với các câu hỏi xã giao hoặc câu hỏi đơn giản chỉ nằm trong một tài liệu duy nhất, hệ thống Multi-agent phản hồi rất chậm do phải chạy qua nhiều node trung gian, gây lãng phí tài nguyên.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Nguyễn Triệu Gia Khánh | Thiết kế Graph, Supervisor Routing logic | 1|
| Nguyễn Hoàng Khải Minh | Xây dựng 3 Workers & Prompt Engineering | 2 |
| Nguyễn Hoàng Duy | Hiện thực hóa MCP Server & Tool integration | 3 |
| Diệu Linh, Thùy Linh | Trace Analysis, Documentation & Git Support | 4 |

**Điều nhóm làm tốt:**

Thống nhất Contract (đầu vào/đầu ra) của các Worker ngay từ đầu nên khi ghép code rất ít lỗi logic.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**

Phối hợp Git ở giai đoạn cuối còn lúng túng dẫn đến sự cố lộ Secret (đã khắc phục).

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**

Nhóm sẽ cấu hình Pre-commit hook để tự động chặn Secret trước khi commit.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

> 1–2 cải tiến cụ thể với lý do có bằng chứng từ trace/scorecard.

Nhóm sẽ triển khai cơ chế Self-Correction. Dựa trên trace của câu gq05 (fail do thiếu data), nhóm muốn synthesis_worker có quyền phản hồi ngược lại Supervisor để yêu cầu retrieval_worker mở rộng phạm vi tìm kiếm (Query Expansion) nếu kết quả ban đầu không đủ thông tin.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
