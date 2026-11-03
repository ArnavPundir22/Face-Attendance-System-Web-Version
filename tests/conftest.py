import os
import sys
from unittest.mock import patch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from src import create_app


@pytest.fixture(scope="session")
def app():
    """Create and configure a Flask app instance for testing."""
    os.environ.setdefault("FLASK_SECRET_KEY", "test_secret_key_for_biosecure_audit_testing_1234567890")
    with patch("src.security.license_verifier.enforce_license_boot", return_value={"customer": "Test", "version": 1}):
        test_app = create_app()
        test_app.config.update({
            "TESTING": True,
        })
        return test_app


@pytest.fixture(autouse=True)
def mock_licensing_for_general_tests(monkeypatch, request):
    """Shield existing unit tests from license expiration so they run hermetically."""
    if "test_licensing" not in request.node.nodeid:
        monkeypatch.setattr(
            "src.security.license_verifier.enforce_license_boot",
            lambda *args, **kwargs: {"customer": "Test", "version": 1},
        )
        monkeypatch.setattr(
            "src.security.license_verifier.check_license_runtime",
            lambda *args, **kwargs: (False, None),
        )


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()
