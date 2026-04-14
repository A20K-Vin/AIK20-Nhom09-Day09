"""
mcp_http_server.py — Advanced MCP Server (Bonus +2)
Sprint 3 Advanced: Real MCP server dùng FastMCP library.

Implements same 4 tools as mcp_server.py nhưng qua real MCP protocol.
Workers có thể kết nối qua stdio hoặc HTTP (với uvicorn).

Chạy standalone:
    python mcp_http_server.py

Hoặc dùng với MCP client:
    mcp dev mcp_http_server.py

Tools:
    1. search_kb(query, top_k)
    2. get_ticket_info(ticket_id)
    3. check_access_permission(access_level, requester_role, is_emergency)
    4. create_ticket(priority, title, description)
"""

import os
import sys
from datetime import datetime
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Thêm thư mục gốc vào sys.path để import mcp_server tools
sys.path.insert(0, os.path.dirname(__file__))

# Khởi tạo FastMCP server
mcp = FastMCP("Day09 Internal KB Server")


# ─────────────────────────────────────────────
# Tool 1: search_kb
# ─────────────────────────────────────────────

@mcp.tool()
def search_kb(query: str, top_k: int = 3) -> dict:
    """
    Tìm kiếm Knowledge Base nội bộ bằng semantic search.
    Trả về top-k chunks liên quan nhất từ 5 tài liệu nội bộ.

    Args:
        query: Câu hỏi hoặc keyword cần tìm
        top_k: Số chunks cần trả về (mặc định 3)

    Returns:
        dict với keys: chunks (list), sources (list), total_found (int)
    """
    try:
        from workers.retrieval import retrieve_dense
        chunks = retrieve_dense(query, top_k=top_k)
        sources = list({c["source"] for c in chunks})
        return {
            "chunks": chunks,
            "sources": sources,
            "total_found": len(chunks),
        }
    except Exception as e:
        return {
            "chunks": [],
            "sources": [],
            "total_found": 0,
            "error": str(e),
        }


# ─────────────────────────────────────────────
# Tool 2: get_ticket_info
# ─────────────────────────────────────────────

# Mock ticket database (giống mcp_server.py)
MOCK_TICKETS = {
    "P1-LATEST": {
        "ticket_id": "IT-9847",
        "priority": "P1",
        "title": "API Gateway down — toàn bộ người dùng không đăng nhập được",
        "status": "in_progress",
        "assignee": "nguyen.van.a@company.internal",
        "created_at": "2026-04-13T22:47:00",
        "sla_deadline": "2026-04-14T02:47:00",
        "escalated": True,
        "escalated_to": "senior_engineer_team",
        "notifications_sent": ["slack:#incident-p1", "email:incident@company.internal", "pagerduty:oncall"],
    },
    "IT-1234": {
        "ticket_id": "IT-1234",
        "priority": "P2",
        "title": "Feature login chậm cho một số user",
        "status": "open",
        "assignee": None,
        "created_at": "2026-04-13T09:15:00",
        "sla_deadline": "2026-04-14T09:15:00",
        "escalated": False,
    },
}


@mcp.tool()
def get_ticket_info(ticket_id: str) -> dict:
    """
    Tra cứu thông tin ticket từ hệ thống Jira nội bộ.

    Args:
        ticket_id: ID ticket (VD: IT-1234, P1-LATEST)

    Returns:
        dict với thông tin ticket hoặc error nếu không tìm thấy
    """
    ticket = MOCK_TICKETS.get(ticket_id.upper())
    if ticket:
        return ticket
    return {
        "error": f"Ticket '{ticket_id}' không tìm thấy.",
        "available_mock_ids": list(MOCK_TICKETS.keys()),
    }


# ─────────────────────────────────────────────
# Tool 3: check_access_permission
# ─────────────────────────────────────────────

ACCESS_RULES = {
    1: {
        "required_approvers": ["Line Manager"],
        "emergency_can_bypass": False,
        "note": "Standard read-only access",
    },
    2: {
        "required_approvers": ["Line Manager", "IT Admin"],
        "emergency_can_bypass": True,
        "emergency_bypass_note": "Level 2 có thể cấp tạm thời với approval đồng thời của Line Manager và IT Admin on-call.",
        "note": "Standard access",
    },
    3: {
        "required_approvers": ["Line Manager", "IT Admin", "IT Security"],
        "emergency_can_bypass": False,
        "note": "Elevated access — không có emergency bypass",
    },
}


@mcp.tool()
def check_access_permission(
    access_level: int,
    requester_role: str,
    is_emergency: bool = False,
) -> dict:
    """
    Kiểm tra điều kiện cấp quyền truy cập theo Access Control SOP.

    Args:
        access_level: Level cần cấp (1, 2, hoặc 3)
        requester_role: Vai trò của người yêu cầu (e.g., contractor, engineer)
        is_emergency: True nếu đây là yêu cầu khẩn cấp (P1 incident)

    Returns:
        dict với can_grant, required_approvers, emergency_override, notes, source
    """
    rule = ACCESS_RULES.get(access_level)
    if not rule:
        return {"error": f"Access level {access_level} không hợp lệ. Levels: 1, 2, 3."}

    notes = []
    if is_emergency and rule.get("emergency_can_bypass"):
        notes.append(rule.get("emergency_bypass_note", ""))
    elif is_emergency and not rule.get("emergency_can_bypass"):
        notes.append(f"Level {access_level} KHÔNG có emergency bypass. Phải follow quy trình chuẩn.")

    return {
        "access_level": access_level,
        "can_grant": True,
        "required_approvers": rule["required_approvers"],
        "approver_count": len(rule["required_approvers"]),
        "emergency_override": is_emergency and rule.get("emergency_can_bypass", False),
        "notes": notes,
        "source": "access_control_sop.txt",
    }


# ─────────────────────────────────────────────
# Tool 4: create_ticket
# ─────────────────────────────────────────────

@mcp.tool()
def create_ticket(priority: str, title: str, description: str = "") -> dict:
    """
    Tạo ticket mới trong hệ thống Jira (MOCK — không tạo thật trong lab).

    Args:
        priority: Mức độ ưu tiên (P1, P2, P3, P4)
        title: Tiêu đề ticket
        description: Mô tả chi tiết (tùy chọn)

    Returns:
        dict với ticket_id, url, created_at
    """
    mock_id = f"IT-{9900 + hash(title) % 99}"
    return {
        "ticket_id": mock_id,
        "priority": priority,
        "title": title,
        "description": description[:200],
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "url": f"https://jira.company.internal/browse/{mock_id}",
        "note": "MOCK ticket — không tồn tại trong hệ thống thật",
    }


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Day09 MCP HTTP Server (FastMCP — Advanced Bonus)")
    print("=" * 60)
    print("\nTools available:")
    print("  • search_kb(query, top_k=3)")
    print("  • get_ticket_info(ticket_id)")
    print("  • check_access_permission(access_level, requester_role, is_emergency=False)")
    print("  • create_ticket(priority, title, description='')")
    print("\nRunning via stdio (MCP protocol)...")
    print("To connect: mcp dev mcp_http_server.py")
    print("Or run with: python mcp_http_server.py\n")
    mcp.run()
