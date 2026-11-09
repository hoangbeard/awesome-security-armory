# Scoring notes — v0.1 candidate data (2026-11-09, Asia/Saigon UTC+7)

> The committed lists are the authority: 102 Main, 50 Watchlist, 34 removed. v0.1 was 89 / 32 / 11. The AI Skills group added 13 Main, 18 Watchlist, and 23 not admitted. The table further down was the count before penpot and excalidraw were removed as out of scope (that table says 90 / 33 / 9). Production scripts live in `scripts/` and replace the one-off collectors this note calls `work/`.

Data collected 2026-11-09 11:40–13:10 (UTC+7) from public, read-only sources. No repo was cloned or run.

## Candidates
- 132 candidates across 8 categories (131 original + `dependency-check/DependencyCheck`, which replaced the archived `jeremylong/DependencyCheck` stub). Includes all 15 repos from the AI Repo Scout Notion catalogue, scored like any other.
- Picked from the plan's taxonomy (section 4b) and well-known projects, then checked against 29 awesome lists (enaqx/awesome-pentest, sbilly/awesome-security, meirwah/awesome-incident-response, devsecops/awesome-devsecops, 4ndersonLin/awesome-cloud-security, corca-ai/awesome-llm-security, ottosulin/awesome-ai-security, toniblyx/my-arsenal-of-aws-security-tools, punkpeye/awesome-mcp-servers, magnologan/awesome-k8s-security, yeyintminthuhtut/awesome-ai-offensive-security, e2b-dev/awesome-ai-agents, agarrharr/awesome-cli-apps, hesreallyhim/awesome-claude-code and others). 91 of them appear in at least one list (`awesome_lists` field in metrics). Being in a list is recorded as evidence only. It is not part of the score.

## Sources per metric
| Metric | Source |
|---|---|
| canonical name, stars, forks, archived, created, license, SECURITY.md, docs files, release count | github.com repo page (embedded JSON), following redirects |
| pushed_at, open issues, owner type | GitHub Search API (`repo:` batches, unauthenticated) |
| contributors (total) | github.com `contributors_list` fragment |
| commits 90d / 52w | github.com `graphs/commit-activity-data` |
| top-contributor share, active contributors (12 months, bots excluded, top 100 only) | github.com `graphs/contributors-data` |
| latest release | `releases.atom` |
| issue close ratio, PR merge ratio | Search API, items created 2026-08-11..2026-10-10 (oldest 100, so each had ≥30 days to resolve) |
| dependents | github.com `network/dependents` (first package only) |
| Scorecard, signed releases, contributing orgs | api.securityscorecards.dev (often months old; `scorecard_date`) |
| License for GitHub `NOASSERTION`/none | LICENSE file read by hand (`license_source`) |

## Score (0–100)
These are the plan's weights: Interest 15 (stars 8, forks 3, 90-day star growth 4), Activity 15 (commits 90d 7, release in 12 months 4, push recency 4), Contributors 15 (count 7, top share 5, orgs 3), Issue/PR 15 (first response 5, issue close ratio 5, PR merge ratio 5), Security 15 (Scorecard 9, SECURITY.md 3, signed releases 3), Dependents 10 (dependents 7, notable users 3), License/docs 10 (OSI 5, docs 5), Reputation/age 5 (org 3, age 2).
- Counts (stars, forks, commits, contributors, dependents) use `log(1+x)/log(1+max(x,T))`, where T is the category's 90th percentile (`category_p90_thresholds` in metrics).
- Top share: ≤50% → 1, ≥80% → 0, linear between. Push recency: ≤30 days → 1, falling to 0 at 365 days. Age: full points at 12 months. Docs: 1/5 each for README, CONTRIBUTING, CODE_OF_CONDUCT, homepage, releases.
- A missing metric is null, and its weight is spread over the available ones (`weight_available` per repo). It is never counted as 0. Always null in v0.1: star growth (no snapshot yet), first-response time, notable users. Often null: Scorecard (not crawled for many repos), dependents (0 or not a package).

## Gates and tiers
- Removed: 404, archived, no push in 24 months, younger than 30 days, score < 50, or out of scope (manual).
- Watchlist: score 50–69, or exceptions: no OSI license (⚠️ `non-osi` tag), age 30–90 days, anomaly flag, or Main cap.
- Main: score ≥ 70, all gates passed, age ≥ 90 days. Cap: about 15 Main per category, as the plan specifies. Overflow drops to Watchlist by score.
- Anomaly rule, which forces Watchlist with a note:
  - star velocity ≥ 1,000 stars/day since creation, or
  - ≥ 5,000 commits in 90 days and ≥ 5 commits per contributor.
  - Plus one manual flag: grok-build (~27.7k stars, only 1 visible contributor).
- There is no v0.1 size cap. `data/candidates.yml` holds only repos still waiting for data or review, and it is empty for now.

## Results (v0.1 files)
| Category | Main | Watchlist | Removed | Candidates |
|---|---|---|---|---|
| ai-coding-agents | 8 | 9 | 1 | 0 |
| llm-agent-frameworks | 13 | 2 | 2 | 0 |
| ai-security | 10 | 4 | 2 | 0 |
| offensive-security | 12 | 4 | 1 | 0 |
| defensive-security | 12 | 3 | 1 | 0 |
| cloud-kubernetes-security | 10 | 4 | 1 | 0 |
| devsecops-appsec | 15 | 1 | 1 | 0 |
| software-dev-tools | 10 | 6 | 0 | 0 |
| **Total** | **90** | **33** | **9** | **0** |

- Moved to Watchlist by the 15-Main cap: `gitleaks/gitleaks` (74.0; it is 16th in devsecops-appsec).
- Moved to Watchlist by the anomaly rule:
  - `deepseek-ai/deepseek-harness` (3,181 stars/day, 13.6k commits/90d, under 90 days old)
  - `can1357/oh-my-pi` (15.4k commits/90d)
  - `BerriAI/litellm` (17.4k commits/90d)
  - `QwenLM/qwen-code` (6.1k commits/90d)
  - `xai-org/grok-build` (manual flag)
- Removed as out of scope: `Comfy-Org/ComfyUI` (generative media).

## Known weaknesses
- Scores bunch up high (most candidates score 70–95), so the 15-Main cap does real filtering in devsecops-appsec. The candidates were already popular, and redistributing missing weight favours easy metrics. The `≥70` Main line therefore filters less than intended (see PR notes).
- Issue/PR ratios come from at most 100 items in a 2-month window, a sample rather than the full history. Repos with issues disabled or very few issues get null.
- Very high commit counts (deepseek-harness 13.6k, oh-my-pi 15.4k, litellm 17.4k in 90 days) are what GitHub reports. They likely reflect automated or agent commits.
- Contributor counts are null for `cli/cli`, `jdx/mise`, `sharkdp/bat`, `zed-industries/zed` and `tldraw/tldraw` (fragment not returned), and `BC-SECURITY/Empire` (a GitHub fork, so 0 contributors were shown). Seven repos fell back to other endpoints because their repo page returned 504 (`fallback` in metrics).
- Scorecard data can be months old, and contributing-org counts exist only when Scorecard covers the repo.
- Manual flags: CyberStrikeus/CyberStrike (topics identical to Strix). ComfyUI is removed as out of scope. tldraw stays on Watchlist (non-OSI). excalidraw and penpot removed as out of scope (drawing/design apps); tldraw kept on Watchlist as a developer SDK.
- Hand-read licenses (`license_source`) are judgement calls. Examples: impacket's modified Apache 1.1 is counted as OSI; open-core repos (litellm, OpenCTI, Tabby) are counted as OSI for their core.

## Reproduce
Collection and scoring scripts are in `work/`: `scrape.py`, `graphs.py`, `issues.py`, `meta.py`, `fallback.py`, `score.py`, `build.py`, `manual.py`. Raw data is in `work/*.jsonl`.

## AI Skills group (added 2026-11-09)

Ninth group, slug `ai-skills`, file `data/ai-skills.yml`. It is placed immediately after AI Coding Agents & Harness in `scripts/common.py`. That is the list order README generation, validation, collection, and rescoring already share. Skill packs are the rules and playbooks those coding agents load, so they sit with the agents rather than with general LLM frameworks.

54 candidates were read from the public GitHub API on 2026-11-09 with `scripts/collect.py` (GraphQL repository fields, contributors, contributor stats, community profile, OpenSSF Scorecard, deps.dev dependents, and issue/PR search). No candidate repository was cloned or executed. Stars, forks, and the other counts below are those API values. They were not estimated. Counts are log-normalized inside this group only. Missing metrics drop out of the average. The same hard gates as v0.1 were applied with `scripts/score.py`.

The group 90th percentiles were stars 103725.1, forks 11519.1, commits in 90 days 543.7, contributors 164.0, dependents 0.0. Star growth is null because the only snapshot is from the same day. OpenSSF Scorecard was missing for 53 of 54 repositories (the one score belongs to `NVIDIA/SkillSpector`, which is out of scope). Dependents were missing for 41 of 54. First-response time was missing for 18 of 54 and was scored when at least five replied issues existed. That differs from the v0.1 rows, where first response was left null.

| Result | Count |
|---|---|
| Main | 13 |
| Watchlist | 18 |
| Removed / not admitted | 23 |

Main (score at least 70, age at least 90 days, OSI license, no anomaly, under the cap of 15): `sickn33/agentic-awesome-skills` 93.0, `github/awesome-copilot` 89.1, `NVIDIA/skills` 83.5, `addyosmani/agent-skills` 81.4, `VoltAgent/awesome-agent-skills` 81.4, `alirezarezvani/claude-skills` 81.1, `wshobson/agents` 76.8, `anthropics/claude-plugins-official` 75.2, `google-gemini/gemini-skills` 73.2, `Jeffallan/claude-skills` 72.0, `getsentry/skills` 71.2, `prompt-security/clawsec` 70.6, `davepoon/buildwithclaude` 70.5.

Watchlist: `affaan-m/ECC` 89.4 and `mattpocock/skills` 75.9 (star velocity at least 1,000/day), `obra/superpowers` 69.5, `SnailSploit/Claude-Red` 68.5, `google/skills` 68.1, `microsoft/skills` 67.7, `trailofbits/skills` 66.9 (CC-BY-SA-4.0, not in the OSI set), `supabase/agent-skills` 66.1, `vercel-labs/agent-skills` 63.6 (no license file), `agentskills/agentskills` 62.4, `openai/plugins` 58.6 (no license file), `cloudflare/security-audit-skill` 56.2, `BehiSecc/awesome-claude-skills` 56.0 (no license file), `openai/skills` 54.2 (no license file; README marks it deprecated), `anthropics/skills` 54.0 (no root LICENSE; sampled skill folders are Apache-2.0), `cursor/plugins` 54.0 (no license file), `PatrickJS/awesome-cursorrules` 52.3, `UnitOneAI/SecuritySkills` 51.5.

Not admitted: seven out-of-scope repositories (installer CLI, skill scanner, GitHub Action, scientific skills, video production, prose rewriting, LLM app demos), `zero-lab-ai/skills` (28 days old, score 59.4), and 15 repositories under a score of 50. Reasons and scores are in `data/removed.yml` and `HISTORY.md`. The 15-Main cap did not move anyone; 13 projects cleared Main.

Hand-read licenses are in `data/license_overrides.yml`. A missing root LICENSE was not treated as OSI even when individual skill folders carry Apache-2.0. `VoltAgent/awesome-agent-skills` stays on Main by the rubric; its GitHub homepage field points at an unrelated marketing URL, noted on the row for Rex.

Tiers are proposals until Rex merges the pull request.

## Ghi chú cho PR
- Ngưỡng Main giữ **70** cho v0.1. Ngưỡng này sẽ được hiệu chỉnh khi đã có đủ dữ liệu tăng stars 90 ngày (cần ít nhất 2 snapshot tuần), Scorecard mới và dependents. Thay đổi ngưỡng sẽ nằm trong một PR riêng để Rex duyệt riêng, không gộp vào PR dữ liệu.
- Tầng trong file chỉ là đề xuất, có hiệu lực khi Rex merge PR.
- Các repo bị gắn cờ bất thường nằm ở Watchlist tới khi có snapshot chứng minh tăng trưởng ổn định.
