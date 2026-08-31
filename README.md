# 会过日子 · Human Skills

[English](README.en.md)

[![CI](https://github.com/KanadeK/codex-skill-harvester/actions/workflows/ci.yml/badge.svg)](https://github.com/KanadeK/codex-skill-harvester/actions/workflows/ci.yml)

> AI 没长手，但可以教你把日子过明白。

这是一套给 Codex 用的中英双语 Skills：把“我该怎么做”变成有边界、可追问、能执行的步骤。它既能陪你买菜、洗衣、做饭，也能检查软件发布、排查网页请求和准备离线 Git 交付。

仓库背后的 Skill Harvester 会从公开且可追溯的资料中增量发现工作流，经证据整理、能力去重、人工监督的语义判断、触发测试和端到端验证后，才把合格能力发布成小而清楚的 Plugin。它不是海量 Skill 搬运站，也不会把网页标题直接包装成 Skill。

## 你可以直接这样问

- “两个人吃三天，冰箱还剩鸡蛋和半颗白菜，帮我买三天菜，控制在 150 元左右。”
- “我有白 T 恤、深色牛仔裤和一件羊毛衫，这桶衣服怎么洗？哪些要分开？”
- “家里有鸡腿、土豆、青椒和一口炒锅，用现有食材安排晚饭，告诉我先做什么。”
- “这个 Python wheel 和 GitHub Actions 发布流程，真的已经可以发 PyPI 了吗？”
- “浏览器说 CORS blocked，我抓到预检请求和响应头了，问题在哪一层？”

Skill 会先补齐真正影响结果的信息，再给出步骤、停止条件和需要你确认的地方。它不会替你完成物理动作，也不会假装已经看见标签、闻到食物、按过洗衣机按钮或发布过软件。

## 当前收录

v0.2.0 候选目录包含 17 个 Skills，按 11 个安装意图明确的 Plugins 分发。

| 生活 Plugin | 能做什么 |
| --- | --- |
| 买菜与食品采购 · Grocery Shopping | 按人数、预算、库存规划采购；用可观察线索挑选易腐食材；回家后安排冷藏、冷冻和先吃顺序 |
| 洗衣与衣物护理 · Laundry Care | 读洗护标签、分桶、按准确机型选择程序和用量、护理羊毛针织物 |
| 家庭做饭与备餐 · Home Cooking | 安排一顿饭的备菜时间线、按功能替代缺少的食材、检查熟度与剩菜处理 |

| 软件 Plugin | 能做什么 |
| --- | --- |
| GitHub Release Evidence | 审计一个已经发布的 GitHub Release 是否真的完整 |
| Python Package Delivery | 发布前检查 sdist、wheel、元数据和 PyPI Trusted Publishing 工作流 |
| JavaScript Package Delivery | 检查 npm pack 内容、声明文件、生命周期脚本边界和发布配置 |
| Git Offline Transfer | 创建并验证用于离线传递已提交历史的 Git bundle |
| Ansible Collection Quality | 为 collection 选择并规划正确的 ansible-test 验证层 |
| Rust Build Performance | 用隔离 target 目录复现并比较 Cargo 冷、热构建 |
| Web Request Diagnostics | 从浏览器请求、响应和预检证据定位 CORS/Fetch 失败 |
| API Request Safety | 在发送前审计 curl 方法、请求体、本地文件和凭据风险 |

逐个 Skill 的触发方式、示例问题、发布状态与安全边界见 [Skill 目录](SKILLS.md)。

## 安装

v0.2.0 正式发布后，可从仓库 Marketplace 安装：

    codex plugin marketplace add KanadeK/codex-skill-harvester --ref v0.2.0

然后在 Codex 或 Work mode 的 Plugins Directory 中，按任务选择一个 Plugin 安装。无需一次安装全部 11 个。

发布前，请以 [GitHub Releases](https://github.com/KanadeK/codex-skill-harvester/releases) 中实际存在的版本为准；当前公开稳定版仍是 [v0.1.1](https://github.com/KanadeK/codex-skill-harvester/releases/tag/v0.1.1)。

## 安全边界

- 生活类 Skills 只提供交互式指导，由人读取标签、操作器具并确认结果。
- 食品安全不会仅凭气味或外观宣称“可以吃”；过敏、婴幼儿食品、罐藏与发酵等高风险场景会停止或转交权威建议。
- 洗衣不会猜模糊标签、机型按钮或鼓励危险化学品混用，也不承担电器维修。
- 软件类脚本默认只检查本地、明确提供的材料；不会执行下载来的第三方脚本，不会替用户发布、推送或绕过安全控制。
- 医疗、法律、金融、凭据密集和现实控制能力目前只积累证据，不自动发布。

## 为什么不是“又一堆提示词”

- 每个能力都有稳定 ID、七字段能力指纹、来源 revision、Evidence Pack 和可审计决策。
- 精确散列只去掉复制品；真正的近重复以用户目标、输入输出、工具、副作用和平台边界判断。
- 新建或更新 Skill 必须通过格式、正向触发、负向误触发、端到端任务、隔离安装/调用、原创性与许可检查。
- 运行态 observation、candidate、queue、decision 和 cursor 由一个 SQLite 权威存储管理；Git 保存可审查的 Skills、清单、评测与发布历史。
- 相同输入重跑只处理新增、变化或未完成批次；无变化会如实 no-op。

## 维护者入口

公开产品页有意保持简洁。架构、真实 campaign 数字、迁移记录、验证命令与历史证据见 [工程状态](docs/engineering-status.md)；贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全问题见 [SECURITY.md](SECURITY.md)。

项目规范只依赖 OpenAI 官方的 [Skills 文档](https://developers.openai.com/codex/skills) 与 [Plugins 文档](https://developers.openai.com/plugins/build/plugins)。外部内容一律作为不可信证据处理。

## License

[MIT](LICENSE)
