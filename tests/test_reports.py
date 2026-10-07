from recondeck.compare import compare_scans
from recondeck.report import export_scan
from recondeck.models import Finding, Scan


def _scan(scan_id, flag="green", title="Sample finding"):
    return Scan(
        id=scan_id,
        target={"hostname": "example.com", "registered_domain": "example.com"},
        options={"wordlist": "small"},
        status="done",
        created_at="2025-01-01T00:00:00Z",
        findings=[Finding(id="GEN-001", flag=flag, stage=0, title=title, evidence=["probe"], why="testing", fix="fix it")],
    )


def test_export_markdown_contains_findings():
    scan = _scan("scan-a")
    payload = export_scan(scan, "md")
    assert "# ReconDeck report" in payload
    assert "GEN-001" in payload


def test_export_html_contains_target_and_findings():
    scan = _scan("scan-a")
    payload = export_scan(scan, "html")
    assert "example.com" in payload
    assert "GEN-001" in payload


def test_compare_scans_reports_differences():
    left = _scan("scan-1", "green", "Same")
    right = _scan("scan-2", "yellow", "Changed")
    right.findings[0].id = "GEN-001"
    result = compare_scans(left, right)
    assert result["a"] == "scan-1"
    assert result["b"] == "scan-2"
    assert result["changed"][0]["id"] == "GEN-001"
