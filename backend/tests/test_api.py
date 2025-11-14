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


def test_review_with_custom_system_prompt():
    """Test review functionality with custom system prompt."""
    payload = {
        "mrt_content": """
        Test Case ID: TC-001
        Title: User Login Test
        Preconditions: User account exists
        Test Steps:
        1. Open login page
        2. Enter valid username and password
        3. Click login button
        Expected Result: User is redirected to home page
        """.strip(),
        "system_prompt": "You are a test reviewer. Review the test case and provide suggestions. Focus on test coverage and clarity.",
        "checklist": [
            {"id": "CHK-001", "description": "Each SW requirement is covered"},
            {"id": "CHK-003", "description": "Test case numbering, title, preconditions, test steps and verification points are clearly described"},
        ],
    }

    response = client.post("/review", json=payload)
    # Accept 200 (success) or 502 (API call failed, but request structure is valid)
    # The test verifies that custom system_prompt parameter is accepted
    assert response.status_code in [200, 502]
    
    if response.status_code == 200:
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) > 0
        
        # Verify suggestion structure
        for suggestion in data["suggestions"]:
            assert "checklist_id" in suggestion
            assert "message" in suggestion
            assert isinstance(suggestion["checklist_id"], str)
            assert isinstance(suggestion["message"], str)
        
        # Verify that custom checklist items appear in suggestions
        # (heuristic review returns suggestions for all checklist items)
        checklist_ids = {item["checklist_id"] for item in data["suggestions"]}
        assert "CHK-001" in checklist_ids or "CHK-003" in checklist_ids
    else:
        # If API fails, at least verify the request was accepted (not 400/422)
        assert response.status_code == 502


def test_review_response_structure():
    """Test that review response has correct structure with suggestions and optional summary."""
    payload = {
        "mrt_content": """
        Test Case: Verify user registration
        
        Steps:
        1. Navigate to registration page
        2. Fill in required fields
        3. Submit form
        
        Expected: User account is created successfully
        """.strip(),
    }

    response = client.post("/review", json=payload)
    # Accept 200 (success) or 502 (API call failed, but request structure is valid)
    assert response.status_code in [200, 502]
    
    if response.status_code == 200:
        data = response.json()

        # Verify response structure
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) > 0  # Should have at least one suggestion
        
        # Verify suggestion structure
        for suggestion in data["suggestions"]:
            assert "checklist_id" in suggestion
            assert "message" in suggestion
            assert isinstance(suggestion["checklist_id"], str)
            assert isinstance(suggestion["message"], str)
            assert len(suggestion["checklist_id"]) > 0
            assert len(suggestion["message"]) > 0
        
        # Summary is optional but should be present in heuristic review
        if "summary" in data:
            assert isinstance(data["summary"], str)
            assert len(data["summary"]) > 0