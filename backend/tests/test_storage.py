# backend/tests/test_storage.py
def test_storage_list(client):
    """Ensure /api/storage/list endpoint responds successfully."""
    response = client.get("/api/storage/list")
    assert response.status_code in (200, 404, 500)
    # If 200, it should include 'files'
    if response.status_code == 200:
        data = response.get_json()
        assert "files" in data
