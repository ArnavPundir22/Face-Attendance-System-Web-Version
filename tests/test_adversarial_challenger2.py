"""
Adversarial Challenge & Stress-Test Suite (Challenger 2).

Empirically challenges:
1. PostgREST pagination (>1,000 rows e.g. 1,126 items) with fetch_all_records.
2. Complete absence of 512D arrays / embeddings in /api/academic_options.
3. Session cookie SameSite and Secure configurations across diverse headers.
4. Data completeness across attendance and drift routes for >1,000 items.
"""

import copy
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock
import pytest
from flask import session


# ---------------------------------------------------------------------------
# Mock PostgREST Query Builder for Stress-Testing Pagination
# ---------------------------------------------------------------------------

class MockPostgrestResponse:
    def __init__(self, data: Optional[List[Dict[str, Any]]]):
        self.data = data


class MockPostgrestQueryBuilder:
    def __init__(self, dataset: List[Dict[str, Any]]):
        self._dataset = dataset
        self._select_fields = "*"
        self._order_calls = []
        self._range_calls = []
        self._current_start = 0
        self._current_end = len(dataset) - 1

    def select(self, fields: str = "*"):
        self._select_fields = fields
        return self

    def order(self, field: str, desc: bool = False):
        self._order_calls.append((field, desc))
        return self

    def range(self, start: int, end: int):
        self._range_calls.append((start, end))
        self._current_start = start
        self._current_end = end
        return self

    def execute(self) -> MockPostgrestResponse:
        # Slicing in Python: range(start, end) is inclusive in PostgREST
        sliced = self._dataset[self._current_start : self._current_end + 1]
        return MockPostgrestResponse(copy.deepcopy(sliced))


class MockPostgrestClient:
    def __init__(self, table_datasets: Dict[str, List[Dict[str, Any]]]):
        self._tables = table_datasets
        self.query_builders: List[MockPostgrestQueryBuilder] = []

    def table(self, table_name: str) -> MockPostgrestQueryBuilder:
        dataset = self._tables.get(table_name, [])
        qb = MockPostgrestQueryBuilder(dataset)
        self.query_builders.append(qb)
        return qb


# ---------------------------------------------------------------------------
# 1. PostgREST Pagination Stress Tests (fetch_all_records)
# ---------------------------------------------------------------------------

class TestPostgrestPaginationAdversarial:
    """Stress-test fetch_all_records under diverse dataset sizes and boundaries."""

    def test_pagination_1126_records_termination_and_completeness(self):
        """Verify fetch_all_records terminates and returns all 1,126 items without skipping or duplication."""
        from src.utils.db import fetch_all_records

        total_records = 1126
        dataset = [
            {"id": f"STU_{i:04d}", "name": f"Student {i}", "enrollment_year": 2020 + (i % 4)}
            for i in range(total_records)
        ]
        mock_client = MockPostgrestClient({"students": dataset})

        records = fetch_all_records(
            client=mock_client,
            table_name="students",
            select_fields="id, name, enrollment_year",
            batch_size=1000
        )

        assert len(records) == 1126
        assert len(mock_client.query_builders) == 2, "Expected exactly 2 page requests for 1,126 items with batch_size=1000"

        # Verify page ranges
        first_page_range = mock_client.query_builders[0]._range_calls[0]
        second_page_range = mock_client.query_builders[1]._range_calls[0]
        assert first_page_range == (0, 999)
        assert second_page_range == (1000, 1999)

        # Verify zero off-by-one errors: all IDs match precisely
        assert [r["id"] for r in records] == [f"STU_{i:04d}" for i in range(total_records)]

    def test_pagination_exact_1000_boundary(self):
        """Verify exact multiple of batch_size (1000) terminates after receiving empty page."""
        from src.utils.db import fetch_all_records

        dataset = [{"id": f"ID_{i}"} for i in range(1000)]
        mock_client = MockPostgrestClient({"items": dataset})

        records = fetch_all_records(client=mock_client, table_name="items", batch_size=1000)

        assert len(records) == 1000
        # Page 1 gets 1000 items; Page 2 gets 0 items (len < batch_size) -> break
        assert len(mock_client.query_builders) == 2
        assert mock_client.query_builders[0]._range_calls[0] == (0, 999)
        assert mock_client.query_builders[1]._range_calls[0] == (1000, 1999)

    def test_pagination_exact_2000_boundary(self):
        """Verify exact multiple of 2,000 items terminates after 3 requests."""
        from src.utils.db import fetch_all_records

        dataset = [{"id": f"ID_{i}"} for i in range(2000)]
        mock_client = MockPostgrestClient({"items": dataset})

        records = fetch_all_records(client=mock_client, table_name="items", batch_size=1000)

        assert len(records) == 2000
        assert len(mock_client.query_builders) == 3
        assert mock_client.query_builders[0]._range_calls[0] == (0, 999)
        assert mock_client.query_builders[1]._range_calls[0] == (1000, 1999)
        assert mock_client.query_builders[2]._range_calls[0] == (2000, 2999)

    def test_pagination_empty_dataset(self):
        """Verify 0 records terminates on the first request."""
        from src.utils.db import fetch_all_records

        mock_client = MockPostgrestClient({"items": []})
        records = fetch_all_records(client=mock_client, table_name="items", batch_size=1000)

        assert records == []
        assert len(mock_client.query_builders) == 1
        assert mock_client.query_builders[0]._range_calls[0] == (0, 999)

    def test_pagination_none_data_response(self):
        """Verify robustness if query.execute().data is None."""
        from src.utils.db import fetch_all_records

        mock_client = MagicMock()
        mock_qb = MagicMock()
        mock_qb.select.return_value = mock_qb
        mock_qb.range.return_value = mock_qb
        mock_res = MagicMock()
        mock_res.data = None
        mock_qb.execute.return_value = mock_res
        mock_client.table.return_value = mock_qb

        records = fetch_all_records(client=mock_client, table_name="items", batch_size=1000)
        assert records == []

    def test_pagination_custom_batch_size(self):
        """Verify pagination with custom batch_size=250 over 1,126 records (5 pages)."""
        from src.utils.db import fetch_all_records

        dataset = [{"id": i} for i in range(1126)]
        mock_client = MockPostgrestClient({"items": dataset})

        records = fetch_all_records(client=mock_client, table_name="items", batch_size=250)

        assert len(records) == 1126
        # Pages: 250, 250, 250, 250, 126 -> 5 queries total
        assert len(mock_client.query_builders) == 5
        assert [r["id"] for r in records] == list(range(1126))

    def test_pagination_order_field_ordering_and_desc(self):
        """Verify multi-column ordering parses and passes desc flag correctly."""
        from src.utils.db import fetch_all_records

        dataset = [{"id": 1, "score": 90}]
        mock_client = MockPostgrestClient({"items": dataset})

        fetch_all_records(
            client=mock_client,
            table_name="items",
            order_field="score, id",
            desc=True
        )

        qb = mock_client.query_builders[0]
        assert ("score", True) in qb._order_calls
        assert ("id", True) in qb._order_calls


# ---------------------------------------------------------------------------
# 2. Absence of 512D Arrays in /api/academic_options
# ---------------------------------------------------------------------------

class TestAcademicOptionsVectorExclusion:
    """Stress-test /api/academic_options to ensure no 512D biometric vectors are leaked."""

    def test_api_academic_options_deep_inspection(self, client):
        """Inspect all keys and nested structures of /api/academic_options response."""
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "tester"

        resp = client.get("/api/academic_options")
        assert resp.status_code == 200
        data = resp.get_json()

        assert set(data.keys()) == {"programs", "branches", "years"}

        # Recursive check for any vector / 512D data
        def assert_no_vector(val, path="root"):
            if isinstance(val, dict):
                for k, v in val.items():
                    assert "embedding" not in k.lower(), f"Disallowed key '{k}' found at {path}"
                    assert "vector" not in k.lower(), f"Disallowed key '{k}' found at {path}"
                    assert_no_vector(v, f"{path}.{k}")
            elif isinstance(val, (list, tuple)):
                assert len(val) != 512, f"Array of length 512 detected at {path}"
                for i, item in enumerate(val):
                    if isinstance(item, (int, float, str, bool)) or item is None:
                        continue
                    assert_no_vector(item, f"{path}[{i}]")

        assert_no_vector(data)

        # Confirm all items in lists are simple scalar primitives
        for p in data["programs"]:
            assert isinstance(p, str)
        for b in data["branches"]:
            assert isinstance(b, str)
        for y in data["years"]:
            assert isinstance(y, (int, str))

    def test_api_academic_options_select_fields_projection(self, monkeypatch, client):
        """Verify fetch_all_records is called strictly with scalar fields for students table."""
        from src.blueprints import attendance

        captured_select_fields = []

        def spy_fetch_all_records(client, table_name, select_fields="*", **kwargs):
            if table_name == "students":
                captured_select_fields.append(select_fields)
                return [{"id": "S1", "enrollment_year": 2024, "academic_year": "2024-2025"}]
            return []

        monkeypatch.setattr(attendance, "fetch_all_records", spy_fetch_all_records)

        with client.session_transaction() as sess:
            sess["logged_in"] = True

        resp = client.get("/api/academic_options")
        assert resp.status_code == 200
        assert len(captured_select_fields) == 1
        assert "embedding" not in captured_select_fields[0]
        assert captured_select_fields[0] == "id, enrollment_year, academic_year"

    def test_api_academic_options_with_vector_in_database(self, monkeypatch, client):
        """Even if database returned embedding column, route never leaks it to the client."""
        from src.blueprints import attendance

        fake_students_with_embeddings = [
            {
                "id": f"STU_{i}",
                "enrollment_year": 2023,
                "academic_year": "2023-2024",
                "embedding": [0.012] * 512,  # Simulated 512D ArcFace vector
            }
            for i in range(10)
        ]

        def mock_fetch(client, table_name, **kwargs):
            if table_name == "students":
                return fake_students_with_embeddings
            return []

        monkeypatch.setattr(attendance, "fetch_all_records", mock_fetch)

        with client.session_transaction() as sess:
            sess["logged_in"] = True

        resp = client.get("/api/academic_options")
        assert resp.status_code == 200
        data = resp.get_json()

        # The JSON response must not contain any embeddings
        assert "embedding" not in data
        assert data["years"] == [2023]


# ---------------------------------------------------------------------------
# 3. Session Cookie SameSite & Security Matrix
# ---------------------------------------------------------------------------

class TestSessionCookieSameSiteAdversarial:
    """Stress-test session cookie SameSite and Secure flags across diverse headers."""

    @pytest.mark.parametrize(
        "base_url,headers,expected_secure",
        [
            ("http://localhost", {}, False),
            ("https://localhost", {}, True),
            ("http://localhost", {"X-Forwarded-Proto": "https"}, True),
            ("http://localhost", {"X-Forwarded-Proto": "http"}, False),
            ("http://localhost", {"X-Forwarded-Proto": "HTTPS"}, False),  # Case-sensitive exact match in hook
            ("http://localhost", {"X-Forwarded-Proto": "HTTP"}, False),
            ("http://localhost", {"X-Forwarded-Proto": "https, http"}, False),
            ("http://localhost", {"X-Forwarded-Proto": "wss"}, True),  # Werkzeug ProxyFix treats wss as secure
            ("http://localhost", {"X-Forwarded-Proto": ""}, False),
            ("http://localhost", {"X-Forwarded-Proto": "unknown-proto"}, False),
            ("https://localhost", {"X-Forwarded-Proto": "http"}, False),  # ProxyFix overrides scheme to http
        ],
    )
    def test_samesite_invariance_across_diverse_headers(self, app, client, base_url, headers, expected_secure):
        """Verify SESSION_COOKIE_SAMESITE is strictly 'Lax' under all request conditions."""
        client.get("/healthz", base_url=base_url, headers=headers)
        assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
        assert app.config["SESSION_COOKIE_SECURE"] is expected_secure

    def test_set_cookie_header_contains_samesite_lax(self, client):
        """Empirically inspect raw Set-Cookie header emitted when session changes via /logout."""
        # 1. Plain HTTP
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "tester"

        resp_http = client.get("/logout", base_url="http://localhost")
        cookie_http = resp_http.headers.get("Set-Cookie", "")
        assert "SameSite=Lax" in cookie_http
        assert "HttpOnly" in cookie_http
        assert "Secure" not in cookie_http

        # 2. Plain HTTPS
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "tester"

        resp_https = client.get("/logout", base_url="https://localhost")
        cookie_https = resp_https.headers.get("Set-Cookie", "")
        assert "SameSite=Lax" in cookie_https
        assert "HttpOnly" in cookie_https
        assert "Secure" in cookie_https

        # 3. Proxied HTTPS via X-Forwarded-Proto: https
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "tester"

        resp_proxy = client.get("/logout", base_url="http://localhost", headers={"X-Forwarded-Proto": "https"})
        cookie_proxy = resp_proxy.headers.get("Set-Cookie", "")
        assert "SameSite=Lax" in cookie_proxy
        assert "HttpOnly" in cookie_proxy
        assert "Secure" in cookie_proxy


# ---------------------------------------------------------------------------
# 4. Roster & Dashboard >1,000 Data Completeness Integration
# ---------------------------------------------------------------------------

class TestRosterCompletenessOver1000:
    """Verify get_attendance_data and admin_drift handle >1,000 students without truncation."""

    def test_get_attendance_data_1126_students(self, monkeypatch, client):
        """Ensure get_attendance_data parses batch years for all 1,126 students."""
        from src.blueprints import attendance

        dataset_1126 = [
            {
                "id": f"2022BCSE{i:04d}",
                "name": f"Student {i}",
                "branch": "CSE",
                "program": "B.Tech",
                "enrollment_year": 2022,
                "academic_year": "2022-2026",
            }
            for i in range(1126)
        ]

        def mock_fetch(client, table_name, **kwargs):
            if table_name == "students":
                return dataset_1126
            return []

        monkeypatch.setattr(attendance, "fetch_all_records", mock_fetch)

        # Mock attendance table to avoid live DB call
        mock_sb = MagicMock()
        mock_table = MagicMock()
        mock_query = MagicMock()
        mock_query.execute.return_value = MockPostgrestResponse([])
        mock_table.select.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_sb.table.return_value = mock_table
        monkeypatch.setattr(attendance, "supabase_admin", mock_sb)

        with client.session_transaction() as sess:
            sess["logged_in"] = True

        resp = client.get("/get_attendance_data")
        assert resp.status_code == 200
        data = resp.get_json()

        assert len(data["students"]) == 1126
        # Check student at index 1125 has correct batch year populated
        assert data["students"][1125]["batch_year"] == 2022

    def test_admin_drift_1126_students(self, monkeypatch, client):
        """Ensure admin_drift counts summary for all 1,126 students."""
        from src.blueprints import admin

        dataset_1126 = [
            {
                "id": f"STU_{i}",
                "name": f"Student {i}",
                "program": "B.Tech",
                "branch": "CSE",
                "current_ewma_drift": 0.05,
                "drift_alert_level": "HEALTHY" if i < 1100 else "WARNING",
            }
            for i in range(1126)
        ]

        def mock_fetch(client, table_name, **kwargs):
            if table_name == "students":
                return dataset_1126
            return []

        monkeypatch.setattr(admin, "fetch_all_records", mock_fetch)

        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["is_admin"] = True

        resp = client.get("/admin/drift")
        assert resp.status_code == 200
        # HTML should render total students 1126
        assert b"1,126" in resp.data or b"1126" in resp.data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
