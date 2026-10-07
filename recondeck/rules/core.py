from __future__ import annotations

from recondeck.models import Finding


def _finding(rule_id: str, flag: str, stage: int, title: str, evidence, why: str, fix: str = "", refs=None):
    refs = refs or []
    return Finding(id=rule_id, flag=flag, stage=stage, title=title, evidence=list(evidence), why=why, fix=fix, refs=refs)


def rule_gen_001(data):
    wildcard = data.get("wildcard")
    if wildcard:
        return [_finding("GEN-001", "yellow", 0, "Wildcard DNS detected", ["Wildcard answer observed"], "The domain responds to random labels, which indicates wildcard DNS and can generate false positives during brute-force checks.", "Filter brute-force findings against the wildcard set or disable wildcard expansion for the target.")]
    return []


def rule_gen_002(data):
    records = data.get("records", {})
    problems = []
    for resolver, per_host in records.items():
        for host, types in per_host.items():
            for rtype in ("NS", "MX", "TXT", "SOA", "CAA"):
                answers = types.get(rtype, {}).get("answers", [])
                if not answers:
                    continue
                values = {entry.get("rdata", "") for entry in answers}
                if len(values) <= 1:
                    continue
                problems.append(f"{resolver}:{host}:{rtype}")
    if problems:
        return [_finding("GEN-002", "yellow", 1, "Resolvers disagree on core record sets", problems[:5], "Different resolvers returned different authoritative record data for the same record type, which can indicate split-horizon or inconsistent DNS views.", "Check whether the domain is intentionally using geo or anycast behavior before treating the disagreement as a problem.")]
    return []


def rule_gen_003(data):
    records = data.get("records", {})
    diffs = []
    for resolver, per_host in records.items():
        for host, types in per_host.items():
            a_values = {entry.get("rdata", "") for entry in types.get("A", {}).get("answers", [])}
            aaaa_values = {entry.get("rdata", "") for entry in types.get("AAAA", {}).get("answers", [])}
            if a_values or aaaa_values:
                diffs.append((resolver, host, sorted(a_values | aaaa_values)))
    if diffs and len(diffs) > 1:
        return [_finding("GEN-003", "green", 1, "Resolver disagreement is limited to A/AAAA", [f"{len(diffs)} resolver differences observed"], "The resolvers disagree only on address records, which is common for CDNs and geo-DNS deployments.", "")]
    return []


def rule_gen_004(data):
    host = data.get("target", {}).get("hostname")
    records = data.get("records", {})
    apex = records.get(next(iter(records), None), {}).get(host, {}) if host else {}
    apex_a = bool(apex.get("A", {}).get("answers")) or bool(apex.get("AAAA", {}).get("answers"))
    www_host = f"www.{host}" if host else None
    www = records.get(next(iter(records), None), {}).get(www_host, {}) if www_host else {}
    if not apex_a and www.get("A", {}).get("answers") or www.get("AAAA", {}).get("answers"):
        return [_finding("GEN-004", "yellow", 1, "Apex has no A/AAAA but www does", [f"{host} has no address; {www_host} resolves"], "The root host does not have direct A/AAAA records even though www does, which is often a hosting or redirect configuration choice.", "Check whether the apex is intentionally redirected or if an A/AAAA record is missing.")]
    return []


def rule_gen_005(data):
    records = data.get("records", {})
    for resolver, per_host in records.items():
        for host, types in per_host.items():
            if types.get("A", {}).get("status") == "SERVFAIL":
                return [_finding("GEN-005", "red", 1, "Apex query returned SERVFAIL", [f"{resolver}: {host} -> SERVFAIL"], "At least one resolver reported a SERVFAIL for the domain, which indicates a failure in the DNS path or zone configuration.", "Verify the authoritative server health and resolver path before treating the domain as normal.")]
    return []


def rule_ns_001(data):
    nameservers = data.get("nameservers", {})
    ns_names = nameservers.get("names", [])
    if len(ns_names) < 2:
        return [_finding("NS-001", "red", 2, "Fewer than 2 nameservers", [f"Found {len(ns_names)} server(s)"], "The domain does not advertise enough delegated nameservers to provide redundancy and resilience.", "Add at least two authoritative nameservers for the zone.")]
    return []


def rule_ns_002(data):
    nameservers = data.get("nameservers", {})
    ns_names = nameservers.get("names", [])
    if len(ns_names) >= 2:
        return [_finding("NS-002", "green", 2, "Multiple nameservers are delegated", [f"{len(ns_names)} nameservers"], "The domain advertises more than one authoritative nameserver, which is the expected delegation pattern.", "")]
    return []


def rule_ns_003(data):
    nameservers = data.get("nameservers", {})
    issues = []
    for name, info in nameservers.items():
        if name == "names":
            continue
        if info.get("unresolvable"):
            issues.append(f"{name}: unresolvable")
    if issues:
        return [_finding("NS-003", "red", 2, "Nameserver does not resolve", issues[:5], "One or more nameservers do not resolve, which makes the delegation unreliable.", "Fix or remove the broken nameserver records.")]
    return []


def rule_ns_004(data):
    nameservers = data.get("nameservers", {})
    issues = []
    for name, info in nameservers.items():
        if name == "names":
            continue
        if info.get("aa") is False:
            issues.append(f"{name}: aa flag missing")
    if issues:
        return [_finding("NS-004", "red", 2, "Authoritative response flag missing", issues[:5], "A nameserver answered without the authoritative aa flag, which can indicate misconfiguration or a non-authoritative responder.", "Verify the authoritative server configuration and the recursion settings.")]
    return []


def rule_ns_005(data):
    nameservers = data.get("nameservers", {})
    parent = set(nameservers.get("parent_ns", []))
    child = set(nameservers.get("names", []))
    if parent and parent != child:
        return [_finding("NS-005", "yellow", 2, "Parent and child nameserver sets differ", [f"parent={sorted(parent)[:5]}", f"child={sorted(child)[:5]}"], "The parent delegation does not match the child nameserver set exactly, which can indicate a stale or inconsistent delegation.", "Review the parent zone and delegation records to make sure they match the child zone.")]
    return []


def rule_ns_006(data):
    serials = data.get("nameservers", {}).get("serials", [])
    if len(set(serials)) > 1:
        return [_finding("NS-006", "yellow", 2, "SOA serials differ across nameservers", [str(sorted(set(serials)))], "The nameservers disagree on the SOA serial, which often indicates a zone transfer or replication problem.", "Confirm zone replication and the authoritative server state.")]
    return []


def rule_ns_007(data):
    nameservers = data.get("nameservers", {})
    issues = []
    for name, info in nameservers.items():
        if name == "names":
            continue
        if info.get("tcp") is False:
            issues.append(f"{name}: no TCP response")
    if issues:
        return [_finding("NS-007", "yellow", 2, "Some nameservers do not answer over TCP", issues[:5], "At least one authoritative server failed its TCP check, which can complicate troubleshooting or zone transfer health checks.", "Verify TCP reachability and firewall policy for the nameserver.")]
    return []


def rule_ns_008(data):
    nameservers = data.get("nameservers", {})
    ip_list = []
    for name, info in nameservers.items():
        if name == "names":
            continue
        ip_list.extend(info.get("ips", []))
    if ip_list:
        asns = {ip_info.get("asn") for ip_info in data.get("ips", {}).values() if ip_info.get("asn")}
        if len(asns) <= 1:
            return [_finding("NS-008", "yellow", 2, "Nameserver IPs are concentrated in one ASN or /24", [f"ASNs: {sorted(asns)[:5]}"], "All responsive nameservers appear to be concentrated in one network space, which can reduce resilience.", "Use a wider distribution of authoritative infrastructure or verify design intent.")]
    return []


def rule_ns_009(data):
    asns = {info.get("asn") for info in data.get("ips", {}).values() if info.get("asn")}
    if len(asns) >= 2:
        return [_finding("NS-009", "green", 2, "Nameservers are spread across ASNs", [f"{len(asns)} ASNs observed"], "The domain uses authoritative infrastructure across multiple ASNs, which is a stronger resilience pattern.", "")]
    return []


def rule_axfr_001(data):
    nameservers = data.get("nameservers", {})
    if nameservers.get("axfr_allowed") or (nameservers.get("axfr_attempted") and nameservers.get("axfr_allowed")):
        return [_finding("AXFR-001", "red", 6, "Zone transfer is allowed", ["At least one nameserver allowed AXFR"], "The zone transfer test succeeded, which exposes the full zone and sensitive records to anyone who can query it.", "Disable AXFR on the authoritative server or restrict access to trusted clients only.")]
    return []


def rule_axfr_002(data):
    nameservers = data.get("nameservers", {})
    if nameservers.get("axfr_attempted") and not nameservers.get("axfr_allowed"):
        return [_finding("AXFR-002", "green", 6, "Zone transfer refused", ["All tested servers refused AXFR"], "The authoritative nameservers refused to permit zone transfer, which is the expected secure baseline.", "")]
    return []


def rule_axfr_003(data):
    nameservers = data.get("nameservers", {})
    if not data.get("active_mode") and not nameservers.get("axfr_attempted"):
        return [_finding("AXFR-003", "grey", 6, "Active zone transfer checks were not run", ["Active probing disabled or not performed"], "The active mode check was not run, so no conclusion can be drawn from a zone-transfer test.", "Run active probing on a domain you are authorized to test.")]
    return []


def rule_ch_001(data):
    leaks = []
    for source in ("version", "hostname", "id"):
        if data.get("nameservers", {}).get(f"{source}_bind"):
            leaks.append(f"{source}.bind: {data['nameservers'][f'{source}_bind']}")
    if leaks:
        return [_finding("CH-001", "yellow", 6, "Version or hostname leak detected", leaks[:5], "The nameserver responded to CHAOS queries with identifying text, which can reveal host and software details.", "Disable or restrict version and hostname queries to trusted parties only.")]
    return []


def rule_rec_001(data):
    if data.get("nameservers", {}).get("open_recursion"):
        return [_finding("REC-001", "red", 6, "Open recursion enabled", ["An authoritative server answered recursive queries"], "The nameserver allowed recursive resolution to unauthenticated clients, which can be abused for cache poisoning and reflection.", "Restrict recursion to trusted clients and disable open recursion where it is not required.")]
    return []


def rule_nsec_001(data):
    if data.get("nameservers", {}).get("nsec_mode") == "NSEC":
        return [_finding("NSEC-001", "yellow", 6, "Plain NSEC zone walk is possible", ["NSEC detected"], "The zone appears to use plain NSEC, which makes enumeration easier and exposes more names.", "Consider NSEC3 or tighter zone access controls to reduce enumeration risk.")]
    return []
