from __future__ import annotations

from .core import *  # noqa: F401,F403
from .dnssec import *  # noqa: F401,F403
from .domain import *  # noqa: F401,F403
from .email import *  # noqa: F401,F403
from .subdomains import *  # noqa: F401,F403

RULES = [
    rule_gen_001,
    rule_gen_002,
    rule_gen_003,
    rule_gen_004,
    rule_gen_005,
    rule_ns_001,
    rule_ns_002,
    rule_ns_003,
    rule_ns_004,
    rule_ns_005,
    rule_ns_006,
    rule_ns_007,
    rule_ns_008,
    rule_ns_009,
    rule_axfr_001,
    rule_axfr_002,
    rule_axfr_003,
    rule_ch_001,
    rule_rec_001,
    rule_nsec_001,
    rule_mx_001,
    rule_mx_002,
    rule_mx_003,
    rule_mx_004,
    rule_mx_005,
    rule_mx_006,
    rule_spf_001,
    rule_spf_002,
    rule_spf_003,
    rule_spf_004,
    rule_spf_005,
    rule_spf_006,
    rule_spf_007,
    rule_dmarc_001,
    rule_dmarc_002,
    rule_dmarc_003,
    rule_dmarc_004,
    rule_dmarc_005,
    rule_dmarc_006,
    rule_dkim_001,
    rule_dkim_002,
    rule_mtasts_001,
    rule_mtasts_002,
    rule_txt_001,
    rule_txt_002,
    rule_dnssec_001,
    rule_dnssec_002,
    rule_dnssec_003,
    rule_dnssec_004,
    rule_caa_001,
    rule_caa_002,
    rule_sub_001,
    rule_sub_002,
    rule_sub_003,
    rule_sub_004,
    rule_sub_005,
    rule_sub_006,
    rule_sub_007,
    rule_ip_001,
    rule_ip_002,
    rule_whois_001,
    rule_whois_002,
    rule_whois_003,
    rule_whois_004,
]


def run_all_rules(data: dict):
    findings = []
    for rule in RULES:
        try:
            result = rule(data)
            if result:
                findings.extend(result)
        except Exception:
            continue
    return findings


__all__ = [
    "run_all_rules", "RULES",
    "rule_gen_001", "rule_gen_002", "rule_gen_003", "rule_gen_004", "rule_gen_005",
    "rule_ns_001", "rule_ns_002", "rule_ns_003", "rule_ns_004", "rule_ns_005", "rule_ns_006", "rule_ns_007", "rule_ns_008", "rule_ns_009",
    "rule_axfr_001", "rule_axfr_002", "rule_axfr_003", "rule_ch_001", "rule_rec_001", "rule_nsec_001",
    "rule_mx_001", "rule_mx_002", "rule_mx_003", "rule_mx_004", "rule_mx_005", "rule_mx_006",
    "rule_spf_001", "rule_spf_002", "rule_spf_003", "rule_spf_004", "rule_spf_005", "rule_spf_006", "rule_spf_007",
    "rule_dmarc_001", "rule_dmarc_002", "rule_dmarc_003", "rule_dmarc_004", "rule_dmarc_005", "rule_dmarc_006",
    "rule_dkim_001", "rule_dkim_002", "rule_mtasts_001", "rule_mtasts_002",
    "rule_txt_001", "rule_txt_002",
    "rule_dnssec_001", "rule_dnssec_002", "rule_dnssec_003", "rule_dnssec_004",
    "rule_caa_001", "rule_caa_002",
    "rule_sub_001", "rule_sub_002", "rule_sub_003", "rule_sub_004", "rule_sub_005", "rule_sub_006", "rule_sub_007",
    "rule_ip_001", "rule_ip_002",
    "rule_whois_001", "rule_whois_002", "rule_whois_003", "rule_whois_004",
]
