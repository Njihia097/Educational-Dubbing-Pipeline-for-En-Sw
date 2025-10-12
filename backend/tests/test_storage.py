from app.storage import storage

def test_minio_upload_download():
    data = b"Hello storage!"
    key = "test/hello.txt"

    url = storage.put(key, data)
    assert url is not None

    content = storage.get(key)
    assert content == data

    storage.delete(key)
