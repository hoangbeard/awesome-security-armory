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
