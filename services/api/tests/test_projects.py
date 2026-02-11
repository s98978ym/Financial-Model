"""Project CRUD tests."""


def test_create_project(client):
    resp = client.post("/v1/projects", json={"name": "My Project"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Project"
    assert "id" in data


def test_create_project_defaults(client):
    """Creating project without name should use default."""
    resp = client.post("/v1/projects", json={})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Untitled"


def test_list_projects(client, sample_project):
    resp = client.get("/v1/projects")
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) >= 1
    assert any(p["id"] == sample_project for p in projects)


def test_get_project(client, sample_project):
    resp = client.get(f"/v1/projects/{sample_project}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sample_project


def test_get_project_not_found(client):
    resp = client.get("/v1/projects/nonexistent-id")
    assert resp.status_code == 404


def test_get_project_state(client, sample_project):
    resp = client.get(f"/v1/projects/{sample_project}/state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project"]["id"] == sample_project
    assert "phase_results" in data
    assert "documents" in data


def test_get_project_state_not_found(client):
    resp = client.get("/v1/projects/nonexistent-id/state")
    assert resp.status_code == 404
