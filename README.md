<div align="center">

# 🛰️ ReconDeck

### A local-first DNS reconnaissance workbench

Inspect a domain's public DNS posture, follow scan progress, review evidence, and export a report — from a browser UI served by your own machine.

![Python](https://img.shields.io/badge/Python-3.10%2B-7C3AED?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-0F172A?style=for-the-badge&logo=flask&logoColor=white)
![Interface](https://img.shields.io/badge/UI-Local%20only-7C3AED?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-0F172A?style=for-the-badge)

**For authorized testing and learning only.** ReconDeck is a work in progress; see [current capabilities](#-capabilities-and-scope) for what is implemented today.

</div>

---

## 🧭 Contents

- [Overview](#-overview)
- [Capabilities and scope](#-capabilities-and-scope)
- [How a scan works](#-how-a-scan-works)
- [Finding flags](#-finding-flags)
- [Security and privacy](#-security-and-privacy)
- [Requirements](#-requirements)
- [Getting started](#-getting-started)
- [Using the app](#-using-the-app)
- [Reports and saved scans](#-reports-and-saved-scans)
- [Project structure](#-project-structure)
- [Development and tests](#-development-and-tests)
- [Terms and Conditions](#-terms-and-conditions)
- [Contributing](#-contributing)
- [Project documents](#-project-documents)

## 🧩 Overview

ReconDeck is a Python/Flask application that runs on your computer and serves a browser interface at `127.0.0.1`. It collects selected public DNS and domain-registration information, records command output and coverage, and presents findings with explanations.

The project is designed to make DNS review more understandable than a collection of disconnected terminal commands:

- **One local interface** for submitting and following a scan.
- **Visible coverage and evidence** so a finding is not just a bare alert.
- **Structured results** saved locally under `scans/`.
- **Report exports** in JSON, Markdown, and HTML.
- **A clear boundary** between checks that are implemented and stages that have not yet been built.

> [!IMPORTANT]
> ReconDeck is not a guarantee of security, a substitute for a full assessment, or proof that a domain is safe. Only scan domains for which you have explicit authorization.

## 🧰 Capabilities and scope

### Implemented scan checks

| Area | What the current implementation does |
|---|---|
| 🎯 Target handling | Accepts a domain or URL, normalizes the hostname, and rejects malformed, local/private-name, or IP-address targets. |
| 🧪 Prerequisites | Checks for `dig`, checks `whois` availability, and probes configured public DNS resolvers. |
| 🌐 DNS records | Queries A, AAAA, NS, MX, TXT, SOA, CNAME, CAA, HTTPS, SVCB, and selected SRV records for the target and `www` hostname. |
| 🧭 Nameservers | Collects NS answers, performs a DNS trace, and queries A/AAAA records for returned nameservers. |
| ✉️ Mail DNS | Collects MX and TXT data plus DMARC, MTA-STS, and BIMI TXT records. |
| 🔏 DNSSEC | Queries DNSKEY, DS, and NSEC3PARAM records. |
| 🗂️ Registration | Runs `whois` for the target domain and records output. |
| 📄 Scan artifacts | Saves scan data, coverage, command records, and raw command output locally in the scan directory. |

### App and report features

- 🪪 First-run terms acceptance screen.
- 📡 Background scan workflow with stage status and progress.
- 🧾 Findings, record data, and command history in the browser UI.
- 📤 JSON, Markdown, and HTML report downloads.
- 🔐 Local API token and loopback request checks.
- 🗃️ Recent scans loaded from local scan storage.

### Incomplete / not yet implemented

The project has scan stages and UI controls for planned functionality that are **not complete** in this version. In particular:

- Passive subdomain discovery is currently a placeholder.
- Active probing, including zone-transfer attempts and wordlist-based discovery, is deferred and is not performed by the current active stage.
- Some advanced finding analysis and broader report views remain under development.
- Scan comparison exists as a backend capability, but should not be assumed to be a complete comparison workflow in the browser UI.

Where a check is not performed, its coverage should not be read as a healthy result. Check the report's status, evidence, and coverage before drawing conclusions.

## 🔄 How a scan works

1. You submit an authorized domain in the local browser UI.
2. ReconDeck validates and normalizes the input.
3. A background job runs the available scan stages.
4. The app records result data, command metadata, and raw output under `scans/<scan-id>/`.
5. Findings and coverage are shown in the UI and can be exported.

The scanner uses **`dig` as its DNS query tool** and **`whois` for registration information**. DNS queries are sent to the resolvers configured in `recondeck/config.py`; the scan also queries the target's DNS data. Requests to these external services are necessary for the checks. The app itself binds to loopback and does not provide a hosted ReconDeck service.

## 🚦 Finding flags

| Flag | Meaning |
|---|---|
| 🟢 **Green** | A check ran and the rule considered its result healthy or expected. Green is not a general security certification. |
| 🟡 **Yellow** | Informational data or something that may deserve review. |
| 🔴 **Red** | A potential misconfiguration or exposure to investigate. It does not mean the domain was compromised. |
| ⚪ **Grey** | The check could not run, is unavailable, or has not been implemented. Treat it as a coverage gap. |

## 🛡️ Security and privacy

ReconDeck is designed as a local application:

- **Loopback binding:** Flask listens on `127.0.0.1`, not on all network interfaces.
- **Runtime token:** a random token is generated when the app starts; the UI URL contains it and API calls require it.
- **Host and Origin checks:** API requests are checked against permitted loopback hosts and origins.
- **Argument-based process execution:** tool commands are launched without a shell, using argument lists.
- **Input validation:** target values are normalized and validated before use.
- **Local scan storage:** scan artifacts are written into the project's `scans/` directory.

Local-only does not mean no network traffic. DNS and WHOIS lookups leave your machine for the relevant resolvers and services. Do not include sensitive data in a scan target.

## 💻 Requirements

### Supported environment

- Python **3.10 or newer**
- `dig` (provided by the `dnsutils` package on Ubuntu)
- `whois`
- Windows users: WSL with Ubuntu is the recommended path; the launcher can also use native Windows Python if WSL is unavailable and the required command-line tools are installed on Windows.

### Python packages

The pinned dependencies are listed in [`requirements.txt`](./requirements.txt):

- Flask 3.1.0
- tldextract 5.1.2

The frontend uses plain HTML, CSS, and JavaScript; there is no frontend build step.

## 🚀 Getting started

### Windows — recommended (WSL)

1. Install WSL with an Ubuntu distribution if it is not already available.
2. Open Ubuntu and install the system prerequisites:

   ```bash
   sudo apt update
   sudo apt install -y dnsutils whois python3 python3-venv python3-pip
   ```

3. From Windows, double-click [`start.bat`](./start.bat).
4. Keep the launcher window open while using ReconDeck. The launcher starts the server and the app attempts to open the browser automatically.

If the browser does not open, use the authenticated loopback URL printed in the launcher window. Do not share that tokenized URL.

### Windows — native Python fallback

If `wsl.exe` is not available, `start.bat` tries a native Python setup. It requires the Python launcher (`py.exe`) plus Windows versions of `dig.exe` and `whois.exe` available on `PATH`. The script creates `.venv` if needed, installs the pinned Python requirements, and starts the server.

### WSL / Ubuntu / Linux — manual start

From the project directory:

```bash
sudo apt update
sudo apt install -y dnsutils whois python3 python3-venv python3-pip
bash start.sh
```

`start.sh` creates a project-local `.venv` if needed, installs `requirements.txt`, checks for `dig` and `whois`, then starts the app on port 5000 (or the next available port in its configured range).

### Manual Python setup

If you prefer to set up the environment yourself:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py --port 5000
```

Install `dig` and `whois` using your operating system's package manager before scanning. On Windows, activate the virtual environment with `.venv\Scripts\activate` and use a Python 3 installation that provides `py.exe`.

## 🖱️ Using the app

1. Start ReconDeck using the relevant instructions above.
2. Open the browser tab created by the launcher, or navigate to the tokenized loopback URL printed in the console.
3. Read and accept the terms shown on first use.
4. Enter a domain you own or are explicitly authorized to test. URL input is also accepted and normalized to a hostname.
5. Select the wordlist size if shown. **Wordlist-driven discovery is not implemented in the current active stage.**
6. Start the scan and monitor stage progress, findings, and command output.
7. Review the details and coverage status; grey or failed checks mean the report is incomplete.
8. Download a JSON, Markdown, or HTML report if needed.

The scan UI includes an active-probing authorization control. It does not mean active probing is available: the current active stage is deferred and reports that it did not run. Do not infer that selecting the control performed active checks.

## 📦 Reports and saved scans

Each scan is stored beneath `scans/<scan-id>/`, including:

- `scan.json` — structured scan state, collected data, stages, findings, and coverage.
- `raw/` — captured command output associated with recorded commands.
- `settings.json` — local terms-version acceptance state.

The browser UI offers JSON, Markdown, and HTML report downloads. Treat scan artifacts and exports as potentially sensitive reconnaissance data; protect them and share them only with authorized people.

## 🗺️ Project structure

```text
recondeck/
├── app.py                 # Flask web server, routes, and startup
├── recondeck/             # Configuration, validation, scanning, rules, reports
│   ├── stages/            # Ordered scan stages
│   └── rules/             # Finding analysis rules
├── static/                # Browser UI: HTML, CSS, vanilla JavaScript
├── tests/                 # Automated tests and fixtures
├── knowledge/             # Local reference data
├── wordlists/             # Wordlist files for planned/current scan controls
├── scans/                 # Local scan data (runtime output)
├── start.bat              # Windows launcher
├── start.sh               # WSL/Linux launcher
├── TERMS.md               # In-app Terms of Use
├── PROGRESS.md            # Milestone and validation notes
├── project_details.md     # Original technical specification
└── requirements.txt       # Pinned Python dependencies
```

## 🧪 Development and tests

Create and activate a virtual environment, install the requirements, then run the test suite:

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

WSL/Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

Tests cover the current parser, validation, rules, security, and report behavior. Network-dependent scanning checks should be tested only against authorized targets.

## ⚖️ Terms and Conditions

The following Terms of Use are included here for visibility and are also shown by the app on first launch. The app's canonical in-app copy is [`TERMS.md`](./TERMS.md).

> **ReconDeck Terms of Use (version 1)**
>
> **1. Purpose.** ReconDeck is for education and authorized security testing only.
>
> **2. Authorization.** By using it you confirm that you own each domain you scan or have explicit permission to test it, and that you are responsible for knowing the laws and rules that apply to you.
>
> **3. Active scanning.** Zone transfer attempts, subdomain brute force, version queries and reverse sweeps send many queries to the target's own servers. You are responsible for that traffic.
>
> **4. No misuse.** Do not use this tool against systems you are not authorized to test, or to harass, disrupt or gain unauthorized access to anything.
>
> **5. No warranty.** Results may be incomplete or wrong. A green flag does not prove a domain is secure.
>
> **6. Liability.** The developer is not responsible for how the tool is used or for any damage that results.
>
> **7. Privacy.** ReconDeck runs on your own machine. The developer collects no data. Queries go to public DNS resolvers, the domain's own nameservers, whois servers and crt.sh (certificate transparency).

These terms are provided as the project's usage notice and are not legal advice. Review applicable law and obtain authorization before running checks. The active checks described in the terms are not implemented in the current active stage; see [Capabilities and scope](#-capabilities-and-scope).

The privacy clause above reflects the project terms text. The current implemented stages do not yet query crt.sh; the current external lookups are the configured public DNS resolvers, the domain's DNS infrastructure, and WHOIS services.

## 🤝 Contributing

Contributions should preserve the local-only security model, safe subprocess handling, and clearly documented scan coverage. Please read [`CONTRIBUTING.md`](./CONTRIBUTING.md) and the original technical requirements in [`project_details.md`](./project_details.md) before making changes.

## 📚 Project documents

| Document | Purpose |
|---|---|
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | Contribution and testing guidance |
| [`PROGRESS.md`](./PROGRESS.md) | Milestone and validation history |
| [`TERMS.md`](./TERMS.md) | Canonical Terms of Use shown in the app |
| [`project_details.md`](./project_details.md) | Original detailed technical specification |
| [`LICENSE`](./LICENSE) | MIT License |

---

<div align="center">

🧭 **Stay authorized. Read the coverage. Treat unknowns as unknowns.**

</div>
