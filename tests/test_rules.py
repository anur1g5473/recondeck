import pytest

from recondeck.rules import run_all_rules


def test_rule_catalog_handles_green_and_non_green_cases():
    data = {
        "target": {"hostname": "example.com"},
        "resolvers": ["1.1.1.1"],
        "records": {
            "1.1.1.1": {
                "example.com": {
                    "TXT": {"answers": [{"rdata": "v=spf1 -all"}]},
                    "CAA": {"answers": [{"rdata": "0 issue \"letsencrypt.org\""}]},
                }
            }
        },
        "mail": {
            "mx": [{"rdata": "10 mail.example.com."}],
            "providers": ["Google Workspace"],
            "dmarc": [{"rdata": "v=DMARC1; p=quarantine; rua=mailto:reports@example.com"}],
            "dkim_selectors": ["default"],
            "mta_sts": [{"rdata": "v=STSv1; id=2024"}],
            "third_party_services": ["Google verification"],
        },
        "dnssec": {"dnskey": [{"rdata": "257 3 13 ABC"}], "validated": True},
        "whois": {"stdout": "Registrar: Example\nCreated: 2023-01-01\nExpires: 2030-01-01\nDomain Status: clientTransferProhibited"},
        "nameservers": {
            "names": ["ns1.example.com", "ns2.example.com"],
            "serials": [12345, 12345],
            "parent_ns": ["ns1.example.com"],
            "axfr_allowed": False,
            "axfr_attempted": True,
        },
        "subdomains": {"api.example.com": {"status": "ok"}},
        "ips": {"93.184.216.34": {"owner": "Example Hosting", "ptr": ["mail.example.com"]}},
    }

    findings = run_all_rules(data)
    ids = {item.id for item in findings}
    assert "NS-002" in ids
    assert "DMARC-003" in ids
    assert "SPF-003" in ids
    assert "TXT-001" in ids


def test_rule_catalog_rejects_bad_cases():
    data = {
        "target": {"hostname": "example.com"},
        "records": {
            "1.1.1.1": {
                "example.com": {
                    "TXT": {"answers": [{"rdata": "v=spf1 +all"}]},
                    "CAA": {"answers": []},
                }
            }
        },
        "mail": {
            "mx": [{"rdata": "10 missing.example.com."}],
            "dmarc": [{"rdata": "v=DMARC1; p=none"}],
            "dkim_selectors": [],
            "mta_sts": [],
            "third_party_services": [],
        },
        "nameservers": {
            "names": ["ns1.example.com"],
            "axfr_allowed": True,
            "axfr_attempted": True,
            "parent_ns": ["ns9.example.com"],
        },
        "subdomains": {},
        "dnssec": {"dnskey": [{"rdata": "257 3 1 ABC"}]},
    }

    findings = run_all_rules(data)
    ids = {item.id for item in findings}
    assert "NS-001" in ids
    assert "SPF-003" in ids
    assert "DMARC-002" in ids
    assert "AXFR-001" in ids
    assert "DNSSEC-004" in ids
