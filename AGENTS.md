# Agent-Central - Workspace Instructions

## 1. Tech Stack
- Language: Python (likely for CLI), Node.js (alternative) - *To be decided based on implementation plan*
- CLI Framework: Typer (Python) or Commander (Node)
- LLM Integration: Google Gemini

## 2. Project Structure & File Placement
- `src/`: Source code for the CLI
- `tests/`: Automated tests
- `docs/`: Documentation

## 3. Code Patterns
- Clean Architecture
- Modular Agent definitions

## 4. Active Context
- Initial setup of the AI-Ops CLI tool.
- Implementing the "Agency" model.

## 5. Change Log (Reverse Chronological)
- [2026-02-03] Hardened Role Definitions (Protocol v2.2):
    - Added Mandatory Protocols, Guardrails, and Decision Trees to all core roles.
    - Standardized `task-assigner` and `jules-qa` enforcement.
- [2026-02-03] Integrated 630+ modular skills and `code-reviewer` agent from external repositories.
- [2026-02-03] Added `--project` argument to `hire` command for easier external project targeting.

- [2026-02-03] Added Dynamic Hiring feature (`hire --config`) and related documentation.

- [2026-02-03] Created comprehensive README.md.

- [2026-02-03] Prepared repository for publication (task.md, JULES_LOG.json audit).

- [2026-02-03] Initial creation of AGENTS.md

## 6. Learned
- [Pattern] Use `pydantic` for config validation to strict type checking.
- [Fix] Resolution for "ModuleNotFoundError" in decentralized CLI.

