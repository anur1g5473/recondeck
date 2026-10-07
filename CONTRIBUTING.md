# Contributing to ReconDeck

Thanks for helping improve ReconDeck.

This project is intentionally focused, security-aware, and local-only. Contributions should stay aligned with the project goals and the technical constraints described in [project_details.md](./project_details.md).

## Core principles

- Keep the tool local-only and loopback-safe.
- Do not add unsupported third-party tooling or cloud services.
- Prefer deterministic rule-based checks over AI or external inference.
- Preserve the project’s minimal, offline-friendly architecture.
- Never broaden scope beyond the domain recon and reporting workflow.

## Before you contribute

1. Read [README.md](./README.md) for the project overview.
2. Read [project_details.md](./project_details.md) for the authoritative technical and security requirements.
3. Check the current milestone status in [PROGRESS.md](./PROGRESS.md).

## Development workflow

- Work in small, testable increments.
- Add or update tests for behavior changes.
- Validate the relevant test targets before finishing.
- Keep security and local-only enforcement in mind for every change.

## Code standards

- Use Python 3.10+ features only when compatible with the project’s target runtime.
- Avoid shell injection patterns. Never use `shell=True`.
- Keep user input validation strict and explicit.
- Prefer plain HTML, CSS, and vanilla JavaScript for the UI.
- Do not introduce frameworks, build tooling, or external asset dependencies.

## Testing

Run the project’s test suite before submitting changes:

```bash
pytest -q
```

If you are fixing a parser or rule, include fixture-based tests under `tests/fixtures/` where appropriate.

## Pull requests

PRs should be:

- small and focused
- clearly tied to a milestone or issue
- described with the change and validation steps
- consistent with the project’s local-only and DNS-first scope

## Reporting issues

Open an issue with:

- the problem summary
- reproduction steps
- expected behavior
- actual behavior
- whether it affects security controls or local-only runtime assumptions

## Community expectations

Be respectful, constructive, and careful about security-sensitive changes. The project’s goal is to remain safe, useful, and easy to reason about.

## A note on scope

ReconDeck is intentionally not a broad enterprise scanner. It is a focused DNS reconnaissance tool with clear operational boundaries. Keep changes aligned with that purpose.
