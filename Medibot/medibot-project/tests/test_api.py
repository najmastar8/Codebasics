from types import SimpleNamespace

from fastapi.testclient import TestClient

import src.main as main


client = TestClient(main.app)


def setup_function():
    main._hybrid_search = SimpleNamespace(
        hybrid_search=lambda question, role, limit: [
            {
                "chunk_id": "general-1",
                "text": "General policy context",
                "metadata": {
                    "source_document": "handbook.pdf",
                    "section_title": "General",
                    "collection": "general",
                },
            }
        ]
    )
    main._llm_service = SimpleNamespace(
        generate_answer=lambda question, chunks: "Grounded answer [1]."
    )
    main._sql_rag = SimpleNamespace(answer=lambda question: "There are 4 claims.")


def login(username="dr.mehta", password="password123"):
    response = client.post(
        "/login",
        json={"username": username, "password": password},
    )
    return response, {"Authorization": "Bearer " + response.json()["access_token"]}


def test_invalid_login_returns_401():
    response = client.post(
        "/login",
        json={"username": "dr.mehta", "password": "wrong"},
    )
    assert response.status_code == 401


def test_invalid_role_returns_400():
    response, headers = login()
    assert response.status_code == 200
    assert client.get("/collections/not-a-role", headers=headers).status_code == 400


def test_health_returns_successfully():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_uses_token_role_not_frontend_role():
    _, headers = login()
    response = client.post(
        "/chat",
        headers=headers,
        json={"question": "What is the policy?", "role": "admin"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "doctor"
    assert response.json()["retrieval_type"] == "hybrid_rag"


def test_analytical_chat_routes_for_admin():
    _, headers = login("admin.sys")
    response = client.post(
        "/chat",
        headers=headers,
        json={"question": "How many claims?", "role": "nurse"},
    )
    assert response.status_code == 200
    assert response.json()["retrieval_type"] == "sql_rag"
