# Skill 目录 · Skill Catalog

[中文首页](README.md) · [English README](README.en.md)

本目录列出 v0.2.0 正式发布版本中的全部 17 个稳定能力。面向用户的名称可以演进，但能力 ID、触发边界和合并历史由能力目录持续维护。所有生活类 Skill 都是交互式指导：人负责观察、判断现场条件并完成物理动作。

## 买菜与食品采购 · Grocery Shopping

### 规划一次买菜 · Plan a Fresh-Market Trip

- 能力 ID：daily-life.fresh-market-shopping-plan
- Plugin：fresh-market-and-grocery-shopping
- 发布状态：v0.2.0 published
- 适合：根据人数、餐数、预算、已有食物、储存空间和路程，生成有份量边界的采购清单与路线。
- 示例提问：“两个人吃三天，冰箱还有鸡蛋，帮我列一份 150 元以内的买菜清单。”
- 安全边界：不替用户下单，不预测实时价格，不提供医疗营养治疗；过敏与特殊饮食必须由用户明确确认。

### 挑选新鲜易腐食材 · Choose Fresh Perishables

- 能力 ID：daily-life.choose-fresh-perishables
- Plugin：fresh-market-and-grocery-shopping
- 发布状态：v0.2.0 published
- 适合：在购买蔬果、蛋、肉或海鲜时，依据可观察的拒收线索、包装温度、用途和运输时间协助比较。
- 示例提问：“这几盒鸡蛋和两条鱼该怎么挑？我还要坐一小时车回家。”
- 安全边界：外观与气味不能证明安全；不诊断食源性疾病，冷链失控或情况不明时给出停止购买/食用条件。

### 买回家后的收纳与先吃顺序 · Put Away Groceries

- 能力 ID：daily-life.put-away-groceries
- Plugin：fresh-market-and-grocery-shopping
- 发布状态：v0.2.0 published
- 适合：根据标签、开封状态、易腐性、计划餐食和冰箱空间安排冷藏、冷冻、常温与先吃顺序。
- 示例提问：“菜、肉、鸡蛋和面包刚买回来，分别放哪儿？这周先吃什么？”
- 安全边界：不凭气味把可疑食物判为安全；标签温度、离开冷藏时间或污染情况未知时会要求补充信息。

## 洗衣与衣物护理 · Laundry Care

### 读标签并分桶 · Sort a Laundry Load

- 能力 ID：daily-life.sort-laundry-load
- Plugin：laundry-and-clothing-care
- 发布状态：v0.2.0 published
- 适合：按洗护符号、温度上限、程序强度、漂白/烘干限制、颜色、面料和污渍风险拆分衣物。
- 示例提问：“白 T 恤、深色牛仔裤、运动服和这件标牌衣服应该分几桶洗？”
- 安全边界：看不清标签时不猜；不处理危险化学品、严重生物污染或专业干洗替代。

### 为这桶衣服选择洗衣机设置 · Choose Washer Settings

- 能力 ID：daily-life.choose-washer-settings
- Plugin：laundry-and-clothing-care
- 发布状态：v0.2.0 published
- 适合：在衣物已经分桶后，结合准确洗衣机说明书选择程序、温度、脱水、装载量、洗涤剂剂量和晾晒交接。
- 示例提问：“这桶衣服怎么洗？这是洗衣机型号和面板，程序、温度、转速、洗衣液选多少？”
- 安全边界：不猜机型按钮含义，不维修电器，不建议混用漂白剂、酸或氨类产品。

### 羊毛针织物洗护 · Wash Wool Knitwear

- 能力 ID：daily-life.wash-wool-knitwear
- Plugin：laundry-and-clothing-care
- 发布状态：v0.2.0 published
- 适合：根据标签和设备判断机洗、手洗、平铺晾干、整形或送专业护理。
- 示例提问：“这件羊毛衫怎么洗和晾才不容易缩水变形？标签上写着这些符号。”
- 安全边界：不用于皮革、皮草和结构复杂的西装；不承诺逆转已经发生的缩水或毡化。

## 家庭做饭与备餐 · Home Cooking

### 安排一顿饭与备菜顺序 · Plan a Home Meal

- 能力 ID：daily-life.plan-home-meal
- Plugin：home-cooking-and-meal-preparation
- 发布状态：v0.2.0 published
- 适合：结合人数、时间、现有食材、厨具、普通偏好和食品安全限制，确定菜品、缺料和并行时间线。
- 示例提问：“三个人 45 分钟后吃饭，用现有鸡腿、土豆和青椒安排晚饭，告诉我先做什么。”
- 安全边界：不制定医疗饮食，不替代过敏专业建议；用刀、热油、明火等步骤由人保持现场控制。

### 按功能替代缺少的食材 · Substitute an Ingredient by Function

- 能力 ID：daily-life.substitute-ingredient-by-function
- Plugin：home-cooking-and-meal-preparation
- 发布状态：v0.2.0 published
- 适合：先判断缺少食材承担的增稠、黏合、膨松、酸度、甜度、水分、质地或风味作用，再给兼容替代与连带调整。
- 示例提问：“这道菜缺玉米淀粉，按它在配方里的作用能用什么替代、用多少？”
- 安全边界：不为过敏、婴幼儿食品、罐藏、发酵等安全关键配方即兴替代。

### 检查熟度与剩菜处理 · Check Doneness and Leftovers

- 能力 ID：daily-life.check-doneness-leftovers
- Plugin：home-cooking-and-meal-preparation
- 发布状态：v0.2.0 published
- 适合：根据食物种类、厚度、烹饪方法、温度计读数、离开控温时间和设备，给出继续加热、食用、保温、冷却、储存、复热或丢弃条件。
- 示例提问：“这块鸡肉熟了吗？吃不完的部分怎么冷却、冷藏和明天再热？”
- 安全边界：不诊断食源性疾病，不凭颜色、气味或单一线索宣称食物安全。

## 软件发布与工程 · Software Delivery and Engineering

### 审计 GitHub Release 完整性 · Audit a GitHub Release

- 能力 ID：github-release-evidence:audit-github-release
- Plugin：github-release-evidence
- 发布状态：v0.1.0 introduced；v0.2.0 updated catalog
- 适合：为一个已经发布的 Release 核对公开仓库、合并 PR/CI、tag 对齐、Release 状态、预期资产、隔离安装/调用和贡献者证据。
- 示例提问：“这个 GitHub Release 真的发布完整了吗？请按 tag、PR、CI、资产和安装证据逐项审计。”
- 安全边界：只读审计，不修 CI、不合并、不发版；未提供或不可观察的证据会标为未验证。

### Python 包发布就绪审计 · Audit Python Release Readiness

- 能力 ID：software.python-release-readiness
- Plugin：python-package-delivery
- 发布状态：v0.2.0 published
- 适合：发布前检查 sdist、wheel、元数据、RECORD、平台覆盖，以及 GitHub Actions PyPI publishing job 的 Trusted Publishing 权限边界。
- 示例提问：“请检查 dist 里的 wheel、sdist 和发布 workflow，告诉我这个 Python 包是否可以发 PyPI。”
- 安全边界：不上传、不发布、不安装网络依赖；归档读取有成员数和字节上限，不执行第三方代码。

### npm 包发布就绪审计 · Audit npm Package Readiness

- 能力 ID：software.npm-package-readiness
- Plugin：javascript-package-delivery
- 发布状态：v0.2.0 published
- 适合：检查 npm pack 实际内容、package.json 入口、类型声明、敏感文件与生命周期脚本边界。
- 示例提问：“这个 Node 包 npm pack 后会包含什么？类型声明和发布配置准备好了吗？”
- 安全边界：不安装依赖、不运行 lifecycle scripts、不访问 registry、不执行 npm publish。

### 创建离线 Git 传输包 · Create a Git Transfer Bundle

- 能力 ID：software.git-offline-transfer
- Plugin：git-offline-transfer
- 发布状态：v0.2.0 published
- 适合：把已经提交的 refs 打成 Git bundle，验证 bundle 并给出离线接收端恢复步骤。
- 示例提问：“这台电脑不能联网，帮我把仓库已提交历史做成可验证的 Git bundle 带到另一台电脑。”
- 安全边界：不包含未提交或未跟踪文件，也不包含 Git LFS 对象；不推送、不抓取、不切换工作树。

### 规划 Ansible Collection 验证 · Validate an Ansible Collection

- 能力 ID：software.ansible-collection-validation
- Plugin：ansible-collection-quality
- 发布状态：v0.2.0 published
- 适合：从 collection 布局和测试目录规划 sanity、unit、integration 与 ansible-core 矩阵验证。
- 示例提问：“这个 Ansible collection 改动在 review 前应该跑哪些 ansible-test 层和版本矩阵？”
- 安全边界：确定性脚本只读结构；不安装依赖、不启动容器、不连接或改变托管主机、不发布 Galaxy。

### 测量 Cargo 构建性能 · Measure Cargo Build Performance

- 能力 ID：software.cargo-build-performance
- Plugin：rust-build-performance
- 发布状态：v0.2.0 published
- 适合：在隔离 target 目录中建立可复现的冷构建和热构建基线，并比较有界的配置变更。
- 示例提问：“这个 Rust workspace 为什么编译慢？请分别测冷、热构建并找出值得验证的改进。”
- 安全边界：不做运行时性能分析、不升级依赖、不发布 crate，也不对用户未授权的项目运行构建。

### 诊断浏览器 CORS/Fetch 失败 · Diagnose a CORS Request

- 能力 ID：software.cors-request-diagnosis
- Plugin：web-request-diagnostics
- 发布状态：v0.2.0 published
- 适合：从已捕获的请求、响应、Origin、凭据模式和 OPTIONS 预检证据区分网络、HTTP、预检与浏览器暴露问题。
- 示例提问：“浏览器报 CORS blocked，这是请求、预检和响应头，究竟缺了什么？”
- 安全边界：不关闭浏览器安全、不搭绕过代理、不自动修改生产响应头、不自动发真实请求。

### 发送前审计 curl 请求 · Audit a curl Request

- 能力 ID：software.curl-request-audit
- Plugin：api-request-safety
- 发布状态：v0.2.0 published
- 适合：在执行前检查 curl 的方法与 body 语义、默认配置、本地文件引用、凭据选项和输出风险。
- 示例提问：“先别发送，帮我审计这条 curl 命令会读取什么文件、带什么凭据、实际使用什么方法。”
- 安全边界：不执行或重放请求，不处理真实凭据，不绕过 TLS，也不用于浏览器 CORS 诊断。

## 发布门槛

“published”表示该能力已包含在不可变 [v0.2.0 Release](https://github.com/KanadeK/codex-skill-harvester/releases/tag/v0.2.0) 中。main CI、注释 tag、13 个签名资产、校验和、远端下载、隔离安装/调用与 live Release Skill 审计均已通过。
