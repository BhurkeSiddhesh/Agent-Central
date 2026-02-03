# 🌌 Agent-Central

**Agent-Central** is a centralized AI-Ops hub designed to supercharge any project with a specialized "Agency" of autonomous agents. Think of it as a master library of personas and **630+ agentic skills** that you can "pull" into any project repository.

---

## 🚀 The Centralized Architecture

Unlike tools that live inside your project, Agent-Central is a **Master Library**.

- **Master HQ (`agency-hq/`)**: Stays here. Contains all agent roles and the modular skills library.
- **Local Artifacts (`.ai-context/`)**: Generated in *your* project. Contains the team personas and skills you've hired for that specific task.

---

## 🛠 Setup & Global Usage

To use the `ai` commands from anywhere, you should set up an alias or add it to your path.

### 1. Installation
```bash
git clone https://github.com/BhurkeSiddhesh/Agent-Central.git
cd Agent-Central
pip install -r requirements.txt
```

### 2. Setting up the Alias (Recommended)
Add this to your shell profile (e.g., `.bashrc`, `.zshrc`, or PowerShell `$PROFILE`):

**PowerShell:**
```powershell
function ai { python -m Agent-Central.src.main $args }
```

---

## ⚡ Staffing Your Project

You can hire agents into any folder on your machine with a simple "Pull" workflow.

### Step 1: Create `agency.yaml`
In the root of your target project (e.g., `C:\Projects\My-App`), create an `agency.yaml`:

```yaml
project_name: "My-App"

# 🧠 Natural Language Requirements
# Describe what you need, and the tool will infer the best roles/skills.
project_requirements: "A React web app with a focus on accessibility and TDD."

# 👥 Explicit Agents (Optional)
required_agents:
  - architect

# 🛠 Explicit Skills (Optional)
required_skills:
  - brainstorming
```

### Step 2: The "Hire" Command
Navigate to your project folder and run:
```bash
ai hire role
```
*If you haven't set up an alias, use:* `python -m Agent-Central.src.main hire role`

**What happens next?**
1. Agent-Central reads your `agency.yaml`.
2. It **infers** that you need a `frontend-dev` and `jules-qa` based on your "accessibility" and "TDD" requirements.
3. It **pulls** the necessary `.md` files from the Master HQ into your project's `.ai-context/team/` and `.ai-context/skills/`.

---

## 📂 Project Anatomy

### In Agent-Central (The Library)
- `agency-hq/roles/`: Master definitions of Architects, Developers, Security, etc.
- `agency-hq/skills/`: **630+ modular skills** for specific tech stacks and protocols.
- `agency-hq/templates/`: Blueprints for new project configurations.

### In Your Project (The Ops Site)
- `.ai-context/team/`: The personas active for your current sprint.
- `.ai-context/skills/`: The specialized playbooks your agents are using.
- `.ai-context/HQ_REQUESTS.md`: If an agent or skill is missing from HQ, it's logged here for sync later.

---

## 📜 Ethical Protocols

Agent-Central operates under the **Durable Agent Protocol v2.1**, ensuring:
1. **Mandatory Pre-Flight Checks**: Branch sweeps before task execution.
2. **Context Anchors**: Persistent state management via `AGENTS.md`.
3. **No-Regression Quality Gates**: Strict automated validation.

---

## 📄 License
MIT License.
