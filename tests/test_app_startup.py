import subprocess

import app


def test_open_browser_uses_windows_url_handler_from_wsl(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0)

    def unexpected_linux_browser(url):
        raise AssertionError("WSL should use the Windows URL handler, not gio")

    monkeypatch.setenv("WSL_INTEROP", "/run/WSL/123_interop")
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    monkeypatch.setattr(app.subprocess, "run", fake_run)
    monkeypatch.setattr(app.webbrowser, "open", unexpected_linux_browser)

    app._open_browser("http://127.0.0.1:5000/?token=test-token")

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == [
        "cmd.exe",
        "/c",
        "start",
        "",
        "http://127.0.0.1:5000/?token=test-token",
    ]
    assert kwargs["check"] is False
    assert kwargs["timeout"] == 10


def test_open_browser_reports_wsl_browser_failure(monkeypatch, capsys):
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 1)

    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    monkeypatch.delenv("WSL_INTEROP", raising=False)
    monkeypatch.setattr(app.subprocess, "run", fake_run)

    app._open_browser("http://127.0.0.1:5000/?token=test-token")

    assert "Could not open the Windows browser automatically" in capsys.readouterr().out
