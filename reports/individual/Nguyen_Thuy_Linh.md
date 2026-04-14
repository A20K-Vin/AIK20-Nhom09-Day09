# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Thùy Linh
**Vai trò trong nhóm:** Trace & Docs Owner  
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
- File chính: eval_trace.py, docs/single_vs_multi_comparison.md, và reports/group_report.md.
- Functions tôi implement: analyze_trace(), calculate_metrics(), và generate_grading_report()

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Tôi chịu trách nhiệm phân tích kết quả và tổng hợp báo cáo cho toàn nhóm. Cụ thể, tôi đã:
- Viết script eval_trace.py để tự động tính toán các chỉ số hiệu năng (latency, confidence, hitl_rate) từ file trace.
- Tạo báo cáo so sánh single-worker vs multi-worker trong docs/single_vs_multi_comparison.md để nhóm có cái nhìn trực quan về hiệu quả của hệ thống.
- Tổng hợp kết quả vào reports/group_report.md, đảm bảo tất cả các thành viên đều có thể hiểu rõ hệ thống hoạt động như thế nào và đóng góp của từng người.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**


---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Thiết lập cấu trúc Trace Format bắt buộc có chứa trường route_reason và mcp_tool_called ngay từ Sprint 1.

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:**

Ban đầu, nhóm dự định chỉ lưu kết quả đầu ra cuối cùng của LLM. Tuy nhiên, tôi đã đề xuất phải lưu lại cả "lý do định tuyến" của Supervisor và "danh sách công cụ MCP đã gọi".

**Trade-off đã chấp nhận:**

Việc này làm tăng kích thước file trace và tốn thêm một chút token cho mỗi lần log, nhưng đổi lại cho phép nhóm phân tích chính xác nguyên nhân gốc rễ của các lỗi routing và đánh giá hiệu quả sử dụng MCP tool.

**Bằng chứng từ trace/code:**

```
[PASTE ĐOẠN CODE HOẶC TRACE RELEVANT VÀO ĐÂY]
```
{
  "run_id": "run_20260414_152624",
  "supervisor_route": "policy_tool_worker",
  "route_reason": "task contains 'hoàn tiền' keyword",
  "mcp_tools_used": ["get_ticket_info"],
  "latency_ms": 16149
}
---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** Lộ OpenAI API Key trong lịch sử Commit và xung đột Merge (Non-fast-forward).

**Symptom (pipeline làm gì sai?):**

Trong quá trình làm việc, do sơ suất, tôi đã vô tình commit file .env chứa OpenAI API Key lên GitHub. Điều này không chỉ vi phạm chính sách bảo mật mà còn gây ra xung đột merge khi các thành viên khác cố gắng push code lên nhánh chính.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Lỗi xảy ra do tôi chưa cấu hình file .gitignore để loại trừ file .env, dẫn đến việc thông tin nhạy cảm bị đưa vào hệ thống quản lý phiên bản.

**Cách sửa:**

Tôi đã ngay lập tức xóa file .env khỏi lịch sử Git bằng lệnh git filter-branch --env-filter 'unset ...' và sau đó thêm .env vào .gitignore để ngăn chặn tái diễn.

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.

remote: error: GH013: Repository rule violations... OpenAI API Key detected.

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.

To https://github.com/A20K-Vin/AIK20-Nhom09-Day09.git  [new branch] main -> main.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

Khả năng phân tích dữ liệu và quản lý rủi ro. Tôi đã giúp nhóm nhìn thấy sự đánh đổi giữa độ trễ (latency tăng 284%) và độ chính xác (accuracy tăng 40%) thông qua số liệu thực tế, giúp báo cáo nhóm có sức thuyết phục cao.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Khả năng xử lý lỗi kỹ thuật. Mặc dù tôi đã sửa được lỗi lộ API Key, nhưng việc này cho thấy tôi cần cẩn trọng hơn trong việc quản lý cấu hình và bảo mật.

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Nhóm phụ thuộc vào tôi trong việc đảm bảo tính toàn vẹn của dữ liệu và báo cáo. Nếu tôi không hoàn thành phần phân tích, nhóm sẽ không có cơ sở để đánh giá hiệu quả của hệ thống và không thể hoàn thiện báo cáo cuối cùng.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Tôi phụ thuộc vào các thành viên khác trong việc cung cấp dữ liệu trace và kết quả chạy thử. Nếu không có dữ liệu này, tôi không thể thực hiện phân tích và đánh giá hiệu quả của hệ thống.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

Tôi sẽ xây dựng một Dashboard Dashboard (Streamlit) đơn giản để hiển thị Trace theo thời gian thực. Lý do là vì trong quá trình làm, việc đọc file .jsonl thủ công để tìm lỗi cho câu gq05 rất mệt mỏi; một giao diện trực quan sẽ giúp Trace Owner phát hiện "nút thắt cổ chai" (bottleneck) về latency của từng worker nhanh hơn nhiều.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*