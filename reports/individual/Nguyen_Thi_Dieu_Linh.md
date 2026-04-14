# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Thị Diệu Linh  
**Vai trò trong nhóm: Trace & Docs Owner  
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
- File chính: `eval_trace.py`, single_vs_multi_comparison.md
- Functions tôi implement: `analyze_traces` `compare_single_vs_multi`

**Cách công việc của tôi kết nối với phần của thành viên khác:**
- Nhận input là trace logs được sinh ra từ `graph.py` (phần orchestrator) và các worker (retrieval, policy, synthesis)  
- Hàm `analyze_traces` xử lý và tổng hợp các metric (confidence, latency, routing, MCP usage) từ output của toàn pipeline  
- Hàm `compare_single_vs_multi` dùng các metric này để so sánh giữa Day 08 (single-agent) và Day 09 (multi-agent)  
- Kết quả được sử dụng trực tiếp trong báo cáo (scorecard, bảng so sánh, analysis theo loại câu hỏi)  

=> Module đóng vai trò evaluation & analysis layer, kết nối output của toàn bộ hệ thống thành insight phục vụ báo cáo
_________________

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
- Commit: b91d9c6 (add single vs multi)
- Commit: 54c8547 (add trace)
- Commit: aa626f5 (fix trace)
- Commit: 396d8bc (reformat trace)
- Commit: 9bff77c (fix grading log code)

- File `eval_trace.py` chứa các hàm `analyze_traces`, `compare_single_vs_multi`
- Trace logs được generate từ `graph.py` và dùng trực tiếp trong module evaluation

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:**  
Chuẩn hóa format output của trace analysis và comparison để phục vụ trực tiếp cho báo cáo (report-ready metrics).

**Các lựa chọn thay thế:**  
- Giữ raw output dạng dict/print log (khó đọc, khó dùng trong báo cáo)  
- Phân tích thủ công từng trace  

**Tại sao chọn cách này:**  
- Raw trace chứa nhiều thông tin nhưng không trực quan  
- Cần chuyển thành các metric tổng hợp (routing %, latency, confidence, top sources) để dễ so sánh và đưa vào report  
- Giảm công sức xử lý thủ công khi viết báo cáo  

**Bằng chứng từ code/trace:**  
- Hàm `analyze_traces` format lại metrics (vd: "8/16 (50%)") thay vì raw count  
- `compare_single_vs_multi` tạo structure rõ ràng cho Day 08 vs Day 09  
- Output `eval_report.json` dùng trực tiếp cho phần analysis trong báo cáo  


---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:**  
Output của `analyze_traces` ở dạng raw count, không phù hợp để sử dụng trực tiếp trong báo cáo

**Symptom (pipeline làm gì sai?):**  

- Metric hiển thị dạng số thô (vd: 8, 16)  
- Không có tỷ lệ (%) → khó so sánh giữa các worker  
- Phải tính toán lại thủ công khi viết report  

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**  

- Lỗi nằm ở **evaluation layer (format output)**  
- Code mẫu chỉ phục vụ debug nội bộ, chưa tối ưu cho presentation/report  

**Cách sửa:**  

- Chuẩn hóa format metric:
  - từ: `retrieval_worker: 8`  
  - thành: `retrieval_worker: 8/16 (50%)`  
- Áp dụng tương tự cho các metric khác (mcp_usage_rate, hitl_rate)

**Bằng chứng trước/sau:**

_Trước:_

routing_distribution:
retrieval_worker: 8
policy_tool_worker: 8


_Sau:_

routing_distribution:
retrieval_worker: 8/16 (50%)
policy_tool_worker: 8/16 (50%)


→ Metric rõ ràng, dùng trực tiếp trong báo cáo mà không cần xử lý thêm

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

- Chuẩn hóa và trình bày kết quả evaluation (trace → metrics → report) rõ ràng, có thể dùng trực tiếp trong báo cáo  
- Kết nối output từ pipeline (graph + workers) thành insight (latency, routing, MCP usage, v.v.)  
- Đảm bảo kết quả phân tích nhất quán, dễ so sánh giữa Day 08 và Day 09  

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

- Chưa tham gia sâu vào core logic (routing, retrieval, policy reasoning)  
- Phụ thuộc nhiều vào code template, ít đóng góp vào thuật toán hoặc kiến trúc  
- Một số metric (multi-hop accuracy, delta thực tế) vẫn cần bổ sung hoặc annotate thủ công  

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

- Không có module evaluation → không có số liệu tổng hợp để viết báo cáo  
- Không có trace analysis → không thể so sánh Day 08 vs Day 09 một cách rõ ràng  
- Không có format chuẩn → các phần khác (report, presentation) bị thiếu dữ liệu hoặc khó trình bày  

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

- Cần pipeline (graph + workers) chạy ổn định để sinh trace đúng  
- Cần retrieval/policy/synthesis worker hoạt động chính xác để metric có ý nghĩa  
- Cần dataset/test questions từ nhóm để chạy evaluation và phân tích

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*
> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.

**Cải tiến đề xuất:**  
Thêm validation và xử lý lỗi (error handling) trong `analyze_traces` khi gặp trace không hoàn chỉnh

**Lý do (dựa trên trace):**  
Trong quá trình chạy evaluation, có trace bị thiếu field (ví dụ: `latency_ms = None`, hoặc thiếu `confidence` khi pipeline fail giữa chừng), dẫn đến:
- Một số metric không được tính (bị skip)
- Average bị sai lệch do thiếu dữ liệu  

**Tôi sẽ thử:**  
- Chuẩn hóa handling:
  - Nếu thiếu `latency_ms` → gán giá trị fallback hoặc log riêng  
  - Nếu thiếu `confidence` → vẫn count vào total nhưng đánh dấu failed case  
- Tách riêng success metrics, failure rate  

**Expected effect:**  
- Metric phản ánh đúng tình trạng hệ thống (bao gồm cả failure)  
- So sánh Day 08 vs Day 09 chính xác hơn  
- Tránh bias khi pipeline có lỗi nhưng evaluation vẫn báo “đẹp”
_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*
