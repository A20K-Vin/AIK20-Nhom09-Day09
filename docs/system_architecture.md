# System Architecture — Lab Day 09

**Nhóm:** ___________  
**Ngày:** ___________  
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

> Mô tả ngắn hệ thống của nhóm: chọn pattern gì, gồm những thành phần nào.

**Pattern đã chọn:** Supervisor-Worker  
**Lý do chọn pattern này (thay vì single agent):**
Phân tách trách nhiệm (Separation of Concerns): Mỗi Worker (Retrieval, Policy, Synthesis) tập trung vào một nhiệm vụ chuyên biệt, giúp prompt ngắn gọn và logic xử lý rõ ràng hơn so với việc bắt một Agent làm tất cả.
Khả năng mở rộng (Scalability): Dễ dàng thêm các năng lực mới (Workers mới hoặc MCP tools mới) bằng cách đăng ký thêm vào Supervisor mà không cần sửa đổi toàn bộ hệ thống.
Kiểm soát rủi ro (Risk Management): Supervisor đóng vai trò "người gác cổng", có khả năng nhận diện các yêu cầu nguy cơ cao (risk_high) để chuyển qua cơ chế kiểm duyệt người đóng (HITL) trước khi thực hiện.
Minh bạch trong vận hành (Observability): Hệ thống cung cấp log chi tiết về lý do tại sao một worker cụ thể được chọn (route_reason), giúp việc debug và đánh giá hiệu năng chính xác từng thành phần.

---

## 2. Sơ đồ Pipeline

> Vẽ sơ đồ pipeline dưới dạng text, Mermaid diagram, hoặc ASCII art.
> Yêu cầu tối thiểu: thể hiện rõ luồng từ input → supervisor → workers → output.

**Ví dụ (ASCII art):**
```
User Request
     │
     ▼
┌──────────────┐
│  Supervisor  │  ← route_reason, risk_high, needs_tool
└──────┬───────┘
       │
   [route_decision]
       │
  ┌────┴────────────────────┐
  │                         │
  ▼                         ▼
Retrieval Worker     Policy Tool Worker
  (evidence)           (policy check + MCP)
  │                         │
  └─────────┬───────────────┘
            │
            ▼
      Synthesis Worker
        (answer + cite)
            │
            ▼
         Output
```

**Sơ đồ thực tế của nhóm:**

```
graph TD
    %% Định nghĩa màu sắc
    classDef start_end fill:#f9f,stroke:#333,stroke-width:2px;
    classDef supervisor fill:#fff4dd,stroke:#d4a017,stroke-width:2px;
    classDef worker fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef external fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    classDef human fill:#ffebee,stroke:#c62828,stroke-width:2px;

    %% Khởi đầu
    Start((User Input)):::start_end --> Supervisor[Supervisor Node]:::supervisor

    %% Bước phân loại của Supervisor
    Supervisor --> Decision{Routing Decision}:::supervisor

    %% Nhánh Human Review (HITL)
    Decision -- "risk_high = True" --> HITL[Human Review Node]:::human
    HITL -- "Human Approved" --> Retrieval

    %% Nhánh Policy
    Decision -- "policy/access task" --> Policy[Policy Tool Worker]:::worker
    Policy -- "Call Tools" --> MCP[MCP Server Tools]:::external
    Policy -- "Context missing" --> Retrieval

    %% Nhánh Retrieval (Mặc định)
    Decision -- "factual task" --> Retrieval[Retrieval Worker]:::worker

    %% Tổng hợp
    Retrieval -- "Evidence" --> Synthesis[Synthesis Worker]:::worker
    Policy -- "Result" --> Synthesis
    
    %% Kết thúc
    Synthesis --> Output((Final Answer)):::start_end

    %% Chú thích Box
    subgraph Workers
        Retrieval
        Policy
        Synthesis
    end

    subgraph External
        MCP
    end

```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích bài toán, phân loại yêu cầu, định tuyến đến Worker phù hợp và nhận diện các tình huống rủi ro cao (HITL). |
| **Input** | `task` (Câu hỏi từ người dùng) |
| **Output** | `supervisor_route`, `route_reason`, `risk_high`, `needs_tool` |
| **Routing logic** | Keyword-based: Policy/Access -> `policy_tool`; SLA/Ticket -> `retrieval`; Các lỗi lạ ERR-XXX -> `human_review`. |
| **HITL condition** | Khi xuất hiện từ khóa rủi ro (`emergency`, `khẩn cấp`) kết hợp với mã lỗi chưa xác định hoặc yêu cầu quyền Level cao. |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Truy xuất thông tin từ Knowledge Base cục bộ sử dụng Vector Search (ChromaDB) hoặc Lexical Search (tổng hợp từ khóa) làm fallback. |
| **Embedding model** | `SentenceTransformer` (all-MiniLM-L6-v2) hoặc `OpenAI` (text-embedding-3-small). |
| **Top-k** | 3 (Mặc định) |
| **Stateless?** | Yes |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Kiểm tra các ngoại lệ của chính sách (Flash Sale, Digital License) và làm giàu dữ liệu bằng cách gọi các công cụ quản trị qua MCP. |
| **MCP tools gọi** | `search_kb`, `get_ticket_info`, `check_access_permission`. |
| **Exception cases xử lý** | Flash Sale, License key đã kích hoạt, Đơn hàng trước mốc 01/02/2026. |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | `gpt-4o-mini` hoặc `gemini-1.5-flash`. |
| **Temperature** | 0.1 (để đảm bảo tính chính xác và tránh sáng tạo quá mức). |
| **Grounding strategy** | CHỈ trả lời dựa trên context được cung cấp từ Retrieval và Policy result. |
| **Abstain condition** | Khi context ghi "Không có info" hoặc gặp mã lỗi lạ không có trong tài liệu. |

### MCP Server (`mcp_server.py`)

| Tool | Input | Output |
|------|-------|--------|
| search_kb | query, top_k | chunks, sources |
| get_ticket_info | ticket_id | ticket details (SLA, status, assignees) |
| check_access_permission | level, role, emergency | can_grant, required_approvers |

---

## 4. Shared State Schema

| Field | Type | Mô tả | Ai đọc/ghi |
|-------|------|-------|-----------|
| `task` | str | Câu hỏi nguyên bản từ người dùng | Supervisor đọc |
| `supervisor_route`| str | ID của Worker được chọn để xử lý tiếp | Supervisor ghi, Graph đọc |
| `route_reason` | str | Giải thích ngắn gọn lý do điều hướng | Supervisor ghi, Trace đọc |
| `risk_high` | bool | Flag đánh dấu yêu cầu cần xem xét kỹ | Supervisor ghi, HITL đọc |
| `needs_tool` | bool | Quyết định có cần gọi external tool không | Supervisor ghi, Policy đọc |
| `retrieved_chunks`| list | Danh sách văn bản tìm được từ KB | Retrieval ghi, Synthesis đọc |
| `policy_result` | dict | Kết quả phân tích chính sách & MCP tools | Policy ghi, Synthesis đọc |
| `final_answer` | str | Câu trả lời cuối cùng cho User | Synthesis ghi |
| `confidence` | float | Điểm tin cậy của câu trả lời (0.0 - 1.0) | Synthesis ghi |
| `history` | list | Nhật ký vết (trace) thực thi của hệ thống | Tất cả (ghi thêm) |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

Dựa trên việc đối chiếu codebase của Day 08 (`rag_answer.py`) và Day 09 (`graph.py`, `workers/`), nhóm rút ra các so sánh sau:

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| **Traceability (Truy vết)** | Chỉ có log text đơn giản. Khi lỗi, khó xác định do Retrieval hay do Reasoning. | **Trace JSON:** `graph.py` lưu toàn bộ `AgentState` vào `artifacts/traces/`. Có thể audit cụ thể từng field: `retrieved_chunks`, `policy_result`, `mcp_tools_used`. |
| **Logic Phức tạp** | Nhồi nhét mọi thứ (SLA, Refund Policy, Tool call) vào một System Prompt duy nhất. | **Phân tách trách nhiệm:** `policy_tool.py` xử lý logic chính sách, `retrieval.py` lo Vector Search, `synthesis.py` tập trung vào việc Grounding context. |
| **Giao diện Tool (MCP)** | Tool được gọi cứng (hard-coded) hoặc mô tả sơ sài trong prompt. | **Standardized MCP:** `mcp_server.py` định nghĩa `TOOL_SCHEMAS` theo chuẩn Model Context Protocol, giúp Agent gọi tool chính xác và minh bạch. |
| **Khả năng Kiểm soát** | LLM tự quyết định mọi thứ. Rủi ro cao với các yêu cầu nhạy cảm (P1, Emergency). | **Cổng Supervisor:** `supervisor_node` trong `graph.py` có flag `risk_high` và định hướng sang `human_review` giúp kiểm duyệt an toàn trước khi thực hiện. |

**Quan sát thực tế từ codebase:**
- **Shared State Management:** Việc dùng `TypedDict` cho `AgentState` giúp quản lý dữ liệu xuyên suốt các node rất tường minh (đọc tại `graph.py:24-51`).
- **Phân tách Metadata:** Quy trình `index.py` tách biệt metadata (source, section, access) giúp Retrieval worker lọc dữ liệu chính xác hơn so với việc chỉ tìm kiếm text thuần túy.
- **Evaluation 4-metric:** Hệ thống Day 09 cho phép chạy `eval.py` để đo lường định lượng (Faithfulness, Relevance, Recall, Completeness), điều mà kiến trúc Single Agent khó thực hiện một cách tự động.

---

## 6. Giới hạn và điểm cần cải tiến

Dựa trên phân tích mã nguồn hiện tại, hệ thống còn các điểm hạn chế kỹ thuật sau:

1. **Supervisor Intelligence (Định tuyến):**
   - *Hiện tại:* `supervisor_node` đang dùng rule-based dựa trên keyword lists (đọc tại `graph.py:106-111`).
   - *Cải tiến:* Chuyển sang LLM-based Intent Classifier hoặc Semantic Router để hiểu các câu hỏi không chứa keyword nhưng mang ý nghĩa tương đương (VD: "Máy chủ sập rồi" 대신 cho "P1").
2. **MCP Server Realization:**
   - *Hiện tại:* `mcp_server.py` đang là một mock registry và chạy cùng process (in-process mock).
   - *Cải tiến:* Triển khai real MCP Host sử dụng FastAPI hoặc thư viện `mcp` chính thức để hỗ trợ gọi tool qua mạng (HTTP/SSE) và bảo mật tốt hơn.
3. **Cơ chế Human-in-the-loop (HITL):**
   - *Hiện tại:* `human_review_node` trong `graph.py` chỉ print ra warning và tự động approve (auto-approve lab mode).
   - *Cải tiến:* Tích hợp thực sự với giao diện người dùng (Frontend) hoặc Webhook để tạm dừng graph và chờ signal từ người vận hành thông qua `state["hitl_triggered"]`.
4. **Hiệu suất (Parallelism):**
   - *Hiện tại:* Graph chạy tuần tự (Sequential) từng node trong hàm `run()`.
   - *Cải tiến:* Sử dụng `asyncio` để khởi chạy đồng thời `retrieval_worker` và `policy_tool_worker` ngay sau khi supervisor định hướng, giúp giảm tổng thời gian xử lý (latency_ms).
5. **Context Memory & History:**
   - *Hiện tại:* `AgentState` khởi tạo mới cho mỗi task (`make_initial_state`).
   - *Cải tiến:* Tích hợp cơ chế lưu trữ Session vào ChromaDB hoặc SQL để Supervisor có thể truy xuất lịch sử hội thoại trước đó, hỗ trợ các câu hỏi follow-up (VD: "Quy trình đó áp dụng cho ai?").
