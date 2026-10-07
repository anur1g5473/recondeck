from __future__ import annotations


def _finding_record(finding):
    if finding is None:
        return None
    return {
        "id": getattr(finding, "id", None),
        "flag": getattr(finding, "flag", None),
        "title": getattr(finding, "title", None),
        "why": getattr(finding, "why", None),
        "fix": getattr(finding, "fix", None),
    }


def compare_scans(left, right):
    left_findings = {item.id: item for item in getattr(left, "findings", [])}
    right_findings = {item.id: item for item in getattr(right, "findings", [])}

    added = []
    removed = []
    changed = []

    for finding_id in sorted(set(right_findings) - set(left_findings)):
        finding = right_findings[finding_id]
        added.append({"id": finding.id, "flag": finding.flag, "title": finding.title})

    for finding_id in sorted(set(left_findings) - set(right_findings)):
        finding = left_findings[finding_id]
        removed.append({"id": finding.id, "flag": finding.flag, "title": finding.title})

    for finding_id in sorted(set(left_findings) & set(right_findings)):
        before = left_findings[finding_id]
        after = right_findings[finding_id]
        before_record = _finding_record(before)
        after_record = _finding_record(after)
        if before_record != after_record:
            changed.append({
                "id": finding_id,
                "before": before_record,
                "after": after_record,
            })

    left_subdomains = set((getattr(left, "data", {}) or {}).get("subdomains", {}).get("hosts", []) or [])
    right_subdomains = set((getattr(right, "data", {}) or {}).get("subdomains", {}).get("hosts", []) or [])
    added_hosts = sorted(right_subdomains - left_subdomains)
    removed_hosts = sorted(left_subdomains - right_subdomains)

    return {
        "a": left.id,
        "b": right.id,
        "added": added,
        "removed": removed,
        "changed": changed,
        "added_hosts": added_hosts,
        "removed_hosts": removed_hosts,
    }
