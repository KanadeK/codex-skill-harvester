# Human Skills · 会过日子

[简体中文](README.md)

[![CI](https://github.com/KanadeK/codex-skill-harvester/actions/workflows/ci.yml/badge.svg)](https://github.com/KanadeK/codex-skill-harvester/actions/workflows/ci.yml)

> AI has no hands, but it can help you make everyday work make sense.

Human Skills is a bilingual set of Codex Skills that turns “how do I do this?” into bounded, interactive, executable guidance. It covers groceries, laundry, and home cooking alongside software release checks, web-request diagnosis, and offline Git delivery.

Behind the catalog, Skill Harvester incrementally discovers public, traceable workflow evidence. A capability is published only after evidence review, deduplication, supervised semantic adjudication, trigger evaluation, and end-to-end validation. This is not a bulk Skill mirror, and a page title never becomes a Skill by itself.

## Ask it like this

- “Plan groceries for two people for three days. I already have eggs and half a cabbage, and my budget is about ¥150.”
- “I have white T-shirts, dark jeans, and a wool sweater. Which loads should I make, and how should I wash them?”
- “I have chicken thighs, potatoes, peppers, and one wok. Plan dinner and tell me what to prep first.”
- “Are this Python wheel and its GitHub Actions publishing workflow actually ready for PyPI?”
- “The browser says CORS blocked. I captured the preflight and response headers—where is the failure?”

Each Skill asks for facts that materially change the answer, then gives steps, stop conditions, and explicit uncertainties. AI has no hands: it does not pretend to read a missing label, smell food, press an appliance button, or publish software.

## What is included

The v0.2.0 candidate catalog contains 17 Skills distributed as 11 small Plugins organized by installation intent.

| Everyday-life Plugin | Scope |
| --- | --- |
| Grocery Shopping | Plan a bounded shop, inspect perishables using observable clues, and put food away in a use-first order |
| Laundry Care | Read care labels, sort loads, select settings for the exact washer, and care for wool knitwear |
| Home Cooking | Sequence one meal, substitute ingredients by function, and check doneness and leftovers |

| Software Plugin | Scope |
| --- | --- |
| GitHub Release Evidence | Audit whether an already-published GitHub Release is genuinely complete |
| Python Package Delivery | Inspect sdist, wheel, metadata, and Trusted Publishing readiness |
| JavaScript Package Delivery | Inspect npm package contents and publication boundaries |
| Git Offline Transfer | Create and verify a Git bundle for committed history |
| Ansible Collection Quality | Plan the appropriate ansible-test validation layers |
| Rust Build Performance | Reproduce and compare cold and warm Cargo builds |
| Web Request Diagnostics | Locate CORS and Fetch failures from captured evidence |
| API Request Safety | Audit curl semantics, local-file references, and credential risks before execution |

See the bilingual [Skill Catalog](SKILLS.md) for every stable capability ID, example prompt, release state, and safety boundary.

## Install

After v0.2.0 is published, add the repository marketplace:

    codex plugin marketplace add KanadeK/codex-skill-harvester --ref v0.2.0

Then open the Plugins Directory in Codex or Work mode and install only the Plugin that matches your task. You do not need all 11.

Until that Release exists, use the version actually listed on [GitHub Releases](https://github.com/KanadeK/codex-skill-harvester/releases). The current public stable version remains [v0.1.1](https://github.com/KanadeK/codex-skill-harvester/releases/tag/v0.1.1).

## Safety boundaries

- Everyday-life Skills provide interactive guidance; a person reads labels, operates tools, and confirms results.
- Food guidance never declares questionable food safe from smell or appearance alone, and stops on medical diets, allergy-critical substitutions, infant food, canning, fermentation, or similar high-risk boundaries.
- Laundry guidance never guesses unreadable symbols or controls, recommends dangerous chemical mixing, or repairs appliances.
- Software scripts inspect explicitly supplied local material. They do not execute downloaded third-party scripts, publish, push, or bypass controls.
- Medical, legal, financial, credential-heavy, and real-world-control capabilities remain evidence-only and cannot be auto-published.

## Why this is more than a prompt collection

- Every capability has a stable ID, seven-field fingerprint, revisioned sources, an Evidence Pack, and an auditable decision.
- Exact hashes remove copies; near-duplicate decisions compare user goals, inputs, outputs, tools, side effects, and platforms.
- A new or updated Skill must pass format, positive trigger, negative trigger, end-to-end, isolated install/invocation, originality, and license gates.
- One SQLite store owns runtime observations, candidates, queues, decisions, and cursors. Git owns reviewable Skills, catalogs, evals, and release history.
- A repeated run handles only changed, new, or unfinished work and truthfully reports a no-op when nothing changed.

## Maintainer entry points

The public README stays intentionally compact. Architecture, measured campaign results, migrations, verification commands, and historical evidence live in [Engineering Status](docs/engineering-status.md). See [CONTRIBUTING.md](CONTRIBUTING.md) for contributions and [SECURITY.md](SECURITY.md) for security reports.

Skill and Plugin format claims rely only on OpenAI's official [Skills documentation](https://developers.openai.com/codex/skills) and [Plugins documentation](https://developers.openai.com/plugins/build/plugins). All external content is treated as untrusted evidence.

## License

[MIT](LICENSE)
