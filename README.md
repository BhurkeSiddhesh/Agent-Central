# 🌌 Agent-Central

**Agent-Central** is an AI-Ops CLI engine designed to orchestrate a specialized "Agency" of autonomous agents. It enforces strict protocols (like the Durable Agent Protocol) to manage codebases with high integrity, zero regressions, and seamless multi-agent collaboration.

---

## 🚀 Key Features

- **Multi-Agent Orchestration**: Specialized roles including Architects, Backend/Frontend Developers, Security, and QA.
- **630+ Agentic Skills**: A massive library of modular skills for debugging, TDD, cloud deployment, security auditing, and more.
- **Self-Evolving Intelligence**: Agents learn from every project via the **Knowledge Feedback Loop** (`ops learn` + `ops upskill`).
- **Protocol Enforcement**: Built-in support for "Durable Agent" workflows and automated quality gates.
- **Agency Sync**: Centralized management of task assignments, branch sweeps, and PR audits.
- **Persona Management**: Dynamic activation of agent personas based on the task at hand.

---

## 🛠 Tech Stack

- **Core**: Python 3.9+
- **CLI Framework**: [Typer](https://typer.tiangolo.com/) & [Rich](https://rich.readthedocs.io/)
- **Git Integration**: [GitPython](https://gitpython.readthedocs.io/)
- **Logic Engine**: YAML-based Agency HQ and Roster templates.

---

## 📂 Project Structure

```text
Agent-Central/
├── agency-hq/          # Agency blueprints and role definitions
│   ├── roles/          # Specialized agent personas (Architect, Code Reviewer, etc.)
│   ├── skills/         # 630+ modular agentic skills
│   ├── knowledge/      # Knowledge base for learned patterns
│   └── templates/      # Roster and configuration templates
├── src/                # Core CLI source code
│   ├── commands/       # CLI command implementations (init, hire, ops, etc.)
│   ├── services/       # Business logic (Git, HQ management)
│   └── main.py         # Application entry point
├── AGENTS.md           # Project DNA and Long-term memory
├── JULES_LOG.json      # Operation audit log for asynchronous agents
└── requirements.txt    # Dependency list
```

---

## ⚡ Getting Started

### 1. Installation

**Prerequisite**: Ensure you have Python 3.9+ installed and Git configured.

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/BhurkeSiddhesh/Agent-Central.git
    cd Agent-Central
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install the CLI Globally**:
    This registers the `ai` command on your system so you can use it in *any* project.
    ```bash
    pip install -e .
    ```

4.  **Verify Installation**:
    ```bash
    ai --help
    ```

---

## 📖 Command Reference

The `ai` CLI is your interface to the Agency. Here are all available commands:

### `init` - Setup
Bootstraps the Agency infrastructure in a new project.

- **`ai init project`**:
    - Creates `.agency-hq` (local copy of blueprints).
    - Initializes `.ai-context` (active team memory).
    - Creates `context/ACTIVE_PERSONA.md`.
    - **Usage**: Run this once at the root of any new project you want to manage.

### `hire` - Staffing
Bringing agents onto the team.

- **`ai hire [ROLE_NAME]`**:
    - Activates a specific persona (e.g., `ai hire architect`).
    - Updates `.ai-context/ACTIVE_PERSONA.md` with that role's instructions.
    - **Usage**: When you need to switch "hats" or assign a specific task.

- **`ai hire --project [PATH]`**:
    - Reads `agency.yaml` from the target project.
    - Automatically hires all required agents and skills.
    - **Usage**: `ai hire --project ../MyNewApp`
    - **Tip**: You don't need to specify agents explicitly if you provide `project_requirements` in YAML; the engine will **infer** the best team for you!

### `ops` - Operations & Learning
Managing the workflow and evolution of the Agency.

- **`ops sync`**:
    - Runs the "Task Assigner" protocol.
    - Audits `JULES_LOG.json`, checks active branches, and updates `SQUAD_GOAL.md`.
    - **Usage**: Run this at the start of a sprint or daily standup.

- **`ops status`**:
    - Displays the currently active persona.

- **`ops learn`** (Protocol v2.3):
    - **The Feedback Loop**: Scans your project's `AGENTS.md` for a `## Learned` section.
    - Extracts new patterns, bug fixes, or insights found during development.
    - Syncs them to the Central HQ (`agency-hq/knowledge/`).
    - **Usage**: Run after completing a feature or fixing a bug.

- **`ops upskill`** (Protocol v2.4):
    - **The Intelligence Layer**: Consolidates raw learnings into the Master Roles.
    - Uses an "Intelligence Layer" to synthesize raw notes into professional **Design Standards** or **Verification Protocols**.
    - **In Action**: If a project learns "Always use atomic writes", running `upskill` will update `architect.md` with a new "Design Standard: Atomic Writes" section.
    - **Usage**: Run periodically to upgrade your entire workforce.

---

## 🔄 The "Agency" Workflow

1.  **Define**: Create an `agency.yaml` describing your project needs.
2.  **Staff**: Run `ai hire --project .` to get your team.
3.  **Execute**:
    - `ai hire architect` -> Create `implementation_plan.md`.
    - `ai hire backend-dev` -> Write code.
    - `ai hire jules-qa` -> Run tests.
4.  **Learn**:
    - Document new findings in `AGENTS.md` -> `## Learned`.
    - `ai ops learn` -> Send knowledge to HQ.
    - `ai ops upskill` -> Upgrade the Agency.

---

## 📜 Ethical Protocols

Agent-Central operates under the **Durable Agent Protocol v2.1**, ensuring:
1. **Mandatory Pre-Flight Checks**: Branch sweeps before task execution.
2. **Context Anchors**: `AGENTS.md` and `task.md` for persistent state.
3. **No-Regression Quality Gates**: Strict linting and testing requirements.

---

## 📄 License

MIT License. See `LICENSE` (if available) for details.
