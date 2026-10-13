import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from src import create_app

@pytest.fixture(scope="session")
def app():
    """Create and configure a Flask app instance for testing."""
    os.environ.setdefault("FLASK_SECRET_KEY", "test_secret_key_for_biosecure_audit_testing_1234567890")
    test_app = create_app()
    test_app.config.update({
        "TESTING": True,
    })
    return test_app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()
