# 规则库约定

`catalog.json` 是规则路由清单，`common.json` 只保存双方言无差异的规则，`mysql.json` 与 `postgresql.json` 成对保存所有方言差异。每个加载路径都完整覆盖 154 个源条款。`schema.json` 定义规则文件格式。

加载顺序固定为：

- MySQL：`common.json` → `mysql.json`；
- PostgreSQL：`common.json` → `postgresql.json`。

只要语法、语义、支持范围、版本行为或整改方式存在差异，源条款就不得留在 `common.json`，必须拆成两条方言规则。官方规范索引见 `references/dialect-spec-sources.md`。

每条规则包含：

- `id`：稳定 ID，发布后不得复用；
- `source`：附件原始条款编号；
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

`check.kind=static` 只用于 `scripts/sql_guard.py` 已实现且无需 live schema 即可高置信判定的公共规则：

公共自动规则为 `G.DEL.01`、`G.INS.01`、`G.SEL.12`、`G.TAB.04`、`G.TAB.16`、`G.TXN.01`、`G.UPD.01`、`G.UPG.03`、`G.UPG.10`、`G.UPG.11`。方言自动规则以 `sql_guard.py` 的 `DIALECT_GUARD_RULES` 与 JSON `checked_rules` 为准。

`hybrid` 规则也可以有明确的高置信语法分支进入 `checked_rules`，但其缺省配置、运行环境或业务语义仍需人工证据。`POSTGRESQL-DDL-001` 依赖生产环境、表规模和迁移事务配置，不因缺少 `CONCURRENTLY` 被脚本直接阻断。

JSON 输出中的 `checked_rules` 明确列出本次自动检查集合。退出码 `0` 只代表该集合未命中，并非加载路径中的全部规则通过。

## 维护规则

1. 规则变更通过 PR，不直接改消费方 submodule 内文件。
2. 新增规则使用新 ID；语义变化不得静默覆盖旧规则。
3. 运行 `python3 scripts/validate_rules.py` 验证每个方言路径的 154 条源覆盖、拆分对称性、方言路由、字段、枚举、ID 唯一性和 static/guard 对账。
4. 更新 `CHANGELOG.md`，按 `MAJOR.MINOR.PATCH` 判断版本：
   - MAJOR：删除规则、改变既有规则语义或新增会让既有合规代码失败的 Block；
   - MINOR：向后兼容地新增规则、检测器或模板能力；
   - PATCH：澄清、误报修复、示例或文档修订，不改变门禁语义。
5. 合并后创建签名 tag（如 `v1.1.0`）和 GitHub Release。

`source` 仅用于追溯，不代表公共仓库可以转载受限原文。发布前应由规范所有者确认授权和脱敏范围。
