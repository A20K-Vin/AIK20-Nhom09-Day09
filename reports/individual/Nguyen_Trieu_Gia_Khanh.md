# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Triệu Gia Khánh  
**Vai trò trong nhóm:** Supervisor Owner & system architecture
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (150 từ)

Trong dự án Lab Day 09, tôi đảm nhận vai trò **Supervisor Owner** và system architecture. Trọng tâm trách nhiệm của tôi nằm ở việc thiết kế và triển khai "bộ não" điều phối của hệ thống tại file `graph.py`. Tôi trực tiếp định nghĩa và quản lý `AgentState`, đảm bảo mọi dữ liệu từ các bước trung gian (Worker outputs, MCP calls) được lưu trữ và truyền tải chính xác.

Cụ thể, tôi đã thực hiện:
- Thiết kế luồng logic cho `supervisor_node`, quyết định việc định tuyến dựa trên ý định của người dùng.
- Xây dựng workflow chính trong hàm `build_graph` (Option A), đảm bảo sự kết nối thông suốt giữa Supervisor, Retrieval, Policy và Synthesis.
- Triển khai cơ chế lưu vết (Trace) dưới dạng JSON để phục vụ quá trình Evaluation và Audit.
- Biên soạn tài liệu kiến trúc hệ thống tại `docs/system_architecture.md`.

Vai trò của tôi là đảm bảo tính nhất quán của hệ thống. Nếu phần việc của tôi gặp lỗi, toàn bộ pipeline sẽ bị gián đoạn vì dữ liệu không được luân chuyển đúng contract giữa các thành viên.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (200 từ)

**Quyết định:** Tôi quyết định sử dụng cơ chế **Keyword-based Routing kết hợp Risk-high Flagging** trong Supervisor thay vì sử dụng LLM Classifier ngay từ đầu.

**Lý do:**
1. **Tối ưu Latency:** Qua thực nghiệm, việc gọi LLM để phân loại task mất từ 1.2s - 2s cho mỗi request. Trong khi đó, việc sử dụng bộ quy tắc keyword (`graph.py:106-111`) chỉ mất dưới 10ms. Đối với một hệ thống IT Helpdesk cần phản hồi nhanh, việc tiết kiệm gần 2 giây ở bước khởi đầu là một lợi thế cực lớn.
2. **Khả năng kiểm soát rủi ro:** Tôi ưu tiên tính an toàn. Bằng cách định nghĩa các từ khóa rủi ro như "emergency", "khẩn cấp" hoặc các mã lỗi hệ thống "ERR-", tôi có thể ép hệ thống đi qua node `human_review` mà không sợ sự không ổn định (hallucination) của LLM khi phân loại.
3. **Trade-off:** Tôi chấp nhận đánh đổi khả năng hiểu ngôn ngữ tự nhiên linh hoạt để lấy sự ổn định và tốc độ. Nếu người dùng dùng các từ lóng không có trong từ điển từ khóa, hệ thống sẽ rơi vào route `retrieval` mặc định.

**Bằng chứng từ code/trace:**
Trong file `graph.py` dòng 113-127, tôi đã cài đặt:
```python
if any(kw in task for kw in policy_keywords):
    route = "policy_tool_worker"
    needs_tool = True
elif any(kw in task for kw in risk_keywords):
    risk_high = True
    route_reason += " | risk_high flagged"
```
Kết quả trong trace JSON cho thấy `latency_ms` ở node supervisor luôn xấp xỉ 0ms, giúp tổng thời gian phản hồi của pipeline duy trì ở mức dưới 3s.

---

## 3. Tôi đã sửa một lỗi gì? (180 từ)

**Lỗi:** State không được cập nhật đúng sau khi qua bước Human Review.

**Symptom:** Khi một câu hỏi kích hoạt `risk_high` (Ví dụ: "ERR-999 cần cấp quyền khẩn cấp"), hệ thống chuyển sang `human_review_node`. Tuy nhiên, sau khi được duyệt, hệ thống kết thúc mà không mang theo kết quả của Retrieval Worker, dẫn đến Synthesis Worker trả lời: "Tôi không tìm thấy thông tin trong tài liệu".

**Root cause:** Lỗi nằm ở logic điều phối trong hàm `run()` của Graph. Ban đầu tôi nghĩ rằng `human_review_node` chỉ là một node thông báo, nhưng thực tế nó cần thay đổi `supervisor_route` để quay lại luồng lấy dữ liệu.

**Cách sửa:**
**Bằng chứng trước/sau:**
Tôi đã điều chỉnh hàm `run()` trong `graph.py` (dòng 231-234) để đảm bảo sau khi duyệt xong, hệ thống phải thực thi ngay Retrieval node:
```python
# Sửa từ:
if route == "human_review":
    state = human_review_node(state)

# Thành:
if route == "human_review":
    state = human_review_node(state)
    # Redirect sang Retrieval ngay sau khi con người Approve
    state = retrieval_worker_node(state)
```

**Bằng chứng:** Trước khi sửa, `workers_called` chỉ chứa `["human_review", "synthesis_worker"]`. Sau khi sửa, trace ghi lại đúng chuỗi: `["human_review", "retrieval_worker", "synthesis_worker"]`, đảm bảo câu trả lời cuối cùng có đầy đủ chứng cứ từ Knowledge Base.

---

## 4. Tôi tự đánh giá đóng góp của mình (120 từ)

**Tôi làm tốt nhất ở điểm nào?**
Khả năng thiết kế cấu trúc dữ liệu `AgentState` đồng nhất. Việc này giúp các thành viên khác khi viết Worker chỉ cần bám sát Contract tôi đưa ra là có thể tích hợp vào Graph mà không gặp lỗi xung đột kiểu dữ liệu.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi chưa tối ưu được việc thực thi song song (Parallelism). Hiện tại các Worker vẫn chạy theo thứ tự tuần tự, điều này làm cho trải nghiệm người dùng chưa đạt mức mượt mượt nhất có thể.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nếu file `graph.py` của tôi không chạy hoặc `AgentState` bị lỗi, toàn bộ dự án sẽ dừng lại vì không có thành phần nào kết nối các Worker đơn lẻ.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc vào tính ổn định của RAG Index từ thành viên phụ trách Retrieval. Nếu Index kém chất lượng, dù Graph của tôi có định tuyến đúng thì câu trả lời cuối cùng vẫn sẽ sai.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (100 từ)

Tôi sẽ nâng cấp Supervisor thành **Semantic Router** dùng Model Embedding (như `all-MiniLM-L6-v2`) để tính toán độ tương đồng cosine giữa câu hỏi và mục tiêu định tuyến. Lý do là trong trace của câu hỏi `gq07`, do người dùng đặt câu hỏi hơi "lắt léo", Supervisor keyword-based của tôi đã không bắt đúng intent, dẫn đến route sai. Việc dùng Semantic Router sẽ cân bằng được giữa tốc độ (vẫn nhanh hơn LLM call) và khả năng hiểu ngôn ngữ tự nhiên sâu hơn.
