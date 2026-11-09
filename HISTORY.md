# History

Tier changes take effect when Rex merges the pull request that carries them. Weekly automation opens that work on `weekly/YYYY-Www` and does not push to `main`.

## 2026-11-09 — v0.1

Initial curated catalogue. 121 repositories are listed (89 Main, 32 Watchlist). 11 candidates were not admitted. Metrics were collected the same day, Asia/Saigon, from public read-only sources. Nothing in the catalogue was cloned or executed. Scores and the group 90th-percentile thresholds are in `data/metrics/2026-11-09.json`. The star baseline for later growth is `data/snapshots/2026-11-09.json`.

### Counts

- AI Coding Agents & Harness: 8 Main, 9 Watchlist, 1 removed
- LLM, Agent Framework & MCP: 13 Main, 2 Watchlist, 2 removed
- AI Security: 10 Main, 4 Watchlist, 2 removed
- Offensive / Red Team: 12 Main, 4 Watchlist, 1 removed
- Defensive / Blue Team: 12 Main, 3 Watchlist, 1 removed
- Cloud & Kubernetes Security: 10 Main, 4 Watchlist, 1 removed
- DevSecOps / AppSec: 15 Main, 1 Watchlist, 1 removed
- Software & Dev Tools: 9 Main, 5 Watchlist, 2 removed

### Not admitted

- `RooCodeInc/Roo-Code` (AI Coding Agents & Harness) — archived. Last score 76.5.
- `Comfy-Org/ComfyUI` (LLM, Agent Framework & MCP) — out of scope (generative media). Last score 83.3.
- `AUTOMATIC1111/stable-diffusion-webui` (LLM, Agent Framework & MCP) — score 45.2, below 50.
- `protectai/llm-guard` (AI Security) — archived. Last score 57.8.
- `meta-llama/PurpleLlama` (AI Security) — score 47.7, below 50.
- `GreyDGL/PentestGPT` (Offensive / Red Team) — score 48.6, below 50.
- `TheHive-Project/TheHive` (Defensive / Blue Team) — archived. Last score 54.3.
- `aquasecurity/kube-hunter` (Cloud & Kubernetes Security) — no push in 24 months. Last score 55.8.
- `jeremylong/DependencyCheck` (DevSecOps / AppSec) — archived stub. The live project is `dependency-check/DependencyCheck`. Last score 48.2.
- `penpot/penpot` (Software & Dev Tools) — out of scope (drawing and design application). Last score 89.3.
- `excalidraw/excalidraw` (Software & Dev Tools) — out of scope (drawing and design application). Last score 66.7.

`gitleaks/gitleaks` scored 74.0 and sits on the DevSecOps Watchlist because that group already has 15 Main projects. `xai-org/grok-build` and `CyberStrikeus/CyberStrike` stay on the Watchlist under manual flags in `data/manual.yml`.

## 2026-11-09 — AI Skills

Ninth group, placed immediately after AI Coding Agents & Harness. Skill packs and rule collections are what those agents load, so the group sits there instead of among general LLM frameworks. 31 repositories are listed (13 Main, 18 Watchlist). 23 candidates were not admitted. Metrics were collected the same day from the public GitHub API with `scripts/collect.py`. Nothing in the group was cloned or executed. Scores use the v0.1 rubric, normalized inside this group. Tiers take effect when Rex merges the pull request.

### Counts

- AI Skills: 13 Main, 18 Watchlist, 23 removed

### Not admitted

- `K-Dense-AI/scientific-agent-skills` (AI Skills) — out of scope (scientific research skills, not security or coding). Last score 86.4.
- `NVIDIA/SkillSpector` (AI Skills) — out of scope (skill scanner, not a skill pack). Last score 84.5.
- `vercel-labs/skills` (AI Skills) — out of scope (skill installer CLI, not a skill pack). Last score 83.4.
- `OpenMontageInc/OpenMontage` (AI Skills) — out of scope (video production, not security or coding). Last score 77.2.
- `Shubhamsaboo/awesome-llm-apps` (AI Skills) — out of scope (LLM app examples, not agent skill packs). Last score 74.6.
- `blader/humanizer` (AI Skills) — out of scope (prose rewriting, not a coding or security skill). Last score 69.1.
- `zero-lab-ai/skills` (AI Skills) — repo younger than 30 days. Last score 59.4.
- `ComposioHQ/awesome-claude-skills` (AI Skills) — score 47.6, below 50. No license file.
- `instructa/ai-prompts` (AI Skills) — score 46.2, below 50.
- `Security-Phoenix-demo/security-skills-claude-code` (AI Skills) — score 44.7, below 50.
- `Masriyan/Claude-Code-CyberSecurity-Skill` (AI Skills) — score 42.6, below 50. Modified MIT, not counted as an OSI SPDX license.
- `raroque/vibe-security-skill` (AI Skills) — score 39.8, below 50.
- `anthropics/claude-code-security-review` (AI Skills) — out of scope (GitHub Action, not a skill pack). Last score 39.0.
- `superagent-ai/skills` (AI Skills) — score 38.7, below 50.
- `Hi-FullHouse/CyberSecurity-Skills` (AI Skills) — score 38.3, below 50.
- `semgrep/skills` (AI Skills) — score 38.0, below 50. Semgrep Rules License v1.0, not OSI.
- `sanjeed5/awesome-cursor-rules-mdc` (AI Skills) — score 36.8, below 50.
- `slowmist/slowmist-agent-security` (AI Skills) — score 33.1, below 50.
- `Batman0506/openclaw-sec-skills` (AI Skills) — score 31.5, below 50.
- `travisvn/awesome-claude-skills` (AI Skills) — score 30.6, below 50. No license file.
- `instavm/security-skills` (AI Skills) — score 26.6, below 50. No license file.
- `EvanThomasLuke/Awesome-AI-Security-Skills` (AI Skills) — score 23.7, below 50. No license file.
- `mrhlaingbwardev/web-security-skill` (AI Skills) — score 19.5, below 50. No license file.

`affaan-m/ECC` (89.4) and `mattpocock/skills` (75.9) stay on the Watchlist under the star-velocity anomaly (at least 1,000 stars per day since creation). `obra/superpowers` scored 69.5, just under the Main line. Several official skill repositories have no root license (`anthropics/skills`, `openai/skills`, `openai/plugins`, `cursor/plugins`, `vercel-labs/agent-skills`) and are Watchlist at most. The Main cap of 15 did not bind; 13 projects cleared it.
