def test_mcp_without_api_key_returns_401(client):
    response = client.get("/mcp")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key."


def test_mcp_with_invalid_api_key_returns_401(client):
    response = client.get(
        "/mcp",
        headers={"Authorization": "Bearer invalid-test-api-key"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key."