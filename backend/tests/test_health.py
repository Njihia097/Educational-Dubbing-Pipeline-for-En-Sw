def test_health_endpoint(client):
    """Check if /health endpoint returns OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"

# if __name__ == "__main__":
#     import pytest
#     pytest.main([__file__])




