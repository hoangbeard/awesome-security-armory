# Scoring notes — v0.1 candidate data (2026-11-09, Asia/Saigon UTC+7)

> The committed lists are the authority: 89 Main, 32 Watchlist, 11 removed. The table further down was the count before penpot and excalidraw were removed as out of scope (that table says 90 / 33 / 9). Production scripts live in `scripts/` and replace the one-off collectors this note calls `work/`.

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

## Ghi chú cho PR
- Ngưỡng Main giữ **70** cho v0.1. Ngưỡng này sẽ được hiệu chỉnh khi đã có đủ dữ liệu tăng stars 90 ngày (cần ít nhất 2 snapshot tuần), Scorecard mới và dependents. Thay đổi ngưỡng sẽ nằm trong một PR riêng để Rex duyệt riêng, không gộp vào PR dữ liệu.
- Tầng trong file chỉ là đề xuất, có hiệu lực khi Rex merge PR.
- Các repo bị gắn cờ bất thường nằm ở Watchlist tới khi có snapshot chứng minh tăng trưởng ổn định.
