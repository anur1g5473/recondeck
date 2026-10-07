import threading
from types import SimpleNamespace

import app
import recondeck.store as store
from recondeck import orchestrator
from recondeck.models import Scan


def _save_test_scan(scan_id):
    scan = Scan(
        id=scan_id,
        target={"hostname": "example.com", "registered_domain": "example.com"},
        options={},
        status="done",
        created_at="2026-01-01T00:00:00Z",
    )
    store.save_scan(scan)


def _api_headers():
    return {
        "Host": "127.0.0.1:5000",
        "X-ReconDeck-Token": app.TOKEN,
    }


def test_delete_scan_api_removes_saved_scan(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(app, "CURRENT_SCAN_ID", None)
    monkeypatch.setattr(app, "CURRENT_SCAN", None)
    monkeypatch.setattr(app, "CURRENT_SCAN_THREAD", None)
    _save_test_scan("scan-test_1")

    response = app.app.test_client().delete(
        "/api/scans/scan-test_1",
        headers=_api_headers(),
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "deleted", "scan_id": "scan-test_1"}
    assert not (tmp_path / "scans" / "scan-test_1").exists()


def test_delete_scan_api_rejects_running_scan(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(app, "CURRENT_SCAN_ID", "scan-busy")
    _save_test_scan("scan-busy")

    finish_worker = threading.Event()
    worker = threading.Thread(target=finish_worker.wait)
    worker.start()
    monkeypatch.setattr(app, "CURRENT_SCAN_THREAD", worker)
    try:
        response = app.app.test_client().delete(
            "/api/scans/scan-busy",
            headers=_api_headers(),
        )
    finally:
        finish_worker.set()
        worker.join()

    assert response.status_code == 409
    assert (tmp_path / "scans" / "scan-busy" / "scan.json").exists()


def test_delete_scan_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "PROJECT_ROOT", tmp_path)

    try:
        store.delete_scan("../outside")
    except ValueError:
        pass
    else:
        raise AssertionError("path traversal scan ID should be rejected")


def test_command_activity_is_saved_while_scan_is_running(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "PROJECT_ROOT", tmp_path)
    scan = Scan(
        id="scan-live-activity",
        target={"hostname": "example.com"},
        options={},
        status="running",
    )
    store.save_scan(scan)
    command = SimpleNamespace(
        id="command-1",
        stage="records",
        label="query_a",
        command_line="dig example.com A",
        duration_ms=42,
        exit_code=0,
        timed_out=False,
        truncated=False,
        stdout="192.0.2.1",
        stderr="",
    )

    orchestrator._log_command(scan, command)

    persisted_scan = store.load_scan("scan-live-activity")
    assert persisted_scan.commands[0]["label"] == "query_a"
    assert (tmp_path / "scans" / scan.id / "raw" / "command-1.txt").read_text() == "192.0.2.1"
