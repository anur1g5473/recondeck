from __future__ import annotations

import json
from html import escape


def export_scan_markdown(scan) -> str:
    target = scan.target.get("hostname") or scan.target.get("registered_domain") or "unknown"
    lines = [
        "# ReconDeck report",
        "",
        f"- Target: {target}",
        f"- Status: {scan.status}",
        f"- Created: {scan.created_at or 'n/a'}",
        f"- Finished: {scan.finished_at or 'n/a'}",
        "",
        "## Findings",
    ]
    findings = scan.findings or []
    if not findings:
        lines.append("No findings recorded.")
    else:
        for finding in findings:
            lines.append(f"### {finding.id} - {finding.title} ({finding.flag})")
            lines.append(f"- Why: {finding.why or 'No explanation recorded.'}")
            lines.append(f"- Fix: {finding.fix or 'No corrective action recorded.'}")
            if finding.evidence:
                lines.append("- Evidence:")
                for entry in finding.evidence:
                    lines.append(f"  - {entry}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_scan_html(scan) -> str:
    target = scan.target.get("hostname") or scan.target.get("registered_domain") or "unknown"
    findings = scan.findings or []
    rows = []
    for finding in findings:
        evidence = "".join(f"<li>{escape(str(item))}</li>" for item in (finding.evidence or [])) or "<li>No evidence recorded.</li>"
        rows.append(
            """
            <article class="finding">
              <h3>{id} · {title}</h3>
              <p><strong>Flag:</strong> {flag}</p>
              <p>{why}</p>
              <p><strong>Fix:</strong> {fix}</p>
              <ul>{evidence}</ul>
            </article>
            """.format(
                id=escape(str(finding.id)),
                title=escape(str(finding.title)),
                flag=escape(str(finding.flag)),
                why=escape(str(finding.why or "No explanation included.")),
                fix=escape(str(finding.fix or "No corrective action recorded.")),
                evidence=evidence,
            )
        )
    body_content = rows or "<p>No findings recorded.</p>"
    return f"""<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <title>ReconDeck report for {escape(target)}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem; color: #111; background: #f7f7f7; }}
      h1, h2, h3 {{ color: #0b1631; }}
      .report {{ max-width: 960px; margin: 0 auto; background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 1px 6px rgba(0,0,0,0.08); }}
      .finding {{ border-left: 6px solid #4aa8ff; background: #f8fbff; margin-bottom: 1rem; padding: 1rem 1.2rem; border-radius: 8px; }}
      ul {{ margin: 0.75rem 0 0 1.25rem; }}
      code {{ background: #eef3ff; padding: 0.15rem 0.35rem; border-radius: 4px; }}
    </style>
  </head>
  <body>
    <main class=\"report\">
      <h1>ReconDeck report</h1>
      <p><strong>Target:</strong> {escape(target)}</p>
      <p><strong>Status:</strong> {escape(str(scan.status))}</p>
      <p><strong>Created:</strong> {escape(str(scan.created_at or 'n/a'))}</p>
      <h2>Findings</h2>
      {body_content}
    </main>
  </body>
</html>
"""


def export_scan(scan, fmt: str = "json") -> str:
    fmt = (fmt or "json").lower()
    if fmt == "json":
        return json.dumps(scan.to_dict(), indent=2, sort_keys=True)
    if fmt == "md":
        return export_scan_markdown(scan)
    if fmt == "html":
        return export_scan_html(scan)
    raise ValueError(f"Unsupported export format: {fmt}")
