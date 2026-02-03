# 🌌 Agent-Central

**Agent-Central** is an AI-Ops CLI engine designed to orchestrate a specialized "Agency" of autonomous agents. It enforces strict protocols (like the Durable Agent Protocol) to manage codebases with high integrity, zero regressions, and seamless multi-agent collaboration.

---

## 🚀 Key Features

- **Multi-Agent Orchestration**: Specialized roles including Architects, Backend/Frontend Developers, Security, and QA.
- **Protocol Enforcement**: Built-in support for "Durable Agent" workflows and automated quality gates.
- **Agency Sync**: Centralized management of task assignments, branch sweeps, and PR audits.
- **Persona Management**: Dynamic activation of agent personas based on the task at hand.

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
│   ├── roles/          # Specialized agent personas (Architect, QA, etc.)
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

Clone the repository and install dependencies:

```bash
git clone https://github.com/BhurkeSiddhesh/Agent-Central.git
cd Agent-Central
pip install -r requirements.txt
```

### 2. Basic Usage

Initialize your project and bootstrap the Agency HQ:

```bash
python -m src.main init project
```

### 3. Hiring an Agent

Activate a specific persona to handle tasks:

```bash
python -m src.main hire architect
```

### 4. Syncing the Agency

Run the Task Assigner protocol to audit branches and update the board:

```bash
python -m src.main ops sync
```

---

## 📜 Ethical Protocols

Agent-Central operates under the **Durable Agent Protocol v2.1**, ensuring:
1. **Mandatory Pre-Flight Checks**: Branch sweeps before task execution.
2. **Context Anchors**: `AGENTS.md` and `task.md` for persistent state.
3. **No-Regression Quality Gates**: Strict linting and testing requirements.

---

## 🤝 Contributing

This project is designed for both human and AI collaboration. If you are an agent, please read `AGENTS.md` before initiating any pull requests.

---

## 📄 License

MIT License. See `LICENSE` (if available) for details.
