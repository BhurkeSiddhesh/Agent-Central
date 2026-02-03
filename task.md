# Task: Dynamic Agent Hiring Flow

## Objectives
- [x] Design Configuration File Schema (`agency.yaml`)
- [x] Update `HQService` to support remote/local HQ lookup
- [x] Implement `hire --from-config` command
- [x] Implement "Missing Agent" Request Mechanism
- [x] Verification w/ Mock Project

- [x] Design Configuration File Schema (`agency.yaml`)
- [x] Update `HQService` to support remote/local HQ lookup
- [x] Implement `hire --from-config` command
- [x] Implement "Missing Agent" Request Mechanism
- [x] Verification w/ Mock Project
- [x] Refactor `hire` to support `--project` argument
- [x] Import Skills & Agents from `antigravity-awesome-skills`
- [x] Implement Skill-aware Hiring
    - [x] Update `agency.yaml` to support `required_skills` and `project_requirements`
    - [x] Update `HQService` to copy skills to `.ai-context/skills`
    - [x] Implement keyword-based inference for agents/skills from requirements
    - [x] VERIFY: `hire --project` copies both agents and inferred skills.

- [ ] Refine Agent Roles (Protocol v2.2)
    - [ ] Rewrite `task-assigner.md` (Protocol Enforcement)
    - [ ] Rewrite `jules-qa.md` (Zero Regression)
    - [ ] Rewrite `architect.md` (System Design)
    - [x] Rewrite `frontend-dev.md`

- [ ] Knowledge Feedback Loop (Protocol v2.3)
    - [x] Create `agency-hq/knowledge/` structure
    - [x] Update `HQService` with `learn_from_project`
    - [x] Implement `ops learn` command
    - [x] Update `AGENTS.md` template with "Learned" section
    - [x] Implement Intelligence Layer (Synthesized Protocols)
    
- [ ] Smart Hiring (Protocol v3.0)
    - [ ] Create `agency-hq/skills/skills.json` registry (Manifest)
    - [ ] Implement `SkillService` (Registry Builder + Matcher)
    - [ ] Refactor `ai hire` to use Semantic Matching
    - [ ] VERIFY: Hire minimal set for a test project






