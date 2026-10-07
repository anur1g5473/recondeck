# ReconDeck: One-Click DNS Recon Tool

> **If you are an AI coding agent reading this file: this is your complete build specification.**
> Read the whole file before writing any code. Build exactly what is described. Do not invent features, do not skip security rules, do not ask the user questions. If something is unclear, choose the safest and simplest option and write your choice into `PROGRESS.md`.

---

## 0. How you (the agent) must work

1. **Build in the milestones listed in section 15, in order.** Finish and test one milestone before starting the next. After each milestone, append a short note to `PROGRESS.md` (what was built, what was tested, what is left).
2. **Never use `shell=True`.** Never build a command as one string. Always pass a list of arguments to `subprocess.run`.
3. **Never put untrusted data into HTML with `innerHTML`.** Use `textContent` only (section 12).
4. **Do not add dependencies** beyond those in section 3.
5. **Write tests** for the parsers (section 6) and the rules (section 9) using saved sample outputs in `tests/fixtures/`. Run them before finishing each milestone.
6. **Do not hardcode any real organization's domain** anywhere in the code, tests or docs. Use `example.com` and `zonetransfer.me` as examples only.
7. When something fails at runtime (timeout, refused, tool missing), the tool must record it as a **grey "could not check"** result. It must never silently skip it and never treat it as "all good".

---

## 1. What this tool is

ReconDeck is a **local web application**. The user types a domain (or pastes a URL), clicks **Scan everything**, and the backend runs a long pipeline of DNS reconnaissance checks in the background using the real command-line tools (mainly `dig`). When it finishes, the web page shows one complete report. Every finding carries a flag:

| Flag | Meaning |
|---|---|
| **Green** | Checked and healthy / expected. Green must only ever mean "checked and fine", never "did not look". |
| **Yellow** | Information exposure or something worth a look (not necessarily a flaw). |
| **Red** | A real misconfiguration or serious exposure. Red does **not** mean "hacked" or "exploitable". |
| **Grey** | Could not check (timeout, refused, tool missing, source down). Coverage gap. |

The scan may take 5 to 30 minutes. That is fine. It runs as a background job with live progress.

**Design decisions already made (do not change):**
- `dig` is the **only DNS engine**. `host`, `nslookup` and `dnsenum` are intentionally not used, because `dig` can do everything they do.
- Non-DNS data comes from exactly two extra sources: the `whois` command (domain registration) and `crt.sh` (certificate transparency, for subdomains).
- IP ownership (ASN, owner) is looked up **with dig** through the Team Cymru DNS service (section 8, stage 7).
- No AI/LLM and no RAG inside the tool. All intelligence is **plain rules** (section 9). Reason: DNS data is small and structured, rules are deterministic and free, and feeding attacker-controlled DNS text (TXT records) into an LLM would allow prompt injection.

---

## 2. Environment

- Backend runs **inside WSL Ubuntu** (the user is on Windows with WSL). It must also work on plain Linux and macOS if `dig` and `whois` are installed.
- The user opens the UI in their normal Windows browser at `http://127.0.0.1:<port>/` (WSL2 forwards localhost).
- Install prerequisites (document in this README's quick start):
  ```bash
  sudo apt update
  sudo apt install -y dnsutils whois python3 python3-venv python3-pip
  ```
- Python 3.10 or newer.

---

## 3. Tech stack (fixed)

- **Backend:** Python + **Flask**. Standard library for everything else (`subprocess`, `threading`, `ipaddress`, `json`, `urllib.request`, `re`, `secrets`, `pathlib`, `concurrent.futures`).
- **One extra library:** `tldextract` (to find the registered domain correctly, e.g. `vit.ac.in` not `ac.in`). Configure it **offline**: `tldextract.TLDExtract(suffix_list_urls=())`, which uses the bundled snapshot.
- **Frontend:** plain HTML + CSS + vanilla JavaScript (ES modules). **No frameworks, no build step, no CDN, no external fonts, no external images.** The tool must work fully offline apart from the DNS/whois/crt.sh queries themselves.
- `requirements.txt` contains exactly: `flask` and `tldextract` (pin versions after installing).

---

## 4. Project structure

```
recondeck/
├── README.md                  (this file)
├── PROGRESS.md                (agent writes milestone notes here)
├── LICENSE                    (MIT)
├── TERMS.md                   (section 13 text)
├── .gitignore                 (scans/, .venv/, __pycache__/)
├── requirements.txt
├── start.bat                  (Windows launcher, section 14)
├── start.sh                   (Linux/WSL launcher, section 14)
├── app.py                     (Flask app + CLI entry)
├── recondeck/
│   ├── __init__.py
│   ├── config.py              (all constants: timeouts, resolvers, limits)
│   ├── security.py            (token, Host/Origin checks, headers)
│   ├── validators.py          (target parsing, domain/IP validation)
│   ├── runner.py              (the only place that runs subprocesses)
│   ├── digparse.py            (dig output parsers)
│   ├── models.py              (Scan, Stage, Finding, CommandRecord dataclasses)
│   ├── store.py               (save/load scans on disk)
│   ├── orchestrator.py        (runs stages in order, handles cancel)
│   ├── stages/
│   │   ├── s0_prepare.py
│   │   ├── s1_records.py
│   │   ├── s2_nameservers.py
│   │   ├── s3_email.py
│   │   ├── s4_dnssec.py
│   │   ├── s5_passive_subs.py
│   │   ├── s6_active.py
│   │   └── s7_enrich.py
│   ├── rules/
│   │   ├── __init__.py        (registry + run_all_rules)
│   │   ├── core.py  email.py  dnssec.py  subdomains.py  domain.py
│   ├── report.py              (export to json / md / html)
│   └── compare.py             (diff two scans)
├── knowledge/
│   ├── records.json           (plain-English explanation of each record type)
│   ├── providers.json         (MX/TXT/NS fingerprints, cloud/CDN keywords, takeover suffixes)
│   └── interesting_names.json
├── wordlists/
│   ├── small.txt  medium.txt  large.txt
├── static/
│   ├── index.html  app.css  app.js
│   └── js/ (api.js, dom.js, views/*.js)
├── scans/                     (runtime output, git-ignored)
└── tests/
    ├── fixtures/              (saved dig/whois outputs)
    └── test_digparse.py  test_rules.py  test_validators.py
```

---

## 5. Security rules (mandatory, not optional)

The server runs commands against user-supplied input, so these protections are required. Each one has a purpose.

1. **Bind to `127.0.0.1` only.** Never `0.0.0.0`.
2. **Never use a shell.** All subprocess calls go through `runner.py` with an argument list.
3. **The browser never sends a command.** It sends only: target, wordlist size (`small|medium|large`), active flag, authorization flag. The backend owns every command template.
4. **Validate the target strictly** (section 5.1) and **reject anything starting with `-`**, because dig would treat it as an option (argument injection).
5. **Startup token.** On start, generate `secrets.token_urlsafe(32)`. Every `/api/*` request must carry it in header `X-ReconDeck-Token`, compared with `secrets.compare_digest`. The index page is served only when opened with `?token=...`, and embeds the token in a `<meta name="token">` tag. This stops other websites open in the user's browser from calling the local API.
6. **Host header check (DNS rebinding defense).** Accept only `127.0.0.1:<port>` and `localhost:<port>`. Reject all other Host values with 403.
7. **Origin check on every POST.** If an `Origin` header is present it must equal `http://127.0.0.1:<port>` or `http://localhost:<port>`.
8. **No CORS headers at all.**
9. **Security response headers** on every response:
   `Content-Security-Policy: default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`,
   `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`.
   This means **no inline scripts and no inline `style="..."` attributes** in the frontend. Put all CSS in `app.css` and all JS in files.
10. **Escape all output.** DNS data (especially TXT) is controlled by the domain owner and may contain HTML or script. The frontend inserts data with `textContent` only (section 12).
11. **Resource limits:** per-command timeout, max 200 KB stored per command output (truncate and mark `truncated: true`), max 1 scan running at a time, max 8 concurrent dig processes overall.
12. **Do not run as root.** If `os.geteuid() == 0`, print a warning and exit unless `--allow-root` is passed.
13. **Active probing is gated server-side.** Stage 6 runs only if the request had `active: true` **and** `authorized: true`. The backend enforces this; the frontend checkbox alone is not enough.
14. **Raw-output files** are saved as plain text with the extension `.txt`, and the API serves them as `text/plain`.

### 5.1 Target parsing and validation (`validators.py`)

Input can be `vit.ac.in`, `https://www.vit.ac.in/some/page?x=1`, `user@host.com`, `HOST.com:8080`, or with a trailing dot. Steps, in this exact order:

1. Strip whitespace. Reject empty or longer than 300 characters.
2. If it contains `://`, take everything after it. Cut at the first of `/`, `?`, `#`. Drop any `user@` prefix. Drop `:port`.
3. Lowercase. Remove one trailing dot.
4. Convert internationalized names with `.encode("idna").decode("ascii")` (catch errors and reject).
5. Validate with this exact regex (each label 1 to 63 chars, letters/digits/hyphen, no leading or trailing hyphen, total length at most 253, at least 2 labels):
   `^(?=.{1,253}$)(?!-)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$`
   Also accept the punycode TLD form `xn--[a-z0-9-]+`.
6. Reject IP addresses (this version scans domains only), reject `localhost`, reject names ending in `.local`, `.internal`, `.lan`, `.home.arpa`.
7. Return `{hostname, registered_domain, suffix}` using `tldextract`. **All scanning is done on `registered_domain`** (for example `vit.ac.in`), and the original hostname is kept for the report. If the user entered a subdomain, scan its registered domain and note this in the report header.

Any IP address that the tool later feeds to a command must pass `ipaddress.ip_address()` first. Any hostname the tool later feeds to a command (nameservers, discovered subdomains) must pass the same hostname regex above, or be skipped and logged as grey.

---

## 6. The command runner and dig parsing

### 6.1 `runner.py` (the only file allowed to start processes)

```
run(argv: list[str], timeout: int, stage: str, label: str) -> CommandRecord
```
- `argv[0]` must be one of the allowed binaries: `dig`, `whois`. Anything else raises an error.
- Use `subprocess.run(argv, capture_output=True, text=True, timeout=timeout, shell=False, errors="replace")`.
- Return a `CommandRecord`: `id`, `stage`, `label`, `argv`, `command_line` (a `shlex.join(argv)` string used **for display only**, never executed), `started_at`, `duration_ms`, `exit_code`, `stdout`, `stderr`, `timed_out`, `truncated`.
- On `TimeoutExpired`: `timed_out = True`, keep any partial output.
- On `FileNotFoundError`: record an error and mark the tool unavailable.
- Every record is appended to the scan's command log and its output is written to `scans/<id>/raw/<command_id>.txt`.
- A global `threading.Semaphore(8)` limits concurrent processes. Per-resolver semaphore (5) and a 20 ms sleep between queries to the same server stop rate limiting.
- Check a cancel flag before every command. If cancelled, return immediately with `cancelled = True`.

### 6.2 Standard dig invocation

Every dig call goes through one helper in `digparse.py`:

```
dig_query(name, rtype, server=None, tcp=False, ipv6=False, norecurse=False, dnssec=False, chaos=False, extra=[]) -> DigResult
```

It builds this argv (order matters; the validated name always comes last among positional items and can never start with `-`):

```
["dig"] + (["-6"] if ipv6 else []) + (["@"+server] if server else []) +
[name, rtype] + (["CH"] if chaos else []) +
["+noall", "+answer", "+authority", "+comments", "+time=3", "+tries=2"] +
(["+tcp"] if tcp else []) + (["+norecurse"] if norecurse else []) +
(["+dnssec"] if dnssec else []) + extra
```

`+noall +answer +authority +comments` gives a small, parseable output. (Note: `+comments` is what prints the header with the status and flags.)

### 6.3 What the parser must extract (`DigResult`)

Sample output the parser must handle:

```
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 4821
;; flags: qr rd ra; QUERY: 1, ANSWER: 2, AUTHORITY: 0, ADDITIONAL: 1

;; ANSWER SECTION:
example.com.		3600	IN	MX	10 mail.example.com.
example.com.		3600	IN	MX	20 mail2.example.com.
```

Parser rules:
- Line starting with `;; ->>HEADER<<-`: extract `status` (NOERROR, NXDOMAIN, SERVFAIL, REFUSED, ...) with regex `status: (\w+)`.
- Line starting with `;; flags:`: extract the flag words before the first `;` (qr, aa, tc, rd, ra, ad, cd) into a list.
- Line `;; ANSWER SECTION:` switches section to `answer`; `;; AUTHORITY SECTION:` to `authority`.
- Any non-empty line **not starting with `;`** is a record line. Split on whitespace into `name, ttl, class, type, rdata...`. `rdata` is the rest joined by single spaces. Lowercase `name` and `type`. Keep `rdata` case as is (but also store `rdata_lower`).
- TXT rdata can contain several quoted chunks: join them into one string with the quotes removed (`"v=spf1 " "include:x"` becomes `v=spf1 include:x`).
- Lines starting with `;` that contain `connection timed out`, `no servers could be reached`, `communications error`, or `Transfer failed` set `error` (string) on the result.
- Output fields: `status`, `flags`, `answers`, `authority`, `error`, `timed_out`, `command` (the CommandRecord), `ok` (true when status is NOERROR/NXDOMAIN and no error).

**NXDOMAIN versus no data:** `status=NXDOMAIN` means the name does not exist. `status=NOERROR` with empty `answers` means the name exists but has no record of that type. Keep these apart everywhere.

Write unit tests with fixtures for: normal answer, NXDOMAIN, SERVFAIL, REFUSED, timeout, multi-chunk TXT, CNAME chain (the answer section lists the CNAME followed by the final A), AXFR success, AXFR refused.

### 6.4 Resolvers

`config.RESOLVERS = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]`. These are the public resolvers used for "what the world sees" queries. Authoritative nameserver queries (stage 2 onward) go directly to the domain's own nameservers with `norecurse=True`.

---

## 7. Data model

```
Scan:   id, target{input,hostname,registered_domain,suffix}, options{wordlist,active,authorized},
        status (queued|running|done|failed|cancelled), created_at, finished_at,
        stages[], findings[], data{}, commands[] (metadata only; raw output on disk), coverage[]
Stage:  id (0..9), name, status (waiting|running|done|failed|skipped|cancelled), started_at, finished_at, note
Finding: id (e.g. "SPF-003"), flag (green|yellow|red|grey), stage, title, evidence[] (strings),
         why (one plain sentence), fix (one plain sentence or empty), refs[] (command ids)
Coverage: {check, status (ran|failed|skipped|partial), detail}
```

`data{}` holds the structured results that rules read: `records` (per name and type, per resolver), `nameservers` (list with IPs and per-server results), `mail` (mx, spf, dmarc, dkim, ...), `dnssec`, `subdomains` (dict hostname to `{sources[], a[], aaaa[], cname_chain[], status, asn, owner, flags[]}`), `ips` (dict ip to `{asn, prefix, country, owner, ptr[], provider_type}`), `whois`.

Persist after every stage to `scans/<id>/scan.json` (write to a temp file, then rename). If the server restarts, interrupted scans load as `status: failed` with the partial data intact.

---

## 8. The scan pipeline: every check, in order

**[P]** = passive: ordinary public queries. **[A]** = active: probes the target's own servers; only runs when `active` and `authorized` are both true.
Each stage records `Coverage` entries and sets its status. A failing check never stops the pipeline.

### Stage 0: Prepare [P]
1. Parse the target (section 5.1).
2. Check tools: run `dig -v` and `whois --version` (or `whois -h` fallback). Missing `dig` is fatal (scan fails with a clear message). Missing `whois` makes only the whois checks grey.
3. Test the resolvers: `dig @<r> . NS +short +time=3 +tries=1`. Drop unresponsive resolvers; if all fail, the scan fails with "no network or DNS access".
4. **Wildcard detection:** generate 2 random labels (16 lowercase letters/digits), query `A` and `AAAA` for `<random>.<domain>` on the first working resolver. If any answer comes back, store `data.wildcard = {a:[...], aaaa:[...], cname:[...]}`. Later brute-force and enrichment use this to filter false positives.

### Stage 1: Core records [P]
Query **every** type below for the apex (`domain`), and `A`, `AAAA`, `CNAME` also for `www.<domain>`. Ask **each** working resolver and store results per resolver:

`A, AAAA, NS, MX, TXT, SOA, CNAME, CAA, HTTPS, SVCB, SRV` plus `NAPTR`, `TLSA` is skipped (needs a service name). Also query these SRV names (the answer may be empty, that is fine):
`_sip._tcp, _sip._udp, _sips._tcp, _ldap._tcp, _kerberos._tcp, _kerberos._udp, _xmpp-client._tcp, _xmpp-server._tcp, _autodiscover._tcp, _imap._tcp, _imaps._tcp, _submission._tcp, _pop3s._tcp, _caldavs._tcp, _carddavs._tcp, _matrix._tcp` (each prefixed to the domain).

Record for each answer: TTL, status, flags. Then **compare resolvers**: for each type, sort the rdata sets and note whether all resolvers agree (`data.resolver_agreement[type] = true/false` plus the differing sets). Remember that CDNs legitimately return different A records, so disagreement on A/AAAA is only a yellow note, not red.

Example command: `dig @1.1.1.1 example.com MX +noall +answer +authority +comments +time=3 +tries=2`

### Stage 2: Delegation and nameservers [P]
1. `dig +trace +nodnssec <domain> NS`. Store the raw output only (informational, shown in the Commands tab). Do not parse it for rules.
2. Get the **parent NS list**: ask a server of the public suffix zone (for `vit.ac.in` the suffix is `ac.in`). Resolve NS for the suffix, resolve one server's IP, then `dig @<ip> <domain> NS +norecurse` and read the **authority** section (delegations appear there). Store as `parent_ns`.
3. Get the **child NS list** from the domain's own servers (`dig @<ns_ip> <domain> NS +norecurse`, answer section), per server.
4. Resolve every nameserver's A and AAAA via a public resolver. A nameserver name that does not resolve is recorded as `unresolvable`.
5. For **each nameserver IP** (IPv4 and IPv6 separately; use `-6` for IPv6):
   - `SOA` query with `+norecurse`: record the **`aa` flag**, the SOA **serial** (3rd field of the SOA rdata), response status, response time.
   - Repeat the SOA query with `tcp=True` to check **TCP support**.
   - Record whether it answered at all (`responsive`).
6. Compute and store: nameserver count, set of ASNs (filled later in stage 7, so rules for diversity run after stage 7), serial set, parent/child NS set difference.

### Stage 3: Email security [P]
All queries via public resolvers.
- **MX analysis:** from Stage 1. For each MX target: resolve A/AAAA, check whether the target is a CNAME (query CNAME for it), detect **provider** by matching the MX hostname against `knowledge/providers.json` (suffix patterns such as `aspmx.l.google.com`/`google.com` = Google Workspace, `mail.protection.outlook.com` = Microsoft 365, `zoho.com`, `pphosted.com` = Proofpoint, `mimecast`, `protonmail`, `secureserver.net` = GoDaddy, etc.). Detect a **null MX** (`0 .`).
- **SPF:** from TXT records on the apex, select values beginning with `v=spf1` (case-insensitive). Parse: list of mechanisms and modifiers, the `all` qualifier (`+`, `-`, `~`, `?`, or missing), `redirect=`, `include:` list, `ip4:`/`ip6:` ranges with prefix length, `ptr` usage, `exists:` usage. **Count DNS lookups** recursively by following `include:`, `redirect=`, `a`, `mx`, `ptr`, `exists` (each counts 1) up to depth 10 and 15 queries total; record the count and whether the follow was truncated.
- **DMARC:** TXT at `_dmarc.<domain>`; value beginning `v=DMARC1`. Parse tags: `p`, `sp`, `pct` (default 100), `rua`, `ruf`, `adkim`, `aspf`, `fo`. If `_dmarc.<domain>` has a CNAME, follow it.
- **DKIM selectors (guessing):** query TXT at `<selector>._domainkey.<domain>` for `default, google, selector1, selector2, k1, k2, k3, s1, s2, mail, dkim, smtp, mandrill, mailgun, mg, sendgrid, zoho, protonmail, protonmail2, protonmail3, cm, em, scph, mxvault`. Also follow CNAMEs (many providers use CNAME to their key). A found selector means DKIM exists. **No hit does not prove DKIM is absent.**
- **MTA-STS:** TXT at `_mta-sts.<domain>` beginning `v=STSv1`.
- **TLS-RPT:** TXT at `_smtp._tls.<domain>` beginning `v=TLSRPTv1`.
- **BIMI:** TXT at `default._bimi.<domain>` beginning `v=BIMI1`.
- **TXT intelligence:** go through all apex TXT records, match against `knowledge/providers.json` `txt_verifications` (for example `google-site-verification=`, `MS=ms`, `atlassian-domain-verification=`, `facebook-domain-verification=`, `stripe-verification=`, `docusign=`, `apple-domain-verification=`, `adobe-idp-site-verification=`, `zoom`, `hubspot`, `onetrust`, `cisco-ci-domain-verification=`, `amazonses`, `_github-challenge`, etc.) and record the revealed third-party services. Also flag TXT values that look like secrets: regex `(?i)(password|passwd|secret|api[_-]?key|token|private[_-]?key)\s*[=:]\s*\S+`.

### Stage 4: DNSSEC [P]
- Query `DNSKEY`, `DS` (the DS is held at the parent; ask a public resolver), `NSEC3PARAM` for the domain, each with `dnssec=True`.
- **Validation test:** `dig @1.1.1.1 <domain> A +dnssec`. Check the `ad` flag in the header flags.
- **Broken-chain test:** if a DS exists and the query above returned `SERVFAIL`, repeat with `+cd` (checking disabled). If that works, the chain is broken (`dnssec.broken = true`).
- **Algorithms:** read the algorithm number (2nd field) from DS and DNSKEY rdata (DNSKEY: `flags protocol algorithm key`; DS: `keytag algorithm digesttype digest`). Weak: 1 (RSAMD5), 3 (DSA), 5 (RSASHA1), 6 (DSA-NSEC3-SHA1), 7 (RSASHA1-NSEC3-SHA1). Good: 8, 10, 13, 14, 15, 16.
- **NSEC versus NSEC3:** ask one authoritative nameserver for a random nonexistent name with `+dnssec +norecurse` and check which record type (`NSEC` or `NSEC3`) appears in the authority section.

### Stage 5: Passive subdomain discovery [P]
1. **crt.sh:** `urllib.request` GET `https://crt.sh/?q=%25.<domain>&output=json` with timeout 90 and up to 3 retries (wait 5 then 15 seconds). Send a `User-Agent: ReconDeck/1.0`. For every item, split `name_value` on newline, lowercase, strip a leading `*.`, keep only names that equal the domain or end with `.<domain>`, validate with the hostname regex, deduplicate. If crt.sh fails after retries: grey coverage entry, scan continues.
2. **Names seen in DNS data:** hostnames found in MX, NS, SRV, CNAME targets, SOA mname/rname, SPF includes of the same domain, `www`.
3. Merge into `data.subdomains` with a `sources` list per name (`crt`, `dns`, `brute`, `axfr`, `nsec`, `ptr`).
4. Cap at 5000 names; if more, keep the first 5000 sorted and add a coverage note.

### Stage 6: Active probing [A] (skipped unless active and authorized)
For each **responsive nameserver IP** (IPv4):
1. **Zone transfer:** `dig @<ns_ip> <domain> AXFR +noall +answer +comments +time=10 +tries=1`, with a 30 s hard timeout. Result is **allowed** if the answer contains more than the two SOA records and the output has no `Transfer failed`; **refused** otherwise. If allowed, parse all records, add their names to `data.subdomains` with source `axfr`, and keep the full record dump in the raw output. Try IXFR only if AXFR is refused: `dig @<ip> <domain> IXFR=0`.
2. **CHAOS version leak:** `dig @<ns_ip> version.bind CH TXT +noall +answer +comments`, and the same for `hostname.bind` and `id.server`. A non-empty TXT answer means information is leaked. Store the text.
3. **Open recursion test:** `dig @<ns_ip> example.com A +recurse +noall +answer +comments`. Open recursion is true if the `ra` flag is set **and** an answer is returned.
4. **NSEC walking** (only if stage 4 found plain NSEC): start at the apex, `dig @<ns_ip> <name> NSEC +noall +answer`, read the "next name", repeat until it wraps around to the apex or 500 steps. Add found names with source `nsec`.

Then **once (not per nameserver)**:
5. **Subdomain brute force:** read the chosen wordlist (`small` ~200 names, `medium` ~1,000, `large` ~5,000; user's choice). Use **dig batch mode**: write the queries to a temp file, one per line (`<word>.<domain> A`), split into chunks of 100 lines, and run `dig @<resolver> -f <chunkfile> +noall +answer +time=2 +tries=1` for each chunk, using a thread pool of at most 4 workers and rotating through the resolvers. Parse answer lines only (a name with no answer line did not resolve). **Discard** any result whose A/AAAA/CNAME answers are a subset of `data.wildcard`. Add the rest with source `brute`.
6. **Recursion:** for every found name whose first label is in `interesting_names.json` `recurse_labels` (`dev, staging, stage, test, internal, corp, intranet, api, vpn, uat, qa, admin, int, preprod`), brute-force the first 50 words of the small list under it (depth max 2). Hard cap: 2,000 extra queries.
7. **Reverse (PTR) sweep:** for every IPv4 discovered so far whose owner (from Team Cymru, section stage 7 step 4, so run that lookup for those IPs first) is **not** a shared cloud/CDN provider (match against `providers.json` `shared_provider_keywords`), take its `/24`; cap at 5 distinct `/24` ranges and 1,280 queries. Use batch mode with `-x`-style names (`<d>.<c>.<b>.<a>.in-addr.arpa PTR`) and add PTR hostnames that end with the target domain as source `ptr`; keep the others as informational `data.ips[ip].ptr`.

Progress for this stage must be reported as `done_queries / total_queries` so the UI can show a bar.

### Stage 7: Enrichment [P]
1. **Resolve everything:** for every name in `data.subdomains` and the apex, query `A`, `AAAA` and `CNAME` (the A query already shows the CNAME chain in its answer section). Use batch mode again for speed, rotating resolvers. Store `a`, `aaaa`, `cname_chain`, `status` (NXDOMAIN / NOERROR / SERVFAIL).
2. **Dangling CNAME check:** for each CNAME chain, take the final target; query its `A`. If `NXDOMAIN`, mark `dangling = true`. Separately, if the target ends with any suffix from `providers.json` `takeover_suffixes`, mark `takeover_prone_provider = "<name>"`.
3. **Private/reserved IP check:** with `ipaddress`: `is_private`, `is_loopback`, `is_link_local`, `is_reserved`, plus CGNAT `100.64.0.0/10`. Mark names pointing at them.
4. **IP ownership via dig (Team Cymru):** for each unique public IPv4, reverse the octets and query `dig +short TXT <d>.<c>.<b>.<a>.origin.asn.cymru.com`. The answer looks like `"13335 | 1.1.1.0/24 | US | arin | 2010-07-14"`, which gives ASN, prefix, country. Then `dig +short TXT AS<asn>.asn.cymru.com` gives the owner name in the last field. For IPv6 use the nibble-reversed name under `origin6.asn.cymru.com`. Classify `provider_type` as `shared_provider` if the owner matches `shared_provider_keywords`, else `own_or_other`.
5. **PTR for discovered IPs:** `dig +short -x <ip>` for each unique IP (cap 500).
6. **Domain whois:** `whois <registered_domain>` (timeout 30). Extract with tolerant regexes (they differ by registry): registrar, creation date, expiry date, `Domain Status` lines (look for `clientTransferProhibited`, `clientDeleteProhibited`, `clientUpdateProhibited`, `serverTransferProhibited`). Parse dates in common formats (`YYYY-MM-DD`, `YYYY-MM-DDTHH:MM:SSZ`, `DD-Mon-YYYY`). If `whois` fails or returns nothing parseable: grey. Do not guess.
7. **Interesting names:** mark names whose labels match `interesting_names.json` `labels` (`dev, test, staging, stage, uat, qa, admin, vpn, jenkins, gitlab, grafana, kibana, phpmyadmin, internal, intranet, backup, old, beta, sandbox, demo, debug, jira, confluence, portal, sso, ldap, rdp, ssh, db, mysql, postgres, redis, elastic, s3, ftp, mail, webmail, owa, exchange, remote`, ...).
8. **Group** hosts by IP, ASN and provider for the "IP & Ownership" view.

### Stage 8: Analysis and flags
Run the rule engine (section 9) over `data{}`. Also add grey findings for every coverage entry whose status is `failed` or `skipped`, and a green/yellow/red per rule outcome. Compute the **posture score** = `100 - 15*reds - 4*yellows`, floor 0, shown as "indicative only".
Generate the **"What to look at next"** list: up to 8 plain sentences derived from red and yellow findings (for example "Zone transfer is allowed on ns1: pull the full zone and review hosts").

### Stage 9: Report
Write `scan.json`, and prepare the exports (section 11). Mark the scan `done`.

---

## 9. Rule engine and flag catalog

Rules are plain Python functions registered in a list. Each takes `data` and returns zero or more `Finding` objects. A rule must emit a **green** finding when its check ran and passed, and a **grey** finding when the data it needs is missing because a check failed. Every finding needs: `title`, `evidence` (the actual values), `why` (one plain sentence), `fix` (one plain sentence, may be empty for green).

Add new rules by adding one function. The list below is the **starting** catalog; implement all of it.

**General / records**
| ID | Condition | Flag |
|---|---|---|
| GEN-001 | Wildcard DNS detected | yellow (brute-force results filtered) |
| GEN-002 | Resolvers disagree on NS, MX, TXT, SOA or CAA | yellow |
| GEN-003 | Resolvers disagree only on A/AAAA | green (note: normal for CDNs/geo DNS) |
| GEN-004 | Apex has no A and no AAAA, but `www` has | yellow (info) |
| GEN-005 | Apex returned SERVFAIL on any resolver | red |

**Nameservers**
| ID | Condition | Flag |
|---|---|---|
| NS-001 | Fewer than 2 distinct nameservers | red |
| NS-002 | 2 or more nameservers | green |
| NS-003 | A nameserver does not respond (lame) or is unresolvable | red |
| NS-004 | A responsive nameserver lacks the `aa` flag | red |
| NS-005 | Parent NS set differs from child NS set | yellow |
| NS-006 | SOA serials differ between nameservers | yellow |
| NS-007 | A nameserver does not answer over TCP | yellow |
| NS-008 | All nameserver IPs in the same ASN, or all in one /24 | yellow |
| NS-009 | Nameservers across 2 or more ASNs | green |

**Active checks**
| ID | Condition | Flag |
|---|---|---|
| AXFR-001 | Zone transfer allowed by any nameserver | red |
| AXFR-002 | All nameservers refused zone transfer | green |
| AXFR-003 | Active mode off or transfers could not be tested | grey |
| CH-001 | `version.bind`/`hostname.bind`/`id.server` leaks text | yellow |
| REC-001 | An authoritative nameserver allows open recursion | red |
| NSEC-001 | Zone uses plain NSEC (names can be walked) | yellow |

**Email**
| ID | Condition | Flag |
|---|---|---|
| MX-001 | No MX and no null MX | yellow |
| MX-002 | Null MX present | green |
| MX-003 | An MX target does not resolve | red |
| MX-004 | An MX target is a CNAME (not allowed by the standard) | yellow |
| MX-005 | Only one MX host | yellow |
| MX-006 | Mail provider identified | green (evidence: provider name) |
| SPF-001 | No SPF record | red |
| SPF-002 | More than one SPF record | red |
| SPF-003 | `all` qualifier: `-all` green; `~all` yellow; `?all` yellow; `+all` red; no `all` yellow | by value |
| SPF-004 | More than 10 DNS lookups | red |
| SPF-005 | Uses the `ptr` mechanism | yellow |
| SPF-006 | An `include:` target does not resolve | yellow |
| SPF-007 | An `ip4:` range wider than /16 (or `ip6:` wider than /32) | yellow |
| DMARC-001 | No DMARC record | red |
| DMARC-002 | `p=none` | yellow |
| DMARC-003 | `p=quarantine` or `p=reject` | green |
| DMARC-004 | `pct` below 100 | yellow |
| DMARC-005 | No `rua` reporting address | yellow |
| DMARC-006 | `sp` is weaker than `p` | yellow |
| DKIM-001 | At least one DKIM selector found | green |
| DKIM-002 | No selector found among those tried | grey (cannot prove absence) |
| MTASTS-001 | MTA-STS present | green |
| MTASTS-002 | MTA-STS missing | yellow |
| TXT-001 | Verification records reveal third-party services | yellow (info exposure; list services) |
| TXT-002 | A TXT record matches the secret-looking pattern | red |

**DNSSEC / CAA**
| ID | Condition | Flag |
|---|---|---|
| DNSSEC-001 | No DS/DNSKEY (DNSSEC not enabled) | yellow |
| DNSSEC-002 | Enabled and a validating resolver set `ad` | green |
| DNSSEC-003 | DS exists but validation breaks | red |
| DNSSEC-004 | Weak algorithm in DS or DNSKEY | yellow |
| CAA-001 | CAA present | green |
| CAA-002 | CAA missing | yellow |

**Subdomains and hosts**
| ID | Condition | Flag |
|---|---|---|
| SUB-001 | Count of discovered subdomains and sources | green (info) |
| SUB-002 | Names matching the interesting-names list | yellow (list them) |
| SUB-003 | A name resolves to a private/reserved IP | yellow |
| SUB-004 | Dangling CNAME (target NXDOMAIN) | red (possible subdomain takeover) |
| SUB-005 | CNAME points to a takeover-prone provider and still resolves | yellow (verify the resource is claimed) |
| SUB-006 | Name found in certificate logs but does not resolve | yellow (historic or internal naming exposed) |
| SUB-007 | Name found in certificates only; brute force and DNS never confirmed | green (info) |
| IP-001 | Hosting overview: which ASNs/owners hold the hosts | green (info) |
| IP-002 | Reverse DNS of an IP exposes internal-looking names | yellow |

**Registration**
| ID | Condition | Flag |
|---|---|---|
| WHOIS-001 | Expires in under 30 days | red; under 90 days yellow; otherwise green |
| WHOIS-002 | No transfer/delete lock status | yellow |
| WHOIS-003 | Domain younger than 30 days | yellow (info) |
| WHOIS-004 | whois failed | grey |

---

## 10. Explanations ("proper description of everything")

Every record type and finding must teach. `knowledge/records.json` maps each type to:
```json
{ "MX": { "name": "Mail exchanger", "what": "Says which servers accept email for the domain, with a priority number (lower is tried first).",
          "why_recon": "Reveals the email provider and sometimes internal mail hosts.", "example": "10 mail.example.com." } }
```
Cover: A, AAAA, NS, MX, TXT, SOA, CNAME, CAA, SRV, HTTPS, SVCB, PTR, DS, DNSKEY, RRSIG, NSEC, NSEC3, NSEC3PARAM, AXFR, IXFR, CHAOS TXT.
In the UI, record-type labels show this text as a hover/focus tooltip and in a "What is this?" expander. Write the text in plain English for a student.

---

## 11. Backend API

All `/api/*` routes require the token header (section 5). JSON in, JSON out.

| Method and path | Purpose |
|---|---|
| `GET /` | Serves `static/index.html` only if `?token=` matches. |
| `GET /static/...` | Static files. |
| `GET /api/tools` | `{dig: true/false, whois: true/false, versions: {...}}` |
| `POST /api/scans` | Body `{target, wordlist, active, authorized}`. Validates, starts the background thread, returns `{scan_id}`. 409 if a scan is already running. 400 with a clear message on bad input. `active:true` without `authorized:true` returns 400. |
| `GET /api/scans` | List of past scans (id, domain, date, flag counts, status). |
| `GET /api/scans/<id>` | Full state for polling: scan status, stages with status, current command, progress `{done, total}`, findings so far, data, recent command log (last 50 with `command_line`, duration, exit status). |
| `GET /api/scans/<id>/commands/<cid>` | Raw output of one command as `text/plain` (truncated at 200 KB). |
| `POST /api/scans/<id>/cancel` | Sets the cancel flag. |
| `GET /api/scans/<id>/export?format=json\|md\|html` | Download the report. The HTML export is a single self-contained file with the same CSS inlined (exports are allowed to inline CSS since they are standalone files, not served by the app). |
| `GET /api/compare?a=<id>&b=<id>` | Differences: new/removed subdomains, changed records, flags that changed. |
| `POST /api/accept-terms` | Records the terms version accepted (stored in `scans/settings.json`). The frontend shows the terms screen when the stored version differs from the current `TERMS_VERSION`. |

The frontend **polls** `GET /api/scans/<id>` once per second while the scan runs (no WebSockets, no SSE; polling is simpler and enough).

---

## 12. Frontend: look, behavior and rules

### 12.1 Hard rules
- Vanilla JS modules, one `app.css`. No inline scripts and no inline `style=` (the CSP forbids them). Use CSS classes and CSS custom properties; to set a dynamic value (like a progress percentage), set a CSS variable through `element.style.setProperty('--p', value)` from JS (this is allowed under the CSP because it is done by script, not inline markup).
- Build elements with a helper `el(tag, {class, text, attrs}, children)` that uses `createElement` and `textContent`. **Never `innerHTML` with any data from the scan.**
- Keyboard accessible, visible focus rings, `prefers-reduced-motion` respected (turn off all animation), responsive down to 360 px width.
- Flags must **never rely on color alone**: each flag also has a distinct shape/icon and a text label (green: check mark in a circle; yellow: triangle; red: octagon with a cross; grey: dashed circle with a question mark). Draw them as small inline SVG built with `createElementNS`, or CSS shapes.

### 12.2 Visual direction: "sonar console"
The theme is a hacker console, but it must look like a modern product, not a 2010 terminal and not a Bootstrap page. The one memorable element is a **sonar ring**: while scanning, a radar-style ring sweeps and blips appear as hosts are discovered; when the scan finishes, the same ring becomes the posture score gauge. Everything around it stays calm and disciplined.

**Design tokens** (define as CSS custom properties on `:root`):

| Token | Value | Use |
|---|---|---|
| `--ink` | `#06090f` | page background (deep blue-black) |
| `--panel` | `#0c121c` | cards |
| `--panel-2` | `#111a28` | raised/hover panels |
| `--line` | `#1c2a3d` | borders |
| `--text` | `#d7e2f0` | body text |
| `--muted` | `#7f93ab` | secondary text |
| `--accent` | `#38f2c4` | primary accent (phosphor mint), buttons, focus |
| `--accent-2` | `#4aa8ff` | links, info |
| `--green` | `#2bd67b` | flag green |
| `--yellow` | `#ffc53d` | flag yellow |
| `--red` | `#ff4d6a` | flag red |
| `--grey` | `#8794a6` | flag grey |

**Type:** monospace for data, code, hostnames, IDs and the logo: stack `"JetBrains Mono", "Cascadia Code", "Fira Code", "SF Mono", Consolas, monospace` (no webfont download; whichever is installed is used). Body copy and descriptions in a clean system sans stack `"Inter", "Segoe UI", system-ui, -apple-system, sans-serif`, which keeps explanations readable. Use sentence case for labels (no all-caps labels, no tracked-out eyebrow text). Line length under 80 characters for paragraphs. Type scale: 12 / 14 / 16 / 20 / 28 / 40 px.

**Surfaces:** panels with 1 px `--line` borders, **two different radii** (10 px for cards, 4 px for chips and inputs), subtle inner glow on the active panel, a faint scanline texture on the page background drawn with a repeating CSS gradient at about 3 percent opacity. Findings use a 4 px colored left bar in the flag color plus a faint tint of the same color in the background. The main button has an animated gradient border (CSS only, paused for reduced motion). No heavy glow everywhere: glow is reserved for the focused input, the main button and red findings.

**Motion** (only these): the sonar sweep while scanning; the pipeline node of the running stage pulses; counters count up once when the report appears; expanding evidence panels slide open. Nothing else animates.

### 12.3 Screens and layout

**A. Terms screen** (first launch, or when `TERMS_VERSION` changes): centered card with the terms text from `TERMS.md` (section 13), a checkbox "I have read and agree", and a Continue button disabled until ticked.

**B. Home / New scan**
```
┌─────────────────────────────────────────────────────────────┐
│ ReconDeck▌                          [tools: dig ✓ whois ✓]   │
├───────────────┬─────────────────────────────────────────────┤
│ Past scans    │   Enter a domain to map everything about it │
│ (list, flags) │   [ example.com or a URL .................. ]│
│               │   Wordlist  (• small  ○ medium  ○ large)     │
│               │   [ ] Active probing (zone transfer, brute   │
│               │       force, version queries)                │
│               │   [ ] I own this domain or have written      │
│               │       permission to test it                  │
│               │   [   Scan everything   ]                    │
└───────────────┴─────────────────────────────────────────────┘
```
- The button is disabled until a valid-looking target is typed **and** the authorization box is ticked. Validate client-side loosely; the server validates strictly.
- The active-probing toggle shows a short warning in plain words: "Sends many queries to the target's own servers. Only use on domains you are allowed to test."
- Left rail lists past scans (domain, date, a tiny row of four flag-count dots) and opens them. Include a "Compare" action to pick two scans of the same domain.

**C. Scanning view** (replaces the main area while running)
- Large **sonar ring** centered at the top with the target name inside. Blips appear for every host discovered (use the count of subdomains for the number of blips, placed at deterministic positions based on a hash of the hostname).
- **Pipeline stepper**: stages 0 to 9 as nodes in a row (wraps on small screens), each with a state: waiting (dim), running (pulsing accent), done (green check), failed (red cross), skipped (grey dash). Stage names: Prepare, Core records, Nameservers, Email, DNSSEC, Passive subdomains, Active probing, Enrichment, Analysis, Report.
- **Progress bar** for the current stage with `done/total` when available (brute-force and sweeps), and an elapsed-time clock.
- **Live console** panel: scrolling list of the most recent commands, each as `$ dig @1.1.1.1 example.com MX ...` in monospace with duration and a small status dot. Auto-scroll with a "pause" toggle. This panel is the "I can see exactly what ran" proof.
- A **Cancel scan** button.
- Findings stream in: a small counter strip (red/yellow/green/grey) updates live.

**D. Report view** (when `status = done`, also reached from past scans)
- Header: target, scan date, duration, "scanned registered domain X (you entered Y)" if they differ, export buttons (JSON, Markdown, HTML).
- **Posture ring** (the sonar ring turned into a gauge showing the score 0 to 100, colored by value) next to **four large flag counters** (red, yellow, green, grey). Clicking a counter filters the Findings tab to that flag.
- **Summary strip:** mail provider, number of nameservers, DNSSEC yes/no, subdomains found, hosting providers, domain expiry.
- **Tabs:** Findings, Records, Nameservers, Email, DNSSEC, Subdomains, IP and ownership, Commands, Coverage, What next.
  - **Findings:** sorted red, yellow, green, grey. Each is a card: flag icon and label, ID chip (for example `SPF-003`), title, the "why it matters" sentence, a collapsible **Evidence** block (monospace, the real values), and a "How to fix" line. Search box and flag filter chips at the top.
  - **Records:** a table per record type: name, TTL, value, which resolvers returned it, an agreement marker. Type labels have the explanation tooltip.
  - **Nameservers:** one card per nameserver: IPs, ASN/owner, `aa` flag, SOA serial, TCP support, response time, zone-transfer result, version leak, recursion result, each with its own small flag.
  - **Email:** the MX list with priorities and provider; SPF broken down mechanism by mechanism with the lookup counter (`7 / 10`); DMARC tags as a small table; DKIM selectors tried and found; MTA-STS/TLS-RPT/BIMI status.
  - **DNSSEC:** chain status, algorithms with a strong/weak chip, NSEC/NSEC3.
  - **Subdomains:** sortable, filterable table: flag dot, hostname, A/AAAA, CNAME chain, owner/ASN, source chips (`crt`, `brute`, `axfr`, ...), notes (dangling, private IP, interesting). Row count, search box, "only interesting" and "only problems" toggles, and "export CSV" (generated client-side from the data).
  - **IP and ownership:** hosts grouped by ASN/owner with counts; reverse DNS names.
  - **Commands:** every command that ran, each as a terminal-style collapsible: `$ command line`, duration, exit code, and the raw output loaded on demand from `/api/scans/<id>/commands/<cid>`.
  - **Coverage:** the honest list: every check, ran / failed / skipped, with the reason, plus the limits ("brute force used a 200-word list, so unusual names can be missed", "zone transfer refused by all nameservers", "crt.sh unreachable"). Include a permanent note: "No DNS tool can list everything. Names that never appear in certificates and are not in the wordlist can stay hidden."
  - **What next:** the generated "what to look at next" list.
- **Compare view:** two scans side by side with added/removed/changed items highlighted.

**Empty and error states:** say what happened and what to do ("dig is not installed. Run: sudo apt install dnsutils"). Errors never apologize and are never vague.

---

## 13. Terms (put this text in `TERMS.md`, show it on first launch, and show a one-line version on every scan form)

```
ReconDeck Terms of Use (version 1)

1. Purpose. ReconDeck is for education and authorized security testing only.
2. Authorization. By using it you confirm that you own each domain you scan or
   have explicit permission to test it, and that you are responsible for knowing
   the laws and rules that apply to you.
3. Active scanning. Zone transfer attempts, subdomain brute force, version
   queries and reverse sweeps send many queries to the target's own servers.
   You are responsible for that traffic.
4. No misuse. Do not use this tool against systems you are not authorized to
   test, or to harass, disrupt or gain unauthorized access to anything.
5. No warranty. Results may be incomplete or wrong. A green flag does not prove
   a domain is secure.
6. Liability. The developer is not responsible for how the tool is used or for
   any damage that results.
7. Privacy. ReconDeck runs on your own machine. The developer collects no data.
   Queries go to public DNS resolvers, the domain's own nameservers, whois
   servers and crt.sh (certificate transparency).
```
Define `TERMS_VERSION = 1` in `config.py`. Also mention these terms at the top of this repo's final README for GitHub visitors.

---

## 14. Launchers and quick start

**`start.sh`** (runs in WSL/Linux): create `.venv` if missing, `pip install -r requirements.txt` into it, check `dig` and `whois` exist (print the `apt install` line if not), then run `python app.py --port 5000`.

**`app.py`** on start: generate the token, bind `127.0.0.1`, pick another port if 5000 is busy, print `ReconDeck running at http://127.0.0.1:<port>/?token=<token>`, and try to open the browser: if `cmd.exe` exists (WSL) run `["cmd.exe", "/c", "start", "", url]`, otherwise `webbrowser.open(url)`.

**`start.bat`** (Windows): calls WSL, converting its own folder path:
```
@echo off
wsl bash -lc "cd \"$(wslpath -u '%~dp0')\" && bash start.sh"
pause
```
Test this on a real Windows + WSL machine; if path conversion fails, fall back to printing instructions to open WSL and run `bash start.sh`.

**Quick start for the final README** (write this for GitHub visitors):
1. Install WSL Ubuntu, then in Ubuntu: `sudo apt update && sudo apt install -y dnsutils whois python3 python3-venv python3-pip`
2. `git clone <repo>` then double-click `start.bat` (or run `bash start.sh` in WSL/Linux).
3. Accept the terms, enter a domain you are allowed to test, tick the authorization box, click **Scan everything**.
4. Safe practice targets: `zonetransfer.me` (deliberately set up for zone transfer practice), your own domain, or lab platforms like HackTheBox and TryHackMe.

---

## 15. Build milestones (do them in this order; test each)

**M1: Foundations.** Project skeleton, `config.py`, `validators.py`, `runner.py`, `digparse.py` with all parsers and fixtures, unit tests passing. CLI check: a small script that runs `dig_query("example.com", "MX")` and prints the parsed result. *Done when:* tests pass and the script prints structured data.

**M2: Passive scan engine without UI.** Stages 0 to 4 and 7 (resolve, ownership, whois), the orchestrator, `models.py`, `store.py`. A CLI `python -m recondeck.orchestrator example.com` prints the findings as JSON. *Done when:* a scan of `example.com` saves `scans/<id>/scan.json` and raw outputs.

**M3: Rules.** Implement the entire catalog in section 9 with tests using fixtures (including bad-case fixtures: `+all` SPF, `p=none`, single NS, zone transfer allowed, dangling CNAME). *Done when:* every rule has at least one passing test for green and one for its non-green case where applicable.

**M4: Web backend.** Flask app, security layer (token, Host, Origin, headers), all API routes, background thread, polling state, cancel. *Done when:* with `curl` (including the token header) you can start a scan, poll it, fetch raw output and cancel; requests without the token or with a wrong Host get 403.

**M5: Frontend core.** Terms screen, home form, scanning view with pipeline, progress and live console, report view with counters and Findings tab. Visual design per 12.2. *Done when:* a full passive scan runs from the browser with live progress and a readable report.

**M6: Remaining report tabs.** Records, Nameservers, Email, DNSSEC, Subdomains, IP and ownership, Commands, Coverage, What next, exports (JSON, Markdown, HTML), past scans list, compare view.

**M7: Active mode.** Stages 5 (crt.sh) and 6 (AXFR, CHAOS, recursion, NSEC walk, brute force with wildcard filtering, recursion, PTR sweep), wordlists, progress reporting. Test only against `zonetransfer.me` and domains you own. *Done when:* the `zonetransfer.me` scan reports AXFR-001 red with the records listed.

**M8: Polish and docs.** `start.bat`/`start.sh`, README for GitHub visitors (screenshots, quick start, tool comparison table explaining why dig is the single engine and what `host`, `nslookup` and `dnsenum` add or do not add), `TERMS.md`, `LICENSE` (MIT), `.gitignore`, security review against section 5, accessibility pass (keyboard, reduced motion, 360 px width).

---

## 16. Acceptance checklist (the agent must verify every item before declaring done)

- [ ] No `shell=True` anywhere; `grep -R "shell=True"` returns nothing.
- [ ] No `innerHTML`, `outerHTML`, `insertAdjacentHTML` or `document.write` in `static/`; `grep` returns nothing.
- [ ] Server binds only to `127.0.0.1`.
- [ ] Requests without a valid token, or with a foreign Host or Origin, are rejected.
- [ ] Targets starting with `-`, containing spaces, `;`, `|`, `&`, backticks, `$(`, newlines, or IP addresses are rejected by the validator (tests included).
- [ ] A TXT record containing `<script>alert(1)</script>` is displayed as visible text and does not execute (test with a fixture).
- [ ] Active stage cannot be started by the API unless both `active` and `authorized` are true.
- [ ] Grey is shown for every failed or skipped check, never green.
- [ ] A scan survives one failing stage and still produces a report.
- [ ] Cancel works within a few seconds and keeps partial results.
- [ ] The UI shows the exact command for every step and the full raw output on demand.
- [ ] Flags are distinguishable without color (icon and text).
- [ ] Works at 360 px width and with reduced motion on.
- [ ] Works with no internet except for the target queries themselves (no CDN or external font requests; verify in the browser's network panel).

---

## 17. Appendix: starter wordlist (`wordlists/small.txt`, one per line)

```
www www1 www2 mail mail1 mail2 webmail smtp pop pop3 imap mx mx1 mx2 email owa exchange autodiscover autoconfig
ns ns1 ns2 ns3 dns dns1 dns2 vpn remote gateway gw firewall fw proxy admin administrator portal intranet internal
extranet corp staff hr erp crm helpdesk support status monitor monitoring grafana kibana prometheus nagios zabbix
jenkins ci cd build git gitlab github svn repo nexus artifactory docker registry k8s kubernetes dev dev1 dev2 test
test1 testing qa uat stage staging preprod prod demo sandbox beta alpha old new backup bak db db1 mysql sql postgres
mongo redis elastic ldap ad sso auth login id accounts oauth api api2 apis rest graphql app apps mobile m web web1
web2 static assets media img images cdn files download downloads upload ftp sftp share cloud s3 storage docs wiki
confluence jira blog news shop store pay payment billing secure ssl cpanel whm plesk webdisk phpmyadmin pma ssh rdp
vnc voip sip lync meet chat slack forum community events careers jobs partners vendor students alumni library lms
moodle exams research labs lab host server srv vps node1 node2 ntp time syslog log logs elk splunk vault secrets
config relay smtp2 mailgw antispam mailserver edge lb loadbalancer
```
(Write these one per line in the file.) For `medium.txt` (about 1,000) and `large.txt` (about 5,000), use a public list such as the SecLists `Discovery/DNS` top-subdomain files if you have internet access; otherwise create the files with whatever you can and note in `PROGRESS.md` that the user should drop in a larger list.

---

*ReconDeck is for authorized testing and learning. See `TERMS.md`.*
