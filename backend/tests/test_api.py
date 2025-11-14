from fastapi.testclient import TestClient

from app.main import agent, app

client = TestClient(app)


def reset_agent_state():
    agent.sessions._sessions.clear()


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_review_with_default_checklist():
    payload = {
        "mrt_content": """
        测试目标: 验证用户可以成功登录系统。
        执行步骤:
        1. 打开登录页面
        2. 输入合法的用户名和密码
        3. 点击登录按钮
        预期结果: 系统跳转至首页。
        """.strip()
    }

    response = client.post("/review", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "suggestions" in data and isinstance(data["suggestions"], list)
    checklist_ids = {item["checklist_id"] for item in data["suggestions"]}
    assert "CHK-002" in checklist_ids  # 前置条件缺失
    assert "CHK-005" in checklist_ids  # 未发现逆向场景


def test_review_with_custom_checklist():
    payload = {
        "mrt_content": "覆盖率测试",
        "checklist": [
            {"id": "CHK-X", "description": "包含覆盖率说明"},
        ],
    }

    response = client.post("/review", json=payload)
    assert response.status_code == 200
    data = response.json()

    checklist_ids = {item["checklist_id"] for item in data["suggestions"]}
    assert "CHK-X" in checklist_ids


def test_conversational_flow_with_inline_inputs():
    reset_agent_state()
    resp1 = client.post("/agent/message", json={"message": "我想审查 MRT"})
    assert resp1.status_code == 200
    payload1 = resp1.json()
    assert payload1["state"] == "awaiting_mrt"
    session_id = payload1["session_id"]

    resp2 = client.post(
        "/agent/message",
        json={
            "session_id": session_id,
            "message": "这是一个测试用例\n步骤: 1. 登录 2. 校验\n预期: 成功跳转首页",
        },
    )
    assert resp2.status_code == 200
    payload2 = resp2.json()
    assert payload2["state"] == "ready"
    assert payload2["suggestions"]
    assert len(payload2["replies"]) == 1
    assert "如需更新 Checklist" in payload2["replies"][0]

    resp_question = client.post(
        "/agent/message",
        json={
            "session_id": session_id,
            "message": "当前 checklist 是什么？",
        },
    )
    assert resp_question.status_code == 200
    payload_question = resp_question.json()
    assert payload_question["state"] == "ready"
    assert payload_question["suggestions"] is None
    assert len(payload_question["replies"]) == 1
    assert "默认 Checklist" in payload_question["replies"][0]
    assert "CHK-001" in payload_question["replies"][0]

    resp3 = client.post(
        "/agent/message",
        json={
            "session_id": session_id,
            "message": "请改用 checklist: [{\"id\":\"CHK-900\",\"description\":\"描述覆盖率\"}]",
        },
    )
    assert resp3.status_code == 200
    payload3 = resp3.json()
    assert payload3["state"] == "ready"
    assert any(item["checklist_id"] == "CHK-900" for item in payload3["suggestions"])
    assert len(payload3["replies"]) == 1
    assert "已更新 Checklist 并重新执行审查。" in payload3["replies"][0]
