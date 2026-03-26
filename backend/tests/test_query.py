def test_search_documents(client):
    workspace = client.post("/workspaces", json={"name": "Search Workspace"}).json()
    workspace_id = workspace["id"]

    client.post("/documents", json={"workspace_id": workspace_id, "content": "FastAPI is great"})
    client.post("/documents", json={"workspace_id": workspace_id, "content": "SQLAlchemy ORM rocks"})
    client.post("/documents", json={"workspace_id": workspace_id, "content": "FastAPI with SQLAlchemy"})

    response = client.post("/query", json={"query": "FastAPI"})
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) >= 2
    assert all("FastAPI" in r["content"] for r in results)


def test_search_documents_no_match(client):
    workspace = client.post("/workspaces", json={"name": "Empty Search Workspace"}).json()
    workspace_id = workspace["id"]

    client.post("/documents", json={"workspace_id": workspace_id, "content": "Hello world"})

    response = client.post("/query", json={"query": "zzznomatchzzz"})
    assert response.status_code == 200
    results = response.json()
    assert results == []