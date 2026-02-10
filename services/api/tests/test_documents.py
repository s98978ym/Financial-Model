"""Document upload tests."""


def test_upload_text(client, sample_project):
    resp = client.post(
        "/v1/documents/upload",
        data={
            "project_id": sample_project,
            "kind": "text",
            "text": "テスト事業計画書の内容です。",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["project_id"] == sample_project
    assert data["kind"] == "text"
    assert "id" in data
    assert data["extracted_chars"] > 0


def test_upload_missing_content(client, sample_project):
    """Upload with neither text nor file should fail."""
    resp = client.post(
        "/v1/documents/upload",
        data={
            "project_id": sample_project,
            "kind": "text",
        },
    )
    assert resp.status_code == 422


def test_upload_file(client, sample_project):
    """Upload a simple text file."""
    resp = client.post(
        "/v1/documents/upload",
        data={
            "project_id": sample_project,
            "kind": "file",
        },
        files={"file": ("test.txt", b"Sample plan content for testing.", "text/plain")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["filename"] == "test.txt"
