

def test_create_document(client):
    workspace = client.post("/workspaces", json={"name": "Doc Workspace"}).json()
    workspace_id = workspace["id"]

    response = client.post("/documents", json={
        "workspace_id": workspace_id,
        "content": "This is a test document."
    })
    assert response.status_code == 200
    data = response.json()
    assert data["workspace_id"] == workspace_id
    assert data["content"] == "This is a test document."
    assert "id" in data


def test_get_documents_by_workspace(client):
    workspace = client.post("/workspaces", json={"name": "Filter Workspace"}).json()
    workspace_id = workspace["id"]

    client.post("/documents", json={"workspace_id": workspace_id, "content": "Doc One"})
    client.post("/documents", json={"workspace_id": workspace_id, "content": "Doc Two"})

    response = client.get(f"/documents?workspace_id={workspace_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert all(d["workspace_id"] == workspace_id for d in data)