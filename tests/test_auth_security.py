def test_protected_endpoint_without_token_returns_401(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_protected_endpoint_with_invalid_token_returns_401(client):
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-test-token"},
    )

    assert response.status_code == 401