def test_create_workspace(client):
    response = client.post("/workspaces", json={"name": "Test Workspace"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Workspace"
    assert "id" in data


def test_get_workspaces(client):
    client.post("/workspaces", json={"name": "Workspace A"})
    client.post("/workspaces", json={"name": "Workspace B"})

    response = client.get("/workspaces")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


def test_delete_workspace(client):
    create_response = client.post("/workspaces", json={"name": "To Delete"})
    workspace_id = create_response.json()["id"]

    delete_response = client.delete(f"/workspaces/{workspace_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Workspace deleted successfully"


def test_delete_workspace_not_found(client):
    response = client.delete("/workspaces/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Workspace not found"