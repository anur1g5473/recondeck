from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import threading
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file

import recondeck.config as config
from recondeck.config import APP_NAME, HOST, START_PORT, PROJECT_ROOT, TERMS_VERSION
from recondeck.compare import compare_scans
from recondeck.orchestrator import run_scan, new_scan_id
from recondeck.report import export_scan
from recondeck.security import ensure_valid_token, host_allowed, origin_allowed, set_app_token
from recondeck.store import delete_scan, list_recent_scans, load_scan, save_scan
from recondeck.validators import parse_target

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

TOKEN = secrets.token_urlsafe(32)
set_app_token(TOKEN)
ACTIVE_SCAN_LOCK = threading.Lock()
CURRENT_SCAN = None
CURRENT_SCAN_ID = None
CURRENT_SCAN_THREAD = None
CURRENT_SCAN_CANCEL = threading.Event()


def _scan_flag_counts(scan):
    counts = {"green": 0, "yellow": 0, "red": 0, "grey": 0}
    for finding in getattr(scan, "findings", []):
        flag = str(finding.flag).lower()
        if flag in counts:
            counts[flag] += 1
    return counts


def _settings_file() -> Path:
    settings_root = PROJECT_ROOT / "scans"
    settings_root.mkdir(exist_ok=True)
    return settings_root / "settings.json"


def _terms_accepted() -> bool:
    settings_file = _settings_file()
    if not settings_file.exists():
        return False
    try:
        data = json.loads(settings_file.read_text(encoding="utf-8"))
    except Exception:
        return False
    return bool(data.get("terms_version") == TERMS_VERSION)


def _run_scan_worker(target_value: str, options: dict, scan_id: str):
    global CURRENT_SCAN, CURRENT_SCAN_ID
    scan = run_scan(target_value, options, scan_id=scan_id)
    CURRENT_SCAN = scan
    CURRENT_SCAN_ID = scan.id


def _security_error(message: str, status: int = 403):
    response = jsonify({"error": message})
    response.status_code = status
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.before_request
def enforce_security():
    if request.path.startswith("/static"):
        return None
    if request.path.startswith("/api"):
        token = request.headers.get("X-ReconDeck-Token")
        if not ensure_valid_token(token):
            return _security_error("missing or invalid token", 403)
        host = request.headers.get("Host")
        port = request.environ.get("SERVER_PORT") or START_PORT
        if host and not host_allowed(host, port):
            return _security_error("host not allowed", 403)
        if request.method == "POST":
            origin = request.headers.get("Origin")
            if origin and not origin_allowed(origin, port):
                return _security_error("origin not allowed", 403)
    return None


@app.get("/terms")
def terms_page():
    token = request.args.get("token")
    if not token or not secrets.compare_digest(token, TOKEN):
        abort(403)
    return send_file(str(PROJECT_ROOT / "TERMS.md"), mimetype="text/plain")


@app.after_request
def add_security_headers(response):
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers.pop("Access-Control-Allow-Origin", None)
    response.headers.pop("Access-Control-Allow-Headers", None)
    return response


@app.get("/")
def index():
    token = request.args.get("token")
    if not token or not secrets.compare_digest(token, TOKEN):
        abort(403)
    html_file = PROJECT_ROOT / "static" / "index.html"
    html = html_file.read_text(encoding="utf-8")
    rendered = html.replace("{{TOKEN}}", TOKEN)
    return rendered


@app.get("/api/tools")
def api_tools():
    return jsonify({
        "dig": True,
        "whois": True,
        "versions": {"dig": "available", "whois": "available"},
    })


@app.post("/api/scans")
def api_start_scan():
    global CURRENT_SCAN, CURRENT_SCAN_ID, CURRENT_SCAN_THREAD, CURRENT_SCAN_CANCEL
    payload = request.get_json(silent=True) or {}
    target = payload.get("target")
    wordlist = payload.get("wordlist", "small")
    active = bool(payload.get("active", False))
    authorized = bool(payload.get("authorized", False))

    if not target:
        return jsonify({"error": "target is required"}), 400
    try:
        parse_target(str(target))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if active and not authorized:
        return jsonify({"error": "active probes require authorization"}), 400
    if CURRENT_SCAN_THREAD is not None and CURRENT_SCAN_THREAD.is_alive():
        return jsonify({"error": "scan already running"}), 409

    CURRENT_SCAN_CANCEL = threading.Event()
    scan_id = new_scan_id()
    options = {"wordlist": wordlist, "active": active, "authorized": authorized}
    CURRENT_SCAN = None
    CURRENT_SCAN_ID = scan_id
    CURRENT_SCAN_THREAD = threading.Thread(target=_run_scan_worker, args=(str(target), options, scan_id), daemon=True)
    CURRENT_SCAN_THREAD.start()

    return jsonify({"scan_id": scan_id})


@app.get("/api/scans/<scan_id>/export")
def api_export_scan(scan_id):
    try:
        scan = load_scan(scan_id)
    except FileNotFoundError:
        abort(404)
    fmt = request.args.get("format", "json").lower()
    if fmt == "json":
        return send_file(str(PROJECT_ROOT / "scans" / scan_id / "scan.json"), mimetype="application/json", as_attachment=True, download_name=f"{scan_id}.json")
    if fmt in {"md", "markdown"}:
        payload = export_scan(scan, "md")
        return app.response_class(payload, mimetype="text/markdown", headers={"Content-Disposition": f'attachment; filename="{scan_id}.md"'})
    if fmt == "html":
        payload = export_scan(scan, "html")
        return app.response_class(payload, mimetype="text/html", headers={"Content-Disposition": f'attachment; filename="{scan_id}.html"'})
    return jsonify({"error": "unsupported export format"}), 400


@app.get("/api/compare")
def api_compare_scans():
    a_id = request.args.get("a")
    b_id = request.args.get("b")
    if not a_id or not b_id:
        return jsonify({"error": "a and b are required"}), 400
    try:
        a = load_scan(a_id)
        b = load_scan(b_id)
    except FileNotFoundError:
        abort(404)
    return jsonify(compare_scans(a, b))


@app.get("/api/scans")
def api_list_scans():
    items = []
    for scan_id in list_recent_scans():
        try:
            scan = load_scan(scan_id)
        except Exception:
            continue
        items.append({
            "id": scan.id,
            "domain": scan.target.get("registered_domain") or scan.target.get("hostname"),
            "date": scan.created_at,
            "status": scan.status,
            "flag_counts": _scan_flag_counts(scan),
        })
    return jsonify(items)


@app.get("/api/scans/<scan_id>")
def api_get_scan(scan_id):
    try:
        scan = load_scan(scan_id)
    except FileNotFoundError:
        abort(404)
    total = max(len(scan.stages), 1)
    done = sum(1 for s in scan.stages if s.status == "done")
    data = scan.to_dict()
    data["progress"] = {"done": done, "total": total}
    data["recent_commands"] = scan.commands[-50:]
    data["flag_counts"] = _scan_flag_counts(scan)
    return jsonify(data)


@app.delete("/api/scans/<scan_id>")
def api_delete_scan(scan_id):
    global CURRENT_SCAN, CURRENT_SCAN_ID
    if scan_id == CURRENT_SCAN_ID and CURRENT_SCAN_THREAD is not None and CURRENT_SCAN_THREAD.is_alive():
        return jsonify({"error": "cannot delete a scan while it is running"}), 409
    try:
        delete_scan(scan_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except FileNotFoundError:
        abort(404)

    if scan_id == CURRENT_SCAN_ID:
        CURRENT_SCAN = None
        CURRENT_SCAN_ID = None
    return jsonify({"status": "deleted", "scan_id": scan_id})


@app.get("/api/scans/<scan_id>/commands/<command_id>")
def api_get_command_output(scan_id, command_id):
    file_path = Path(PROJECT_ROOT) / "scans" / scan_id / "raw" / f"{command_id}.txt"
    if not file_path.exists():
        abort(404)
    return send_file(file_path, mimetype="text/plain")


@app.post("/api/scans/<scan_id>/cancel")
def api_cancel_scan(scan_id):
    global CURRENT_SCAN_CANCEL
    CURRENT_SCAN_CANCEL.set()
    try:
        scan = load_scan(scan_id)
        scan.status = "cancelled"
        save_scan(scan)
    except Exception:
        pass
    return jsonify({"status": "cancelled"})


@app.post("/api/accept-terms")
def api_accept_terms():
    settings_root = PROJECT_ROOT / "scans"
    settings_root.mkdir(exist_ok=True)
    settings = settings_root / "settings.json"
    settings.write_text(json.dumps({"terms_version": TERMS_VERSION}, indent=2), encoding="utf-8")
    return jsonify({"ok": True})


def _choose_port(start_port):
    for port in range(start_port, start_port + 20):
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((HOST, port))
                return port
            except OSError:
                continue
    return start_port


def _open_browser(url):
    if os.environ.get("WSL_INTEROP") or os.environ.get("WSL_DISTRO_NAME"):
        try:
            result = subprocess.run(
                ["cmd.exe", "/c", "start", "", url],
                check=False,
                timeout=10,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"Could not open the Windows browser automatically ({exc}). Open this URL manually: {url}")
            return
        if result.returncode != 0:
            print(f"Could not open the Windows browser automatically. Open this URL manually: {url}")
        return

    if not webbrowser.open(url):
        print(f"Could not open a browser automatically. Open this URL manually: {url}")


def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--port", type=int, default=START_PORT)
    parser.add_argument("--allow-root", action="store_true")
    args = parser.parse_args()

    if hasattr(os, "geteuid") and os.geteuid() == 0 and not args.allow_root:
        print("Warning: refusing to run as root. Re-run with --allow-root if you intend to do so.")
        raise SystemExit(1)

    set_app_token(TOKEN)
    port = _choose_port(args.port)
    url = f"http://127.0.0.1:{port}/?token={TOKEN}"
    print(f"{APP_NAME} running at {url}")
    threading.Timer(1.0, _open_browser, args=(url,)).start()
    app.run(host=HOST, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
