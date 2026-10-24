from unittest.mock import MagicMock, patch
import pytest

def test_admin_academics_unauthorized(client):
    """Ensure non-admin users cannot access the academics management route."""
    # Without any session
    res = client.get("/admin/academics")
    # Redirects to /login or returns error
    assert res.status_code in (200, 302)
    if res.status_code == 200:
        assert b"Admin access required" in res.data

    # Logged in as non-admin user
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "regular_user"
        sess["is_admin"] = False

    res = client.get("/admin/academics")
    assert b"Admin access required" in res.data


def test_admin_academics_get_success(client):
    """Ensure admin users can view the academics management page with counts."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "admin"
        sess["is_admin"] = True

    res = client.get("/admin/academics")
    assert res.status_code == 200
    assert b"Manage Programs &amp; Branches" in res.data or b"Manage Programs & Branches" in res.data
    assert b"Programs" in res.data
    assert b"Branches" in res.data
    assert b"Select All" in res.data
    assert b"delete-modal" in res.data


def test_admin_academics_json_bulk_delete(client):
    """Test bulk deletion of multiple programs and branches via JSON API."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "admin"
        sess["is_admin"] = True

    with patch("src.blueprints.admin.supabase") as mock_supabase:
        mock_delete = MagicMock()
        mock_supabase.table.return_value.delete.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(data=[])

        payload = {
            "action": "delete_multiple",
            "programs": ["TestProg1", "TestProg2"],
            "branches": ["TestBranch1"]
        }

        res = client.post(
            "/admin/academics",
            json=payload,
            headers={"Accept": "application/json"}
        )

        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["deleted_count"] == 3


def test_admin_academics_form_bulk_delete(client):
    """Test bulk deletion of programs via standard form POST."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "admin"
        sess["is_admin"] = True

    with patch("src.blueprints.admin.supabase") as mock_supabase:
        mock_supabase.table.return_value.delete.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(data=[])

        form_data = {
            "action": "delete_multiple",
            "type": "program",
            "values": ["UnwantedProgA", "UnwantedProgB"]
        }

        res = client.post("/admin/academics", data=form_data)
        assert res.status_code == 302
        assert "/admin/academics" in res.headers["Location"]
