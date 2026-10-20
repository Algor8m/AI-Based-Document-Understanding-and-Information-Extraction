from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_and_info():
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    info = client.get("/api/v1/info").json()
    assert info["schema_version"] == "1.0"
    assert info["supported_file_types"] == ["PNG", "JPEG"]


def test_upload_success(monkeypatch, png_bytes):
    monkeypatch.setattr("api.main.prepare_document", lambda data, filename, document_id, options: type("R", (), {"to_dict": lambda self: {
        "schema_version": "1.0", "document_id": document_id or "generated", "source": {"type": "image", "filename": filename}, "text": "mock OCR", "metadata": {"page_count": 1}, "warnings": []}})())
    response = client.post("/api/v1/documents/prepare", files={"file": ("sample.png", png_bytes, "image/png")}, data={"document_id": "given"})
    assert response.status_code == 200
    assert response.json()["document_id"] == "given"
    assert response.json()["text"] == "mock OCR"


def test_upload_errors(monkeypatch):
    response = client.post("/api/v1/documents/prepare", files={"file": ("x.gif", b"xx", "image/gif")})
    assert response.status_code == 415
    assert response.json()["detail"]["error"]["code"] == "UNSUPPORTED_FILE_FORMAT"
    response = client.post("/api/v1/documents/prepare", files={"file": ("x.png", b"", "image/png")})
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "EMPTY_INPUT"


def test_consecutive_request_isolation(monkeypatch, png_bytes):
    def fake(data, filename, document_id, options):
        text = "first" if document_id == "one" else "second"
        return type("R", (), {"to_dict": lambda self: {"document_id": document_id, "text": text}})()
    monkeypatch.setattr("api.main.prepare_document", fake)
    for doc_id, expected in [("one", "first"), ("two", "second")]:
        response = client.post("/api/v1/documents/prepare", files={"file": ("x.png", png_bytes, "image/png")}, data={"document_id": doc_id})
        assert response.json()["text"] == expected
