---
name: sql-governance
description: Detect and review MySQL or PostgreSQL design, code, migrations, schema changes, CodeCheck, commits, and PRs against shared portable rules plus dialect-specific rules. Use whenever work contains SQL, database access, DDL/DML, migrations, tables, columns, indexes, constraints, partitions, views, procedures, or triggers; structural and bulk-data changes require explicit developer confirmation.
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

## 先识别数据库方言

1. 优先读取项目配置、连接驱动、迁移工具和已有 DDL 中的明确证据，确定每个文件是 `mysql` 还是 `postgresql`。
2. MySQL 线索包括反引号标识符、表选项和列定义中的 `AUTO_INCREMENT` 或 `UNSIGNED`。PostgreSQL 线索包括 `::type` 转型、列定义中的 `jsonb` 或 `serial` 类型，以及 `CREATE INDEX CONCURRENTLY`。按语法位置判断，项目明确配置优先。
3. 方言不明确时只应用公共规则，并以 `Block: dialect-required` 停止方言合规结论，要求开发者明确选择 MySQL 或 PostgreSQL。不得默认按 MySQL，也不得把两种方言规则同时套到同一文件。
4. 一个变更同时包含两种方言时，按文件分别检查并在报告中分别汇总。

## 加载规则

1. 读取 [rules/catalog.json](rules/catalog.json)，严格按 `load_order` 加载：
   - MySQL：`rules/common.json` + `rules/mysql.json`；
   - PostgreSQL：`rules/common.json` + `rules/postgresql.json`。
2. 禁止对 PostgreSQL 应用 MySQL 的 `utf8mb4`、InnoDB、前缀索引或 `BINARY(16)` 要求；禁止对 MySQL 应用 PostgreSQL 的 `uuid`、`CONCURRENTLY`、GIN/GiST、父子分区索引要求。PostgreSQL 检视发现疑似混入的 MySQL 表语法时，按 `POSTGRESQL-TAB-001` 提示 Warn，并复核目标数据库兼容性。按 `POSTGRESQL-PK-001` 判定自增违规时，先确认该列实际参与主键，再检查其 `serial` 系列类型或 `IDENTITY` 属性。
3. 需要解释层级、自动化能力或例外时，读取 [references/severity-model.md](references/severity-model.md)。
4. 规则涉及语法、类型、标识符、注释、DML/DDL、事务、锁、索引或分区事实时，读取 [references/dialect-spec-sources.md](references/dialect-spec-sources.md)，并以其中对应版本的官方文档为准；项目策略可以更严格，但不得把“项目禁止”写成“数据库不支持”。
5. 需要判断某个源条款为何保留 common 或拆分时，读取 [references/dialect-isolation-audit.md](references/dialect-isolation-audit.md)。不得把已拆分条款的另一方言规则作为补充规则加载。
6. 只加载与本次 SQL 对象和阶段相关的规则；不要因未检查无关领域而声称全量合规。
7. `check.kind=static` 表示本仓库 `sql_guard.py` 已实现高置信自动判定；`manual` 必须收集证据；`hybrid` 先做静态筛查，再确认上下文。具体自动覆盖 ID 以 [rules/README.md](rules/README.md) 为准。
8. 对 SQL 文件运行 `python3 scripts/sql_guard.py --dialect <mysql|postgresql> <files...>`。退出码 `1` 为已实现规则命中 Block，`2` 为输入或方言错误；`--format json` 的 `checked_rules` 列出静态规则，`screened_rules` 列出带自动分支的混合规则。根据数据模型、运行配置和适用的审批记录复核 Warn，并在确认违规后按规则层级定级。

## 场景一：方案生成、编码与方案分析

1. 识别 SQL 对象、数据库方言和版本、运行环境、数据规模与变更类型。
2. 在生成或修改内容前，筛查是否属于结构性或高风险数据变更：建表；字段、索引、触发器、约束、外键的增删改；分区策略；大批量数据变更/订正；规则标记的人工确认项。
3. 命中时，使用 [templates/developer-confirmation.md](templates/developer-confirmation.md) 列明变更、影响范围、风险、回滚/备份方案和合规结论，然后停止相关 SQL 的生成、写入或执行。必须获得“确认 / 拒绝 / 修改方案”之一的明确答复；沉默、模糊答复和历史上对不同方案的确认均不算通过。
4. 确认后仅在已确认范围内继续；范围、对象、风险或实施方式变化时重新确认。
5. 按 Block、Warn、Info 输出方案期意见，使用 [templates/design-review.md](templates/design-review.md)。Block 未清零不得宣告方案合规。

开发者确认不是对规则违规的豁免。确认后仍须修复 Block；只有规则自身声明的例外且证据充分时，才可记录 `exception`。

## 场景二：检视、CodeCheck、提交与 PR 门禁

1. 以目标分支为基线获取完整差异；检查 SQL 文件、迁移、ORM/schema 及应用内嵌 SQL，并为每个入口记录方言证据。
2. 对命中规则逐条记录文件、1-based 行号、最小片段、规则 ID、原文条款、层级、判定证据和整改建议。
3. 使用 [templates/gate-report.md](templates/gate-report.md) 输出报告：
   - `prohibition` 或 `mandatory` 违规 => `Block`，退出/门禁状态为失败；
   - `recommendation` => `Warn`；`reference` => `Info`；
   - 无法静态判定但要求人工确认 => `Block: confirmation-required`，直到提供准确确认记录；
   - 已有明确、匹配当前方案的确认记录 => 记录证据，但仍独立检查规则合规性。
4. 不得用“未发现”代替“已检查”。报告必须列出检查范围、未检查项与限制。

若任务仅要求审查，不得替用户修改代码、执行 SQL 或代替开发者确认；只报告问题和门禁结论。

## 归档 SQL 可移植与直接执行门禁

- 生成或检视初始化、升级、回滚、数据订正等归档 SQL 时，应用目标方言的 `DBS-003`。数据库、账号、schema 和 search_path 均由部署或连接配置提供；检查 SQL 正文、转储头部、注释、客户端指令和占位符。PostgreSQL 也禁止 `target_schema := current_schema()` 一类目标环境绑定、匿名 `DO` 迁移块、迁移条件/循环和动态 SQL，固定操作展开为直接原生 DDL/DML。
- 已有业务行为所必需的函数和触发器保留原生定义；不得新建或调用临时迁移函数来绕过匿名块禁令。对象定义及不兼容数据的前置检查放在独立只读核验或隔离测试中。
- PostgreSQL 的版本升级和回滚从声明的前置版本执行一次，再核验结构、持久数据和配对往返。不能强制每版 DDL 原地连续重跑，不能以该要求引入过程包装。初始化及原生幂等 DML 单独声明重复策略，并仅对这些支持重复的入口验证重跑。MySQL 的重跑要求仍按 `MYSQL-DBS-003`。
- PostgreSQL 的门禁证据包括脱敏的上下文、同一文件在两套不同目标环境从正确前置状态执行的结果，以及预期结构和持久数据对比。对声明可重复的初始化或 DML 补充重跑对比。静态检查仅覆盖高置信分支，不能代替前置状态、业务函数用途和环境可移植性复核。

## 升级与回滚配对

- 按项目归档的同批、同方言配对 upgrade 和 rollback。审查从升级前状态开始，验证升级再回滚后表结构、约束、索引和持久数据一致。恢复升级前定义与恢复原数据均需要证据。
- 已证明的正常逆操作只检查目标方言语法，沿用整批迁移的确认。单向删除存量对象、配对缺失、无法还原数据或证据不足时，仍按现有规则判定。业务演进例外需要开发者明确确认及对应脚本中的原因、范围和恢复说明。
- 可将可信隔离数据库测试的验证回执通过 `--migration-evidence <receipt.json>` 传给 `sql_guard.py`，同时传入整批脚本与回执所依赖的历史升级脚本。普通单文件扫描沿用现有判定。回执无效时门禁失败，不能用 SQL 注释或手写的通过声明替代。

### 既有迁移的直接 SQL 等价展开

这仅用于保留已有批准迁移的原生操作，不是新 DDL 的批准或整文件豁免。可信隔离测试先在相同前置状态和相同夹具上比较旧脚本与直接 SQL 的完整结构、持久数据；有损转换还须用代表性数据核对备份恢复及拒绝路径。测试执行成功后，向现有 version 1 批次回执增加 `expansion`：

- `reference_files`：一一对应当前批次 upgrade/rollback × ddl/dml 四侧，每项为 `{path, reference_path, sha256}`。`path` 是当前文件，`reference_path` 是测试从可信已存在版本提取的旧参考 SQL 临时文件；后者仅作为只读证据，不执行静态迁移门禁。当前文件哈希仍由 `batch.files` 锁定。
- `same_precondition`、`same_fixture`、`schema_equal`、`data_equal` 必须均为 `true`；`comparisons` 的 `precondition`、`fixture`、`schema`、`data` 各项记录 `{reference_sha256, current_sha256}`，必须是实际规范化快照或夹具输入的相等 SHA256。测试必须实际执行，不能手写通过声明。
- `operations` 每项为 `{path, line, end_line?, sql, rule_id, reference_line, reference_end_line?}`。当前范围须定位一条完整顶层 SQL，旧范围须定位同一文件中真正可执行的原生 SQL；只忽略注释和空白，不能改变值或标识符。旧匿名 DO 里的语句可定位；注释、字符串、动态 SQL 和嵌套例程正文不能提供原生操作证据。
- 只覆盖 PostgreSQL 的 `GTAB-004`、`GUPG-003`、`UPG-005`、`UPG-007`、`UPG-008` 五条既有结构规则，逐语句、逐规则定位；`DBS-003` 等其他规则及新增/改变的操作继续阻断。无法确认旧来源或对照不一致时保留失败。
- 同日多版本批次用 `{dialect, batch, upgrade_id, rollback_id}` 区分；旧未提供 V/U 身份的回执继续支持。普通回滚回执保持原结构，允许 `end_line` 定位多行语句；仅支持完整同类删列、同类类型转换、单独 SET NOT NULL 和已验证的简单/级联/延迟 FK 恢复，不覆盖混入其他动作的 ALTER。

## 判定与输出约束

- 同一根因只报一个主问题，可关联多个规则，避免重复噪声。
- 静态规则必须给出可复现证据；人工规则必须给出待确认问题和所需材料。
- Block 报告必须包含可执行的最小整改路径。
- 例外必须记录批准人/角色、范围、理由、有效期和证据链接；没有这些字段视为未批准。
- 不执行生产 SQL，不把生成 SQL 等同于获准执行，不泄露连接串、凭据或敏感数据。
- 报告必须写明 `dialect` 与版本；方言未知时不得输出“符合 MySQL/PostgreSQL 规范”。

## 维护与发布

维护规则或发布版本时读取 [references/submodule-integration.md](references/submodule-integration.md) 和 [rules/README.md](rules/README.md)。规则变更必须通过 PR，更新 `CHANGELOG.md`，按语义化版本打 tag；消费方只通过显式 submodule commit 升级。
