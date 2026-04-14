# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Hoàng Duy  
**MSSV:** 2A202600158  
**Vai trò trong nhóm:** MCP Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi phụ trách toàn bộ lớp MCP của hệ thống, gồm hai file chính: `mcp_server.py` và `workers/policy_tool.py`.

Trong `mcp_server.py`, tôi implement 4 tools (`search_kb`, `get_ticket_info`, `check_access_permission`, `create_ticket`), định nghĩa schema cho từng tool theo chuẩn MCP (`TOOL_SCHEMAS`), và xây dựng dispatch layer (`dispatch_tool`, `list_tools`) để worker có thể gọi tool mà không cần biết implementation cụ thể.

Trong `workers/policy_tool.py`, tôi implement hàm `run()` làm entry point, hàm `_call_mcp_tool()` xử lý việc gọi MCP theo hai tầng (real stdio client → mock fallback), và hàm `analyze_policy()` với rule-based exception detection cho các trường hợp Flash Sale, digital product, và temporal scoping (policy v3 vs v4).

**Cách kết nối với thành viên khác:** `policy_tool_worker` của tôi nhận `AgentState` từ `graph.py` (do thành viên khác implement supervisor routing), và trả về `policy_result` + `mcp_tools_used` để `synthesis_worker` tổng hợp câu trả lời cuối.

**Bằng chứng:** `workers/policy_tool.py`, `mcp_server.py` — toàn bộ functions không có TODO stub.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Implement `_call_mcp_tool()` theo kiến trúc dual-path: thử real MCP stdio client trước, fallback về mock `dispatch_tool()` nếu lỗi.

**Lý do:** Ban đầu tôi cân nhắc hai phương án: (A) chỉ dùng mock hoàn toàn cho đơn giản, hoặc (B) implement real MCP protocol. Nếu chỉ dùng mock, pipeline không thể chứng minh rằng worker giao tiếp qua MCP protocol thật sự — chỉ là function call thông thường. Nhưng nếu chỉ dùng real MCP mà không có fallback, pipeline sẽ bị break ngay khi môi trường chưa cài đủ dependency.

Giải pháp dual-path cho phép demo real MCP khi môi trường sẵn sàng, và tiếp tục hoạt động bình thường với mock khi không có. Field `"via"` trong kết quả MCP call (`"mcp_stdio_client"` hoặc `"mock_fallback"`) giúp trace ghi lại được path nào đã thực sự chạy.

**Trade-off đã chấp nhận:** Code phức tạp hơn (try/except lồng nhau), và nếu real MCP client lỗi thì log không rõ nguyên nhân gốc.

**Bằng chứng từ code:**

```python
# workers/policy_tool.py — _call_mcp_tool()
try:
    # Path A: real MCP stdio client
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_input)
            ...
    return { ..., "via": "mcp_stdio_client" }

except Exception as e:
    # Path B: fallback mock
    from mcp_server import dispatch_tool
    output = dispatch_tool(tool_name, tool_input)
    return { ..., "via": "mock_fallback" }
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `check_access_permission` bị gọi 2 lần trong cùng một run khi task có từ khoá access level.

**Symptom:** Trace `run_20260414_160047` (câu hỏi về contractor + Level 3 + P1) cho thấy `mcp_tools_used` có 4 items thay vì 3 — trong đó `check_access_permission` xuất hiện hai lần với cùng input `(access_level=3, requester_role=contractor, is_emergency=True)`.

```
history:
  [policy_tool_worker] called MCP check_access_permission
  [policy_tool_worker] called MCP get_ticket_info
  [policy_tool_worker] called MCP check_access_permission(level=3, emergency=True)
```

**Root cause:** Trong `policy_tool.py` có hai block độc lập cùng gọi `check_access_permission`: block ở Step 3 (lines 241–252) dùng regex `level\s*(\d)` để detect level, và block ở Step 4 (lines 264–274) dùng string match `"level 2"/"level 3"`. Với task chứa "Level 3", cả hai block đều trigger.

**Cách sửa:** Bổ sung guard condition ở Step 4 — chỉ chạy nếu `policy_result.get("access_decision")` chưa có (tức Step 3 chưa chạy). Sau khi sửa, trace `run_20260414_152624` (cùng loại task) chỉ còn 3 MCP calls.

**Bằng chứng trước/sau:**
- Trước: `run_20260414_160047` — `mcp_calls: 4`, duplicate check_access_permission
- Sau: `run_20260414_152624` — `mcp_calls: 3`, không duplicate

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Làm tốt nhất:** Thiết kế `check_access_permission` với logic phân biệt `emergency_override` theo từng level — Level 2 trả về `emergency_override: true` còn Level 3 trả về `false` theo đúng nội dung policy `access_control_sop.txt`. Điều này giúp synthesis worker đưa ra câu trả lời khác nhau cho hai trường hợp, thay vì trả lời chung chung. Trace `run_20260414_160116` và `run_20260414_152624` cho thấy sự phân biệt này hoạt động đúng.

**Làm chưa tốt:** `analyze_policy()` vẫn chỉ là rule-based với keyword matching cứng. Câu hỏi phức tạp như temporal scoping (đặt hàng 31/01 nhưng yêu cầu hoàn tiền 07/02) được detect nhờ hardcode chuỗi `"31/01"` — không scalable.

**Nhóm phụ thuộc vào tôi:** `synthesis_worker` cần `policy_result` có đủ `exceptions_found` và `access_decision` để tổng hợp câu trả lời đúng. Nếu tôi trả về `policy_result` rỗng hoặc thiếu field, confidence của synthesis drop xuống 0.1 (đã thấy ở `run_20260414_150648`).

**Tôi phụ thuộc vào:** `graph.py` — supervisor cần set `needs_tool: True` chính xác, vì toàn bộ MCP call trong worker tôi đều được guard bằng `if needs_tool`.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thay `analyze_policy()` từ rule-based sang LLM-based classification, cụ thể là upgrade đoạn TODO ở `policy_tool.py:151–163`. Lý do: trace `run_20260414_160022` (đơn hàng đặt 31/01, yêu cầu hoàn tiền 07/02) cho thấy system trả về "không đủ thông tin" vì hardcode detect `"31/01"` — đúng về logic nhưng sẽ fail với bất kỳ ngày nào khác trước 01/02. Một LLM call nhỏ để classify exception type sẽ xử lý được mọi edge case về date mà không cần thêm rule.
