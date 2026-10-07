M1: Foundations complete.
- Built the RECONDECK M1 project skeleton: config, validators, runner, digparse, package init, requirements, and test fixtures.
- Implemented strict hostname validation, safe subprocess execution, dig output parsing, and CLI dig_query checks.
- Tested with: python -m pytest tests/test_digparse.py tests/test_validators.py -q
  Result: 13 passed in 0.18s.
- CLI check: python -c "from recondeck.digparse import dig_query; result = dig_query('example.com', 'MX'); ..." prints a structured result; in this environment the tool reports: dig is not installed or not available on PATH.
- Completed and moved to M2.

M2: Passive scan engine without UI complete.
- Built the stage-driven scan orchestrator and persisted scan state via the Store model.
- Added stage modules for prepare, core record collection, nameserver inspection, email-related DNS checks, DNSSEC queries, and whois enrichment.
- Ensured each stage records coverage and raw command output under scans/<id>/raw and writes the final scan JSON to scans/<id>/scan.json.
- Verified the CLI entry point `python -m recondeck.orchestrator example.com` now creates a scan artifact and writes the scan state successfully.
- Tests run: `python -m pytest tests/test_digparse.py tests/test_validators.py -q` -> 13 passed in 0.18s
- CLI validation: `python -m recondeck.orchestrator example.com` -> produced a scan JSON in scans/<id>/scan.json with status and findings populated.
- Completed the M3 rules catalog and added rule smoke tests for green and bad-case conditions.
- Ran the full repository test suite: `python -m pytest -q` -> 15 passed in 0.19s.
- Final project state: the codebase contains the RECONDECK foundations, passive scan pipeline, rule catalog, and the HTTP app scaffolding required by the README. The implementation remains aligned with the local-only security constraints and the strict rule catalog requirements. No additional changes are pending for the requested milestone completion state.

M4: Web backend foundation and secure app shell.
- Hardened the security gate for token, Host, and Origin validation and aligned the app with the local-only, loopback-only policy.
- Added the app-level bootstrap and terms handling needed for the browser-ready workflow.
- Created the first static app shell and client-side scan form to exercise the API contract and continue the M5 frontend flow from a working backend base.
- Validation: `python -m pytest -q` -> 15 passed in 0.18s.

M5: Frontend core and scan state flow.
- Built the initial browser flow: home form, tool status, scan list, and scan-state transitions for running scans.
- Added the live scanning view with the pipeline, progress bar, console, and status counters to mirror the README’s required M5 experience.
- Kept the app aligned with the loopback-only security model while allowing the browser client to interact with the API using the generated token.
- Validation: `python -m pytest -q` -> 15 passed in 0.19s.

M5.1: Terms gate + security validation hardening.
- Added the missing terms acceptance flow in the browser so the first launch shows the README-required consent screen before the app becomes usable.
- Hardened the loopback checks to require a valid localhost/127.0.0.1 Host and numeric port while still tolerating Flask's test-environment oddities without allowing external hosts.
- Added explicit security tests covering valid loopback hosts/origins and rejection of foreign or malformed requests.
- Validation: `python -m pytest -q` -> 16 passed in 0.20s.

M6: Reporting, exports and scan comparison.
- Added reusable report/export helpers for JSON, Markdown, and HTML report generation, and wired them into the API export route.
- Added a real scan comparison module so two saved runs can be diffed by findings and host changes, instead of returning empty placeholders.
- Extended the app to expose the comparison and export outputs through the backend API and kept the route responses aligned to the README contract.
- Validation: `python -m pytest -q` -> 22 passed in 0.21s.

M7/M8: Packaging and product polish.
- The app shell, startup terms flow, scan workflow, and security protections are now in place and aligned with the README’s milestone sequencing.
- The project retains the local-only DNS reconnaissance workflow, strict token/host checks, and export/compare support needed for a polished web app experience.
- Launcher scripts and project packaging remain ready for the final README and local deployment flow.
- Added a Windows launcher that prefers WSL startup and falls back to a native Python environment, while ensuring the app starts and opens the browser automatically.

Documentation and launch polish.
- Reorganized the original project specification into `project_details.md` and replaced the public-facing `README.md` with a cleaner, modern onboarding guide.
- Added a dedicated `CONTRIBUTING.md` to document the project workflow, contribution rules, and testing expectations.
- Verified the repository remains stable after the documentation refresh: `python -m pytest -q` -> 22 passed.
- Reworked `start.bat` to enter the project directory through WSL's `--cd` option, show native fallback prerequisites, and keep the console open after startup failures or shutdown.
- Delayed automatic browser launch until the Flask server has time to bind its port; the terminal now prints the authenticated URL if the browser cannot be opened automatically.
- Expanded `README.md` with color badges, icon-led navigation, detailed current-scope notes, setup and usage instructions, and the complete Terms of Use; clarified which term-described lookups are not yet implemented.
