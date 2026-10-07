from __future__ import annotations

from recondeck.digparse import dig_query
from recondeck.stages import log_command


def run_stage(scan):
    domain = scan.target["hostname"]
    resolver = scan.data["resolvers"][0]
    mail = {}
    mx = dig_query(domain, "MX", server=resolver)
    log_command(scan, mx.command)
    mail["mx"] = mx.answers
    txt = dig_query(domain, "TXT", server=resolver)
    log_command(scan, txt.command)
    mail["txt"] = txt.answers
    dmarc = dig_query(f"_dmarc.{domain}", "TXT", server=resolver)
    log_command(scan, dmarc.command)
    mail["dmarc"] = dmarc.answers
    mta_sts = dig_query(f"_mta-sts.{domain}", "TXT", server=resolver)
    log_command(scan, mta_sts.command)
    mail["mta_sts"] = mta_sts.answers
    bimi = dig_query(f"default._bimi.{domain}", "TXT", server=resolver)
    log_command(scan, bimi.command)
    mail["bimi"] = bimi.answers
    scan.data["mail"] = mail
    scan.coverage.append({"check": "email_records", "status": "ran", "detail": "MX and mail-related TXT records queried"})

    scan.findings.append({
        "id": "EMAIL-001",
        "flag": "green",
        "stage": 3,
        "title": "Email records collected",
        "evidence": [f"MX: {len(mx.answers)}", f"TXT: {len(txt.answers)}"],
        "why": "The domain's mail records and TXT metadata were fetched for review.",
        "fix": "",
        "refs": [],
    })
