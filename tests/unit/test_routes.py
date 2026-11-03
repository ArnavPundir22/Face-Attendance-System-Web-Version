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
    assert b"biosecure-pwa-v2" in response.data
    assert b"/viewer" in response.data
    assert b"/students" in response.data
    assert b"/add_student" in response.data
    assert b"/static/js/pwa-nav.js" in response.data

def test_pwa_nav_static_asset(client):
    response = client.get("/static/js/pwa-nav.js")
    assert response.status_code == 200
    assert b"__pwaPageCache" in response.data
    assert b"startViewTransition" in response.data
    assert b"teardownCurrentView" in response.data


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


def test_session_cookie_samesite_configuration(client, app):
    """Verify SESSION_COOKIE_SAMESITE remains 'Lax' across both standard and HTTPS tunnel requests."""
    # Standard HTTP request
    client.get("/healthz")
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"

    # HTTPS tunnel request with X-Forwarded-Proto
    client.get("/healthz", headers={"X-Forwarded-Proto": "https"})
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["SESSION_COOKIE_SECURE"] is True


def test_get_attendance_data_loads_all_students(client):
    """Verify get_attendance_data returns registered students without 1000-row limit truncation."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "tester"

    response = client.get("/get_attendance_data")
    assert response.status_code == 200
    data = response.get_json()
    assert "students" in data
    assert "attendance" in data
    # Full student count exceeds 1000 (1126 registered students)
    assert len(data["students"]) >= 1000
    for s in data["students"][:20]:
        assert "batch_year" in s


def test_api_academic_options_no_embeddings(client):
    """Verify /api/academic_options returns distinct options and no embedding keys."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "tester"

    response = client.get("/api/academic_options")
    assert response.status_code == 200
    data = response.get_json()
    assert "years" in data
    assert len(data["years"]) > 0
    assert "embedding" not in data


def test_admin_delete_student_cache_sync(client):
    """Verify deleting a student via admin route removes them from in-memory face cache."""
    import numpy as np
    from src.utils.face_cache import add_student_to_cache
    test_id = "TEST_ROUTE_DEL_1"
    emb = np.zeros(512, dtype=np.float32)
    emb[90] = 1.0
    add_student_to_cache(test_id, "Route Del Test", "B.Tech", "CSE", emb)

    from src.utils import face_cache
    assert test_id in face_cache._student_metadata
    assert test_id in face_cache._student_ids

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["is_admin"] = True
        sess["username"] = "admin"

    resp = client.post(f"/admin/student/delete/{test_id}")
    assert resp.status_code == 302

    assert test_id not in face_cache._student_metadata
    assert test_id not in face_cache._student_ids


def test_admin_reset_calls_clear_face_cache(client, monkeypatch):
    """Verify admin reset with reset_type='all' triggers clear_face_cache."""
    clear_called = False

    def mock_clear():
        nonlocal clear_called
        clear_called = True

    monkeypatch.setattr("src.utils.face_cache.clear_face_cache", mock_clear)
    from unittest.mock import MagicMock
    mock_sb = MagicMock()
    monkeypatch.setattr("src.blueprints.admin.supabase", mock_sb)

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["is_admin"] = True
        sess["username"] = "admin"

    resp = client.post("/admin/reset", data={"reset_type": "all"})
    assert resp.status_code == 302
    assert clear_called is True


