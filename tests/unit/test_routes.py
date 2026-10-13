import pytest

def test_healthz_endpoint(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert "service" in data

def test_manifest_endpoint(client):
    response = client.get("/manifest.json")
    assert response.status_code == 200
    data = response.get_json()
    assert "name" in data
    assert "start_url" in data

def test_offline_page_endpoint(client):
    response = client.get("/offline")
    assert response.status_code == 200
    assert b"Offline Mode" in response.data or b"offline" in response.data.lower()

def test_service_worker_endpoint(client):
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert response.headers.get("Service-Worker-Allowed") == "/"

def test_error_404_handler(client):
    # Unauthenticated non-existent route redirects to /login per security policy
    unauth_resp = client.get("/non_existent_route_404")
    assert unauth_resp.status_code == 302
    assert "/login" in unauth_resp.headers.get("Location", "")

    # Authenticated non-existent route returns 404 error page
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    auth_resp = client.get("/non_existent_route_404")
    assert auth_resp.status_code == 404


def test_api_academic_options(client):
    # Set session logged_in so before_request allows route access
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "tester"

    response = client.get("/api/academic_options")
    assert response.status_code == 200
    data = response.get_json()
    assert "programs" in data
    assert "branches" in data
    assert "years" in data
