---
name: sql-governance
description: Detect and review SQL-related design, code, migrations, schema changes, CodeCheck, commits, and PRs against the shared SQL rule catalog. Use whenever work contains SQL, database access, DDL/DML, migrations, tables, columns, indexes, constraints, partitions, views, procedures, or triggers; structural and bulk-data changes require explicit developer confirmation.
metadata:
  short-description: SQL 规范检视与门禁
---

# SQL Governance

把本仓库视为 SQL 规则唯一事实来源。不要在消费方仓库复制或改写规则；消费方通过 git submodule 锁定本仓库 commit。

## 先判断是否触发

出现下列任一内容即触发：

- 方案、代码或分析涉及 SQL、数据库访问、DDL、DML、迁移、存储过程、视图或触发器；
- 变更包含 `.sql`、迁移目录、ORM schema/model、原生 SQL、数据库初始化或数据订正；
- 用户要求代码检视、CodeCheck、提交、创建/更新 PR 或门禁检查，且差异涉及上述内容。

没有 SQL 行为时，说明“未触发 SQL 规范”后继续原任务，不制造无关意见。

## 加载规则

1. 读取 [rules/catalog.json](rules/catalog.json)，以其中规则为判定依据。
2. 需要解释层级、自动化能力或例外时，读取 [references/severity-model.md](references/severity-model.md)。
3. 只加载与本次 SQL 对象和阶段相关的规则；不要因未检查无关领域而声称全量合规。
4. `check.kind=static` 的规则可自动判定；`manual` 必须收集证据；`hybrid` 先做静态筛查，再确认上下文。

## 场景一：方案生成、编码与方案分析

1. 识别 SQL 对象、数据库方言、运行环境、数据规模与变更类型。
2. 在生成或修改内容前，筛查是否属于结构性或高风险数据变更：建表；字段、索引、触发器、约束、外键的增删改；分区策略；大批量数据变更/订正；规则标记的人工确认项。
3. 命中时，使用 [templates/developer-confirmation.md](templates/developer-confirmation.md) 列明变更、影响范围、风险、回滚/备份方案和合规结论，然后停止相关 SQL 的生成、写入或执行。必须获得“确认 / 拒绝 / 修改方案”之一的明确答复；沉默、模糊答复和历史上对不同方案的确认均不算通过。
4. 确认后仅在已确认范围内继续；范围、对象、风险或实施方式变化时重新确认。
5. 按 Block、Warn、Info 输出方案期意见，使用 [templates/design-review.md](templates/design-review.md)。Block 未清零不得宣告方案合规。

开发者确认不是对规则违规的豁免。确认后仍须修复 Block；只有规则自身声明的例外且证据充分时，才可记录 `exception`。

## 场景二：检视、CodeCheck、提交与 PR 门禁

1. 以目标分支为基线获取完整差异；检查 SQL 文件、迁移、ORM/schema 及应用内嵌 SQL。
2. 对命中规则逐条记录文件、1-based 行号、最小片段、规则 ID、原文条款、层级、判定证据和整改建议。
3. 使用 [templates/gate-report.md](templates/gate-report.md) 输出报告：
   - `prohibition` 或 `mandatory` 违规 => `Block`，退出/门禁状态为失败；
   - `recommendation` => `Warn`；`reference` => `Info`；
   - 无法静态判定但要求人工确认 => `Block: confirmation-required`，直到提供准确确认记录；
   - 已有明确、匹配当前方案的确认记录 => 记录证据，但仍独立检查规则合规性。
4. 不得用“未发现”代替“已检查”。报告必须列出检查范围、未检查项与限制。

若任务仅要求审查，不得替用户修改代码、执行 SQL 或代替开发者确认；只报告问题和门禁结论。

## 判定与输出约束

- 同一根因只报一个主问题，可关联多个规则，避免重复噪声。
- 静态规则必须给出可复现证据；人工规则必须给出待确认问题和所需材料。
- Block 报告必须包含可执行的最小整改路径。
- 例外必须记录批准人/角色、范围、理由、有效期和证据链接；没有这些字段视为未批准。
- 不执行生产 SQL，不把生成 SQL 等同于获准执行，不泄露连接串、凭据或敏感数据。

## 维护与发布

维护规则或发布版本时读取 [references/submodule-integration.md](references/submodule-integration.md) 和 [rules/README.md](rules/README.md)。规则变更必须通过 PR，更新 `CHANGELOG.md`，按语义化版本打 tag；消费方只通过显式 submodule commit 升级。
