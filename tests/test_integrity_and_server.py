"""Tamper detection and server/UI regression tests."""
import pytest
from agents.base import AuditTrail


def test_audit_hmac_detects_entry_editing():
    audit = AuditTrail(secret_key="unit-test-secret")
    audit.log("runner", "worker", "RUN", {"status": "SUCCESS"})
    audit.log("runner", "worker", "STOP", {"status": "SUCCESS"})
    assert audit.verify_integrity()
    audit.logs[0]["event_type"] = "FORGED"
    assert not audit.verify_integrity()


def test_audit_hmac_detects_last_signature_editing():
    audit = AuditTrail(secret_key="unit-test-secret")
    audit.log("runner", "worker", "RUN", {"status": "SUCCESS"})
    audit.logs[0]["current_hash"] = "0" * 64
    assert not audit.verify_integrity()


def test_server_qec_routes():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from surface_code_qec.server import create_app
    client = TestClient(create_app(), raise_server_exceptions=False)
    assert client.get("/health").status_code == 200
    properties = client.get("/api/qec/properties/3")
    assert properties.status_code == 200
    assert properties.json()["n_stabilizers"] == 8
    cycle = client.post("/api/qec/cycle", json={"distance": 3, "error_rate": 0, "seed": 42})
    assert cycle.status_code == 200
    assert cycle.json()["residual_syndrome_weight"] == 0
    rare = client.post("/api/qec/rate", json={"distance": 3, "error_rate": 0.001, "trials": 5, "seed": 42})
    assert rare.status_code == 200
    assert rare.json()["logical_error_rate"] == 0.0
    invalid = client.post("/api/qec/cycle", json={"distance": 4, "error_rate": 0.1})
    assert invalid.status_code in (400, 422)
    assert client.get("/").status_code == 200
    assert client.get("/worker.js").status_code == 200
    assert client.get("/engine.py").status_code == 200
