# Codex Skill Harvester

[English](README.en.md)

[![CI](https://github.com/KanadeK/codex-skill-harvester/actions/workflows/ci.yml/badge.svg)](https://github.com/KanadeK/codex-skill-harvester/actions/workflows/ci.yml)

Codex Skill Harvester 是公开工作流的**后台发现、证据、去重与维护引擎**。它增量读取可信来源，把原始发现整理成 Evidence Pack 和规范化能力，经监督式语义裁决后，维护可验证的 Codex / Open Agent Skills。

> 想直接阅读和“安装”给人类的生活技能，请去：
>
> **[Skills for Humans / 给人类的 Skill](https://github.com/KanadeK/skills-for-humans)**。

两个仓库的职责不同：

- **Skill Harvester** 负责来源、游标、证据、能力指纹、去重、候选、决策、验证和发行工程。
- **Skills for Humans** 只保存给人类直接阅读与执行的最终 SKILL.md，不携带数据库、campaign 或候选队列。

## v0.2.0 的历史位置

[v0.2.0](https://github.com/KanadeK/codex-skill-harvester/releases/tag/v0.2.0) 是已保留的历史技术原型。它证明了 204 个可执行端点、1,622 个真实查询、SQLite v4、内容评审、17 个 Skills、11 个 Plugins、双平台 CI 与不可变 Release 工程；其中生活类 Plugin 曾被错误地当作本仓库前台产品。

这段公开历史不会被删除或改写。新的产品分工是：

    codex-skill-harvester
        发现 → 证据 → 去重 → 监督裁决 → 验证 → 维护
                                      |
                                      └── 合格的人类内容进入 skills-for-humans

当前仓库中的 v0.2.0 Skills、Plugins、评测和报告继续作为技术原型、回归样本与维护证据存在，不再代表 Harvester 的前台品牌。

## 它实际做什么

### 1. Evidence / Discovery

- 固定来源注册表包含官方文档、CLI/API/OpenAPI、正式仓库、Release/Changelog、RSS/Atom、sitemap 与受控发现查询。
- 来源有信任、许可证、revision、ETag/Last-Modified、查询和游标。
- 外部内容始终是不可信数据；原始网页只进临时缓存，不执行第三方脚本，也不提交许可证不明的正文。

### 2. Capability Registry

- observation 经内容评估后才可能成为 Evidence Pack 和 normalized candidate。
- 能力指纹覆盖 goal、triggers、inputs、outputs、tools、side_effects、platforms。
- 精确散列只处理复制品；L2/L3 只负责召回，监督式 L4 决定 not_promoted、merge、update、variant 或 create。
- not_promoted 保留来源、理由和重新激活条件，不等于删除资料。

### 3. Published artifacts

- 只有独立用户目标、可信证据、原创综合、清楚触发边界、格式、E2E、安装和许可门槛都通过，才产生发布候选。
- Git 保存 Skill/Plugin、catalog、eval、紧凑报告和发行历史。
- 人类直接阅读的生活内容现在由 [Skills for Humans](https://github.com/KanadeK/skills-for-humans) 承担前台发行。

## 唯一运行态权威

运行态 observation、Evidence Pack、candidate、query/semantic batch、五队列、decision、source cursor 和 checkpoint 只有一个权威：[state/harvest.sqlite3](state/harvest.sqlite3)，SQLite schema 4。

没有 Git-JSON fallback、长期双写或多套真源。未来迁移仍采用一次写入、验证、原子替换，并明确删除旧路径。

## 本地使用

要求 Python 3.12+。

    python -m venv .venv
    .\.venv\Scripts\python -m pip install --no-build-isolation -e .
    .\.venv\Scripts\skill-harvester status --root . --json
    .\.venv\Scripts\skill-harvester review-queue --root . --json

维护与验证：

    .\.venv\Scripts\python -m unittest discover -s tests -v
    .\.venv\Scripts\python scripts/run_evals.py
    .\.venv\Scripts\python scripts/validate_repo.py
    .\.venv\Scripts\python scripts/benchmark_storage.py
    .\.venv\Scripts\python scripts/build_release.py

定时 GitHub Actions 只运行有界 campaign 并打开 review PR；它不会无人值守执行 L4 merge、发布 Skill 或创建 Release。

## 当前持久状态

- 217 个注册来源与 source states
- 1,217 observations
- 180 Evidence Packs
- 145 个已裁决 candidates
- 1,642 个 Topic Bank queries
- SQLite v4，0 个待裁决 candidate

规模数字是观测结果，不是制造 Skill 的 KPI。完整历史、campaign 数字、迁移和验证证据见 [工程状态](docs/engineering-status.md)。

## 安全和范围

- 不运行下载的第三方脚本，不保存密钥，不把社区讨论当操作权威。
- 医疗、法律、金融、凭据密集、高权限和现实控制能力只积累证据，禁止自动发布。
- 不以空队列冒充长期 campaign 完成；no-op 只表示同一组输入没有新增、变化或未完成工作。
- [RepoPilot Skillforge](https://github.com/KanadeK/repopilot-skillforge) 扫描单个代码仓库并生成仓库级指导；Harvester 维护跨来源能力生态，两者不重复。

## 文档

- [规格](docs/spec.md)
- [架构](docs/architecture.md)
- [计划采用审计](docs/plan-adoption-audit.md)
- [分类法](docs/taxonomy.md)
- [Schema migrations](docs/schema-migrations.md)
- [工程状态](docs/engineering-status.md)
- [贡献指南](CONTRIBUTING.md)
- [安全政策](SECURITY.md)

Skill 格式只依赖 OpenAI 官方 [Skills 文档](https://developers.openai.com/codex/skills)；外部来源只提供事实和发现信号。

## License

[MIT](LICENSE)
