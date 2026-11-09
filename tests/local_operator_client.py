"""Explicit supported local authentication for non-auth endpoint owner tests."""
from fastapi.testclient import TestClient


def configure_local_operator(monkeypatch):
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")


class LocalOperatorTestClient(TestClient):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("client", ("127.0.0.1", 50000))
        super().__init__(*args, **kwargs)
