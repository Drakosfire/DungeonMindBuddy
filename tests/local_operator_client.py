"""Explicit supported local authentication for non-auth endpoint owner tests."""
from fastapi.testclient import TestClient


def configure_local_operator(monkeypatch):
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")


class LocalOperatorTestClient(TestClient):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("client", ("127.0.0.1", 50000))
        super().__init__(*args, **kwargs)


NATIVE_TEST_TOKEN = "ci-owned-native-test-operator-token"


def configure_native_local_operator(monkeypatch):
    configure_local_operator(monkeypatch)
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", NATIVE_TEST_TOKEN)


class NativeLocalOperatorTestClient(LocalOperatorTestClient):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("headers", {"Authorization": f"Bearer {NATIVE_TEST_TOKEN}"})
        super().__init__(*args, **kwargs)
