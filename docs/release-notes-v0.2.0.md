# 会过日子 · Human Skills v0.2.0

[English](#english)

v0.2.0 把 Codex Skill Harvester 从“工程管线样例”变成可以直接理解和安装的双语 Skill 产品，同时保留完整、可恢复的证据生产线。

## 给使用者

- 新增 3 个生活任务域 Plugin、9 个中英双语 Daily Life Skills：买菜与食品采购、洗衣与衣物护理、家庭做饭与备餐。
- 软件能力扩展为 8 个 Skills：GitHub Release 审计、Python/npm 发布准备、Git 离线传递、Ansible collection 验证、Cargo 构建性能、CORS 诊断和 curl 请求审计。
- 新增中英双语首页和完整 [Skill 目录](../SKILLS.md)，每个能力都写明自然提问、适用范围、发布状态和安全边界。
- 用户按任务安装小 Plugin，无需安装整个证据库或全部能力。

## 可信生产线

- 一次真实完整 campaign 覆盖 204 个可执行端点和 1,622 个唯一查询；Daily Life pilot 进一步验证中文/英文生活资料、三种交互模式与 63 个场景。
- 运行态升级为唯一权威 SQLite v4，分别保存 observation、Evidence Pack、candidate、query/semantic batch、五队列、decision 和 checkpoint；没有长期双写或 fallback。
- workflow_signal 不再决定候选准入。Codex 读取真实 Evidence Pack，执行 L4 not_promoted/merge/update/variant/create 判断和原创综合。
- 相同查询、语义批次与稳定来源重放均证明 no-op；中断和 stop-loss 留下可恢复 checkpoint。

## 修复与安全

- 父 campaign 只在显式 objective 达成或总控结束时完成；批次 pending=0 不再冒充长期 campaign completed。
- Python Release Readiness 只接受 publishing job 自身 permissions.id-token: write，顶层、env、step、注释或其他 job 的同名文本均不能误通过。
- 对不可信 wheel/sdist 元数据、RECORD 与归档成员检查增加可测试资源上限，超限快速失败且不解压、执行第三方代码。
- 医疗、法律、金融、凭据密集和现实控制域继续禁止自动发布。

## 资产

Release 提供一个源码归档、11 个独立 Plugin 归档和 SHA256SUMS。发布门槛要求 Ubuntu/Windows CI、确定性双构建、官方 Skill/Plugin 格式验证、完整测试/evals/validator、隔离安装/调用、远端资产回读和贡献者核验全部通过。

---

<a id="english"></a>

# Human Skills · 会过日子 v0.2.0

v0.2.0 turns Codex Skill Harvester from an engineering pipeline demonstration into a bilingual, installable Skill product while preserving its resumable evidence-production system.

## For users

- Adds 3 everyday-life Plugins with 9 bilingual Skills for grocery shopping, laundry care, and home cooking.
- Expands the software catalog to 8 Skills covering GitHub Release audits, Python/npm publication readiness, offline Git transfer, Ansible collection validation, Cargo build performance, CORS diagnosis, and curl request review.
- Adds bilingual storefronts and a complete [Skill Catalog](../SKILLS.md) with natural prompts, scope, release state, and safety boundaries.
- Users install small task-focused Plugins rather than the evidence corpus or the whole catalog.

## Trustworthy production

- One real campaign exercised 204 executable endpoints and 1,622 unique queries; the Daily Life pilot added bilingual official evidence, three interaction modes, and 63 resolved scenarios.
- SQLite v4 is the sole runtime authority for observations, Evidence Packs, candidates, query/semantic batches, five queues, decisions, and checkpoints. There is no long-lived dual write or fallback.
- A manually seeded workflow_signal no longer controls promotion. Codex reads real Evidence Packs, performs supervised L4 adjudication, and writes original synthesis.
- Stable query, semantic, and source replays prove truthful no-op behavior; interruptions and stop-losses preserve resumable checkpoints.

## Fixes and safety

- A parent campaign completes only when its explicit objective is met or the controller ends it; an empty batch no longer impersonates campaign completion.
- Python Release Readiness accepts OIDC only from permissions.id-token: write on the publishing job itself.
- Untrusted wheel/sdist archive and metadata checks now enforce testable member and byte limits without extracting or executing third-party code.
- Medical, legal, financial, credential-heavy, and real-world-control domains remain blocked from automatic publication.

## Assets

The Release contains one source archive, 11 individual Plugin archives, and SHA256SUMS. Publication requires green Ubuntu/Windows CI, two deterministic builds, official Skill/Plugin format checks, the full test/eval/validator suite, isolated install/invocation, remote asset readback, and contributor verification.
