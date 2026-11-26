# 规则库约定

`catalog.json` 是规则路由清单，`common.json` 只保存双方言无差异的规则，`mysql.json` 与 `postgresql.json` 成对保存所有方言差异。每个加载路径都完整覆盖 154 个源条款。`schema.json` 定义规则文件格式。

加载顺序固定为：

- MySQL：`common.json` → `mysql.json`；
- PostgreSQL：`common.json` → `postgresql.json`。

只要语法、语义、支持范围、版本行为或整改方式存在差异，源条款就不得留在 `common.json`，必须拆成两条方言规则。官方规范索引见 `references/dialect-spec-sources.md`。

每条规则包含：

- `id`：稳定 ID，发布后不得复用；
- `source`：附件原始条款编号或 `project:` 项目规则来源；
- `level`：`prohibition | mandatory | recommendation | reference`；
- `gate`：`block | warn | info`；
- `scope`：适用对象；
- `dialects`：规则适用的数据库方言；
- `condition`：可验证的判定条件；
- `check`：`static | manual | hybrid` 及检测提示；
- `examples`：正反例；
- `remediation`：整改建议；
- `confirmation_required`：是否必须进入开发者确认流程。

## 自动门禁覆盖

`MYSQL-DML-001` 和 `POSTGRESQL-DML-001` 阻断直接执行的 `TRUNCATE`。MySQL 可执行注释中的直接语句同样检查。例程和动态 SQL 中的清理操作需要结合上下文检视。

归档 PostgreSQL SQL 应传入 `--archived-sql` 以启用 `POSTGRESQL-UPG-012`。整批重跑必须由隔离数据库执行器验证，静态检查通过不能代替重跑结果。

`check.kind=static` 表示 `scripts/sql_guard.py` 已实现自动判定，列入 JSON 的 `checked_rules`。带有 `check.review_gate` 的混合规则列入 `screened_rules`。候选命中按 `review_gate=warn` 输出，明确的违规分支仍使用规则定义的 `gate`。退出码由实际发现的 Block 决定。

字符集、引擎及分布式事务的候选命中需要结合部署配置和审批记录。可能承载 UUID 的主键列依据数据模型、生成方式或写入代码核实；业务编码可以使用字符类型。`POSTGRESQL-DDL-001` 的并发建索引要求需要结合生产环境、表规模和迁移事务配置评审。

归档门禁使用 `--archived-sql`。检查器对 `MYSQL-DBS-003` 和 `POSTGRESQL-DBS-003` 自动校验同库重跑回执。双环境可移植性和执行器真实性按 `SKILL.md` 另外核验。

回执采用 `{"version":1,"batches":[...]}`。每个批次包含 `dialect`、按实际执行顺序排列的 `files`（每项为 `{path,sha256}`）及按顺序排列的两项 `runs`（每项为 `{database,success,schema_sha256,data_sha256}`）。`database` 为同一次隔离验证内的脱敏库标识。快照 SHA-256 为可信测试执行后采集的规范化结构和持久数据的摘要。升级与回滚分别形成批次，文件必须全部参与检查，且每个文件恰好有一条匹配的记录。执行器负责选择完整批次、前置版本和测试数据，并保证执行间无清库或还原。自动流水线应直接传递自身产生的回执，不接受代码差异附带的手写 JSON。

## 维护规则

1. 规则变更通过 PR，不直接改消费方 submodule 内文件。
2. 新增规则使用新 ID；语义变化不得静默覆盖旧规则。
3. 运行 `python3 scripts/validate_rules.py` 验证每个方言路径的 154 条源覆盖、拆分对称性、方言路由、字段、枚举、ID 唯一性和 static/guard 对账。
4. 逐条审计结论见 `references/dialect-isolation-audit.md`；改变 common allowlist 时必须同步审计表和测试。
5. 更新 `CHANGELOG.md`，按 `MAJOR.MINOR.PATCH` 判断版本：
   - MAJOR：删除规则、改变既有规则语义或新增会让既有合规代码失败的 Block；
   - MINOR：向后兼容地新增规则、检测器或模板能力；
   - PATCH：澄清、误报修复、示例或文档修订，不改变门禁语义。
6. 合并后创建签名 tag（如 `v1.1.0`）和 GitHub Release。

`source` 可追溯附件条款或项目新增规则。以 `project:` 标记的项目规则单独计入规则目录，附件覆盖仍为 154 条。

`source` 仅用于追溯，不代表公共仓库可以转载受限原文。发布前应由规范所有者确认授权和脱敏范围。
