# Agent contract (public overview) — Controlled Dataset Generator

This project was built with an **agent-contract workflow**: before code was written,
a structured specification defined the tool's purpose, constraints, and invariants so
an AI model could produce consistent code across sessions.

This document is a **public overview** of that approach. The full operational contract —
detailed rules, version-by-version instructions, and exact implementation directives —
is kept private.

---

## What the contract defines

A single source-of-truth document that an AI collaborator reads before each work session. It covers, at a high level:

- **Purpose** — what the tool is for and what it must produce.
- **Technology boundaries** — local-only Python (pandas, numpy, Tkinter); no API, cloud, or database.
- **Core outputs** — the fixed set of files every run must generate.
- **Invariants** — rules that must never break across versions.
- **Difficulty model** — the meaning of Type 1 / 2 / 3 errors.
- **Versioning** — the current version and what changed.

---

## Core invariants (high level)

- Stay **local and minimal** — no external services, no cloud deployment.
- Prefer **deterministic generation** via a seed.
- Keep output files **easy for another agent to read and compare**.
- Treat the **manifest as ground truth** and the JSON spec as the calibration summary.
- Count **schema-level errors once per column**, never multiplied per cell.
- Keep the **UI compact** and the generate action always accessible.

---

## Difficulty model

| Level | Intent |
|---|---|
| Type 1 — Simple | Easy to detect and clean automatically |
| Type 2 — Intermediate | May need validation or cautious cleaning |
| Type 3 — Advanced | Often detected or flagged rather than auto-cleaned |

---

## Why this workflow

Writing the contract first let each iteration resume with full context and produce
consistent, reviewable changes — without re-explaining the project every session.
The contract acts as a persistent agreement between the developer and the AI model:
it defines the rules and invariants so any capable model can continue the work.

> This is a deliberately partial view. The detailed contract is not published, to keep
> the operational instructions and internal structure private.
